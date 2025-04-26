import os
import typer
import yaml
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

app = typer.Typer(help="Check the health of Kafka clusters and components")
console = Console()


@app.command("check")
def check_health(
    profile_name: Optional[str] = typer.Option(
        None, "--profile", "-p", help="Profile to check health for"
    ),
    component: Optional[str] = typer.Option(
        None, 
        "--component", 
        "-c", 
        help="Specific component to check (kafka, addons, network)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed health information"
    ),
):
    """Check the health of a Kafka cluster and its components"""
    from kafka_cli.utils.config import get_config, get_config_dir
    
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
    
    console.print(f"Checking health for profile: [bold cyan]{profile_name}[/bold cyan]")
    
    # Start the health check process with a progress bar
    with Progress() as progress:
        overall_task = progress.add_task("[green]Running health checks...", total=100)
        
        # Check infrastructure/network if requested or if checking all components
        if not component or component.lower() == "network":
            progress.update(overall_task, advance=10, description="[green]Checking network...")
            network_status = check_network_health(profile, verbose)
            progress.update(overall_task, advance=20)
        
        # Check Kafka if requested or if checking all components
        if not component or component.lower() == "kafka":
            progress.update(overall_task, description="[green]Checking Kafka brokers...")
            kafka_status = check_kafka_health(profile, verbose)
            progress.update(overall_task, advance=40)
        
        # Check addons if requested or if checking all components
        if not component or component.lower() == "addons":
            progress.update(overall_task, description="[green]Checking add-ons...")
            addons_status = check_addons_health(profile, verbose)
            progress.update(overall_task, advance=30)
        
        # Complete the progress
        progress.update(overall_task, completed=100)
    
    # Display the overall health summary
    console.print("\n[bold]Health Check Summary:[/bold]")
    
    table = Table(title=f"Cluster Health: {profile_name}")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="magenta")
    
    if not component or component.lower() == "network":
        table.add_row(
            "Network", 
            network_status.get("status", "Unknown"),
            network_status.get("message", "")
        )
    
    if not component or component.lower() == "kafka":
        table.add_row(
            "Kafka Brokers", 
            kafka_status.get("status", "Unknown"),
            kafka_status.get("message", "")
        )
    
    if not component or component.lower() == "addons":
        for addon, status in addons_status.items():
            table.add_row(
                f"Addon: {addon}", 
                status.get("status", "Unknown"),
                status.get("message", "")
            )
    
    console.print(table)


def check_network_health(profile, verbose):
    """Check the health of the network infrastructure"""
    # This is a placeholder for actual network health checks
    # In a real implementation, this would connect to GCP APIs to check resources
    
    # For demonstration purposes, we'll simulate a healthy network
    return {
        "status": "Healthy",
        "message": "All network components are running",
        "details": {
            "vpc": "OK",
            "subnets": "OK",
            "firewall_rules": "OK",
            "peering": "OK" if profile.get("networking", {}).get("enable_peering") else "N/A"
        }
    }


def check_kafka_health(profile, verbose):
    """Check the health of the Kafka brokers"""
    # This is a placeholder for actual Kafka health checks
    # In a real implementation, this would connect to the Kafka cluster and run health checks
    
    # For demonstration purposes, we'll simulate a healthy Kafka cluster
    return {
        "status": "Healthy",
        "message": f"All {profile.get('kafka', {}).get('broker_count', 3)} brokers are running",
        "details": {
            "brokers_online": profile.get("kafka", {}).get("broker_count", 3),
            "topics_count": 12,  # Simulated value
            "controller_id": 1,   # Simulated value
            "kraft_mode": "Enabled" if profile.get("kafka", {}).get("kraft_mode") else "Disabled"
        }
    }


def check_addons_health(profile, verbose):
    """Check the health of the add-ons"""
    # This is a placeholder for actual add-on health checks
    # In a real implementation, this would check each add-on's status
    
    addons = profile.get("addons", {})
    results = {}
    
    # Check Kafka UI if enabled
    if addons.get("kafka_ui"):
        results["Kafka UI"] = {
            "status": "Healthy",
            "message": "Service is running",
            "url": "https://kafka-ui.example.com"  # Simulated URL
        }
    
    # Check Prometheus if enabled
    if addons.get("prometheus"):
        results["Prometheus"] = {
            "status": "Healthy",
            "message": "Service is running",
            "url": "https://prometheus.example.com"  # Simulated URL
        }
    
    # Check Kafka Exporter if enabled
    if addons.get("kafka_exporter"):
        results["Kafka Exporter"] = {
            "status": "Healthy",
            "message": "Service is running and collecting metrics"
        }
    
    # Check Grafana if enabled
    if addons.get("grafana"):
        results["Grafana"] = {
            "status": "Healthy",
            "message": "Service is running",
            "url": "https://grafana.example.com"  # Simulated URL
        }
    
    # Check Schema Registry if enabled
    if addons.get("schema_registry"):
        results["Schema Registry"] = {
            "status": "Healthy",
            "message": "Service is running",
            "url": "https://schema-registry.example.com"  # Simulated URL
        }
    
    return results


@app.command("logs")
def view_logs(
    profile_name: Optional[str] = typer.Option(
        None, "--profile", "-p", help="Profile to view logs for"
    ),
    component: str = typer.Option(
        "kafka", "--component", "-c", 
        help="Component to view logs for (kafka, zookeeper, kafka-ui, etc.)"
    ),
    lines: int = typer.Option(
        50, "--lines", "-n", help="Number of log lines to display"
    ),
    follow: bool = typer.Option(
        False, "--follow", "-f", help="Follow log output"
    ),
):
    """View logs for a specific component of the Kafka cluster"""
    from kafka_cli.utils.config import get_config, get_config_dir
    
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
    
    console.print(f"Fetching {lines} lines of logs for {component} in profile: [bold cyan]{profile_name}[/bold cyan]")
    
    # This is a placeholder where actual log retrieval would happen
    # In a real implementation, this would connect to the appropriate service and retrieve logs
    console.print("[italic]Log retrieval not implemented in this demo version[/italic]", style="yellow")
