"""
Configuration Manager using the Singleton pattern.
Centralizes all configuration operations.
"""
import os
import pathlib
from typing import Any, Dict, List, Optional

import yaml
from rich.console import Console

from kafka_cli.core.errors import ConfigurationError, ErrorHandler
from kafka_cli.utils.singleton import Singleton

console = Console()


class ConfigManager(metaclass=Singleton):
    """
    Singleton manager for configuration handling.
    Provides centralized access to application settings and profiles.
    """

    # Default configuration paths
    DEFAULT_CONFIG_DIR = os.path.expanduser("~/.kafka-cli")
    CONFIG_FILE = "config.yaml"
    PROFILES_DIR = "profiles"
    TERRAFORM_DIR = "terraform"

    def __init__(self) -> None:
        """Initialize the Configuration Manager"""
        self._config: Dict[str, Any] = {}
        self._config_dir: str = self.DEFAULT_CONFIG_DIR
        self._initialized: bool = False

    def init_config_dir(self, custom_config_dir: Optional[str] = None) -> str:
        """Initialize the configuration directory structure."""
        if custom_config_dir:
            self._config_dir = os.path.expanduser(custom_config_dir)
        else:
            self._config_dir = self.DEFAULT_CONFIG_DIR

        try:
            # Create main config directory if it doesn't exist
            pathlib.Path(self._config_dir).mkdir(parents=True, exist_ok=True)

            # Create profile and terraform directories
            pathlib.Path(os.path.join(self._config_dir, self.PROFILES_DIR)).mkdir(exist_ok=True)
            pathlib.Path(os.path.join(self._config_dir, self.TERRAFORM_DIR)).mkdir(exist_ok=True)

            # Create default config file if it doesn't exist
            config_path = os.path.join(self._config_dir, self.CONFIG_FILE)
            if not os.path.exists(config_path):
                with open(config_path, "w") as f:
                    yaml.dump(
                        {
                            "version": "1.0.0",
                            "default_profile": None,
                            "gcp": {
                                "project_id": None,
                                "region": "us-central1",
                                "zone": "us-central1-a",
                            },
                            "terraform": {
                                "log_level": "INFO",
                                "auto_approve": False,
                            },
                        },
                        f,
                        default_flow_style=False,
                    )
                console.print(f"Created default configuration at [cyan]{config_path}[/cyan]")

            self.load_config()
            self._initialized = True
            return self._config_dir

        except OSError as e:
            error_msg = f"Failed to initialize configuration directory: {str(e)}"
            ErrorHandler().handle_exception(ConfigurationError(error_msg, help_text="Please check directory permissions"))
            raise ConfigurationError(error_msg) from e

    def load_config(self) -> Dict[str, Any]:
        """Load the configuration from the config file."""
        config_path = os.path.join(self._config_dir, self.CONFIG_FILE)
        try:
            with open(config_path, "r") as f:
                self._config = yaml.safe_load(f) or {}
            return self._config
        except FileNotFoundError:
            error_msg = f"Configuration file not found at {config_path}"
            self._config = {}
            ErrorHandler().handle_exception(
                ConfigurationError(error_msg, help_text="Run init command to create a new configuration")
            )
            return {}
        except yaml.YAMLError as e:
            error_msg = f"Invalid YAML in configuration file: {str(e)}"
            self._config = {}
            ErrorHandler().handle_exception(ConfigurationError(error_msg, help_text="The configuration file may be corrupted"))
            return {}
        except Exception as e:
            error_msg = f"Error loading configuration: {str(e)}"
            self._config = {}
            ErrorHandler().handle_exception(ConfigurationError(error_msg))
            return {}

    def save_config(self) -> bool:
        """Save the current configuration to the config file."""
        config_path = os.path.join(self._config_dir, self.CONFIG_FILE)
        try:
            with open(config_path, "w") as f:
                yaml.dump(self._config, f, default_flow_style=False)
            return True
        except Exception as e:
            error_msg = f"Error saving configuration: {str(e)}"
            ErrorHandler().handle_exception(ConfigurationError(error_msg))
            return False

    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration."""
        if not self._config:
            self.load_config()
        return self._config

    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Update the configuration with new values."""
        self._config.update(updates)
        return self.save_config()

    def get_config_dir(self) -> str:
        """Get the current configuration directory."""
        return self._config_dir

    def get_profiles_dir(self) -> str:
        """Get the profiles directory path"""
        return os.path.join(self._config_dir, self.PROFILES_DIR)

    def get_terraform_dir(self) -> str:
        """Get the terraform directory path"""
        return os.path.join(self._config_dir, self.TERRAFORM_DIR)

    def get_default_profile(self) -> Optional[str]:
        """Get the name of the default profile"""
        return self.get_config().get("default_profile")

    def set_default_profile(self, profile_name: Optional[str]) -> bool:
        """Set the default profile"""
        return self.update_config({"default_profile": profile_name})

    def get_profile_path(self, profile_name: str) -> str:
        """Get the full path to a profile file"""
        return os.path.join(self.get_profiles_dir(), f"{profile_name}.yaml")

    def profile_exists(self, profile_name: str) -> bool:
        """Check if a profile exists"""
        return os.path.exists(self.get_profile_path(profile_name))

    def list_profiles(self) -> List[str]:
        """List all available profiles"""
        profiles_dir = self.get_profiles_dir()
        if not os.path.exists(profiles_dir):
            return []

        try:
            return [f[:-5] for f in os.listdir(profiles_dir) if f.endswith(".yaml")]
        except OSError as e:
            error_msg = f"Failed to list profiles: {str(e)}"
            ErrorHandler().handle_exception(ConfigurationError(error_msg))
            return []

    def load_profile(self, profile_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Load a profile configuration.
        If profile_name is None, loads the default profile.
        """
        if profile_name is None:
            profile_name = self.get_default_profile()
            if profile_name is None:
                # No default profile set
                return None

        profile_path = self.get_profile_path(profile_name)
        if not os.path.exists(profile_path):
            return None

        try:
            with open(profile_path, "r") as f:
                profile_data = yaml.safe_load(f)
                return profile_data or {}
        except yaml.YAMLError as e:
            error_msg = f"Invalid YAML in profile {profile_name}: {str(e)}"
            ErrorHandler().handle_exception(
                ConfigurationError(error_msg, help_text=f"The profile file at {profile_path} may be corrupted")
            )
            return None
        except Exception as e:
            error_msg = f"Error loading profile {profile_name}: {str(e)}"
            ErrorHandler().handle_exception(ConfigurationError(error_msg))
            return None

    def save_profile(self, profile_data: Dict[str, Any], profile_name: Optional[str] = None) -> bool:
        """
        Save a profile configuration.
        If profile_name is None, saves to the default profile.
        """
        if profile_name is None:
            profile_name = self.get_default_profile()
            if profile_name is None:
                error_msg = "No profile name provided and no default profile set"
                ErrorHandler().handle_exception(
                    ConfigurationError(error_msg, help_text="Specify a profile name or set a default profile first")
                )
                return False

        profile_path = self.get_profile_path(profile_name)
        try:
            os.makedirs(os.path.dirname(profile_path), exist_ok=True)
            with open(profile_path, "w") as f:
                yaml.dump(profile_data, f, default_flow_style=False)
            return True
        except Exception as e:
            error_msg = f"Error saving profile {profile_name}: {str(e)}"
            ErrorHandler().handle_exception(ConfigurationError(error_msg))
            return False

    def delete_profile(self, profile_name: str) -> bool:
        """Delete a profile"""
        profile_path = self.get_profile_path(profile_name)
        if not os.path.exists(profile_path):
            return False

        try:
            os.remove(profile_path)

            # If this was the default profile, update the config
            if self.get_default_profile() == profile_name:
                self.set_default_profile(None)

            return True
        except Exception as e:
            error_msg = f"Error deleting profile {profile_name}: {str(e)}"
            ErrorHandler().handle_exception(ConfigurationError(error_msg))
            return False
