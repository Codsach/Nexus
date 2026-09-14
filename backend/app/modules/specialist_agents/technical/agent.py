"""Technical Specialist Agent — queries KB and diagnoses technical issues."""
from __future__ import annotations
from app.modules.specialist_agents.base_agent import BaseSpecialistAgent
from app.modules.mock_systems import store
from app.shared.schemas.models import AgentFinding

# Known issues KB (static for prototype — RAG enriches this)
KNOWN_ISSUES = [
    {
        "id": "BUG-3211",
        "title": "App crash on startup after update to v3.2.1",
        "affected_versions": ["3.2.1"],
        "fix_version": "3.2.2",
        "symptoms": ["crash", "startup", "launch", "open", "update"],
        "resolution": "Update to v3.2.2 released Sep 12, 2026. Cache clear as workaround.",
    },
    {
        "id": "BUG-4471",
        "title": "Duplicate payment webhook — known edge case",
        "affected_versions": ["payment_gateway_v2"],
        "fix_version": "payment_gateway_v2.1",
        "symptoms": ["charged twice", "duplicate", "double charge"],
        "resolution": "Payment gateway deduplication deployed Sep 10, 2026.",
    },
    {
        "id": "INC-0912",
        "title": "Login failure for VPN users — false fraud flag",
        "affected_versions": ["auth_service_v4"],
        "fix_version": "auth_service_v4.1",
        "symptoms": ["login", "login failed", "cannot access", "locked", "suspended", "vpn"],
        "resolution": "Auth service false positive rate reduced. Manual review for flagged accounts.",
    },
    {
        "id": "INC-0908",
        "title": "Performance degradation — US-WEST region (resolved)",
        "affected_versions": [],
        "fix_version": "resolved",
        "symptoms": ["slow", "loading", "performance", "timeout", "lag"],
        "resolution": "Infrastructure scaling completed Sep 8, 14:00 UTC. Service restored.",
    },
]


def _match_known_issue(message: str) -> dict | None:
    msg_lower = message.lower()
    for issue in KNOWN_ISSUES:
        if any(s in msg_lower for s in issue["symptoms"]):
            return issue
    return None


class TechnicalAgent(BaseSpecialistAgent):
    name = "technical"
    system_name = "Knowledge Base & Incident Log"

    async def _query_system(self, customer_id: str) -> dict:
        crm = store.get_crm(customer_id)
        history = store.get_ticket_history(customer_id)
        tech_history = [h for h in history if h.category == "technical"]
        return {
            "customer_id": customer_id,
            "customer_name": crm.name if crm else "Unknown",
            "tier": crm.tier if crm else "Standard",
            "tech_ticket_history_count": len(tech_history),
            "recent_tech_issues": [h.issue_summary for h in tech_history[:3]],
        }

    def _build_prompt(self, message: str, raw_data: dict) -> str:
        matched = _match_known_issue(message)
        return (
            f"Customer message: {message}\n\n"
            f"Known issue match: {matched}\n"
            f"Customer tech history: {raw_data.get('recent_tech_issues', [])}\n\n"
            "Diagnose the technical issue and provide a resolution path."
        )

    def _build_finding(self, ticket_id: str, raw_data: dict, llm_result) -> AgentFinding:
        # We need to re-match here since we don't pass message through
        # Instead use llm_result context
        evidence = []
        actions = []
        sub_type = "default"
        confidence = 0.70

        # Check if raw_data has matched issue (we pass it in context)
        matched = raw_data.get("matched_issue")

        if matched:
            evidence.append(f"KNOWN ISSUE MATCH: {matched['id']} — {matched['title']}")
            evidence.append(f"Fix available in: {matched['fix_version']}")
            evidence.append(f"Resolution: {matched['resolution']}")
            actions.append(f"Apply fix: {matched['resolution']}")
            actions.append("Send update notification to customer")
            confidence = 0.91
            if "crash" in matched["title"].lower():
                sub_type = "app_error"
            elif "login" in matched["title"].lower():
                sub_type = "login_issue"
            elif "performance" in matched["title"].lower():
                sub_type = "performance"
        else:
            evidence.append("No exact known-issue match. Escalating to technical review.")
            evidence.append(f"Customer has {raw_data.get('tech_ticket_history_count', 0)} prior technical tickets")
            actions.append("Escalate to Level 2 technical support")
            actions.append("Collect diagnostics: app version, device, error message")
            confidence = 0.55

        root_cause = llm_result.content if llm_result else "Technical issue identified via KB lookup"

        return AgentFinding(
            ticket_id=ticket_id,
            agent_name=self.name,
            summary=f"Technical investigation complete. KB match: {'yes' if matched else 'no'}.",
            evidence=evidence,
            confidence=confidence,
            actions_available=actions,
            root_cause=root_cause,
            raw_data={
                "sub_type": sub_type,
                "version": "3.2.1",
                "new_version": "3.2.2",
                "start_time": "2:00 PM UTC",
                "end_time": "3:45 PM UTC",
            },
        )

    async def investigate(self, ticket_id: str, customer_id: str, message: str) -> AgentFinding:
        """Override to inject matched issue into raw_data before building finding."""
        from app.shared.schemas.models import TraceEventType
        from app.shared.events import bus

        await bus.emit(bus.make_event(
            ticket_id=ticket_id,
            event_type=TraceEventType.agent_started,
            agent_name=self.name,
            message=f"🔍 Technical Agent: searching knowledge base and incident log...",
        ))

        raw_data = await self._query_system(customer_id)
        matched = _match_known_issue(message)
        raw_data["matched_issue"] = matched

        from app.adapters.llm import llm
        result = await llm.complete(
            prompt=self._build_prompt(message, raw_data),
            system_prompt=self._system_prompt(),
            context={"task_type": "root_cause_analysis", "domain": self.name, "raw_data": raw_data},
        )

        finding = self._build_finding(ticket_id, raw_data, result)

        await bus.emit(bus.make_event(
            ticket_id=ticket_id,
            event_type=TraceEventType.agent_finished,
            agent_name=self.name,
            message=f"✅ Technical Agent complete — confidence: {finding.confidence:.0%}",
            confidence=finding.confidence,
        ))

        return finding
