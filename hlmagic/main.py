import typer
from typing import Optional
from hlmagic.commands import init
from hlmagic.utils.agent import HLMagicAgent

app = typer.Typer(help="HLMagic: Your Local Homelab Agent.")

# Add subcommands
app.add_typer(init.app, name="init")

@app.command()
def run(prompt: str):
    """Pass a natural language instruction to the HLMagic Brain."""
    agent = HLMagicAgent()
    agent.run(prompt)

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, prompt: Optional[str] = typer.Argument(None)):
    """
    HLMagic: Autonomous WSL2 Homelab Agent.
    
    If a prompt is provided without a command, it defaults to 'run'.
    """
    if ctx.invoked_subcommand is None and prompt:
        agent = HLMagicAgent()
        agent.run(prompt)
    elif ctx.invoked_subcommand is None:
        print(ctx.get_help())

if __name__ == "__main__":
    app()