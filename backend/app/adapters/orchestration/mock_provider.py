"""
In-process mock orchestration provider.
Faithfully simulates EnterPro's routing, parallel dispatch, and workflow triggers.
"""
from __future__ import annotations
import asyncio
import uuid
from typing import Any, Callable, Coroutine

from app.adapters.orchestration.base import OrchestrationProvider, RouteDecision, WorkflowResult


# ---------------------------------------------------------------------------
# Routing rules — mirrors what EnterPro would compute
# ---------------------------------------------------------------------------

INTENT_TO_AGENTS = {
    "billing": (["billing"], False),
    "order": (["order"], False),
    "technical": (["technical"], False),
    "account": (["account"], False),
    "multi": (["billing", "order"], True),   # parallel by default for multi-domain
    "unknown": (["billing", "order", "technical", "account"], False),  # try all, sequential
}

ROUTING_REASONING = {
    "billing": "Single billing domain identified. Routing to BillingAgent for ledger investigation.",
    "order": "Single order domain identified. Routing to OrderAgent for fulfillment investigation.",
    "technical": "Technical issue detected. Routing to TechnicalAgent for KB-grounded diagnosis.",
    "account": "Account management issue. Routing to AccountAgent for CRM investigation.",
    "multi": "Multi-domain signals detected (billing + order). Dispatching both agents in parallel for fastest resolution.",
    "unknown": "Unable to determine primary domain with high confidence. Routing sequentially through all agents.",
}


class MockOrchestrationProvider(OrchestrationProvider):

    async def route(
        self,
        intent: str,
        urgency: str,
        confidence: float,
        customer_tier: str,
    ) -> RouteDecision:
        agents, parallel = INTENT_TO_AGENTS.get(intent, (["billing"], False))
        reasoning = ROUTING_REASONING.get(intent, f"Routing intent '{intent}' to default agent.")

        # Enterprise customers with high urgency get expanded investigation
        if customer_tier == "Enterprise" and urgency in ("high", "critical"):
            if len(agents) == 1:
                reasoning += f" [Enterprise priority: adding account agent for full-context investigation]"
                if "account" not in agents:
                    agents = agents + ["account"]

        return RouteDecision(
            agents=agents,
            parallel=parallel,
            reasoning=reasoning,
            priority=urgency,
        )

    async def dispatch_parallel(
        self,
        agents: list[str],
        task: Callable[..., Coroutine],
        ticket_id: str,
    ) -> list[Any]:
        """Run agent coroutines concurrently using asyncio.gather."""
        coroutines = [task(agent_name=agent, ticket_id=ticket_id) for agent in agents]
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        # Filter out exceptions, log them
        valid = []
        for r in results:
            if isinstance(r, Exception):
                # Degrade gracefully — don't crash the whole ticket
                continue
            valid.append(r)
        return valid

    async def trigger_workflow(self, workflow_name: str, payload: dict[str, Any]) -> WorkflowResult:
        """Simulate async workflow trigger with a small delay."""
        await asyncio.sleep(0.05)  # simulate network round-trip
        return WorkflowResult(
            workflow_id=f"wf-{uuid.uuid4().hex[:8]}",
            status="triggered",
            payload={"workflow": workflow_name, **payload},
        )

    async def schedule(self, task_name: str, cron: str, payload: dict[str, Any] | None = None) -> str:
        """Simulate task scheduling — returns a fake task ID."""
        task_id = f"sched-{uuid.uuid4().hex[:8]}"
        return task_id
