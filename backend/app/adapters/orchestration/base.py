"""
Abstract orchestration provider interface.
Mirrors what EnterPro would provide — routing, workflow triggers, scheduling.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


@dataclass
class RouteDecision:
    agents: list[str]           # e.g. ["billing", "order"] for multi-domain
    parallel: bool              # whether to run agents in parallel
    reasoning: str              # why this routing decision was made
    priority: str = "medium"    # low | medium | high | critical


@dataclass
class WorkflowResult:
    workflow_id: str
    status: str     # "triggered" | "completed" | "failed"
    payload: dict[str, Any] = field(default_factory=dict)


class OrchestrationProvider(ABC):

    @abstractmethod
    async def route(
        self,
        intent: str,
        urgency: str,
        confidence: float,
        customer_tier: str,
    ) -> RouteDecision:
        """Decide which specialist agent(s) to invoke for this ticket."""

    @abstractmethod
    async def dispatch_parallel(
        self,
        agents: list[str],
        task: Callable[..., Coroutine],
        ticket_id: str,
    ) -> list[Any]:
        """Run multiple agent coroutines in parallel and collect results."""

    @abstractmethod
    async def trigger_workflow(self, workflow_name: str, payload: dict[str, Any]) -> WorkflowResult:
        """Trigger a named workflow (e.g. 'escalation', 'analytics_refresh')."""

    @abstractmethod
    async def schedule(self, task_name: str, cron: str, payload: dict[str, Any] | None = None) -> str:
        """Schedule a recurring task. Returns task ID."""
