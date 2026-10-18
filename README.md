# 🤖 Hermes Copilot: Auto Local Models Router & Proxy

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
2. **VRAM Thrashing:** Traditional proxy routers switch models per-request, forcing Ollama to unload and reload 10–20 GB model weights on every agent step (taking 15+ seconds each time).

**Hermes Copilot** introduces a native OpenAI-compatible **Auto-Proxy (`hermes_proxy.py`)**:
* **50ms Evaluation:** Uses `qwen2.5:0.5b` (~350 MB VRAM) to classify user prompt difficulty.
* **Native In-Chat Auto Mode:** You simply select `model: auto` in the Hermes Web UI or TUI, exactly like VS Code Copilot.
* **Tool-Turn Pinning:** When Hermes enters an iterative tool-execution cycle (bash commands, writing files), the proxy locks the model in place to prevent VRAM swapping freezes.
* **Cloud-Ready:** Standard OpenAI API interface allows routing to cloud models (OpenRouter, Claude 3.5 Sonnet, GPT-4o) with zero Hermes reconfiguration.

---

## 🧠 The 3-Tier Local Fleet Architecture

Tailored specifically for consumer GPUs (NVIDIA RTX 5060 / 4060 with 8GB VRAM + 32GB DDR5 system):

| Model | Footprint | Speed | Specialized Role |
| :--- | :--- | :--- | :--- |
| **`qwen2.5:0.5b`** | 397 MB | **180+ tok/s** | ⚡ **The Pocket Router:** Classifies task intent in < 50ms |
| **`qwen2.5-coder:14b`** | 9.0 GB | **25 tok/s** | 💻 **Daily Coder & Systems Architect:** Clean architecture, unit tests, code & tool calls |
| **`deepseek-r1:14b`** | 9.0 GB | **20 tok/s** | 🔒 **Security & Logic:** Vulnerability audit, race conditions & cryptographic proofs |

> [!NOTE]
> `qwen2.5-coder:32b` (19.0 GB) is strictly optional and only recommended for high-VRAM rigs ($\ge 16\text{GB}$ VRAM or $\ge 64\text{GB}$ RAM) to avoid Windows paging freezes. On 8GB VRAM cards, `14b` is the verified optimal performer.

---

## 🏗️ Architecture

```
 ┌─────────────────────────────────────────────────────────────────┐
 │               HERMES AGENT (Web UI / TUI / Chat)                │
 │                     Active Model: "auto"                        │
 └──────────────────────────────┬──────────────────────────────────┘
                                │ POST /v1/chat/completions (model: "auto")
                                ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │       HERMES AUTO-PROXY (FastAPI • Local Port 8000)             │
 │                                                                 │
 │ 1. Intercepts incoming turn with model: "auto"                  │
 │ 2. Sub-Second Pocket Classifier (qwen2.5:0.5b in 50ms):         │
 │    • Security / Cryptography / Logic ──▶ deepseek-r1:14b        │
 │    • Architecture / Systems Design   ──▶ qwen2.5-coder:14b      │
 │    • Routine Coding / Unit Tests     ──▶ qwen2.5-coder:14b      │
 │ 3. Tool-Execution Pinning: Keeps model warm during active tool  │
 │    cycles (bash, write_file) to prevent VRAM swapping freezes.  │
 └──────────────────────────────┬──────────────────────────────────┘
                                │ Forwards with real model name
                                ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │               OLLAMA (GPU Port 11434)                           │
 │        Executes the chosen model and streams back               │
 └─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart Guide

### 1. Provision GPU-Accelerated Ollama
Run Ollama in Docker with model persistence:
```powershell
docker run -d --gpus=all -e OLLAMA_KEEP_ALIVE="-1" --name ollama-sandbox-pro `
  -p 11434:11434 -v "D:\Data\Docker Data\Ollama:/root/.ollama" ollama/ollama:latest
```

Pull the model fleet:
```powershell
docker exec -it ollama-sandbox-pro ollama pull qwen2.5:0.5b
docker exec -it ollama-sandbox-pro ollama pull qwen2.5-coder:14b
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

### 3. Start the Auto-Proxy Service
Ensure `hermes_proxy.py` is in `/workspace/` and launch the daemon inside the container:
```bash
nohup /usr/local/lib/hermes-agent/venv/bin/python3 /workspace/hermes_proxy.py > /workspace/proxy.log 2>&1 &
```

### 4. Configure Hermes Agent for Auto-Mode
Point Hermes to the Auto-Proxy:
```bash
hermes config set model.base_url http://127.0.0.1:8000/v1
hermes config set model.default auto
```

### 5. Launch the Web UI Dashboard
Inside `hermes-sandbox-pro`, start the dashboard server:
```bash
hermes dashboard --host 0.0.0.0
```
Open your browser on Windows and navigate to: **`http://localhost:9119`**  

---

## 💡 How to Use It

Open your Hermes Chat UI (terminal or Web UI). The model indicator displays **`auto`**. Type your prompt naturally:

```text
# Security & Logic -> Automatically routes to deepseek-r1:14b
Analyze this authentication handshake for timing attack vulnerabilities and race conditions

# Architecture -> Automatically routes to qwen2.5-coder:14b and calls architecture-diagram
Design the enterprise clean architecture for an order fulfillment service with CQRS and MediatR

# Daily Implementation -> Automatically routes to qwen2.5-coder:14b
Write a C# FluentValidation validator for a UserRegistrationDTO and create unit tests
```

---

## 📁 Repository Structure

```text
hermes-copilot/
├── README.md                              # This file
├── LICENSE                                # MIT License
├── .gitignore                             # Git ignore rules
├── hermes_proxy.py                        # OpenAI-compatible Auto-Proxy router
└── docs/
    ├── hermes_docker_setup_guide.md       # Complete Hermes Docker setup & Auto-Proxy guide
    ├── ollama_docker_setup_guide.md       # GPU-accelerated Ollama setup & health checks
    └── hermes_copilot_auto_proxy_guide.md # Detailed Auto-Proxy architecture & benchmarks
```

---

## 📚 In-Depth Documentation

* 📖 [Hermes Docker Setup Guide](docs/hermes_docker_setup_guide.md)
* 📖 [Ollama Docker Setup Guide](docs/ollama_docker_setup_guide.md)
* 📖 [Hermes Copilot Auto-Proxy Technical Guide](docs/hermes_copilot_auto_proxy_guide.md)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
