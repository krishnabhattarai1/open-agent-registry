"""oar register — register a new agent from an agent-card.yaml."""

from pathlib import Path

import typer
import yaml
from pydantic import ValidationError
from rich.console import Console

from oar.cli.client import get_client
from oar.schemas.manifest import AgentManifest

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def register(manifest_path: Path = typer.Argument(..., help="Path to agent-card.yaml")) -> None:
    """Register a new agent. Validates locally before submitting."""
    if not manifest_path.exists():
        console.print(f"[red]File not found: {manifest_path}[/red]")
        raise typer.Exit(1)

    with open(manifest_path) as f:
        raw = yaml.safe_load(f)

    try:
        manifest = AgentManifest.model_validate(raw)
    except ValidationError as e:
        console.print("[red]Manifest validation failed:[/red]")
        for err in e.errors():
            loc = " → ".join(str(l) for l in err["loc"])
            console.print(f"  [yellow]{loc}[/yellow]: {err['msg']}")
        raise typer.Exit(1)

    payload = {
        "name": manifest.name,
        "slug": manifest.name.lower().replace(" ", "-"),
        "description": manifest.description,
        "version": manifest.version,
        "status": manifest.status,
        "homepage_url": manifest.homepage,
        "repository_url": manifest.repository,
        "license": manifest.license,
        "tags": manifest.tags,
        "capabilities": [
            {
                "code": c.code,
                "input_types": c.input_types,
                "output_types": c.output_types,
            }
            for c in manifest.capabilities
        ],
        "endpoints": [
            {
                "protocol": e.protocol,
                "url": e.url,
                "auth_type": e.auth.type if e.auth else None,
                "auth_config": e.auth.config if e.auth else None,
            }
            for e in manifest.endpoints
        ],
    }

    with get_client() as client:
        resp = client.post("/v1/agents", json=payload)

    if resp.status_code == 201:
        data = resp.json()
        console.print(f"[green]✓ Registered:[/green] {manifest.publisher}/{data.get('slug', manifest.name)}")
        console.print(f"  short_id: [bold]{data.get('short_id')}[/bold]")
    elif resp.status_code == 409:
        console.print("[yellow]Agent already exists. Use `oar publish` to update.[/yellow]")
        raise typer.Exit(1)
    else:
        console.print(f"[red]Error {resp.status_code}:[/red] {resp.text}")
        raise typer.Exit(1)
