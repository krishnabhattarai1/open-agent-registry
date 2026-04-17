"""oar validate — validate an agent-card.yaml locally (no API call)."""

from pathlib import Path

import typer
import yaml
from pydantic import ValidationError
from rich.console import Console

from oar.schemas.manifest import AgentManifest

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def validate(manifest_path: Path = typer.Argument(..., help="Path to agent-card.yaml")) -> None:
    """Validate an agent card manifest against the OAR schema."""
    if not manifest_path.exists():
        console.print(f"[red]File not found: {manifest_path}[/red]")
        raise typer.Exit(1)

    with open(manifest_path) as f:
        raw = yaml.safe_load(f)

    try:
        AgentManifest.model_validate(raw)
        console.print(f"[green]✓ {manifest_path} is valid[/green]")
    except ValidationError as e:
        console.print(f"[red]Validation errors in {manifest_path}:[/red]")
        for err in e.errors():
            loc = " → ".join(str(l) for l in err["loc"])
            console.print(f"  [yellow]{loc}[/yellow]: {err['msg']}")
        raise typer.Exit(1)
