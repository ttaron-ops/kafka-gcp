import os
import time
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn

from kafka_cli.utils.config import get_config, get_config_dir
from kafka_cli.utils.interactive import safe_text, safe_typer_confirm
from kafka_cli.utils.terraform import run_terraform_command

app = typer.Typer(help="Manage Terraform operations for Kafka clusters")
console = Console()


@app.command("plan")
def terraform_plan(
    profile_name: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use for Terraform plan"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Save plan output to file"),
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
        console.print(
            Panel.fit(
                "Terraform plan completed successfully",
                title="Success",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel.fit(
                "Terraform plan failed. Check the logs for details.",
                title="Error",
                border_style="red",
            )
        )


@app.command("apply")
def terraform_apply(
    profile_name: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use for Terraform apply"),
    auto_approve: bool = typer.Option(False, "--auto-approve", "-y", help="Auto-approve Terraform apply"),
    test: bool = typer.Option(False, "--test", help="Apply test.tf file instead of regular configuration"),
):
    """
    Apply Terraform configuration for the specified profile
    """
    if test:
        # Apply test.tf file directly
        console.print("Applying test.tf Terraform configuration")

        # Get terraform directory
        terraform_dir = os.path.join(get_config_dir(), "infra")
        os.makedirs(terraform_dir, exist_ok=True)

        # Check if test.tf exists
        # test_tf_path = os.path.join(terraform_dir, "test.tf")
        if not os.path.exists(terraform_dir):
            console.print(f"[bold red]Error:[/bold red] .tf files not found at {terraform_dir}")
            console.print("Create a test.tf file in the terraform directory first.")
            return

        # Confirm apply if not auto-approved
        if not auto_approve:
            console.print("[bold yellow]Warning:[/bold yellow] This operation will apply the test.tf file in your GCP account.")
            if not safe_typer_confirm("Do you want to continue?"):
                console.print("Operation cancelled", style="yellow")
                return

        # Display a loading bar for 1 minute (60 seconds)
        console.print("Preparing environment for Terraform apply...")

        # Create a progress bar that will run for 60 seconds
        with Progress(
            TextColumn("[bold blue]Loading...", justify="right"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            # Create a task that will run for 60 seconds (60 * 100 steps)
            task = progress.add_task("[cyan]Initializing...", total=100)

            # Update the progress bar over 60 seconds
            for i in range(100):
                # Sleep for 0.6 seconds (60 seconds total / 100 steps)
                time.sleep(0.6)
                # Update the progress description periodically
                if i < 25:
                    progress.update(task, description="[cyan]Initializing Terraform environment...", advance=1)
                elif i < 50:
                    progress.update(task, description="[cyan]Loading modules...", advance=1)
                elif i < 75:
                    progress.update(task, description="[cyan]Preparing providers...", advance=1)
                else:
                    progress.update(task, description="[cyan]Finalizing setup...", advance=1)

        console.print("[bold green]Preparation complete![/bold green]")

        # Run terraform apply on test.tf
        import shutil
        import subprocess

        # Check if terraform is installed
        if not shutil.which("terraform"):
            console.print("[bold red]Error:[/bold red] Terraform not found in PATH")
            console.print("Please install Terraform from https://www.terraform.io/downloads.html")
            return

        # Initialize Terraform if needed
        console.print("Initializing Terraform...")
        init_result = subprocess.run(
            ["terraform", "init"],
            cwd=terraform_dir,
            capture_output=True,
            text=True,
        )

        if init_result.returncode != 0:
            console.print("[bold red]Error:[/bold red] Terraform initialization failed")
            console.print(init_result.stderr)
            return

        # Apply the test.tf file
        console.print("Applying test.tf configuration...")

        # Construct apply command with auto-approve if specified
        apply_cmd = ["terraform", f"-chdir={terraform_dir}", "apply"]
        if auto_approve:
            apply_cmd.append("-auto-approve")
        try:
            # Run the apply command and stream output to console
            process = subprocess.Popen(
                apply_cmd,
                cwd=terraform_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            # Stream output
            for line in process.stdout:
                console.print(line.rstrip())

            # Wait for process to complete
            return_code = process.wait()

            if return_code == 0:
                console.print(
                    Panel.fit(
                        "test.tf applied successfully",
                        title="Success",
                        border_style="green",
                    )
                )
            else:
                console.print(
                    Panel.fit(
                        "Failed to apply test.tf. See output above for details.",
                        title="Error",
                        border_style="red",
                    )
                )

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] Failed to run Terraform apply: {str(e)}")
            return

        return

    # Regular profile-based apply
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
        console.print(
            Panel.fit(
                "Terraform apply completed successfully",
                title="Success",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel.fit(
                "Terraform apply failed. Check the logs for details.",
                title="Error",
                border_style="red",
            )
        )


@app.command("destroy")
def terraform_destroy(
    profile_name: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use for Terraform destroy"),
    auto_approve: bool = typer.Option(False, "--auto-approve", "-y", help="Auto-approve Terraform destroy"),
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

        confirmation = safe_text("Type the profile name to confirm destruction:", default="")

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
        console.print(
            Panel.fit(
                "Terraform destroy completed successfully",
                title="Success",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel.fit(
                "Terraform destroy failed. Check the logs for details.",
                title="Error",
                border_style="red",
            )
        )


@app.command("output")
def terraform_output(
    profile_name: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use for Terraform output"),
    output_name: Optional[str] = typer.Option(None, "--name", "-n", help="Specific output to retrieve"),
    json_format: bool = typer.Option(False, "--json", "-j", help="Output in JSON format"),
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
        console.print(
            Panel.fit(
                "Failed to retrieve Terraform outputs. Check the logs for details.",
                title="Error",
                border_style="red",
            )
        )
