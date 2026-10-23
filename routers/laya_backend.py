"""
Laya backend: Convai Innovations' 421M ModernBERT non-autoregressive System 1 decision engine
(convaiinnovations/laya, formerly Jev).
Classifies prompts into coding, reasoning, or general in a single CPU forward pass with
temperature-calibrated probabilities.
"""

import os
import time
import warnings
from typing import Any, Dict, List

from .base import Decision

MODEL_ID = os.getenv("LAYA_MODEL", "convaiinnovations/laya")

QUESTIONS: Dict[str, Dict[str, Any]] = {
    "category": {
        "type": "choice",
        "instructions": "Which task category does `request` belong to?",
        "criteria": {
            "coding": (
                "writing, implementing, refactoring, or fixing code, functions, classes, "
                "bash scripts, SQL queries, Dockerfiles, regex, or unit tests"
            ),
            "reasoning": (
                "auditing or analyzing code/protocols for security vulnerabilities (timing attacks, "
                "JWT, reentrancy, MITM, PRNG), concurrency and memory-model proofs (thread-safety, "
                "double-checked locking, ABA), mathematical proofs, logic puzzles, or complexity proofs"
            ),
            "general": (
                "casual conversation, greetings, general knowledge, summarization, "
                "translation, creative writing, email drafting, or simple factual definitions"
            ),
        },
    }
}


class LayaBackend:
    name = "laya"
    categories: List[str] = ["coding", "reasoning", "general"]
    label_map: Dict[str, str] = {}

    def __init__(self, model_id: str = MODEL_ID, questions: Dict[str, Dict[str, Any]] = QUESTIONS):
        self.model_id = model_id
        self.questions = questions
        self.agent = None

    def load(self) -> None:
        """Loads Laya's ModernBERT System 1 decision model onto CPU."""
        import laya

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            self.agent = laya.load(self.model_id, device="cpu")
        # Warm up a single pass (also caches question token encodings)
        self.agent.predict({"request": "warmup"}, self.questions)

    def classify(self, prompt: str) -> Decision:
        t0 = time.perf_counter()
        res = self.agent.predict({"request": prompt}, self.questions)
        latency = (time.perf_counter() - t0) * 1000

        answers = res.get("answers", {}) if isinstance(res, dict) else {}
        cat_res = answers.get("category", {})
        category = cat_res.get("choice", "coding")
        confidence = cat_res.get("answer_confidence") or cat_res.get("confidence")

        if category not in self.categories:
            category = "coding"
        if confidence is not None:
            confidence = float(confidence)

        return Decision(
            category=category,
            confidence=confidence,
            latency_ms=latency,
            raw={
                "choice": category,
                "confidence": confidence,
                "probabilities": cat_res.get("probabilities"),
            },
        )
