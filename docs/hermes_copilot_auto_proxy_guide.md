# Hermes Copilot Auto-Proxy Guide (Autonomous Universal Orchestrator)

This guide documents the **Hermes Copilot Auto-Proxy** (`hermes_proxy.py` and the 3 standalone editions in `copilot/`). It brings a genuine **GitHub Copilot "Auto"** model selection experience to locally hosted LLMs running in Ollama and Hermes Agent.

---

## 1. Overview & Architecture

Instead of manually guessing models, switching configs, or running rigid linear scripts, you simply select **`auto`** in Hermes Agent. 

When you submit a prompt in the Hermes Chat, TUI, or Web UI dashboard:
1. The request is intercepted by the local **Hermes Auto-Proxy** on port `8000`.
2. An in-process **System 1 Router** (**Semantic Router**, **Laya / Jev**, or **RouteLLM** running on CPU) evaluates the prompt intent in milliseconds with **0 MB GPU VRAM**.
3. A dynamic **Fleet Profiler** (`routers/fleet.py`) inspects Ollama model capabilities (`thinking` for reasoning, `tools` for coding/tools) and pairs the intent with the best installed model.
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
 │   • copilot/hermes_proxy_semantic.py (Semantic Router, ~5.6ms)  │
 │   • copilot/hermes_proxy_laya.py     (Laya ModernBERT, ~241ms)  │
 │   • copilot/hermes_proxy_routellm.py (RouteLLM BERT, ~14.8ms)   │
 │   • hermes_proxy.py                  (Universal via env var)    │
 │                                                                 │
 │ 1. Intercepts incoming turn with model: "auto"                  │
 │ 2. In-Process System 1 Router (CPU, 0 MB Ollama VRAM):          │
 │    • Dynamic Fleet Profiler (queries Ollama /api/show)          │
 │    • Head & Tail Intent Extraction (< 1,200 chars)              │
 │    • Fast intent classification (coding | reasoning | general)  │
 │ 3. Tool-Execution Pinning: Keeps model warm during active tool  │
 │    cycles (bash, write_file) to prevent mid-turn model swaps.   │
 │ 4. Injects visual badge: > 🧭 [Auto Router • <Edition>] ...     │
 └──────────────────────────────┬──────────────────────────────────┘
                                │ Forwards with real model name
                                ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │               OLLAMA (GPU Port 11434)                           │
 │     Executes ONLY the active worker model (100% GPU VRAM)       │
 └─────────────────────────────────────────────────────────────────┘
```

---

## 2. Comparing the 3 Standalone Router Editions (`copilot/`)

Hermes Copilot ships with **three dedicated standalone proxy scripts** inside `copilot/`, each paired with its own isolated Python virtual environment in `/opt/router-venvs/`:

| Edition | Script Path | Engine / Backbone | 3-Class Accuracy | 2-Model Dispatch Accuracy* | Warm Latency (p50 / p95) | Cold Load | CPU RAM Delta | Chat Badge Prefix |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Semantic Router** *(Default)* | `copilot/hermes_proxy_semantic.py` | Aurelio AI + FastEmbed (`BAAI/bge-small-en-v1.5` ONNX) | **87.5%** (35/40) | **97.5%** (39/40) | **5.58 ms / 7.22 ms** | **3.76 s** | **+340.5 MB** | `🧭 [Auto Router • Semantic]` |
| **Laya (formerly Jev)** | `copilot/hermes_proxy_laya.py` | Convai `convaiinnovations/laya` (421M ModernBERT-large) | **92.5%** (37/40) | **92.5%** (37/40) | **241.2 ms / 279.8 ms** | **4.44 s** | **+1,990.2 MB** | `🧭 [Auto Router • Laya]` |
| **RouteLLM** | `copilot/hermes_proxy_routellm.py` | LMSYS `routellm/bert_gpt4_augmented` (BERT Classifier) | **67.5%** (27/40) | **67.5%** (27/40) | **14.81 ms / 22.31 ms** | **7.85 s** | **+1,210.1 MB** | `🧭 [Auto Router • RouteLLM]` |

*\*In a 2-model fleet (`qwen2.5-coder:14b` + `deepseek-r1:14b`), both `coding` and `general` categories route to `qwen2.5-coder:14b`, and `reasoning` routes to `deepseek-r1:14b`.*

### Deep Dive into Each Edition

1. **Edition 1: Semantic Router (`copilot/hermes_proxy_semantic.py`) — *Recommended for Most Users***
   * **How it works:** Embeds incoming prompts using `BAAI/bge-small-en-v1.5` on ONNX Runtime (CPU) and computes cosine similarity against curated domain utterances (`coding`, `reasoning`, `general`) in `routers/semantic_backend.py`.
   * **Why choose it:** Requires **no PyTorch** (~340 MB RAM), classifies in **5.6 ms**, and achieves **97.5% (39/40)** effective model dispatch accuracy for the 2-model fleet.
2. **Edition 2: Laya / Jev (`copilot/hermes_proxy_laya.py`) — *Best for 3-Model Fleets & Zero-Shot Criteria***
   * **How it works:** Uses Convai Innovations' 421M ModernBERT non-autoregressive System 1 decision engine (`convaiinnovations/laya`, the official PyPI release of `jev`) to evaluate natural-language `choice` criteria in a single forward pass with calibrated probabilities (`routers/laya_backend.py`).
   * **Why choose it:** Achieves the **highest strict 3-way accuracy (92.5%: 100% coding, 100% general, 80% reasoning)** without needing example utterances—you simply describe each category in plain English.
3. **Edition 3: RouteLLM (`copilot/hermes_proxy_routellm.py`) — *Best for Generic Arena Difficulty Thresholding***
   * **How it works:** Runs LMSYS's `BERTRouter` (`routellm/bert_gpt4_augmented`) trained on Chatbot Arena battles to predict the probability (`win_rate`) that a prompt requires a frontier/strong model (`routers/routellm_backend.py`).
   * **Why choose it:** Fast (**14.8 ms**) binary difficulty router controlled by a single environment variable (`ROUTELLM_THRESHOLD=0.5`).

---

## 3. Core Architectural Principles

### A. In-Process System 1 Routing (0 MB GPU VRAM)
* **Zero GPU VRAM:** Earlier architectures ran a 1.5B LLM inside Ollama as the router, causing GPU VRAM thrashing and model-swapping evictions. All three System 1 routers run entirely in Python on CPU.
* **100% Dedicated Worker VRAM:** Because routing uses 0 MB of Ollama memory, Ollama is configured with `OLLAMA_MAX_LOADED_MODELS=1` and dedicates 100% of its resources to the active worker model (`qwen2.5-coder:14b` or `deepseek-r1:14b`).

### B. Dynamic Capability-Based Fleet Profiling (Zero Hardcoded Names)
* **No Hardcoded Model Names:** `routers/fleet.py` queries Ollama's active catalog (`/v1/models` and `/api/show`) and reads model capabilities:
  - `reasoning` $\rightarrow$ Model with the `thinking` capability (e.g. `deepseek-r1:14b`).
  - `coding` $\rightarrow$ Model with `tools` and without `thinking` (e.g. `qwen2.5-coder:14b`).
  - `general` $\rightarrow$ Smallest model without `thinking` (resolves to `qwen2.5-coder:14b` in a 2-model fleet).
* **Fail Loudly & Actionably:** If no installed model satisfies the required capability, the proxy returns a clear error banner in chat rather than silently defaulting.

### C. Head & Tail Truncation
In real autonomous agent workflows, conversation turns can reach 10,000 to 20,000+ tokens (system prompts, tool definitions, file contents, bash outputs).
* `extract_routing_intent()` in `routers/base.py` extracts the **Head (first 600 characters)** and **Tail (last 600 characters)** of the latest user prompt.
* This captures both the primary objective and immediate instructions while skipping middle noise, ensuring instant classification regardless of conversation length.

### D. Single-Turn Continuation Pinning
* **Why tool loops must stay pinned:** During iterative agent tool cycles (reading files, executing bash, running tests), switching models mid-step breaks execution context.
* **Pinning Logic:** The proxy checks **only the immediate last message role**. If the last message is a `tool` result or an identical user prompt, the model remains pinned. The moment the user types a new prompt, routing runs fresh.

### E. Live In-Chat Transparency Badge
Every time the router selects a model, it injects a clean markdown badge at the very top of the chat response stream indicating which edition made the decision:

> 🧭 **[Auto Router • Semantic]** Using **`qwen2.5-coder:14b`** *(Task: `coding` • 5.6ms)*

---

## 4. Setup, Deployment & Switching Routers

### Step 1: Ensure Your Execution Fleet is Pulled
From your Windows PowerShell host:
```powershell
docker exec -it ollama-sandbox-pro ollama pull qwen2.5-coder:14b
docker exec -it ollama-sandbox-pro ollama pull deepseek-r1:14b
```

### Step 2: Launch Your Preferred Router Edition

The automated switcher manages isolated virtual environments, CPU dependencies, copying, and background daemon execution with one command:
```powershell
# Semantic Router Edition (Recommended Default: ~5.6ms, ~340MB RAM):
docker exec -it hermes-sandbox-pro bash /workspace/scripts/switch_router.sh semantic

# Or Laya (Jev) Edition (Highest 3-Class Accuracy: ~241ms, ~2GB RAM):
docker exec -it hermes-sandbox-pro bash /workspace/scripts/switch_router.sh laya

# Or RouteLLM Edition (LMSYS Arena BERT Classifier: ~14.8ms, ~1.2GB RAM):
docker exec -it hermes-sandbox-pro bash /workspace/scripts/switch_router.sh routellm

# Check active router status & health at any time:
docker exec -it hermes-sandbox-pro bash /workspace/scripts/switch_router.sh status
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

---

## 5. Live Verified Prompts & Multi-Turn Behavior

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

## 6. Live Monitoring & Logs

Every dispatch decision is logged in real-time to:
* **Host:** `D:\Data\Docker Data\Hermes\proxy.log`
* **Container:** `/workspace/proxy.log`

**Sample Log Entry:**
```text
[2026-10-23 15:39:56]
┌─────────────────────────────────────────────────────────────────┐
│ 🤖 Hermes Copilot Autonomous Orchestrator (Semantic Router Edition)
│ 🧭 Router Backend   : semantic (FastEmbed ONNX, CPU)
│ 📦 Execution Fleet  : ['qwen2.5-coder:14b', 'deepseek-r1:14b']
│ 🏷️  Task Category    : coding (confidence 0.63)
│ 🚀 Dispatched Model : qwen2.5-coder:14b ['completion', 'tools', 'insert'] 14.8B
│ ⏱️  Routing Latency  : 5.6ms
└─────────────────────────────────────────────────────────────────┘
```
