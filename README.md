# 🪄 HLMagic: The Autonomous WSL2 Homelab Agent

**HLMagic** is a "zero-config" autonomous agent designed specifically for **WSL2 (Ubuntu 24.04)**. It transforms a fresh WSL2 instance into a high-performance, local-AI-powered media stack with a single command. 

No Docker Desktop. No Cloud APIs. Just local hardware and local intelligence.

---

## ✨ The "Magic" Features

- **🛡️ Self-Healing WSL2:** Automatically patches `/etc/wsl.conf` to enable `systemd` and ensures your environment is ready for modern Linux services.
- **🚀 Universal Hardware Engine:** Detects and configures **Intel (QuickSync)**, **NVIDIA (CUDA)**, and **AMD (ROCm)** GPUs automatically. It even handles 2026-era RDNA 4 overrides (`GFX1200`) for the latest hardware.
- **🧠 Local AI Brain:** Powered by **Ollama**, the agent understands natural language instructions like *"Setup Plex using my D: drive for movies"* and executes them by writing secure, optimized Docker Compose files.
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

Run this single command to install HLMagic and initialize your environment:

```bash
pip install git+https://github.com/youruser/hlmagic.git && hlmagic init
```
*Note: If systemd was just enabled, you will be prompted to run `wsl --shutdown` in Windows and restart your terminal.*

### 3. Talk to the Agent
Once initialized, just tell HLMagic what you want:

```bash
hlmagic "Setup Plex and Sonarr, use /mnt/d/Media for storage"
```

---

## 🏗️ Technical Architecture

- **CLI Framework:** [Typer](https://typer.tiangolo.com/) & [Rich](https://github.com/Textualize/rich)
- **AI Integration:** [Ollama Python](https://github.com/ollama/ollama-python)
- **Hardware Detection:** `lspci` Vendor ID mapping (`10de`, `1002`, `8086`)
- **Config Standard:** All services are deployed to `/opt/hlmagic/services/` with a consistent `PUID/PGID` of `1000`.

---

## 🛡️ Safety & Constraints
- **Path Confinement:** The agent can only write to `/opt/hlmagic/`.
- **User-Space Only:** HLMagic never attempts to install Linux kernel drivers (which would break WSL2); it only installs the necessary user-space libraries and container toolkits.
- **Non-Interactive:** Designed for high-speed deployment with `-y` flags for all package managers.

---

## 📜 License
MIT
