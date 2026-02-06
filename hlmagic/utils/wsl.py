import os
import subprocess
import shutil
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

def is_systemd_running() -> bool:
    """Check if systemd is actually running as PID 1."""
    try:
        result = subprocess.run(["ps", "-p", "1", "-o", "comm="], capture_output=True, text=True)
        return result.stdout.strip() == "systemd"
    except Exception:
        return False

def ensure_systemd():
    """Ensure [boot] systemd=true and [network] hostname=hlmagic are in /etc/wsl.conf."""
    # 1. Check if it's already running
    systemd_ok = is_systemd_running()
    
    # Check hostname
    import socket
    hostname_ok = socket.gethostname() == "hlmagic"

    if systemd_ok and hostname_ok:
        return True

    # 2. Check/Update config
    needs_update = False
    content = ""
    if WSL_CONF_PATH.exists():
        content = WSL_CONF_PATH.read_text()

    if "[boot]" not in content:
        content += "\n[boot]\nsystemd=true\n"
        needs_update = True
    elif "systemd=true" not in content:
        content = content.replace("[boot]", "[boot]\nsystemd=true")
        needs_update = True

    if "[network]" not in content:
        content += "\n[network]\nhostname=hlmagic\ngenerateHosts=true\n"
        needs_update = True
    elif "hostname=hlmagic" not in content:
        content = content.replace("[network]", "[network]\nhostname=hlmagic\ngenerateHosts=true")
        needs_update = True
    
    if needs_update:
        console.print("[yellow]Updating /etc/wsl.conf for systemd and hostname...[/yellow]")
        _write_wsl_conf(content.strip() + "\n")
        return False # Needs restart

    return systemd_ok and hostname_ok

def setup_mdns():
    """Install and enable Avahi for .local resolution."""
    try:
        console.print("[yellow]Setting up mDNS (hlmagic.local)...[/yellow]")
        subprocess.run(["sudo", "apt-get", "install", "-y", "avahi-daemon"], check=True, capture_output=True)
        subprocess.run(["sudo", "systemctl", "enable", "--now", "avahi-daemon"], check=True, capture_output=True)
        return True
    except Exception as e:
        console.print(f"[red]Error setting up mDNS: {e}[/red]")
        return False

def validate_sudo():
    """Verify the user has sudo privileges and refresh the timestamp."""
    try:
        # -v (validate) refreshes the sudo timestamp. If it needs a password, 
        # it will prompt the user in the terminal since we aren't capturing output.
        subprocess.run(["sudo", "-v"], check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def install_ollama():
    """Install Ollama using the official installer script."""
    # Ensure dependencies are present
    subprocess.run(["sudo", "apt-get", "install", "-y", "zstd", "curl"], check=False)

    if subprocess.run(["which", "ollama"], capture_output=True).returncode == 0:
        console.print("[green]✓ Ollama binary detected.[/green]")
    else:
        console.print("[yellow]Installing Ollama via official script...[/yellow]")
        try:
            cmd = "curl -fsSL https://ollama.com/install.sh | sh"
            subprocess.run(["bash", "-c", cmd], check=True)
        except Exception as e:
            console.print(f"[red]Error installing Ollama: {e}[/red]")
            return False

    return setup_ollama_service()

def setup_ollama_service():
    """Configure Ollama as a startup service (Official Recommended Method)."""
    try:
        console.print("[yellow]Configuring Ollama service...[/yellow]")
        
        # 1. Create user and group
        # We use check=False because they might already exist
        subprocess.run(["sudo", "useradd", "-r", "-s", "/bin/false", "-U", "-m", "-d", "/usr/share/ollama", "ollama"], capture_output=True)
        subprocess.run(["sudo", "usermod", "-a", "-G", "ollama", os.environ.get("USER", "ubuntu")], capture_output=True)

        # 2. Create service file
        service_content = """[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="PATH=$PATH"
Environment="OLLAMA_HOST=0.0.0.0"

[Install]
WantedBy=multi-user.target
"""
        service_path = "/etc/systemd/system/ollama.service"
        # Write using sudo tee
        process = subprocess.Popen(['sudo', 'tee', service_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        process.communicate(input=service_content)

        # 3. Reload and Enable
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        subprocess.run(["sudo", "systemctl", "enable", "ollama"], check=True)
        return True
    except Exception as e:
        console.print(f"[red]Error configuring Ollama service: {e}[/red]")
        return False

def start_ollama_service():
    """Start the ollama systemd service."""
    try:
        console.print("[yellow]Starting Ollama service...[/yellow]")
        subprocess.run(["sudo", "systemctl", "start", "ollama"], check=True)
        return True
    except Exception as e:
        console.print(f"[red]Error starting Ollama: {e}[/red]")
        return False

def pull_model(model_name: str):
    """Pull the specified model using Ollama."""
    console.print(f"[yellow]Pulling AI model '{model_name}' (this may take a few minutes)...[/yellow]")
    try:
        subprocess.run(["ollama", "pull", model_name], check=True)
        return True
    except Exception as e:
        console.print(f"[red]Error pulling model: {e}[/red]")
        return False

def install_docker():
    """Install Docker Engine using the official script."""
    if shutil.which("docker"):
        console.print("[green]✓ Docker is already installed.[/green]")
        return True

    console.print("[yellow]Installing Docker Engine...[/yellow]")
    try:
        cmd = "curl -fsSL https://get.docker.com | sh"
        subprocess.run(["bash", "-c", cmd], check=True)
        
        # Add user to docker group
        user = os.getenv("USER", "ubuntu")
        subprocess.run(["sudo", "usermod", "-aG", "docker", user], check=True)
        
        console.print("[green]✓ Docker installed and permissions set.[/green]")
        return True
    except Exception as e:
        console.print(f"[red]Error installing Docker: {e}[/red]")
        return False

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
