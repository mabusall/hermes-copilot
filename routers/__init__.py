"""
Router backend factory. Backends are imported lazily so each one only needs
its own dependencies installed (each lives in its own venv).
"""

from .base import CATEGORIES, Decision, RouterBackend, extract_routing_intent

BACKENDS = ("semantic", "routellm", "laya")


def get_backend(name: str) -> RouterBackend:
    if name == "semantic":
        from .semantic import SemanticBackend
        return SemanticBackend()
    if name == "routellm":
        from .routellm_backend import RouteLLMBackend
        return RouteLLMBackend()
    if name == "laya":
        from .laya_backend import LayaBackend
        return LayaBackend()
    raise ValueError(f"Unknown ROUTER_BACKEND '{name}'. Valid options: {', '.join(BACKENDS)}")


__all__ = ["CATEGORIES", "Decision", "RouterBackend", "extract_routing_intent", "get_backend", "BACKENDS"]
