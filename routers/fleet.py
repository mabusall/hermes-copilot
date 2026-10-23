"""
Fleet profiler: turns a router category into a concrete Ollama model tag
using ONLY what Ollama reports about each model (/api/show capabilities and
parameter size). No model names are hardcoded anywhere.

Selection rules:
  reasoning -> largest model with the 'thinking' capability
  coding    -> largest model with 'tools' and without 'thinking'
               (models with 'insert' / fill-in-the-middle win ties)
  general   -> smallest model without 'thinking' (fast answers)

If no model satisfies a rule, select() raises FleetError. The proxy turns that
into a loud error banner; there is no silent fallback.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import httpx


class FleetError(Exception):
    pass


@dataclass
class ModelProfile:
    name: str
    capabilities: List[str]
    family: str
    params_b: float          # parameter count in billions (0 if unknown)

    @property
    def thinking(self) -> bool:
        return "thinking" in self.capabilities

    @property
    def tools(self) -> bool:
        return "tools" in self.capabilities

    @property
    def insert(self) -> bool:
        return "insert" in self.capabilities


RULE_TEXT = {
    "reasoning": "a model with the 'thinking' capability",
    "coding": "a model with 'tools' and without 'thinking'",
    "general": "any model without 'thinking'",
}


def _parse_params(size: str) -> float:
    """'14.8B' -> 14.8, '500M' -> 0.5, '' -> 0."""
    m = re.match(r"([\d.]+)\s*([BbMm])", size or "")
    if not m:
        return 0.0
    value = float(m.group(1))
    return value if m.group(2).lower() == "b" else value / 1000.0


class Fleet:
    def __init__(self, ollama_base: str, exclude: Optional[List[str]] = None):
        self.ollama_base = ollama_base
        self.exclude = set(exclude or [])
        self._cache: Dict[str, ModelProfile] = {}

    async def profiles(self, client: httpx.AsyncClient) -> List[ModelProfile]:
        """Lists installed models; /api/show is only called for models not seen before."""
        r = await client.get(f"{self.ollama_base}/v1/models", timeout=5.0)
        r.raise_for_status()
        names = [m["id"] for m in r.json().get("data", []) if m["id"] not in self.exclude]

        result = []
        for name in names:
            if name not in self._cache:
                s = await client.post(f"{self.ollama_base}/api/show", json={"model": name}, timeout=10.0)
                s.raise_for_status()
                d = s.json()
                details = d.get("details", {}) or {}
                self._cache[name] = ModelProfile(
                    name=name,
                    capabilities=d.get("capabilities", []) or [],
                    family=details.get("family", ""),
                    params_b=_parse_params(details.get("parameter_size", "")),
                )
            result.append(self._cache[name])
        # forget models that were removed from Ollama
        for gone in set(self._cache) - set(names):
            del self._cache[gone]
        return result

    @staticmethod
    def select(category: str, profiles: List[ModelProfile]) -> ModelProfile:
        if category == "reasoning":
            pool = [p for p in profiles if p.thinking]
            key = lambda p: p.params_b
            best = max(pool, key=key) if pool else None
        elif category == "coding":
            pool = [p for p in profiles if p.tools and not p.thinking]
            best = max(pool, key=lambda p: (p.params_b, p.insert)) if pool else None
        elif category == "general":
            pool = [p for p in profiles if not p.thinking]
            best = min(pool, key=lambda p: p.params_b) if pool else None
        else:
            raise FleetError(f"Router returned unknown category '{category}'")

        if best is None:
            fleet = ", ".join(f"{p.name} {p.capabilities}" for p in profiles) or "EMPTY"
            raise FleetError(
                f"No installed model qualifies for category '{category}' "
                f"(needs {RULE_TEXT[category]}). Installed fleet: {fleet}"
            )
        return best
