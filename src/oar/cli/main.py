"""OAR CLI entry point — `oar` command."""

import typer

from oar.cli.commands import (
    config_cmd,
    info,
    list_agents,
    match_cmd,
    publish,
    register,
    search,
    taxonomy_cmd,
    validate,
)

app = typer.Typer(
    name="oar",
    help="Open Agent Registry — token-efficient agent discovery CLI",
    no_args_is_help=True,
)

app.add_typer(config_cmd.app, name="config")
app.add_typer(register.app, name="register")
app.add_typer(publish.app, name="publish")
app.add_typer(search.app, name="search")
app.add_typer(match_cmd.app, name="match")
app.add_typer(info.app, name="info")
app.add_typer(list_agents.app, name="list")
app.add_typer(validate.app, name="validate")
app.add_typer(taxonomy_cmd.app, name="taxonomy")


if __name__ == "__main__":
    app()
