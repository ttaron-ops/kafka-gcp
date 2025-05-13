import os
import pathlib
from typing import Optional, Dict, Any

import yaml
from rich.console import Console

console = Console()

# Default configuration paths
DEFAULT_CONFIG_DIR = os.path.expanduser("~/.kafka-cli")
CONFIG_FILE = "config.yaml"
PROFILES_DIR = "profiles"
TERRAFORM_DIR = "terraform"

# Current active configuration
_config: Dict[str, Any] = {}
_config_dir: str = DEFAULT_CONFIG_DIR


def init_config_dir(custom_config_dir: Optional[str] = None) -> str:
    """Initialize the configuration directory structure."""
    global _config_dir
    
    if custom_config_dir:
        _config_dir = os.path.expanduser(custom_config_dir)
    else:
        _config_dir = DEFAULT_CONFIG_DIR
    
    # Create main config directory if it doesn't exist
    pathlib.Path(_config_dir).mkdir(parents=True, exist_ok=True)
    
    # Create profile and terraform directories
    pathlib.Path(os.path.join(_config_dir, PROFILES_DIR)).mkdir(exist_ok=True)
    pathlib.Path(os.path.join(_config_dir, TERRAFORM_DIR)).mkdir(exist_ok=True)
    
    # Create default config file if it doesn't exist
    config_path = os.path.join(_config_dir, CONFIG_FILE)
    if not os.path.exists(config_path):
        with open(config_path, 'w') as f:
            yaml.dump({
                'version': '1.0.0',
                'default_profile': None,
                'gcp': {
                    'project_id': None,
                    'region': 'us-central1',
                    'zone': 'us-central1-a',
                },
                'terraform': {
                    'log_level': 'INFO',
                    'auto_approve': False,
                },
            }, f, default_flow_style=False)
        console.print(f"Created default configuration at [cyan]{config_path}[/cyan]")
    
    load_config()
    return _config_dir


def load_config() -> Dict[str, Any]:
    """Load the configuration from the config file."""
    global _config
    
    config_path = os.path.join(_config_dir, CONFIG_FILE)
    try:
        with open(config_path, 'r') as f:
            _config = yaml.safe_load(f) or {}
        return _config
    except Exception as e:
        console.print(f"Error loading config: {str(e)}", style="red")
        return {}


def save_config() -> bool:
    """Save the current configuration to the config file."""
    config_path = os.path.join(_config_dir, CONFIG_FILE)
    try:
        with open(config_path, 'w') as f:
            yaml.dump(_config, f, default_flow_style=False)
        return True
    except Exception as e:
        console.print(f"Error saving config: {str(e)}", style="red")
        return False


def get_config() -> Dict[str, Any]:
    """Get the current configuration."""
    global _config
    if not _config:
        load_config()
    return _config


def update_config(updates: Dict[str, Any]) -> bool:
    """Update the configuration with new values."""
    global _config
    _config.update(updates)
    return save_config()


def get_config_dir() -> str:
    """Get the current configuration directory."""
    global _config_dir
    return _config_dir
