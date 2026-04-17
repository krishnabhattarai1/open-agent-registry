"""oar config — manage registry URL and API key."""

import typer
from rich.console import Console
from rich.table import Table

from oar.cli.client import CONFIG_PATH, load_config, save_config

app = typer.Typer(help="Configure the OAR CLI.")
console = Console()


@app.command("set")
def config_set(key: str, value: str) -> None:
    """Set a config value (registry-url or api-key)."""
    key = key.replace("-", "_")
    save_config(key, value)
    console.print(f"[green]Set {key}[/green]")


@app.command("show")
def config_show() -> None:
    """Show current configuration."""
    cfg = load_config()
    t = Table(title=f"Config ({CONFIG_PATH})")
    t.add_column("Key")
    t.add_column("Value")
    for k, v in cfg.items():
        display_val = v[:8] + "..." if k == "api_key" and len(v) > 8 else v
        t.add_row(k, display_val)
    console.print(t)
