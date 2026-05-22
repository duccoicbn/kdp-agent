"""Cross-volume seed and prompt deduplication helpers."""

from __future__ import annotations

import hashlib
import random
from datetime import datetime

from kdp_agent.db import KdpSeries, PromptFingerprint


def prompt_fingerprint(theme: str, sub_theme: str = "") -> str:
    """Stable 16-char hash for theme deduplication."""
    normalized = " ".join(f"{theme}|{sub_theme}".lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def check_theme_collision(
    series: KdpSeries,
    theme: str,
    sub_theme: str = "",
) -> PromptFingerprint | None:
    """Return matching fingerprint record if this theme was used before."""
    target = prompt_fingerprint(theme, sub_theme)
    for record in series.used_prompts:
        if record.hash == target:
            return record
    return None


def select_seeds(series: KdpSeries, count: int) -> list[int]:
    """Pick `count` random seeds that have not been used in this series."""
    if count < 1:
        return []

    forbidden = set(series.used_seeds)
    selected: list[int] = []
    while len(selected) < count:
        seed = random.randint(1, 2**32 - 1)
        if seed in forbidden:
            continue
        selected.append(seed)
        forbidden.add(seed)
    return selected


def build_prompt_record(
    theme: str,
    sub_theme: str,
    volume_number: int,
    book_id: str,
    forced: bool = False,
) -> PromptFingerprint:
    """Create a serializable record for a generated volume prompt."""
    return PromptFingerprint(
        hash=prompt_fingerprint(theme, sub_theme),
        theme=theme,
        sub_theme=sub_theme,
        volume_number=volume_number,
        book_id=book_id,
        forced=forced,
        created_at=datetime.utcnow(),
    )
