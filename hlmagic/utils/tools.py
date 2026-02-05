import os
import subprocess
import psutil
import re
from pathlib import Path
from typing import List, Dict
from hlmagic.utils import templates
from hlmagic.utils.hardware import HardwareScanner

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
    """Identify Windows mount points (e.g., /mnt/d/) for media storage."""
    mounts = []
    for part in psutil.disk_partitions():
        if part.mountpoint.startswith("/mnt/") and len(part.mountpoint) > 5:
            mounts.append({
                "path": part.mountpoint,
                "device": part.device,
                "fstype": part.fstype
            })
    return mounts

def write_compose_file(service_name: str, compose_content: str):
    """Generate Docker Compose YAMLs in the standard /opt/hlmagic/ path."""
    try:
        # 1. Input Sanitization
        _validate_service_name(service_name)
        _validate_compose_content(compose_content)

        # 2. Path Confinement
        base_path = Path("/opt/hlmagic/services").resolve()
        target_dir = (base_path / service_name).resolve()

        # Ensure we didn't escape /opt/hlmagic/services (double check)
        if not str(target_dir).startswith(str(base_path)):
            raise SecurityViolation("Path traversal detected: Target directory matches outside /opt/hlmagic.")

        # 3. Execution (via sudo)
        # Use sudo to create directory and write file
        subprocess.run(["sudo", "mkdir", "-p", str(target_dir)], check=True)
        
        temp_file = Path(f"/tmp/{service_name}_docker-compose.yml")
        temp_file.write_text(compose_content)
        
        # Verify temp file exists before moving
        if not temp_file.exists():
             raise IOError("Failed to write temporary compose file.")

        subprocess.run(["sudo", "mv", str(temp_file), str(target_dir / "docker-compose.yml")], check=True)
        return f"Successfully wrote compose file to {target_dir}/docker-compose.yml"

    except SecurityViolation as e:
        return f"SECURITY BLOCK: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

def deploy_service(service_name: str) -> str:
    \"\"\"Start a service using docker compose. Creates config directories automatically.\"\"\"
    try:
        # 1. Path Setup
        base_path = Path(\"/opt/hlmagic/services\").resolve()
        service_dir = (base_path / service_name).resolve()
        config_dir = Path(f\"/opt/hlmagic/config/{service_name}\").resolve()

        if not (service_dir / \"docker-compose.yml\").exists():
            return f\"Error: No docker-compose.yml found in {service_dir}. Write the file first!\"

        # 2. Pre-flight: Create config dir with correct permissions
        subprocess.run([\"sudo\", \"mkdir\", \"-p\", str(config_dir)], check=True)
        user_ids = get_user_ids()
        subprocess.run([\"sudo\", \"chown\", f\"{user_ids['PUID']}:{user_ids['PGID']}\", str(config_dir)], check=True)

        # 3. Execution
        console.print(f\"[yellow]Deploying {service_name}...[/yellow]\")
        result = subprocess.run(
            [\"sudo\", \"docker\", \"compose\", \"up\", \"-d\"],
            cwd=service_dir,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return f\"Successfully deployed {service_name}. Output: {result.stdout.strip()}\"
        else:
            return f\"Error deploying {service_name}: {result.stderr.strip()}\"

    except Exception as e:
        return f\"Error: {str(e)}\"

def check_service_status(service_name: str = \"docker\") -> str:
    """Check if a systemd service is active."""
    # Validate service name to prevent command injection
    if not re.match(r"^[a-zA-Z0-9_\-\.]+", service_name):
        return "Error: Invalid service name."

    try:
        result = subprocess.run(["systemctl", "is-active", service_name], capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"error: {str(e)}"

def get_user_ids() -> Dict[str, int]:
    """Get PUID and PGID for the current WSL user (usually 1000)."""
    return {
        "PUID": os.getuid(),
        "PGID": os.getgid()
    }