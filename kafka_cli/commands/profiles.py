import os
import typer
import yaml
import datetime
from typing import List
from rich.console import Console
from rich.table import Table

from kafka_cli.utils.config import get_config, update_config, get_config_dir
from kafka_cli.utils.interactive import safe_typer_confirm, check_interactive_or_exit

app = typer.Typer(help="Manage configuration profiles")
console = Console()


@app.command("list")
def list_profiles():
    """List all available configuration profiles"""
    profiles_dir = os.path.join(get_config_dir(), "profiles")
    
    if not os.path.exists(profiles_dir):
        console.print("Profiles directory not found", style="yellow")
        return
    
    profiles = [f[:-5] for f in os.listdir(profiles_dir) if f.endswith(".yaml")]
    
    if not profiles:
        console.print("No profiles found", style="yellow")
        return
    
    config = get_config()
    default_profile = config.get("default_profile")
    
    table = Table(title="Available Profiles")
    table.add_column("Profile Name", style="cyan")
    table.add_column("Default", style="green")
    table.add_column("Last Modified", style="magenta")
    
    for profile in sorted(profiles):
        profile_path = os.path.join(profiles_dir, f"{profile}.yaml")
        last_modified = os.path.getmtime(profile_path)
        last_modified_dt = datetime.datetime.fromtimestamp(last_modified)
        last_modified_str = last_modified_dt.strftime("%Y-%m-%d %H:%M:%S")
        
        is_default = "✓" if profile == default_profile else ""
        table.add_row(profile, is_default, last_modified_str)
    
    console.print(table)


@app.command("show")
def show_profile(
    profile_name: str = typer.Argument(..., help="Name of the profile to display"),
):
    """Show the details of a specific profile"""
    profile_path = os.path.join(get_config_dir(), "profiles", f"{profile_name}.yaml")
    
    if not os.path.exists(profile_path):
        console.print(f"Profile [bold red]{profile_name}[/bold red] not found", style="red")
        return
    
    try:
        with open(profile_path, 'r') as f:
            profile = yaml.safe_load(f)
        
        console.print(f"\n[bold]Profile: [cyan]{profile_name}[/cyan][/bold]")
        
        # Display GCP configuration
        if "gcp" in profile:
            console.print("\n[bold cyan]GCP Configuration:[/bold cyan]")
            for key, value in profile["gcp"].items():
                console.print(f"  {key}: {value}")
        
        # Display networking configuration
        if "networking" in profile:
            console.print("\n[bold cyan]Networking Configuration:[/bold cyan]")
            for key, value in profile["networking"].items():
                console.print(f"  {key}: {value}")
        
        # Display Kafka configuration
        if "kafka" in profile:
            console.print("\n[bold cyan]Kafka Configuration:[/bold cyan]")
            for key, value in profile["kafka"].items():
                console.print(f"  {key}: {value}")
        
        # Display add-ons configuration
        if "addons" in profile:
            console.print("\n[bold cyan]Add-ons Configuration:[/bold cyan]")
            for key, value in profile["addons"].items():
                if key not in ["deployment_target", "kubeconfig_path"]:
                    console.print(f"  {key}: {'Enabled' if value else 'Disabled'}")
            
            if "deployment_target" in profile["addons"]:
                console.print(f"  Deployment Target: {profile['addons']['deployment_target']}")
            
            if "kubeconfig_path" in profile["addons"]:
                console.print(f"  Kubeconfig Path: {profile['addons']['kubeconfig_path']}")
        
    except Exception as e:
        console.print(f"Error reading profile: {str(e)}", style="red")


@app.command("create")
def create_profile(
    profile_name: str = typer.Argument(..., help="Name for the new profile"),
):
    """Create a new configuration profile via the interactive wizard"""
    from kafka_cli.commands.start import run_wizard
    
    # Check if profile already exists
    profile_path = os.path.join(get_config_dir(), "profiles", f"{profile_name}.yaml")
    if os.path.exists(profile_path):
        if not safe_typer_confirm(f"Profile {profile_name} already exists. Do you want to overwrite it?"):
            console.print("Profile creation aborted", style="yellow")
            return
    
    console.print(f"Creating new profile: [bold cyan]{profile_name}[/bold cyan]")
    # Launch the wizard with the profile name
    run_wizard(profile_name=None)  # We'll use None here and save as the specified name


@app.command("delete")
def delete_profile(
    profile_name: str = typer.Argument(..., help="Name of the profile to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Force deletion without confirmation"),
):
    """Delete a configuration profile"""
    profiles_dir = os.path.join(get_config_dir(), "profiles")
    profile_path = os.path.join(profiles_dir, f"{profile_name}.yaml")
    
    if not os.path.exists(profile_path):
        console.print(f"Profile [bold red]{profile_name}[/bold red] not found", style="red")
        return
    
    # Check if this is the default profile
    config = get_config()
    if config.get("default_profile") == profile_name:
        console.print(
            f"Warning: You are deleting the default profile.",
            style="yellow"
        )
    
    if not force and not safe_typer_confirm(f"Are you sure you want to delete profile '{profile_name}'?"):
        console.print("Profile deletion aborted", style="yellow")
        return
    
    try:
        os.remove(profile_path)
        console.print(f"Profile [bold cyan]{profile_name}[/bold cyan] deleted successfully")
        
        # If this was the default profile, update the config
        if config.get("default_profile") == profile_name:
            config["default_profile"] = None
            update_config(config)
            console.print("Default profile has been cleared", style="yellow")
    
    except Exception as e:
        console.print(f"Error deleting profile: {str(e)}", style="red")


@app.command("set-default")
def set_default_profile(
    profile_name: str = typer.Argument(..., help="Name of the profile to set as default"),
):
    """Set a profile as the default for commands"""
    profile_path = os.path.join(get_config_dir(), "profiles", f"{profile_name}.yaml")
    
    if not os.path.exists(profile_path):
        console.print(f"Profile [bold red]{profile_name}[/bold red] not found", style="red")
        return
    
    config = get_config()
    config["default_profile"] = profile_name
    
    if update_config(config):
        console.print(f"Default profile set to [bold cyan]{profile_name}[/bold cyan]")
    else:
        console.print("Failed to update default profile", style="red")
