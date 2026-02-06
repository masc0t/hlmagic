import os
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from hlmagic.utils.agent import HLMagicAgent
from hlmagic.utils.hardware import HardwareScanner
import threading

app = FastAPI(title="HLMagic Web Interface")

# Shared Agent Instance
agent = HLMagicAgent()

class ChatRequest(BaseModel):
    message: str

@app.get("/", response_class=HTMLResponse)
async def index():
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
                    <h1 class="text-xl font-bold tracking-tight">HLMagic <span class="text-blue-500 text-sm font-normal">v1.0.0</span></h1>
                </div>
                <div id="status-badge" class="px-3 py-1 rounded-full text-xs bg-green-900 text-green-300 border border-green-700">
                    System Ready
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
async def chat(request: ChatRequest):
    try:
        # Run the agent and get the final response string
        response_text = agent.run(request.message)
        return {"response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
