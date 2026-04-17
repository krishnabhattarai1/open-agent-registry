"""oar info — get details about an agent."""

import json

import typer
from rich.console import Console
from rich.panel import Panel

from oar.cli.client import get_client

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def info(
    agent_ref: str = typer.Argument(..., help="publisher/slug or short_id"),
    fields: str | None = typer.Option(None, "--fields", "-f", help="Comma-separated field groups: ep,auth,caps"),
    version: str | None = typer.Option(None, "--version", "-v"),
    output_json: bool = typer.Option(False, "--json"),
) -> None:
    """Get agent details. Use --fields ep,auth for connection info only."""
    with get_client() as client:
        if "/" in agent_ref:
            # publisher/slug format — verbose
            url = f"/v1/agents/{agent_ref}"
            resp = client.get(url, headers={"Accept": "application/json"})
        else:
            # short_id format — compact or field-selected
            params = {}
            if fields:
                params["fields"] = fields
            resp = client.get(f"/v1/agents/{agent_ref}", params=params)

    if resp.status_code == 404:
        console.print(f"[red]Agent not found: {agent_ref}[/red]")
        raise typer.Exit(1)
    elif resp.status_code != 200:
        console.print(f"[red]Error {resp.status_code}:[/red] {resp.text}")
        raise typer.Exit(1)

    data = resp.json()

    if output_json:
        console.print_json(json.dumps(data))
        return

    if fields or "/" not in agent_ref:
        # Compact display
        console.print_json(json.dumps(data))
        return

    # Full verbose display
    name = data.get("name", "")
    pub = data.get("publisher", {}).get("slug", "")
    ver = data.get("version", "")
    desc = data.get("description", "")
    caps = [c["code"] for c in data.get("capabilities", [])]
    eps = data.get("endpoints", [])

    console.print(Panel(
        f"[bold]{name}[/bold] v{ver}\n"
        f"[dim]{pub}[/dim]\n\n"
        f"{desc}\n\n"
        f"[bold]Capabilities:[/bold] {', '.join(caps)}\n"
        f"[bold]Endpoints:[/bold] {len(eps)}\n" +
        "\n".join(f"  • {e['protocol']}: {e['url']}" for e in eps),
        title=f"{pub}/{data.get('slug', '')}",
    ))
