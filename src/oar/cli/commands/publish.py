"""oar publish — idempotent create-or-update from an agent-card.yaml."""

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
def publish(manifest_path: Path = typer.Argument(..., help="Path to agent-card.yaml")) -> None:
    """Publish an agent: creates if new, updates if already exists."""
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

    slug = manifest.name.lower().replace(" ", "-")
    payload = {
        "name": manifest.name,
        "slug": slug,
        "description": manifest.description,
        "version": manifest.version,
        "status": manifest.status,
        "homepage_url": manifest.homepage,
        "repository_url": manifest.repository,
        "license": manifest.license,
        "tags": manifest.tags,
        "capabilities": [
            {"code": c.code, "input_types": c.input_types, "output_types": c.output_types}
            for c in manifest.capabilities
        ],
        "endpoints": [
            {"protocol": e.protocol, "url": e.url,
             "auth_type": e.auth.type if e.auth else None,
             "auth_config": e.auth.config if e.auth else None}
            for e in manifest.endpoints
        ],
    }

    with get_client() as client:
        # Try create first
        resp = client.post("/v1/agents", json=payload)
        if resp.status_code == 201:
            console.print(f"[green]✓ Created:[/green] {manifest.publisher}/{slug}")
            return
        elif resp.status_code == 409:
            # Already exists — update
            update_payload = {k: v for k, v in payload.items() if k != "slug"}
            resp = client.patch(f"/v1/agents/{manifest.publisher}/{slug}", json=update_payload)
            if resp.status_code == 200:
                console.print(f"[green]✓ Updated:[/green] {manifest.publisher}/{slug} → v{manifest.version}")
            else:
                console.print(f"[red]Update failed {resp.status_code}:[/red] {resp.text}")
                raise typer.Exit(1)
        else:
            console.print(f"[red]Error {resp.status_code}:[/red] {resp.text}")
            raise typer.Exit(1)
