"""KDP-compliant PDF assembly for coloring book interiors."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image
from reportlab.lib.pagesizes import inch
from reportlab.lib.units import inch as rl_inch
from reportlab.pdfgen import canvas

if TYPE_CHECKING:
    from kdp_agent.config import KdpConfig

# KDP standard coloring book: 8.5" × 11" with 0.125" bleed
TRIM_W = 8.5
TRIM_H = 11.0
BLEED = 0.125

# Full page size with bleed
PAGE_W = TRIM_W + 2 * BLEED
PAGE_H = TRIM_H + 2 * BLEED


class PdfBuilder:
    """Assemble KDP-compliant interior PDF from page images."""

    def __init__(self, config: "KdpConfig") -> None:
        self._cfg = config.generation

    def build_interior(self, page_paths: list[Path], output_path: Path) -> Path:
        """
        Build single-sided KDP interior PDF.
        Each coloring design is on a right-hand (odd) page; even pages are blank.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        page_w_pt = PAGE_W * rl_inch
        page_h_pt = PAGE_H * rl_inch
        bleed_pt = BLEED * rl_inch

        c = canvas.Canvas(str(output_path), pagesize=(page_w_pt, page_h_pt))
        c.setTitle("Coloring Book Interior")

        for i, img_path in enumerate(page_paths):
            # --- Design page (odd page) ---
            self._draw_image_page(c, img_path, page_w_pt, page_h_pt, bleed_pt)
            c.showPage()

            # --- Blank backing page (even page, prevents bleed-through) ---
            c.setPageSize((page_w_pt, page_h_pt))
            c.showPage()

        c.save()
        return output_path

    def _draw_image_page(
        self,
        c: canvas.Canvas,
        img_path: Path,
        page_w: float,
        page_h: float,
        bleed: float,
    ) -> None:
        # Fill white background first
        c.setFillColorRGB(1, 1, 1)
        c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

        # Draw image filling the trim area (inside bleed)
        img = Image.open(img_path)
        # Convert to grayscale (line art)
        img = img.convert("L")

        # Image area = trim area = page minus bleed on all sides
        img_x = bleed
        img_y = bleed
        img_w = page_w - 2 * bleed
        img_h = page_h - 2 * bleed

        c.drawImage(
            str(img_path),
            img_x,
            img_y,
            width=img_w,
            height=img_h,
            preserveAspectRatio=True,
            anchor="c",
        )

    def get_page_count_for_books(self, design_count: int) -> int:
        """Return total PDF page count: each design = 2 pages (design + blank)."""
        return design_count * 2
