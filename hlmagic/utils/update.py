import subprocess
import os
from pathlib import Path
from rich.console import Console

console = Console()
REPO_PATH = Path("/opt/hlmagic/repo")

def get_current_version() -> str:
    """Get the version from pyproject.toml."""
    pyproject_path = REPO_PATH / "pyproject.toml"
    if not pyproject_path.exists():
        return "unknown"
    
    try:
        for line in pyproject_path.read_text().splitlines():
            if line.startswith("version ="):
                return line.split("=")[1].strip().replace('"', '')
    except Exception:
        pass
    return "unknown"

def get_version_info():
    """Get version and last update datetime."""
    version = get_current_version()
    last_update = "unknown"
    if REPO_PATH.exists():
        try:
            # Get the ISO 8601 date of the last commit
            res = subprocess.run(
                ["git", "log", "-1", "--format=%cI"], 
                cwd=REPO_PATH, check=True, capture_output=True, text=True
            )
            last_update = res.stdout.strip()
        except Exception:
            pass
    return {"version": version, "date": last_update}

def check_for_updates():
    """Check if the local repo is behind origin/main."""
    if not REPO_PATH.exists():
        return False, "Repository not found at /opt/hlmagic/repo"

    try:
        # Fetch latest
        subprocess.run(["git", "fetch"], cwd=REPO_PATH, check=True, capture_output=True)
        
        # Compare local HEAD with origin/main
        local = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_PATH, check=True, capture_output=True, text=True).stdout.strip()
        remote = subprocess.run(["git", "rev-parse", "origin/main"], cwd=REPO_PATH, check=True, capture_output=True, text=True).stdout.strip()
        
        if local != remote:
            return True, "A new update is available!"
        return False, "HLMagic is up to date."
    except Exception as e:
        return False, f"Error checking for updates: {e}"

def restart_server():
    """Exit the process and let systemd or the background loop restart it."""
    import sys
    print("Restart: Signalling process exit for restart...")
    # Systemd will see this exit and restart the service automatically
    sys.exit(0)

def apply_update():
    """Pull the latest changes and reinstall dependencies."""
    if not REPO_PATH.exists():
        print(f"Update error: REPO_PATH {REPO_PATH} does not exist.")
        return False, "Repository not found."

    try:
        console.print("[yellow]Updating HLMagic code...[/yellow]")
        print("Update: Running git fetch...")
        subprocess.run(["git", "fetch"], cwd=REPO_PATH, check=True, capture_output=True)
        
        print("Update: Running git pull...")
        subprocess.run(["git", "pull", "origin", "main"], cwd=REPO_PATH, check=True, capture_output=True)
        
        # Re-install in editable mode to update dependencies
        venv_pip = Path("/opt/hlmagic/venv/bin/pip")
        print(f"Update: Re-installing via {venv_pip if venv_pip.exists() else 'pip'}...")
        if venv_pip.exists():
            subprocess.run([str(venv_pip), "install", "-e", "."], cwd=REPO_PATH, check=True, capture_output=True)
        else:
            subprocess.run(["pip", "install", "-e", "."], cwd=REPO_PATH, check=True, capture_output=True)
            
        console.print("[green]✓ HLMagic update applied to disk.[/green]")
        print("Update: Successfully applied to disk.")
        return True, "Update applied successfully. Server will restart in a moment."
    except Exception as e:
        error_msg = f"Update failed: {e}"
        console.print(f"[red]{error_msg}[/red]")
        print(error_msg)
        return False, error_msg
