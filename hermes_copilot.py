import sys
import json
import urllib.request
import subprocess

def get_ollama_base():
    """Finds the reachable Ollama endpoint without IPv6 routing issues."""
    candidates = [
        "http://172.17.0.1:11434",
        "http://host.docker.internal:11434",
        "http://127.0.0.1:11434"
    ]
    for url in candidates:
        try:
            req = urllib.request.Request(f"{url}/v1/models")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    return url
        except Exception:
            continue
    return "http://172.17.0.1:11434"

OLLAMA_BASE = get_ollama_base()
ROUTER_MODEL = "qwen2.5:0.5b"

def get_installed_models():
    """Dynamically queries Ollama for all currently pulled models."""
    try:
        url = f"{OLLAMA_BASE}/v1/models"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m["id"] for m in data.get("data", [])]
            # Exclude the router itself
            return [m for m in models if not m.startswith("qwen2.5:0.5b")]
    except Exception as e:
        # Fallback list if Ollama API call fails
        return ["qwen2.5-coder:14b", "qwen2.5-coder:32b", "deepseek-r1:14b"]

def classify_and_route(prompt, available_models):
    guidelines = []
    for m in available_models:
        m_lower = m.lower()
        if "deepseek" in m_lower or "r1" in m_lower:
            guidelines.append(f"- {m} -> Best for security vulnerabilities, race conditions, authentication logic, math proofs, reasoning.")
        elif "32b" in m_lower or "70b" in m_lower:
            guidelines.append(f"- {m} -> Best for system architecture, enterprise design patterns, class structures, refactoring.")
        else:
            guidelines.append(f"- {m} -> Best for writing code, unit tests, bug fixes, scripts, routine development.")

    guidelines_text = "\n".join(guidelines)

    system_prompt = f"""You are a precise Model Dispatcher. Select the BEST model name from the candidate list for the user task.

Candidate Models:
{json.dumps(available_models)}

Guidelines:
{guidelines_text}

Rules:
- Tasks for security, vulnerability, authentication, or race conditions MUST be Category: "Security & Logic".
- Tasks for system architecture, enterprise structure, or design patterns MUST be Category: "Architecture".
- Tasks for unit testing, writing code, bug fixes, or scripts MUST be Category: "Routine Coding".

Example 1:
Task: "Audit this token handshake for timing attacks and race conditions"
{{"selected_model": "deepseek-r1:14b", "category": "Security & Logic", "reason": "Requires security vulnerability and logic analysis."}}

Example 2:
Task: "Design clean architecture domain entities and repository interfaces"
{{"selected_model": "qwen2.5-coder:32b", "category": "Architecture", "reason": "Requires high-level software system design."}}

Example 3:
Task: "Write a unit test for email validation function using xUnit"
{{"selected_model": "qwen2.5-coder:14b", "category": "Routine Coding", "reason": "Standard code implementation and testing."}}

Now classify:
Task: "{prompt}"
JSON Output:"""

    payload = json.dumps({
        "model": ROUTER_MODEL,
        "prompt": f"{system_prompt}\nJSON Output:",
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 120
        }
    }).encode("utf-8")

    try:
        req = urllib.request.Request(f"{OLLAMA_BASE}/api/generate", data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode("utf-8")).get("response", "{}")
            decision = json.loads(raw)
            cat = decision.get("category", "").lower()
            selected = decision.get("selected_model", "")
            p_lower = prompt.lower()

            # Priority 1: Security & Logic (DeepSeek-R1)
            if ("security" in cat or "audit" in cat or "race condition" in p_lower or "vulnerability" in p_lower or "token" in p_lower) and any("deepseek" in m or "r1" in m for m in available_models):
                selected = next(m for m in available_models if "deepseek" in m or "r1" in m)
                decision["category"] = "Security & Logic"
            # Priority 2: Routine Coding (14B) - unit tests, functions, scripts
            elif ("test" in p_lower or "script" in p_lower or "fix" in p_lower or "implement" in p_lower or "function" in p_lower) and not ("architect" in p_lower or "system design" in p_lower):
                selected = next((m for m in available_models if "14b" in m or "7b" in m), selected)
                decision["category"] = "Routine Software Engineering"
            # Priority 3: Architecture & System Design (32B)
            elif ("architect" in cat or "design" in cat or "architect" in p_lower or "system" in p_lower) and any("32b" in m or "70b" in m for m in available_models):
                selected = next(m for m in available_models if "32b" in m or "70b" in m)
                decision["category"] = "Architecture"

            if selected in available_models:
                decision["selected_model"] = selected
                return decision
    except Exception:
        pass

    # Safe default fallback
    return {
        "selected_model": "qwen2.5-coder:14b",
        "category": "Routine Software Engineering",
        "reason": "Defaulting to high-speed daily coding model"
    }

def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: hermes-copilot 'Your task or question'")
        print("   or: h 'Your task or question'")
        print("   or: python3 hermes_copilot.py --recommend 'Your task'")
        sys.exit(1)

    recommend_only = False
    if "--recommend" in args:
        recommend_only = True
        args = [a for a in args if a != "--recommend"]

    user_prompt = " ".join(args)
    
    # 1. Dynamic Model Discovery
    models = get_installed_models()
    
    # 2. 50ms Intent Classification
    decision = classify_and_route(user_prompt, models)

    if recommend_only:
        print(json.dumps(decision))
        sys.exit(0)

    chosen_model = decision["selected_model"]
    category = decision.get("category", "General")
    reason = decision.get("reason", "Optimal task fit")

    # 3. Print Clean Copilot Banner
    print("┌─────────────────────────────────────────────────────────────────┐")
    print(f"│ 🤖 Hermes Copilot (Auto-Mode)")
    print(f"│ 🎯 Task Category  : {category}")
    print(f"│ 🧠 Dispatched Brain: {chosen_model}")
    print(f"│ 💡 Rationale       : {reason}")
    print("└─────────────────────────────────────────────────────────────────┘\n")

    # 4. Launch Hermes seamlessly with the chosen model
    cmd = [
        "hermes", "chat",
        "-m", chosen_model,
        "-q", user_prompt
    ]
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
