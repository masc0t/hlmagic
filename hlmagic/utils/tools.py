import os
import subprocess
import psutil
import re
from pathlib import Path
from typing import List, Dict
from hlmagic.utils import templates
from hlmagic.utils.hardware import HardwareScanner
from rich.console import Console

console = Console()

# --- Security Constants ---
ALLOWED_SERVICE_NAME = re.compile(r"^[a-zA-Z0-9_-]+$")
FORBIDDEN_MOUNTS = [
    "/:",       # Root
    "/boot:",   # Boot
    "/proc:",   # Kernel stats
    "/sys:",    # Kernel objects
    "/etc:",    # Configs
    "/usr:",    # System binaries
    "/var/run:" # Docker socket (sometimes needed, but risky for auto-gen)
]

class SecurityViolation(Exception):
    pass

def _validate_service_name(name: str):
    """Ensure service name is alphanumeric and safe."""
    if not ALLOWED_SERVICE_NAME.match(name):
        raise SecurityViolation(f"Invalid service name: '{name}'. Must be alphanumeric with dashes/underscores.")
    # Using chr(92) for backslash to avoid any escaping issues in transit/tools
    if ".." in name or "/" in name or chr(92) in name:
        raise SecurityViolation("Path traversal attempt detected in service name.")

def _validate_compose_content(content: str):
    """Scan Docker Compose content for dangerous patterns."""
    # Check for dangerous volume mounts
    for line in content.splitlines():
        if "volumes:" in line:
            continue
        for forbidden in FORBIDDEN_MOUNTS:
            # Simple substring check for now; robust parsing would be better but heavier
            if forbidden in line and not line.strip().startswith("#"):
                 raise SecurityViolation(f"Dangerous volume mount detected: '{forbidden}' in line: {line.strip()}")
    
    # Check for privileged mode (risky for automated agents)
    if "privileged: true" in content.lower():
        raise SecurityViolation("Privileged mode is currently restricted for automated agents.")

def get_optimized_template(service_name: str, mounts: List[str] = None) -> str:
    """Retrieve a hardware-optimized Docker Compose template for a given service."""
    # 1. Get Hardware Info
    scanner = HardwareScanner()
    scanner.scan()
    gpu_vendor = scanner.primary_gpu.value
    
    # 2. Get User Info
    user_ids = get_user_ids()
    
    # 3. Generate Template
    template = templates.get_service_template(
        service_name, 
        gpu_vendor, 
        user_ids["PUID"], 
        user_ids["PGID"],
        mounts=mounts
    )
    
    if not template:
        return f"No template found for {service_name}."
        
    return template

def scan_wsl_storage() -> List[Dict[str, str]]:
    """Identify mount points for media storage. On Windows, finds all drive letters."""
    mounts = []
    for part in psutil.disk_partitions():
        if os.name == 'nt':
            # On Windows, list all fixed drives
            if 'fixed' in part.opts or part.fstype:
                mounts.append({
                    "path": part.mountpoint,
                    "device": part.device,
                    "fstype": part.fstype
                })
        else:
            # On Linux/WSL, find Windows mounts
            if part.mountpoint.startswith("/mnt/") and len(part.mountpoint) > 5:
                mounts.append({
                    "path": part.mountpoint,
                    "device": part.device,
                    "fstype": part.fstype
                })
    return mounts

def write_compose_file(service_name: str, compose_content: str):
    """Generate Docker Compose YAMLs in the standard path."""
    try:
        from hlmagic.utils.config import load_config
        # 1. Input Sanitization
        _validate_service_name(service_name)
        _validate_compose_content(compose_content)

        # 2. Path Confinement
        base_path = Path(load_config()['storage']['base_path']) / "services"
        target_dir = (base_path / service_name).resolve()

        # 3. Execution
        os.makedirs(str(target_dir), exist_ok=True)
        
        compose_file = target_dir / "docker-compose.yml"
        compose_file.write_text(compose_content)
        
        return f"Successfully wrote compose file to {compose_file}"

    except SecurityViolation as e:
        return f"SECURITY BLOCK: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

def setup_and_deploy_service(service_name: str, mounts: List[str] = None) -> str:
    """COMPLETELY setup and start a service. This is the preferred way to deploy."""
    try:
        # 1. Generate the optimized content
        content = get_optimized_template(service_name, mounts)
        if "No template found" in content:
            return content

        # 2. Write the file
        write_res = write_compose_file(service_name, content)
        if "SECURITY BLOCK" in write_res or "Error" in write_res:
            return write_res

        # 3. Deploy
        deploy_res = deploy_service(service_name)
        return f"Successfully configured and started {service_name}. {deploy_res}"

    except Exception as e:
        return f"Error in autonomous setup: {str(e)}"

def deploy_service(service_name: str) -> str:
    """Start a service using docker compose. Creates config directories automatically."""
    try:
        from hlmagic.utils.config import load_config
        # 1. Path Setup
        base_path = Path(load_config()['storage']['base_path']) / "services"
        service_dir = (base_path / service_name).resolve()
        config_dir = Path(load_config()['storage']['base_path']) / "config" / service_name

        if not (service_dir / "docker-compose.yml").exists():
            return f"Error: No docker-compose.yml found in {service_dir}. Write the file first!"

        # 2. Pre-flight: Create config dir with correct permissions
        os.makedirs(str(config_dir), exist_ok=True)

        # 3. Execution
        console.print(f"[yellow]Deploying {service_name}...[/yellow]")
        cmd = ["docker", "compose", "up", "-d"]
        result = subprocess.run(
            cmd,
            cwd=service_dir,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return f"Successfully deployed {service_name}. Output: {result.stdout.strip()}"
        else:
            return f"Error deploying {service_name}: {result.stderr.strip()}"

    except Exception as e:
        return f"Error: {str(e)}"

def check_service_status(service_name: str = "docker") -> str:
    """Check if a systemd service is active."""
    # Validate service name to prevent command injection
    if not re.match(r"^[a-zA-Z0-9_\-\.]+", service_name):
        return "Error: Invalid service name."

    try:
        result = subprocess.run(["systemctl", "is-active", service_name], capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"error: {str(e)}"

def execute_autonomous_task(script_content: str, interpreter: str = "bash") -> str:
    """
    Execute a complex task by writing and running an ephemeral script.
    Use this for debugging, fixing permissions, or any task not covered by other tools.
    """
    import uuid
    import subprocess
    from pathlib import Path

    task_id = str(uuid.uuid4())[:8]
    script_path = Path(f"/tmp/hl_task_{task_id}.sh")
    
    try:
        # Write the script
        script_path.write_text(script_content)
        script_path.chmod(0o755)
        
        # Execute the script
        cmd = [interpreter, str(script_path)]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60 # Safety timeout
        )
        
        # Combine output
        output = f"--- STDOUT ---\n{result.stdout}\n"
        if result.stderr:
            output += f"--- STDERR ---\n{result.stderr}\n"
            
        return output
    except Exception as e:
        return f"Execution Error: {str(e)}"
    finally:
        # Cleanup
        if script_path.exists():
            script_path.unlink()

def get_service_urls() -> Dict[str, str]:
    """Retrieve local access URLs for all deployed HLMagic services."""
    urls = {
        "hlmagic": "http://localhost:8000 (or http://hlmagic.local:8000)"
    }
    
    # Common port mappings
    port_map = {
        "jellyfin": 8096,
        "plex": 32400,
        "sonarr": 8989,
        "radarr": 7878,
        "lidarr": 8686,
        "overseerr": 5055,
        "ollama": 11434
    }

    from hlmagic.utils.config import load_config
    base_path = Path(load_config()['storage']['base_path']) / "services"
    if base_path.exists():
        for service_dir in base_path.iterdir():
            if service_dir.is_dir() and (service_dir / "docker-compose.yml").exists():
                name = service_dir.name.lower()
                if name in port_map:
                    urls[name] = f"http://localhost:{port_map[name]} (or http://hlmagic.local:{port_map[name]})"
                else:
                    urls[name] = "Service deployed, but port unknown."
                    
    return urls

def get_user_ids() -> Dict[str, int]:
    """Get PUID and PGID for the current user. Returns 1000 on Windows as dummy."""
    try:
        return {
            "PUID": os.getuid(),
            "PGID": os.getgid()
        }
    except AttributeError:
        # We are on Windows, return standard IDs
        return {
            "PUID": 1000,
            "PGID": 1000
        }
