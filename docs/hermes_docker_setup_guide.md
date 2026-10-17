# Comprehensive Guide to Hermes Agent in Docker & Copilot Auto-Router

This production guide provides a step-by-step Standard Operating Procedure (SOP) to deploy **Hermes Agent** in an isolated Docker sandbox. The environment is configured with:
- An interactive **Web UI Dashboard** accessible on your host machine.
- Seamless **GitHub** integration for autonomous code review and PR workflows.
- A built-in **Hermes Copilot Auto-Router** that dynamically switches between local Ollama models (`qwen2.5:0.5b`, `qwen2.5-coder:14b`, `qwen2.5-coder:32b`, `deepseek-r1:14b`) based on task difficulty — functioning just like VS Code GitHub Copilot Auto-mode, 100% offline.

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
│  - Custom Skills (~/.hermes/skills)  │────▶│  - Local 4-Model Fleet:          │
│  - Copilot Router (hermes_copilot.py)│     │    • qwen2.5:0.5b (Router)       │
│  - Workspace Volume (/workspace)     │     │    • qwen2.5-coder:14b (Coding)  │
│  - Dev Tools: Git, GitHub CLI        │     │    • qwen2.5-coder:32b (Arch)    │
└──────────────────────────────────────┘     │    • deepseek-r1:14b (Security)  │
                                             └──────────────────────────────────┘
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

## Step 5: Configure Hermes for Local Ollama

Point Hermes to your local GPU-accelerated Ollama container instead of external cloud APIs:

1. Inside `hermes-sandbox-pro`, start the model setup wizard:
   ```bash
   hermes model
   ```
2. Select **Custom OpenAI-Compatible API** (or **Local Ollama**).
3. **Base URL:** Enter `http://172.17.0.1:11434/v1` (or `http://host.docker.internal:11434/v1`).
   > [!TIP]
   > `172.17.0.1` is the Docker bridge default gateway on Linux/Windows and avoids IPv6 DNS resolution issues.
4. **API Key:** Enter `ollama` (or any non-empty string).
5. **Default Model:** Enter `qwen2.5-coder:14b`.

---

## Step 6: Install Hermes Copilot Auto-Router

The **Copilot Auto-Router** (`hermes_copilot.py`) operates as a local dispatcher. It queries Ollama's active model catalog and uses a lightweight `qwen2.5:0.5b` model (~350 MB VRAM) to classify user tasks in **< 1 second** and automatically route to the optimal model:
- **`deepseek-r1:14b`** $\rightarrow$ Security vulnerabilities, authentication audits, race conditions, math proofs.
- **`qwen2.5-coder:32b`** $\rightarrow$ System architecture, enterprise design patterns, clean architecture domain modeling.
- **`qwen2.5-coder:14b`** $\rightarrow$ Daily software engineering, writing functions, unit tests, bug fixes, scripts.

### 1. Ensure `hermes_copilot.py` is in `/workspace/`
Make the script executable inside `hermes-sandbox-pro`:
```bash
chmod +x /workspace/hermes_copilot.py
```

### 2. Configure Copilot Shell Aliases
Add shortcuts to `~/.bashrc`:
```bash
cat << 'EOF' >> ~/.bashrc

# Hermes Copilot Auto-Router Shortcuts
alias hermes-copilot="python3 /workspace/hermes_copilot.py"
alias h="python3 /workspace/hermes_copilot.py"
EOF

source ~/.bashrc
```

### 3. Test the Router via CLI
```bash
h "Audit this token handshake for timing attacks and race conditions"
```
Hermes Copilot will classify the intent, display a clean routing banner, and launch Hermes with `deepseek-r1:14b`!

---

## Step 7: How to Add & Manage Custom Skills in Hermes

Hermes Agent has an extensible plugin/skill engine. Skills teach the agent how to run specialized workflows, query tools, or route tasks.

### 1. Anatomy of a Hermes Skill
A Hermes skill is a directory placed inside `/root/.hermes/skills/<skill-name>/` containing a `SKILL.md` file with standard YAML frontmatter:

```markdown
---
name: skill-name
description: Clear, 1-2 sentence description of when the agent should trigger this skill.
version: 1.0.0
author: Engineering Team
license: MIT
---

# Skill Title

## When to Trigger
- Scenarios where the agent should use this skill.

## Execution Steps
1. Commands or scripts the agent must run.
2. How to present the output to the user.
```

### 2. Installing the `copilot-router` Skill
To allow Hermes to recommend models dynamically inside the **Chat window** or **Web UI**:

1. Create the skill directory and copy the skill file:
   ```bash
   mkdir -p /root/.hermes/skills/copilot-router
   cp -rf /workspace/skills/copilot-router/* /root/.hermes/skills/copilot-router/
   ```

2. Verify that Hermes discovers the skill:
   ```bash
   hermes skills list
   ```
   **Output:**
   ```text
   Installed Skills
   ┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┓
   ┃ Name                    ┃ Category ┃ Source  ┃ Trust   ┃ Status  ┃
   ┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━┩
   │ copilot-router          │          │ local   │ local   │ enabled │
   └─────────────────────────┴──────────┴─────────┴─────────┴─────────┘
   ```

### 3. How the In-Chat Skill Works
When chatting with Hermes, simply ask:
> *"Which model should I use for: Analyzing authentication handshake for race conditions?"*

Hermes will:
1. Detect that the query matches the `copilot-router` skill trigger.
2. Execute `python3 /workspace/hermes_copilot.py --recommend "<task>"`.
3. Receive the structured JSON decision from `qwen2.5:0.5b` in < 1 second.
4. Reply directly in chat with the recommended model, category, rationale, and the `/model <name>` switch command!

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

### Mode 1: Terminal Auto-Dispatcher (`h "prompt"`)
Launch a fresh session with the optimal model automatically selected:
```bash
# Security task -> routes to deepseek-r1:14b
h "Audit this JWT validation logic for replay vulnerabilities"

# System design -> routes to qwen2.5-coder:32b
h "Design clean architecture domain boundaries for order fulfillment"

# Implementation -> routes to qwen2.5-coder:14b
h "Write unit tests for the password hashing utility with xUnit"
```

### Mode 2: In-Chat Skill Recommendation (Chat & Web UI)
While chatting in the terminal or Web UI, ask naturally:
> *"Which model should I switch to for designing the microservices event schema?"*

Hermes will reply with the recommendation (`qwen2.5-coder:32b`) and guide you to switch.

### Mode 3: In-Session Hot-Swap (`/model`)
To switch models mid-conversation without losing context or restarting:
```text
/model
```
Select the target model from the list. Ollama swaps the weights in memory smoothly.

---

## Step 11: Maintenance & Lifecycle

### 1. Resuming After Host Reboot
When restarting your Windows machine, do **not** recreate the container. Simply restart:
```powershell
docker start hermes-sandbox-pro
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
