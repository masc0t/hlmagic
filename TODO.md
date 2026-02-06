# 📝 HLMagic Development Todo List

## Phase 1: Fresh Install Robustness (DONE ✅)
- [x] **Dependency Check & Install**: Auto-installs `pciutils`, `curl`, `gnupg`, `clinfo`.
- [x] **Systemd Flow Handling**: Improved detection of active systemd vs configured-only.
- [x] **Sudo Handling**: Upfront `validate_sudo` check.

## Phase 2: Hardware Engine Completion (DONE ✅)
- [x] **AMD Support**: ROCm 6.2 installer for Ubuntu 24.04 implemented.
- [x] **Intel Support**: Noble-specific repo and package stack implemented.

## Phase 3: AI & Configuration (DONE ✅)
- [x] **Configurable AI Model**: `~/.hlmagic/config.toml` support added.
- [x] **Model Puller**: Auto-pulls missing Ollama models.
- [x] **Template Injection**: (Next Step) Improve injection to be more deterministic.

## Phase 4: Quality Assurance & Safety (DONE ✅)
- [x] **Test Suite**: Security and Template tests created.
- [x] **Status Command**: `hlmagic status` implemented.
- [x] **Uninstall/Cleanup**: `hlmagic purge` implemented.

## Phase 5: Documentation (DONE ✅)

- [x] Update `README.md` with a "Troubleshooting" section for common Fresh Install issues.



## Phase 6: Web-First Experience (IN PROGRESS 🏗️)

- [ ] **PowerShell Installer (`install.ps1`)**: Complete automation from Windows.

- [ ] **FastAPI Backend**: Expose agent via REST/WebSockets.

- [ ] **ChatGPT-Style Web UI**: Build the primary interface.

- [ ] **Auto-Launch Logic**: Ensure browser opens automatically on successful install.
