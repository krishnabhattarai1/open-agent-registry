"""oar search — text search (human-friendly output)."""

import typer
from rich.console import Console
from rich.table import Table

from oar.cli.client import get_client

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def search(
    query: str | None = typer.Argument(None, help="Text search query"),
    cap: str | None = typer.Option(None, "--cap", "-c", help="Capability code filter"),
    proto: str | None = typer.Option(None, "--proto", "-p"),
    tag: str | None = typer.Option(None, "--tag", "-t"),
    publisher: str | None = typer.Option(None, "--publisher"),
    page: int = typer.Option(1, "--page"),
) -> None:
    """Search agents by text, capability, tag, or protocol."""
    params: dict = {"page": page}
    if query:
        params["q"] = query
    if proto:
        params["protocol"] = proto
    if tag:
        params["tag"] = tag
    if publisher:
        params["publisher"] = publisher

    with get_client() as client:
        resp = client.get("/v1/agents", params=params, headers={"Accept": "application/json"})

    if resp.status_code != 200:
        console.print(f"[red]Error {resp.status_code}:[/red] {resp.text}")
        raise typer.Exit(1)

    data = resp.json()
    agents = data.get("data", [])
    meta = data.get("meta", {})

    if not agents:
        console.print("[yellow]No agents found.[/yellow]")
        return

    t = Table(title=f"Agents ({meta.get('total', len(agents))} total)")
    t.add_column("Publisher/Slug", style="bold cyan")
    t.add_column("Name")
    t.add_column("Version")
    t.add_column("Capabilities")
    t.add_column("Description")

    for a in agents:
        slug = f"{a['publisher']['slug']}/{a['slug']}"
        caps = ", ".join(c["code"] for c in a.get("capabilities", []))
        desc = a["description"][:60] + "..." if len(a["description"]) > 60 else a["description"]
        t.add_row(slug, a["name"], a["version"], caps, desc)

    console.print(t)
