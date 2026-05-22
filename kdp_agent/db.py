"""SurrealDB client wrapper with KdpBook model."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from kdp_agent.config import get_config


class BookStatus(str, Enum):
    RESEARCH = "research"
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHING = "publishing"
    LIVE = "live"
    REJECTED = "rejected"


class SeriesStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class RelationshipType(str, Enum):
    STANDALONE = "standalone"
    VOLUME = "volume"
    ANTHOLOGY_ENTRY = "anthology_entry"


class BookMetadata(BaseModel):
    title: str = ""
    subtitle: str = ""
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    price_usd: float = 8.99


class BookFiles(BaseModel):
    interior_pdf: str = ""
    cover_pdf: str = ""
    cover_jpg: str = ""
    pages_dir: str = ""


class BookKdp(BaseModel):
    asin: str = ""
    publish_date: Optional[datetime] = None
    bsr: int = 0
    review_count: int = 0
    approval_status: str = ""


class StyleDna(BaseModel):
    prompt_template: str = ""
    negative_prompt: str = ""
    palette: list[str] = Field(default_factory=list)
    character_descriptor: str = ""
    reference_image_paths: list[str] = Field(default_factory=list)
    captured_at: Optional[datetime] = None
    captured_from_book_id: str = ""

    @property
    def is_frozen(self) -> bool:
        """A DNA profile is usable once it has at least style text or references."""
        return bool(
            self.character_descriptor
            or self.prompt_template
            or self.reference_image_paths
        )


class PromptFingerprint(BaseModel):
    hash: str
    theme: str
    sub_theme: str = ""
    volume_number: int = 0
    book_id: str = ""
    forced: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class KdpSeries(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    brand: str = ""
    author: str = "KDP Agent"
    style: str = "anime"
    status: SeriesStatus = SeriesStatus.ACTIVE
    style_dna: StyleDna = Field(default_factory=StyleDna)
    used_seeds: list[int] = Field(default_factory=list)
    used_prompts: list[PromptFingerprint] = Field(default_factory=list)
    volume_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class KdpBook(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    niche: str
    theme: str
    style: str = "space"
    status: BookStatus = BookStatus.DRAFT
    pages_generated: int = 0
    cover_generated: bool = False
    metadata: BookMetadata = Field(default_factory=BookMetadata)
    files: BookFiles = Field(default_factory=BookFiles)
    kdp: BookKdp = Field(default_factory=BookKdp)
    page_seeds: list[int] = Field(default_factory=list)
    series_id: str = ""
    volume_number: int = 0
    relationship_type: RelationshipType = RelationshipType.STANDALONE
    publish_state: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class KdpDb:
    """Thin async wrapper around SurrealDB for KDP Agent."""

    def __init__(self) -> None:
        self._client: Any = None
        cfg = get_config().surreal
        self._url = cfg.url
        self._ns = cfg.namespace
        self._db = cfg.database

    async def connect(self) -> None:
        try:
            from surrealdb import AsyncSurreal  # type: ignore
            self._client = AsyncSurreal(self._url)
            await self._client.connect()
            await self._client.use(self._ns, self._db)
        except Exception as exc:
            raise RuntimeError(f"SurrealDB connect failed ({self._url}): {exc}") from exc

    async def disconnect(self) -> None:
        if self._client:
            await self._client.close()

    async def create_book(self, book: KdpBook) -> KdpBook:
        data = book.model_dump(mode="json")
        result = await self._client.create("kdp_book", data)
        return book

    async def get_book(self, book_id: str) -> Optional[KdpBook]:
        results = await self._client.query(
            "SELECT * FROM kdp_book WHERE id = $id LIMIT 1",
            {"id": book_id},
        )
        if results and results[0]:
            return KdpBook(**results[0][0])
        return None

    async def update_book(self, book: KdpBook) -> None:
        book.updated_at = datetime.utcnow()
        data = book.model_dump(mode="json")
        await self._client.query(
            "UPDATE kdp_book SET $data WHERE id = $id",
            {"data": data, "id": book.id},
        )

    async def list_books(self, status: Optional[BookStatus] = None) -> list[KdpBook]:
        if status:
            results = await self._client.query(
                "SELECT * FROM kdp_book WHERE status = $status ORDER BY created_at DESC",
                {"status": status.value},
            )
        else:
            results = await self._client.query(
                "SELECT * FROM kdp_book ORDER BY created_at DESC"
            )
        rows = results[0] if results else []
        return [KdpBook(**row) for row in rows]

    async def update_status(self, book_id: str, status: BookStatus) -> None:
        await self._client.query(
            "UPDATE kdp_book SET status = $status, updated_at = time::now() WHERE id = $id",
            {"status": status.value, "id": book_id},
        )

    async def create_series(self, series: KdpSeries) -> KdpSeries:
        data = series.model_dump(mode="json")
        await self._client.create("kdp_series", data)
        return series

    async def get_series(self, name_or_id: str) -> Optional[KdpSeries]:
        results = await self._client.query(
            "SELECT * FROM kdp_series WHERE id = $value OR name = $value LIMIT 1",
            {"value": name_or_id},
        )
        rows = results[0] if results else []
        if not rows:
            return None
        return KdpSeries(**rows[0])

    async def list_series(
        self,
        brand: str = "",
        status: Optional[SeriesStatus] = None,
    ) -> list[KdpSeries]:
        clauses = []
        params: dict[str, Any] = {}
        if brand:
            clauses.append("brand = $brand")
            params["brand"] = brand
        if status:
            clauses.append("status = $status")
            params["status"] = status.value

        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        results = await self._client.query(
            f"SELECT * FROM kdp_series{where} ORDER BY created_at DESC",
            params,
        )
        rows = results[0] if results else []
        return [KdpSeries(**row) for row in rows]

    async def update_series(self, series: KdpSeries) -> None:
        series.updated_at = datetime.utcnow()
        data = series.model_dump(mode="json")
        await self._client.query(
            "UPDATE kdp_series SET $data WHERE id = $id",
            {"data": data, "id": series.id},
        )

    async def list_series_volumes(self, series_id: str) -> list[KdpBook]:
        results = await self._client.query(
            "SELECT * FROM kdp_book WHERE series_id = $series_id ORDER BY volume_number ASC",
            {"series_id": series_id},
        )
        rows = results[0] if results else []
        return [KdpBook(**row) for row in rows]


_db: Optional[KdpDb] = None


def get_db() -> KdpDb:
    """Return singleton KdpDb (must call connect() before use)."""
    global _db
    if _db is None:
        _db = KdpDb()
    return _db
