# 🤖 Hermes Copilot: Auto Local Models Router & Proxy

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Hermes Agent](https://img.shields.io/badge/Agent-Hermes--Sandbox-orange.svg)](https://github.com/NousResearch/hermes-agent)
[![Ollama](https://img.shields.io/badge/Engine-Ollama-black.svg)](https://ollama.com)
[![Hardware](https://img.shields.io/badge/GPU-RTX%204060%20%2F%205060%20(8GB%20VRAM)-green.svg)](https://www.nvidia.com)

> **GitHub Copilot "Auto-Mode" for 100% Offline, Local LLMs.**  
> Dynamically evaluates user tasks in **< 60ms** using an in-process System 1 Router (Semantic Router via FastEmbed / ONNX on CPU) and automatically routes to the best specialized local model — zero cloud costs, zero privacy leaks, and zero GPU memory thrashing.

---

## 🌟 Why Hermes Copilot?

When using autonomous coding agents locally on consumer hardware (e.g., **8GB VRAM GPU + 32GB RAM**), developers face two major obstacles:
1. **Model Selection Fatigue:** Manually guessing whether a task needs a fast coder, a heavy architect, or a deep reasoning model.
2. **VRAM Thrashing:** Traditional proxy routers switch models inside Ollama, forcing Ollama to unload and reload 10–20 GB model weights on every agent step (taking 15+ seconds each time).

**Hermes Copilot** introduces a native OpenAI-compatible **Auto-Proxy (`hermes_proxy.py`)**:
* **Sub-60ms In-Process Router:** Routes prompts directly in Python on CPU in **5–60 ms** with **0 MB GPU VRAM**, leaving 100% of your GPU dedicated to the active worker model.
* **In-Chat UI Badge:** Injects real-time feedback directly into your chat: `> 🧭 [Auto Router] Using qwen2.5-coder:14b (Task: coding • 56.9ms)`.
* **Native In-Chat Auto Mode:** You simply select `model: auto` in the Hermes Web UI or TUI, exactly like VS Code Copilot.
* **Tool-Turn Pinning:** When Hermes enters an iterative tool-execution cycle (bash commands, writing files), the proxy locks the model in place to prevent mid-task model swapping.
* **Zero Hardcoded Names:** Dispatches dynamically using Ollama capability tags (`thinking`, `tools`).

---

## 🧠 The 2-Tier Execution Fleet + CPU System 1 Router

Tailored specifically for consumer GPUs (NVIDIA RTX 5060 / 4060 with 8GB VRAM + 32GB DDR5 system):

| Component | Footprint | Speed / Latency | Specialized Role |
| :--- | :--- | :--- | :--- |
| **System 1 Router** *(Semantic Router / FastEmbed)* | ~350 MB RAM (CPU) | **5–60 ms** | 🧭 **The Orchestrator:** Classifies intent in Python on CPU (0 MB Ollama VRAM) |
| **`qwen2.5-coder:14b`** *(Ollama GPU)* | 9.0 GB | **25 tok/s** | 💻 **Daily Coder & Tools:** Architecture, code, unit tests, and terminal tools |
| **`deepseek-r1:14b`** *(Ollama GPU)* | 9.0 GB | **20 tok/s** | 🔒 **Security & Reasoning:** Vulnerabilities, timing attacks, math & deep thinking |

> [!NOTE]
> With the router running entirely in Python on CPU, Ollama only needs to load **1 worker model at a time**, dedicating 100% of your GPU VRAM to task execution without model-swapping lag.

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
 │ 2. Sub-60ms System 1 Router (In-Process CPU / ONNX):            │
 │    • Dynamic Fleet Profiler (queries Ollama capabilities)       │
 │    • Head & Tail Intent Extraction (< 1,200 chars)              │
 │    • Fast intent classification (Semantic Router / FastEmbed)   │
 │ 3. Tool-Execution Pinning: Keeps model warm during active tool  │
 │    cycles (bash, write_file) to prevent VRAM swapping freezes.  │
 │ 4. Injects real-time visual badge into the chat response stream │
 └──────────────────────────────┬──────────────────────────────────┘
                                │ Forwards with real model name
                                ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │               OLLAMA (GPU Port 11434)                           │
 │     Executes ONLY the active worker model (100% GPU VRAM)       │
 └─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart Guide

### 1. Provision GPU-Accelerated Ollama
Run Ollama in Docker with model persistence (dedicated single worker slot for 100% GPU VRAM):
```powershell
docker run -d --gpus=all -e OLLAMA_KEEP_ALIVE="-1" -e OLLAMA_MAX_LOADED_MODELS="1" --name ollama-sandbox-pro `
  -p 11434:11434 -v "D:\Data\Docker Data\Ollama:/root/.ollama" ollama/ollama:latest
```

Pull the execution model fleet:
```powershell
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
Ensure `hermes_proxy.py` and `routers/` are in `/workspace/` and install router prerequisites:
```bash
pip install semantic-router fastembed fastapi uvicorn httpx
nohup python3 /workspace/hermes_proxy.py > /workspace/proxy.log 2>&1 &
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
├── README.md                              # Project overview and quickstart
├── LICENSE                                # MIT License
├── .gitignore                             # Git ignore rules
├── hermes_proxy.py                        # OpenAI-compatible Auto-Proxy router with chat UI badges
├── ROUTER_EVALUATION_PLAN.md              # Living evaluation plan & benchmark tracker
├── routers/                               # System 1 router backends & dynamic fleet profiler
│   ├── __init__.py                        # Lazy backend factory
│   ├── base.py                            # Shared interfaces, Decision types & intent truncation
│   ├── fleet.py                           # Dynamic Ollama capability profiler (zero hardcoding)
│   └── semantic.py                        # Semantic Router backend (FastEmbed / ONNX)
├── router_lab/                            # Benchmarking test suite & offline datasets
│   ├── bench.py                           # Automated latency, RAM, and accuracy benchmark runner
│   ├── prompts.jsonl                      # 40-prompt labeled evaluation benchmark suite
│   └── results/                           # JSON benchmark output records
└── docs/                                  # Comprehensive architecture and setup guides
    ├── hermes_docker_setup_guide.md       # Complete Hermes Docker setup & Auto-Proxy guide
    ├── ollama_docker_setup_guide.md       # GPU-accelerated Ollama setup & health checks
    └── hermes_copilot_auto_proxy_guide.md # Detailed Auto-Proxy architecture & verified benchmarks
```

---

## 📚 In-Depth Documentation

* 📖 [Hermes Docker Setup Guide](docs/hermes_docker_setup_guide.md)
* 📖 [Ollama Docker Setup Guide](docs/ollama_docker_setup_guide.md)
* 📖 [Hermes Copilot Auto-Proxy Technical Guide](docs/hermes_copilot_auto_proxy_guide.md)
* 📋 [System 1 Router Evaluation Plan](ROUTER_EVALUATION_PLAN.md)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
