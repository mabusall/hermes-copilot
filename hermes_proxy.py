#!/usr/bin/env python3
"""
Hermes Copilot Auto-Proxy (Universal Autonomous Orchestrator)
OpenAI-compatible reverse proxy providing GitHub Copilot "Auto" mode for local LLMs.

Routing is done by a pluggable System 1 backend that runs IN THIS PROCESS on CPU
(ROUTER_BACKEND = semantic | routellm | laya | ollama-llm). The backend returns a task
category; routers/fleet.py maps it to an installed Ollama model using the capabilities
Ollama reports. Ollama itself only ever runs the worker model.
No hardcoded model names. No silent fallbacks. 100% dynamic.
"""

import os
import json
import time
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn

from routers import get_backend, extract_routing_intent
from routers.fleet import Fleet, FleetError

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://172.17.0.1:11434")
PROXY_HOST = "0.0.0.0"
PROXY_PORT = 8000
ROUTER_BACKEND = os.getenv("ROUTER_BACKEND", "semantic")
LOG_FILE = os.getenv("PROXY_LOG_FILE", "/workspace/proxy.log")
DEBUG_ROLES = os.getenv("PROXY_DEBUG_ROLES", "1") == "1"        # log message structure (no content) per request

backend = get_backend(ROUTER_BACKEND)
fleet = Fleet(OLLAMA_BASE)

backend_load_task: Optional[asyncio.Task] = None
backend_load_error: Optional[str] = None

# Turn state: avoids re-routing (and model swaps) inside one tool loop
current_pinned_model: Optional[str] = None
last_evaluated_prompt: Optional[str] = None


def log(text: str) -> None:
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    output = f"\n{timestamp}\n{text}" if text.startswith("┌") else f"{timestamp} {text}"
    print(output, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(output + "\n")
    except Exception:
        pass


def banner(lines: List[str]) -> str:
    bar = "─" * 65
    return "\n".join([f"┌{bar}┐"] + [f"│ {line}" for line in lines] + [f"└{bar}┘"]) + "\n"


async def _load_backend() -> None:
    global backend_load_error
    t0 = time.perf_counter()
    log(f"🔥 Loading router backend '{backend.name}' (CPU, in-process)...")
    try:
        await asyncio.to_thread(backend.load)
        log(f"✅ Router backend '{backend.name}' ready in {time.perf_counter() - t0:.1f}s")
    except Exception as e:
        backend_load_error = f"{type(e).__name__}: {e}"
        log(f"❌ Router backend '{backend.name}' failed to load: {backend_load_error}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Loads the router backend in the background; requests wait for it instead of failing."""
    global backend_load_task
    backend_load_task = asyncio.create_task(_load_backend())
    yield


app = FastAPI(title="Hermes Copilot Universal Autonomous Proxy", lifespan=lifespan)


def make_error_stream(err_msg: str):
    """Creates a clean OpenAI-compatible SSE error stream for the Hermes UI."""
    async def err_stream():
        chunk = {
            "id": f"chatcmpl-err-{int(time.time())}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "auto",
            "choices": [{
                "index": 0,
                "delta": {"role": "assistant", "content": err_msg},
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(err_stream(), media_type="text/event-stream")


def error_response(title: str, details: List[str], stream: bool, status: int, err_type: str):
    log(banner([f"❌ Hermes Copilot Error: {title}"] + details))
    msg = f"❌ **Hermes Copilot Error: {title}**\n\n" + "\n\n".join(details)
    if stream:
        return make_error_stream(msg)
    return JSONResponse(status_code=status, content={"error": {"message": msg, "type": err_type}})


def _text_of(content: Any) -> str:
    if isinstance(content, list):
        return " ".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text")
    return content if isinstance(content, str) else ""


def _structure(messages: List[Dict[str, Any]]) -> str:
    """Role sequence + extra keys, no content. Used to verify how Hermes formats tool turns."""
    parts = []
    for m in messages[-6:]:
        extra = [k for k in m.keys() if k not in ("role", "content")]
        parts.append(m.get("role", "?") + (f"{extra}" if extra else ""))
    return f"{len(messages)} msgs, last 6: " + " → ".join(parts)


@app.get("/v1/models")
async def list_models():
    """Returns Ollama models with 'auto' dynamically prepended as the default choice."""
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
    global current_pinned_model, last_evaluated_prompt
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": {"message": "Invalid JSON payload", "type": "invalid_request_error"}})

    model = body.get("model", "auto")
    messages = body.get("messages", []) or []
    stream = body.get("stream", False)
    chat_badge: Optional[str] = None

    # If the user selected a specific model manually via /model, respect it directly
    if model != "auto":
        target_model = model
    else:
        user_texts = [_text_of(m.get("content")) for m in messages if m.get("role") == "user"]
        latest_prompt = user_texts[-1] if user_texts else ""
        last_role = messages[-1].get("role") if messages else None

        if DEBUG_ROLES:
            log(f"🔎 Request: {_structure(messages)} | latest user: {latest_prompt[:60]!r}")

        # Only the LAST message decides whether this is a tool-loop continuation.
        # (The previous version scanned the whole history, which pinned every later prompt.)
        is_tool_continuation = last_role == "tool"
        is_same_prompt = bool(latest_prompt) and latest_prompt == last_evaluated_prompt

        if (is_tool_continuation or is_same_prompt) and current_pinned_model:
            target_model = current_pinned_model
            reason = "tool result" if is_tool_continuation else "same user prompt"
            log(f"🔄 Reusing '{target_model}' ({reason}, no re-routing)")
        else:
            # Wait for the backend if it is still loading
            if backend_load_task and not backend_load_task.done():
                await backend_load_task
            if backend_load_error:
                return error_response(
                    "Router Backend Failed to Load",
                    [f"Backend: `{backend.name}`", f"Reason: {backend_load_error}"],
                    stream, 500, "router_load_error")

            try:
                async with httpx.AsyncClient() as client:
                    profiles = await fleet.profiles(client)
            except Exception as e:
                return error_response(
                    "Cannot Read Ollama Fleet",
                    [f"Ollama: `{OLLAMA_BASE}`", f"Reason: {type(e).__name__}: {e}"],
                    stream, 502, "ollama_unreachable")
            if not profiles:
                return error_response(
                    "No Execution Models Available",
                    ["Ollama has no models to execute your task. Pull at least one model (e.g. qwen2.5-coder, deepseek-r1, llama)."],
                    stream, 404, "no_models_available")

            intent = extract_routing_intent(latest_prompt)
            try:
                decision = await asyncio.to_thread(backend.classify, intent)
            except Exception as e:
                return error_response(
                    "Routing Failed",
                    [f"Backend: `{backend.name}`", f"Reason: {type(e).__name__}: {e}"],
                    stream, 500, "routing_error")

            try:
                chosen = Fleet.select(decision.category, profiles)
            except FleetError as e:
                return error_response("No Suitable Model", [str(e)], stream, 404, "no_suitable_model")

            target_model = chosen.name
            current_pinned_model = target_model
            last_evaluated_prompt = latest_prompt

            conf = f"{decision.confidence:.2f}" if decision.confidence is not None else "n/a"
            chat_badge = f"> 🧭 **[Auto Router]** Using **`{target_model}`** *(Task: `{decision.category}` • {decision.latency_ms:.1f}ms)*\n\n"
            log(banner([
                "🤖 Hermes Copilot Autonomous Orchestrator",
                f"🧭 Router Backend   : {backend.name} (CPU, in-process)",
                f"📦 Execution Fleet  : {[p.name for p in profiles]}",
                f"🏷️  Task Category    : {decision.category} (confidence {conf})",
                f"🚀 Dispatched Model : {target_model} {chosen.capabilities} {chosen.params_b}B",
                f"⏱️  Routing Latency  : {decision.latency_ms:.1f}ms",
            ]))

    # Rewrite model name to the selected real Ollama model
    body["model"] = target_model

    client = httpx.AsyncClient(timeout=httpx.Timeout(connect=15.0, read=None, write=30.0, pool=30.0))

    if stream:
        req = client.build_request("POST", f"{OLLAMA_BASE}/v1/chat/completions", json=body)
        resp = await client.send(req, stream=True)

        async def stream_generator():
            try:
                if chat_badge:
                    badge_chunk = {
                        "id": f"chatcmpl-badge-{int(time.time()*1000)}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": target_model,
                        "choices": [{
                            "index": 0,
                            "delta": {"role": "assistant", "content": chat_badge},
                            "finish_reason": None,
                        }],
                    }
                    yield f"data: {json.dumps(badge_chunk)}\n\n".encode("utf-8")
                async for chunk in resp.aiter_bytes():
                    yield chunk
            finally:
                await resp.aclose()
                await client.aclose()

        return StreamingResponse(stream_generator(), media_type="text/event-stream")
    else:
        resp = await client.post(f"{OLLAMA_BASE}/v1/chat/completions", json=body)
        await client.aclose()
        resp_data = resp.json()
        if chat_badge and "choices" in resp_data and resp_data["choices"]:
            msg = resp_data["choices"][0].get("message", {})
            if "content" in msg and msg["content"] is not None:
                msg["content"] = chat_badge + msg["content"]
        return JSONResponse(content=resp_data, status_code=resp.status_code)


if __name__ == "__main__":
    print(f"🚀 Starting Hermes Copilot Auto-Proxy on http://{PROXY_HOST}:{PROXY_PORT}", flush=True)
    print(f"🔗 Forwarding target: {OLLAMA_BASE} | Router backend: {ROUTER_BACKEND}", flush=True)
    uvicorn.run(app, host=PROXY_HOST, port=PROXY_PORT, log_level="warning")
