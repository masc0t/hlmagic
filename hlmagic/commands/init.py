import typer
from rich.console import Console
from hlmagic.utils import wsl, config
from hlmagic.utils.hardware import HardwareScanner

app = typer.Typer()
console = Console()

@app.command()
def init():
    """Verify WSL2 sanity and initialize HLMagic environment."""
    console.print("[bold blue]HLMagic Initializing...[/bold blue]")

    # 0. Validate Sudo Access Upfront
    if not wsl.validate_sudo():
        console.print("[red]Error: HLMagic requires sudo privileges to configure WSL and install drivers.[/red]")
        raise typer.Exit(code=1)

    if not wsl.is_wsl():
        console.print("[red]Error: HLMagic must be run inside WSL2 (Ubuntu).[/red]")
        raise typer.Exit(code=1)

    # 1. Verify WSL2 Version (Heuristic)
    if wsl.get_wsl_version() < 2.0:
        console.print("[red]Error: WSL2 is required. Found WSL1.[/red]")
        raise typer.Exit(code=1)
    console.print("[green]✓ WSL2 detected.[/green]")

    # 2. Check systemd
    systemd_enabled = wsl.ensure_systemd()
    if not systemd_enabled:
        console.print("[bold yellow]Action Required:[/bold yellow] systemd was just enabled.")
        console.print("Please run [bold cyan]wsl --shutdown[/bold cyan] from your Windows terminal, then restart WSL.")
        raise typer.Exit()
    console.print("[green]✓ systemd is enabled.[/green]")

    # 3. Universal Hardware Setup
    console.print("\n[bold]Phase 2: Universal Hardware Engine[/bold]")
    scanner = HardwareScanner()
    
    console.print("Scanning for Hardware...")
    gpus = scanner.scan()
    
    if gpus:
        gpu_names = ", ".join([g.value.upper() for g in gpus])
        console.print(f"[green]✓ Detected GPUs: {gpu_names}[/green]")
        console.print(f"[blue]  Primary: {scanner.primary_gpu.value.upper()}[/blue]")
        
        # Display optimization info
        scanner._calculate_optimization() # Refresh calc
        console.print("[dim]  Applying 60/40 VRAM/RAM Split Rules...[/dim]")
        for k, v in scanner.vram_split.items():
            console.print(f"  - {k}: {v}GB")

        # Install & Configure
        scanner.install_drivers()
        
        # Validate
        scanner.validate_installation()
        
    else:
        console.print("[yellow]! No supported acceleration hardware found. Running in CPU-only mode.[/yellow]")

    # 4. Ollama Setup
    console.print("\n[bold]Phase 3: AI Engine Setup[/bold]")
    
    if wsl.install_ollama():
        wsl.start_ollama_service()
        # Ensure the model is pulled
        target_model = config.get_model()
        wsl.pull_model(target_model)
        console.print("[green]✓ Ollama AI Engine is ready.[/green]")

    console.print("\n[bold green]HLMagic Environment Ready![/bold green]")

if __name__ == "__main__":
    app()