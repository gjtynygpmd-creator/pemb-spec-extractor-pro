#!/usr/bin/env python3
"""Local extraction runner for debugging without S3, Postgres, or the worker queue.

It runs the exact same routing the worker uses (rich-text -> regex fast path,
otherwise -> vision path) against a PDF on disk, and prints per-page results.

Usage:
    python -m tools.local_extract path/to/drawings.pdf
    python -m tools.local_extract path/to/spec.pdf --pages 1-5
    python -m tools.local_extract path/to/file.pdf --mock-vision   # simulate vision output

Set ANTHROPIC_API_KEY (and keep VISION_EXTRACTION_ENABLED=true) to exercise the
real vision path. Without a key, non-rich pages report as "needs OCR/review".
"""

from __future__ import annotations

import argparse
import sys

import fitz

from app.core.config import settings
from app.services.document_analysis import (
    classify_page,
    extract_fields,
    page_has_rich_text_layer,
    count_rich_text_labels,
)
from app.services import vision_extraction


def _parse_pages(spec: str, page_count: int) -> list[int]:
    if not spec:
        return list(range(page_count))
    pages: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            pages.update(range(int(a) - 1, int(b)))
        elif part:
            pages.add(int(part) - 1)
    return sorted(p for p in pages if 0 <= p < page_count)


def _install_mock_vision() -> None:
    """Replace the real vision call with a deterministic stub for offline testing."""
    def fake_extract_from_page(page, dpi=None):
        return vision_extraction.VisionResult(
            candidates=[
                {
                    "category": "Geometry", "field_name": "Eave Height", "value": "24'-0\"",
                    "confidence": 0.9, "source_excerpt": "[mock] elevation callout",
                    "match_method": "vision",
                },
                {
                    "category": "Codes & Loads", "field_name": "Basic Wind Speed", "value": "115 mph",
                    "confidence": 0.92, "source_excerpt": "[mock] design criteria block",
                    "match_method": "vision",
                },
            ],
            used=True,
            reason="mock vision",
        )
    vision_extraction.extract_from_page = fake_extract_from_page
    vision_extraction.vision_available = lambda: True


def main() -> int:
    ap = argparse.ArgumentParser(description="Local PEMB extraction runner")
    ap.add_argument("pdf", help="Path to a PDF file")
    ap.add_argument("--pages", default="", help="Page range, e.g. '1-5' or '1,3,7'")
    ap.add_argument("--mock-vision", action="store_true", help="Simulate vision output offline")
    args = ap.parse_args()

    if args.mock_vision:
        _install_mock_vision()

    vision_ready = vision_extraction.vision_available()
    print(f"Vision available: {vision_ready} ({vision_extraction.describe_config()})")
    print(f"Routing thresholds: min_chars={settings.text_layer_min_chars}, "
          f"min_labels={settings.text_layer_min_labels}\n")

    doc = fitz.open(args.pdf)
    page_indices = _parse_pages(args.pages, doc.page_count)

    totals = {"text": 0, "vision": 0, "needs_ocr": 0, "fields": 0}
    for index in page_indices:
        page = doc.load_page(index)
        text = (page.get_text("text") or "").strip()
        blocks = page.get_text("blocks") or []
        blocks_text = "\n".join(
            str(b[4]).strip() for b in sorted(blocks, key=lambda b: (round(b[1] / 18), b[0]))
            if len(b) > 4 and str(b[4]).strip()
        )
        page_type, division, sheet_number, sheet_title = classify_page(text)
        rich = page_has_rich_text_layer(
            text, settings.text_layer_min_chars, settings.text_layer_min_labels
        )
        label_hits = count_rich_text_labels(text)

        if rich:
            method = "text"
            candidates = extract_fields(text, page_type=page_type, division=division, blocks_text=blocks_text)
        else:
            vr = vision_extraction.extract_from_page(page)
            if vr.used and vr.candidates:
                method, candidates = "vision", vr.candidates
            else:
                method, candidates = "needs_ocr", []

        totals[method] += 1
        totals["fields"] += len(candidates)

        header = f"Page {index + 1}"
        if sheet_number:
            label = sheet_number + (f" {sheet_title}" if sheet_title else "")
            header += f"  [{label}]"
        print(f"{header}")
        print(f"  type={page_type or 'unknown'} division={division or '-'} "
              f"chars={len(text)} labels={label_hits} -> route={method}")
        for c in candidates:
            print(f"    - {c['field_name']}: {c['value']}  ({c.get('match_method', method)})")
        print()

    print("Summary:", ", ".join(f"{k}={v}" for k, v in totals.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
