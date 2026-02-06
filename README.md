# 🪄 HLMagic: Autonomous WSL2 Homelab Agent

HLMagic is a "zero-config" assistant that transforms your standard Windows computer into a high-performance, offline media and AI center. It automates the setup of Docker, Ollama, and hardware acceleration across NVIDIA, AMD, and Intel GPUs—all managed through a beautiful, local web interface.

## 🚀 One-Line Installation

Open **PowerShell as Administrator** and run:

```powershell
iex (iwr -useb https://raw.githubusercontent.com/masc0t/hlmagic/main/install.ps1)
```

### What happens next?
1.  **Environment Prep:** Ensures WSL2 is enabled and Ubuntu 24.04 is installed.
2.  **Hardware Injection:** Automatically bridges your Windows GPU (NVIDIA, AMD RDNA 3/4, or Intel) into Linux.
3.  **Systemd Management:** Installs HLMagic as a background service for 24/7 availability.
4.  **Auto-Launcher:** Creates a **Desktop Shortcut** to start the agent and open the UI.
5.  **Secure Setup:** Prompts you to set a private passphrase on first launch.

---

## 🧠 The Management Interface

HLMagic eliminates the need for the Linux terminal. Manage your entire stack at **http://localhost:8000**.

### 💬 Chat (Autonomous Brain)
Talk to your homelab in plain English. The HLMagic Agent uses its own local LLM to execute complex tasks:
*   *"Setup Plex and mount my D: drive for movies."*
*   *"Install Sonarr and Radarr."*
*   *"Check my GPU status."*

### 📊 Dashboard (Service Control)
A central hub for your homelab health:
*   **Service Grid:** View and control (Start/Stop) all deployed containers.
*   **System Health:** Real-time status of Docker, Ollama, and mDNS.
*   **Hardware Context:** Detailed view of GPU detection and Windows drive mount points.

### ⚙️ Settings (Self-Healing)
*   **Full Debug Mode:** Toggle verbose logging for advanced troubleshooting.
*   **Live Log Viewer:** Watch systemd and update logs in real-time.
*   **Auto-Updates:** Hourly background checks ensure you always have the latest fixes.

---

## 🏎️ Hardware Acceleration

HLMagic is built for high-performance workloads:
- **NVIDIA:** Automatic CUDA runtime and container toolkit configuration.
- **AMD (RDNA 3/4):** Native **ROCm 7.2** support with GFX12 overrides for the RX 9000-series.
- **Intel:** OneAPI and QuickSync passthrough for transcoding.
- **Direct Docker:** Runs Docker Engine directly in WSL (skipping Docker Desktop overhead).

---

## ❓ Common Troubleshooting

### GPU not detected? (`/dev/dri` missing)
1.  **Check BIOS:** Ensure **IOMMU** is Enabled and **Secure Boot** is set to a "WSL-friendly" state (or disabled if handshake fails).
2.  **Driver Version:** For RDNA 4 (RX 9000), ensure you are using the **AMD Adrenalin Preview for WSL2** driver.
3.  **Hard Reset:** Run `wsl --shutdown` in PowerShell to re-initialize the hardware bridge.

### Port Conflict?
If you see a "Port 8000 in use" error, HLMagic will automatically attempt to clear it. If it persists, use the **Restart** button in the Settings tab.

---
*Built for privacy, powered by local AI.*
