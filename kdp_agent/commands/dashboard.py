"""CLI: start the review dashboard."""

from __future__ import annotations

import subprocess
import sys
import webbrowser
from pathlib import Path

import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def run(ctx: typer.Context) -> None:
    """Start the KDP Agent review dashboard at localhost:8090."""
    if ctx.invoked_subcommand is not None:
        return
    from kdp_agent.config import get_config

    cfg = get_config()
    host = cfg.dashboard.host
    port = cfg.dashboard.port
    url = f"http://{host}:{port}"

    typer.echo(f"Starting dashboard at {url}")
    if cfg.dashboard.auto_open_browser:
        import threading
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    import uvicorn
    uvicorn.run(
        "kdp_agent.dashboard.app:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )
