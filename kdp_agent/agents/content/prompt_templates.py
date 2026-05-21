"""Prompt templates for Space/Universe and Anime coloring book styles."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kdp_agent.config import KdpConfig

STYLE_TEMPLATES: dict[str, str] = {
    "space": (
        "detailed line art coloring book page, {theme}, outer space scene, "
        "nebula clouds, distant planets, stars, astronaut, spacecraft, cosmic elements, "
        "black and white only, thick clean outlines, no fill, no shading, no gray tones, "
        "white background, intricate details, adult coloring book style, "
        "high contrast, professional illustration"
    ),
    "anime": (
        "manga line art coloring book page, {theme}, anime style character, "
        "clean black outlines, no fill, no shading, black and white only, "
        "white background, thick bold lines, expressive eyes, dynamic pose, "
        "detailed clothing, adult coloring book style, professional manga illustration"
    ),
    "mandala": (
        "intricate mandala coloring book page, {theme}, geometric symmetrical pattern, "
        "floral elements, ornate details, black and white only, clean lines, "
        "no fill, no shading, white background, adult coloring book, "
        "circular composition, high detail"
    ),
}

_DEFAULT_NEGATIVE = (
    "known anime characters, naruto, goku, luffy, pikachu, dragon ball, "
    "one piece, bleach, attack on titan, existing IP, copyrighted characters, "
    "watermark, logo, text, brand names, famous fictional characters, "
    "trademarked characters, signature, low quality, blurry, jpeg artifacts, "
    "color, colored, filled shapes, gray tones, shadows, gradients, "
    "3d render, photorealistic, photograph"
)


def build_prompt(theme: str, style: str, config: "KdpConfig") -> str:
    """Build a positive prompt for the given theme and style."""
    template = STYLE_TEMPLATES.get(style, STYLE_TEMPLATES["space"])
    return template.format(theme=theme)


def build_negative_prompt(config: "KdpConfig") -> str:
    """Build the negative prompt, merging baseline with config overrides."""
    baseline = config.image_gen.negative_prompts_baseline.strip()
    if baseline:
        return f"{_DEFAULT_NEGATIVE}, {baseline}"
    return _DEFAULT_NEGATIVE
