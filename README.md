# 🪄 HLMagic: The Autonomous WSL2 Homelab Agent

**HLMagic** is a "zero-config" autonomous agent designed specifically for **WSL2 (Ubuntu 24.04)**. It transforms a fresh WSL2 instance into a high-performance, local-AI-powered media stack with a single command. 

No Docker Desktop. No Cloud APIs. Just local hardware and local intelligence.

---

## ✨ The "Magic" Features

- **🛡️ Self-Healing WSL2:** Automatically patches `/etc/wsl.conf` to enable `systemd` and ensures your environment is ready for modern Linux services.
- **🚀 Universal Hardware Engine:** Detects and configures **Intel (QuickSync/Arc)**, **NVIDIA (CUDA)**, and **AMD (ROCm)** GPUs automatically. Supports the latest drivers for Ubuntu 24.04 (Noble).
- **🧠 Local AI Brain:** Powered by **Ollama**, the agent understands natural language instructions like *"Setup Plex using my D: drive for movies"* and executes them by writing secure, optimized Docker Compose files. It automatically pulls the required AI models if they are missing.
- **⚙️ Resource Optimization:** Automatically applies a **60/40 VRAM split** to ensure your local LLM (The Brain) and your media server (The Muscle) coexist perfectly without crashing your host Windows OS.
- **🔒 Security Hardened:** Every file written by the agent is audited for path traversal and dangerous volume mounts (e.g., blocking access to host `/etc` or `/proc`).

---

## 🛠️ Supported Services
HLMagic comes with "Golden Templates" for the following, pre-tuned for your specific hardware:
- **AI Backend:** Ollama
- **Media Servers:** Plex, Jellyfin
- **Automation (The Arrs):** Sonarr, Radarr, Lidarr
- **Request Management:** Overseerr

---

## 🚀 Quick Start (Inside WSL2)

### 1. Install & Initialize
Run this command to install HLMagic and initialize your environment. This will auto-detect your GPU and install the necessary drivers.

```bash
pip install git+https://github.com/youruser/hlmagic.git
hlmagic init
```
*Note: If systemd was just enabled, you will be prompted to run `wsl --shutdown` in Windows and restart your terminal.*

### 2. Talk to the Agent
Once initialized, just tell HLMagic what you want:

```bash
hlmagic run "Setup Plex and Sonarr, use /mnt/d/Media for storage"
```

### 3. Manage Your Lab
Check the status of your services or clean up:

```bash
# View all running services and ports
hlmagic status

# Stop all services and remove configuration
hlmagic purge
```

---

## ⚙️ Configuration
HLMagic uses a TOML configuration file located at `~/.hlmagic/config.toml`. You can customize the AI model and other settings:

```toml
[brain]
model = "llama3"   # Change to 'mistral', 'gemma', etc.
temperature = 0.1

[storage]
base_path = "/opt/hlmagic"
```

---

## ❓ Troubleshooting

**"lspci not found" or missing dependencies?**  
`hlmagic init` will attempt to auto-install `pciutils`, `curl`, and `gnupg`. Ensure you have internet access and sudo privileges.

**Systemd warnings?**  
HLMagic relies on systemd to manage Docker. If `hlmagic init` says systemd is enabled but not running, run `wsl --shutdown` in a Windows terminal (PowerShell) and restart your WSL instance.

**Ollama model errors?**  
The agent will try to `ollama pull` the configured model automatically. If this fails, ensure Ollama is running (`systemctl status ollama`) or pull the model manually: `ollama pull llama3`.

---

## 🏗️ Technical Architecture

- **CLI Framework:** [Typer](https://typer.tiangolo.com/) & [Rich](https://github.com/Textualize/rich)
- **AI Integration:** [Ollama Python](https://github.com/ollama/ollama-python)
- **Hardware Detection:** `lspci` Vendor ID mapping (`10de`, `1002`, `8086`)
- **Config Standard:** All services are deployed to `/opt/hlmagic/services/` with a consistent `PUID/PGID` of `1000`.

---

## 📜 License
MIT