# 🤖 Hermes Copilot: Auto Local Models Router & Proxy

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Hermes Agent](https://img.shields.io/badge/Agent-Hermes--Sandbox-orange.svg)](https://github.com/NousResearch/hermes-agent)
[![Ollama](https://img.shields.io/badge/Engine-Ollama-black.svg)](https://ollama.com)
[![Hardware](https://img.shields.io/badge/GPU-RTX%204060%20%2F%205060%20(8GB%20VRAM)-green.svg)](https://www.nvidia.com)

> **GitHub Copilot "Auto-Mode" for 100% Offline, Local LLMs.**  
> Dynamically evaluates user prompts in **milliseconds on CPU** using your choice of **three in-process System 1 Routers** (**Semantic Router**, **RouteLLM**, or **Laya / Jev**) and automatically routes to the best specialized local Ollama model — zero cloud costs, zero privacy leaks, and **0 MB GPU VRAM** wasted on routing.

---

## 🌟 Why Hermes Copilot?

When using autonomous coding agents locally on consumer hardware (e.g., **8GB VRAM GPU + 32GB RAM**), developers face two major obstacles:
1. **Model Selection Fatigue:** Manually guessing whether a task needs a fast daily coder or a deep reasoning/security model.
2. **VRAM Thrashing:** Traditional LLM routers run a small LLM inside Ollama to classify prompts, forcing Ollama to unload and reload 9–18 GB worker weights on every agent turn.

**Hermes Copilot** solves both with an OpenAI-compatible **Auto-Proxy** offered in **3 standalone editions** (`copilot/`) plus a universal configurable entry point (`hermes_proxy.py`):
* **100% CPU In-Process Routing (0 MB GPU VRAM):** The router runs entirely inside the Python proxy process on CPU, leaving **100% of your GPU VRAM** dedicated to the active Ollama worker model (`OLLAMA_MAX_LOADED_MODELS=1`).
* **3 Pluggable System 1 Engines:** Choose between **Semantic Router** (FastEmbed ONNX), **Laya / Jev** (Convai 421M ModernBERT), or **RouteLLM** (LMSYS BERT classifier).
* **Live In-Chat UI Badge:** Injects real-time routing transparency at the top of every chat response:
  `> 🧭 **[Auto Router • Semantic]** Using **`qwen2.5-coder:14b`** *(Task: `coding` • 5.6ms)*`
* **Native `model: auto` Experience:** Select `auto` once in the Hermes Web UI or TUI, just like VS Code GitHub Copilot.
* **Single-Turn Tool Pinning:** Keeps the chosen model pinned during active multi-step tool loops (`bash`, `write_file`) without pinning subsequent user prompts.
* **Zero Hardcoded Model Names:** Queries Ollama `/api/show` capabilities (`thinking`, `tools`) dynamically at runtime.

---

## 🧭 Choose Your Router: 3 Standalone Editions

We benchmarked all three System 1 routers head-to-head on our 40-prompt evaluation suite (`router_lab/prompts.jsonl`: 15 `coding`, 15 `reasoning`, 10 `general`) inside `hermes-sandbox-pro`:

| Router Edition | Standalone Script | 3-Class Accuracy | 2-Model Dispatch Accuracy* | Warm Latency (p50 / p95) | Cold Load | CPU RAM Delta | GPU VRAM | Best For |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Semantic Router** *(Recommended)* | `copilot/hermes_proxy_semantic.py` | **87.5%** (35/40) | **97.5%** (39/40) | **5.58 ms / 7.22 ms** | **3.76 s** | **+340.5 MB** | **0 MB** | 🏆 **Fastest speed, lowest RAM (no PyTorch), best 2-model accuracy** |
| **2. Laya (formerly Jev)** | `copilot/hermes_proxy_laya.py` | **92.5%** (37/40) | **92.5%** (37/40) | **241.2 ms / 279.8 ms** | **4.44 s** | **+1,990.2 MB** | **0 MB** | 🥇 **Highest strict 3-class accuracy (`coding` vs `reasoning` vs `general`)** |
| **3. RouteLLM (LMSYS BERT)** | `copilot/hermes_proxy_routellm.py` | **67.5%** (27/40) | **67.5%** (27/40) | **14.81 ms / 22.31 ms** | **7.85 s** | **+1,210.1 MB** | **0 MB** | ⚡ **Generic Chatbot Arena strong/weak difficulty threshold** |

*\*In the standard 2-model fleet (`qwen2.5-coder:14b` + `deepseek-r1:14b`), both `coding` and `general` prompts route to `qwen2.5-coder:14b`, while `reasoning` routes to `deepseek-r1:14b`. Semantic Router dispatches **39/40 (97.5%)** prompts to the exact right worker model.*

### How to Decide Which Router is Best for You
1. **Pick Semantic Router (`copilot/hermes_proxy_semantic.py`)** if you want **instant ~5ms routing**, minimal CPU RAM (**~340 MB** via ONNX Runtime without PyTorch), and **97.5% effective accuracy** across `qwen2.5-coder:14b` and `deepseek-r1:14b`.
2. **Pick Laya (`copilot/hermes_proxy_laya.py`)** if you run a **3-model fleet** (separate models for `coding`, `reasoning`, and `general` chat), have ~2 GB of spare system RAM, and want zero-shot natural-language criteria powered by Convai's 421M ModernBERT System 1 engine (`convaiinnovations/laya`, formerly `jev`).
3. **Pick RouteLLM (`copilot/hermes_proxy_routellm.py`)** if you prefer LMSYS's Chatbot Arena BERT classifier (`routellm/bert_gpt4_augmented`) that scores general prompt complexity (`win_rate >= threshold`) in **~15ms**.

---

## 🧠 The 2-Tier Execution Fleet (Ollama GPU)

Tailored specifically for consumer GPUs (NVIDIA RTX 5060 / 4060 with 8GB VRAM + 32GB DDR5 system RAM):

| Component | Footprint | Speed / Latency | Specialized Role |
| :--- | :--- | :--- | :--- |
| **System 1 Router** *(Semantic / Laya / RouteLLM)* | 340 MB – 2.0 GB CPU RAM | **5–240 ms** | 🧭 **The Orchestrator:** Classifies intent in Python on CPU (**0 MB Ollama VRAM**) |
| **`qwen2.5-coder:14b`** *(Ollama GPU)* | 9.0 GB | **~25 tok/s** | 💻 **Daily Coder & Tools:** Architecture, code, unit tests, and terminal tools (`tools` capability) |
| **`deepseek-r1:14b`** *(Ollama GPU)* | 9.0 GB | **~20 tok/s** | 🔒 **Security & Reasoning:** Vulnerabilities, timing attacks, math & deep thinking (`thinking` capability) |

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
 │   • copilot/hermes_proxy_semantic.py (FastEmbed ONNX, ~5.6ms)   │
 │   • copilot/hermes_proxy_laya.py     (ModernBERT, ~241ms)       │
 │   • copilot/hermes_proxy_routellm.py (LMSYS BERT, ~14.8ms)      │
 │   • hermes_proxy.py                  (Universal via env var)    │
 │                                                                 │
 │ 1. Intercepts incoming turn with model: "auto"                  │
 │ 2. In-Process CPU System 1 Router (0 MB GPU VRAM):              │
 │    • Dynamic Fleet Profiler (queries Ollama /api/show)          │
 │    • Head & Tail Intent Extraction (< 1,200 chars)              │
 │    • Classifies task category (coding | reasoning | general)    │
 │ 3. Tool-Execution Pinning: Keeps model warm during active tool  │
 │    cycles (bash, write_file) without pinning future prompts.    │
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
Run Ollama in Docker with model persistence and single-slot worker memory (`OLLAMA_MAX_LOADED_MODELS=1`):
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

### 3. Launch Your Chosen Router Edition
The automated switcher manages isolated virtual environments, CPU dependencies, copying, and background daemon execution with zero manual setup:

```powershell
# Launch Semantic Router (Default & Recommended: 5.6ms, ~340MB RAM):
docker exec -it hermes-sandbox-pro bash /workspace/scripts/switch_router.sh semantic

# Or switch to Laya / Jev (Highest 3-Class Accuracy: ~241ms, ~2GB RAM):
docker exec -it hermes-sandbox-pro bash /workspace/scripts/switch_router.sh laya

# Or switch to RouteLLM (LMSYS Arena BERT Classifier: ~14.8ms, ~1.2GB RAM):
docker exec -it hermes-sandbox-pro bash /workspace/scripts/switch_router.sh routellm

# Check active router status & health at any time:
docker exec -it hermes-sandbox-pro bash /workspace/scripts/switch_router.sh status
```

### 4. Configure Hermes Agent for Auto-Mode
Point Hermes to the Auto-Proxy:
```powershell
docker exec -it hermes-sandbox-pro hermes config set model.base_url http://127.0.0.1:8000/v1
docker exec -it hermes-sandbox-pro hermes config set model.default auto
```

### 5. Launch the Web UI Dashboard
Inside `hermes-sandbox-pro`, start the dashboard server:
```powershell
docker exec -it hermes-sandbox-pro hermes dashboard --host 0.0.0.0
```
Open your browser on Windows and navigate to: **`http://localhost:9119`**  

---

## 💡 How to Use It

Open your Hermes Chat UI (terminal or Web UI). The model indicator displays **`auto`**. Type your prompt naturally:

```text
# Security & Logic -> Automatically routes to deepseek-r1:14b
Analyze this authentication handshake for timing attack vulnerabilities and race conditions

# Architecture -> Automatically routes to qwen2.5-coder:14b
Design the enterprise clean architecture for an order fulfillment service with CQRS and MediatR

# Daily Implementation -> Automatically routes to qwen2.5-coder:14b
Write a C# FluentValidation validator for a UserRegistrationDTO and create unit tests
```

---

## 📁 Repository Structure

```text
hermes-copilot/
├── README.md                              # Project overview, router comparison & quickstart
├── LICENSE                                # MIT License
├── .gitignore                             # Git ignore rules
├── requirements.txt                       # Default requirements (Semantic Router ONNX)
├── hermes_proxy.py                        # Active Auto-Proxy (copied or universal entry point)
├── ROUTER_EVALUATION_PLAN.md              # System 1 router evaluation plan & full benchmark report
├── copilot/                               # 3 Standalone Auto-Proxy Editions
│   ├── hermes_proxy_semantic.py           # Edition 1: Semantic Router (FastEmbed ONNX, ~5.6ms)
│   ├── hermes_proxy_routellm.py           # Edition 2: RouteLLM (LMSYS BERT, ~14.8ms)
│   └── hermes_proxy_laya.py               # Edition 3: Laya / Jev (Convai ModernBERT, ~241ms)
├── scripts/                               # Automation & lifecycle scripts
│   └── switch_router.sh                   # 1-command router installer, switcher & health checker
├── requirements/                          # Per-router isolated requirements
│   ├── README.md                          # Human-readable dependency installation guide
│   ├── semantic.txt                       # Semantic Router dependencies (ONNX CPU)
│   ├── routellm.txt                       # RouteLLM dependencies (PyTorch CPU)
│   └── laya.txt                           # Laya dependencies (PyTorch CPU)
├── routers/                               # Pluggable System 1 router backends & fleet profiler
│   ├── __init__.py                        # Lazy backend factory (semantic | routellm | laya)
│   ├── base.py                            # Shared interfaces, Decision types & Head/Tail truncation
│   ├── fleet.py                           # Dynamic Ollama capability profiler (zero hardcoding)
│   ├── semantic_backend.py                # Aurelio AI Semantic Router + FastEmbed ONNX adapter
│   ├── routellm_backend.py                # LMSYS RouteLLM BERTRouter adapter
│   └── laya_backend.py                    # Convai Laya (Jev) ModernBERT choice adapter
├── router_lab/                            # Offline benchmarking suite & recorded measurements
│   ├── bench.py                           # Automated accuracy, latency (p50/p95), and RAM runner
│   ├── prompts.jsonl                      # 40-prompt labeled evaluation dataset
│   └── results/                           # Recorded benchmark JSON outputs
│       ├── semantic.json                  # Semantic Router benchmark results (87.5% / 97.5% fleet)
│       ├── routellm.json                  # RouteLLM benchmark results (67.5%)
│       └── laya.json                      # Laya benchmark results (92.5%)
└── docs/                                  # Comprehensive architecture and setup guides
    ├── hermes_docker_setup_guide.md       # Complete Hermes Docker setup & Auto-Proxy SOP
    ├── ollama_docker_setup_guide.md       # GPU-accelerated Ollama setup & health checks
    └── hermes_copilot_auto_proxy_guide.md # Deep-dive Auto-Proxy guide & 3-router comparison
```

---

## 📚 In-Depth Documentation

* 📖 [Hermes Copilot Auto-Proxy Technical Guide](docs/hermes_copilot_auto_proxy_guide.md)
* 📖 [Hermes Docker Setup Guide](docs/hermes_docker_setup_guide.md)
* 📖 [Ollama Docker Setup Guide](docs/ollama_docker_setup_guide.md)
* 📋 [System 1 Router Evaluation Plan & Benchmarks](ROUTER_EVALUATION_PLAN.md)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
