"""CLI: generate promotional images and video (Phase 10 — coming soon)."""
import typer
app = typer.Typer()

@app.callback(invoke_without_command=True)
def run(ctx: typer.Context) -> None:
    """Generate promotional images and video for a book (Phase 10)."""
    if ctx.invoked_subcommand is not None:
        return
    typer.echo("Marketing agent — Phase 10 (not yet implemented).")
