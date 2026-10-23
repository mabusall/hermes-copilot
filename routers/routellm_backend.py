"""
RouteLLM backend: LMSYS BERT classifier router running 100% offline on CPU.
Evaluates prompt difficulty/complexity and predicts the strong-model win rate:
  - win_rate >= threshold -> "reasoning" (dispatches to deepseek-r1:14b)
  - win_rate <  threshold -> "coding"    (dispatches to qwen2.5-coder:14b)
"""

import os
import time
from typing import Dict, List

from .base import Decision

# RouteLLM's routers.py imports similarity_weighted/utils.py at module load time,
# which instantiates OpenAI() even when only BERTRouter (local HuggingFace BERT) is used.
os.environ.setdefault("OPENAI_API_KEY", "local-bert-router-no-openai-needed")

CHECKPOINT = os.getenv("ROUTELLM_CHECKPOINT", "routellm/bert_gpt4_augmented")
THRESHOLD = float(os.getenv("ROUTELLM_THRESHOLD", "0.5"))


class RouteLLMBackend:
    name = "routellm"
    categories: List[str] = ["coding", "reasoning"]
    # RouteLLM is a binary strong/weak router; in our 2-model fleet both 'coding' and
    # 'general' map to the fast non-thinking worker (qwen2.5-coder:14b).
    label_map: Dict[str, str] = {"general": "coding"}

    def __init__(self, checkpoint: str = CHECKPOINT, threshold: float = THRESHOLD):
        self.checkpoint = checkpoint
        self.threshold = threshold
        self.router = None

    def load(self) -> None:
        """Loads the LMSYS RouteLLM BERT classifier onto CPU."""
        from routellm.routers.routers import BERTRouter

        self.router = BERTRouter(self.checkpoint)
        # Warm up a single pass
        self.router.calculate_strong_win_rate("warmup")

    def classify(self, prompt: str) -> Decision:
        t0 = time.perf_counter()
        win_rate = float(self.router.calculate_strong_win_rate(prompt))
        latency = (time.perf_counter() - t0) * 1000

        if win_rate >= self.threshold:
            category = "reasoning"
            confidence = win_rate
        else:
            category = "coding"
            confidence = 1.0 - win_rate

        return Decision(
            category=category,
            confidence=confidence,
            latency_ms=latency,
            raw={
                "strong_win_rate": round(win_rate, 4),
                "threshold": self.threshold,
                "checkpoint": self.checkpoint,
            },
        )
