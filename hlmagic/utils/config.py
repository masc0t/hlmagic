import os
import tomllib
from pathlib import Path
from typing import Any, Dict

CONFIG_DIR = Path.home() / ".hlmagic"
CONFIG_FILE = CONFIG_DIR / "config.toml"

DEFAULT_CONFIG = {
    "brain": {
        "model": "llama3.1",
        "temperature": 0.1
    },
    "storage": {
        "base_path": "/opt/hlmagic",
        "media_mounts": ["/mnt/d", "/mnt/e"]
    },
    "auth": {
        "password": ""
    }
}

def ensure_config():
    """Ensure config directory and file exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)

def load_config() -> Dict[str, Any]:
    """Load configuration from TOML file."""
    ensure_config()
    with open(CONFIG_FILE, "rb") as f:
        return tomllib.load(f)

def save_config(config: Dict[str, Any]):
    """Save configuration to TOML file."""
    # Simple manual write to avoid extra deps for now
    content = f"""[brain]
model = "{config['brain']['model']}"
temperature = {config['brain']['temperature']}

[storage]
base_path = "{config['storage']['base_path']}"
media_mounts = {config['storage']['media_mounts']}

[auth]
password = "{config.get('auth', {}).get('password', '')}"
"""
    CONFIG_FILE.write_text(content)

def get_password() -> str:
    """Get the configured access password."""
    config = load_config()
    return config.get("auth", {}).get("password", "")

def set_password(password: str):
    """Set the access password in config."""
    config = load_config()
    if "auth" not in config:
        config["auth"] = {}
    config["auth"]["password"] = password
    save_config(config)

def get_model() -> str:
    """Get the configured AI model."""
    config = load_config()
    return config.get("brain", {}).get("model", "llama3.1")
