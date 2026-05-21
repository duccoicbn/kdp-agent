"""FastAPI dashboard for reviewing and approving KDP books."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from kdp_agent.config import get_config
from kdp_agent.db import BookStatus, KdpBook, get_db

_ROOT = Path(__file__).parent.parent.parent

app = FastAPI(title="KDP Agent Dashboard", version="0.1.0")

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Mount output directory for serving generated images/PDFs
if (_ROOT / "output").exists():
    app.mount("/output", StaticFiles(directory=str(_ROOT / "output")), name="output")


@app.on_event("startup")
async def startup() -> None:
    db = get_db()
    try:
        await db.connect()
    except Exception:
        pass  # Dashboard still loads even if DB is down


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    db = get_db()
    try:
        books = await db.list_books()
    except Exception:
        books = []

    status_counts: dict[str, int] = {}
    for book in books:
        status_counts[book.status.value] = status_counts.get(book.status.value, 0) + 1

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "books": books, "status_counts": status_counts},
    )


@app.get("/book/{book_id}", response_class=HTMLResponse)
async def book_review(request: Request, book_id: str) -> HTMLResponse:
    db = get_db()
    book = await db.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    pages_dir = Path(book.files.pages_dir) if book.files.pages_dir else None
    page_files: list[str] = []
    if pages_dir and pages_dir.exists():
        page_files = sorted([
            f"/output/{book_id}/pages/{p.name}"
            for p in pages_dir.glob("page_*.png")
        ])

    return templates.TemplateResponse(
        "review.html",
        {
            "request": request,
            "book": book,
            "page_files": page_files,
            "cover_jpg": f"/output/{book_id}/cover.jpg" if book.files.cover_jpg else None,
        },
    )


@app.post("/api/book/{book_id}/approve")
async def approve_book(book_id: str) -> JSONResponse:
    db = get_db()
    book = await db.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    await db.update_status(book_id, BookStatus.APPROVED)
    return JSONResponse({"status": "approved", "book_id": book_id})


@app.post("/api/book/{book_id}/reject")
async def reject_book(book_id: str, reason: str = "") -> JSONResponse:
    db = get_db()
    book = await db.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    await db.update_status(book_id, BookStatus.REJECTED)
    return JSONResponse({"status": "rejected", "book_id": book_id})


@app.post("/api/book/{book_id}/metadata")
async def update_metadata(book_id: str, request: Request) -> JSONResponse:
    db = get_db()
    book = await db.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    data = await request.json()
    if "title" in data:
        book.metadata.title = data["title"]
    if "subtitle" in data:
        book.metadata.subtitle = data["subtitle"]
    if "description" in data:
        book.metadata.description = data["description"]
    if "keywords" in data:
        book.metadata.keywords = data["keywords"]
    if "price_usd" in data:
        book.metadata.price_usd = float(data["price_usd"])
    await db.update_book(book)
    return JSONResponse({"status": "updated"})


@app.get("/preflight/{book_id}", response_class=HTMLResponse)
async def preflight(request: Request, book_id: str) -> HTMLResponse:
    db = get_db()
    book = await db.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    checks = _run_preflight(book)
    return templates.TemplateResponse(
        "preflight.html",
        {"request": request, "book": book, "checks": checks},
    )


def _run_preflight(book: KdpBook) -> list[dict[str, Any]]:
    checks = []

    # Title check
    checks.append({
        "name": "Title not empty",
        "pass": bool(book.metadata.title),
        "detail": book.metadata.title[:60] or "(empty)",
    })
    # Description check
    checks.append({
        "name": "Description (min 50 words)",
        "pass": len(book.metadata.description.split()) >= 50,
        "detail": f"{len(book.metadata.description.split())} words",
    })
    # Keywords check
    checks.append({
        "name": f"{7} keywords set",
        "pass": len(book.metadata.keywords) >= 7,
        "detail": f"{len(book.metadata.keywords)} keywords",
    })
    # Interior PDF
    pdf_path = Path(book.files.interior_pdf) if book.files.interior_pdf else None
    checks.append({
        "name": "Interior PDF exists",
        "pass": bool(pdf_path and pdf_path.exists()),
        "detail": str(pdf_path) if pdf_path else "(not generated)",
    })
    # Cover PDF
    cover_path = Path(book.files.cover_pdf) if book.files.cover_pdf else None
    checks.append({
        "name": "Cover PDF exists",
        "pass": bool(cover_path and cover_path.exists()),
        "detail": str(cover_path) if cover_path else "(not generated)",
    })
    # Pages count
    checks.append({
        "name": "40 pages generated",
        "pass": book.pages_generated >= 40,
        "detail": f"{book.pages_generated} pages",
    })

    return checks


@app.get("/health", response_class=HTMLResponse)
async def health_page(request: Request) -> HTMLResponse:
    cfg = get_config()
    services = await _check_services(cfg)
    return templates.TemplateResponse(
        "health.html",
        {"request": request, "services": services},
    )


@app.get("/api/health")
async def health_api() -> JSONResponse:
    cfg = get_config()
    services = await _check_services(cfg)
    all_ok = all(s["ok"] for s in services)
    return JSONResponse({"ok": all_ok, "services": services})


async def _check_services(cfg: Any) -> list[dict[str, Any]]:
    services = []

    async def _ping(name: str, url: str) -> dict[str, Any]:
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(url)
                ms = int((time.monotonic() - t0) * 1000)
                return {"name": name, "ok": r.status_code < 400, "ms": ms, "detail": f"HTTP {r.status_code}"}
        except Exception as exc:
            ms = int((time.monotonic() - t0) * 1000)
            return {"name": name, "ok": False, "ms": ms, "detail": str(exc)[:80]}

    surreal_http = cfg.surreal.url.replace("ws://", "http://").replace("wss://", "https://")

    import asyncio
    results = await asyncio.gather(
        _ping("Ollama", f"{cfg.metadata.ollama_base_url}/api/tags"),
        _ping("SurrealDB", f"{surreal_http}/health"),
    )
    return list(results)
