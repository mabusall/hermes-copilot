"""
Shared types for Hermes Copilot router backends.

A router backend only answers ONE question: "what kind of task is this?"
It returns a category (coding / reasoning / general). Turning that category
into a concrete Ollama model tag is the job of routers/fleet.py, so no
backend ever needs to know model names.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Protocol

CATEGORIES: List[str] = ["coding", "reasoning", "general"]


@dataclass
class Decision:
    category: str                       # one of CATEGORIES
    confidence: Optional[float]         # 0..1, or None if the backend has no confidence signal
    latency_ms: float                   # time spent inside classify()
    raw: Dict[str, Any] = field(default_factory=dict)  # backend-specific details for logs


class RouterBackend(Protocol):
    name: str
    categories: List[str]               # categories this backend can emit
    label_map: Dict[str, str]           # how benchmark labels map onto this backend's categories

    def load(self) -> None:
        """One-time initialisation (download/load weights, warm up)."""
        ...

    def classify(self, prompt: str) -> Decision:
        """Classify an (already truncated) prompt. Must be safe to call from a worker thread."""
        ...


def extract_routing_intent(prompt: str, max_chars: int = 1200) -> str:
    """Extracts head and tail of large prompts for fast intent classification."""
    prompt = prompt.strip()
    if len(prompt) <= max_chars:
        return prompt
    head = prompt[:600]
    tail = prompt[-600:]
    return f"{head}\n...[content omitted for intent classification]...\n{tail}"
