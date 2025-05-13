"""
Cloud provider interface and implementations.
Follows the Strategy pattern for different cloud platforms.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from rich.console import Console

console = Console()


class CloudProvider(ABC):
    """Abstract base class for cloud providers"""

    @abstractmethod
    def is_authenticated(self) -> bool:
        """Check if user is authenticated with the cloud provider"""
        pass

    @abstractmethod
    def get_active_project(self) -> Optional[str]:
        """Get the currently active project/account"""
        pass

    @abstractmethod
    def list_regions(self) -> List[Dict[str, Any]]:
        """List available regions"""
        pass

    @abstractmethod
    def get_zones_for_region(self, region: str) -> List[str]:
        """Get available zones for a region"""
        pass

    @abstractmethod
    def list_networks(self) -> List[Dict[str, Any]]:
        """List available networks/VPCs"""
        pass

    @abstractmethod
    def list_subnets(self, network_name: str) -> List[Dict[str, Any]]:
        """List available subnets for a network"""
        pass

    @abstractmethod
    def list_security_groups(self) -> List[Dict[str, Any]]:
        """List available security groups/firewall rules"""
        pass

    @abstractmethod
    def estimate_costs(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate costs for a given configuration"""
        pass

    @abstractmethod
    def setup_state_storage(self, bucket_name: str, prefix: str) -> bool:
        """Set up cloud storage for Terraform state"""
        pass


# Factory for creating cloud providers
class CloudProviderFactory:
    """Factory for creating cloud provider instances"""

    @staticmethod
    def create_provider(provider_type: str) -> CloudProvider:
        """Create a cloud provider of the specified type"""
        if provider_type.lower() == "gcp":
            from kafka_cli.core.cloud.gcp import GCPProvider

            return GCPProvider()
        else:
            raise ValueError(f"Unsupported cloud provider: {provider_type}")
