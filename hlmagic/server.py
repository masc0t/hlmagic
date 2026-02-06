import os
import uvicorn
from fastapi import FastAPI, Request, HTTPException, Form, Depends, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from hlmagic.utils.agent import HLMagicAgent
from hlmagic.utils.hardware import HardwareScanner
from hlmagic.utils.update import check_for_updates, apply_update, get_current_version
from hlmagic.utils.config import get_password, set_password
import threading
import time

app = FastAPI(title="HLMagic Web Interface")

# Shared Agent Instance
agent = HLMagicAgent()

def auto_update_loop():
    """Background task to automatically check and apply updates."""
    # Wait for startup
    time.sleep(60)
    while True:
        try:
            available, _ = check_for_updates()
            if available:
                print("Automatic Update: New version found. Applying...")
                from hlmagic.utils.update import apply_update, restart_server
                success, _ = apply_update()
                if success:
                    threading.Timer(5.0, restart_server).start()
        except Exception as e:
            print(f"Auto-update error: {e}")
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
    return {"available": available, "message": message, "version": get_current_version()}

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
        <div class="max-w-4xl mx-auto p-4 flex flex-col h-screen">
            <header class="flex items-center justify-between py-4 border-b border-gray-800">
                <div class="flex items-center space-x-2">
                    <span class="text-2xl">🪄</span>
                    <h1 class="text-xl font-bold tracking-tight">HLMagic <span id="version-tag" class="text-blue-500 text-sm font-normal">v...</span></h1>
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

            <main id="chat-window" class="chat-container overflow-y-auto py-6 space-y-4 flex-1">
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

            <footer class="py-4">
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
            const chatWindow = document.getElementById('chat-window');
            const chatForm = document.getElementById('chat-form');
            const userInput = document.getElementById('user-input');
            const updateBtn = document.getElementById('update-btn');
            const versionTag = document.getElementById('version-tag');

            async function checkUpdates() {
                try {
                    const res = await fetch('/update-status');
                    const data = await res.json();
                    versionTag.innerText = `v${data.version}`;
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
                chatWindow.appendChild(div);
                chatWindow.scrollTop = chatWindow.scrollHeight;
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
        # Run the agent and get the final response string
        response_text = agent.run(request.message)
        return {"response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
