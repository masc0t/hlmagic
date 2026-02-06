# 🪄 HLMagic: Autonomous WSL2 Homelab Agent

HLMagic transforms your standard WSL2 environment into a high-performance, offline media and AI stack. No Docker Desktop, no cloud dependencies—just your hardware and local AI.

## 🚀 One-Line Installation (Windows PowerShell)

Open PowerShell as Administrator and run:

```powershell
iex (iwr -useb https://raw.githubusercontent.com/masc0t/hlmagic/main/install.ps1)
```

**What this does:**
1.  **WSL2 Prep:** Ensures WSL2 is enabled and Ubuntu 24.04 is installed.
2.  **Systemd Setup:** Automatically configures `systemd=true` and hardware passthrough.
3.  **Local AI Brain:** Installs Ollama for private, local reasoning.
4.  **Auto-Launcher:** Creates a **Desktop Shortcut** to start the server and open the UI.
5.  **Launch:** Opens the **HLMagic Web Interface** (http://localhost:8000) to set your passphrase.

## 🧠 The Web Interface

HLMagic is fully managed via a modern web interface. No terminal knowledge required.

*   **Chat:** Tell your homelab what to do in plain English. *"Setup Plex and mount my D: drive."*
*   **Dashboard:** Monitor service health, start/stop containers, and view hardware detection in real-time.
*   **Settings:** Enable **Full Debug Mode** and view live logs for easy troubleshooting.
*   **Auto-Updates:** Code and dependencies stay fresh automatically.

## 🛠️ Features
- **Zero-Config Hardware Acceleration:** Automatic support for NVIDIA, AMD (RDNA 3/4), and Intel GPUs.
- **Local-First AI:** Private LLM reasoning via Ollama.
- **Docker Engine (Direct):** High-performance container engine running directly in WSL2.
- **Secure by Design:** Password-protected access and strict volume auditing.

## 📂 Project Structure
- `/hlmagic/server.py`: FastAPI backend and Dashboard UI.
- `/hlmagic/utils/agent.py`: The autonomous AI "Brain".
- `/install.ps1`: The Windows-to-WSL one-line installer.
- `/start_hlmagic.ps1`: Background service starter and browser launcher.

---
*Built for the privacy-conscious homelab enthusiast.*