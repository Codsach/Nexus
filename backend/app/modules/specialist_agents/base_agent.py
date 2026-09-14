"""
Base specialist agent. All four agents (Billing, Order, Technical, Account) extend this.
Every agent: queries its mock system → reasons with LLM → returns AgentFinding + emits trace events.
"""
from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime

from app.adapters.llm import llm
from app.shared.schemas.models import AgentFinding, TraceEventType
from app.shared.events import bus


class BaseSpecialistAgent(ABC):
    name: str = "base"
    system_name: str = "Unknown System"

    async def investigate(self, ticket_id: str, customer_id: str, message: str) -> AgentFinding:
        """Full investigation pipeline: query → reason → finding."""
        # Emit started
        await bus.emit(bus.make_event(
            ticket_id=ticket_id,
            event_type=TraceEventType.agent_started,
            agent_name=self.name,
            message=f"🔍 {self.name.title()} Agent: querying {self.system_name}...",
            system=self.system_name,
        ))

        try:
            # 1. Query mock system
            raw_data = await self._query_system(customer_id)

            # 2. Reason with LLM
            result = await llm.complete(
                prompt=self._build_prompt(message, raw_data),
                system_prompt=self._system_prompt(),
                context={
                    "task_type": "root_cause_analysis",
                    "domain": self.name,
                    "raw_data": raw_data,
                },
            )

            # 3. Build finding
            finding = self._build_finding(ticket_id, raw_data, result)

            # Emit finished
            await bus.emit(bus.make_event(
                ticket_id=ticket_id,
                event_type=TraceEventType.agent_finished,
                agent_name=self.name,
                message=(
                    f"✅ {self.name.title()} Agent complete — "
                    f"confidence: {finding.confidence:.0%} | "
                    f"root cause: {(finding.root_cause or 'identified')[:80]}"
                ),
                confidence=finding.confidence,
                root_cause=finding.root_cause,
            ))

            return finding

        except Exception as e:
            await bus.emit(bus.make_event(
                ticket_id=ticket_id,
                event_type=TraceEventType.agent_finished,
                agent_name=self.name,
                message=f"⚠️ {self.name.title()} Agent: degraded — {str(e)[:100]}",
                error=str(e),
            ))
            # Return low-confidence finding to allow graceful degradation
            return AgentFinding(
                ticket_id=ticket_id,
                agent_name=self.name,
                summary=f"{self.name.title()} system query encountered an error. Partial data only.",
                evidence=[f"Error: {str(e)}"],
                confidence=0.2,
                actions_available=[],
            )

    @abstractmethod
    async def _query_system(self, customer_id: str) -> dict:
        """Query the relevant mock backend system. Return raw data dict."""

    @abstractmethod
    def _build_prompt(self, message: str, raw_data: dict) -> str:
        """Build the investigation prompt for the LLM."""

    @abstractmethod
    def _build_finding(self, ticket_id: str, raw_data: dict, llm_result) -> AgentFinding:
        """Construct the AgentFinding from raw data + LLM result."""

    def _system_prompt(self) -> str:
        return (
            f"You are a specialist {self.name} support agent for Nexus. "
            "Investigate the issue using the provided system data. "
            "Identify the root cause, not just the surface symptom. "
            "Be specific about what the data shows."
        )
