"""CLI: generate coloring book interior pages."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def generate(
    ctx: typer.Context,
    book_id: str | None = typer.Option(None, help="Book ID from SurrealDB."),
    theme: str = typer.Option(..., help="Content theme, e.g. 'galaxy astronaut'."),
    style: str = typer.Option("space", help="Art style: space | anime | mandala"),
    pages: int = typer.Option(None, help="Override pages count (default from config)."),
    output_dir: Path = typer.Option(None, help="Override output directory."),
    series_name: str = typer.Option("", "--series", help="Series name/ID for multi-volume generation."),
    volume: int | None = typer.Option(None, help="Series volume number (auto if omitted)."),
    sub_theme: str = typer.Option("", help="Optional sub-theme for series dedup."),
    force: bool = typer.Option(False, help="Allow duplicate theme within a series."),
) -> None:
    """Generate coloring book interior pages and assemble into a KDP-compliant PDF."""
    if ctx.invoked_subcommand is not None:
        return
    asyncio.run(
        _run(
            book_id=book_id,
            theme=theme,
            style=style,
            pages=pages,
            output_dir=output_dir,
            series_name=series_name,
            volume=volume,
            sub_theme=sub_theme,
            force=force,
        )
    )


@app.command("run")
def run_generate(
    book_id: str | None = typer.Option(None, help="Book ID from SurrealDB."),
    theme: str = typer.Option(..., help="Content theme, e.g. 'galaxy astronaut'."),
    style: str = typer.Option("space", help="Art style: space | anime | mandala"),
    pages: int = typer.Option(None, help="Override pages count (default from config)."),
    output_dir: Path = typer.Option(None, help="Override output directory."),
    series_name: str = typer.Option("", "--series", help="Series name/ID for multi-volume generation."),
    volume: int | None = typer.Option(None, help="Series volume number (auto if omitted)."),
    sub_theme: str = typer.Option("", help="Optional sub-theme for series dedup."),
    force: bool = typer.Option(False, help="Allow duplicate theme within a series."),
) -> None:
    """Explicit alias for docs/spec examples: `kdp-agent generate run ...`."""
    asyncio.run(
        _run(
            book_id=book_id,
            theme=theme,
            style=style,
            pages=pages,
            output_dir=output_dir,
            series_name=series_name,
            volume=volume,
            sub_theme=sub_theme,
            force=force,
        )
    )


async def _run(
    book_id: str | None,
    theme: str,
    style: str,
    pages: int | None,
    output_dir: Path | None,
    series_name: str = "",
    volume: int | None = None,
    sub_theme: str = "",
    force: bool = False,
) -> None:
    from kdp_agent.config import get_config
    from kdp_agent.db import get_db, BookStatus, KdpBook, RelationshipType
    from kdp_agent.agents.content.prompt_templates import build_prompt, build_negative_prompt
    from kdp_agent.agents.content.image_gen import ImageGenerator
    from kdp_agent.agents.content.postprocess import PostProcessor
    from kdp_agent.agents.content.pdf_builder import PdfBuilder
    from kdp_agent.agents.content.ip_check import IpChecker
    import random

    cfg = get_config()
    db = get_db()
    await db.connect()

    series = None
    repo = None
    prompt_record_force = False
    if series_name:
        from kdp_agent.agents.series.dedup import check_theme_collision, select_seeds
        from kdp_agent.agents.series.series_repo import SeriesRepository
        from kdp_agent.agents.series.style_dna import apply_dna

        repo = SeriesRepository(db)
        series = await repo.get_required(series_name)
        await repo.ensure_dna_ready(series)
        collision = check_theme_collision(series, theme, sub_theme)
        if collision and not force:
            if book_id and collision.book_id == book_id:
                collision = None
            else:
                console.print(
                    "[yellow]Theme already used in this series.[/yellow] "
                    f"Previous volume: {collision.volume_number}, book: {collision.book_id}. "
                    "Use --force to allow duplicate."
                )
                raise typer.Exit(1)
        if collision and force:
            console.print(
                "[yellow]Theme already used in this series; continuing due to --force.[/yellow]"
            )
        prompt_record_force = bool(collision and force)
        style = series.style

        if not book_id:
            volume_number = volume or await repo.next_volume_number(series)
            book = KdpBook(
                niche=series.brand or series.name,
                theme=theme,
                style=style,
                series_id=series.id,
                volume_number=volume_number,
                relationship_type=RelationshipType.VOLUME,
            )
            await db.create_book(book)
            book_id = book.id
            console.print(f"[cyan]Created series Vol.{volume_number} book: {book.id}[/cyan]")
        else:
            book = await db.get_book(book_id)
            if not book:
                console.print(f"[red]Book {book_id} not found.[/red]")
                raise typer.Exit(1)
            if not book.series_id:
                book.series_id = series.id
                book.relationship_type = RelationshipType.VOLUME
            if volume:
                book.volume_number = volume
    else:
        if not book_id:
            console.print("[red]--book-id is required unless --series is provided.[/red]")
            raise typer.Exit(1)
        book = await db.get_book(book_id)
        if not book:
            console.print(f"[red]Book {book_id} not found.[/red]")
            raise typer.Exit(1)

    n_pages = pages or cfg.generation.pages_per_book
    out_dir = output_dir or Path(f"output/{book_id}/pages")
    out_dir.mkdir(parents=True, exist_ok=True)

    gen = ImageGenerator(cfg)
    proc = PostProcessor(cfg)
    builder = PdfBuilder(cfg)
    ip = IpChecker(cfg)

    positive = build_prompt(theme=theme, style=style, config=cfg)
    if series:
        positive = apply_dna(positive, series.style_dna)
    negative = build_negative_prompt(cfg)
    if series and series.style_dna.negative_prompt:
        negative = f"{negative}, {series.style_dna.negative_prompt}"

    page_paths: list[Path] = []
    seeds: list[int] = []

    with console.status(f"[bold green]Generating {n_pages} pages...") as status:
        if series:
            seed_pool = select_seeds(series, n_pages)
        else:
            seed_pool = [random.randint(1, 999999) for _ in range(n_pages)]
        for i in range(n_pages):
            seed = seed_pool[i]
            seeds.append(seed)
            raw_path = out_dir / f"raw_{i+1:02d}.png"
            clean_path = out_dir / f"page_{i+1:02d}.png"

            status.update(f"[bold green]Page {i+1}/{n_pages}: generating...")
            attempt = 0
            while attempt < cfg.generation.max_gen_retries:
                await gen.generate(
                    prompt=positive,
                    output_path=raw_path,
                    negative_prompt=negative,
                    style=style,
                    seed=seed + attempt * 100,
                )
                status.update(f"[bold green]Page {i+1}/{n_pages}: post-processing...")
                proc.binarize(raw_path, clean_path)
                report = proc.check_quality(clean_path)
                if report.passed:
                    is_safe, sim = ip.check(clean_path)
                    if not is_safe:
                        console.print(f"  [yellow]Page {i+1}: IP similarity {sim:.2f} > threshold — regenerating[/yellow]")
                        attempt += 1
                        continue
                    break
                attempt += 1
                console.print(f"  [yellow]Page {i+1} attempt {attempt} failed: {report.details}[/yellow]")

            if not report.passed:
                console.print(f"  [red]Page {i+1} failed all quality checks — using best attempt[/red]")

            page_paths.append(clean_path)
            console.print(f"  [green]✓[/green] Page {i+1}")

    pdf_path = Path(f"output/{book_id}/interior.pdf")
    builder.build_interior(page_paths=page_paths, output_path=pdf_path)
    console.print(f"\n[green]✓[/green] Interior PDF → {pdf_path}")

    book.pages_generated = n_pages
    book.page_seeds = seeds
    book.files.interior_pdf = str(pdf_path)
    book.files.pages_dir = str(out_dir)
    book.status = BookStatus.DRAFT
    await db.update_book(book)
    if series and repo:
        await repo.commit_dedup_record(
            series=series,
            seeds=seeds,
            theme=theme,
            sub_theme=sub_theme,
            volume_number=book.volume_number,
            book_id=book.id,
            forced=prompt_record_force,
        )
    await db.disconnect()

    console.print(f"[bold green]Done![/bold green] Book updated in database.")
