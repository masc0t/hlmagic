import os
import subprocess
from pathlib import Path
from rich.console import Console

console = Console()

WSL_CONF_PATH = Path("/etc/wsl.conf")

def is_wsl() -> bool:
    """Check if the current environment is WSL."""
    return os.path.exists("/proc/sys/fs/binfmt_misc/WSLInterop") or "WSL_DISTRO_NAME" in os.environ

def get_wsl_version() -> float:
    """Attempt to get WSL version. Requires running outside or specific checks."""
    # This is tricky from inside WSL, but we can check for specific features.
    # Usually, if systemd is available and /etc/wsl.conf works, it's WSL2.
    # We can try to run 'wsl.exe -l -v' but that's from Windows.
    # A common way inside is to check 'uname -r' for 'microsoft'
    try:
        result = subprocess.run(["uname", "-r"], capture_output=True, text=True)
        if "microsoft" in result.stdout.lower():
            return 2.0 # Assume 2.0 for modern kernels
    except Exception:
        pass
    return 1.0

def ensure_systemd():
    """Ensure [boot] systemd=true is in /etc/wsl.conf"""
    if not WSL_CONF_PATH.exists():
        console.print("[yellow]Creating /etc/wsl.conf...[/yellow]")
        content = "[boot]\nsystemd=true\n"
        _write_wsl_conf(content)
        return False # Needs restart

    content = WSL_CONF_PATH.read_text()
    if "systemd=true" in content:
        return True
    
    console.print("[yellow]Updating /etc/wsl.conf to enable systemd...[/yellow]")
    if "[boot]" in content:
        content = content.replace("[boot]", "[boot]\nsystemd=true")
    else:
        content += "\n[boot]\nsystemd=true\n"
    
    _write_wsl_conf(content)
    return False # Needs restart

def _write_wsl_conf(content: str):
    """Write to /etc/wsl.conf, requires sudo."""
    try:
        # We use sudo tee to write to protected file
        process = subprocess.Popen(['sudo', 'tee', str(WSL_CONF_PATH)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        process.communicate(input=content)
    except Exception as e:
        console.print(f"[red]Error writing to /etc/wsl.conf: {e}[/red]")
        raise

def check_nvidia_drivers():
    """Check if NVIDIA drivers are available in WSL."""
    try:
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False
