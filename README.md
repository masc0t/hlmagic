# 🪄 HLMagic: Your Easy AI Homelab

**HLMagic** is a "zero-config" assistant that turns your Windows computer into a powerful home media and AI center. 

You don't need to know how to code, how Linux works, or how to manage servers. You just talk to the agent, and it builds everything for you using your computer's hidden "Linux Mode" (WSL2).

---

## 🏁 Before You Start
Ensure you have a modern Graphics Card (GPU) from **NVIDIA**, **AMD**, or **Intel**. For the best experience, make sure your Windows drivers are up to date!

---

## 🚀 Step-by-Step Setup

### Step 1: Turn on "Linux Mode" (WSL)
1. Click your **Start Menu** and type `PowerShell`.
2. Right-click **Windows PowerShell** and choose **Run as Administrator**.
3. Copy and paste this command, then press Enter:
   ```powershell
   wsl --install -d Ubuntu-24.04
   ```
4. It will ask you to create a **Username** and **Password**. 
   * *Note: When typing your password, you won't see any dots or stars. This is normal! Just type it and hit Enter.*

### Step 3: Prepare your Linux system
Copy and paste these two lines (one at a time) and press Enter. This installs the tools needed to run the agent.
```bash
sudo apt update
sudo apt install -y python3-pip git
```

### Step 4: Install HLMagic
Now, install the agent itself:
```bash
pip install git+https://github.com/masc0t/hlmagic.git --break-system-packages
```
*(Note: We use --break-system-packages because this is a dedicated "Magic" environment just for your homelab!)*

### Step 5: The "Magic" Initialization
Run this command to let the agent scan your computer and install your video card drivers automatically:
```bash
hlmagic init
```
* **If it tells you to restart:** Close the window, open PowerShell again, type `wsl --shutdown`, then reopen the Ubuntu app and run the command again.

---

## 🧠 Talking to Your Agent
Now for the fun part. You can tell HLMagic what you want in plain English.

**Example: Setup a Movie Server (Plex)**
```bash
hlmagic run "Setup Plex using my D: drive for movies"
```
The agent will:
1. Find your D: drive.
2. Configure your Graphics Card so movies play smoothly.
3. Start the server.

**Check what's running:**
```bash
hlmagic status
```

**Clean up everything (Reset):**
```bash
hlmagic purge
```

---

## ❓ Simple Troubleshooting

**"I get an error about WSL1"**
Open PowerShell as Administrator and run:
`wsl --set-version Ubuntu-24.04 2`

**"My GPU isn't showing up"**
Make sure you installed the latest drivers from the NVIDIA, AMD, or Intel website on your **Windows** desktop first.

**"What is my password?"**
This is the password you created in **Step 2**. The agent needs it to install software for you.

---

## 📜 License
MIT
