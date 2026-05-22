"""Capture and apply reusable visual DNA for multi-volume series."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PIL import Image

from kdp_agent.agents.content.prompt_templates import build_negative_prompt, build_prompt
from kdp_agent.config import KdpConfig
from kdp_agent.db import BookStatus, KdpBook, StyleDna


def extract_palette(image_path: Path, max_colors: int = 5) -> list[str]:
    """Extract a small dominant color palette from a cover/reference image."""
    if not image_path.exists():
        return []

    img = Image.open(image_path).convert("RGB")
    img.thumbnail((128, 128))
    quantized = img.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette() or []
    counts = quantized.getcolors(maxcolors=128 * 128) or []
    counts.sort(reverse=True)

    colors: list[str] = []
    for _, idx in counts[:max_colors]:
        offset = idx * 3
        r, g, b = palette[offset : offset + 3]
        colors.append(f"#{r:02X}{g:02X}{b:02X}")
    return colors


def collect_reference_images(book: KdpBook, limit: int = 5) -> list[str]:
    """Collect up to `limit` generated page image paths from a book output folder."""
    pages_dir = Path(book.files.pages_dir) if book.files.pages_dir else None
    if not pages_dir or not pages_dir.exists():
        return []
    return [str(path) for path in sorted(pages_dir.glob("page_*.png"))[:limit]]


def build_character_descriptor(book: KdpBook) -> str:
    """
    Build a deterministic descriptor from existing book metadata.

    This is deliberately local/offline. A future improvement can ask Ollama to
    summarize prompts, but this keeps `freeze-dna` usable without LLM services.
    """
    title = book.metadata.title or book.theme
    return (
        f"{book.style} coloring book style for '{title}', "
        f"theme '{book.theme}', niche '{book.niche}', consistent original characters"
    )


def capture_dna(book: KdpBook, config: KdpConfig) -> StyleDna:
    """Capture Style DNA from an approved/live book."""
    if book.status not in {BookStatus.APPROVED, BookStatus.LIVE}:
        raise ValueError("Style DNA can only be frozen from an approved or live book")

    prompt_template = build_prompt(theme=book.theme, style=book.style, config=config)
    negative_prompt = build_negative_prompt(config)

    cover_candidates = [
        Path(book.files.cover_jpg) if book.files.cover_jpg else None,
        Path(book.files.cover_pdf) if book.files.cover_pdf else None,
    ]
    palette: list[str] = []
    for candidate in cover_candidates:
        if candidate and candidate.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            palette = extract_palette(candidate)
            if palette:
                break

    return StyleDna(
        prompt_template=prompt_template,
        negative_prompt=negative_prompt,
        palette=palette,
        character_descriptor=build_character_descriptor(book),
        reference_image_paths=collect_reference_images(book),
        captured_at=datetime.utcnow(),
        captured_from_book_id=book.id,
    )


def apply_dna(prompt: str, dna: StyleDna) -> str:
    """Inject series style hints into a base image prompt."""
    if not dna.is_frozen:
        return prompt

    hints: list[str] = [prompt, "in the SAME STYLE as previous volumes"]
    if dna.character_descriptor:
        hints.append(f"series character/style descriptor: {dna.character_descriptor}")
    if dna.palette:
        hints.append(f"use consistent palette cues: {', '.join(dna.palette)}")
    return ". ".join(hints)
