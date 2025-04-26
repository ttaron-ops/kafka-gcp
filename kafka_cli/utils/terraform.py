import os
import json
import shutil
import subprocess
from typing import Optional, Dict, Any, List
from rich.console import Console

from kafka_cli.utils.config import get_config, get_config_dir

console = Console()

def generate_terraform_vars(config: Dict[str, Any], dry_run: bool = False) -> bool:
    """
    Generate Terraform variables file from the configuration dictionary
    
    Args:
        config: Configuration dictionary
        dry_run: If True, only print what would be generated
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create the terraform directory if it doesn't exist
        terraform_dir = os.path.join(get_config_dir(), "terraform")
        os.makedirs(terraform_dir, exist_ok=True)
        
        # Prepare the variables dictionary
        variables = {
            # GCP configuration
            "gcp_project_id": config.get("gcp", {}).get("project_id"),
            "gcp_region": config.get("gcp", {}).get("region", "us-central1"),
            "gcp_zone": config.get("gcp", {}).get("zone", "us-central1-a"),
            
            # Network configuration
            "network_name": config.get("networking", {}).get("network_name", "kafka-network"),
            "network_cidr": config.get("networking", {}).get("network_cidr", "10.0.0.0/16"),
            "subnet_cidr": config.get("networking", {}).get("subnet_cidr", "10.0.1.0/24"),
            "enable_vpc_peering": config.get("networking", {}).get("enable_peering", False),
            "peering_network": config.get("networking", {}).get("peering_network", ""),
            
            # Kafka configuration
            "kafka_broker_count": config.get("kafka", {}).get("broker_count", 3),
            "kafka_machine_type": config.get("kafka", {}).get("machine_type", "e2-standard-4"),
            "kafka_disk_size_gb": config.get("kafka", {}).get("disk_size", 100),
            "kafka_version": config.get("kafka", {}).get("kafka_version", "3.4.0"),
            "kafka_kraft_mode": config.get("kafka", {}).get("kraft_mode", True),
            
            # Add-ons configuration
            "addons": {
                "kafka_ui": config.get("addons", {}).get("kafka_ui", False),
                "prometheus": config.get("addons", {}).get("prometheus", False),
                "kafka_exporter": config.get("addons", {}).get("kafka_exporter", False),
                "grafana": config.get("addons", {}).get("grafana", False),
                "schema_registry": config.get("addons", {}).get("schema_registry", False),
            },
            "addons_deployment_target": config.get("addons", {}).get("deployment_target", "GCP Compute Engine VM"),
            "kubeconfig_path": config.get("addons", {}).get("kubeconfig_path", "~/.kube/config"),
        }
        
        # Generate tfvars file
        tfvars_file = os.path.join(terraform_dir, "terraform.tfvars.json")
        
        if dry_run:
            console.print("\n[bold]Generated Terraform variables (dry run):[/bold]")
            console.print(json.dumps(variables, indent=2), highlight=True)
            return True
        
        with open(tfvars_file, 'w') as f:
            json.dump(variables, f, indent=2)
        
        console.print(f"Terraform variables written to: [cyan]{tfvars_file}[/cyan]")
        
        # Ensure Terraform template files are copied to the terraform directory
        copy_terraform_templates(terraform_dir)
        
        return True
    
    except Exception as e:
        console.print(f"Error generating Terraform variables: {str(e)}", style="red")
        return False


def copy_terraform_templates(terraform_dir: str) -> bool:
    """
    Copy Terraform template files to the terraform directory
    
    Args:
        terraform_dir: Target directory
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # In a real implementation, this would copy the Terraform template files
        # from a package directory to the user's terraform directory
        
        # For demonstration purposes, we'll create placeholder files
        placeholder_files = [
            "main.tf",
            "variables.tf",
            "outputs.tf",
            "gcp.tf",
            "kafka.tf",
            "addons.tf",
        ]
        
        for file in placeholder_files:
            file_path = os.path.join(terraform_dir, file)
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    f.write(f"# Placeholder for {file}\n# This would contain the actual Terraform code in a real implementation\n")
        
        return True
    
    except Exception as e:
        console.print(f"Error copying Terraform templates: {str(e)}", style="red")
        return False


def run_terraform_command(
    profile_name: str,
    command: str,
    auto_approve: bool = False,
    output_file: Optional[str] = None,
    output_name: Optional[str] = None,
    json_format: bool = False,
) -> bool:
    """
    Run a Terraform command for the specified profile
    
    Args:
        profile_name: Name of the profile to use
        command: Terraform command to run (init, plan, apply, destroy, output)
        auto_approve: Whether to auto-approve apply/destroy commands
        output_file: Path to save plan output to
        output_name: Specific output to retrieve (for output command)
        json_format: Whether to output in JSON format (for output command)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if terraform is installed
        if not shutil.which("terraform"):
            console.print("Terraform not found. Please install Terraform.", style="red")
            return False
        
        # Get terraform directory
        terraform_dir = os.path.join(get_config_dir(), "terraform")
        os.makedirs(terraform_dir, exist_ok=True)
        
        # Initialize Terraform if not already initialized
        init_result = subprocess.run(
            ["terraform", "init"],
            cwd=terraform_dir,
            capture_output=True,
            text=True,
        )
        
        if init_result.returncode != 0:
            console.print("Terraform initialization failed:", style="red")
            console.print(init_result.stderr)
            return False
        
        # Prepare the command arguments
        cmd = ["terraform", command]
        
        # Add command-specific arguments
        if command == "plan" and output_file:
            cmd.extend(["-out", output_file])
        
        if command in ["apply", "destroy"] and auto_approve:
            cmd.append("-auto-approve")
        
        if command == "output":
            if output_name:
                cmd.append(output_name)
            if json_format:
                cmd.append("-json")
        
        # Run the command
        console.print(f"Running: [bold]{' '.join(cmd)}[/bold]")
        
        process = subprocess.run(
            cmd,
            cwd=terraform_dir,
            capture_output=True,
            text=True,
        )
        
        # Display the output
        if process.stdout:
            console.print(process.stdout)
        
        if process.returncode != 0:
            console.print("Terraform command failed:", style="red")
            console.print(process.stderr)
            return False
        
        return True
    
    except Exception as e:
        console.print(f"Error running Terraform command: {str(e)}", style="red")
        return False
