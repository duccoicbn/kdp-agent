"""Cover generation agent: AI central art + SVG template compositing + typography."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from kdp_agent.config import KdpConfig

TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "assets" / "cover-templates"

# KDP spine formula: total_pages × 0.002252 + 0.06 inches (for white paper, 60# offset)
SPINE_PER_PAGE_IN = 0.002252
SPINE_BASE_IN = 0.06
DPI = 300


def compute_dimensions(pages: int) -> dict[str, float]:
    """Return cover canvas dimensions in pixels at 300 DPI."""
    bleed = 0.125
    front_w = 8.5 + bleed
    height = 11.0 + bleed * 2
    spine_w = pages * SPINE_PER_PAGE_IN + SPINE_BASE_IN
    back_w = 8.5 + bleed
    total_w = front_w + spine_w + back_w
    return {
        "total_w_px": int(total_w * DPI),
        "height_px": int(height * DPI),
        "front_w_px": int(front_w * DPI),
        "spine_w_px": int(spine_w * DPI),
        "back_w_px": int(back_w * DPI),
        "spine_w_in": spine_w,
        "bleed_px": int(bleed * DPI),
    }


def select_template(style: str) -> Path:
    """Pick best SVG template for the given art style."""
    mapping = {
        "space": TEMPLATES_DIR / "space-dark.svg",
        "space_light": TEMPLATES_DIR / "space-light.svg",
        "anime": TEMPLATES_DIR / "anime-vibrant.svg",
        "anime_minimal": TEMPLATES_DIR / "anime-minimal.svg",
    }
    return mapping.get(style, TEMPLATES_DIR / "universal.svg")


async def generate_central_art(
    prompt: str,
    config: "KdpConfig",
    out_path: Path,
    style: str = "space",
) -> Path:
    """
    Generate central cover art using the same provider stack as interior pages
    (Replicate primary, Together.ai fallback — controlled via kdp-config.yaml).
    Returns path to downloaded PNG.
    """
    from kdp_agent.agents.content.image_gen import ImageGenerator

    negative = (
        "text, watermark, signature, blurry, low quality, "
        "nsfw, trademarked characters, copyrighted"
    )
    full_prompt = (
        f"{prompt}, coloring book cover art, professional illustration, "
        "vibrant colors, centered composition, square format, no text"
    )

    gen = ImageGenerator(config)
    return await gen.generate(
        prompt=full_prompt,
        output_path=out_path,
        negative_prompt=negative,
        style=style,
    )


def _px(value_str: str) -> int:
    """Parse SVG coordinate string to int."""
    return int(float(re.sub(r"[^\d.\-]", "", value_str)))


def composite_cover(
    template_path: Path,
    central_art_path: Path,
    title: str,
    author: str,
    pages: int,
    out_path: Path,
    subtitle: str = "COLORING BOOK",
) -> Path:
    """
    Rasterize SVG template, paste AI art, and render text overlays.
    Returns path to final cover PNG.
    """
    dims = compute_dimensions(pages)
    total_w = dims["total_w_px"]
    height = dims["height_px"]

    try:
        import cairosvg  # type: ignore
        png_bytes = cairosvg.svg2png(
            url=str(template_path),
            output_width=total_w,
            output_height=height,
        )
        canvas = Image.open(__import__("io").BytesIO(png_bytes)).convert("RGBA")
    except ImportError:
        canvas = Image.new("RGBA", (total_w, height), (3, 0, 28, 255))

    tree = ET.parse(template_path)
    root = tree.getroot()
    ns = {"svg": "http://www.w3.org/2000/svg"}

    bounds_el = root.find(".//*[@id='central_art_bounds']", ns)
    if bounds_el is not None:
        art_x = _px(bounds_el.get("x", "412"))
        art_y = _px(bounds_el.get("y", "500"))
        art_w = _px(bounds_el.get("width", "1800"))
        art_h = _px(bounds_el.get("height", "1800"))

        # Scale coordinates from SVG viewBox (2625×3375) to actual canvas
        vb_w, vb_h = 2625, 3375
        scale_x = total_w / vb_w
        scale_y = height / vb_h

        art_img = Image.open(central_art_path).convert("RGBA")
        art_img = art_img.resize(
            (int(art_w * scale_x), int(art_h * scale_y)),
            Image.LANCZOS,
        )
        canvas.paste(art_img, (int(art_x * scale_x), int(art_y * scale_y)), art_img)

    draw = ImageDraw.Draw(canvas)

    def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        for name in ["DejaVuSerif.ttf", "Georgia.ttf", "arial.ttf"]:
            for base in ["/usr/share/fonts", "/Library/Fonts", "C:/Windows/Fonts"]:
                p = Path(base) / name
                if p.exists():
                    return ImageFont.truetype(str(p), size)
        return ImageFont.load_default()

    scale_x = total_w / 2625
    scale_y = height / 3375

    title_font = load_font(int(90 * scale_y))
    subtitle_font = load_font(int(48 * scale_y))
    author_font = load_font(int(48 * scale_y))

    title_y = int(2500 * scale_y)
    sub_y = int(2640 * scale_y)
    author_y = int(3200 * scale_y)

    def draw_centered(text: str, y: int, font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
                      fill: tuple) -> None:
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((total_w - w) // 2, y), text, font=font, fill=fill)

    draw_centered(title.upper(), title_y, title_font, (230, 213, 255, 255))
    draw_centered(subtitle, sub_y, subtitle_font, (155, 114, 207, 200))
    draw_centered(author, author_y, author_font, (123, 94, 167, 200))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(str(out_path), "PNG")
    return out_path


async def generate_cover(
    book_id: str,
    title: str,
    author: str,
    niche: str,
    style: str,
    pages: int,
    config: "KdpConfig",
    output_dir: Path,
) -> dict[str, Path]:
    """
    Full cover generation pipeline:
    1. Generate central art via Replicate
    2. Composite onto SVG template
    3. Return paths to art PNG and full cover PNG
    """
    art_prompt = f"{niche}, {style} style, coloring book cover illustration"

    art_path = output_dir / f"{book_id}_cover_art.png"
    cover_path = output_dir / f"{book_id}_cover_full.png"

    await generate_central_art(art_prompt, config, art_path, style=style)

    template = select_template(style)
    composite_cover(
        template_path=template,
        central_art_path=art_path,
        title=title,
        author=author,
        pages=pages,
        out_path=cover_path,
    )

    return {"art": art_path, "cover": cover_path}
