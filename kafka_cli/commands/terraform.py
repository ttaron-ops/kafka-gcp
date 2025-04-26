import os
import typer
from typing import Optional
from rich.console import Console
from rich.panel import Panel

from kafka_cli.utils.config import get_config, get_config_dir
from kafka_cli.utils.terraform import run_terraform_command
from kafka_cli.utils.interactive import safe_typer_confirm, safe_text

app = typer.Typer(help="Manage Terraform operations for Kafka clusters")
console = Console()


@app.command("plan")
def terraform_plan(
    profile_name: Optional[str] = typer.Option(
        None, "--profile", "-p", help="Profile to use for Terraform plan"
    ),
    output_file: Optional[str] = typer.Option(
        None, "--output", "-o", help="Save plan output to file"
    ),
):
    """
    Generate a Terraform plan for the specified profile
    """
    # Determine which profile to use
    config = get_config()
    if not profile_name:
        profile_name = config.get("default_profile")
        
    if not profile_name:
        console.print("No profile specified and no default profile set", style="red")
        return
    
    # Check if profile exists
    profile_path = os.path.join(get_config_dir(), "profiles", f"{profile_name}.yaml")
    if not os.path.exists(profile_path):
        console.print(f"Profile [bold red]{profile_name}[/bold red] not found", style="red")
        return
    
    console.print(f"Generating Terraform plan for profile: [bold cyan]{profile_name}[/bold cyan]")
    
    # Run terraform plan
    success = run_terraform_command(
        profile_name=profile_name,
        command="plan",
        output_file=output_file,
    )
    
    if success:
        console.print(Panel.fit(
            "Terraform plan completed successfully",
            title="Success",
            border_style="green",
        ))
    else:
        console.print(Panel.fit(
            "Terraform plan failed. Check the logs for details.",
            title="Error",
            border_style="red",
        ))


@app.command("apply")
def terraform_apply(
    profile_name: Optional[str] = typer.Option(
        None, "--profile", "-p", help="Profile to use for Terraform apply"
    ),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", "-y", help="Auto-approve Terraform apply"
    ),
):
    """
    Apply Terraform configuration for the specified profile
    """
    # Determine which profile to use
    config = get_config()
    if not profile_name:
        profile_name = config.get("default_profile")
        
    if not profile_name:
        console.print("No profile specified and no default profile set", style="red")
        return
    
    # Check if profile exists
    profile_path = os.path.join(get_config_dir(), "profiles", f"{profile_name}.yaml")
    if not os.path.exists(profile_path):
        console.print(f"Profile [bold red]{profile_name}[/bold red] not found", style="red")
        return
    
    # Confirm apply if not auto-approved
    if not auto_approve:
        console.print("[bold yellow]Warning:[/bold yellow] This operation will provision real infrastructure in your GCP account.")
        if not safe_typer_confirm("Do you want to continue?"):
            console.print("Operation cancelled", style="yellow")
            return
    
    console.print(f"Applying Terraform configuration for profile: [bold cyan]{profile_name}[/bold cyan]")
    
    # Run terraform apply
    success = run_terraform_command(
        profile_name=profile_name,
        command="apply",
        auto_approve=auto_approve,
    )
    
    if success:
        console.print(Panel.fit(
            "Terraform apply completed successfully",
            title="Success",
            border_style="green",
        ))
    else:
        console.print(Panel.fit(
            "Terraform apply failed. Check the logs for details.",
            title="Error",
            border_style="red",
        ))


@app.command("destroy")
def terraform_destroy(
    profile_name: Optional[str] = typer.Option(
        None, "--profile", "-p", help="Profile to use for Terraform destroy"
    ),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", "-y", help="Auto-approve Terraform destroy"
    ),
):
    """
    Destroy Terraform-managed infrastructure for the specified profile
    """
    # Determine which profile to use
    config = get_config()
    if not profile_name:
        profile_name = config.get("default_profile")
        
    if not profile_name:
        console.print("No profile specified and no default profile set", style="red")
        return
    
    # Check if profile exists
    profile_path = os.path.join(get_config_dir(), "profiles", f"{profile_name}.yaml")
    if not os.path.exists(profile_path):
        console.print(f"Profile [bold red]{profile_name}[/bold red] not found", style="red")
        return
    
    # Confirm destroy if not auto-approved
    if not auto_approve:
        console.print("[bold red]Warning:[/bold red] This operation will DESTROY all infrastructure resources in your GCP account.")
        console.print("[bold red]This action cannot be undone.[/bold red]")
        
        confirmation = safe_text(
            "Type the profile name to confirm destruction:",
            default=""
        )
        
        if confirmation != profile_name:
            console.print("Destruction cancelled: profile name did not match", style="yellow")
            return
    
    console.print(f"Destroying Terraform-managed infrastructure for profile: [bold cyan]{profile_name}[/bold cyan]")
    
    # Run terraform destroy
    success = run_terraform_command(
        profile_name=profile_name,
        command="destroy",
        auto_approve=auto_approve,
    )
    
    if success:
        console.print(Panel.fit(
            "Terraform destroy completed successfully",
            title="Success",
            border_style="green",
        ))
    else:
        console.print(Panel.fit(
            "Terraform destroy failed. Check the logs for details.",
            title="Error",
            border_style="red",
        ))


@app.command("output")
def terraform_output(
    profile_name: Optional[str] = typer.Option(
        None, "--profile", "-p", help="Profile to use for Terraform output"
    ),
    output_name: Optional[str] = typer.Option(
        None, "--name", "-n", help="Specific output to retrieve"
    ),
    json_format: bool = typer.Option(
        False, "--json", "-j", help="Output in JSON format"
    ),
):
    """
    Show Terraform outputs for the specified profile
    """
    # Determine which profile to use
    config = get_config()
    if not profile_name:
        profile_name = config.get("default_profile")
        
    if not profile_name:
        console.print("No profile specified and no default profile set", style="red")
        return
    
    # Check if profile exists
    profile_path = os.path.join(get_config_dir(), "profiles", f"{profile_name}.yaml")
    if not os.path.exists(profile_path):
        console.print(f"Profile [bold red]{profile_name}[/bold red] not found", style="red")
        return
    
    console.print(f"Retrieving Terraform outputs for profile: [bold cyan]{profile_name}[/bold cyan]")
    
    # Run terraform output
    success = run_terraform_command(
        profile_name=profile_name,
        command="output",
        output_name=output_name,
        json_format=json_format,
    )
    
    if not success:
        console.print(Panel.fit(
            "Failed to retrieve Terraform outputs. Check the logs for details.",
            title="Error",
            border_style="red",
        ))
