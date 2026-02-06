import os
import uvicorn
from fastapi import FastAPI, Request, HTTPException, Form, Depends, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from hlmagic.utils.agent import HLMagicAgent
from hlmagic.utils.hardware import HardwareScanner
from hlmagic.utils.update import check_for_updates, apply_update, get_current_version, get_version_info, restart_server
from hlmagic.utils.config import get_password, set_password, get_debug_mode, set_debug_mode
import threading
import time

app = FastAPI(title="HLMagic Web Interface")

# Shared Agent Instance
agent = HLMagicAgent()

def debug_log(msg: str):
    """Log to console and file if debug mode is enabled."""
    if get_debug_mode():
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] DEBUG: {msg}"
        print(formatted)
        try:
            # Note: /opt/hlmagic/server.log is where we redirect stdout/stderr in install.ps1
            with open("/opt/hlmagic/server.log", "a") as f:
                f.write(formatted + "\n")
        except: pass

def auto_update_loop():
    """Background task to automatically check and apply updates."""
    # Wait for startup
    time.sleep(60)
    while True:
        try:
            debug_log("Auto-update check starting...")
            available, _ = check_for_updates()
            if available:
                debug_log("Automatic Update: New version found. Applying...")
                from hlmagic.utils.update import apply_update, restart_server
                success, _ = apply_update()
                if success:
                    debug_log("Update applied. Scheduling restart in 5s.")
                    threading.Timer(5.0, restart_server).start()
            else:
                debug_log("Auto-update check: No updates found.")
        except Exception as e:
            debug_log(f"Auto-update error: {e}")
        # Check every hour
        time.sleep(3600)

# Start background auto-updater
threading.Thread(target=auto_update_loop, daemon=True).start()

class ChatRequest(BaseModel):
    message: str

def is_authenticated(hl_token: str = Cookie(None)):
    pwd = get_password()
    if not pwd:
        return False
    if hl_token == pwd:
        return True
    return False

@app.get("/setup-password", response_class=HTMLResponse)
async def setup_password_page(error: str = None):
    if get_password():
        return RedirectResponse(url="/login")
    
    info = get_version_info()
    version_str = f"v{info['version']} ({info['date'][:10]})"
    
    error_html = f'<p class="text-red-500 text-xs mt-2">{error}</p>' if error else ''
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Setup - HLMagic</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-900 text-gray-100 flex items-center justify-center h-screen">
        <div class="bg-gray-800 p-8 rounded-2xl shadow-2xl w-96 border border-gray-700">
            <div class="text-center mb-8">
                <span class="text-4xl">🪄</span>
                <h1 class="text-2xl font-bold mt-2">Set Your Passphrase</h1>
                <p class="text-gray-400 text-sm mt-1">This will be used to secure your HLMagic Brain.</p>
                <p class="text-gray-500 text-[10px] mt-2">{version_str}</p>
            </div>
            <form action="/setup-password" method="post" class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-400 mb-1">New Passphrase</label>
                    <input type="password" name="password" required 
                        class="w-full bg-gray-900 border border-gray-700 rounded-xl py-3 px-4 focus:outline-none focus:ring-2 focus:ring-blue-500 text-white">
                </div>
                {error_html}
                <button type="submit" class="w-full bg-green-600 hover:bg-green-500 py-3 rounded-xl font-bold transition-colors">
                    Save and Continue
                </button>
            </form>
        </div>
    </body>
    </html>
    """

@app.post("/setup-password")
async def setup_password(password: str = Form(...)):
    if get_password():
        return RedirectResponse(url="/login")
    if len(password) < 4:
        return RedirectResponse(url="/setup-password?error=Minimum+4+characters")
    set_password(password)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="hl_token", value=password, httponly=True)
    return response

@app.get("/login", response_class=HTMLResponse)
async def login_page(error: str = None):
    if not get_password():
        return RedirectResponse(url="/setup-password")
    
    info = get_version_info()
    version_str = f"v{info['version']} ({info['date'][:10]})"
    
    error_html = f'<p class="text-red-500 text-xs mt-2">{error}</p>' if error else ''
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login - HLMagic</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-900 text-gray-100 flex items-center justify-center h-screen">
        <div class="bg-gray-800 p-8 rounded-2xl shadow-2xl w-96 border border-gray-700">
            <div class="text-center mb-8">
                <span class="text-4xl">🪄</span>
                <h1 class="text-2xl font-bold mt-2">HLMagic Access</h1>
                <p class="text-gray-500 text-[10px] mt-1">{version_str}</p>
            </div>
            <form action="/login" method="post" class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-400 mb-1">Passphrase</label>
                    <input type="password" name="password" required 
                        class="w-full bg-gray-900 border border-gray-700 rounded-xl py-3 px-4 focus:outline-none focus:ring-2 focus:ring-blue-500 text-white">
                </div>
                {error_html}
                <button type="submit" class="w-full bg-blue-600 hover:bg-blue-500 py-3 rounded-xl font-bold transition-colors">
                    Unlock Brain
                </button>
            </form>
        </div>
    </body>
    </html>
    """

@app.post("/login")
async def login(password: str = Form(...)):
    if password == get_password():
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key="hl_token", value=password, httponly=True)
        return response
    return RedirectResponse(url="/login?error=Invalid+passphrase", status_code=303)

@app.get("/update-status")
async def update_status(authenticated: bool = Depends(is_authenticated)):
    if not authenticated: raise HTTPException(status_code=401)
    available, message = check_for_updates()
    info = get_version_info()
    return {"available": available, "message": message, "version": info["version"], "date": info["date"]}

@app.post("/update")
async def run_update(authenticated: bool = Depends(is_authenticated)):
    if not authenticated: raise HTTPException(status_code=401)
    from hlmagic.utils.update import apply_update, restart_server
    success, message = apply_update()
    if success:
        # Restart in 5 seconds to allow UI to show message
        threading.Timer(5.0, restart_server).start()
    return {"success": success, "message": message}

@app.post("/restart")
async def run_restart(authenticated: bool = Depends(is_authenticated)):
    if not authenticated: raise HTTPException(status_code=401)
    from hlmagic.utils.update import restart_server
    # Restart in a separate thread to allow response to be sent
    threading.Timer(1.0, restart_server).start()
    return {"message": "Server restarting..."}

@app.get("/system-status")
async def system_status(authenticated: bool = Depends(is_authenticated)):
    if not authenticated: raise HTTPException(status_code=401)
    
    from hlmagic.utils.tools import scan_wsl_storage
    from hlmagic.utils.hardware import HardwareScanner
    import subprocess
    from pathlib import Path

    # 1. Core Services
    core = {}
    for svc in ["docker", "ollama", "avahi-daemon"]:
        res = subprocess.run(["systemctl", "is-active", svc], capture_output=True, text=True)
        core[svc] = res.stdout.strip()

    # 2. Deployed Services
    services = []
    base_path = Path("/opt/hlmagic/services")
    if base_path.exists():
        for service_dir in base_path.iterdir():
            if service_dir.is_dir() and (service_dir / "docker-compose.yml").exists():
                name = service_dir.name
                status = "Stopped"
                try:
                    res = subprocess.run(
                        ["sudo", "docker", "compose", "ps", "--format", "json"],
                        cwd=service_dir, capture_output=True, text=True
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        status = "Running"
                except: status = "Error"
                services.append({"name": name, "status": status})

    # 3. Hardware
    scanner = HardwareScanner()
    scanner.scan()
    
    return {
        "core": core,
        "services": services,
        "hardware": {
            "gpu": scanner.primary_gpu.value,
            "vram_split": scanner.vram_split,
            "storage": scan_wsl_storage()
        }
    }

@app.get("/settings")
async def get_settings(authenticated: bool = Depends(is_authenticated)):
    if not authenticated: raise HTTPException(status_code=401)
    return {
        "debug": get_debug_mode(),
        "version": get_current_version()
    }

@app.post("/settings/debug/{enabled}")
async def toggle_debug(enabled: bool, authenticated: bool = Depends(is_authenticated)):
    if not authenticated: raise HTTPException(status_code=401)
    set_debug_mode(enabled)
    debug_log(f"Debug mode set to: {enabled}")
    return {"success": True, "debug": enabled}

@app.get("/logs")
async def get_logs(authenticated: bool = Depends(is_authenticated)):
    if not authenticated: raise HTTPException(status_code=401)
    try:
        if os.path.exists("/opt/hlmagic/server.log"):
            with open("/opt/hlmagic/server.log", "r") as f:
                # Return last 200 lines
                lines = f.readlines()
                return {"logs": "".join(lines[-200:])}
        return {"logs": "Log file not found."}
    except Exception as e:
        return {"logs": f"Error reading logs: {e}"}

@app.post("/service/{name}/{action}")
async def manage_service(name: str, action: str, authenticated: bool = Depends(is_authenticated)):
    if not authenticated: raise HTTPException(status_code=401)
    import subprocess
    from pathlib import Path
    
    service_dir = Path(f"/opt/hlmagic/services/{name}")
    if not service_dir.exists():
        raise HTTPException(status_code=404, detail="Service not found")
    
    cmd = ["sudo", "docker", "compose", "up", "-d"] if action == "start" else ["sudo", "docker", "compose", "down"]
    res = subprocess.run(cmd, cwd=service_dir, capture_output=True, text=True)
    
    return {"success": res.returncode == 0, "output": res.stdout or res.stderr}

@app.get("/", response_class=HTMLResponse)
async def index(hl_token: str = Cookie(None)):
    if not get_password():
        return RedirectResponse(url="/setup-password")
    if hl_token != get_password():
        return RedirectResponse(url="/login")
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>HLMagic Agent</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            .chat-container { height: calc(100vh - 160px); }
            ::-webkit-scrollbar { width: 6px; }
            ::-webkit-scrollbar-thumb { background: #4a5568; border-radius: 10px; }
        </style>
    </head>
    <body class="bg-gray-900 text-gray-100 font-sans">
        <div class="max-w-6xl mx-auto p-4 flex flex-col h-screen">
            <header class="flex items-center justify-between py-4 border-b border-gray-800">
                <div class="flex items-center space-x-6">
                    <div class="flex items-center space-x-2">
                        <span class="text-2xl">🪄</span>
                        <div>
                            <h1 class="text-xl font-bold tracking-tight leading-tight">HLMagic</h1>
                            <p class="text-[10px] text-gray-500 font-mono"><span id="version-tag">v...</span> <span id="version-date"></span></p>
                        </div>
                    </div>
                    <nav class="flex space-x-1 bg-gray-800 p-1 rounded-xl">
                        <button onclick="showTab('chat')" id="tab-chat" class="px-4 py-1.5 rounded-lg text-sm font-medium transition-colors bg-blue-600 text-white">Chat</button>
                        <button onclick="showTab('dashboard')" id="tab-dashboard" class="px-4 py-1.5 rounded-lg text-sm font-medium transition-colors text-gray-400 hover:text-white">Dashboard</button>
                        <button onclick="showTab('settings')" id="tab-settings" class="px-4 py-1.5 rounded-lg text-sm font-medium transition-colors text-gray-400 hover:text-white">Settings</button>
                    </nav>
                </div>
                <div class="flex items-center space-x-3">
                    <button id="update-btn" onclick="triggerUpdate()" class="hidden px-3 py-1 rounded-md text-xs bg-blue-600 hover:bg-blue-500 text-white transition-colors">
                        Update Available
                    </button>
                    <button id="restart-btn" onclick="triggerRestart()" class="px-3 py-1 rounded-md text-xs bg-gray-700 hover:bg-gray-600 text-white transition-colors">
                        Restart
                    </button>
                    <div id="status-badge" class="px-3 py-1 rounded-full text-xs bg-green-900 text-green-300 border border-green-700">
                        System Ready
                    </div>
                </div>
            </header>

            <main id="chat-view" class="chat-container overflow-y-auto py-6 space-y-4 flex-1">
                <!-- Initial Message -->
                <div class="flex items-start space-x-3">
                    <div class="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0">🪄</div>
                    <div class="bg-gray-800 p-4 rounded-2xl rounded-tl-none max-w-[80%] shadow-lg">
                        <p class="text-sm">Welcome! I'm your HLMagic agent. I've finished scanning your hardware. What would you like to build today?</p>
                        <div class="mt-3 flex flex-wrap gap-2">
                            <button onclick="suggest('Setup Plex')" class="text-xs bg-gray-700 hover:bg-gray-600 px-2 py-1 rounded">Setup Plex</button>
                            <button onclick="suggest('Install Sonarr')" class="text-xs bg-gray-700 hover:bg-gray-600 px-2 py-1 rounded">Install Sonarr</button>
                            <button onclick="suggest('Check my GPU')" class="text-xs bg-gray-700 hover:bg-gray-600 px-2 py-1 rounded">Check my GPU</button>
                        </div>
                    </div>
                </div>
            </main>

            <main id="dashboard-view" class="hidden flex-1 overflow-y-auto py-6 space-y-8">
                <section>
                    <h2 class="text-lg font-bold mb-4 flex items-center"><span class="mr-2">📦</span> Deployed Services</h2>
                    <div id="services-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        <!-- Service cards injected here -->
                    </div>
                </section>

                <section class="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div>
                        <h2 class="text-lg font-bold mb-4 flex items-center"><span class="mr-2">⚡</span> System Health</h2>
                        <div id="core-status" class="bg-gray-800 rounded-2xl p-6 border border-gray-700 space-y-4">
                            <!-- Core status injected here -->
                        </div>
                    </div>
                    <div>
                        <h2 class="text-lg font-bold mb-4 flex items-center"><span class="mr-2">📟</span> Hardware Context</h2>
                        <div id="hw-status" class="bg-gray-800 rounded-2xl p-6 border border-gray-700 space-y-4">
                            <!-- HW info injected here -->
                        </div>
                    </div>
                </section>
            </main>

            <main id="settings-view" class="hidden flex-1 overflow-y-auto py-6 space-y-8">
                <section class="max-w-2xl">
                    <h2 class="text-lg font-bold mb-4 flex items-center"><span class="mr-2">⚙️</span> System Settings</h2>
                    <div class="bg-gray-800 rounded-2xl p-6 border border-gray-700 space-y-6">
                        <div class="flex items-center justify-between">
                            <div>
                                <h3 class="font-bold">Full Debug Mode</h3>
                                <p class="text-xs text-gray-400">Enable verbose logging to help diagnose update and restart issues.</p>
                            </div>
                            <button id="debug-toggle" onclick="toggleDebug()" class="px-4 py-2 rounded-xl text-xs font-bold transition-colors bg-gray-700 text-white">
                                Disabled
                            </button>
                        </div>
                    </div>
                </section>

                <section>
                    <h2 class="text-lg font-bold mb-4 flex items-center"><span class="mr-2">📜</span> System Logs</h2>
                    <div class="bg-gray-900 rounded-2xl border border-gray-800 overflow-hidden">
                        <div class="bg-gray-800 px-4 py-2 border-b border-gray-700 flex justify-between items-center">
                            <span class="text-xs font-mono text-gray-400">/opt/hlmagic/server.log</span>
                            <button onclick="refreshLogs()" class="text-[10px] bg-gray-700 hover:bg-gray-600 px-2 py-1 rounded">Refresh</button>
                        </div>
                        <pre id="log-viewer" class="p-4 text-[10px] font-mono text-gray-300 overflow-x-auto h-96 overflow-y-auto whitespace-pre-wrap">Loading logs...</pre>
                    </div>
                </section>
            </main>

            <footer id="chat-footer" class="py-4">
                <form id="chat-form" class="relative">
                    <input type="text" id="user-input" 
                        class="w-full bg-gray-800 border border-gray-700 rounded-2xl py-4 pl-6 pr-16 focus:outline-none focus:ring-2 focus:ring-blue-500 text-white placeholder-gray-500"
                        placeholder="Type your command (e.g. 'Deploy Jellyfin using my D: drive')...">
                    <button type="submit" 
                        class="absolute right-2 top-2 bottom-2 px-4 bg-blue-600 hover:bg-blue-500 text-white rounded-xl transition-colors">
                        Send
                    </button>
                </form>
                <p class="text-[10px] text-center text-gray-600 mt-2 italic">HLMagic executes commands directly in your WSL2 environment.</p>
            </footer>
        </div>

        <script>
            const chatView = document.getElementById('chat-view');
            const dashboardView = document.getElementById('dashboard-view');
            const settingsView = document.getElementById('settings-view');
            const chatFooter = document.getElementById('chat-footer');
            const tabChat = document.getElementById('tab-chat');
            const tabDashboard = document.getElementById('tab-dashboard');
            const tabSettings = document.getElementById('tab-settings');

            const chatForm = document.getElementById('chat-form');
            const userInput = document.getElementById('user-input');
            const updateBtn = document.getElementById('update-btn');
            const versionTag = document.getElementById('version-tag');
            const versionDate = document.getElementById('version-date');

            function showTab(tab) {
                [chatView, dashboardView, settingsView, chatFooter].forEach(v => v.classList.add('hidden'));
                [tabChat, tabDashboard, tabSettings].forEach(t => {
                    t.classList.remove('bg-blue-600', 'text-white');
                    t.classList.add('text-gray-400');
                });

                if (tab === 'chat') {
                    chatView.classList.remove('hidden');
                    chatFooter.classList.remove('hidden');
                    tabChat.classList.add('bg-blue-600', 'text-white');
                    tabChat.classList.remove('text-gray-400');
                } else if (tab === 'dashboard') {
                    dashboardView.classList.remove('hidden');
                    tabDashboard.classList.add('bg-blue-600', 'text-white');
                    tabDashboard.classList.remove('text-gray-400');
                    refreshDashboard();
                } else if (tab === 'settings') {
                    settingsView.classList.remove('hidden');
                    tabSettings.classList.add('bg-blue-600', 'text-white');
                    tabSettings.classList.remove('text-gray-400');
                    refreshSettings();
                    refreshLogs();
                }
            }

            async function refreshSettings() {
                try {
                    const res = await fetch('/settings');
                    const data = await res.json();
                    const btn = document.getElementById('debug-toggle');
                    if (data.debug) {
                        btn.innerText = "Enabled";
                        btn.classList.replace('bg-gray-700', 'bg-blue-600');
                    } else {
                        btn.innerText = "Disabled";
                        btn.classList.replace('bg-blue-600', 'bg-gray-700');
                    }
                } catch (e) {}
            }

            async function toggleDebug() {
                const btn = document.getElementById('debug-toggle');
                const currentlyEnabled = btn.innerText === "Enabled";
                try {
                    await fetch(`/settings/debug/${!currentlyEnabled}`, { method: 'POST' });
                    refreshSettings();
                } catch (e) {}
            }

            async function refreshLogs() {
                const viewer = document.getElementById('log-viewer');
                try {
                    const res = await fetch('/logs');
                    const data = await res.json();
                    viewer.innerText = data.logs;
                    viewer.scrollTop = viewer.scrollHeight;
                } catch (e) {
                    viewer.innerText = "Error loading logs.";
                }
            }

            async function refreshDashboard() {
                try {
                    const res = await fetch('/system-status');
                    const data = await res.json();
                    
                    // 1. Services Grid
                    const grid = document.getElementById('services-grid');
                    grid.innerHTML = data.services.length ? '' : '<p class="text-gray-500 text-sm italic">No services deployed yet. Ask the agent to setup something!</p>';
                    data.services.forEach(svc => {
                        const card = document.createElement('div');
                        card.className = "bg-gray-800 border border-gray-700 rounded-2xl p-5 flex flex-col justify-between";
                        card.innerHTML = `
                            <div class="flex justify-between items-start mb-4">
                                <div>
                                    <h3 class="font-bold text-lg capitalize">${svc.name}</h3>
                                    <span class="text-xs px-2 py-0.5 rounded-full ${svc.status === 'Running' ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}">
                                        ${svc.status}
                                    </span>
                                </div>
                                <span class="text-2xl">${svc.name === 'jellyfin' ? '🎬' : svc.name === 'plex' ? '📽️' : '📦'}</span>
                            </div>
                            <div class="flex space-x-2">
                                <button onclick="svcAction('${svc.name}', 'start')" class="flex-1 bg-gray-700 hover:bg-gray-600 py-2 rounded-xl text-xs font-bold transition-colors">Start</button>
                                <button onclick="svcAction('${svc.name}', 'stop')" class="flex-1 bg-gray-900 hover:bg-red-900 py-2 rounded-xl text-xs font-bold transition-colors border border-gray-700">Stop</button>
                            </div>
                        `;
                        grid.appendChild(card);
                    });

                    // 2. Core Health
                    const core = document.getElementById('core-status');
                    core.innerHTML = '';
                    Object.entries(data.core).forEach(([name, status]) => {
                        const row = document.createElement('div');
                        row.className = "flex justify-between items-center";
                        row.innerHTML = `
                            <span class="text-sm text-gray-400 font-mono">${name}</span>
                            <span class="text-xs font-bold ${status === 'active' ? 'text-green-400' : 'text-red-400'}">${status.toUpperCase()}</span>
                        `;
                        core.appendChild(row);
                    });

                    // 3. Hardware Info
                    const hw = document.getElementById('hw-status');
                    hw.innerHTML = `
                        <div class="flex justify-between">
                            <span class="text-sm text-gray-400">Primary GPU</span>
                            <span class="text-sm font-bold text-blue-400">${data.hardware.gpu.toUpperCase()}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-sm text-gray-400">VRAM/RAM Split</span>
                            <span class="text-sm font-mono">${data.hardware.vram_split.HLMAGIC_BRAIN_RAM_GB}GB / ${data.hardware.vram_split.HLMAGIC_RESERVED_RAM_GB}GB</span>
                        </div>
                        <div class="pt-2 border-t border-gray-700">
                            <span class="text-xs text-gray-500 uppercase font-bold">Mount Points</span>
                            <div class="mt-2 space-y-1">
                                ${data.hardware.storage.map(s => `<div class="text-[10px] text-gray-400 font-mono">${s.path} (${s.device})</div>`).join('')}
                            </div>
                        </div>
                    `;

                } catch (e) {
                    console.error("Dashboard refresh failed", e);
                }
            }

            async function svcAction(name, action) {
                if (!confirm(`Are you sure you want to ${action} ${name}?`)) return;
                try {
                    await fetch(`/service/${name}/${action}`, { method: 'POST' });
                    refreshDashboard();
                } catch (e) { alert("Action failed"); }
            }

            async function checkUpdates() {
                try {
                    const res = await fetch('/update-status');
                    const data = await res.json();
                    versionTag.innerText = `v${data.version}`;
                    if (data.date) {
                        versionDate.innerText = `(${data.date.substring(0, 10)})`;
                    }
                    if (data.available) {
                        updateBtn.classList.remove('hidden');
                    }
                } catch (e) {}
            }

            async function triggerRestart() {
                if (!confirm("Are you sure you want to restart the HLMagic server?")) return;
                const btn = document.getElementById('restart-btn');
                btn.innerText = "Restarting...";
                btn.disabled = true;
                try {
                    await fetch('/restart', { method: 'POST' });
                    setTimeout(() => {
                        location.reload();
                    }, 3000);
                } catch (e) {
                    alert("Restart triggered.");
                    setTimeout(() => {
                        location.reload();
                    }, 3000);
                }
            }

            async function triggerUpdate() {
                if (!confirm("Are you sure you want to update HLMagic? This will pull latest code and restart dependencies.")) return;
                updateBtn.innerText = "Updating...";
                updateBtn.disabled = true;
                try {
                    const res = await fetch('/update', { method: 'POST' });
                    const data = await res.json();
                    if (data.success) {
                        alert(data.message + " The server will restart automatically in 5 seconds.");
                        setTimeout(() => {
                            location.reload();
                        }, 6000);
                    } else {
                        alert(data.message);
                        updateBtn.innerText = "Update Available";
                        updateBtn.disabled = false;
                    }
                } catch (e) {
                    alert("Update triggered. Server may be restarting.");
                    setTimeout(() => {
                        location.reload();
                    }, 6000);
                }
            }

            // Initial Check
            checkUpdates();

            function addMessage(role, text) {
                const div = document.createElement('div');
                div.className = `flex items-start space-x-3 ${role === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`;
                
                const avatar = document.createElement('div');
                avatar.className = `w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${role === 'user' ? 'bg-gray-600' : 'bg-blue-600'}`;
                avatar.innerText = role === 'user' ? '👤' : '🪄';

                const content = document.createElement('div');
                content.className = `${role === 'user' ? 'bg-blue-700' : 'bg-gray-800'} p-4 rounded-2xl shadow-lg max-w-[80%] ${role === 'user' ? 'rounded-tr-none' : 'rounded-tl-none'}`;
                
                const p = document.createElement('p');
                p.className = "text-sm whitespace-pre-wrap";
                p.innerText = text;

                content.appendChild(p);
                div.appendChild(avatar);
                div.appendChild(content);
                chatView.appendChild(div);
                chatView.scrollTop = chatView.scrollHeight;
                return p;
            }

            function suggest(text) {
                userInput.value = text;
                chatForm.dispatchEvent(new Event('submit'));
            }

            chatForm.onsubmit = async (e) => {
                e.preventDefault();
                const msg = userInput.value.trim();
                if (!msg) return;

                userInput.value = '';
                addMessage('user', msg);

                // Add loading indicator
                const loadingMsg = addMessage('agent', 'Thinking...');
                
                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: msg })
                    });
                    const data = await response.json();
                    loadingMsg.innerText = data.response;
                } catch (err) {
                    loadingMsg.innerText = "Error: Could not reach the HLMagic agent.";
                    loadingMsg.parentElement.classList.add('bg-red-900');
                }
            };
        </script>
    </body>
    </html>
    """

@app.post("/chat")
async def chat(request: ChatRequest, authenticated: bool = Depends(is_authenticated)):
    if not authenticated: raise HTTPException(status_code=401)
    try:
        debug_log(f"Chat request received: {request.message}")
        # Run the agent and get the final response string
        response_text = agent.run(request.message)
        debug_log(f"Agent response: {response_text[:100]}...")
        return {"response": response_text}
    except Exception as e:
        debug_log(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
