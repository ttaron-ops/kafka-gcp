"""
Add-on management commands implementation using the Command pattern.
"""
from typing import Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.table import Table

from kafka_cli.core.commands.base import CommandFactory, CommandResult, ProfileAwareCommand
from kafka_cli.core.errors import ErrorHandler
from kafka_cli.core.interactive import Prompt

console = Console()


class AddonConfiguration:
    """Helper class for add-on configuration management"""

    # Available add-ons with their properties
    AVAILABLE_ADDONS = {
        "schema-registry": {
            "name": "Schema Registry",
            "description": "Confluent Schema Registry for schema management",
            "default_port": 8081,
            "machine_type": "e2-small",
            "disk_size_gb": 10,
        },
        "kafka-connect": {
            "name": "Kafka Connect",
            "description": "Distributed Kafka Connect for integrations",
            "default_port": 8083,
            "machine_type": "e2-medium",
            "disk_size_gb": 20,
        },
        "ksqldb": {
            "name": "ksqlDB",
            "description": "Stream processing SQL engine for Kafka",
            "default_port": 8088,
            "machine_type": "e2-medium",
            "disk_size_gb": 20,
        },
        "kafka-ui": {
            "name": "Kafka UI",
            "description": "Web UI for monitoring Kafka clusters",
            "default_port": 8080,
            "machine_type": "e2-small",
            "disk_size_gb": 10,
        },
        "prometheus": {
            "name": "Prometheus",
            "description": "Monitoring and alerting toolkit",
            "default_port": 9090,
            "machine_type": "e2-small",
            "disk_size_gb": 20,
        },
        "grafana": {
            "name": "Grafana",
            "description": "Analytics and monitoring platform",
            "default_port": 3000,
            "machine_type": "e2-small",
            "disk_size_gb": 10,
        },
    }

    @classmethod
    def get_addon_metadata(cls, addon_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for an addon by ID"""
        return cls.AVAILABLE_ADDONS.get(addon_id)

    @classmethod
    def list_available_addons(cls) -> List[Dict[str, Any]]:
        """List all available add-ons with their details"""
        return [{"id": addon_id, **properties} for addon_id, properties in cls.AVAILABLE_ADDONS.items()]

    @classmethod
    def is_valid_addon(cls, addon_id: str) -> bool:
        """Check if an add-on ID is valid"""
        return addon_id in cls.AVAILABLE_ADDONS

    @classmethod
    def get_installed_addons(cls, profile_data: Dict[str, Any]) -> List[str]:
        """Get list of installed add-on IDs from a profile"""
        addons = profile_data.get("addons", {}).get("enabled", [])
        if isinstance(addons, list):
            return addons
        return []

    @classmethod
    def add_addon_to_profile(cls, profile_data: Dict[str, Any], addon_id: str) -> Dict[str, Any]:
        """Add an add-on to a profile configuration"""
        # Initialize the addons section if it doesn't exist
        if "addons" not in profile_data:
            profile_data["addons"] = {"enabled": []}
        elif "enabled" not in profile_data["addons"]:
            profile_data["addons"]["enabled"] = []

        # Add the add-on if not already in the list
        enabled_addons = profile_data["addons"]["enabled"]
        if addon_id not in enabled_addons:
            enabled_addons.append(addon_id)

            # Initialize add-on-specific configuration with defaults
            addon_config = cls.get_addon_metadata(addon_id)
            if addon_config:
                config_key = f"addon_{addon_id.replace('-', '_')}"
                profile_data[config_key] = {
                    "enabled": True,
                    "machine_type": addon_config.get("machine_type", "e2-small"),
                    "disk_size_gb": addon_config.get("disk_size_gb", 10),
                    "port": addon_config.get("default_port", 8080),
                }

        return profile_data

    @classmethod
    def remove_addon_from_profile(cls, profile_data: Dict[str, Any], addon_id: str) -> Dict[str, Any]:
        """Remove an add-on from a profile configuration"""
        if "addons" in profile_data and "enabled" in profile_data["addons"]:
            # Remove the add-on from the enabled list
            enabled_addons = profile_data["addons"]["enabled"]
            if addon_id in enabled_addons:
                enabled_addons.remove(addon_id)

                # Remove add-on-specific configuration
                config_key = f"addon_{addon_id.replace('-', '_')}"
                if config_key in profile_data:
                    del profile_data[config_key]

        return profile_data


@CommandFactory.register("list_addons")
class ListAddonsCommand(ProfileAwareCommand):
    """Command for listing all addons for a profile"""

    def name(self) -> str:
        return "list_addons"

    def description(self) -> str:
        return "List all available and installed add-ons for a profile"

    def execute(self, profile_name: Optional[str] = None, **kwargs) -> CommandResult[Dict[str, List[str]]]:
        """List all available and installed add-ons for a profile"""
        try:
            # Load the profile
            profile_data = self.get_profile(profile_name)
            if not profile_data:
                profile_name = profile_name or self.config_manager.get_active_profile_name() or "default"
                console.print(f"[yellow]Profile '{profile_name}' not found.[/yellow]")
                console.print("Use [bold]kafka-cli profiles create[/bold] to create a new profile.")
                return CommandResult.error(f"Profile '{profile_name}' not found")

            profile_name = profile_data.get("profile", {}).get("name", "unknown")

            # Get installed add-ons
            installed_addons = AddonConfiguration.get_installed_addons(profile_data)

            # Get all available add-ons
            available_addons = AddonConfiguration.list_available_addons()

            # Display the add-ons
            console.print(f"[bold cyan]Add-ons for profile:[/bold cyan] {profile_name}")

            table = Table(title="Available Add-ons")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Description")
            table.add_column("Status", style="yellow")

            for addon in available_addons:
                status = "[bold green]INSTALLED[/bold green]" if addon["id"] in installed_addons else ""
                table.add_row(addon["id"], addon["name"], addon["description"], status)

            console.print(table)

            if not installed_addons:
                console.print("[yellow]No add-ons installed for this profile.[/yellow]")
                console.print("Use [bold]kafka-cli addons install[/bold] to install an add-on.")

            return CommandResult.ok({"available": [addon["id"] for addon in available_addons], "installed": installed_addons})

        except Exception as e:
            ErrorHandler().handle_exception(e)
            return CommandResult.error(str(e))


@CommandFactory.register("install_addon")
class InstallAddonCommand(ProfileAwareCommand):
    """Command for installing an addon to a profile"""

    def name(self) -> str:
        return "install_addon"

    def description(self) -> str:
        return "Install an add-on to a profile"

    def execute(self, addon_id: Optional[str] = None, profile_name: Optional[str] = None, **kwargs) -> CommandResult[bool]:
        """Install an add-on to a profile"""
        try:
            # Load the profile
            profile_data = self.get_profile(profile_name)
            if not profile_data:
                profile_name = profile_name or self.config_manager.get_active_profile_name() or "default"
                console.print(f"[yellow]Profile '{profile_name}' not found.[/yellow]")
                console.print("Use [bold]kafka-cli profiles create[/bold] to create a new profile.")
                return CommandResult.error(f"Profile '{profile_name}' not found")

            profile_name = profile_data.get("profile", {}).get("name", "unknown")

            # Get installed add-ons
            installed_addons = AddonConfiguration.get_installed_addons(profile_data)

            # Get all available add-ons
            available_addons = AddonConfiguration.list_available_addons()
            available_ids = [addon["id"] for addon in available_addons]

            # If no add-on specified, prompt for one
            if not addon_id:
                # Filter out already installed add-ons
                uninstalled_addons = [addon["id"] for addon in available_addons if addon["id"] not in installed_addons]

                if not uninstalled_addons:
                    console.print("[yellow]All available add-ons are already installed.[/yellow]")
                    return CommandResult.error("All add-ons already installed")

                addon_choices = []
                for addon_id in uninstalled_addons:
                    metadata = AddonConfiguration.get_addon_metadata(addon_id)
                    if metadata:
                        addon_choices.append(f"{addon_id} - {metadata['name']}")

                selected = Prompt.select("Select an add-on to install", choices=addon_choices)

                # Extract the ID from the selection
                addon_id = selected.split(" - ")[0]

            # Validate the add-on ID
            if addon_id not in available_ids:
                console.print(f"[red]Add-on '{addon_id}' is not a valid add-on.[/red]")
                console.print(f"Available add-ons: {', '.join(available_ids)}")
                return CommandResult.error(f"Invalid add-on ID: {addon_id}")

            # Check if already installed
            if addon_id in installed_addons:
                console.print(f"[yellow]Add-on '{addon_id}' is already installed in profile '{profile_name}'.[/yellow]")
                return CommandResult.error("Add-on already installed")

            # Get add-on metadata
            addon_metadata = AddonConfiguration.get_addon_metadata(addon_id)

            # Add the add-on to the profile
            console.print(f"Installing add-on: [bold cyan]{addon_metadata['name']}[/bold cyan]")
            updated_profile = AddonConfiguration.add_addon_to_profile(profile_data, addon_id)

            # Optional: Configure add-on settings interactively
            config_key = f"addon_{addon_id.replace('-', '_')}"
            if Prompt.confirm("Do you want to configure advanced settings for this add-on?", default=False):
                if config_key in updated_profile:
                    # Machine type
                    machine_type = Prompt.text(
                        "Machine type",
                        default=updated_profile[config_key].get("machine_type", addon_metadata.get("machine_type", "e2-small")),
                    )
                    updated_profile[config_key]["machine_type"] = machine_type

                    # Disk size
                    disk_size = Prompt.number(
                        "Disk size (GB)",
                        default=updated_profile[config_key].get("disk_size_gb", addon_metadata.get("disk_size_gb", 10)),
                        min_value=1,
                    )
                    updated_profile[config_key]["disk_size_gb"] = disk_size

                    # Port
                    port = Prompt.number(
                        "Port",
                        default=updated_profile[config_key].get("port", addon_metadata.get("default_port", 8080)),
                        min_value=1024,
                        max_value=65535,
                    )
                    updated_profile[config_key]["port"] = port

            # Save the updated profile
            if self.save_profile(updated_profile, profile_name):
                console.print(f"[bold green]Success:[/bold green] Add-on '{addon_id}' installed in profile '{profile_name}'.")
                return CommandResult.ok(True)
            else:
                console.print("[red]Failed to save profile after installing add-on.[/red]")
                return CommandResult.error("Failed to save profile")

        except Exception as e:
            ErrorHandler().handle_exception(e)
            return CommandResult.error(str(e))


@CommandFactory.register("uninstall_addon")
class UninstallAddonCommand(ProfileAwareCommand):
    """Command for uninstalling an addon from a profile"""

    def name(self) -> str:
        return "uninstall_addon"

    def description(self) -> str:
        return "Uninstall an add-on from a profile"

    def execute(
        self, addon_id: Optional[str] = None, profile_name: Optional[str] = None, force: bool = False, **kwargs
    ) -> CommandResult[bool]:
        """Uninstall an add-on from a profile"""
        try:
            # Load the profile
            profile_data = self.get_profile(profile_name)
            if not profile_data:
                profile_name = profile_name or self.config_manager.get_active_profile_name() or "default"
                console.print(f"[yellow]Profile '{profile_name}' not found.[/yellow]")
                console.print("Use [bold]kafka-cli profiles create[/bold] to create a new profile.")
                return CommandResult.error(f"Profile '{profile_name}' not found")

            profile_name = profile_data.get("profile", {}).get("name", "unknown")

            # Get installed add-ons
            installed_addons = AddonConfiguration.get_installed_addons(profile_data)

            if not installed_addons:
                console.print(f"[yellow]No add-ons installed in profile '{profile_name}'.[/yellow]")
                return CommandResult.error("No add-ons installed")

            # If no add-on specified, prompt for one
            if not addon_id:
                addon_choices = []
                for addon_id in installed_addons:
                    metadata = AddonConfiguration.get_addon_metadata(addon_id)
                    if metadata:
                        addon_choices.append(f"{addon_id} - {metadata['name']}")

                selected = Prompt.select("Select an add-on to uninstall", choices=addon_choices)

                # Extract the ID from the selection
                addon_id = selected.split(" - ")[0]

            # Validate the add-on ID
            if addon_id not in installed_addons:
                console.print(f"[red]Add-on '{addon_id}' is not installed in profile '{profile_name}'.[/red]")
                return CommandResult.error("Add-on not installed")

            # Get add-on metadata
            addon_metadata = AddonConfiguration.get_addon_metadata(addon_id)

            # Confirm uninstallation
            if not force and not Prompt.confirm(
                f"Are you sure you want to uninstall add-on '{addon_metadata['name']}' from profile '{profile_name}'?", default=False
            ):
                console.print("[yellow]Uninstallation cancelled.[/yellow]")
                return CommandResult.error("Uninstallation cancelled by user")

            # Remove the add-on from the profile
            console.print(f"Uninstalling add-on: [bold cyan]{addon_metadata['name']}[/bold cyan]")
            updated_profile = AddonConfiguration.remove_addon_from_profile(profile_data, addon_id)

            # Save the updated profile
            if self.save_profile(updated_profile, profile_name):
                console.print(f"[bold green]Success:[/bold green] Add-on '{addon_id}' uninstalled from profile '{profile_name}'.")
                return CommandResult.ok(True)
            else:
                console.print("[red]Failed to save profile after uninstalling add-on.[/red]")
                return CommandResult.error("Failed to save profile")

        except Exception as e:
            ErrorHandler().handle_exception(e)
            return CommandResult.error(str(e))


@CommandFactory.register("configure_addon")
class ConfigureAddonCommand(ProfileAwareCommand):
    """Command for configuring an addon in a profile"""

    def name(self) -> str:
        return "configure_addon"

    def description(self) -> str:
        return "Configure settings for an installed add-on"

    def execute(self, addon_id: Optional[str] = None, profile_name: Optional[str] = None, **kwargs) -> CommandResult[Dict[str, Any]]:
        """Configure an installed add-on"""
        try:
            # Load the profile
            profile_data = self.get_profile(profile_name)
            if not profile_data:
                profile_name = profile_name or self.config_manager.get_active_profile_name() or "default"
                console.print(f"[yellow]Profile '{profile_name}' not found.[/yellow]")
                console.print("Use [bold]kafka-cli profiles create[/bold] to create a new profile.")
                return CommandResult.error(f"Profile '{profile_name}' not found")

            profile_name = profile_data.get("profile", {}).get("name", "unknown")

            # Get installed add-ons
            installed_addons = AddonConfiguration.get_installed_addons(profile_data)

            if not installed_addons:
                console.print(f"[yellow]No add-ons installed in profile '{profile_name}'.[/yellow]")
                return CommandResult.error("No add-ons installed")

            # If no add-on specified, prompt for one
            if not addon_id:
                addon_choices = []
                for addon_id in installed_addons:
                    metadata = AddonConfiguration.get_addon_metadata(addon_id)
                    if metadata:
                        addon_choices.append(f"{addon_id} - {metadata['name']}")

                selected = Prompt.select("Select an add-on to configure", choices=addon_choices)

                # Extract the ID from the selection
                addon_id = selected.split(" - ")[0]

            # Validate the add-on ID
            if addon_id not in installed_addons:
                console.print(f"[red]Add-on '{addon_id}' is not installed in profile '{profile_name}'.[/red]")
                return CommandResult.error("Add-on not installed")

            # Get add-on metadata and configuration
            addon_metadata = AddonConfiguration.get_addon_metadata(addon_id)
            config_key = f"addon_{addon_id.replace('-', '_')}"

            # If the add-on config section doesn't exist, create it
            if config_key not in profile_data:
                profile_data[config_key] = {
                    "enabled": True,
                    "machine_type": addon_metadata.get("machine_type", "e2-small"),
                    "disk_size_gb": addon_metadata.get("disk_size_gb", 10),
                    "port": addon_metadata.get("default_port", 8080),
                }

            addon_config = profile_data[config_key]

            # Display current configuration
            console.print(f"[bold cyan]Current configuration for add-on:[/bold cyan] {addon_metadata['name']}")

            table = Table()
            table.add_column("Setting", style="cyan")
            table.add_column("Current Value", style="green")

            for key, value in addon_config.items():
                table.add_row(key, str(value))

            console.print(table)

            # Update configuration interactively
            console.print("[bold cyan]Update configuration:[/bold cyan]")

            # Update enabled status
            enabled = Prompt.confirm("Enable this add-on?", default=addon_config.get("enabled", True))
            addon_config["enabled"] = enabled

            if enabled:
                # Machine type
                machine_type = Prompt.text(
                    "Machine type", default=addon_config.get("machine_type", addon_metadata.get("machine_type", "e2-small"))
                )
                addon_config["machine_type"] = machine_type

                # Disk size
                disk_size = Prompt.number(
                    "Disk size (GB)", default=addon_config.get("disk_size_gb", addon_metadata.get("disk_size_gb", 10)), min_value=1
                )
                addon_config["disk_size_gb"] = disk_size

                # Port
                port = Prompt.number(
                    "Port",
                    default=addon_config.get("port", addon_metadata.get("default_port", 8080)),
                    min_value=1024,
                    max_value=65535,
                )
                addon_config["port"] = port

                # Add any add-on-specific configuration options here
                if addon_id == "kafka-connect":
                    # Plugin list
                    plugins = Prompt.text(
                        "Comma-separated list of connector plugins to install", default=addon_config.get("plugins", "")
                    )
                    addon_config["plugins"] = plugins
                elif addon_id == "schema-registry":
                    # Compatibility setting
                    compatibility = Prompt.select(
                        "Schema compatibility setting",
                        choices=["BACKWARD", "FORWARD", "FULL", "NONE"],
                        default=addon_config.get("compatibility", "BACKWARD"),
                    )
                    addon_config["compatibility"] = compatibility

            # Save the updated profile
            if self.save_profile(profile_data, profile_name):
                console.print(f"[bold green]Success:[/bold green] Configuration updated for add-on '{addon_id}'.")
                return CommandResult.ok(addon_config)
            else:
                console.print("[red]Failed to save profile after updating add-on configuration.[/red]")
                return CommandResult.error("Failed to save profile")

        except Exception as e:
            ErrorHandler().handle_exception(e)
            return CommandResult.error(str(e))


# Helper function to register commands with typer
def register_addon_commands(app: typer.Typer) -> None:
    """Register all addon commands with the Typer app"""

    @app.command("list")
    def list_addons(profile_name: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to list add-ons for")):
        """List all available and installed add-ons for a profile"""
        cmd = CommandFactory.create("list_addons")
        cmd.execute(profile_name=profile_name)

    @app.command("install")
    def install_addon(
        addon_id: Optional[str] = typer.Option(None, "--addon", "-a", help="ID of the add-on to install"),
        profile_name: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to install the add-on to"),
    ):
        """Install an add-on to a profile"""
        cmd = CommandFactory.create("install_addon")
        cmd.execute(addon_id=addon_id, profile_name=profile_name)

    @app.command("uninstall")
    def uninstall_addon(
        addon_id: Optional[str] = typer.Option(None, "--addon", "-a", help="ID of the add-on to uninstall"),
        profile_name: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to uninstall the add-on from"),
        force: bool = typer.Option(False, "--force", "-f", help="Uninstall without confirmation"),
    ):
        """Uninstall an add-on from a profile"""
        cmd = CommandFactory.create("uninstall_addon")
        cmd.execute(addon_id=addon_id, profile_name=profile_name, force=force)

    @app.command("configure")
    def configure_addon(
        addon_id: Optional[str] = typer.Option(None, "--addon", "-a", help="ID of the add-on to configure"),
        profile_name: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile containing the add-on"),
    ):
        """Configure settings for an installed add-on"""
        cmd = CommandFactory.create("configure_addon")
        cmd.execute(addon_id=addon_id, profile_name=profile_name)
