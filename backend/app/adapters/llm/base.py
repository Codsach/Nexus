"""
Abstract LLM provider interface. All modules depend on this — never on a concrete provider.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ClassificationResult:
    intent: str          # billing | order | technical | account | multi | unknown
    urgency: str         # low | medium | high | critical
    sentiment: str       # positive | neutral | negative | very_negative
    confidence: float    # 0.0 – 1.0
    reasoning: str       # brief explanation of classification


@dataclass
class CompletionResult:
    content: str
    reasoning_steps: list[str]  # chain-of-thought steps shown in trace
    confidence: float
    citations: list[str] = None  # source IDs used in generation

    def __post_init__(self):
        if self.citations is None:
            self.citations = []


@dataclass
class EmbeddingResult:
    embedding: list[float]
    model: str


class LLMProvider(ABC):
    """Abstract interface — implement once per backend (mock, qwen, etc.)."""

    @abstractmethod
    async def classify(self, text: str, context: dict[str, Any] | None = None) -> ClassificationResult:
        """Classify a customer message: intent, urgency, sentiment."""

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> CompletionResult:
        """Generate a text completion (reasoning, response, narrative)."""

    @abstractmethod
    async def embed(self, text: str) -> EmbeddingResult:
        """Generate an embedding vector for RAG."""
