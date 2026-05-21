"""Setup wizard: health checks + demo book generation."""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Optional

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer()
console = Console()

_ROOT = Path(__file__).parent.parent.parent


async def _check_ollama(base_url: str) -> tuple[bool, str]:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{base_url}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
            return True, f"OK — {len(models)} model(s) loaded"
    except Exception as exc:
        return False, str(exc)


async def _check_replicate() -> tuple[bool, str]:
    key = os.environ.get("REPLICATE_API_TOKEN", "")
    if not key:
        return False, "REPLICATE_API_TOKEN not set in environment"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                "https://api.replicate.com/v1/models",
                headers={"Authorization": f"Token {key}"},
            )
            if r.status_code == 200:
                return True, "OK — API key valid"
            return False, f"HTTP {r.status_code}"
    except Exception as exc:
        return False, str(exc)


async def _check_surreal(url: str) -> tuple[bool, str]:
    ws_url = url.replace("ws://", "http://").replace("wss://", "https://")
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{ws_url}/health")
            if r.status_code == 200:
                return True, "OK — SurrealDB is running"
            return False, f"HTTP {r.status_code}"
    except Exception as exc:
        return False, str(exc)


async def _run_health_checks() -> bool:
    from kdp_agent.config import get_config
    cfg = get_config()

    table = Table(title="API Health Check", show_header=True)
    table.add_column("Service", style="bold")
    table.add_column("Status")
    table.add_column("Detail")

    all_ok = True

    checks = [
        ("Ollama (LLM)", _check_ollama(cfg.metadata.ollama_base_url)),
        ("Replicate API", _check_replicate()),
        ("SurrealDB", _check_surreal(cfg.surreal.url)),
    ]

    results = await asyncio.gather(*[c[1] for c in checks], return_exceptions=True)
    for (name, _), result in zip(checks, results):
        if isinstance(result, Exception):
            ok, detail = False, str(result)
        else:
            ok, detail = result
        status = "[green]✓ OK[/green]" if ok else "[red]✗ FAIL[/red]"
        table.add_row(name, status, detail)
        if not ok:
            all_ok = False

    console.print(table)
    return all_ok


@app.callback(invoke_without_command=True)
def run(ctx: typer.Context) -> None:
    """Run setup wizard: verify configuration and API connectivity."""
    if ctx.invoked_subcommand is not None:
        return
    asyncio.run(_async_setup())


async def _async_setup() -> None:
    console.print(Panel("[bold cyan]KDP Agent — Setup Wizard[/bold cyan]", expand=False))

    # Ensure config exists
    config_path = _ROOT / "kdp-config.yaml"
    if not config_path.exists():
        console.print("[yellow]kdp-config.yaml not found — creating from template...[/yellow]")
        import shutil
        template = Path(__file__).parent.parent.parent / "kdp-config.yaml"
        if template.exists():
            shutil.copy(template, config_path)
        else:
            console.print("[red]Template not found. Please create kdp-config.yaml manually.[/red]")
            raise typer.Exit(1)

    console.print(f"[dim]Config: {config_path}[/dim]\n")
    all_ok = await _run_health_checks()

    if all_ok:
        console.print("\n[bold green]✓ All systems operational! Ready to generate books.[/bold green]")
        console.print("  Run [cyan]python -m kdp_agent demo[/cyan] to generate a sample book.\n")
    else:
        console.print(
            "\n[yellow]Some services are not reachable. Check the issues above.[/yellow]"
        )
        console.print("  Image generation requires Replicate API token in environment:")
        console.print("  [cyan]set REPLICATE_API_TOKEN=your_token_here[/cyan]\n")


async def run_demo(niche: str, pages: int, style: str) -> None:
    """Generate a demo book without uploading to KDP."""
    from kdp_agent.config import get_config
    from kdp_agent.agents.content.prompt_templates import build_prompt
    from kdp_agent.agents.content.image_gen import ImageGenerator
    from kdp_agent.agents.content.pdf_builder import PdfBuilder

    cfg = get_config()
    output_dir = _ROOT / "output" / "demo"
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(Panel(
        f"[bold]Demo Book Generation[/bold]\n"
        f"Niche: [cyan]{niche}[/cyan]  Style: [cyan]{style}[/cyan]  Pages: [cyan]{pages}[/cyan]",
        expand=False,
    ))

    gen = ImageGenerator(cfg)
    builder = PdfBuilder(cfg)
    page_paths: list[Path] = []

    with console.status("[bold green]Generating pages...") as status:
        for i in range(pages):
            status.update(f"[bold green]Generating page {i+1}/{pages}...")
            prompt = build_prompt(theme=niche, style=style, config=cfg)
            img_path = output_dir / f"page_{i+1:02d}.png"
            await gen.generate(prompt=prompt, output_path=img_path, seed=1000 + i)
            page_paths.append(img_path)
            console.print(f"  [green]✓[/green] Page {i+1} → {img_path.name}")

    pdf_path = output_dir / "demo_interior.pdf"
    console.print("\n[bold]Assembling PDF...[/bold]")
    builder.build_interior(page_paths=page_paths, output_path=pdf_path)
    console.print(f"  [green]✓[/green] PDF → {pdf_path}")

    console.print(f"\n[bold green]Demo complete![/bold green] Output: {output_dir}")
    console.print("  Open the PDF to preview the coloring pages.")
