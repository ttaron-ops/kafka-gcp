#!/usr/bin/env python3
import os
import sys
from typing import Optional

import typer
from rich.console import Console

from kafka_cli.commands import (
    addons,
    health,
    profiles,
    start,
    terraform,
)
from kafka_cli.utils.config import init_config_dir
from kafka_cli.utils.interactive import is_interactive

# Initialize the Typer app
app = typer.Typer(
    name="kafka-cli",
    help="Interactive CLI tool for provisioning and managing Kafka clusters on GCP",
    add_completion=False,
)

console = Console()

# Register the commands
app.add_typer(start.app, name="start")
app.add_typer(profiles.app, name="profiles")
app.add_typer(health.app, name="health")
app.add_typer(addons.app, name="addons")
app.add_typer(terraform.app, name="terraform")


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    config_dir: Optional[str] = typer.Option(None, "--config-dir", help="Custom configuration directory"),
):
    """
    Main entry point for the Kafka CLI
    """
    # Set up custom config directory if specified
    if config_dir:
        os.environ["KAFKA_CLI_CONFIG_DIR"] = config_dir

    # Initialize the configuration directory
    init_config_dir()


@app.command("version")
def version():
    """Show the current version of the CLI tool"""
    from importlib.metadata import version as get_version

    try:
        ver = get_version("kafka-cli")
        console.print(f"Kafka CLI version: {ver}")
    except Exception as e:
        console.print("Kafka CLI version: 0.1.0")
        console.print(f"Error: {e}")


if __name__ == "__main__":
    # Handle questionary/prompt_toolkit in non-interactive environments
    if not is_interactive() and any(cmd in sys.argv for cmd in ["start"]):
        console.print("[bold red]Error:[/bold red] This command requires an interactive terminal.")
        console.print("Please run this command in a terminal where you can provide input.")
        console.print("\nFor automation purposes, consider using command-line options instead of the interactive wizard.")
        sys.exit(1)

    app()
