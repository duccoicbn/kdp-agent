"""Metadata validation against KDP character limits and field requirements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from kdp_agent.db import BookMetadata

if TYPE_CHECKING:
    from kdp_agent.config import KdpConfig


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]


class MetadataValidator:
    def __init__(self, config: "KdpConfig") -> None:
        self._cfg = config.metadata

    def validate(self, meta: BookMetadata) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        if not meta.title:
            errors.append("Title is empty")
        elif len(meta.title) > self._cfg.title_max_chars:
            errors.append(f"Title too long: {len(meta.title)} > {self._cfg.title_max_chars}")

        if not meta.subtitle:
            warnings.append("Subtitle is empty (optional but recommended)")
        elif len(meta.subtitle) > self._cfg.subtitle_max_chars:
            errors.append(f"Subtitle too long: {len(meta.subtitle)} > {self._cfg.subtitle_max_chars}")

        if not meta.description:
            errors.append("Description is empty")
        elif len(meta.description.split()) < 50:
            warnings.append(f"Description is short ({len(meta.description.split())} words, recommend 300+)")

        if len(meta.keywords) < self._cfg.keyword_count:
            warnings.append(
                f"Only {len(meta.keywords)} keywords (recommend {self._cfg.keyword_count})"
            )
        for i, kw in enumerate(meta.keywords):
            if len(kw) > self._cfg.keyword_max_chars:
                errors.append(f"Keyword {i+1} too long: '{kw[:30]}...' ({len(kw)} chars)")

        if len(meta.categories) < self._cfg.category_count:
            warnings.append(
                f"Only {len(meta.categories)} categories (recommend {self._cfg.category_count})"
            )

        if meta.price_usd < 0.99:
            errors.append(f"Price ${meta.price_usd} is below KDP minimum ($0.99)")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
