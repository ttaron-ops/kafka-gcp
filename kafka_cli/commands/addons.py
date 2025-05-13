import os
import typer
import yaml
from enum import Enum
from typing import Optional
from rich.console import Console
from rich.table import Table

from kafka_cli.utils.config import get_config, get_config_dir
from kafka_cli.utils.interactive import safe_typer_confirm, safe_select, safe_text

app = typer.Typer(help="Manage Kafka cluster add-ons")
console = Console()


class AddonType(str, Enum):
    KAFKA_UI = "kafka-ui"
    PROMETHEUS = "prometheus"
    KAFKA_EXPORTER = "kafka-exporter"
    GRAFANA = "grafana"
    SCHEMA_REGISTRY = "schema-registry"


@app.command("list")
def list_addons(
    profile_name: Optional[str] = typer.Option(
        None, "--profile", "-p", help="Profile to list add-ons for"
    ),
):
    """List all available and installed add-ons for a cluster"""
    # Determine which profile to use
    config = get_config()
    if not profile_name:
        profile_name = config.get("default_profile")
        
    if not profile_name:
        console.print("No profile specified and no default profile set", style="red")
        return
    
    profile_path = os.path.join(get_config_dir(), "profiles", f"{profile_name}.yaml")
    if not os.path.exists(profile_path):
        console.print(f"Profile [bold red]{profile_name}[/bold red] not found", style="red")
        return
    
    # Load the profile
    try:
        with open(profile_path, 'r') as f:
            profile = yaml.safe_load(f)
    except Exception as e:
        console.print(f"Error reading profile: {str(e)}", style="red")
        return
    
    # Get the addons configuration
    addons = profile.get("addons", {})
    
    # Create a table to display the add-ons
    table = Table(title=f"Add-ons for Profile: {profile_name}")
    table.add_column("Add-on", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("URL", style="blue")
    
    # Available add-ons
    addon_list = [
        {"name": "Kafka UI", "key": "kafka_ui", "default_port": 8080},
        {"name": "Prometheus", "key": "prometheus", "default_port": 9090},
        {"name": "Kafka Exporter", "key": "kafka_exporter", "default_port": 9308},
        {"name": "Grafana", "key": "grafana", "default_port": 3000},
        {"name": "Schema Registry", "key": "schema_registry", "default_port": 8081},
    ]
    
    # Add-on URLs will depend on the deployment target
    deployment_target = addons.get("deployment_target", "Unknown")
    
    for addon in addon_list:
        status = "Installed" if addons.get(addon["key"]) else "Not Installed"
        
        # Generate a dummy URL for installed add-ons
        url = ""
        if addons.get(addon["key"]):
            if deployment_target == "GCP Cloud Run":
                url = f"https://{addon['key']}-{profile_name}.run.app"
            elif deployment_target == "GCP Compute Engine VM":
                url = f"http://addon-vm-{profile_name}.example.com:{addon['default_port']}"
            elif deployment_target == "Existing Kubernetes Cluster":
                url = f"http://{addon['key']}.{profile_name}.svc.cluster.local:{addon['default_port']}"
        
        table.add_row(addon["name"], status, url if addons.get(addon["key"]) else "N/A")
    
    console.print(table)


@app.command("install")
def install_addon(
    addon: AddonType = typer.Argument(..., help="Add-on to install"),
    profile_name: Optional[str] = typer.Option(
        None, "--profile", "-p", help="Profile to install add-on for"
    ),
    custom_values: Optional[str] = typer.Option(
        None, "--values", "-f", help="Path to custom Helm values file"
    ),
):
    """Install an add-on to a Kafka cluster"""
    # Determine which profile to use
    config = get_config()
    if not profile_name:
        profile_name = config.get("default_profile")
        
    if not profile_name:
        console.print("No profile specified and no default profile set", style="red")
        return
    
    profile_path = os.path.join(get_config_dir(), "profiles", f"{profile_name}.yaml")
    if not os.path.exists(profile_path):
        console.print(f"Profile [bold red]{profile_name}[/bold red] not found", style="red")
        return
    
    # Load the profile
    try:
        with open(profile_path, 'r') as f:
            profile = yaml.safe_load(f)
    except Exception as e:
        console.print(f"Error reading profile: {str(e)}", style="red")
        return
    
    # Get the addons configuration
    addons = profile.get("addons", {})
    
    # Convert addon type enum to profile key
    addon_key = addon.value.replace("-", "_")
    
    # Check if addon is already installed
    if addons.get(addon_key):
        console.print(f"Add-on [bold cyan]{addon.value}[/bold cyan] is already installed", style="yellow")
        return
    
    # Check if deployment target is set
    if "deployment_target" not in addons:
        deployment_target = safe_select(
            "Select deployment target:",
            choices=["GCP Cloud Run", "GCP Compute Engine VM", "Existing Kubernetes Cluster"],
            default="GCP Compute Engine VM"
        )
        addons["deployment_target"] = deployment_target
    
    # If using Kubernetes and no kubeconfig is set, prompt for it
    if addons["deployment_target"] == "Existing Kubernetes Cluster" and "kubeconfig_path" not in addons:
        kubeconfig_path = safe_text(
            "Enter path to kubeconfig file:",
            default="~/.kube/config"
        )
        addons["kubeconfig_path"] = kubeconfig_path
    
    console.print(f"Installing add-on [bold cyan]{addon.value}[/bold cyan] for profile [bold cyan]{profile_name}[/bold cyan]...")
    
    # Here would be the actual installation logic
    # This is a placeholder for demonstration purposes
    
    # Update the profile with the new addon
    addons[addon_key] = True
    profile["addons"] = addons
    
    # Save the updated profile
    try:
        with open(profile_path, 'w') as f:
            yaml.dump(profile, f, default_flow_style=False)
        console.print(f"✅ Add-on [bold cyan]{addon.value}[/bold cyan] installed successfully")
    except Exception as e:
        console.print(f"Error saving profile: {str(e)}", style="red")


@app.command("uninstall")
def uninstall_addon(
    addon: AddonType = typer.Argument(..., help="Add-on to uninstall"),
    profile_name: Optional[str] = typer.Option(
        None, "--profile", "-p", help="Profile to uninstall add-on from"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force uninstallation without confirmation"
    ),
):
    """Uninstall an add-on from a Kafka cluster"""
    # Determine which profile to use
    config = get_config()
    if not profile_name:
        profile_name = config.get("default_profile")
        
    if not profile_name:
        console.print("No profile specified and no default profile set", style="red")
        return
    
    profile_path = os.path.join(get_config_dir(), "profiles", f"{profile_name}.yaml")
    if not os.path.exists(profile_path):
        console.print(f"Profile [bold red]{profile_name}[/bold red] not found", style="red")
        return
    
    # Load the profile
    try:
        with open(profile_path, 'r') as f:
            profile = yaml.safe_load(f)
    except Exception as e:
        console.print(f"Error reading profile: {str(e)}", style="red")
        return
    
    # Get the addons configuration
    addons = profile.get("addons", {})
    
    # Convert addon type enum to profile key
    addon_key = addon.value.replace("-", "_")
    
    # Check if addon is installed
    if not addons.get(addon_key):
        console.print(f"Add-on [bold cyan]{addon.value}[/bold cyan] is not installed", style="yellow")
        return
    
    # Confirm uninstallation
    if not force and not safe_typer_confirm(f"Are you sure you want to uninstall {addon.value}?"):
        console.print("Uninstallation cancelled", style="yellow")
        return
    
    console.print(f"Uninstalling add-on [bold cyan]{addon.value}[/bold cyan] from profile [bold cyan]{profile_name}[/bold cyan]...")
    
    # Here would be the actual uninstallation logic
    # This is a placeholder for demonstration purposes
    
    # Update the profile to remove the addon
    addons[addon_key] = False
    profile["addons"] = addons
    
    # Save the updated profile
    try:
        with open(profile_path, 'w') as f:
            yaml.dump(profile, f, default_flow_style=False)
        console.print(f"✅ Add-on [bold cyan]{addon.value}[/bold cyan] uninstalled successfully")
    except Exception as e:
        console.print(f"Error saving profile: {str(e)}", style="red")
