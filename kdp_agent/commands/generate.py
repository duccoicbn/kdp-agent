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
    book_id: str = typer.Option(..., help="Book ID from SurrealDB."),
    theme: str = typer.Option(..., help="Content theme, e.g. 'galaxy astronaut'."),
    style: str = typer.Option("space", help="Art style: space | anime | mandala"),
    pages: int = typer.Option(None, help="Override pages count (default from config)."),
    output_dir: Path = typer.Option(None, help="Override output directory."),
) -> None:
    """Generate coloring book interior pages and assemble into a KDP-compliant PDF."""
    if ctx.invoked_subcommand is not None:
        return
    asyncio.run(_run(book_id=book_id, theme=theme, style=style, pages=pages, output_dir=output_dir))


async def _run(
    book_id: str,
    theme: str,
    style: str,
    pages: int | None,
    output_dir: Path | None,
) -> None:
    from kdp_agent.config import get_config
    from kdp_agent.db import get_db, BookStatus
    from kdp_agent.agents.content.prompt_templates import build_prompt, build_negative_prompt
    from kdp_agent.agents.content.image_gen import ImageGenerator
    from kdp_agent.agents.content.postprocess import PostProcessor
    from kdp_agent.agents.content.pdf_builder import PdfBuilder
    from kdp_agent.agents.content.ip_check import IpChecker
    import random

    cfg = get_config()
    db = get_db()
    await db.connect()

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
    negative = build_negative_prompt(cfg)

    page_paths: list[Path] = []
    seeds: list[int] = []

    with console.status(f"[bold green]Generating {n_pages} pages...") as status:
        for i in range(n_pages):
            seed = random.randint(1, 999999)
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
    await db.disconnect()

    console.print(f"[bold green]Done![/bold green] Book updated in database.")
