"""oar taxonomy — show available capability codes."""

import typer
from rich.console import Console
from rich.table import Table

from oar.taxonomy import TAXONOMY

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def taxonomy(
    domain: str | None = typer.Argument(None, help="Filter by domain e.g. code"),
) -> None:
    """Show built-in capability taxonomy codes."""
    domains = {domain: TAXONOMY[domain]} if domain and domain in TAXONOMY else TAXONOMY

    if domain and domain not in TAXONOMY:
        console.print(f"[red]Unknown domain: {domain}[/red]")
        console.print(f"Available: {', '.join(TAXONOMY.keys())}")
        raise typer.Exit(1)

    t = Table(title="OAR Capability Taxonomy")
    t.add_column("Domain", style="bold cyan")
    t.add_column("Codes")

    for dom, actions in domains.items():
        codes = ", ".join(f"{dom}.{a}" for a in actions)
        t.add_row(dom, codes)

    console.print(t)
    console.print(f"\n[dim]Usage: code.review, data.transform, text.summarize ...[/dim]")
