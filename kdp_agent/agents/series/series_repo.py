"""Repository/service helpers for KDP series records."""

from __future__ import annotations

from kdp_agent.agents.series.dedup import build_prompt_record
from kdp_agent.db import KdpBook, KdpDb, KdpSeries, SeriesStatus, StyleDna


class SeriesNotFoundError(ValueError):
    """Raised when a named series does not exist."""


class SeriesDnaMissingError(ValueError):
    """Raised when generating a later volume before freezing Style DNA."""


class SeriesRepository:
    """High-level operations for series and volume tracking."""

    def __init__(self, db: KdpDb) -> None:
        self._db = db

    async def create_series(
        self,
        name: str,
        style: str,
        brand: str = "",
        author: str = "KDP Agent",
    ) -> KdpSeries:
        existing = await self._db.get_series(name)
        if existing:
            raise ValueError(f"Series already exists: {name}")
        series = KdpSeries(name=name, style=style, brand=brand, author=author)
        return await self._db.create_series(series)

    async def get_required(self, name_or_id: str) -> KdpSeries:
        series = await self._db.get_series(name_or_id)
        if not series:
            raise SeriesNotFoundError(f"Series not found: {name_or_id}")
        return series

    async def list_series(
        self,
        brand: str = "",
        status: SeriesStatus | None = None,
    ) -> list[KdpSeries]:
        return await self._db.list_series(brand=brand, status=status)

    async def archive_series(self, name_or_id: str) -> KdpSeries:
        series = await self.get_required(name_or_id)
        series.status = SeriesStatus.ARCHIVED
        await self._db.update_series(series)
        return series

    async def update_dna(self, name_or_id: str, dna: StyleDna) -> KdpSeries:
        series = await self.get_required(name_or_id)
        series.style_dna = dna
        await self._db.update_series(series)
        return series

    async def list_volumes(self, series: KdpSeries) -> list[KdpBook]:
        return await self._db.list_series_volumes(series.id)

    async def next_volume_number(self, series: KdpSeries) -> int:
        volumes = await self.list_volumes(series)
        existing = [book.volume_number for book in volumes if book.volume_number > 0]
        return max(existing, default=0) + 1

    async def ensure_dna_ready(self, series: KdpSeries) -> None:
        if not series.style_dna.is_frozen:
            raise SeriesDnaMissingError(
                f"Series '{series.name}' has no frozen Style DNA. "
                "Run: kdp-agent series freeze-dna <series> --from-book <vol1_id>"
            )

    async def commit_dedup_record(
        self,
        series: KdpSeries,
        seeds: list[int],
        theme: str,
        sub_theme: str,
        volume_number: int,
        book_id: str,
        forced: bool = False,
    ) -> KdpSeries:
        record = build_prompt_record(
            theme=theme,
            sub_theme=sub_theme,
            volume_number=volume_number,
            book_id=book_id,
            forced=forced,
        )
        series.used_seeds.extend(seeds)
        existing = next(
            (
                item
                for item in series.used_prompts
                if item.hash == record.hash and item.book_id == book_id
            ),
            None,
        )
        if existing:
            existing.forced = existing.forced or forced
        else:
            series.used_prompts.append(record)
        series.volume_count = max(series.volume_count, volume_number)
        await self._db.update_series(series)
        return series
