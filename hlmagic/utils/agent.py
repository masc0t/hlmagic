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
        
        # Get Hardware Context
        scanner = HardwareScanner()
        scanner.scan() # Detecting current state
        hw_env = scanner.get_env_vars()
        primary_gpu = scanner.primary_gpu.value
        
        self.system_prompt = (
            "You are HLMagic, an ABSOLUTELY AUTONOMOUS Homelab Agent for WSL2. "
            "Your MISSION is to completely setup, configure, and START services for the user using your tools. "
            "CRITICAL: DO NOT explain what you are going to do. DO NOT ask for permission. DO NOT ask the user to run commands. "
            "STAY IN TOOL-CALLING MODE until the service is deployed and running. "
            "A typical sequence is: "
            "1. scan_wsl_storage (to find media drives) "
            "2. get_optimized_template (to get the base docker-compose content) "
            "3. write_compose_file (to save the file to /opt/hlmagic/services/<name>/docker-compose.yml) "
            "4. deploy_service (to create config dirs and start the container) "
            "ONLY when deploy_service returns success should you provide a final summary to the user. "
            "If a tool fails, try to fix the issue yourself using other tools. "
            "Always prefer /opt/hlmagic/ for configurations. "
            f"Current User IDs: {tools.get_user_ids()} "
            f"Hardware Acceleration: {primary_gpu.upper()} "
            f"Resource Constraints: {json.dumps(hw_env)} "
        )
        self.available_tools = {
            "scan_wsl_storage": tools.scan_wsl_storage,
            "write_compose_file": tools.write_compose_file,
            "check_service_status": tools.check_service_status,
            "get_optimized_template": tools.get_optimized_template,
            "deploy_service": tools.deploy_service
        }

    def _ensure_model(self):
        """Check if model exists in Ollama, pull if missing."""
        try:
            # The ollama-python library returns a ListResponse or similar
            # where models is a list of Model objects.
            response = ollama.list()
            # Handle different possible response structures
            models_list = response.get('models', [])
            model_names = []
            for m in models_list:
                if isinstance(m, dict):
                    model_names.append(m.get('name', ''))
                    model_names.append(m.get('model', ''))
                else:
                    model_names.append(getattr(m, 'name', ''))
                    model_names.append(getattr(m, 'model', ''))
            
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
        # Ensure Ollama has the model before running
        self._ensure_model()

        messages = [
            {'role': 'system', 'content': self.system_prompt},
            {'role': 'user', 'content': user_input}
        ]

        console.print(f"[bold cyan]HLMagic Brain thinking...[/bold cyan]")
        
        # Limit to 10 iterations to prevent infinite loops
        for _ in range(10):
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
                                                    'description': 'Retrieve the hardware-optimized docker-compose YAML content for a service. Use this output for write_compose_file.',
                                                    'parameters': {
                                                        'type': 'object',
                                                        'properties': {
                                                            'service_name': {'type': 'string'},
                                                            'mounts': {
                                                                'type': 'array',
                                                                'items': {'type': 'string'},
                                                                'description': 'Optional list of host paths to mount (e.g., ["/mnt/d/Movies"]).'
                                                            },
                                                        },
                                                        'required': ['service_name'],
                                                    },
                                                },
                                            },
                                            {
                                                'type': 'function',
                                                'function': {
                                                    'name': 'write_compose_file',
                                                    'description': 'Save docker-compose content to disk. Requires EXACT content from get_optimized_template.',
                                                    'parameters': {
                                                        'type': 'object',
                                                        'properties': {
                                                            'service_name': {'type': 'string'},
                                                            'compose_content': {'type': 'string', 'description': 'The full YAML content to write.'},
                                                        },
                                                        'required': ['service_name', 'compose_content'],
                                                    },
                                                },
                                            },                        {
                            'type': 'function',
                            'function': {
                                'name': 'deploy_service',
                                'description': 'Start a service stack. MUST be called after write_compose_file.',
                                'parameters': {
                                    'type': 'object',
                                    'properties': {
                                        'service_name': {'type': 'string'},
                                    },
                                    'required': ['service_name'],
                                },
                            },
                        }
                    ]
                )

                message = response['message']
                messages.append(message)

                # If no tool calls, the brain is done talking to us
                if not message.get('tool_calls'):
                    console.print(f"\n[bold green]HLMagic:[/bold green] {message['content']}")
                    break

                # Process tool calls
                for tool_call in message['tool_calls']:
                    function_name = tool_call['function']['name']
                    args = tool_call['function']['arguments']
                    
                    console.print(f"[yellow]Action: Calling tool {function_name} with args: {json.dumps(args)}...[/yellow]")
                    
                    if function_name in self.available_tools:
                        try:
                            result = self.available_tools[function_name](**args)
                            messages.append({
                                'role': 'tool',
                                'content': str(result),
                            })
                        except TypeError as e:
                            error_msg = f"Error: Tool {function_name} failed due to incorrect arguments: {e}"
                            console.print(f"[red]{error_msg}[/red]")
                            messages.append({
                                'role': 'tool',
                                'content': error_msg,
                            })
                    else:
                        messages.append({
                            'role': 'tool',
                            'content': f"Error: Tool {function_name} not found.",
                        })

            except Exception as e:
                console.print(f"[red]Error interacting with Ollama: {e}[/red]")
                break
        else:
            console.print("[red]Error: Brain reached maximum thought depth (10 steps).[/red]")

