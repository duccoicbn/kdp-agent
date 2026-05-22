"""KDP Agent CLI entry point."""

import typer

app = typer.Typer(
    name="kdp-agent",
    help="Semi-auto AI system for Amazon KDP coloring book publishing.",
    add_completion=False,
)


def _load_commands() -> None:
    from kdp_agent.commands import (
        cover,
        dashboard,
        generate,
        marketing,
        metadata,
        monitor,
        publish,
        research,
        series,
        setup,
    )

    app.add_typer(setup.app, name="setup", help="First-run setup wizard & health checks.")
    app.add_typer(generate.app, name="generate", help="Generate coloring book interior pages.")
    app.add_typer(cover.app, name="cover", help="Generate KDP cover (art + PDF).")
    app.add_typer(metadata.app, name="metadata", help="Generate book metadata via Ollama.")
    app.add_typer(dashboard.app, name="dashboard", help="Start the review dashboard.")
    app.add_typer(publish.app, name="publish", help="Upload approved book to KDP via Playwright.")
    app.add_typer(research.app, name="research", help="Run niche keyword research.")
    app.add_typer(series.app, name="series", help="Manage multi-volume book series.")
    app.add_typer(monitor.app, name="monitor", help="Monitor live books BSR and approval status.")
    app.add_typer(marketing.app, name="marketing", help="Generate promotional images and video.")


@app.command("demo")
def demo(
    niche: str = typer.Option("geometric mandala", help="Niche theme for demo book."),
    pages: int = typer.Option(5, help="Number of pages to generate."),
    style: str = typer.Option("space", help="Art style: space | anime"),
) -> None:
    """Generate a demo book (no KDP upload) to verify the pipeline."""
    import asyncio
    from kdp_agent.commands.setup import run_demo

    asyncio.run(run_demo(niche=niche, pages=pages, style=style))


_load_commands()


if __name__ == "__main__":
    app()
