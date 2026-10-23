"""
Semantic Router backend: Aurelio AI semantic router using FastEmbed / ONNX.
Runs in-process on CPU with ~50 MB RAM and < 5 ms decision latency.
Zero GPU VRAM, zero dependencies on Ollama.
"""

import time
from typing import Dict, Any, List, Optional

from .base import CATEGORIES, Decision, extract_routing_intent

CODING_UTTERANCES = [
    "Write a Python function to validate an IPv4 address with regex and unit tests",
    "Refactor this C# service class to use dependency injection and add xUnit tests",
    "Create a FluentValidation validator for a UserRegistrationDTO in .NET",
    "Fix the NullReferenceException in my ASP.NET Core controller when the request body is empty",
    "Write a SQL query that returns the top 5 customers by total order value in the last 30 days",
    "Implement a REST endpoint in FastAPI for uploading a file and storing it in S3",
    "Convert this JavaScript callback-based code to async/await",
    "Add a Dockerfile and docker-compose.yml for a Node.js app with a Postgres database",
    "Write a bash script that backs up a folder to a timestamped tar.gz and deletes backups older than 7 days",
    "Design the clean architecture folder structure for an order fulfillment service with CQRS and MediatR",
    "Write unit tests with pytest for a function that parses CSV rows into dataclasses",
    "Implement a constant-time string comparison helper in C# for comparing API keys",
    "My React component re-renders infinitely when I call setState inside useEffect, fix it",
    "Write a regex to extract all email addresses from a text file and a Python script that uses it",
    "Create a GitHub Actions workflow that builds and tests a .NET 8 solution on every pull request",
    "Implement a binary search algorithm in TypeScript",
    "Debug this memory leak in my Go HTTP server",
    "Set up Kubernetes deployment manifests with ingress and horizontal pod autoscaler",
]

REASONING_UTTERANCES = [
    "Audit this HMAC-SHA256 signature verification function for timing attacks and constant-time safety",
    "Analyze this authentication handshake for timing attack vulnerabilities and race conditions",
    "Prove that the square root of 2 is irrational",
    "Is this double-checked locking implementation thread-safe under the Java memory model? Explain step by step",
    "A bat and a ball cost $1.10 in total. The bat costs $1 more than the ball. How much does the ball cost? Reason carefully",
    "Audit this Solidity smart contract for reentrancy bugs and integer overflow",
    "Prove by induction that the sum of the first n odd numbers is n squared",
    "Can a process deadlock if all resources are requested in strict linear order? Formal proof",
    "Find the subtle race condition in this concurrent queue implementation",
    "Solve this logic riddle: three gods A, B, and C are called True, False, and Random",
    "Evaluate the mathematical correctness of this custom elliptic curve cryptography formula",
    "Perform a threat model and security risk assessment for this OAuth2 token exchange",
    "What is the time complexity of this recursive divide-and-conquer algorithm? Prove with Master Theorem",
    "Determine if this distributed consensus algorithm guarantees safety during network partitions",
    "Analyze this AES-GCM nonce reuse scenario and explain how plaintext recovery works",
]

GENERAL_UTTERANCES = [
    "Hello! How are you doing today?",
    "Summarize the key differences between REST and GraphQL in three bullet points",
    "What are the pros and cons of working remotely?",
    "Help me draft a polite email declining an invitation to a meeting",
    "Explain quantum computing in simple terms for a high school student",
    "Translate this paragraph into Spanish",
    "What does the acronym SOLID stand for in software engineering?",
    "Give me 5 creative ideas for a team building activity",
    "What is the capital of France and what is it known for?",
    "Tell me a short joke about programming",
]


class SemanticBackend:
    name = "semantic"
    categories = list(CATEGORIES)
    label_map: Dict[str, str] = {}

    def __init__(self):
        self.router = None
        self.encoder = None

    def load(self) -> None:
        """Initializes FastEmbed encoder and Semantic Router layer."""
        from semantic_router import Route, IndexedRouter
        from semantic_router.encoders import FastEmbedEncoder

        # Default model is BAAI/bge-small-en-v1.5 running via ONNX on CPU
        self.encoder = FastEmbedEncoder()

        routes = [
            Route(name="coding", utterances=CODING_UTTERANCES),
            Route(name="reasoning", utterances=REASONING_UTTERANCES),
            Route(name="general", utterances=GENERAL_UTTERANCES),
        ]

        self.router = IndexedRouter(encoder=self.encoder, routes=routes)

    def classify(self, prompt: str) -> Decision:
        t0 = time.perf_counter()
        choice = self.router(prompt)
        latency = (time.perf_counter() - t0) * 1000

        # choice.name is the chosen route name, or None if below similarity threshold
        category = choice.name if (choice and choice.name in CATEGORIES) else "coding"
        confidence = choice.confidence if choice else None

        return Decision(
            category=category,
            confidence=confidence,
            latency_ms=latency,
            raw={"choice_name": getattr(choice, "name", None), "confidence": confidence},
        )
