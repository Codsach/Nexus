from app.core.config import settings
from app.adapters.llm.base import LLMProvider


def get_llm_provider() -> LLMProvider:
    """Factory — returns the configured LLM provider. Change LLM_PROVIDER env var to switch."""
    provider = settings.llm_provider.lower()
    if provider == "mock":
        from app.adapters.llm.mock_provider import MockLLMProvider
        return MockLLMProvider()
    elif provider == "qwen":
        from app.adapters.llm.qwen_provider import QwenProvider
        return QwenProvider()
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}. Valid: mock, qwen")


# Singleton instance
llm: LLMProvider = get_llm_provider()
