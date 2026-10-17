# 🤖 Hermes Copilot: Auto Local Models Switcher

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Hermes Agent](https://img.shields.io/badge/Agent-Hermes--Sandbox-orange.svg)](https://github.com/NousResearch/hermes-agent)
[![Ollama](https://img.shields.io/badge/Engine-Ollama-black.svg)](https://ollama.com)
[![Hardware](https://img.shields.io/badge/GPU-RTX%204060%20%2F%205060%20(8GB%20VRAM)-green.svg)](https://www.nvidia.com)

> **GitHub Copilot "Auto-Mode" for 100% Offline, Local LLMs.**  
> Dynamically evaluates user tasks in **< 1 second** using an ultra-lightweight Pocket-LLM (`qwen2.5:0.5b`) and automatically routes to the best specialized local model — zero cloud costs, zero privacy leaks, and zero GPU memory thrashing.

---

## 🌟 Why Hermes Copilot?

When using autonomous coding agents locally on consumer hardware (e.g., **8GB VRAM GPU + 32GB RAM**), developers face two major obstacles:
1. **Model Selection Fatigue:** Manually guessing whether a task needs a fast coder, a heavy architect, or a deep reasoning model.
2. **VRAM Thrashing:** Traditional proxy routers (like LiteLLM) switch models per-request, forcing Ollama to unload and reload 10–20 GB model weights on every agent step (taking 15+ seconds each time).

**Hermes Copilot** introduces a sub-second **Pocket-LLM Intent Classifier**:
* **50ms Evaluation:** Uses `qwen2.5:0.5b` (~350 MB VRAM) to classify user prompt difficulty.
* **Dynamic Catalog Discovery:** Queries Ollama’s active `/v1/models` API live — no hardcoded config files. When you `ollama pull` a new model, the router instantly knows about it.
* **Hardware-Aware Routing:** Keeps models persistent per session or dispatches recommendations via native in-chat skills.

---

## 🧠 The 4-Model Local Fleet

Tailored for an NVIDIA RTX 5060 / 4060 (8GB VRAM) + 32GB DDR5 system:

| Model | Footprint | Speed | Specialized Role |
| :--- | :--- | :--- | :--- |
| **`qwen2.5:0.5b`** | 397 MB | **180+ tok/s** | ⚡ **The Pocket Router:** Classifies intent in < 50ms |
| **`qwen2.5-coder:14b`** | 9.0 GB | **25 tok/s** | 💻 **Daily Coder:** Functions, unit tests, bug fixes & agent tool calls |
| **`qwen2.5-coder:32b`** | 19.0 GB | **8 tok/s** | 🏛️ **Systems Architect:** Domain design, large refactors & class hierarchies |
| **`deepseek-r1:14b`** | 9.0 GB | **20 tok/s** | 🔒 **Security & Logic:** Vulnerability audit, race conditions & math proofs |

---

## 🏗️ Architecture

```
                       [ User Prompt / Task Query ]
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│         POCKET ROUTER (qwen2.5:0.5b • 397 MB • <1s evaluation)         │
│  1. Live Query: GET http://172.17.0.1:11434/v1/models                   │
│  2. Discovers Pulled Models: [14b-coder, 32b-coder, deepseek-r1:14b]   │
│  3. Intent & Domain Classification:                                    │
│     {                                                                  │
│       "selected_model": "deepseek-r1:14b",                             │
│       "category": "Security & Logic",                                  │
│       "reason": "Requires cryptographic proof and race-condition audit"│
│     }                                                                  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
    [Security / Logic]        [Architecture]        [Routine Coding]
     deepseek-r1:14b         qwen2.5-coder:32b      qwen2.5-coder:14b
            │                       │                       │
            └───────────────────────┼───────────────────────┘
                                    ▼
               [ Hermes Agent Booted with Optimal Brain ]
```

---

## 🚀 Quickstart Guide

### 1. Provision GPU-Accelerated Ollama
Run Ollama in Docker with model persistence:
```powershell
docker run -d --gpus=all -e OLLAMA_KEEP_ALIVE="-1" --name ollama-sandbox-pro `
  -p 11434:11434 -v "D:\Data\Docker Data\Ollama:/root/.ollama" ollama/ollama:latest
```

Pull the 4-model fleet:
```powershell
docker exec -it ollama-sandbox-pro ollama pull qwen2.5:0.5b
docker exec -it ollama-sandbox-pro ollama pull qwen2.5-coder:14b
docker exec -it ollama-sandbox-pro ollama pull qwen2.5-coder:32b
docker exec -it ollama-sandbox-pro ollama pull deepseek-r1:14b
```

### 2. Provision Hermes Sandbox Container
```powershell
docker run -it --name hermes-sandbox-pro -p 9119:9119 `
  -v "D:\Data\Docker Data\Hermes:/workspace" ubuntu:latest bash
```

Inside the container, install dependencies and Hermes Agent:
```bash
apt update && apt install -y curl git sudo nano nodejs npm python3 python3-pip
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc
```

### 3. Install Copilot Router & Aliases
Copy `hermes_copilot.py` to `/workspace/` and configure bash aliases:
```bash
cat << 'EOF' >> ~/.bashrc
alias hermes-copilot="python3 /workspace/hermes_copilot.py"
alias h="python3 /workspace/hermes_copilot.py"
EOF
source ~/.bashrc
```

### 4. Install the Hermes Skill (For In-Chat Routing)
```bash
mkdir -p /root/.hermes/skills/hermes-copilot
cp -rf /workspace/skills/hermes-copilot/* /root/.hermes/skills/hermes-copilot/
hermes skills list
```

### 5. Launch the Web UI Dashboard
Inside `hermes-sandbox-pro`, start the graphical dashboard server:
```bash
hermes dashboard --host 0.0.0.0
```
Open your browser on Windows and navigate to: **`http://localhost:9119`**  
*(Configure your username & password on first launch, then chat visually with memory graphs and tool inspection).*

---

## 💡 How to Use It

### Mode 1: Terminal Auto-Dispatcher (`h "prompt"`)
Launch an autonomous session with the best model selected in ~1 second:
```bash
# Security & Logic -> Automatically dispatches deepseek-r1:14b
h "Audit this token handshake for timing attacks and race conditions"

# Architecture -> Automatically dispatches qwen2.5-coder:32b
h "Design clean architecture domain entities and repository interfaces"

# Daily Coding -> Automatically dispatches qwen2.5-coder:14b
h "Write unit tests for email validation utility with xUnit"
```

**Banner Output Example:**
```text
┌─────────────────────────────────────────────────────────────────┐
│ 🤖 Hermes Copilot (Auto-Mode)
│ 🎯 Task Category  : Security & Logic
│ 🧠 Dispatched Brain: deepseek-r1:14b
│ 💡 Rationale       : Requires security vulnerability and logic analysis.
└─────────────────────────────────────────────────────────────────┘
```

### Mode 2: In-Chat Skill Recommendation (Terminal & Web UI)
While chatting in the terminal or Web UI (`http://localhost:9119`), ask naturally:
> *"Which model should I use for: Analyzing authentication handshake for race conditions?"*

Hermes invokes the local `hermes-copilot` skill, evaluates with `qwen2.5:0.5b`, and responds:
> **Recommended Brain:** `deepseek-r1:14b`  
> **Category:** Security & Logic  
> **Rationale:** Requires vulnerability analysis and formal logic reasoning.  
> *To switch to this model, type:* `/model deepseek-r1:14b`

### Mode 3: In-Session Hot-Swap (`/model`)
Switch models on the fly during an ongoing conversation without losing context:
```text
/model
```

---

## 📁 Repository Structure

```text
hermes-copilot/
├── README.md                              # This file
├── LICENSE                                # MIT License
├── .gitignore                             # Standard Python & OS ignore rules
├── hermes_copilot.py                      # Sub-second Auto-Router script
├── skills/
│   └── hermes-copilot/
│       └── SKILL.md                       # Hermes native in-chat skill
└── docs/
    ├── hermes_docker_setup_guide.md       # Full Hermes sandbox deployment guide
    ├── ollama_docker_setup_guide.md       # GPU-accelerated Ollama 4-model fleet setup
    └── hermes_copilot_auto_router_guide.md # Detailed router architecture & benchmarks
```

---

## 📚 In-Depth Documentation

* 📖 [Hermes Docker Setup Guide](docs/hermes_docker_setup_guide.md)
* 📖 [Ollama Docker & 4-Model Fleet Setup Guide](docs/ollama_docker_setup_guide.md)
* 📖 [Hermes Copilot Auto-Router Technical Guide](docs/hermes_copilot_auto_router_guide.md)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
