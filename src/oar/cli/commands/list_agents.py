"""oar list — list agents with filters."""

import typer
from rich.console import Console
from rich.table import Table

from oar.cli.client import get_client

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def list_agents(
    publisher: str | None = typer.Option(None, "--publisher"),
    status: str = typer.Option("active", "--status"),
    protocol: str | None = typer.Option(None, "--proto"),
    tag: str | None = typer.Option(None, "--tag"),
    page: int = typer.Option(1, "--page"),
    per_page: int = typer.Option(20, "--per-page"),
) -> None:
    """List registered agents with optional filters."""
    params: dict = {"status": status, "page": page, "per_page": per_page}
    if publisher:
        params["publisher"] = publisher
    if protocol:
        params["protocol"] = protocol
    if tag:
        params["tag"] = tag

    with get_client() as client:
        resp = client.get("/v1/agents", params=params, headers={"Accept": "application/json"})

    if resp.status_code != 200:
        console.print(f"[red]Error {resp.status_code}:[/red] {resp.text}")
        raise typer.Exit(1)

    data = resp.json()
    agents = data.get("data", [])
    meta = data.get("meta", {})

    t = Table(title=f"Agents (page {page}, {meta.get('total', 0)} total)")
    t.add_column("short_id", style="dim")
    t.add_column("Publisher/Slug", style="bold cyan")
    t.add_column("Version")
    t.add_column("Status")
    t.add_column("Protocols")

    for a in agents:
        slug = f"{a['publisher']['slug']}/{a['slug']}"
        protos = ", ".join({e["protocol"] for e in a.get("endpoints", [])})
        t.add_row(a["short_id"], slug, a["version"], a["status"], protos)

    console.print(t)
