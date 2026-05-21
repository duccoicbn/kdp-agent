"""CLI: upload approved book to KDP via Playwright (human submits)."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def run(
    ctx: typer.Context,
    book_id: str = typer.Option(..., help="Book ID to publish (must be in 'approved' status)."),
) -> None:
    """Upload approved book to KDP. Human must click 'Submit for Review' at the end."""
    if ctx.invoked_subcommand is not None:
        return
    asyncio.run(_run(book_id))


async def _run(book_id: str) -> None:
    from kdp_agent.config import get_config
    from kdp_agent.db import get_db, BookStatus
    from kdp_agent.agents.publisher.session import KdpSession

    cfg = get_config()
    db = get_db()
    await db.connect()

    book = await db.get_book(book_id)
    if not book:
        console.print(f"[red]Book {book_id} not found.[/red]")
        raise typer.Exit(1)

    if book.status != BookStatus.APPROVED:
        console.print(f"[red]Book must be 'approved' before publishing. Current: {book.status.value}[/red]")
        raise typer.Exit(1)

    console.print("[bold]KDP Publisher Agent[/bold]")
    console.print(
        "\n[yellow]Instructions:[/yellow]\n"
        "1. Open Chrome with remote debugging:\n"
        "   [cyan]chrome.exe --remote-debugging-port=9222[/cyan]\n"
        "2. Log in to KDP at [cyan]https://kdp.amazon.com[/cyan]\n"
        "3. Press Enter here when ready.\n"
    )
    input()

    session = KdpSession(cfg)
    try:
        await session.connect()
        await session.fill_and_upload(book)
        await db.update_status(book_id, BookStatus.PUBLISHING)
        console.print(
            "\n[bold green]Form filled! The browser is paused before 'Submit for Review'.[/bold green]\n"
            "[yellow]Please review the KDP page and click Submit yourself.[/yellow]"
        )
    finally:
        await session.disconnect()

    await db.disconnect()
