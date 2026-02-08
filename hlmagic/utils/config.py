import os
import tomllib
from pathlib import Path
from typing import Any, Dict

CONFIG_DIR = Path.home() / ".hlmagic"
CONFIG_FILE = CONFIG_DIR / "config.toml"

DEFAULT_CONFIG = {
    "brain": {
        "model": "llama3.1",
        "temperature": 0.1,
        "ollama_host": "http://localhost:11434"
    },
    "storage": {
        "base_path": str(Path.home() / "hlmagic_data"),
        "media_mounts": []
    },
    "auth": {
        "password": ""
    },
    "system": {
        "debug": False,
        "max_sessions": 5
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
        config = tomllib.load(f)
        
        # Migration: Ensure ollama_host exists
        if "brain" in config and "ollama_host" not in config["brain"]:
            config["brain"]["ollama_host"] = "http://localhost:11434"
            
        # Migration: Ensure max_sessions exists
        if "system" in config and "max_sessions" not in config["system"]:
            config["system"]["max_sessions"] = 5

        # Migration: Fix base_path on Windows if it was hardcoded to Linux path
        if os.name == 'nt' and config.get('storage', {}).get('base_path') == '/opt/hlmagic':
            config['storage']['base_path'] = str(Path.home() / "hlmagic_data")
            save_config(config) # Save the migration
            
        return config

def save_config(config: Dict[str, Any]):
    """Save configuration to TOML file."""
    # Escape backslashes for TOML on Windows
    base_path = config['storage']['base_path'].replace("\\", "\\\\")
    media_mounts = str(config['storage']['media_mounts']).replace("'", '"')
    
    content = f"""[brain]
model = "{config['brain']['model']}"
temperature = {config['brain']['temperature']}
ollama_host = "{config['brain'].get('ollama_host', 'http://localhost:11434')}"

[storage]
base_path = "{base_path}"
media_mounts = {media_mounts}

[auth]
password = "{config.get('auth', {}).get('password', '')}"

[system]
debug = {str(config.get('system', {}).get('debug', False)).lower()}
max_sessions = {config.get('system', {}).get('max_sessions', 5)}
"""
    CONFIG_FILE.write_text(content)

def get_debug_mode() -> bool:
    """Check if debug mode is enabled."""
    config = load_config()
    return config.get("system", {}).get("debug", False)

def get_max_sessions() -> int:
    """Get the maximum number of sessions to keep."""
    config = load_config()
    return config.get("system", {}).get("max_sessions", 5)

def set_debug_mode(enabled: bool):
    """Set debug mode in config."""
    config = load_config()
    if "system" not in config:
        config["system"] = {}
    config["system"]["debug"] = enabled
    save_config(config)

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

def get_ollama_host() -> str:
    """Get the configured Ollama host URL."""
    config = load_config()
    return config.get("brain", {}).get("ollama_host", "http://localhost:11434")

def set_ollama_host(host: str):
    """Set the Ollama host URL in config."""
    config = load_config()
    if "brain" not in config:
        config["brain"] = {}
    config["brain"]["ollama_host"] = host
    save_config(config)
