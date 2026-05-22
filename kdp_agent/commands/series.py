"""CLI commands for managing multi-volume KDP series."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()


@app.command("create")
def create_series(
    name: str = typer.Argument(..., help="Series name, e.g. Ghost Anime Galaxy."),
    style: str = typer.Option("anime", help="Series style: space | anime | mandala | other."),
    brand: str = typer.Option("", help="Optional anthology brand/group name."),
    author: str = typer.Option("KDP Agent", help="Author / studio name."),
) -> None:
    """Create a new canonical series record."""
    asyncio.run(_create_series(name=name, style=style, brand=brand, author=author))


async def _create_series(name: str, style: str, brand: str, author: str) -> None:
    from kdp_agent.agents.series.series_repo import SeriesRepository
    from kdp_agent.db import get_db

    db = get_db()
    await db.connect()
    try:
        series = await SeriesRepository(db).create_series(
            name=name,
            style=style,
            brand=brand,
            author=author,
        )
        console.print(f"[green]✓[/green] Series created: {series.name} ({series.id})")
    finally:
        await db.disconnect()


@app.command("list")
def list_series(
    brand: str = typer.Option("", help="Filter by anthology brand."),
    status: str = typer.Option("", help="Filter by status: active | completed | archived."),
) -> None:
    """List tracked series."""
    asyncio.run(_list_series(brand=brand, status=status))


async def _list_series(brand: str, status: str) -> None:
    from kdp_agent.agents.series.series_repo import SeriesRepository
    from kdp_agent.db import SeriesStatus, get_db

    db = get_db()
    await db.connect()
    try:
        parsed_status = SeriesStatus(status) if status else None
        rows = await SeriesRepository(db).list_series(brand=brand, status=parsed_status)

        table = Table(title="KDP Series")
        table.add_column("Name")
        table.add_column("Brand")
        table.add_column("Style")
        table.add_column("Status")
        table.add_column("Volumes", justify="right")
        table.add_column("DNA")
        for series in rows:
            table.add_row(
                series.name,
                series.brand or "-",
                series.style,
                series.status.value,
                str(series.volume_count),
                "frozen" if series.style_dna.is_frozen else "missing",
            )
        console.print(table)
    finally:
        await db.disconnect()


@app.command("show")
def show_series(name: str = typer.Argument(..., help="Series name or ID.")) -> None:
    """Show one series and its volumes."""
    asyncio.run(_show_series(name))


async def _show_series(name: str) -> None:
    from kdp_agent.agents.series.series_repo import SeriesRepository
    from kdp_agent.db import get_db

    db = get_db()
    await db.connect()
    try:
        repo = SeriesRepository(db)
        series = await repo.get_required(name)
        volumes = await repo.list_volumes(series)

        console.print(f"[bold cyan]{series.name}[/bold cyan] ({series.status.value})")
        console.print(f"Brand : {series.brand or '-'}")
        console.print(f"Author: {series.author}")
        console.print(f"Style : {series.style}")
        console.print(f"DNA   : {'frozen' if series.style_dna.is_frozen else 'missing'}")
        if series.style_dna.palette:
            console.print(f"Palette: {', '.join(series.style_dna.palette)}")
        if series.style_dna.character_descriptor:
            console.print(f"Descriptor: {series.style_dna.character_descriptor}")

        table = Table(title="Volumes")
        table.add_column("Vol", justify="right")
        table.add_column("Book ID")
        table.add_column("Theme")
        table.add_column("Status")
        for book in volumes:
            table.add_row(
                str(book.volume_number),
                book.id,
                book.theme,
                book.status.value,
            )
        console.print(table)
    finally:
        await db.disconnect()


@app.command("archive")
def archive_series(name: str = typer.Argument(..., help="Series name or ID.")) -> None:
    """Archive a series without deleting books."""
    asyncio.run(_archive_series(name))


async def _archive_series(name: str) -> None:
    from kdp_agent.agents.series.series_repo import SeriesRepository
    from kdp_agent.db import get_db

    db = get_db()
    await db.connect()
    try:
        series = await SeriesRepository(db).archive_series(name)
        console.print(f"[green]✓[/green] Archived series: {series.name}")
    finally:
        await db.disconnect()


@app.command("freeze-dna")
def freeze_dna(
    name: str = typer.Argument(..., help="Series name or ID."),
    from_book: str = typer.Option(..., "--from-book", help="Approved/live Vol.1 book ID."),
) -> None:
    """Freeze Style DNA from an approved/live book."""
    asyncio.run(_freeze_dna(name=name, from_book=from_book))


async def _freeze_dna(name: str, from_book: str) -> None:
    from kdp_agent.agents.series.series_repo import SeriesRepository
    from kdp_agent.agents.series.style_dna import capture_dna
    from kdp_agent.config import get_config
    from kdp_agent.db import get_db

    cfg = get_config()
    db = get_db()
    await db.connect()
    try:
        book = await db.get_book(from_book)
        if not book:
            console.print(f"[red]Book not found: {from_book}[/red]")
            raise typer.Exit(1)

        dna = capture_dna(book, cfg)
        series = await SeriesRepository(db).update_dna(name, dna)
        console.print(f"[green]✓[/green] Style DNA frozen for {series.name}")
        console.print(f"Descriptor: {dna.character_descriptor}")
        console.print(f"Palette: {', '.join(dna.palette) or '(none)'}")
        console.print(f"Refs: {len(dna.reference_image_paths)} images")
    finally:
        await db.disconnect()


@app.command("add-volume")
def add_volume(
    name: str = typer.Argument(..., help="Series name or ID."),
    theme: str = typer.Option(..., help="Volume theme."),
    sub_theme: str = typer.Option("", help="Optional sub-theme for dedup fingerprinting."),
    pages: int = typer.Option(40, help="Pages to generate."),
    volume: int | None = typer.Option(None, help="Explicit volume number."),
    force: bool = typer.Option(False, help="Allow duplicate theme fingerprint."),
    generate_now: bool = typer.Option(False, help="Generate pages immediately after creating the book."),
) -> None:
    """Create the next volume, optionally generating it immediately."""
    asyncio.run(
        _add_volume(
            name=name,
            theme=theme,
            sub_theme=sub_theme,
            pages=pages,
            volume=volume,
            force=force,
            generate_now=generate_now,
        )
    )


async def _add_volume(
    name: str,
    theme: str,
    sub_theme: str,
    pages: int,
    volume: int | None,
    force: bool,
    generate_now: bool,
) -> None:
    from kdp_agent.agents.series.dedup import check_theme_collision
    from kdp_agent.agents.series.series_repo import SeriesRepository
    from kdp_agent.db import KdpBook, RelationshipType, get_db

    db = get_db()
    await db.connect()
    try:
        repo = SeriesRepository(db)
        series = await repo.get_required(name)
        await repo.ensure_dna_ready(series)

        collision = check_theme_collision(series, theme, sub_theme)
        if collision and not force:
            console.print(
                "[yellow]Theme already used in this series.[/yellow] "
                f"Previous volume: {collision.volume_number}, book: {collision.book_id}. "
                "Use --force to allow."
            )
            raise typer.Exit(1)

        volume_number = volume or await repo.next_volume_number(series)
        book = KdpBook(
            niche=series.brand or series.name,
            theme=theme,
            style=series.style,
            series_id=series.id,
            volume_number=volume_number,
            relationship_type=RelationshipType.VOLUME,
        )
        await db.create_book(book)
        console.print(
            f"[green]✓[/green] Created Vol.{volume_number} book {book.id} "
            f"for series '{series.name}'"
        )

        if generate_now:
            from kdp_agent.commands.generate import _run

            await _run(
                book_id=book.id,
                theme=theme,
                style=series.style,
                pages=pages,
                output_dir=None,
                series_name=series.name,
                volume=volume_number,
                sub_theme=sub_theme,
                force=force,
            )
        else:
            await repo.commit_dedup_record(
                series=series,
                seeds=[],
                theme=theme,
                sub_theme=sub_theme,
                volume_number=volume_number,
                book_id=book.id,
                forced=force,
            )
    finally:
        await db.disconnect()
