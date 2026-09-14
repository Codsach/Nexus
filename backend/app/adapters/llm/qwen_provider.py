"""
Qwen provider stub — implements LLMProvider against DashScope OpenAI-compatible API.
Activate with: LLM_PROVIDER=qwen in .env
"""
from __future__ import annotations
from typing import Any
from app.adapters.llm.base import LLMProvider, ClassificationResult, CompletionResult, EmbeddingResult
from app.core.config import settings


class QwenProvider(LLMProvider):
    """Real Qwen implementation via DashScope OpenAI-compatible endpoint."""

    def __init__(self):
        try:
            import openai
            self.client = openai.AsyncOpenAI(
                api_key=settings.qwen_api_key,
                base_url=settings.qwen_base_url,
            )
        except ImportError:
            raise RuntimeError("openai package required for QwenProvider: pip install openai")

    async def classify(self, text: str, context: dict[str, Any] | None = None) -> ClassificationResult:
        # TODO: implement real Qwen classification call
        raise NotImplementedError("QwenProvider.classify() — wire up when API access confirmed")

    async def complete(self, prompt: str, system_prompt: str | None = None, context: dict[str, Any] | None = None) -> CompletionResult:
        # TODO: implement real Qwen completion call
        raise NotImplementedError("QwenProvider.complete() — wire up when API access confirmed")

    async def embed(self, text: str) -> EmbeddingResult:
        # TODO: implement real Qwen embeddings
        raise NotImplementedError("QwenProvider.embed() — wire up when API access confirmed")
