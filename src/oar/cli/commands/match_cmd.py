"""oar match — structured capability query (compact, agent-optimized output)."""

import json

import typer
from rich.console import Console
from rich.table import Table

from oar.cli.client import get_client

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def match(
    need: list[str] = typer.Option(..., "--need", "-n", help="Required capability codes"),
    want: list[str] = typer.Option([], "--want", "-w", help="Preferred capability codes"),
    proto: str | None = typer.Option(None, "--proto", "-p", help="Required protocol"),
    auth: list[str] = typer.Option([], "--auth", "-a", help="Acceptable auth types"),
    limit: int = typer.Option(5, "--limit", "-l"),
    min_score: int = typer.Option(0, "--min-score"),
    raw: bool = typer.Option(False, "--json", help="Output raw compact JSON"),
) -> None:
    """Find agents matching required capabilities. Returns compact scored results."""
    payload: dict = {"need": need, "limit": limit, "min_score": min_score}
    if want:
        payload["want"] = want
    if proto:
        payload["proto"] = proto
    if auth:
        payload["auth"] = auth

    with get_client() as client:
        resp = client.post("/v1/match", json=payload)

    if resp.status_code != 200:
        console.print(f"[red]Error {resp.status_code}:[/red] {resp.text}")
        raise typer.Exit(1)

    data = resp.json()

    if raw:
        console.print_json(json.dumps(data))
        return

    results = data.get("r", [])
    total = data.get("t", 0)
    ttl = data.get("ttl", 0)

    if not results:
        console.print("[yellow]No agents found matching your query.[/yellow]")
        return

    t = Table(title=f"Match results ({total} found, cached {ttl}s)")
    t.add_column("ID", style="bold cyan")
    t.add_column("Name")
    t.add_column("Capabilities")
    t.add_column("Protocol")
    t.add_column("Score", justify="right")

    for r in results:
        t.add_row(r["id"], r["n"], ", ".join(r["c"]), r["p"], str(r["s"]))

    console.print(t)
    console.print(f"\n[dim]Stage 2: oar info <id> --fields ep,auth[/dim]")
