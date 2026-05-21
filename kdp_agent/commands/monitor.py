"""CLI: BSR monitoring stub."""
import typer
app = typer.Typer()

@app.callback(invoke_without_command=True)
def run(ctx: typer.Context) -> None:
    """Monitor live books BSR and approval status (Phase 7 — coming soon)."""
    if ctx.invoked_subcommand is not None:
        return
    typer.echo("Monitor agent — Phase 7 (not yet implemented).")
