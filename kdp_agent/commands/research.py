"""CLI: niche keyword research stub."""
import typer
app = typer.Typer()

@app.callback(invoke_without_command=True)
def run(ctx: typer.Context) -> None:
    """Run niche keyword research (Phase 6 — coming soon)."""
    if ctx.invoked_subcommand is not None:
        return
    typer.echo("Niche research agent — Phase 6 (not yet implemented). Use kdp-scout CLI for now.")
