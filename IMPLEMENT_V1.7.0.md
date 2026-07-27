"""Regression test for v1.9.2 memory safety.

Large-format sheets must not render to unbounded bitmaps (the cause of the
worker being OOM-killed and the job hanging at 18%). Run from backend/:
    DATABASE_URL=postgresql://unused python tests/test_render_bounds.py
"""

import fitz

from app.core.config import settings
from app.services.vision_extraction import render_page_png


def _edge_for(width_in, height_in):
    doc = fitz.open()
    page = doc.new_page(width=width_in * 72, height=height_in * 72)
    png = render_page_png(page, dpi=settings.vision_dpi)
    pix = fitz.Pixmap(png)
    return max(pix.width, pix.height)


def test_large_sheet_is_bounded():
    # ARCH-D (34x22 in) and ARCH-E (48x36 in) must both respect the edge cap.
    assert _edge_for(34, 22) <= settings.vision_max_edge_px
    assert _edge_for(48, 36) <= settings.vision_max_edge_px


def test_small_page_not_upscaled_past_cap():
    # A letter-size page at target DPI stays well under the cap.
    assert _edge_for(8.5, 11) <= settings.vision_max_edge_px


if __name__ == "__main__":
    test_large_sheet_is_bounded()
    test_small_page_not_upscaled_past_cap()
    print("All v1.9.2 render-bound tests passed.")
