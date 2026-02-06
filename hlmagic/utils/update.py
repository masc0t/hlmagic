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

def apply_update():
    """Pull the latest changes and reinstall dependencies."""
    if not REPO_PATH.exists():
        return False, "Repository not found."

    try:
        console.print("[yellow]Updating HLMagic...[/yellow]")
        
        # Pull latest
        subprocess.run(["git", "pull", "origin", "main"], cwd=REPO_PATH, check=True, capture_output=True)
        
        # Re-install in editable mode to update dependencies
        venv_pip = Path("/opt/hlmagic/venv/bin/pip")
        if venv_pip.exists():
            subprocess.run([str(venv_pip), "install", "-e", "."], cwd=REPO_PATH, check=True, capture_output=True)
        else:
            # Fallback to system pip if venv not found (though it should be there)
            subprocess.run(["pip", "install", "-e", "."], cwd=REPO_PATH, check=True, capture_output=True)
            
        console.print("[green]✓ HLMagic updated successfully. Please restart the service.[/green]")
        return True, "Update applied successfully. Restarting the server is recommended."
    except Exception as e:
        console.print(f"[red]Error applying update: {e}[/red]")
        return False, f"Update failed: {e}"
