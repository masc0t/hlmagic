import typer
from typing import Optional
from rich.console import Console
from hlmagic.commands import init

app = typer.Typer(help="HLMagic: Your Local Homelab Agent.")
console = Console()

# Add subcommands
app.add_typer(init.app, name="init")

@app.command()
def run(prompt: str):
    """Pass a natural language instruction to the HLMagic Brain."""
    from hlmagic.utils.agent import HLMagicAgent
    agent = HLMagicAgent()
    agent.run(prompt)

@app.command()
def status():
    """Show the status of all HLMagic services."""
    from rich.table import Table
    from pathlib import Path
    import subprocess

    console.print("[bold]HLMagic Service Status[/bold]\n")
    
    base_path = Path("/opt/hlmagic/services")
    if not base_path.exists():
        console.print("[yellow]No services found. Run 'hlmagic init' or ask the brain to setup a service.[/yellow]")
        return

    table = Table(title="Deployed Services")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Path", style="dim")

    for service_dir in base_path.iterdir():
        if service_dir.is_dir() and (service_dir / "docker-compose.yml").exists():
            name = service_dir.name
            try:
                # Check docker status
                res = subprocess.run(
                    ["sudo", "docker", "compose", "ps", "--format", "json"],
                    cwd=service_dir, capture_output=True, text=True
                )
                if res.returncode == 0 and res.stdout.strip():
                    status_str = "Running" # Simple check, can be parsed more deeply
                else:
                    status_str = "Stopped/Unknown"
            except Exception:
                status_str = "Error"
            
            table.add_row(name, status_str, str(service_dir))

    console.print(table)

@app.command()
def purge():
    """UNINSTALL: Stop all services and remove /opt/hlmagic/."""
    import shutil
    import subprocess
    from pathlib import Path

    confirm = typer.confirm("This will stop all HLMagic containers and DELETE all configurations in /opt/hlmagic. Are you sure?")
    if not confirm:
        raise typer.Abort()

    console.print("[yellow]Purging HLMagic...[/yellow]")
    
    base_path = Path("/opt/hlmagic")
    services_path = base_path / "services"

    if services_path.exists():
        for service_dir in services_path.iterdir():
            if service_dir.is_dir() and (service_dir / "docker-compose.yml").exists():
                console.print(f"Stopping service: {service_dir.name}...")
                subprocess.run(["sudo", "docker", "compose", "down"], cwd=service_dir)

    console.print("[red]Deleting /opt/hlmagic/...[/red]")
    subprocess.run(["sudo", "rm", "-rf", str(base_path)])
    
    console.print("[green]✓ HLMagic has been purged.[/green]")

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, prompt: Optional[str] = typer.Argument(None)):
    """
    HLMagic: Autonomous WSL2 Homelab Agent. 
    
    If a prompt is provided without a command, it defaults to 'run'.
    """
    if ctx.invoked_subcommand is None and prompt:
        from hlmagic.utils.agent import HLMagicAgent
        agent = HLMagicAgent()
        agent.run(prompt)
    elif ctx.invoked_subcommand is None:
        print(ctx.get_help())

if __name__ == "__main__":
    app()
