import ollama
import json
import subprocess
from typing import List, Dict, Any
from rich.console import Console
from hlmagic.utils import tools, config
from hlmagic.utils.hardware import HardwareScanner

console = Console()

class HLMagicAgent:
    def __init__(self, model: str = None):
        self.model = model or config.get_model()
        
        # Ensure Ollama has the model
        self._ensure_model()
        
        # Get Hardware Context
        scanner = HardwareScanner()
        scanner.scan() # Detecting current state
        hw_env = scanner.get_env_vars()
        primary_gpu = scanner.primary_gpu.value
        
        self.system_prompt = (
            "You are HLMagic, an autonomous Homelab Agent for WSL2. "
            "You help users setup media and AI stacks (Ollama, Docker, Plex, Sonarr, etc.). "
            "You have access to local tools. Use them to gather information or perform actions. "
            "Always prefer /opt/hlmagic/ for configurations. "
            f"Current User IDs: {tools.get_user_ids()} "
            f"Hardware Acceleration: {primary_gpu.upper()} "
            f"Resource Constraints: {json.dumps(hw_env)} "
            "IMPORTANT: When writing docker-compose.yml files, ALWAYS try to use 'get_optimized_template' "
            "first to get a safe, hardware-aware base. Modify only if necessary."
        )
        self.available_tools = {
            "scan_wsl_storage": tools.scan_wsl_storage,
            "write_compose_file": tools.write_compose_file,
            "check_service_status": tools.check_service_status,
            "get_optimized_template": tools.get_optimized_template
        }

    def _ensure_model(self):
        """Check if model exists in Ollama, pull if missing."""
        try:
            models = ollama.list()
            model_names = [m['name'] for m in models.get('models', [])]
            
            target = self.model
            if ":" not in target:
                target += ":latest"
            
            if target not in model_names and self.model not in model_names:
                console.print(f"[yellow]Model '{self.model}' not found. Pulling...[/yellow]")
                subprocess.run(["ollama", "pull", self.model], check=True)
                console.print(f"[green]✓ Model '{self.model}' pulled.[/green]")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not verify/pull model '{self.model}': {e}[/yellow]")

    def run(self, user_input: str):
        """Main loop for processing user requests with tool support."""
        messages = [
            {'role': 'system', 'content': self.system_prompt},
            {'role': 'user', 'content': user_input}
        ]

        console.print(f"[bold cyan]HLMagic Brain thinking...[/bold cyan]")
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=messages,
                tools=[
                    {
                        'type': 'function',
                        'function': {
                            'name': 'scan_wsl_storage',
                            'description': 'Identify Windows mount points for media.',
                        },
                    },
                    {
                        'type': 'function',
                        'function': {
                            'name': 'check_service_status',
                            'description': 'Check if docker or ollama services are running.',
                            'parameters': {
                                'type': 'object',
                                'properties': {
                                    'service_name': {'type': 'string'},
                                },
                            },
                        },
                    },
                    {
                        'type': 'function',
                        'function': {
                            'name': 'get_optimized_template',
                            'description': 'Get a safe, hardware-optimized docker-compose template for a service (e.g., plex, ollama).',
                            'parameters': {
                                'type': 'object',
                                'properties': {
                                    'service_name': {'type': 'string'},
                                },
                                'required': ['service_name'],
                            },
                        },
                    },
                    {
                        'type': 'function',
                        'function': {
                            'name': 'write_compose_file',
                            'description': 'Generate a docker-compose.yml for a service.',
                            'parameters': {
                                'type': 'object',
                                'properties': {
                                    'service_name': {'type': 'string'},
                                    'compose_content': {'type': 'string'},
                                },
                                'required': ['service_name', 'compose_content'],
                            },
                        },
                    }
                ]
            )

            # Handle tool calls
            if response.get('message', {}).get('tool_calls'):
                for tool_call in response['message']['tool_calls']:
                    function_name = tool_call['function']['name']
                    args = tool_call['function']['arguments']
                    
                    console.print(f"[yellow]Action: Calling tool {function_name}...[/yellow]")
                    
                    if function_name in self.available_tools:
                        result = self.available_tools[function_name](**args)
                        messages.append(response['message'])
                        messages.append({
                            'role': 'tool',
                            'content': str(result),
                        })
                
                # Get final response after tool execution
                final_response = ollama.chat(model=self.model, messages=messages)
                console.print(f"\n[bold green]HLMagic:[/bold green] {final_response['message']['content']}")
            else:
                console.print(f"\n[bold green]HLMagic:[/bold green] {response['message']['content']}")

        except Exception as e:
            console.print(f"[red]Error interacting with Ollama: {e}[/red]")
            console.print("[yellow]Ensure Ollama is running: 'systemctl status ollama'[/yellow]")
            console.print("[dim]Hint: You might need to pull the model first: 'ollama pull llama3'[/dim]")
