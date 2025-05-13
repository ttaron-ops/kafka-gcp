"""
Profile management commands implementation using the Command pattern.
"""
from typing import Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.table import Table

from kafka_cli.core.commands.base import Command, CommandFactory, CommandResult, ProfileAwareCommand
from kafka_cli.core.config_manager import ConfigManager
from kafka_cli.core.errors import ErrorHandler, ValidationError
from kafka_cli.core.interactive import Prompt

console = Console()


@CommandFactory.register("list_profiles")
class ListProfilesCommand(Command):
    """Command for listing all profiles"""

    def __init__(self):
        self.config_manager = ConfigManager()

    def name(self) -> str:
        return "list_profiles"

    def description(self) -> str:
        return "List all available configuration profiles"

    def execute(self, *args, **kwargs) -> CommandResult[List[str]]:
        """List all available profiles"""
        try:
            profiles = self.config_manager.list_profiles()
            active_profile = self.config_manager.get_active_profile_name()

            if not profiles:
                console.print("[yellow]No configuration profiles found.[/yellow]")
                console.print("Use [bold]kafka-cli profiles create[/bold] to create a new profile.")
                return CommandResult.ok([])

            # Display profiles in a table
            table = Table(title="Available Configuration Profiles")
            table.add_column("Profile Name", style="cyan")
            table.add_column("Status", style="green")

            for profile in profiles:
                status = "[bold green]ACTIVE[/bold green]" if profile == active_profile else ""
                table.add_row(profile, status)

            console.print(table)
            return CommandResult.ok(profiles)

        except Exception as e:
            ErrorHandler().handle_exception(e)
            return CommandResult.error(str(e))


@CommandFactory.register("create_profile")
class CreateProfileCommand(ProfileAwareCommand):
    """Command for creating a new profile"""

    def name(self) -> str:
        return "create_profile"

    def description(self) -> str:
        return "Create a new configuration profile"

    def execute(self, profile_name: Optional[str] = None, interactive: bool = True, **kwargs) -> CommandResult[str]:
        """Create a new profile with the given name"""
        try:
            if not profile_name and interactive:
                profile_name = Prompt.text("Enter a name for the new profile", default="default")

            if not profile_name:
                raise ValidationError("Profile name is required")

            # Check if profile already exists
            profiles = self.list_profiles()
            if profile_name in profiles:
                if interactive and not Prompt.confirm(f"Profile '{profile_name}' already exists. Overwrite?", default=False):
                    console.print("[yellow]Profile creation cancelled.[/yellow]")
                    return CommandResult.error("Profile creation cancelled by user")

            # Create basic profile structure
            profile_data = {
                "profile": {"name": profile_name, "cloud": "gcp"},
                "gcp": {"project_id": "", "region": "", "zone": ""},
                "kafka": {
                    "cluster_name": "",
                    "broker_count": 3,
                    "zookeeper_count": 3,
                    "machine_type": "e2-standard-2",
                    "disk_type": "pd-standard",
                    "disk_size_gb": 100,
                },
                "network": {"network_name": "default", "subnet_name": "default"},
                "security": {"enable_public_endpoints": False, "enable_tls": True, "enable_sasl": False},
            }

            # If interactive, gather minimal required info
            if interactive:
                # Cloud provider
                cloud_provider = Prompt.select("Select cloud provider", choices=["gcp", "aws"], default="gcp")
                profile_data["profile"]["cloud"] = cloud_provider

                # Project ID
                if cloud_provider == "gcp":
                    profile_data["gcp"]["project_id"] = Prompt.text("Enter GCP project ID", default="")

                # Basic Kafka config
                profile_data["kafka"]["cluster_name"] = Prompt.text(
                    "Enter a name for your Kafka cluster", default=f"kafka-{profile_name}"
                )

                # Save the new configuration
                console.print(f"Creating new profile: [bold cyan]{profile_name}[/bold cyan]")

            # Save the profile
            if self.save_profile(profile_data, profile_name):
                console.print(f"[bold green]Success:[/bold green] Profile '{profile_name}' created.")

                # Set as active if it's the first profile
                if len(profiles) == 0:
                    self.config_manager.set_active_profile(profile_name)
                    console.print(f"[bold green]Profile '{profile_name}' set as active.[/bold green]")
                elif interactive and Prompt.confirm(f"Set '{profile_name}' as the active profile?", default=True):
                    self.config_manager.set_active_profile(profile_name)
                    console.print(f"[bold green]Profile '{profile_name}' set as active.[/bold green]")

                return CommandResult.ok(profile_name)
            else:
                return CommandResult.error(f"Failed to save profile '{profile_name}'")

        except Exception as e:
            ErrorHandler().handle_exception(e)
            return CommandResult.error(str(e))


@CommandFactory.register("delete_profile")
class DeleteProfileCommand(ProfileAwareCommand):
    """Command for deleting a profile"""

    def name(self) -> str:
        return "delete_profile"

    def description(self) -> str:
        return "Delete a configuration profile"

    def execute(self, profile_name: Optional[str] = None, force: bool = False, **kwargs) -> CommandResult[bool]:
        """Delete the profile with the given name"""
        try:
            profiles = self.list_profiles()

            if not profiles:
                console.print("[yellow]No profiles available to delete.[/yellow]")
                return CommandResult.error("No profiles available")

            if not profile_name:
                profile_name = Prompt.select("Select a profile to delete", choices=profiles)

            if profile_name not in profiles:
                raise ValidationError(f"Profile '{profile_name}' does not exist")

            # Confirm deletion unless force is True
            if not force and not Prompt.confirm(f"Are you sure you want to delete profile '{profile_name}'?", default=False):
                console.print("[yellow]Profile deletion cancelled.[/yellow]")
                return CommandResult.error("Profile deletion cancelled by user")

            # Check if it's the active profile
            active_profile = self.config_manager.get_active_profile_name()

            # Delete the profile
            if self.config_manager.delete_profile(profile_name):
                console.print(f"[bold green]Success:[/bold green] Profile '{profile_name}' deleted.")

                # If we deleted the active profile, reset to another one if available
                if profile_name == active_profile and profiles:
                    remaining_profiles = [p for p in profiles if p != profile_name]
                    if remaining_profiles:
                        new_active = remaining_profiles[0]
                        self.config_manager.set_active_profile(new_active)
                        console.print(f"[bold green]Profile '{new_active}' set as active.[/bold green]")

                return CommandResult.ok(True)
            else:
                return CommandResult.error(f"Failed to delete profile '{profile_name}'")

        except Exception as e:
            ErrorHandler().handle_exception(e)
            return CommandResult.error(str(e))


@CommandFactory.register("set_active_profile")
class SetActiveProfileCommand(ProfileAwareCommand):
    """Command for setting the active profile"""

    def name(self) -> str:
        return "set_active_profile"

    def description(self) -> str:
        return "Set the active configuration profile"

    def execute(self, profile_name: Optional[str] = None, **kwargs) -> CommandResult[str]:
        """Set the active profile"""
        try:
            profiles = self.list_profiles()

            if not profiles:
                console.print("[yellow]No profiles available.[/yellow]")
                console.print("Use [bold]kafka-cli profiles create[/bold] to create a new profile.")
                return CommandResult.error("No profiles available")

            if not profile_name:
                current_active = self.config_manager.get_active_profile_name()
                default_choice = current_active if current_active in profiles else profiles[0]

                profile_name = Prompt.select("Select the profile to set as active", choices=profiles, default=default_choice)

            if profile_name not in profiles:
                raise ValidationError(f"Profile '{profile_name}' does not exist")

            # Set the active profile
            if self.config_manager.set_active_profile(profile_name):
                console.print(f"[bold green]Success:[/bold green] Profile '{profile_name}' set as active.")
                return CommandResult.ok(profile_name)
            else:
                return CommandResult.error(f"Failed to set profile '{profile_name}' as active")

        except Exception as e:
            ErrorHandler().handle_exception(e)
            return CommandResult.error(str(e))


@CommandFactory.register("show_profile")
class ShowProfileCommand(ProfileAwareCommand):
    """Command for showing profile details"""

    def name(self) -> str:
        return "show_profile"

    def description(self) -> str:
        return "Show details of a configuration profile"

    def execute(self, profile_name: Optional[str] = None, **kwargs) -> CommandResult[Dict[str, Any]]:
        """Show details of a profile"""
        try:
            profiles = self.list_profiles()

            if not profiles:
                console.print("[yellow]No profiles available.[/yellow]")
                console.print("Use [bold]kafka-cli profiles create[/bold] to create a new profile.")
                return CommandResult.error("No profiles available")

            if not profile_name:
                current_active = self.config_manager.get_active_profile_name()
                default_choice = current_active if current_active in profiles else profiles[0]

                profile_name = Prompt.select("Select a profile to view", choices=profiles, default=default_choice)

            # Load the profile
            profile_data = self.get_profile(profile_name)
            if not profile_data:
                raise ValidationError(f"Failed to load profile '{profile_name}'")

            # Display profile details
            console.print(f"[bold cyan]Profile: {profile_name}[/bold cyan]")

            # Create tables for each section
            self._display_section(profile_data, "profile", "Profile Settings")
            self._display_section(profile_data, "gcp", "GCP Configuration")
            self._display_section(profile_data, "kafka", "Kafka Configuration")
            self._display_section(profile_data, "network", "Network Configuration")
            self._display_section(profile_data, "security", "Security Configuration")

            return CommandResult.ok(profile_data)

        except Exception as e:
            ErrorHandler().handle_exception(e)
            return CommandResult.error(str(e))

    def _display_section(self, profile_data: Dict[str, Any], section: str, title: str) -> None:
        """Helper to display a section of the profile"""
        if section in profile_data:
            table = Table(title=title)
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="green")

            for key, value in profile_data[section].items():
                # Format boolean values
                if isinstance(value, bool):
                    value_str = "[green]✓[/green]" if value else "[red]✗[/red]"
                else:
                    value_str = str(value) if value is not None else ""

                table.add_row(key, value_str)

            console.print(table)
            console.print("")  # Add spacing between tables


# Helper function to register commands with typer
def register_profile_commands(app: typer.Typer) -> None:
    """Register all profile commands with the Typer app"""

    @app.command("list")
    def list_profiles():
        """List all available configuration profiles"""
        cmd = CommandFactory.create("list_profiles")
        cmd.execute()

    @app.command("create")
    def create_profile(profile_name: Optional[str] = typer.Option(None, "--name", "-n", help="Name for the new profile")):
        """Create a new configuration profile"""
        cmd = CommandFactory.create("create_profile")
        cmd.execute(profile_name=profile_name)

    @app.command("delete")
    def delete_profile(
        profile_name: Optional[str] = typer.Option(None, "--name", "-n", help="Name of the profile to delete"),
        force: bool = typer.Option(False, "--force", "-f", help="Delete without confirmation"),
    ):
        """Delete a configuration profile"""
        cmd = CommandFactory.create("delete_profile")
        cmd.execute(profile_name=profile_name, force=force)

    @app.command("set-active")
    def set_active_profile(
        profile_name: Optional[str] = typer.Option(None, "--name", "-n", help="Name of the profile to set as active")
    ):
        """Set the active configuration profile"""
        cmd = CommandFactory.create("set_active_profile")
        cmd.execute(profile_name=profile_name)

    @app.command("show")
    def show_profile(profile_name: Optional[str] = typer.Option(None, "--name", "-n", help="Name of the profile to show")):
        """Show details of a configuration profile"""
        cmd = CommandFactory.create("show_profile")
        cmd.execute(profile_name=profile_name)
