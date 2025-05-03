"""
Google Cloud Platform provider implementation.
Encapsulates all GCP-specific functionality.
"""
import json
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional

from rich.console import Console

from kafka_cli.core.cloud.provider import CloudProvider

console = Console()


class GCPProvider(CloudProvider):
    """Google Cloud Platform provider implementation"""

    def __init__(self):
        self._authenticated = None
        self._active_project = None

    def is_gcloud_installed(self) -> bool:
        """Check if gcloud CLI is installed and available in PATH"""
        return shutil.which("gcloud") is not None

    def is_authenticated(self) -> bool:
        """Check if user is authenticated with GCP"""
        if self._authenticated is not None:
            return self._authenticated

        try:
            if not self.is_gcloud_installed():
                console.print("[bold red]Error:[/bold red] Google Cloud SDK (gcloud) is not installed or not in your PATH.")
                console.print("Please install the Google Cloud SDK from: [link]https://cloud.google.com/sdk/docs/install[/link]")
                self._authenticated = False
                return False

            result = subprocess.run(["gcloud", "auth", "list", "--format", "json"], capture_output=True, text=True, check=True)

            auth_list = json.loads(result.stdout)
            if not auth_list:
                console.print("[bold red]No active GCP authentication found.[/bold red]")
                console.print("Please run [bold]gcloud auth login[/bold] to authenticate.")
                self._authenticated = False
                return False

            active_account = next((acc for acc in auth_list if acc.get("status") == "ACTIVE"), None)
            if active_account:
                console.print(f"[bold green]Authenticated as:[/bold green] {active_account.get('account')}")
                self._authenticated = True
                return True
            else:
                console.print("[bold red]No active GCP authentication found.[/bold red]")
                console.print("Please run [bold]gcloud auth login[/bold] to authenticate.")
                self._authenticated = False
                return False

        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Error checking GCP authentication:[/bold red] {str(e)}")
            console.print("Please ensure gcloud CLI is installed and properly configured.")
            self._authenticated = False
            return False
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            self._authenticated = False
            return False

    def get_active_project(self) -> Optional[str]:
        """Get the currently active GCP project"""
        if self._active_project:
            return self._active_project

        try:
            if not self.is_gcloud_installed():
                console.print("[bold yellow]Cannot determine active GCP project:[/bold yellow] Google Cloud SDK not installed.")
                return None

            result = subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True, check=True)

            project_id = result.stdout.strip()
            if not project_id:
                console.print("[bold yellow]No active GCP project set.[/bold yellow]")
                console.print("Please run [bold]gcloud config set project PROJECT_ID[/bold] to set a project.")
                return None

            self._active_project = project_id
            return project_id

        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Error getting active GCP project:[/bold red] {str(e)}")
            return None
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            return None

    def list_configurations(self) -> List[Dict]:
        """List all available GCP configurations and mark the active one"""
        try:
            if not self.is_gcloud_installed():
                console.print("[bold yellow]Cannot list GCP configurations:[/bold yellow] Google Cloud SDK not installed.")
                return []

            result = subprocess.run(
                ["gcloud", "config", "configurations", "list", "--format", "json"], capture_output=True, text=True, check=True
            )

            configurations = json.loads(result.stdout)
            return configurations

        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Error listing GCP configurations:[/bold red] {str(e)}")
            return []
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            return []

    def activate_configuration(self, config_name: str) -> bool:
        """Activate a specific GCP configuration"""
        try:
            if not self.is_gcloud_installed():
                console.print("[bold yellow]Cannot activate GCP configuration:[/bold yellow] Google Cloud SDK not installed.")
                return False

            subprocess.run(["gcloud", "config", "configurations", "activate", config_name], check=True)
            console.print(f"[bold green]Activated GCP configuration:[/bold green] {config_name}")

            # Clear cached project as it may have changed
            self._active_project = None

            return True

        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Error activating GCP configuration:[/bold red] {str(e)}")
            return False
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            return False

    def list_regions(self) -> List[Dict[str, Any]]:
        """List available GCP regions"""
        try:
            if not self.is_authenticated():
                # Return mock data if not authenticated
                return [
                    {"name": "us-central1", "description": "Iowa, North America"},
                    {"name": "us-east1", "description": "South Carolina, North America"},
                    {"name": "us-west1", "description": "Oregon, North America"},
                    {"name": "europe-west1", "description": "Belgium, Europe"},
                    {"name": "asia-east1", "description": "Taiwan, Asia"},
                ]

            project_id = self.get_active_project()
            if not project_id:
                return []

            result = subprocess.run(
                ["gcloud", "compute", "regions", "list", "--format", "json", "--project", project_id],
                capture_output=True,
                text=True,
                check=True,
            )

            regions = json.loads(result.stdout)
            return [{"name": r["name"], "description": r.get("description", "")} for r in regions]

        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Error listing GCP regions:[/bold red] {str(e)}")
            return []
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            return []

    def get_zones_for_region(self, region: str) -> List[str]:
        """Get available zones for a GCP region"""
        try:
            if not self.is_authenticated():
                # Return mock data if not authenticated
                return [f"{region}-a", f"{region}-b", f"{region}-c"]

            project_id = self.get_active_project()
            if not project_id:
                return []

            result = subprocess.run(
                ["gcloud", "compute", "zones", "list", "--filter", f"region:{region}", "--format", "json", "--project", project_id],
                capture_output=True,
                text=True,
                check=True,
            )

            zones = json.loads(result.stdout)
            return [z["name"] for z in zones]

        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Error listing zones for region {region}:[/bold red] {str(e)}")
            # Fallback to default zone pattern
            return [f"{region}-a", f"{region}-b", f"{region}-c"]
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            return [f"{region}-a", f"{region}-b", f"{region}-c"]

    def list_networks(self) -> List[Dict[str, Any]]:
        """List available VPC networks in GCP"""
        try:
            if not self.is_authenticated():
                # Return mock data if not authenticated
                return [
                    {"name": "default", "description": "Default network"},
                    {"name": "custom-vpc", "description": "Custom VPC network"},
                ]

            project_id = self.get_active_project()
            if not project_id:
                return []

            result = subprocess.run(
                ["gcloud", "compute", "networks", "list", "--format", "json", "--project", project_id],
                capture_output=True,
                text=True,
                check=True,
            )

            networks = json.loads(result.stdout)
            return [{"name": n["name"], "description": n.get("description", "")} for n in networks]

        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Error listing GCP networks:[/bold red] {str(e)}")
            return []
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            return []

    def list_subnets(self, network_name: str) -> List[Dict[str, Any]]:
        """List available subnets for a VPC network in GCP"""
        try:
            if not self.is_authenticated():
                # Return mock data if not authenticated
                return [
                    {"name": f"{network_name}-subnet-1", "region": "us-central1", "ipCidrRange": "10.0.0.0/24"},
                    {"name": f"{network_name}-subnet-2", "region": "us-east1", "ipCidrRange": "10.0.1.0/24"},
                ]

            project_id = self.get_active_project()
            if not project_id:
                return []

            result = subprocess.run(
                [
                    "gcloud",
                    "compute",
                    "networks",
                    "subnets",
                    "list",
                    "--filter",
                    f"network:{network_name}",
                    "--format",
                    "json",
                    "--project",
                    project_id,
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            subnets = json.loads(result.stdout)
            return [{"name": s["name"], "region": s["region"].split("/")[-1], "ipCidrRange": s["ipCidrRange"]} for s in subnets]

        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Error listing subnets for network {network_name}:[/bold red] {str(e)}")
            return []
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            return []

    def list_security_groups(self) -> List[Dict[str, Any]]:
        """List available firewall rules in GCP"""
        try:
            if not self.is_authenticated():
                # Return mock data if not authenticated
                return [
                    {"name": "default-allow-internal", "network": "default", "direction": "INGRESS"},
                    {"name": "default-allow-ssh", "network": "default", "direction": "INGRESS"},
                ]

            project_id = self.get_active_project()
            if not project_id:
                return []

            result = subprocess.run(
                ["gcloud", "compute", "firewall-rules", "list", "--format", "json", "--project", project_id],
                capture_output=True,
                text=True,
                check=True,
            )

            firewall_rules = json.loads(result.stdout)
            return [{"name": f["name"], "network": f["network"].split("/")[-1], "direction": f["direction"]} for f in firewall_rules]

        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Error listing GCP firewall rules:[/bold red] {str(e)}")
            return []
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            return []

    def estimate_costs(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate costs for a given GCP configuration"""
        # This is a simple cost estimation function
        # In a real implementation, this would use the GCP Pricing API

        cost_map = {
            "e2-standard-2": 0.067,  # hourly rate
            "e2-standard-4": 0.134,
            "e2-standard-8": 0.268,
            "e2-standard-16": 0.537,
            "n2-standard-2": 0.0971,
            "n2-standard-4": 0.1942,
            "n2-standard-8": 0.3884,
            "n2-standard-16": 0.7768,
            "pd-standard": 0.040,  # per GB per month
            "pd-balanced": 0.100,
            "pd-ssd": 0.170,
        }

        try:
            # Extract relevant configuration
            broker_count = config.get("kafka", {}).get("broker_count", 3)
            machine_type = config.get("kafka", {}).get("machine_type", "e2-standard-2")
            disk_type = config.get("kafka", {}).get("disk_type", "pd-standard")
            disk_size = config.get("kafka", {}).get("disk_size_gb", 100)

            # Calculate instance costs
            instance_hourly_rate = cost_map.get(machine_type, 0.067)
            instance_monthly_cost = instance_hourly_rate * 24 * 30 * broker_count

            # Calculate disk costs
            disk_gb_monthly_rate = cost_map.get(disk_type, 0.040)
            disk_monthly_cost = disk_gb_monthly_rate * disk_size * broker_count

            # Calculate network costs (rough estimate)
            network_monthly_cost = 0.01 * 1000  # Assuming 1TB of data transfer

            # Total monthly cost
            total_monthly_cost = instance_monthly_cost + disk_monthly_cost + network_monthly_cost

            return {
                "estimate": {
                    "currency": "USD",
                    "monthly": {
                        "total": round(total_monthly_cost, 2),
                        "compute": round(instance_monthly_cost, 2),
                        "storage": round(disk_monthly_cost, 2),
                        "network": round(network_monthly_cost, 2),
                    },
                    "hourly": round(total_monthly_cost / (24 * 30), 2),
                },
                "breakdown": {
                    "instances": {"type": machine_type, "count": broker_count, "rate": instance_hourly_rate},
                    "disks": {"type": disk_type, "size_gb": disk_size, "count": broker_count, "rate": disk_gb_monthly_rate},
                },
            }

        except Exception as e:
            console.print(f"[bold red]Error estimating costs:[/bold red] {str(e)}")
            return {"error": str(e)}

    def setup_state_storage(self, bucket_name: str, prefix: str) -> bool:
        """Set up GCS bucket for Terraform state storage"""
        try:
            if not self.is_authenticated():
                console.print("[bold yellow]Cannot set up Terraform backend:[/bold yellow] Not authenticated with GCP.")
                return False

            project_id = self.get_active_project()
            if not project_id:
                console.print("[bold yellow]Cannot set up Terraform backend:[/bold yellow] No active GCP project.")
                return False

            # Check if bucket exists
            check_result = subprocess.run(["gsutil", "ls", "-b", f"gs://{bucket_name}"], capture_output=True, text=True)

            if check_result.returncode != 0:
                # Create the bucket if it doesn't exist
                console.print(f"Creating GCS bucket for Terraform state: [cyan]gs://{bucket_name}[/cyan]")
                create_result = subprocess.run(
                    ["gsutil", "mb", "-p", project_id, f"gs://{bucket_name}"], capture_output=True, text=True
                )

                if create_result.returncode != 0:
                    console.print(f"[bold red]Failed to create bucket:[/bold red] {create_result.stderr}")
                    return False

                # Enable versioning for better state management
                subprocess.run(["gsutil", "versioning", "set", "on", f"gs://{bucket_name}"], capture_output=True, text=True)
            else:
                console.print(f"Using existing GCS bucket for Terraform state: [cyan]gs://{bucket_name}[/cyan]")

            # Generate backend configuration
            backend_config = f"""
terraform {{
  backend "gcs" {{
    bucket  = "{bucket_name}"
    prefix  = "{prefix}"
  }}
}}
"""

            # Save backend configuration
            backend_path = os.path.join(os.getcwd(), "backend.tf")
            with open(backend_path, "w") as f:
                f.write(backend_config)

            console.print(f"Terraform backend configuration saved to: [cyan]{backend_path}[/cyan]")
            return True

        except Exception as e:
            console.print(f"[bold red]Error setting up Terraform backend:[/bold red] {str(e)}")
            return False
