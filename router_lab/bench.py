#!/usr/bin/env python3
"""
Router benchmark: runs one backend over router_lab/prompts.jsonl and reports
accuracy, confusion matrix, warm latency (p50/p95), cold load time and RAM.

Usage (inside the Hermes container, with the backend's venv):
    python /workspace/router_lab/bench.py --backend semantic
"""

import argparse
import json
import os
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))   # makes 'routers' importable


def rss_mb() -> float:
    """Resident memory of this process in MB (Linux /proc, no extra deps)."""
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024.0
    return 0.0


def percentile(values, pct):
    s = sorted(values)
    k = (len(s) - 1) * pct / 100.0
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", required=True)
    ap.add_argument("--prompts", default=os.path.join(HERE, "prompts.jsonl"))
    ap.add_argument("--out", default=os.path.join(HERE, "results"))
    ap.add_argument("--warmup", type=int, default=3)
    args = ap.parse_args()

    with open(args.prompts, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]

    rss_before = rss_mb()
    t0 = time.perf_counter()
    from routers import get_backend, extract_routing_intent   # imported here so import cost is measured
    backend = get_backend(args.backend)
    backend.load()
    cold_load_s = time.perf_counter() - t0
    rss_after = rss_mb()

    for _ in range(args.warmup):
        backend.classify("warm up the router")

    latencies, details = [], []
    confusion = defaultdict(Counter)
    correct = 0
    for row in rows:
        expected = backend.label_map.get(row["label"], row["label"])
        t = time.perf_counter()
        d = backend.classify(extract_routing_intent(row["prompt"]))
        wall_ms = (time.perf_counter() - t) * 1000
        if d.category not in backend.categories:
            print(f"❌ backend returned category outside its label set: {d.category!r}", file=sys.stderr)
            return 2
        ok = d.category == expected
        correct += ok
        latencies.append(wall_ms)
        confusion[expected][d.category] += 1
        details.append({"prompt": row["prompt"], "expected": expected, "got": d.category,
                        "confidence": d.confidence, "ms": round(wall_ms, 2), "ok": ok})

    result = {
        "backend": args.backend,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "n": len(rows),
        "accuracy": round(correct / len(rows), 4),
        "latency_ms": {"p50": round(percentile(latencies, 50), 2),
                       "p95": round(percentile(latencies, 95), 2),
                       "mean": round(statistics.mean(latencies), 2)},
        "cold_load_s": round(cold_load_s, 2),
        "ram_mb": {"before": round(rss_before, 1), "after_load": round(rss_after, 1),
                   "delta": round(rss_after - rss_before, 1), "end": round(rss_mb(), 1)},
        "label_map": backend.label_map,
        "confusion": {k: dict(v) for k, v in confusion.items()},
        "details": details,
    }

    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, f"{args.backend}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n=== {args.backend} ===")
    print(f"accuracy   : {result['accuracy']:.1%} ({correct}/{len(rows)})")
    print(f"latency ms : p50 {result['latency_ms']['p50']}  p95 {result['latency_ms']['p95']}")
    print(f"cold load  : {result['cold_load_s']} s")
    print(f"RAM        : +{result['ram_mb']['delta']} MB (process {result['ram_mb']['end']} MB)")
    print("confusion (expected -> got):")
    for exp, got in result["confusion"].items():
        print(f"  {exp:10s} {dict(got)}")
    misses = [d for d in details if not d["ok"]]
    if misses:
        print("misses:")
        for m in misses:
            print(f"  [{m['expected']} -> {m['got']}] {m['prompt'][:90]}")
    print(f"\nsaved: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
