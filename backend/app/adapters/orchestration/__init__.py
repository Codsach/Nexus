from app.core.config import settings
from app.adapters.orchestration.base import OrchestrationProvider


def get_orchestration_provider() -> OrchestrationProvider:
    p = settings.orchestration_provider.lower()
    if p == "mock":
        from app.adapters.orchestration.mock_provider import MockOrchestrationProvider
        return MockOrchestrationProvider()
    elif p == "enterpro":
        from app.adapters.orchestration.enterpro_provider import EnterProProvider
        return EnterProProvider()
    raise ValueError(f"Unknown ORCHESTRATION_PROVIDER: {p}")


orchestrator: OrchestrationProvider = get_orchestration_provider()
