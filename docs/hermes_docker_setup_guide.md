# Comprehensive Guide to Hermes Agent in Docker & Copilot Auto-Proxy

This production guide provides a step-by-step Standard Operating Procedure (SOP) to deploy **Hermes Agent** in an isolated Docker sandbox. The environment is configured with:
- An interactive **Web UI Dashboard** accessible on your host machine.
- Seamless **GitHub** integration for autonomous code review and PR workflows.
- A built-in **Hermes Copilot Auto-Proxy** that dynamically routes between local Ollama models (`qwen2.5:0.5b`, `qwen2.5-coder:14b`, `deepseek-r1:14b`) based on task intent and difficulty — functioning just like VS Code GitHub Copilot Auto-mode, 100% offline and native to the Hermes Chat UI and TUI.

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                        WINDOWS HOST MACHINE                            │
│  - Browser Web UI: http://localhost:9119                               │
│  - Persistent Codebase: D:\Data\Docker Data\Hermes                     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
       ┌────────────────────────────┴───────────────────────────┐
       ▼                                                        ▼
┌──────────────────────────────────────┐     ┌──────────────────────────────────┐
│  CONTAINER: hermes-sandbox-pro       │     │  CONTAINER: ollama-sandbox-pro   │
│  - Hermes Agent Runtime & Web UI     │     │  - Port 11434 (GPU Accelerated)  │
│    (Model set to "auto")             │     │  - Local Models:                 │
│  - Auto-Proxy (hermes_proxy.py:8000) │────▶│    • qwen2.5:0.5b (Router)       │
│  - Workspace Volume (/workspace)     │     │    • qwen2.5-coder:14b (Coding)  │
│  - Dev Tools: Git, GitHub CLI        │     │    • deepseek-r1:14b (Security)  │
└──────────────────────────────────────┘     └──────────────────────────────────┘
```

---

## Step 1: Provision the Hermes Container (Docker Run)

Create the host storage folder and launch the Ubuntu container with port forwarding for the Web UI and volume mapping for your workspace:

1. Open **PowerShell** on your host machine and ensure the workspace directory exists:
   ```powershell
   New-Item -ItemType Directory -Force -Path "D:\Data\Docker Data\Hermes"
   ```

2. Run the Docker container:
   ```powershell
   docker run -it `
     --name hermes-sandbox-pro `
     -p 9119:9119 `
     -v "D:\Data\Docker Data\Hermes:/workspace" `
     ubuntu:latest bash
   ```

---

## Step 2: Consolidated System Update & Prerequisites

Inside the container shell (`root@...:/#`), install all required system libraries, Python tooling, and Node.js runtime in a single consolidated command:

```bash
apt update && apt install -y \
  curl git sudo nano nodejs npm \
  python3 python3-pip python3-venv \
  apt-transport-https ca-certificates gnupg lsb-release
```

---

## Step 3: Install GitHub CLI (`gh`)

Install the official GitHub CLI for automated repository operations, PR reviews, and issue triage:

```bash
# Add official GitHub CLI repository and install
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null
apt update && apt install -y gh
```

---

## Step 4: Install Hermes Agent & Web Browsing Tools

### 1. Install Hermes Agent
Download and execute the official installer:
```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc
```

### 2. Install Headless Web Browsing (Playwright)
To allow Hermes to perform internet research, browse web documentation, and run autonomous tasks, install Playwright in the Hermes virtual environment:

From your host **PowerShell**:
```powershell
docker exec hermes-sandbox-pro /usr/local/lib/hermes-agent/venv/bin/pip install playwright
docker exec hermes-sandbox-pro /usr/local/lib/hermes-agent/venv/bin/python3 -m playwright install --with-deps chromium
```

---

## Step 5: Pull Required Models in Ollama

Ensure the GPU-accelerated Ollama container has the required local models pulled. Run from Windows PowerShell:

```powershell
# 1. Pocket classifier router (< 50ms classification, ~350MB VRAM)
docker exec -it ollama-sandbox-pro ollama pull qwen2.5:0.5b

# 2. Daily software engineering, coding & unit tests (~9GB)
docker exec -it ollama-sandbox-pro ollama pull qwen2.5-coder:14b

# 3. Deep reasoning, security audits, cryptography & logic proofs (~9GB)
docker exec -it ollama-sandbox-pro ollama pull deepseek-r1:14b
```

---

## Step 6: Deploy Hermes Copilot Auto-Proxy (`hermes_proxy.py`)

The **Hermes Copilot Auto-Proxy** acts as an intelligent OpenAI-compatible reverse proxy running locally inside `hermes-sandbox-pro` on port `8000`.

### 1. Ensure `hermes_proxy.py` is in `/workspace/`
The repository file `hermes_proxy.py` maps automatically to `/workspace/hermes_proxy.py` inside the container via your Docker volume (`D:\Data\Docker Data\Hermes`).

### 2. Launch the Auto-Proxy in the Background
Start the proxy as a persistent background daemon:
```bash
nohup /usr/local/lib/hermes-agent/venv/bin/python3 /workspace/hermes_proxy.py > /workspace/proxy.log 2>&1 &
```

> [!TIP]
> The proxy logs every routing decision, model assignment, and latency benchmark to `/workspace/proxy.log` (accessible on host at `D:\Data\Docker Data\Hermes\proxy.log`).

### 3. Verify Proxy Health
Test the proxy's model catalog:
```bash
curl http://127.0.0.1:8000/v1/models
```
The output will list `"id": "auto"` at the top, along with all local Ollama models.

---

## Step 7: Configure Hermes Agent for Auto-Mode

Configure Hermes to communicate with the Auto-Proxy so all chats default to `auto`:

1. Set the OpenAI-compatible Base URL and default model:
   ```bash
   hermes config set model.base_url http://127.0.0.1:8000/v1
   hermes config set model.default auto
   ```

2. Verify the configuration:
   ```bash
   hermes config get model
   ```
   **Output:**
   ```yaml
   default: auto
   provider: custom
   base_url: http://127.0.0.1:8000/v1
   api_key: '***'
   ```

Now, any session started via CLI, TUI, or Web UI will natively submit prompts with `model: "auto"`. The proxy classifies intent in 50ms and routes to the ideal model without manual switching!

---

## Step 8: Launching the Web UI Dashboard

Start the graphical dashboard to interact with Hermes visually:

1. Inside `hermes-sandbox-pro`, start the server:
   ```bash
   hermes dashboard --host 0.0.0.0
   ```
   > [!IMPORTANT]
   > **Why `--host 0.0.0.0` is required:** By default, Hermes binds locally to `127.0.0.1` inside the container. You must supply `--host 0.0.0.0` to bind to all network interfaces, allowing the port mapping (`-p 9119:9119`) to forward connections from your Windows host browser.

2. On first launch, type `1` to configure username/password authentication (e.g. `admin` and a secure password).
3. Open your browser on Windows and navigate to:
   **`http://localhost:9119`**
   *(Do NOT navigate to `0.0.0.0:9119` as Windows browsers cannot route to the all-interfaces wildcard address).*

---

## Step 9: GitHub Authentication & Agent Skills

Authenticate your GitHub account and equip Hermes with official GitHub skills:

1. Authenticate with GitHub CLI:
   ```bash
   gh auth login
   ```
   *Select: `GitHub.com` -> `HTTPS` -> `Login with a web browser`, and complete the token authorization.*

2. Install the official GitHub agent skill:
   ```bash
   hermes skills install github
   ```

---

## Step 10: Day-to-Day Workflow & Usage Guide

### Mode 1: Native In-Chat "Auto" Experience (Web UI & TUI)
Simply chat naturally in the Hermes Web UI (`http://localhost:9119`) or CLI chat (`hermes chat`). You do not need to specify model names or run helper scripts:
```text
Write a C# FluentValidation validator for a UserRegistrationDTO and create unit tests
```
The Auto-Proxy detects software engineering intent, streams the prompt to `qwen2.5-coder:14b`, and executes unit tests.

### Mode 2: Deep Security & Reasoning Auto-Routing
Submit a complex cryptographic or security analysis prompt:
```text
Analyze this authentication handshake for timing attack vulnerabilities and race conditions
```
The Auto-Proxy detects security and reasoning keywords in < 50ms, dynamically routes to `deepseek-r1:14b`, and streams deep chain-of-thought analysis.

### Mode 3: Multi-Turn Tool Pinning
When Hermes invokes agent tools (e.g., executing code, editing files, or running git commands), the Auto-Proxy pins the active model for all subsequent tool calls in that turn. This guarantees zero weight thrashing or VRAM swapping during multi-step tool execution.

### Mode 4: Manual Hot-Swap (`/model`)
If you ever want to force a specific model instead of `auto`:
```text
/model
```
Select any specific model from the list. Ollama swaps the weights smoothly.

---

## Step 11: Maintenance & Lifecycle

### 1. Resuming After Host Reboot
When restarting your Windows machine, do **not** recreate the container. Simply restart:
```powershell
docker start hermes-sandbox-pro
```
Ensure the Auto-Proxy background daemon is running inside `hermes-sandbox-pro`:
```powershell
docker exec -d hermes-sandbox-pro nohup /usr/local/lib/hermes-agent/venv/bin/python3 /workspace/hermes_proxy.py > /workspace/proxy.log 2>&1
```

To reopen the bash shell:
```powershell
docker exec -it hermes-sandbox-pro bash
```

### 2. Updating Hermes Agent
Check version and update to latest releases:
```bash
hermes --version
hermes update
```
