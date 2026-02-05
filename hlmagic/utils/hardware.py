import shutil
import subprocess
import os
import psutil
from enum import Enum
from pathlib import Path
from typing import List, Dict, Tuple
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

class GPUVendor(str, Enum):
    NVIDIA = "nvidia"
    AMD = "amd"
    INTEL = "intel"
    NONE = "none"

class HardwareScanner:
    def __init__(self):
        self.gpus: List[GPUVendor] = []
        self.primary_gpu: GPUVendor = GPUVendor.NONE
        self.vram_split: Dict[str, str] = {} # e.g. {"OLLAMA_NUM_GPU": "..."}

    def _ensure_dependencies(self):
        """Ensure system tools like lspci, curl, and gnupg are installed."""
        deps = {
            "lspci": "pciutils",
            "curl": "curl",
            "gpg": "gnupg",
            "clinfo": "clinfo"
        }
        
        missing_pkgs = [pkg for cmd, pkg in deps.items() if not shutil.which(cmd)]
        
        if missing_pkgs:
            console.print(f"[yellow]Missing dependencies: {', '.join(missing_pkgs)}. Installing...[/yellow]")
            try:
                # Update first if it's a fresh install
                subprocess.run(["sudo", "apt-get", "update"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["sudo", "apt-get", "install", "-y"] + missing_pkgs, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                console.print(f"[green]✓ Installed {', '.join(missing_pkgs)}.[/green]")
            except subprocess.CalledProcessError:
                console.print(f"[red]Failed to install dependencies ({', '.join(missing_pkgs)}). Some features may fail.[/red]")

    def scan(self) -> List[GPUVendor]:
        """Detects available GPUs using Vendor IDs (lspci) and /dev/dxg."""
        self._ensure_dependencies()
        detected = []
        
        # 1. lspci Detection (Primary method)
        try:
            # -nn gets numeric IDs
            lspci_nn = subprocess.run(["lspci", "-nn"], capture_output=True, text=True).stdout.lower()
            lspci_raw = subprocess.run(["lspci"], capture_output=True, text=True).stdout.lower()
            
            if "10de" in lspci_nn or "nvidia" in lspci_raw: # NVIDIA
                detected.append(GPUVendor.NVIDIA)
            if "1002" in lspci_nn or any(x in lspci_raw for x in ["amd", "radeon", "navi", "advanced micro devices"]): # AMD
                detected.append(GPUVendor.AMD)
            if "8086" in lspci_nn or "intel" in lspci_raw: # Intel
                 detected.append(GPUVendor.INTEL)
                     
        except FileNotFoundError:
            pass

        # 2. Check /dev/dxg (WSL2 bridge)
        # If lspci failed to show the physical IDs (common in some WSL versions/kernels),
        # but /dev/dxg exists, we have GPU passthrough.
        if Path("/dev/dxg").exists() and not detected:
            console.print("[blue]DirectX Graphics Link (/dev/dxg) detected. Identifying vendor via alternative means...[/blue]")
            
            # Try to find vendor via /proc/pal (AMD) or nvidia-smi
            if Path("/proc/amdgpu").exists() or Path("/sys/module/amdgpu").exists():
                detected.append(GPUVendor.AMD)
            elif Path("/proc/driver/nvidia").exists() or shutil.which("nvidia-smi"):
                detected.append(GPUVendor.NVIDIA)
            else:
                # If we have dxg but can't find specific drivers yet, 
                # we'll look for any "Microsoft" or "Basic Render" string in lspci which often masks the real GPU
                lspci_raw = subprocess.run(["lspci"], capture_output=True, text=True).stdout
                if "Microsoft" in lspci_raw or "Basic Render" in lspci_raw or "GFX" in lspci_raw:
                    # In this case, we have a passthrough but it's generic.
                    # Given the RX 9070 XT context, we will fallback to AMD if it's the only likely choice.
                    detected.append(GPUVendor.AMD)
                    
        # Multi-GPU Logic: If we found Intel (Integrated) and another (Discrete), prefer the Discrete one.
        if len(detected) > 1 and GPUVendor.INTEL in detected:
             # Keep Intel but ensure it's not the primary if others exist
             pass

        if not detected and Path("/dev/dxg").exists():
            console.print("[yellow]GPU passthrough detected via /dev/dxg, but vendor identification is ambiguous.[/yellow]")

        self.gpus = list(set(detected))
        self._assign_roles()
        return self.gpus

    def _assign_roles(self):
        """Logic for Dual-GPU setups and VRAM calculation."""
        if not self.gpus:
            self.primary_gpu = GPUVendor.NONE
            return

        # Priority: NVIDIA > AMD > INTEL for primary AI tasks
        if GPUVendor.NVIDIA in self.gpus:
            self.primary_gpu = GPUVendor.NVIDIA
        elif GPUVendor.AMD in self.gpus:
            self.primary_gpu = GPUVendor.AMD
        elif GPUVendor.INTEL in self.gpus:
            self.primary_gpu = GPUVendor.INTEL
            
        self._calculate_optimization()

    def _calculate_optimization(self):
        """Apply the 60/40 Rule for VRAM/RAM."""
        # Getting VRAM is hard in a universal way without specific tools installed.
        # We will approximate or use total system RAM if VRAM unknown (as shared memory often applies in WSL/APUs)
        # For discrete GPUs passed through, we rely on the user or defaults.
        # However, we can detect System RAM easily.
        
        mem = psutil.virtual_memory()
        total_ram_gb = mem.total / (1024 ** 3)
        
        # Heuristic: In WSL2, we often share system RAM.
        # If we can't detect VRAM, we assume a safe split of available system RAM.
        # But let's try to be smarter.
        
        # 60% for Brain (Ollama)
        brain_vram = int(total_ram_gb * 0.6)
        
        # This is primarily for Ollama environment variables or Docker limits
        self.vram_split = {
            "HLMAGIC_BRAIN_RAM_GB": str(brain_vram),
            "HLMAGIC_RESERVED_RAM_GB": str(int(total_ram_gb - brain_vram))
        }

    def install_drivers(self):
        """Orchestrates driver installation based on detected hardware."""
        if not self.gpus:
            console.print("[yellow]No supported GPUs detected for acceleration.[/yellow]")
            return

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            
            # Common setup
            progress.add_task(description="Configuring user permissions (render/video groups)...", total=None)
            self._add_user_groups()

            if GPUVendor.NVIDIA in self.gpus:
                task = progress.add_task(description="Installing NVIDIA Stack (Toolkit & Docker)...", total=None)
                self._install_nvidia()

            if GPUVendor.AMD in self.gpus:
                task = progress.add_task(description="Installing AMD Stack (ROCm & Overrides)...", total=None)
                self._install_amd()

            if GPUVendor.INTEL in self.gpus:
                task = progress.add_task(description="Installing Intel Stack (OneAPI/Level-Zero)...", total=None)
                self._install_intel()

    def _add_user_groups(self):
        user = os.getenv("USER")
        if not user:
            return
        subprocess.run(["sudo", "usermod", "-aG", "render,video", user], capture_output=True)

    def _install_nvidia(self):
        if shutil.which("nvidia-ctk"):
            return

        # Distribution-agnostic setup for Ubuntu 24.04 (noble)
        cmds = [
            "curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg",
            "curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list",
            "sudo apt-get update",
            "sudo apt-get install -y nvidia-container-toolkit nvidia-docker2"
        ]
        
        for cmd in cmds:
            subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL)
            
        subprocess.run(["sudo", "nvidia-ctk", "runtime", "configure", "--runtime=docker"], check=True)
        # We don't restart docker here, usually needs systemd restart or wsl restart

    def _install_amd(self):
        """Install AMD ROCm stack for WSL2."""
        if shutil.which("amdgpu-install"):
            return

        # Noble (24.04) specific installer
        deb_url = "https://repo.radeon.com/amdgpu-install/6.2/ubuntu/noble/amdgpu-install_6.2.60200-1_all.deb"
        deb_path = "/tmp/amdgpu-install.deb"

        try:
            console.print("[yellow]Downloading AMD GPU installer...[/yellow]")
            subprocess.run(["curl", "-L", deb_url, "-o", deb_path], check=True)
            
            console.print("[yellow]Installing AMD GPU installer package...[/yellow]")
            subprocess.run(["sudo", "apt-get", "install", "-y", deb_path], check=True)
            
            console.print("[yellow]Running AMD GPU installation (ROCm/WSL usecase)...[/yellow]")
            # --no-dkms is CRITICAL for WSL2 as we use the host kernel drivers
            subprocess.run(["sudo", "amdgpu-install", "-y", "--usecase=wsl,rocm", "--no-dkms"], check=True)
            
            # Cleanup
            os.remove(deb_path)
        except Exception as e:
            console.print(f"[red]Error installing AMD stack: {e}[/red]")
            return

        # 3. RDNA 4 Override Check (Hypothetical for GFX1200)
        try:
            lspci = subprocess.run(["lspci"], capture_output=True, text=True).stdout
            if "Navi 4" in lspci or "GFX1200" in lspci: 
                 self._append_to_bashrc("export HSA_OVERRIDE_GFX_VERSION=12.0.0")
        except Exception:
            pass

    def _install_intel(self):
        """Install Intel Graphics stack for WSL2."""
        # 1. Add Repository
        cmds = [
            "wget -qO - https://repositories.intel.com/gpu/intel-graphics.key | sudo gpg --dearmor --yes -o /usr/share/keyrings/intel-graphics.gpg",
            "echo 'deb [arch=amd64,i386 signed-by=/usr/share/keyrings/intel-graphics.gpg] https://repositories.intel.com/gpu/ubuntu noble unified' | sudo tee /etc/apt/sources.list.d/intel.gpu.noble.list",
            "sudo apt-get update"
        ]
        
        # 2. Install Packages
        pkgs = [
            "intel-opencl-icd", "intel-level-zero-gpu", "intel-media-va-driver-non-free",
            "libze-dev", "libvpl2", "libigdgmm12", "va-driver-all"
        ]

        try:
            for cmd in cmds:
                subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL)
            
            subprocess.run(["sudo", "apt-get", "install", "-y"] + pkgs, check=True, stdout=subprocess.DEVNULL)
        except Exception as e:
            console.print(f"[red]Error installing Intel stack: {e}[/red]")

    def _append_to_bashrc(self, line: str):
        bashrc = Path(os.path.expanduser("~/.bashrc"))
        if bashrc.exists():
            content = bashrc.read_text()
            if line not in content:
                with open(bashrc, "a") as f:
                    f.write(f"\n{line}\n")

    def validate_installation(self):
        """Runs a validation command based on the primary GPU."""
        console.print("[bold]Validating GPU Configuration...[/bold]")
        
        if self.primary_gpu == GPUVendor.NVIDIA:
             if shutil.which("nvidia-smi"):
                 subprocess.run(["nvidia-smi"], check=False)
             else:
                 console.print("[red]Validation Failed: nvidia-smi not found.[/red]")

        elif self.primary_gpu == GPUVendor.AMD:
             if shutil.which("clinfo"): # or rocm-smi
                 subprocess.run(["clinfo"], check=False)
             else:
                 console.print("[yellow]Validation: clinfo not found. Install 'clinfo' package to verify.[/yellow]")

        elif self.primary_gpu == GPUVendor.INTEL:
             # Intel doesn't have a ubiquitous 'smi' tool installed by default, usually 'clinfo' works for OpenCL
             if shutil.which("clinfo"):
                 subprocess.run(["clinfo"], check=False)
             else:
                 console.print("[yellow]Validation: clinfo not found.[/yellow]")

    def get_env_vars(self) -> Dict[str, str]:
        env = self.vram_split.copy()
        if self.primary_gpu == GPUVendor.AMD:
             # Re-check for override necessity or just include if we set it
             pass 
        return env