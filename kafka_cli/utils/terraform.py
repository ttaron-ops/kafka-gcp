import json
import os
import shutil
import subprocess
from typing import Any, Dict, Optional, Union, cast

from rich.console import Console

from kafka_cli.core.errors import CommandError, ConfigurationError, ErrorHandler, ResourceError
from kafka_cli.utils.config import get_config_dir

console = Console()


def generate_terraform_vars(config: Dict[str, Any], dry_run: bool = False) -> bool:
    """
    Generate Terraform variables file from the configuration dictionary

    Args:
        config: Configuration dictionary containing deployment settings
        dry_run: If True, only print what would be generated without writing files

    Returns:
        bool: True if successful, False otherwise

    Raises:
        ConfigurationError: If there's an issue with the configuration or file operations
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

        # Validate critical values
        if not variables["gcp_project_id"]:
            raise ConfigurationError(
                "Missing GCP project ID in configuration",
                help_text="Set your GCP project ID using the 'kafka-cli config set gcp.project_id PROJECT_ID' command",
            )

        # Generate tfvars file
        tfvars_file = os.path.join(terraform_dir, "terraform.tfvars.json")

        if dry_run:
            console.print("\n[bold]Generated Terraform variables (dry run):[/bold]")
            console.print(json.dumps(variables, indent=2), highlight=True)
            return True

        with open(tfvars_file, "w") as f:
            json.dump(variables, f, indent=2)

        console.print(f"Terraform variables written to: [cyan]{tfvars_file}[/cyan]")

        # Ensure Terraform template files are copied to the terraform directory
        copy_terraform_templates(terraform_dir)

        return True

    except ConfigurationError:
        # Just reraise ConfigurationError as it will be handled by the caller
        raise
    except OSError as e:
        err_msg = f"Failed to generate Terraform files: {str(e)}"
        ErrorHandler().handle_exception(ConfigurationError(err_msg, help_text="Check file system permissions or free disk space"))
        return False
    except Exception as e:
        err_msg = f"Error generating Terraform variables: {str(e)}"
        ErrorHandler().handle_exception(ConfigurationError(err_msg))
        return False


def copy_terraform_templates(terraform_dir: str) -> bool:
    """
    Copy Terraform template files to the terraform directory

    Args:
        terraform_dir: Target directory to copy template files into

    Returns:
        bool: True if successful, False otherwise

    Raises:
        ConfigurationError: If there's an issue copying the files
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
                with open(file_path, "w") as f:
                    f.write(f"# Placeholder for {file}\n# This would contain the actual Terraform code in a real implementation\n")

        return True

    except OSError as e:
        err_msg = f"Failed to create Terraform template files: {str(e)}"
        ErrorHandler().handle_exception(ConfigurationError(err_msg, help_text="Check file system permissions or free disk space"))
        return False
    except Exception as e:
        err_msg = f"Error copying Terraform templates: {str(e)}"
        ErrorHandler().handle_exception(ConfigurationError(err_msg))
        return False


def run_terraform_command(
    profile_name: str,
    command: str,
    auto_approve: bool = False,
    output_file: Optional[str] = None,
    output_name: Optional[str] = None,
    json_format: bool = False,
) -> Union[bool, Dict[str, Any]]:
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
        Union[bool, Dict[str, Any]]: Boolean success status, or dictionary of outputs for output command

    Raises:
        CommandError: If terraform command fails
        ConfigurationError: If terraform is not installed or configuration is invalid
    """
    try:
        # Check if terraform is installed
        if not shutil.which("terraform"):
            raise ConfigurationError(
                "Terraform not found in PATH", help_text="Please install Terraform from https://www.terraform.io/downloads.html"
            )

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
            raise CommandError(
                "Terraform initialization failed",
                command="terraform init",
                details={"stderr": init_result.stderr},
                help_text="Check network connectivity and permissions",
            )

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
            raise CommandError(
                "Terraform command failed",
                command=" ".join(cmd),
                details={"stderr": process.stderr, "return_code": process.returncode},
                help_text="Check the error message and your configuration",
            )

        # For output command with json format, return the parsed JSON
        if command == "output" and json_format and process.stdout:
            try:
                return cast(Dict[str, Any], json.loads(process.stdout))
            except json.JSONDecodeError:
                ErrorHandler().handle_exception(CommandError("Failed to parse Terraform output JSON", command=" ".join(cmd)))
                return {}

        return True

    except (ConfigurationError, CommandError, ResourceError):
        # Just reraise these errors as they will be handled by the caller
        raise
    except subprocess.SubprocessError as e:
        err_msg = f"Failed to execute Terraform command: {str(e)}"
        ErrorHandler().handle_exception(CommandError(err_msg, command=command))
        return False
    except Exception as e:
        err_msg = f"Error executing Terraform command: {str(e)}"
        ErrorHandler().handle_exception(CommandError(err_msg, command=command))
        return False


def get_terraform_output(profile_name: str, output_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get the Terraform outputs for a profile

    Args:
        profile_name: Name of the profile to get outputs for
        output_name: Specific output to retrieve, or None for all outputs

    Returns:
        Dict[str, Any]: Dictionary containing the Terraform outputs
    """
    try:
        result = run_terraform_command(profile_name=profile_name, command="output", json_format=True, output_name=output_name)

        if isinstance(result, dict):
            return result
        return {}

    except Exception as e:
        err_msg = f"Failed to get Terraform outputs: {str(e)}"
        ErrorHandler().handle_exception(CommandError(err_msg, command="terraform output"))
        return {}
