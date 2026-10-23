# Hermes Copilot Auto-Proxy Guide (Autonomous Universal Orchestrator)

This guide documents the **Hermes Copilot Auto-Proxy** (`hermes_proxy.py`). It brings a genuine **GitHub Copilot "Auto"** model selection experience to locally hosted LLMs running in Ollama and Hermes Agent.

---

## 1. Overview & Architecture

Instead of manually guessing models, switching configs, or running rigid linear scripts, you simply select **`auto`** in Hermes Agent. 

When you submit a prompt in the Hermes Chat, TUI, or Web UI dashboard:
1. The request is intercepted by the local **Hermes Auto-Proxy** on port `8000`.
2. An in-process **System 1 Router** (Semantic Router via FastEmbed / ONNX on CPU) evaluates the prompt intent in **5–60 milliseconds** with **0 MB GPU VRAM**.
3. A dynamic **Fleet Profiler** inspects Ollama model capabilities (`thinking` for reasoning, `tools` for coding/tools) and pairs the intent with the best installed model.
4. The proxy dynamically rewrites `model: "auto"` to the chosen model, injects a **visual status badge** into the chat stream, and streams the worker model directly into Hermes.

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
 │    • Dynamic Fleet Profiler (queries Ollama /api/show)          │
 │    • Head & Tail Intent Extraction (< 1,200 chars)              │
 │    • Fast intent classification (Semantic Router / FastEmbed)   │
 │ 3. Tool-Execution Pinning: Keeps model warm during active tool  │
 │    cycles (bash, write_file) to prevent mid-turn model swaps.   │
 │ 4. Injects visual badge: > 🧭 [Auto Router] Using model...      │
 └──────────────────────────────┬──────────────────────────────────┘
                                │ Forwards with real model name
                                ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │               OLLAMA (GPU Port 11434)                           │
 │     Executes ONLY the active worker model (100% GPU VRAM)       │
 └─────────────────────────────────────────────────────────────────┘
```

---

## 2. The System 1 Router Architecture

The core architectural breakthrough of Hermes Copilot Auto-Proxy is the **complete separation of routing from the Ollama GPU daemon**.

### A. In-Process System 1 Routing (CPU / ONNX)
* **Zero GPU VRAM:** Previous architectures ran a 1.5B LLM inside Ollama as the router, causing GPU VRAM thrashing and model-swapping evictions. The new router runs entirely in Python on CPU using FastEmbed ONNX embeddings (~350 MB RAM).
* **Blazing Fast (< 60ms):** Vector similarity classification finishes in **5 to 60 ms**—over 50x faster than prompting an LLM.
* **100% Dedicated Worker VRAM:** Because routing uses 0 MB of Ollama memory, Ollama dedicates 100% of its resources to the currently active worker model (`qwen2.5-coder:14b` or `deepseek-r1:14b`).

### B. Dynamic Capability-Based Fleet Profiling (Zero Hardcoded Names)
* **No Hardcoded Model Names:** The proxy queries Ollama's active catalog (`/v1/models` and `/api/show`) and reads model capabilities:
  - `reasoning` $\rightarrow$ Model with the `thinking` capability (e.g. `deepseek-r1:14b`).
  - `coding` $\rightarrow$ Model with `tools` and without `thinking` (e.g. `qwen2.5-coder:14b`).
  - `general` $\rightarrow$ Smallest model without `thinking` (falls back to coder if 2-model fleet).
* **Fail Loudly & Actionably:** If no installed model satisfies the required capability, the proxy stops with a clear banner rather than silently defaulting.

### C. Head & Tail Truncation
In real autonomous agent workflows, conversation turns can reach 10,000 to 20,000+ tokens (system prompts, tool definitions, file contents, bash outputs).
* The proxy extracts the **Head (first 600 characters)** and **Tail (last 600 characters)** of the latest user prompt.
* This captures both the primary objective and immediate instructions while skipping middle noise, ensuring instant classification regardless of conversation length.

### D. Single-Turn Continuation Pinning
* **Why tool loops must stay pinned:** During iterative agent tool cycles (reading files, executing bash, running tests), switching models mid-step breaks execution context.
* **Pinning Logic:** The proxy checks **only the immediate last message role**. If the last message is a `tool` result or an identical user prompt, the model remains pinned. The moment the user types a new prompt, routing runs fresh.

### E. Live In-Chat Transparency Badge
Every time the router selects a model, it injects a clean markdown badge at the very top of the chat response stream:

> 🧭 **[Auto Router]** Using **`qwen2.5-coder:14b`** *(Task: `coding` • 56.9ms)*

---

## 3. Setup & Deployment Instructions

### Step 1: Ensure Your Execution Fleet is Pulled
From your Windows PowerShell host:
```powershell
docker exec -it ollama-sandbox-pro ollama pull qwen2.5-coder:14b
docker exec -it ollama-sandbox-pro ollama pull deepseek-r1:14b
```

### Step 2: Start the Auto-Proxy in Hermes Container
Inside `hermes-sandbox-pro`, launch the proxy in the background using its isolated router virtual environment:
```powershell
docker exec -d hermes-sandbox-pro nohup /opt/router-venvs/semantic/bin/python /workspace/hermes_proxy.py > /workspace/proxy.log 2>&1
```

Verify that the proxy is healthy:
```powershell
docker exec -it hermes-sandbox-pro curl -s http://127.0.0.1:8000/v1/models
```
*(You will see `"id": "auto"` listed at the top of the model catalog).*

### Step 3: Configure Hermes Agent to Use Auto-Mode
Point Hermes to the Auto-Proxy:
```powershell
docker exec -it hermes-sandbox-pro hermes config set model.base_url http://127.0.0.1:8000/v1
docker exec -it hermes-sandbox-pro hermes config set model.default auto
```

Verify active configuration:
```powershell
docker exec -it hermes-sandbox-pro hermes config get model
```
**Output:**
```yaml
default: auto
provider: custom
base_url: http://127.0.0.1:8000/v1
api_key: '***'
```

---

## 4. Live Verified Prompts & Multi-Turn Behavior

Here is the exact verified behavior across consecutive turns in the same chat session:

### Turn 1: Coding & Autonomous Tools
**Prompt:**
```text
Write a Python script that searches a directory for log files older than 30 days, compresses them into a tar.gz archive, and deletes the originals. Include error handling.
```
* **Routing:** `coding` • **77.0ms**
* **Dispatched Model:** `qwen2.5-coder:14b`
* **Behavior:** Dispatched autonomous bash terminal tool command to find, archive, and clean up files.

### Turn 2: Security & Deep Reasoning
**Prompt (same session):**
```text
Audit this signature verification logic for timing attack vulnerabilities:
def verify(user_sig, real_sig):
    if len(user_sig) != len(real_sig): return False
    for a, b in zip(user_sig, real_sig):
        if a != b: return False
    return True
Explain how an attacker exploits this and provide the constant-time fix.
```
* **Routing:** `reasoning` • **55.7ms**
* **Dispatched Model:** `deepseek-r1:14b`
* **Behavior:** DeepSeek engaged **542 thinking tokens**, analyzed the early-exit vulnerability, and provided the constant-time fix.

### Turn 3: Switching Back to Coding (Zero Pinning Regression)
**Prompt (same session):**
```text
Now write comprehensive pytest unit tests for the constant-time fix you just provided, testing valid signatures, invalid signatures, and different lengths.
```
* **Routing:** `coding` • **56.9ms**
* **Dispatched Model:** `qwen2.5-coder:14b`
* **Behavior:** Switched smoothly back to the coding model, writing a 5-case pytest test suite.

---

## 5. Live Monitoring & Logs

Every dispatch decision is logged in real-time to:
* **Host:** `D:\Data\Docker Data\Hermes\proxy.log`
* **Container:** `/workspace/proxy.log`

**Sample Log Entry:**
```text
[2026-10-23 15:39:56]
┌─────────────────────────────────────────────────────────────────┐
│ 🤖 Hermes Copilot Autonomous Orchestrator
│ 🧭 Router Backend   : semantic (CPU, in-process)
│ 📦 Execution Fleet  : ['qwen2.5-coder:14b', 'deepseek-r1:14b']
│ 🏷️  Task Category    : coding (confidence 0.63)
│ 🚀 Dispatched Model : qwen2.5-coder:14b ['completion', 'tools', 'insert'] 14.8B
│ ⏱️  Routing Latency  : 16.7ms
└─────────────────────────────────────────────────────────────────┘
```
