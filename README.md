# 🪄 HLMagic: Autonomous WSL2 Homelab Agent

HLMagic transforms your standard WSL2 environment into a high-performance, offline media and AI stack. No Docker Desktop, no cloud dependencies—just your hardware and local AI.

## 🚀 One-Line Installation (Windows PowerShell)

Open PowerShell as Administrator and run:

```powershell
iex (iwr -useb https://raw.githubusercontent.com/masc0t/hlmagic/main/install.ps1)
```

**What this does:**
1.  **WSL2 Prep:** Ensures WSL2 is enabled and Ubuntu 24.04 is installed.
2.  **Systemd Setup:** Automatically configures `systemd=true` for Docker support.
3.  **Hardware Detection:** Identifies your GPU (NVIDIA, AMD, or Intel) and installs the correct drivers/runtimes.
4.  **Local AI Brain:** Installs Ollama for private, local reasoning.
5.  **Launch:** Opens the **HLMagic Web Interface** in your browser to begin setup.

## 🧠 The Web Interface

HLMagic is now fully managed via a ChatGPT-style web interface. Once installed, you can simply chat with your homelab:

*   *"Setup Plex and mount my D: drive for movies."*
*   *"Install Sonarr and Radarr."*
*   *"Check the status of my services."*
*   *"Update Ollama to use Llama3."*

No direct WSL connection or terminal knowledge required.

## 🛠️ Features
- **Zero-Config Hardware Acceleration:** Automatic passthrough for NVIDIA (CUDA), AMD (ROCm), and Intel (OneAPI) GPUs.
- **Local-First AI:** All reasoning happens on your machine via Ollama.
- **Docker Engine (Direct):** Runs Docker directly in WSL2 (skipping Docker Desktop overhead).
- **Secure by Design:** Strict path confinement and volume auditing for all generated configs.

## 📂 Project Structure
- `/hlmagic`: Core Python logic and Agent.
- `/hlmagic/utils/templates.py`: Hardware-aware Docker Compose templates.
- `/hlmagic/server.py`: FastAPI backend for the web interface.
- `/install.ps1`: The Windows-to-WSL bridge installer.

---
*Built for the privacy-conscious homelab enthusiast.*