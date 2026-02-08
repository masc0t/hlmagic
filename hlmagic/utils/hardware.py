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
        if os.name != 'posix':
            return # Skip on Windows

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
        
        # 1. lspci Detection (Primary method for Linux)
        if shutil.which("lspci"):
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

        # 2. Windows-Specific Detection (if lspci not found)
        if os.name == 'nt' and not detected:
            try:
                # Check for NVIDIA
                if shutil.which("nvidia-smi"):
                    detected.append(GPUVendor.NVIDIA)
                
                # Check for AMD/Intel via PowerShell
                res = subprocess.run(["powershell", "-NoProfile", "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"], capture_output=True, text=True)
                gpu_names = res.stdout.lower()
                
                if "nvidia" in gpu_names:
                    if GPUVendor.NVIDIA not in detected: detected.append(GPUVendor.NVIDIA)
                if "amd" in gpu_names or "radeon" in gpu_names:
                    if GPUVendor.AMD not in detected: detected.append(GPUVendor.AMD)
                if "intel" in gpu_names:
                    if GPUVendor.INTEL not in detected: detected.append(GPUVendor.INTEL)
            except:
                pass

        # 3. Check /dev/dxg (WSL2 bridge)
        # If lspci failed to show the physical IDs (common in some WSL versions/kernels),
        # but /dev/dxg exists, we have GPU passthrough.
        if Path("/dev/dxg").exists():
            # Check for AMD-specific indicators first
            if Path("/proc/amdgpu").exists() or Path("/sys/module/amdgpu").exists() or shutil.which("rocminfo") or shutil.which("clinfo"):
                if GPUVendor.AMD not in detected:
                    detected.append(GPUVendor.AMD)
            
            # If still nothing detected but dxg is there, look at lspci raw strings
            if not detected:
                lspci_raw = subprocess.run(["lspci"], capture_output=True, text=True).stdout.lower()
                if any(x in lspci_raw for x in ["microsoft", "basic render", "gfx"]):
                    # On many modern RDNA 3/4 systems, it shows as a generic MS driver initially.
                    # We will assume AMD if rocminfo or clinfo are present (set by our installer)
                    if shutil.which("clinfo"):
                        detected.append(GPUVendor.AMD)
                    elif shutil.which("nvidia-smi"):
                        detected.append(GPUVendor.NVIDIA)
                    
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
            t1 = progress.add_task(description="Configuring user permissions...", total=None)
            self._add_user_groups()
            progress.update(t1, description="[green]✓ User permissions configured.[/green]", completed=True)

            if GPUVendor.NVIDIA in self.gpus:
                t2 = progress.add_task(description="Installing NVIDIA Stack...", total=None)
                self._install_nvidia()
                progress.update(t2, description="[green]✓ NVIDIA Stack installed.[/green]", completed=True)

            if GPUVendor.AMD in self.gpus:
                t3 = progress.add_task(description="Installing AMD Stack (ROCm)...", total=None)
                self._install_amd()
                progress.update(t3, description="[green]✓ AMD Stack installed.[/green]", completed=True)

            if GPUVendor.INTEL in self.gpus:
                t4 = progress.add_task(description="Installing Intel Stack...", total=None)
                self._install_intel()
                progress.update(t4, description="[green]✓ Intel Stack installed.[/green]", completed=True)

    def _add_user_groups(self):
        user = os.getenv("USER")
        if not user:
            return
        # Use -f to avoid errors if already present, and pipe yes just in case
        subprocess.run(f"yes | sudo usermod -aG render,video {user}", shell=True, capture_output=True)

    def _install_nvidia(self):
        if shutil.which("nvidia-ctk"):
            return

        # Distribution-agnostic setup for Ubuntu 24.04 (noble)
        cmds = [
            "curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor --yes -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg",
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
        try:
            # 1. Add ROCm Repository for Noble (Ubuntu 24.04)
            cmds = [
                "sudo mkdir -p /etc/apt/keyrings",
                "curl -fsSL https://repo.radeon.com/rocm/rocm.gpg.key | sudo gpg --dearmor --yes -o /etc/apt/keyrings/rocm.gpg",
                "echo 'deb [arch=amd64 signed-by=/etc/apt/keyrings/rocm.gpg] https://repo.radeon.com/rocm/apt/7.2 noble main' | sudo tee /etc/apt/sources.list.d/rocm.list",
                "echo 'deb [arch=amd64 signed-by=/etc/apt/keyrings/rocm.gpg] https://repo.radeon.com/amdgpu/30.30/ubuntu noble main' | sudo tee /etc/apt/sources.list.d/amdgpu.list",
                "sudo apt-get update"
            ]
            for cmd in cmds:
                subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL)

            # 2. Install the AMD GPU installer package if not present (ROCm 7.2)
            deb_url = "https://repo.radeon.com/amdgpu-install/7.2/ubuntu/noble/amdgpu-install_7.2.70200-1_all.deb"
            deb_path = "/tmp/amdgpu-install.deb"

            if not shutil.which("amdgpu-install"):
                console.print("[yellow]Downloading AMD GPU installer (v7.2)...[/yellow]")
                subprocess.run(["curl", "-L", deb_url, "-o", deb_path], check=True)
                subprocess.run(["sudo", "apt-get", "install", "-y", deb_path], check=True)
            
            console.print("[yellow]Running AMD GPU installation (WSL + ROCm usecase)...[/yellow]")
            console.print("[dim]Log: /tmp/hlmagic_amd_install.log[/dim]")
            
            env = os.environ.copy()
            env["DEBIAN_FRONTEND"] = "noninteractive"
            env["UCF_FORCE_CONFFOLD"] = "1" 
            
            # Important: Use --usecase=wsl,rocm for modern AMD support in WSL
            log_file = "/tmp/hlmagic_amd_install.log"
            cmd = f"yes | sudo -E amdgpu-install -y --usecase=wsl,rocm --no-dkms > {log_file} 2>&1"
            result = subprocess.run(cmd, shell=True, env=env)
            
            if result.returncode != 0:
                console.print("[yellow]amdgpu-install failed, attempting manual component installation...[/yellow]")
                pkgs = ["rocm-core", "rocm-smi-lib", "clinfo", "rocm-opencl-runtime", "hsa-rocr-dev"]
                apt_cmd = f"sudo -E apt-get install -y -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold {' '.join(pkgs)} >> {log_file} 2>&1"
                subprocess.run(apt_cmd, shell=True, env=env, check=True)
            
            # Cleanup
            if os.path.exists(deb_path):
                os.remove(deb_path)
        except Exception as e:
            console.print(f"[red]Error installing AMD stack: {e}[/red]")
            return

        # 3. RDNA 4 / Navi 4 Override Check
        try:
            # Check for RX 9000 series or GFX12 architecture
            lspci = subprocess.run(["lspci", "-nn"], capture_output=True, text=True).stdout.lower()
            # 7550 is the RX 9070 XT ID we found earlier
            if "7550" in lspci or "navi 4" in lspci or "gfx12" in lspci: 
                 console.print("[blue]RDNA 4 detected! Applying GFX12 compatibility overrides...[/blue]")
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
             # 1. Check for device nodes
             kfd_exists = Path("/dev/kfd").exists()
             dri_exists = Path("/dev/dri").exists()
             
             if not kfd_exists or not dri_exists:
                 console.print("[bold yellow]Action Required: GPU nodes not found.[/bold yellow]")
                 console.print("The drivers are installed, but WSL2 needs a full restart to map the hardware.")
                 console.print("Please run [bold cyan]wsl --shutdown[/bold cyan] in PowerShell, then restart Ubuntu.")
             
             # 2. Check clinfo
             if shutil.which("clinfo"):
                 res = subprocess.run(["clinfo"], capture_output=True, text=True)
                 if "Number of devices" in res.stdout:
                     # Extract device count
                     import re
                     count_match = re.search(r"Number of devices\s+(\d+)", res.stdout)
                     if count_match and int(count_match.group(1)) > 0:
                         console.print(f"[green]✓ AMD GPU verified ({count_match.group(1)} device(s) found).[/green]")
                     else:
                         console.print("[yellow]! AMD Platform detected, but 0 devices found. Restart recommended.[/yellow]")
             else:
                 console.print("[yellow]Validation: clinfo not found.[/yellow]")

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