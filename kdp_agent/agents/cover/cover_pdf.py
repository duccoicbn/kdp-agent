"""Export cover PNG to KDP-compliant full-cover PDF (front + spine + back)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image
from reportlab.lib.units import inch as rl_inch
from reportlab.pdfgen import canvas as rl_canvas

from kdp_agent.agents.cover.cover_gen import compute_dimensions

if TYPE_CHECKING:
    from kdp_agent.config import KdpConfig

DPI = 300
PT_PER_INCH = 72.0


def px_to_pt(px: int) -> float:
    return px / DPI * PT_PER_INCH


def build_cover_pdf(
    cover_png: Path,
    pages: int,
    config: "KdpConfig",
    out_path: Path,
) -> Path:
    """
    Create a KDP-compliant full-cover PDF from the composited PNG.

    - Single PDF page = front cover + spine + back cover
    - Dimensions match KDP bleed spec (0.125" bleed on all sides)
    - Embedded at 300 DPI equivalent

    Returns path to output PDF.
    """
    dims = compute_dimensions(pages)
    total_w_px = dims["total_w_px"]
    height_px = dims["height_px"]

    width_pt = px_to_pt(total_w_px)
    height_pt = px_to_pt(height_px)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    c = rl_canvas.Canvas(str(out_path), pagesize=(width_pt, height_pt))

    img = Image.open(cover_png)
    if img.mode != "RGB":
        img = img.convert("RGB")

    tmp_jpg = out_path.with_suffix(".tmp.jpg")
    img.save(str(tmp_jpg), "JPEG", quality=95, dpi=(DPI, DPI))

    c.drawImage(
        str(tmp_jpg),
        0, 0,
        width=width_pt,
        height=height_pt,
        preserveAspectRatio=False,
    )

    c.setTitle(out_path.stem)
    c.setAuthor(getattr(config, "default_author", "KDP Agent"))
    c.setSubject("KDP Full Cover")
    c.showPage()
    c.save()

    tmp_jpg.unlink(missing_ok=True)

    return out_path


def get_spine_text(title: str, author: str, pages: int) -> str | None:
    """Return spine text if spine is wide enough (>= 130 pages ~0.35 inches)."""
    min_spine_pages = 130
    if pages < min_spine_pages:
        return None
    return f"{title}  ·  {author}"
