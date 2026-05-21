"""CLI command: generate KDP cover for an approved book."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer()
console = Console()


@app.command("generate")
def generate_cover(
    book_id: str = typer.Argument(..., help="Book ID from SurrealDB"),
    pages: int = typer.Option(50, help="Total interior page count (used for spine calc)"),
    style: str = typer.Option("", help="Override art style: space | anime | space_light | anime_minimal"),
    author: str = typer.Option("", help="Override author name (default from config)"),
    output_dir: Path = typer.Option(Path("output/covers"), help="Directory for cover outputs"),
) -> None:
    """Generate a full KDP cover (central art + composite + PDF) for a book."""
    asyncio.run(_run(book_id, pages, style, author, output_dir))


async def _run(
    book_id: str,
    pages: int,
    style_override: str,
    author_override: str,
    output_dir: Path,
) -> None:
    from kdp_agent.config import get_config
    from kdp_agent.db import KdpDb
    from kdp_agent.agents.cover.cover_gen import generate_cover
    from kdp_agent.agents.cover.cover_pdf import build_cover_pdf

    cfg = get_config()
    db = KdpDb(cfg)

    console.print(Panel(f"[bold cyan]Cover Generator[/bold cyan] — Book: {book_id}"))

    await db.connect()
    try:
        book = await db.get_book(book_id)
        if not book:
            console.print(f"[red]Book {book_id} not found.[/red]")
            raise typer.Exit(1)

        title = book.metadata.title if book.metadata else book_id
        niche = book.niche or "coloring book"
        style = style_override or book.style or "space"
        author = author_override or getattr(cfg, "default_author", "KDP Agent")
        page_count = pages or book.page_count or 50

        console.print(f"  Title  : [yellow]{title}[/yellow]")
        console.print(f"  Style  : [yellow]{style}[/yellow]")
        console.print(f"  Pages  : [yellow]{page_count}[/yellow]")
        console.print(f"  Author : [yellow]{author}[/yellow]")
        console.print()

        output_dir.mkdir(parents=True, exist_ok=True)

        console.print("[cyan]→ Generating central art via Replicate...[/cyan]")
        paths = await generate_cover(
            book_id=book_id,
            title=title,
            author=author,
            niche=niche,
            style=style,
            pages=page_count,
            config=cfg,
            output_dir=output_dir,
        )
        console.print(f"  ✓ Cover PNG : {paths['cover']}")

        console.print("[cyan]→ Building KDP cover PDF...[/cyan]")
        pdf_path = output_dir / f"{book_id}_cover.pdf"
        build_cover_pdf(
            cover_png=paths["cover"],
            pages=page_count,
            config=cfg,
            out_path=pdf_path,
        )
        console.print(f"  ✓ Cover PDF : {pdf_path}")

        await db.update_book(book_id, {"cover_path": str(pdf_path), "status": "cover_ready"})
        console.print("\n[bold green]✓ Cover generation complete![/bold green]")

    finally:
        await db.close()
