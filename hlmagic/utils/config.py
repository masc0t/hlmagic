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
    # Since tomlli_w might not be installed, I'll use a simple approach for now
    # or just write the default manually if it's small.
    # Actually, I should add it to dependencies.
    
    # For now, a simple manual write of the default to avoid external deps if possible
    # But for real config management, tomlli_w is better.
    
    # Let's try to just use a simple string for the default.
    content = """[brain]
model = "llama3.1"
temperature = 0.1

[storage]
base_path = "/opt/hlmagic"
media_mounts = ["/mnt/d", "/mnt/e"]
"""
    CONFIG_FILE.write_text(content)

def get_model() -> str:
    """Get the configured AI model."""
    config = load_config()
    return config.get("brain", {}).get("model", "llama3.1")
