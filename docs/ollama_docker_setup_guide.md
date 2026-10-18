# Ollama Docker Setup Guide & 3-Tier Local Fleet Infrastructure

This Standard Operating Procedure (SOP) provides a complete, reproducible guide to deploying **Ollama** in Docker with full NVIDIA GPU acceleration. It establishes the 3-tier local AI fleet designed to power the **Hermes Copilot** ecosystem — providing automated model routing, fast daily coding, system architecture, and deep security analysis completely offline.

---

## 1. System Architecture & The 3-Tier Local Fleet

Rather than relying on a single generalist model or paying cloud API fees, this infrastructure provisions a specialized **3-tier local fleet** tailored specifically for an 8GB VRAM GPU (such as NVIDIA GeForce RTX 4060 / 5060) backed by 32GB DDR5 system RAM:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      LOCAL OLLAMA DOCKER FLEET                         │
│                    (Port 11434 • GPU-Accelerated)                      │
├────────────────────┬───────────┬─────────────┬─────────────────────────┤
│ Model              │ Footprint │ Speed       │ Primary Role            │
├────────────────────┼───────────┼─────────────┼─────────────────────────┤
│ qwen2.5:0.5b       │ 397 MB    │ ~180 tok/s  │ ⚡ Copilot Router / 50ms │
│ qwen2.5-coder:14b  │ 9.0 GB    │ ~25 tok/s   │ 💻 Coder & Architect    │
│ deepseek-r1:14b    │ 9.0 GB    │ ~20 tok/s   │ 🔒 Security & Logic     │
└────────────────────┴───────────┴─────────────┴─────────────────────────┘
```

### Fleet Roles & Capabilities
1. **`qwen2.5:0.5b` (Pocket Router & Intent Classifier):**
   * **Size:** 397 MB (~350 MB VRAM).
   * **Role:** Evaluates user task complexity and queries Ollama's active `/v1/models` catalog in **< 50ms**. Dispatches the optimal specialized model without swapping large weights out of GPU memory.
2. **`qwen2.5-coder:14b` (Primary Daily Driver & Systems Architect):**
   * **Size:** 9.0 GB (fits ~80% in 8GB VRAM, offloads remainder to DDR5).
   * **Role:** Handles 90% of software tasks: implementing features, clean architecture domain design, writing unit tests, debugging, and executing terminal agent tools with blazing fast 8-second response times.
3. **`deepseek-r1:14b` (Security, Math & Algorithmic Logic):**
   * **Size:** 9.0 GB.
   * **Role:** Distilled reasoning model for cryptographic analysis, race condition discovery, authentication audits, exploit modeling, and complex mathematical proofs with deep chain-of-thought (`<think>`) reasoning.

> [!NOTE]
> **What about `qwen2.5-coder:32b`?**
> The 32B model is 18.5 GB. On an 8GB VRAM card with 32GB host RAM (where Windows + apps already use ~22GB), running 32B exhausts physical memory and forces Windows into disk paging/swapping, causing Ollama to hang and timeout. The 32B model is strictly reserved for systems with $\ge 16\text{GB}$ VRAM or $\ge 64\text{GB}$ system RAM. For standard workstations, `14b` is the verified optimal performer.

---

## 2. Step 1: Host Directory Preparation

Model weights are substantial (totaling ~19 GB for the 3-tier fleet). To ensure models persist permanently across container rebuilds and system restarts, create a dedicated data folder on your fastest SSD drive:

```powershell
# Open Windows PowerShell
New-Item -ItemType Directory -Force -Path "D:\Data\Docker Data\Ollama"
```

---

## 3. Step 2: Provisioning the Ollama Container (Docker Run)

Run the official Ollama Docker container with GPU acceleration, memory persistence, and host port forwarding:

```powershell
docker run -d `
  --gpus=all `
  -e OLLAMA_KEEP_ALIVE="-1" `
  --name ollama-sandbox-pro `
  -p 11434:11434 `
  -v "D:\Data\Docker Data\Ollama:/root/.ollama" `
  ollama/ollama:latest
```

### Key Parameters Explained:
* `--gpus=all`: Exposes your host NVIDIA GPU (CUDA cores + Tensor cores) into the container via the NVIDIA Container Toolkit.
* `-e OLLAMA_KEEP_ALIVE="-1"`: Instructs Ollama to keep loaded models in memory indefinitely instead of unloading them after 5 minutes of inactivity. This eliminates annoying warm-up lag during active sessions.
* `-p 11434:11434`: Maps the default Ollama REST API to the host for both local access (`localhost:11434`) and inter-container networking.
* `-v "D:\Data\Docker Data\Ollama:/root/.ollama"`: Maps the model storage directory to your host disk so downloaded weights are never lost.

---

## 4. Step 3: Downloading the 3-Tier Fleet

Execute the following pull commands directly from your host PowerShell to download the verified local fleet:

```powershell
# 1. Pocket Router (Ultra-fast 50ms dispatcher)
docker exec -it ollama-sandbox-pro ollama pull qwen2.5:0.5b

# 2. Daily Driver & Architecture (Coding, clean design, unit tests & tool calls)
docker exec -it ollama-sandbox-pro ollama pull qwen2.5-coder:14b

# 3. Security & Logic (Vulnerability analysis, cryptography & deep reasoning)
docker exec -it ollama-sandbox-pro ollama pull deepseek-r1:14b

# (Optional: Only for systems with >= 16GB VRAM or >= 64GB System RAM)
# docker exec -it ollama-sandbox-pro ollama pull qwen2.5-coder:32b
```

### Verify Installed Models on Disk (`ollama list`):
```powershell
docker exec -it ollama-sandbox-pro ollama list
```

**Expected Output:**
```text
NAME                 ID              SIZE      MODIFIED
qwen2.5:0.5b         a8b0c5157701    397 MB    Just now
qwen2.5-coder:14b    4828733707be    9.0 GB    Just now
deepseek-r1:14b      c333b7232bdb    9.0 GB    Just now
```

### Check Active / Warm Models in Memory (`ollama ps`):
To see which models are currently loaded into GPU VRAM and System RAM ready for instant response:
```powershell
docker exec -it ollama-sandbox-pro ollama ps
```

**Example Output:**
```text
NAME                 ID              SIZE      PROCESSOR          CONTEXT    UNTIL               
qwen2.5-coder:14b    4828733707be    15 GB     62%/38% CPU/GPU    32768      25 minutes from now    
qwen2.5:0.5b         a8b0c5157701    481 MB    100% GPU           4096       11 minutes from now    
```

> [!NOTE]
> **`ollama list` vs. `ollama ps`:**
> * `ollama list`: Shows all models stored on disk (equivalent to `docker images`).
> * `ollama ps`: Shows models currently loaded into memory (equivalent to `docker ps`), displaying their VRAM/CPU distribution and keep-alive countdown.

---

## 5. Hardware Sizing & Performance Benchmark (RTX 5060 8GB + 32GB DDR5)

Evaluated on an ASUS TUF Gaming F16 (Intel Core i7-14650HX, NVIDIA RTX 5060 8GB Mobile, 32GB DDR5-5600 RAM):

| Model | Weights Size | GPU VRAM Allocated | System RAM Allocated | Inference Speed | First Token Latency |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`qwen2.5:0.5b`** | 397 MB | 100% (~0.4 GB) | 0 GB | **180+ tok/s** | < 50 ms |
| **`qwen2.5-coder:14b`** | 9.0 GB | ~75% (~6.2 GB) | ~3.8 GB | **22–28 tok/s** | 1–2 sec |
| **`deepseek-r1:14b`** | 9.0 GB | ~75% (~6.2 GB) | ~3.8 GB | **18–24 tok/s** | 2–3 sec |
| **`qwen2.5-coder:32b`** | 19.0 GB | ~35% (~6.5 GB) | ~14.5 GB | **7–9 tok/s** | 8–12 sec |

> [!TIP]
> **VRAM Management:** Ollama manages GPU memory dynamically. The `0.5B` router stays resident in memory almost cost-free (~350 MB VRAM). Switching between `qwen2.5-coder:14b` and `deepseek-r1:14b` is smooth, swap-free, and avoids Windows memory thrashing.

---

## 6. Model Comparison & Behavioral Differences

### `qwen2.5-coder:14b` vs. `deepseek-r1:14b`

| Dimension | `qwen2.5-coder:14b` (Daily Coding) | `deepseek-r1:14b` (Logic & Security) |
| :--- | :--- | :--- |
| **Primary Strength** | Structured code, diffs, bash tool calls | Deep multi-step reasoning, mathematical proofs |
| **Tool Calling Fidelity** | **Excellent** — Emits clean JSON/bash commands | **Requires parser** — Emits `<think>...</think>` tags |
| **Best Scenario** | Implementing PRs, writing unit tests, fixing bugs | Auditing auth flows, cryptographic proofs, race conditions |

---

## 7. Connecting Dockerized Clients (Hermes Agent & Claude Code)

Because Ollama runs in Docker, how other tools connect depends on where the client is running:

### 1. From the Windows Host (PowerShell, Curl, VS Code)
Connect directly to localhost:
```text
http://localhost:11434
```

### 2. From Another Docker Container (e.g. `hermes-sandbox-pro`)
Docker containers on the bridge network cannot use `localhost` (which points to themselves). Use either:
* **Host Gateway (Recommended & Most Reliable):**
  ```text
  http://172.17.0.1:11434
  ```
* **Docker DNS:**
  ```text
  http://host.docker.internal:11434
  ```

---

## 8. Verification & Health Checks

You can verify that Ollama is healthy and test model generation directly using `curl` from your host terminal (PowerShell, WSL, or Git Bash):

### 1. Model Discovery (OpenAI-Compatible `/v1/models` API)
*Used by Hermes Agent and the Hermes Copilot Auto-Proxy to dynamically discover installed models:*
```bash
curl --location 'http://localhost:11434/v1/models'
```

### 2. Native Ollama Tags Endpoint
```bash
curl --location 'http://localhost:11434/api/tags'
```

### 3. Test Pocket Router Generation (`qwen2.5:0.5b` - Sub-second latency)
```bash
curl --location 'http://localhost:11434/api/generate' \
  --header 'Content-Type: application/json' \
  --data '{
    "model": "qwen2.5:0.5b",
    "prompt": "Identify the capital of France in one word.",
    "stream": false
  }'
```

### 4. Test Coder & Architect Generation (`qwen2.5-coder:14b`)
```bash
curl --location 'http://localhost:11434/api/generate' \
  --header 'Content-Type: application/json' \
  --data '{
    "model": "qwen2.5-coder:14b",
    "prompt": "i need sample for using FluentValidation in .NET",
    "stream": false
  }'
```

---

## 9. Maintenance & Lifecycle

### Interactive Shell Access (Optional)
To open an interactive shell inside the Ollama container (e.g. to run `ollama` commands or test models directly):
```powershell
docker exec -it ollama-sandbox-pro bash
```
*(Once inside, you can run commands like `ollama list`, `ollama run qwen2.5:0.5b`, or inspect files directly without typing `docker exec` each time).*

### Resuming After Machine Reboot
When you reboot Windows, do **not** run `docker run` again. Simply restart the existing container:
```powershell
docker start ollama-sandbox-pro
```
All models remain intact in `D:\Data\Docker Data\Ollama`.

### Updating the Ollama Engine
To upgrade the Ollama runtime to the latest release without losing any downloaded models:
```powershell
# 1. Stop and remove existing container
docker stop ollama-sandbox-pro
docker rm ollama-sandbox-pro

# 2. Pull latest image
docker pull ollama/ollama:latest

# 3. Re-create container using identical command from Step 2
docker run -d --gpus=all -e OLLAMA_KEEP_ALIVE="-1" --name ollama-sandbox-pro -p 11434:11434 -v "D:\Data\Docker Data\Ollama:/root/.ollama" ollama/ollama:latest
```
All your models will be immediately recognized without re-downloading!
