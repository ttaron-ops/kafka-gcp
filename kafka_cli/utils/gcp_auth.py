import json
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Union, cast

from rich.console import Console

from kafka_cli.core.errors import AuthenticationError, CommandError, ConfigurationError, ErrorHandler, ErrorSeverity

console = Console()


def is_gcloud_installed() -> bool:
    """
    Check if gcloud CLI is installed and available in PATH

    Returns:
        bool: True if gcloud is installed, False otherwise
    """
    return shutil.which("gcloud") is not None


def check_gcp_auth() -> bool:
    """
    Check if user is authenticated with GCP

    Returns:
        bool: True if authenticated, False otherwise

    Raises:
        AuthenticationError: If there's an issue with GCP authentication
    """
    try:
        if not is_gcloud_installed():
            raise AuthenticationError(
                "Google Cloud SDK (gcloud) is not installed or not in your PATH",
                help_text="Please install the Google Cloud SDK from: https://cloud.google.com/sdk/docs/install",
            )

        result = subprocess.run(["gcloud", "auth", "list", "--format", "json"], capture_output=True, text=True, check=True)

        auth_list = json.loads(result.stdout)
        if not auth_list:
            raise AuthenticationError(
                "No active GCP authentication found", help_text="Please run 'gcloud auth login' to authenticate"
            )

        active_account = next((acc for acc in auth_list if acc.get("status") == "ACTIVE"), None)
        if active_account:
            console.print(f"[bold green]Authenticated as:[/bold green] {active_account.get('account')}")
            return True
        else:
            raise AuthenticationError(
                "No active GCP authentication found", help_text="Please run 'gcloud auth login' to authenticate"
            )

    except subprocess.CalledProcessError as e:
        error_msg = f"Error checking GCP authentication: {str(e)}"
        ErrorHandler().handle_exception(
            AuthenticationError(error_msg, help_text="Please ensure gcloud CLI is installed and properly configured")
        )
        return False
    except json.JSONDecodeError as e:
        error_msg = f"Invalid response from gcloud: {str(e)}"
        ErrorHandler().handle_exception(AuthenticationError(error_msg))
        return False
    except AuthenticationError:
        # Just re-raise authentication errors to be handled by caller
        raise
    except Exception as e:
        error_msg = f"Unexpected error during authentication check: {str(e)}"
        ErrorHandler().handle_exception(AuthenticationError(error_msg))
        return False


def get_active_project() -> Optional[str]:
    """
    Get the currently active GCP project

    Returns:
        Optional[str]: Project ID if available, None otherwise

    Raises:
        ConfigurationError: If there's an issue getting the project info
    """
    try:
        if not is_gcloud_installed():
            error_msg = "Cannot determine active GCP project: Google Cloud SDK not installed"
            ErrorHandler().handle_exception(ConfigurationError(error_msg, severity=ErrorSeverity.WARNING))
            return None

        result = subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True, check=True)

        project_id = result.stdout.strip()
        if not project_id:
            error_msg = "No active GCP project set"
            ErrorHandler().handle_exception(
                ConfigurationError(
                    error_msg,
                    severity=ErrorSeverity.WARNING,
                    help_text="Please run 'gcloud config set project PROJECT_ID' to set a project",
                )
            )
            return None

        console.print(f"[bold green]Active GCP project:[/bold green] {project_id}")
        return project_id

    except subprocess.CalledProcessError as e:
        error_msg = f"Error getting active GCP project: {str(e)}"
        ErrorHandler().handle_exception(ConfigurationError(error_msg))
        return None
    except ConfigurationError:
        # Just re-raise configuration errors to be handled by caller
        raise
    except Exception as e:
        error_msg = f"Unexpected error getting GCP project: {str(e)}"
        ErrorHandler().handle_exception(ConfigurationError(error_msg))
        return None


def list_gcp_configurations() -> List[Dict[str, Any]]:
    """
    List all available GCP configurations and mark the active one

    Returns:
        List[Dict[str, Any]]: List of GCP configurations, each as a dictionary
    """
    try:
        if not is_gcloud_installed():
            error_msg = "Cannot list GCP configurations: Google Cloud SDK not installed"
            ErrorHandler().handle_exception(ConfigurationError(error_msg, severity=ErrorSeverity.WARNING))
            return []

        result = subprocess.run(
            ["gcloud", "config", "configurations", "list", "--format", "json"], capture_output=True, text=True, check=True
        )

        configurations = json.loads(result.stdout)
        return cast(List[Dict[str, Any]], configurations)

    except subprocess.CalledProcessError as e:
        error_msg = f"Error listing GCP configurations: {str(e)}"
        ErrorHandler().handle_exception(CommandError(error_msg, command="gcloud config configurations list"))
        return []
    except json.JSONDecodeError as e:
        error_msg = f"Invalid response from gcloud: {str(e)}"
        ErrorHandler().handle_exception(CommandError(error_msg))
        return []
    except Exception as e:
        error_msg = f"Unexpected error listing GCP configurations: {str(e)}"
        ErrorHandler().handle_exception(CommandError(error_msg))
        return []


def activate_gcp_configuration(config_name: str) -> bool:
    """
    Activate a specific GCP configuration

    Args:
        config_name: Name of the configuration to activate

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not is_gcloud_installed():
            error_msg = "Cannot activate GCP configuration: Google Cloud SDK not installed"
            ErrorHandler().handle_exception(ConfigurationError(error_msg, severity=ErrorSeverity.WARNING))
            return False

        subprocess.run(["gcloud", "config", "configurations", "activate", config_name], capture_output=True, text=True, check=True)

        console.print(f"[bold green]Activated GCP configuration:[/bold green] {config_name}")
        return True

    except subprocess.CalledProcessError as e:
        error_msg = f"Error activating GCP configuration: {str(e)}"
        ErrorHandler().handle_exception(CommandError(error_msg, command=f"gcloud config configurations activate {config_name}"))
        return False
    except Exception as e:
        error_msg = f"Unexpected error activating GCP configuration: {str(e)}"
        ErrorHandler().handle_exception(CommandError(error_msg))
        return False


def select_gcp_configuration() -> Optional[str]:
    """
    Display available GCP configurations and let the user select one.

    Returns:
        Optional[str]: Project ID of the selected configuration, or None if selection failed
    """
    from kafka_cli.utils.interactive import safe_select

    try:
        if not is_gcloud_installed():
            error_msg = "Cannot select GCP configuration: Google Cloud SDK not installed"
            ErrorHandler().handle_exception(ConfigurationError(error_msg, severity=ErrorSeverity.WARNING))
            return None

        # Get all available configurations
        configurations = list_gcp_configurations()
        if not configurations:
            error_msg = "No GCP configurations found"
            ErrorHandler().handle_exception(
                ConfigurationError(
                    error_msg, severity=ErrorSeverity.WARNING, help_text="Please run 'gcloud init' to set up a configuration"
                )
            )
            return None

        # Mark active configuration and build selection list
        active_config = next((c for c in configurations if c.get("is_active", False)), None)

        # Build options list
        options: List[str] = []
        config_mapping: Dict[str, Dict[str, Any]] = {}

        for config in configurations:
            name = config.get("name", "")
            project = config.get("properties", {}).get("core", {}).get("project", "Not set")
            account = config.get("properties", {}).get("core", {}).get("account", "Not set")

            # Create display option
            is_active = config.get("is_active", False)
            display = f"{name} - Project: {project}, Account: {account}"
            if is_active:
                display += " [ACTIVE]"

            options.append(display)
            config_mapping[display] = config

        # Current project from active config
        current_project = active_config.get("properties", {}).get("core", {}).get("project", "") if active_config else ""

        # Let user select
        console.print("\n[bold]GCP Configuration Selection[/bold]")
        if active_config:
            console.print(f"Currently active: [bold cyan]{active_config.get('name')}[/bold cyan] (Project: {current_project})")

        # If only one configuration and it's active, return its project
        if len(configurations) == 1 and active_config:
            console.print("[bold green]Using the only available GCP configuration.[/bold green]")
            return current_project

        selected = safe_select(
            "Select GCP configuration to use", choices=options, default=next((o for o in options if "[ACTIVE]" in o), None)
        )

        # Activate the selected configuration if it's not already active
        selected_config = config_mapping[selected]
        if not selected_config.get("is_active", False):
            activated = activate_gcp_configuration(selected_config.get("name", ""))
            if not activated:
                return None

        # Return the project ID from the selected configuration
        return selected_config.get("properties", {}).get("core", {}).get("project", "")

    except Exception as e:
        error_msg = f"Error selecting GCP configuration: {str(e)}"
        ErrorHandler().handle_exception(CommandError(error_msg))
        return None


def list_gcp_regions() -> List[str]:
    """
    Get list of available GCP regions

    Returns:
        List[str]: List of GCP region names
    """
    if not is_gcloud_installed():
        error_msg = "Using default regions list: Google Cloud SDK not installed"
        ErrorHandler().handle_exception(ConfigurationError(error_msg, severity=ErrorSeverity.WARNING))
        # Return common regions as fallback
        return ["us-central1", "us-east1", "us-west1", "europe-west1", "asia-east1"]

    try:
        result = subprocess.run(
            ["gcloud", "compute", "regions", "list", "--format", "json"], capture_output=True, text=True, check=True
        )

        regions_data = json.loads(result.stdout)
        return [region.get("name") for region in regions_data if region.get("name")]

    except subprocess.CalledProcessError as e:
        error_msg = f"Error listing GCP regions: {str(e)}"
        ErrorHandler().handle_exception(CommandError(error_msg, command="gcloud compute regions list"))
        # Return common regions as fallback
        return ["us-central1", "us-east1", "us-west1", "europe-west1", "asia-east1"]
    except json.JSONDecodeError:
        error_msg = "Invalid response from gcloud while listing regions"
        ErrorHandler().handle_exception(CommandError(error_msg))
        return ["us-central1", "us-east1", "us-west1", "europe-west1", "asia-east1"]
    except Exception as e:
        error_msg = f"Unexpected error listing GCP regions: {str(e)}"
        ErrorHandler().handle_exception(CommandError(error_msg))
        return ["us-central1", "us-east1", "us-west1", "europe-west1", "asia-east1"]


def get_zones_for_region(region: str) -> List[str]:
    """
    Get availability zones for a specific GCP region

    Args:
        region: GCP region name

    Returns:
        List[str]: List of zone names
    """
    if not is_gcloud_installed():
        error_msg = f"Using default zones for region {region}: Google Cloud SDK not installed"
        ErrorHandler().handle_exception(ConfigurationError(error_msg, severity=ErrorSeverity.WARNING))
        # Return common zones for the region as fallback
        return [f"{region}-a", f"{region}-b", f"{region}-c"]

    try:
        result = subprocess.run(
            ["gcloud", "compute", "zones", "list", "--filter", f"region:{region}", "--format", "json"],
            capture_output=True,
            text=True,
            check=True,
        )

        zones_data = json.loads(result.stdout)
        return [zone.get("name") for zone in zones_data if zone.get("name")]

    except subprocess.CalledProcessError as e:
        error_msg = f"Error listing zones for region {region}: {str(e)}"
        ErrorHandler().handle_exception(CommandError(error_msg, command=f"gcloud compute zones list --filter region:{region}"))
        return [f"{region}-a", f"{region}-b", f"{region}-c"]
    except json.JSONDecodeError:
        error_msg = f"Invalid response from gcloud while listing zones for region {region}"
        ErrorHandler().handle_exception(CommandError(error_msg))
        return [f"{region}-a", f"{region}-b", f"{region}-c"]
    except Exception as e:
        error_msg = f"Unexpected error listing zones for region {region}: {str(e)}"
        ErrorHandler().handle_exception(CommandError(error_msg))
        return [f"{region}-a", f"{region}-b", f"{region}-c"]


def list_gcp_vpcs() -> List[Dict[str, Any]]:
    """
    Get list of VPC networks in the project

    Returns:
        List[Dict[str, Any]]: List of VPC networks
    """
    if not is_gcloud_installed():
        error_msg = "Cannot list VPC networks: Google Cloud SDK not installed"
        ErrorHandler().handle_exception(ConfigurationError(error_msg, severity=ErrorSeverity.WARNING))
        return []

    try:
        result = subprocess.run(
            ["gcloud", "compute", "networks", "list", "--format", "json"], capture_output=True, text=True, check=True
        )

        vpc_data = json.loads(result.stdout)
        return cast(List[Dict[str, Any]], vpc_data)

    except subprocess.CalledProcessError as e:
        error_msg = f"Error listing VPC networks: {str(e)}"
        ErrorHandler().handle_exception(CommandError(error_msg, command="gcloud compute networks list"))
        return []
    except json.JSONDecodeError:
        error_msg = "Invalid response from gcloud while listing VPC networks"
        ErrorHandler().handle_exception(CommandError(error_msg))
        return []
    except Exception as e:
        error_msg = f"Unexpected error listing VPC networks: {str(e)}"
        ErrorHandler().handle_exception(CommandError(error_msg))
        return []


def list_subnets_for_vpc(vpc_name: str) -> List[Dict[str, Any]]:
    """
    Get list of subnets for a specific VPC

    Args:
        vpc_name: Name of the VPC network

    Returns:
        List[Dict[str, Any]]: List of subnets
    """
    if not is_gcloud_installed():
        error_msg = f"Cannot list subnets for VPC {vpc_name}: Google Cloud SDK not installed"
        ErrorHandler().handle_exception(ConfigurationError(error_msg, severity=ErrorSeverity.WARNING))
        return []

    try:
        result = subprocess.run(
            ["gcloud", "compute", "networks", "subnets", "list", "--filter", f"network:{vpc_name}", "--format", "json"],
            capture_output=True,
            text=True,
            check=True,
        )

        subnet_data = json.loads(result.stdout)
        return cast(List[Dict[str, Any]], subnet_data)

    except subprocess.CalledProcessError as e:
        error_msg = f"Error listing subnets for VPC {vpc_name}: {str(e)}"
        ErrorHandler().handle_exception(
            CommandError(error_msg, command=f"gcloud compute networks subnets list --filter network:{vpc_name}")
        )
        return []
    except json.JSONDecodeError:
        error_msg = f"Invalid response from gcloud while listing subnets for VPC {vpc_name}"
        ErrorHandler().handle_exception(CommandError(error_msg))
        return []
    except Exception as e:
        error_msg = f"Unexpected error listing subnets for VPC {vpc_name}: {str(e)}"
        ErrorHandler().handle_exception(CommandError(error_msg))
        return []


def list_security_groups() -> List[Dict[str, Any]]:
    """
    Get list of firewall rules (equivalent to security groups)

    Returns:
        List[Dict[str, Any]]: List of firewall rules
    """
    if not is_gcloud_installed():
        error_msg = "Cannot list firewall rules: Google Cloud SDK not installed"
        ErrorHandler().handle_exception(ConfigurationError(error_msg, severity=ErrorSeverity.WARNING))
        return []

    try:
        result = subprocess.run(
            ["gcloud", "compute", "firewall-rules", "list", "--format", "json"], capture_output=True, text=True, check=True
        )

        firewall_data = json.loads(result.stdout)
        return cast(List[Dict[str, Any]], firewall_data)

    except subprocess.CalledProcessError as e:
        error_msg = f"Error listing firewall rules: {str(e)}"
        ErrorHandler().handle_exception(CommandError(error_msg, command="gcloud compute firewall-rules list"))
        return []
    except json.JSONDecodeError:
        error_msg = "Invalid response from gcloud while listing firewall rules"
        ErrorHandler().handle_exception(CommandError(error_msg))
        return []
    except Exception as e:
        error_msg = f"Unexpected error listing firewall rules: {str(e)}"
        ErrorHandler().handle_exception(CommandError(error_msg))
        return []


def init_terraform_backend(bucket_name: str, prefix: str) -> bool:
    """
    Initialize Terraform backend with GCS bucket

    Args:
        bucket_name: Name of the GCS bucket to use
        prefix: Prefix within the bucket for storing state

    Returns:
        bool: True if successful, False otherwise
    """
    if not is_gcloud_installed():
        error_msg = "Cannot initialize Terraform backend: Google Cloud SDK not installed"
        ErrorHandler().handle_exception(
            ConfigurationError(error_msg, severity=ErrorSeverity.ERROR, help_text="Please install the Google Cloud SDK")
        )
        return False

    try:
        # Check if bucket exists
        check_result = subprocess.run(["gsutil", "ls", f"gs://{bucket_name}"], capture_output=True, text=True)

        # Create bucket if it doesn't exist
        if check_result.returncode != 0:
            console.print(f"Creating GCS bucket for Terraform state: [cyan]{bucket_name}[/cyan]")
            subprocess.run(["gsutil", "mb", f"gs://{bucket_name}"], capture_output=True, text=True, check=True)

            # Enable versioning on the bucket
            console.print("Enabling versioning on the bucket...")
            subprocess.run(["gsutil", "versioning", "set", "on", f"gs://{bucket_name}"], capture_output=True, text=True, check=True)

        # Generate backend configuration
        backend_config = {"terraform": {"backend": {"gcs": {"bucket": bucket_name, "prefix": prefix}}}}

        # Get terraform directory
        terraform_dir = os.path.join(os.path.expanduser("~/.kafka-cli"), "terraform")
        os.makedirs(terraform_dir, exist_ok=True)

        # Write backend configuration
        backend_file = os.path.join(terraform_dir, "backend.tf.json")
        with open(backend_file, "w") as f:
            json.dump(backend_config, f, indent=2)

        console.print(f"Terraform backend configuration written to: [cyan]{backend_file}[/cyan]")
        return True

    except subprocess.CalledProcessError as e:
        error_msg = f"Error initializing Terraform backend: {str(e)}"
        ErrorHandler().handle_exception(CommandError(error_msg, command="gsutil operations"))
        return False
    except Exception as e:
        error_msg = f"Unexpected error initializing Terraform backend: {str(e)}"
        ErrorHandler().handle_exception(CommandError(error_msg))
        return False


def estimate_compute_costs(region: str, instance_type: str, num_instances: int, disk_type: str, disk_size_gb: int) -> Dict[str, Any]:
    """
    Estimate GCP compute costs for the configured cluster.
    This is a simplified estimation and actual costs may vary.

    Args:
        region: GCP region name
        instance_type: GCP machine type
        num_instances: Number of instances
        disk_type: Disk type (pd-standard, pd-ssd)
        disk_size_gb: Disk size in GB

    Returns:
        Dict[str, Any]: Dictionary with cost estimates
    """
    try:
        # Simplified cost estimates (placeholder - would be better to use actual GCP pricing API)
        # These are very rough approximations
        costs: Dict[str, Union[float, Dict[str, Any]]] = {
            "compute": 0.0,
            "storage": 0.0,
            "network": 0.0,
            "total": 0.0,
            "breakdown": {"hourly": {}, "monthly": {}, "yearly": {}},
        }

        # Rough compute costs by machine type (per hour)
        compute_costs = {
            "e2-standard-2": 0.07,
            "e2-standard-4": 0.14,
            "e2-standard-8": 0.28,
            "e2-highmem-2": 0.09,
            "e2-highmem-4": 0.19,
            "e2-highcpu-2": 0.05,
            "e2-highcpu-4": 0.10,
            "n2-standard-2": 0.10,
            "n2-standard-4": 0.19,
            "n2-standard-8": 0.38,
        }

        # Rough disk costs by type (per GB per month)
        disk_costs = {
            "pd-standard": 0.04,
            "pd-ssd": 0.17,
            "pd-balanced": 0.10,
        }

        # Calculate compute cost per hour
        compute_cost_per_hour = compute_costs.get(instance_type, 0.10) * num_instances
        compute_cost_per_month = compute_cost_per_hour * 24 * 30

        # Calculate disk cost per month
        disk_cost_per_month = disk_costs.get(disk_type, 0.04) * disk_size_gb * num_instances

        # Calculate network cost (very simplified estimate)
        network_cost_per_month = 0.10 * num_instances * 30

        # Total monthly cost
        total_cost_per_month = compute_cost_per_month + disk_cost_per_month + network_cost_per_month
        total_cost_per_year = total_cost_per_month * 12

        # Update costs dictionary
        costs["compute"] = compute_cost_per_month
        costs["storage"] = disk_cost_per_month
        costs["network"] = network_cost_per_month
        costs["total"] = total_cost_per_month

        # Add breakdowns
        costs["breakdown"] = {
            "hourly": {
                "compute": compute_cost_per_hour,
                "total": compute_cost_per_hour + (disk_cost_per_month + network_cost_per_month) / (24 * 30),
            },
            "monthly": {
                "compute": compute_cost_per_month,
                "storage": disk_cost_per_month,
                "network": network_cost_per_month,
                "total": total_cost_per_month,
            },
            "yearly": {
                "compute": compute_cost_per_month * 12,
                "storage": disk_cost_per_month * 12,
                "network": network_cost_per_month * 12,
                "total": total_cost_per_year,
            },
        }

        console.print("\n[bold]Estimated GCP Costs (USD)[/bold]")
        console.print(f"Region: {region}, Instance Type: {instance_type}, Count: {num_instances}")
        console.print(f"Disk: {disk_type}, Size: {disk_size_gb}GB per instance")
        console.print(f"[bold]Monthly Estimate:[/bold] ${total_cost_per_month:.2f}")
        console.print(f"[bold]Yearly Estimate:[/bold] ${total_cost_per_year:.2f}")
        console.print("[yellow]Note:[/yellow] This is a simplified estimation. Actual costs may vary.")

        return cast(Dict[str, Any], costs)

    except Exception as e:
        error_msg = f"Error estimating compute costs: {str(e)}"
        ErrorHandler().handle_exception(CommandError(error_msg))
        return {"compute": 0.0, "storage": 0.0, "network": 0.0, "total": 0.0, "error": str(e)}
