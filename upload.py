"""Provider-agnostic vision-based PEMB field extraction.

This is the primary extraction path for drawings and any page whose embedded
text layer is too sparse or too spatially scattered for the regex engine to
read reliably. Each page is rendered to an image and sent to a vision model,
which is asked to return the PEMB estimator field schema as JSON.

Two providers are supported behind a single config switch (settings.vision_provider):
  - "openai"    (default) uses the OpenAI Chat Completions API with an image
  - "anthropic" uses the Claude Messages API with an image

The module degrades gracefully: if the selected provider has no API key or the
SDK is not installed, it returns an empty result and a human-readable reason
instead of raising, so the worker can fall back to flagging the page for
OCR/manual review rather than crashing the whole job.
"""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass, field

from app.core.config import settings
from app.services import schema_loader
from app.services.document_analysis import normalize_field_value, normalize_space

log = logging.getLogger("pemb-worker.vision")

_SYSTEM_PROMPT = (
    "You read a single sheet from a pre-engineered metal building (PEMB) "
    "drawing set or specification manual and pull out estimating data. "
    "You are precise and never guess. If a value is not clearly present on "
    "the sheet, you omit that field rather than inferring it."
)


def _user_instructions() -> str:
    # Built from the canonical schema so the prompt always matches the field dictionary.
    return schema_loader.build_vision_instructions()


@dataclass
class VisionResult:
    candidates: list[dict] = field(default_factory=list)
    used: bool = False          # True if a model call actually ran
    reason: str = ""            # why it did/did not run, for logging/telemetry


# ---------------------------------------------------------------------------
# Provider selection and availability
# ---------------------------------------------------------------------------

def _provider() -> str:
    return (settings.vision_provider or "openai").strip().lower()


def active_model() -> str:
    return settings.vision_model_anthropic if _provider() == "anthropic" else settings.vision_model_openai


def _provider_key() -> str:
    return settings.anthropic_api_key if _provider() == "anthropic" else settings.openai_api_key


def _sdk_available() -> bool:
    try:
        if _provider() == "anthropic":
            import anthropic  # noqa: F401
        else:
            import openai  # noqa: F401
    except Exception:
        return False
    return True


def vision_available() -> bool:
    """True when a vision call can be attempted (feature on + key + SDK)."""
    if not settings.vision_extraction_enabled:
        return False
    if not _provider_key():
        return False
    return _sdk_available()


def describe_config() -> str:
    """One-line human-readable summary for logs and the local tool."""
    return f"provider={_provider()} model={active_model()} dpi={settings.vision_dpi}"


# ---------------------------------------------------------------------------
# Rendering and parsing
# ---------------------------------------------------------------------------

def render_page_png(page, dpi: int | None = None) -> bytes:
    """Render a PyMuPDF page to PNG bytes, bounded so large sheets can't OOM.

    The target resolution is settings.vision_dpi, but the longest edge is capped at
    settings.vision_max_edge_px. A 34x22 in ARCH-D sheet at 200 DPI would be ~6800x4400
    px (~90 MB raw); capping the edge keeps every render to a few MB regardless of the
    physical sheet size, which is what previously risked killing the worker.
    """
    import fitz

    dpi = dpi or settings.vision_dpi
    zoom = dpi / 72.0
    rect = page.rect
    longest_pt = max(rect.width, rect.height) or 1.0
    max_edge = max(256, settings.vision_max_edge_px)
    # Scale down if the requested zoom would exceed the pixel cap on the long edge.
    if longest_pt * zoom > max_edge:
        zoom = max_edge / longest_pt
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    try:
        return pix.tobytes("png")
    finally:
        # Release the pixmap buffer promptly rather than waiting for GC.
        pix = None


def _parse_model_json(raw: str) -> list[dict]:
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1] if raw.count("```") >= 2 else raw.strip("`")
        if raw.lstrip().lower().startswith("json"):
            raw = raw.lstrip()[4:]
    raw = raw.strip().strip("`").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return []
        try:
            data = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return []
    if isinstance(data, dict):
        items = data.get("fields", [])
    elif isinstance(data, list):
        items = data
    else:
        items = []
    return items if isinstance(items, list) else []


def _normalize_candidates(items: list[dict]) -> list[dict]:
    """Validate model output against the canonical schema.

    Accepts either a field_id (preferred, what the prompt asks for) or a display
    name, resolves it to the canonical field, coerces enum values to an allowed
    option, and drops anything not in the schema.
    """
    out: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        key = normalize_space(str(item.get("field_id") or item.get("field_name") or ""))
        field_def = schema_loader.resolve(key)
        if not field_def:
            continue
        raw_value = normalize_space(str(item.get("value", "")))
        if not raw_value:
            continue
        note = normalize_space(str(item.get("source_note", "")))
        cleaned = schema_loader.coerce_value(field_def.field_id, raw_value)
        if not cleaned:
            continue
        try:
            confidence = float(item.get("confidence", 0.8))
        except (TypeError, ValueError):
            confidence = 0.8
        confidence = max(0.4, min(0.98, confidence))
        try:
            normalized = normalize_field_value(field_def.name, cleaned)
        except Exception:
            normalized = cleaned
        out.append(
            {
                "category": field_def.category,
                "field_name": field_def.name,
                "value": cleaned,
                "normalized_value": normalized,
                "confidence": confidence,
                "source_excerpt": note or "Read from rendered page by vision model",
                "match_method": "vision",
            }
        )
    return out


# ---------------------------------------------------------------------------
# Provider calls
# ---------------------------------------------------------------------------

def _call_openai(b64_png: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    resp = client.chat.completions.create(
        model=settings.vision_model_openai,
        max_tokens=3000,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _user_instructions()},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64_png}"},
                    },
                ],
            },
        ],
    )
    return resp.choices[0].message.content or ""


def _call_anthropic(b64_png: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=settings.vision_model_anthropic,
        max_tokens=3000,
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": b64_png,
                        },
                    },
                    {"type": "text", "text": _user_instructions()},
                ],
            }
        ],
    )
    return "".join(
        block.text for block in message.content if getattr(block, "type", "") == "text"
    )


def extract_from_png(png_bytes: bytes) -> VisionResult:
    """Send a rendered page image to the configured provider and normalize results."""
    if not vision_available():
        return VisionResult(reason=f"vision unavailable ({describe_config()}; feature off, no key, or SDK missing)")
    try:
        b64 = base64.standard_b64encode(png_bytes).decode("ascii")
        raw = _call_anthropic(b64) if _provider() == "anthropic" else _call_openai(b64)
        candidates = _normalize_candidates(_parse_model_json(raw))
        return VisionResult(candidates=candidates, used=True, reason=f"{len(candidates)} field(s) via {_provider()}")
    except Exception as exc:  # never let a vision failure kill the job
        log.warning("Vision extraction failed (%s): %s", _provider(), exc)
        return VisionResult(reason=f"vision error ({_provider()}): {exc}")


def extract_from_page(page, dpi: int | None = None) -> VisionResult:
    """Render a PyMuPDF page and run vision extraction on it."""
    if not vision_available():
        return VisionResult(reason=f"vision unavailable ({describe_config()}; feature off, no key, or SDK missing)")
    try:
        png = render_page_png(page, dpi=dpi)
    except Exception as exc:
        log.warning("Page render failed: %s", exc)
        return VisionResult(reason=f"render error: {exc}")
    return extract_from_png(png)
