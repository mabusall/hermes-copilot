#!/usr/bin/env bash
# Hermes Copilot — One-Command Router Switcher & Manager
# Usage:
#   bash scripts/switch_router.sh semantic   # Switch to Semantic Router (FastEmbed ONNX, ~5.6ms, ~340MB RAM)
#   bash scripts/switch_router.sh laya       # Switch to Laya (Convai ModernBERT, ~241ms, ~2GB RAM)
#   bash scripts/switch_router.sh routellm   # Switch to RouteLLM (LMSYS BERT, ~14.8ms, ~1.2GB RAM)
#   bash scripts/switch_router.sh status     # Check active router & proxy health
#   bash scripts/switch_router.sh stop       # Stop the proxy daemon

set -e

ROUTER="${1:-}"
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_BASE="/opt/router-venvs"
LOG_FILE="/workspace/proxy.log"

print_usage() {
    echo "==================================================================="
    echo "🧭 Hermes Copilot — Router Switcher"
    echo "==================================================================="
    echo "Usage: bash scripts/switch_router.sh <router_name|action>"
    echo ""
    echo "Available Routers:"
    echo "  semantic  - Aurelio FastEmbed ONNX (Recommended: ~5.6ms, ~340MB RAM)"
    echo "  laya      - Convai ModernBERT Choice (92.5% 3-Class, ~241ms, ~2GB RAM)"
    echo "  routellm  - LMSYS Arena BERT Classifier (~14.8ms, ~1.2GB RAM)"
    echo ""
    echo "Actions:"
    echo "  status    - Check running proxy status and Ollama connection"
    echo "  stop      - Stop running proxy daemon"
    echo "==================================================================="
}

check_status() {
    echo "🔍 Checking Hermes Copilot Auto-Proxy status..."
    if pgrep -f "hermes_proxy" > /dev/null; then
        PID=$(pgrep -f "hermes_proxy" | head -n 1)
        echo "✅ Auto-Proxy is RUNNING (PID: $PID)"
        echo ""
        echo "Testing http://127.0.0.1:8000/v1/models:"
        curl -s http://127.0.0.1:8000/v1/models | grep -o '"id":"[^"]*"' || echo "⚠️  Proxy not responding to HTTP yet"
    else
        echo "❌ Auto-Proxy is NOT running."
    fi
}

stop_proxy() {
    echo "🛑 Stopping any running Auto-Proxy daemons..."
    pkill -f "hermes_proxy" || true
    sleep 1
    echo "✅ Stopped."
}

if [ -z "$ROUTER" ]; then
    print_usage
    exit 1
fi

if [ "$ROUTER" = "status" ]; then
    check_status
    exit 0
fi

if [ "$ROUTER" = "stop" ]; then
    stop_proxy
    exit 0
fi

if [[ "$ROUTER" != "semantic" && "$ROUTER" != "laya" && "$ROUTER" != "routellm" ]]; then
    echo "❌ Unknown router '$ROUTER'."
    print_usage
    exit 1
fi

SOURCE_FILE="${WORKSPACE_DIR}/copilot/hermes_proxy_${ROUTER}.py"
TARGET_FILE="${WORKSPACE_DIR}/hermes_proxy.py"
VENV_DIR="${VENV_BASE}/${ROUTER}"
REQ_FILE="${WORKSPACE_DIR}/requirements/${ROUTER}.txt"

if [ ! -f "$SOURCE_FILE" ]; then
    echo "❌ Source proxy file not found: $SOURCE_FILE"
    exit 1
fi

echo "==================================================================="
echo "🚀 Switching Hermes Copilot to: ${ROUTER^^}"
echo "==================================================================="

# 1. Ensure isolated virtual environment exists
if [ ! -f "${VENV_DIR}/bin/python" ]; then
    echo "📦 Creating isolated virtual environment at ${VENV_DIR}..."
    mkdir -p "${VENV_BASE}"
    UV_BIN="/root/.hermes/bin/uv"
    SYS_PY="/usr/local/lib/hermes-agent/venv/bin/python"
    
    if [ -f "$UV_BIN" ] && [ -f "$SYS_PY" ]; then
        "$UV_BIN" venv "$VENV_DIR" --python "$SYS_PY"
        if [ "$ROUTER" = "laya" ] || [ "$ROUTER" = "routellm" ]; then
            echo "⚡ Pre-installing lightweight CPU-only PyTorch (187MB, avoids CUDA bloat)..."
            "$UV_BIN" pip install --python "${VENV_DIR}/bin/python" --index-url https://download.pytorch.org/whl/cpu torch
        fi
        echo "📥 Installing dependencies from ${REQ_FILE}..."
        "$UV_BIN" pip install --python "${VENV_DIR}/bin/python" --extra-index-url https://download.pytorch.org/whl/cpu -r "$REQ_FILE"
    else
        python3 -m venv "$VENV_DIR"
        "${VENV_DIR}/bin/pip" install --upgrade pip
        if [ "$ROUTER" = "laya" ] || [ "$ROUTER" = "routellm" ]; then
            echo "⚡ Pre-installing lightweight CPU-only PyTorch..."
            "${VENV_DIR}/bin/pip" install --index-url https://download.pytorch.org/whl/cpu torch
        fi
        echo "📥 Installing dependencies from ${REQ_FILE}..."
        "${VENV_DIR}/bin/pip" install -r "$REQ_FILE"
    fi
    echo "✅ Environment ready."
fi

# 2. Stop running proxy
stop_proxy

# 3. Copy chosen router edition to root `hermes_proxy.py`
echo "📋 Updating ${TARGET_FILE} with ${ROUTER} edition..."
cp -f "$SOURCE_FILE" "$TARGET_FILE"

# 4. Start the new proxy in the background
echo "🔥 Starting Auto-Proxy with ${ROUTER} backend on port 8000..."
nohup "${VENV_DIR}/bin/python" "$TARGET_FILE" > "$LOG_FILE" 2>&1 &

sleep 2

# 5. Health verification
if pgrep -f "hermes_proxy" > /dev/null; then
    PID=$(pgrep -f "hermes_proxy" | head -n 1)
    echo "✅ Success! Hermes Copilot Auto-Proxy is live (PID: $PID)"
    echo "📡 Endpoint: http://127.0.0.1:8000/v1"
    echo "📜 Live log: $LOG_FILE"
    echo ""
    echo "Chat indicator badge will show:"
    case "$ROUTER" in
        semantic) echo "> 🧭 [Auto Router • Semantic] Using model..." ;;
        laya)     echo "> 🧭 [Auto Router • Laya] Using model..." ;;
        routellm) echo "> 🧭 [Auto Router • RouteLLM] Using model..." ;;
    esac
else
    echo "❌ Proxy failed to start. Last log output:"
    tail -n 20 "$LOG_FILE"
    exit 1
fi
