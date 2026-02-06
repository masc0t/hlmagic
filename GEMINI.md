# HLMagic: Autonomous WSL2 Homelab Agent

## Project Overview
**HLMagic** is an autonomous, local-AI agent designed to transform a standard WSL2 (Ubuntu 24.04) environment into a high-performance, offline media and AI stack. It automates the setup of Ollama, Docker, and hardware acceleration across Intel, NVIDIA, and AMD GPUs without relying on Docker Desktop or cloud-based reasoning.

## Core Mission
- **Hardware Agnostic:** Automatically detects and configures any GPU (NVIDIA, AMD, Intel) passed through from Windows.
- **Local-First:** All LLM reasoning is handled locally via Ollama.
- **Resource Efficient:** Installs Docker Engine directly in WSL2; uses a "60/40" VRAM/RAM split to optimize performance between the AI "Brain" and the Windows host.
- **Secure:** Enforces strict security policies for automated file generation, preventing path traversal and dangerous volume mounts.

## Supported Services (Optimized Templates)
HLMagic includes built-in, hardware-aware templates for:
- **AI:** Ollama
- **Media Server:** Plex, Jellyfin
- **Arr Stack:** Sonarr, Radarr, Lidarr
- **Management:** Overseerr

## Technical Architecture
### 1. The PowerShell Bridge (Phase 1)
- Automates WSL2 installation and hardware passthrough from Windows.
- Eliminates the need for users to touch the Linux terminal.

### 2. The Web Brain (Phase 2)
- **FastAPI Backend:** Runs inside WSL2, exposing the HLMagic Agent.
- **ChatGPT-Style UI:** A modern, reactive web interface for all interactions.
- **Automatic Init:** The first time the UI opens, it triggers the `hlmagic init` logic via the agent.

### 3. Universal Hardware Engine (Phase 3)
- **Detection:** Uses `lspci` Vendor IDs (`10de`, `1002`, `8086`) to identify GPUs.
- **Optimized Templates:** Generates Docker Compose configurations that are automatically tuned for the detected hardware (e.g., adding `nvidia` runtime or `devices: [/dev/dri]`).
- **Resource Management:** 60/40 VRAM split logic integrated into agent context.

### 3. The Brain (Agent)
- **Natural Language Control:** `hlmagic "Setup Plex using my D: drive"`
- **Toolbox:**
    - `scan_wsl_storage`: Finds Windows drives mounted in `/mnt/`.
    - `get_optimized_template`: Retrieves safe, hardware-aware Compose templates.
    - `write_compose_file`: securely writes to `/opt/hlmagic/services/`.
- **Security Safeguards:**
    - **Path Confinement:** Strictly limits writes to `/opt/hlmagic`.
    - **Volume Audit:** Blocks mounting host root `/` or system paths `/etc`, `/proc`.
    - **Privilege Drop:** Prevents `privileged: true` containers.

## Development Commands
### Initialization
```bash
# Install in editable mode for development
pip install -e .

# Run the sanity check and hardware setup
hlmagic init
```

### Usage
```bash
# Deploy a service with natural language
hlmagic run "Deploy Plex and Sonarr"
```

## Current Status
- [x] Project Scaffolding & CLI Structure
- [x] WSL2 /etc/wsl.conf patching logic
- [x] Universal Hardware Scanner (LSPCI-based)
- [x] GPU-specific installation profiles
- [x] Local Tool Binding (Storage Scan, Service Check)
- [x] Secure Docker Compose Writer (Input Validation, Path Traversal Protection)
- [x] Hardware-Aware Templates (Plex, Ollama, Sonarr, Radarr, Lidarr, Jellyfin, Overseerr)
- [x] Agent Integration with Ollama