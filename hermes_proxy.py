#!/usr/bin/env python3
"""
Hermes Copilot Auto-Proxy
OpenAI-compatible reverse proxy providing GitHub Copilot "Auto" mode for local LLMs.
Intercepts requests with model: "auto", classifies intent via qwen2.5:0.5b in ~50ms,
and forwards to the optimal specialized model in Ollama with zero GPU thrashing.
"""

import os
import sys
import json
import time
import httpx
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://172.17.0.1:11434")
ROUTER_MODEL = "qwen2.5:0.5b"
PROXY_HOST = "0.0.0.0"
PROXY_PORT = 8000

app = FastAPI(title="Hermes Copilot Auto-Proxy")

# State to avoid VRAM thrashing during tool execution
current_pinned_model: str = "qwen2.5-coder:14b"


async def get_available_models(client: httpx.AsyncClient) -> List[str]:
    """Dynamically queries Ollama for active models."""
    try:
        r = await client.get(f"{OLLAMA_BASE}/v1/models", timeout=3.0)
        if r.status_code == 200:
            data = r.json()
            models = [m["id"] for m in data.get("data", [])]
            return [m for m in models if not m.startswith("qwen2.5:0.5b")]
    except Exception:
        pass
    return ["qwen2.5-coder:14b", "qwen2.5-coder:32b", "deepseek-r1:14b"]


async def classify_prompt(prompt: str, available_models: List[str], client: httpx.AsyncClient) -> Dict[str, str]:
    """Uses qwen2.5:0.5b to classify task intent in ~50ms."""
    p_lower = prompt.lower()

    # Rule-based fast paths for zero-latency classification
    if any(k in p_lower for k in ["security", "vulnerability", "race condition", "timing attack", "exploit", "handshake"]):
        if any("deepseek" in m or "r1" in m for m in available_models):
            return {
                "model": next(m for m in available_models if "deepseek" in m or "r1" in m),
                "category": "Security & Logic",
                "reason": "Security vulnerability and race-condition analysis"
            }

    if any(k in p_lower for k in ["enterprise architecture", "system design", "clean architecture", "domain-driven", "cqrs", "class hierarchy"]):
        return {
            "model": "qwen2.5-coder:14b",
            "category": "Architecture & Systems Design",
            "reason": "High-level software system design and enterprise patterns (optimized for 8GB GPU)"
        }

    # Ask the pocket router (qwen2.5:0.5b) for nuanced classification
    payload = {
        "model": ROUTER_MODEL,
        "prompt": f"""Classify task and select best model from: {json.dumps(available_models)}
Guidelines:
- Security, math, cryptographic logic -> deepseek-r1:14b
- Architecture, system design, enterprise patterns -> qwen2.5-coder:32b
- Routine coding, functions, unit tests, scripts -> qwen2.5-coder:14b

Task: "{prompt}"
JSON output (keys: selected_model, category, reason):""",
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 100}
    }

    try:
        r = await client.post(f"{OLLAMA_BASE}/api/generate", json=payload, timeout=5.0)
        if r.status_code == 200:
            res = json.loads(r.json().get("response", "{}"))
            selected = res.get("selected_model", "")
            if selected in available_models:
                return {
                    "model": selected,
                    "category": res.get("category", "General"),
                    "reason": res.get("reason", "Optimal task fit")
                }
    except Exception:
        pass

    # Safe default: Primary Daily Driver
    return {
        "model": "qwen2.5-coder:14b",
        "category": "Routine Software Engineering",
        "reason": "Default high-speed daily coding driver"
    }


@app.get("/v1/models")
async def list_models():
    """Returns Ollama models with 'auto' added as the default option."""
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{OLLAMA_BASE}/v1/models", timeout=3.0)
            data = r.json() if r.status_code == 200 else {"data": []}
        except Exception:
            data = {"data": []}

    auto_entry = {
        "id": "auto",
        "object": "model",
        "created": int(time.time()),
        "owned_by": "hermes-copilot",
        "permission": [],
        "root": "auto",
        "parent": None
    }
    data["data"] = [auto_entry] + [m for m in data.get("data", []) if m["id"] != "auto"]
    return JSONResponse(content=data)


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    global current_pinned_model
    body = await request.json()
    model = body.get("model", "auto")
    messages = body.get("messages", [])
    stream = body.get("stream", False)

    # If the user selected a specific model manually, respect it directly
    if model != "auto":
        target_model = model
    else:
        # Check if this is an intermediate tool-turn (preserve current model to avoid VRAM thrashing)
        last_message = messages[-1] if messages else {}
        is_tool_continuation = last_message.get("role") in ("tool", "assistant")

        if is_tool_continuation and current_pinned_model:
            target_model = current_pinned_model
        else:
            # Extract latest user message
            user_texts = []
            for m in messages:
                if m.get("role") == "user":
                    content = m.get("content", "")
                    if isinstance(content, list):
                        text = " ".join([c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"])
                        user_texts.append(text)
                    elif isinstance(content, str):
                        user_texts.append(content)
            latest_prompt = user_texts[-1] if user_texts else ""

            async with httpx.AsyncClient() as client:
                available = await get_available_models(client)
                start_t = time.time()
                decision = await classify_prompt(str(latest_prompt), available, client)
                elapsed_ms = int((time.time() - start_t) * 1000)

            target_model = decision["model"]
            current_pinned_model = target_model

            log_banner = (
                f"┌─────────────────────────────────────────────────────────────────┐\n"
                f"│ 🤖 Hermes Copilot Auto-Proxy                                    │\n"
                f"│ 🎯 Task Category  : {decision.get('category')}\n"
                f"│ 🧠 Dispatched Brain: {target_model}\n"
                f"│ ⏱️  Routing Latency : {elapsed_ms}ms\n"
                f"└─────────────────────────────────────────────────────────────────┘\n"
            )
            print(log_banner, flush=True)
            try:
                with open("/workspace/proxy.log", "a", encoding="utf-8") as f:
                    f.write(log_banner + "\n")
            except Exception:
                pass

    # Rewrite model name to the selected real Ollama model
    body["model"] = target_model

    client = httpx.AsyncClient(timeout=httpx.Timeout(connect=15.0, read=None, write=30.0, pool=30.0))

    if stream:
        req = client.build_request("POST", f"{OLLAMA_BASE}/v1/chat/completions", json=body)
        resp = await client.send(req, stream=True)

        async def stream_generator():
            try:
                async for chunk in resp.aiter_bytes():
                    yield chunk
            finally:
                await resp.aclose()
                await client.aclose()

        return StreamingResponse(stream_generator(), media_type="text/event-stream")
    else:
        resp = await client.post(f"{OLLAMA_BASE}/v1/chat/completions", json=body)
        await client.aclose()
        return JSONResponse(content=resp.json(), status_code=resp.status_code)


if __name__ == "__main__":
    print(f"🚀 Starting Hermes Copilot Auto-Proxy on http://{PROXY_HOST}:{PROXY_PORT}", flush=True)
    print(f"🔗 Forwarding target: {OLLAMA_BASE}", flush=True)
    uvicorn.run(app, host=PROXY_HOST, port=PROXY_PORT, log_level="warning")
