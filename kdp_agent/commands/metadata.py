"""CLI: generate and validate book metadata."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def metadata_cmd(
    ctx: typer.Context,
    book_id: str = typer.Option(..., help="Book ID from SurrealDB."),
    niche: str = typer.Option(..., help="Niche, e.g. 'space coloring'."),
    theme: str = typer.Option(..., help="Theme, e.g. 'astronaut with planets'."),
    style: str = typer.Option("space", help="Art style: space | anime | mandala"),
) -> None:
    """Generate metadata (title, description, keywords) for a book via Ollama."""
    if ctx.invoked_subcommand is not None:
        return
    asyncio.run(_run(book_id=book_id, niche=niche, theme=theme, style=style))


async def _run(book_id: str, niche: str, theme: str, style: str) -> None:
    from kdp_agent.config import get_config
    from kdp_agent.db import get_db
    from kdp_agent.agents.metadata.metadata_gen import MetadataGenerator
    from kdp_agent.agents.metadata.validator import MetadataValidator

    cfg = get_config()
    db = get_db()
    await db.connect()

    book = await db.get_book(book_id)
    if not book:
        console.print(f"[red]Book {book_id} not found.[/red]")
        raise typer.Exit(1)

    gen = MetadataGenerator(cfg)
    validator = MetadataValidator(cfg)

    with console.status("[bold green]Generating metadata via Ollama..."):
        meta = await gen.generate(niche=niche, theme=theme, style=style)

    result = validator.validate(meta)

    table = Table(title="Generated Metadata")
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Title", meta.title)
    table.add_row("Subtitle", meta.subtitle)
    table.add_row("Description", meta.description[:200] + "..." if len(meta.description) > 200 else meta.description)
    table.add_row("Keywords", "\n".join(meta.keywords))
    table.add_row("Categories", "\n".join(meta.categories))
    table.add_row("Price", f"${meta.price_usd:.2f}")
    console.print(table)

    if result.errors:
        console.print("\n[red]Validation errors:[/red]")
        for e in result.errors:
            console.print(f"  [red]✗[/red] {e}")
        raise typer.Exit(1)

    if result.warnings:
        console.print("\n[yellow]Warnings:[/yellow]")
        for w in result.warnings:
            console.print(f"  [yellow]⚠[/yellow] {w}")

    book.metadata = meta
    await db.update_book(book)
    await db.disconnect()
    console.print("\n[bold green]✓ Metadata saved to book record.[/bold green]")
