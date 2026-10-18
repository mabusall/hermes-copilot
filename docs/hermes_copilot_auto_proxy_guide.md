# Hermes Copilot Auto-Proxy Guide (Intelligent Model Router)

This guide documents the **Hermes Copilot Auto-Proxy** (`hermes_proxy.py`). It brings a genuine **GitHub Copilot "Auto"** model selection experience to locally hosted LLMs running in Ollama and Hermes Agent.

---

## 1. Overview & Architecture

Instead of manually guessing models or running rigid linear scripts, you simply select **`auto`** in Hermes Agent. 

When you submit a prompt in the Hermes Chat, TUI, or Web UI dashboard:
1. The request is intercepted by the local **Hermes Auto-Proxy** on port `8000`.
2. A pocket-sized **`qwen2.5:0.5b`** model evaluates task difficulty and domain requirements in **50 milliseconds**.
3. The proxy dynamically rewrites `model: "auto"` to the ideal model (`deepseek-r1:14b` or `qwen2.5-coder:14b`) and streams the response directly into Hermes without delay.

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

## 2. Why This is Better Than Traditional Proxies

1. **Native In-Chat "Auto" Experience:** Works directly inside Hermes Agent's chat prompt and Web UI dashboard. No external CLI launchers required.
2. **Zero VRAM Thrashing (Tool-Turn Pinning):** When an agent executes multiple tool calls (e.g. running unit tests, fixing code, creating files), the proxy keeps the dispatched model pinned for that entire turn so Ollama never swaps weights mid-step.
3. **Hardware-Optimized for Consumer GPUs:** Tuned specifically for 8GB VRAM cards (RTX 4060 / 5060) backed by 32GB RAM, preventing out-of-memory disk swapping freezes.
4. **Cloud-Ready Compatibility:** Because it speaks the standard OpenAI API (`/v1/chat/completions`), this exact proxy architecture can be pointed to cloud providers (OpenRouter, Anthropic Claude 3.5 Sonnet, OpenAI o1) with zero changes to Hermes!

---

## 3. Setup Instructions

### Step 1: Ensure Pocket Router is Pulled in Ollama
From your Windows PowerShell host:
```powershell
docker exec -it ollama-sandbox-pro ollama pull qwen2.5:0.5b
```

### Step 2: Start the Auto-Proxy in Hermes Container
Inside `hermes-sandbox-pro`, start the proxy daemon:
```bash
nohup /usr/local/lib/hermes-agent/venv/bin/python3 /workspace/hermes_proxy.py > /workspace/proxy.log 2>&1 &
```

Verify that the proxy is healthy:
```bash
curl http://127.0.0.1:8000/v1/models
```
*(You will see `"id": "auto"` listed at the top of the model catalog).*

### Step 3: Configure Hermes Agent to Use Auto-Mode
Run these commands inside the container (or via `docker exec` from host PowerShell):
```bash
hermes config set model.base_url http://127.0.0.1:8000/v1
hermes config set model.default auto
```

Verify the active configuration:
```bash
hermes config get model
```
**Output:**
```text
default: auto
provider: custom
base_url: http://127.0.0.1:8000/v1
api_key: '***'
```

---

## 4. Verified Usage Examples

### Example A: Security & Cryptographic Analysis (Routes to DeepSeek)
**Prompt in Hermes Chat:**
```text
Analyze this authentication handshake for timing attack vulnerabilities and race conditions
```
* **Dispatched Brain:** `deepseek-r1:14b`
* **Behavior:** DeepSeek engages deep chain-of-thought thinking (`Thinking ~547 tokens`), analyzing TLS handshakes, constant-time mitigations, and race conditions.
* **GPU Verification (`ollama ps`):**
  ```text
  NAME             ID              SIZE      PROCESSOR          CONTEXT    UNTIL
  deepseek-r1:14b  c333b7232bdb    10.0 GB   38%/62% CPU/GPU    4096       29 minutes from now
  ```

---

### Example B: Software Architecture & System Design (Routes to Qwen 14B)
**Prompt in Hermes Chat:**
```text
Design the enterprise clean architecture for an order fulfillment service with CQRS and MediatR
```
* **Dispatched Brain:** `qwen2.5-coder:14b`
* **Latency:** Responded in **8 seconds** without VRAM freezes.
* **Behavior:** Autonomously invoked Hermes's built-in `architecture-diagram` tool to render the CQRS/MediatR system flow.
* **GPU Verification (`ollama ps`):**
  ```text
  NAME               ID              SIZE      PROCESSOR          CONTEXT    UNTIL
  qwen2.5-coder:14b  4828733707be    15 GB     62%/38% CPU/GPU    32768      29 minutes from now
  ```

---

### Example C: Routine Development & Tool Execution (Routes to Qwen 14B)
**Prompt in Hermes Chat:**
```text
Write a C# FluentValidation validator for a UserRegistrationDTO and create unit tests
```
* **Dispatched Brain:** `qwen2.5-coder:14b`
* **Behavior:** Generated `UserRegistrationDTO`, created comprehensive validation rules, and built an NUnit test fixture with happy and edge cases via `execute_code`.

---

## 5. Live Monitoring & Logs

Every dispatch decision is logged in real-time to:
* **Host:** `D:\Data\Docker Data\Hermes\proxy.log`
* **Container:** `/workspace/proxy.log`

**Sample Log Entry:**
```text
┌─────────────────────────────────────────────────────────────────┐
│ 🤖 Hermes Copilot Auto-Proxy                                    │
│ 🎯 Task Category  : Architecture & Systems Design
│ 🧠 Dispatched Brain: qwen2.5-coder:14b
│ ⏱️  Routing Latency : 0ms
└─────────────────────────────────────────────────────────────────┘
```
