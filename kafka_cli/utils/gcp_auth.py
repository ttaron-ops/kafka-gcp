import os
import json
import subprocess
import shutil
from typing import Dict, Optional, Tuple, List
from rich.console import Console

console = Console()

def is_gcloud_installed() -> bool:
    """Check if gcloud CLI is installed and available in PATH"""
    return shutil.which("gcloud") is not None

def check_gcp_auth() -> bool:
    """Check if user is authenticated with GCP"""
    try:
        if not is_gcloud_installed():
            console.print("[bold red]Error:[/bold red] Google Cloud SDK (gcloud) is not installed or not in your PATH.")
            console.print("Please install the Google Cloud SDK from: [link]https://cloud.google.com/sdk/docs/install[/link]")
            return False
            
        result = subprocess.run(
            ["gcloud", "auth", "list", "--format", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        
        auth_list = json.loads(result.stdout)
        if not auth_list:
            console.print("[bold red]No active GCP authentication found.[/bold red]")
            console.print("Please run [bold]gcloud auth login[/bold] to authenticate.")
            return False
            
        active_account = next((acc for acc in auth_list if acc.get("status") == "ACTIVE"), None)
        if active_account:
            console.print(f"[bold green]Authenticated as:[/bold green] {active_account.get('account')}")
            return True
        else:
            console.print("[bold red]No active GCP authentication found.[/bold red]")
            console.print("Please run [bold]gcloud auth login[/bold] to authenticate.")
            return False
            
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error checking GCP authentication:[/bold red] {str(e)}")
        console.print("Please ensure gcloud CLI is installed and properly configured.")
        return False
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return False

def get_active_project() -> Optional[str]:
    """Get the currently active GCP project"""
    try:
        if not is_gcloud_installed():
            console.print("[bold yellow]Cannot determine active GCP project:[/bold yellow] Google Cloud SDK not installed.")
            return None
            
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            check=True
        )
        
        project_id = result.stdout.strip()
        if not project_id:
            console.print("[bold yellow]No active GCP project set.[/bold yellow]")
            console.print("Please run [bold]gcloud config set project PROJECT_ID[/bold] to set a project.")
            return None
            
        console.print(f"[bold green]Active GCP project:[/bold green] {project_id}")
        return project_id
        
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error getting active GCP project:[/bold red] {str(e)}")
        return None
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return None

def list_gcp_regions() -> List[str]:
    """Get list of available GCP regions"""
    if not is_gcloud_installed():
        console.print("[bold yellow]Using default regions list:[/bold yellow] Google Cloud SDK not installed.")
        # Return common regions as fallback
        return ["us-central1", "us-east1", "us-west1", "europe-west1", "asia-east1"]
        
    try:
        result = subprocess.run(
            ["gcloud", "compute", "regions", "list", "--format", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        
        regions_data = json.loads(result.stdout)
        return [region["name"] for region in regions_data]
        
    except Exception as e:
        console.print(f"[bold yellow]Error fetching GCP regions:[/bold yellow] {str(e)}")
        console.print("[bold yellow]Using default regions list.[/bold yellow]")
        # Return some common regions as fallback
        return ["us-central1", "us-east1", "us-west1", "europe-west1", "asia-east1"]

def get_zones_for_region(region: str) -> List[str]:
    """Get availability zones for a specific GCP region"""
    if not is_gcloud_installed():
        console.print("[bold yellow]Using default zones:[/bold yellow] Google Cloud SDK not installed.")
        # Return default zones as fallback
        return [f"{region}-a", f"{region}-b", f"{region}-c"]
        
    try:
        result = subprocess.run(
            ["gcloud", "compute", "zones", "list", "--filter", f"region:{region}", "--format", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        
        zones_data = json.loads(result.stdout)
        return [zone["name"] for zone in zones_data]
        
    except Exception as e:
        console.print(f"[bold yellow]Error fetching zones for region {region}:[/bold yellow] {str(e)}")
        console.print("[bold yellow]Using default zones.[/bold yellow]")
        # Return default zones as fallback
        return [f"{region}-a", f"{region}-b", f"{region}-c"]

def list_gcp_vpcs() -> List[Dict]:
    """Get list of VPC networks in the project"""
    if not is_gcloud_installed():
        console.print("[bold yellow]Cannot fetch VPC networks:[/bold yellow] Google Cloud SDK not installed.")
        return []
        
    try:
        result = subprocess.run(
            ["gcloud", "compute", "networks", "list", "--format", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        
        networks = json.loads(result.stdout)
        return networks
        
    except Exception as e:
        console.print(f"[bold yellow]Error fetching VPC networks:[/bold yellow] {str(e)}")
        return []

def list_subnets_for_vpc(vpc_name: str) -> List[Dict]:
    """Get list of subnets for a specific VPC"""
    if not is_gcloud_installed():
        console.print("[bold yellow]Cannot fetch subnets:[/bold yellow] Google Cloud SDK not installed.")
        return []
        
    try:
        result = subprocess.run(
            ["gcloud", "compute", "networks", "subnets", "list", 
             "--filter", f"network:{vpc_name}", "--format", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        
        subnets = json.loads(result.stdout)
        return subnets
        
    except Exception as e:
        console.print(f"[bold yellow]Error fetching subnets for VPC {vpc_name}:[/bold yellow] {str(e)}")
        return []

def list_security_groups() -> List[Dict]:
    """Get list of firewall rules (equivalent to security groups)"""
    if not is_gcloud_installed():
        console.print("[bold yellow]Cannot fetch firewall rules:[/bold yellow] Google Cloud SDK not installed.")
        return []
        
    try:
        result = subprocess.run(
            ["gcloud", "compute", "firewall-rules", "list", "--format", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        
        firewall_rules = json.loads(result.stdout)
        return firewall_rules
        
    except Exception as e:
        console.print(f"[bold yellow]Error fetching firewall rules:[/bold yellow] {str(e)}")
        return []

def init_terraform_backend(bucket_name: str, prefix: str) -> bool:
    """Initialize Terraform backend with GCS bucket"""
    try:
        # Check if terraform is installed
        if not shutil.which("terraform"):
            console.print("[bold red]Error:[/bold red] Terraform is not installed or not in your PATH.")
            console.print("Please install Terraform from: [link]https://www.terraform.io/downloads[/link]")
            return False
            
        # Create backend.tf file with GCS configuration
        backend_config = f'''terraform {{
  backend "gcs" {{
    bucket = "{bucket_name}"
    prefix = "{prefix}"
  }}
}}
'''
        
        # Get Terraform directory path
        from kafka_cli.utils.config import get_config_dir
        terraform_dir = os.path.join(get_config_dir(), "terraform")
        os.makedirs(terraform_dir, exist_ok=True)
        
        # Write backend configuration
        backend_file = os.path.join(terraform_dir, "backend.tf")
        with open(backend_file, 'w') as f:
            f.write(backend_config)
            
        # Run terraform init
        console.print(f"[bold]Initializing Terraform backend with bucket [cyan]{bucket_name}[/cyan]...[/bold]")
        result = subprocess.run(
            ["terraform", "init"],
            cwd=terraform_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            console.print("[bold red]Terraform initialization failed:[/bold red]")
            console.print(result.stderr)
            return False
            
        console.print("[bold green]Terraform backend initialized successfully![/bold green]")
        return True
        
    except Exception as e:
        console.print(f"[bold red]Error initializing Terraform backend:[/bold red] {str(e)}")
        return False

def estimate_compute_costs(
    region: str,
    instance_type: str,
    num_instances: int,
    disk_type: str,
    disk_size_gb: int
) -> Optional[Dict]:
    """
    Estimate GCP compute costs for the configured cluster
    This is a simplified estimation and actual costs may vary
    """
    # Basic rate mapping (very simplified)
    region_multipliers = {
        "us-central1": 1.0,
        "us-east1": 1.0,
        "us-west1": 1.05,
        "europe-west1": 1.1,
        "asia-east1": 1.15,
    }
    
    instance_costs = {
        "e2-small": 0.02,
        "e2-medium": 0.03,
        "e2-standard-2": 0.07,
        "e2-standard-4": 0.14,
        "e2-standard-8": 0.28,
        "n2-standard-2": 0.10,
        "n2-standard-4": 0.20,
        "n2-standard-8": 0.40,
    }
    
    disk_costs = {
        "pd-standard": 0.04,
        "pd-balanced": 0.10,
        "pd-ssd": 0.17,
    }
    
    region_factor = region_multipliers.get(region, 1.1)  # Default if unknown
    
    try:
        # Calculate costs
        instance_hourly = instance_costs.get(instance_type, 0.10) * region_factor
        instance_monthly = instance_hourly * 24 * 30
        
        disk_monthly_per_gb = disk_costs.get(disk_type, 0.10) * region_factor
        disk_monthly = disk_monthly_per_gb * disk_size_gb
        
        # Total costs
        instance_total = instance_monthly * num_instances
        disk_total = disk_monthly * num_instances
        monthly_total = instance_total + disk_total
        
        return {
            "instance_hourly": round(instance_hourly, 3),
            "instance_monthly_per_node": round(instance_monthly, 2),
            "disk_monthly_per_node": round(disk_monthly, 2),
            "total_monthly": round(monthly_total, 2)
        }
        
    except Exception as e:
        console.print(f"[bold red]Error estimating costs:[/bold red] {str(e)}")
        return None
