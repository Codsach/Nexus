"""Account Specialist Agent — queries CRM, identifies account state issues."""
from __future__ import annotations
from app.modules.specialist_agents.base_agent import BaseSpecialistAgent
from app.modules.mock_systems import store
from app.shared.schemas.models import AgentFinding


class AccountAgent(BaseSpecialistAgent):
    name = "account"
    system_name = "CRM & Account Management"

    async def _query_system(self, customer_id: str) -> dict:
        crm = store.get_crm(customer_id)
        billing = store.get_billing(customer_id)
        history = store.get_ticket_history(customer_id)

        if not crm:
            return {"error": "no_crm_record", "customer_id": customer_id}

        churn_risk = (
            crm.account_status in ("suspended", "at_risk") or
            len(history) >= 3
        )

        return {
            "customer_id": customer_id,
            "customer_name": crm.name,
            "email": crm.email,
            "tier": crm.tier,
            "account_status": crm.account_status,
            "join_date": crm.join_date,
            "total_spend_usd": crm.total_spend_usd,
            "notes": crm.notes,
            "ticket_count": len(history),
            "subscription_status": billing.subscription_status if billing else "unknown",
            "payment_method": billing.payment_method if billing else "unknown",
            "churn_risk": churn_risk,
            "churn_risk_level": "critical" if len(history) >= 4 else "high" if len(history) >= 3 else "low",
        }

    def _build_prompt(self, message: str, raw_data: dict) -> str:
        return (
            f"Customer message: {message}\n\n"
            f"CRM data:\n"
            f"- Customer: {raw_data.get('customer_name')} ({raw_data.get('tier')} tier)\n"
            f"- Account status: {raw_data.get('account_status')}\n"
            f"- Subscription: {raw_data.get('subscription_status')}\n"
            f"- Member since: {raw_data.get('join_date')} | Total spend: ${raw_data.get('total_spend_usd')}\n"
            f"- Notes: {raw_data.get('notes')}\n"
            f"- Prior tickets: {raw_data.get('ticket_count')}\n"
            f"- Churn risk: {raw_data.get('churn_risk_level')}\n\n"
            "Identify account-related root cause and recommended action."
        )

    def _build_finding(self, ticket_id: str, raw_data: dict, llm_result) -> AgentFinding:
        evidence = []
        actions = []
        confidence = 0.75
        sub_type = "default"

        status = raw_data.get("account_status", "active")
        tier = raw_data.get("tier", "Standard")

        if status == "suspended":
            evidence.append(f"ACCOUNT SUSPENDED: {raw_data.get('customer_name')}'s account is currently suspended")
            sub_status = raw_data.get("subscription_status", "")
            if sub_status == "past_due":
                evidence.append("Suspension reason: payment failure — subscription past due")
                actions.append("Prompt customer to update payment method")
                actions.append("Account will reactivate automatically within 24h of payment")
            else:
                evidence.append("Suspension reason: automated fraud detection flag (possible false positive)")
                actions.append("Review fraud flag — clear if false positive")
                actions.append("Restore account immediately if flag confirmed false positive")
            confidence = 0.92
            sub_type = "suspended"

        elif status == "at_risk":
            count = raw_data.get("ticket_count", 0)
            risk = raw_data.get("churn_risk_level", "high")
            evidence.append(f"CHURN RISK ({risk.upper()}): {count} support tickets in recent period")
            evidence.append(f"Account notes: {raw_data.get('notes', '')}")
            evidence.append(f"Customer LTV: ${raw_data.get('total_spend_usd', 0):.2f}")
            actions.append("Prioritize resolution — high-value at-risk customer")
            actions.append("Consider proactive retention offer after ticket resolved")
            actions.append("Flag for Customer Success Manager follow-up")
            confidence = 0.85

        if tier == "Enterprise":
            evidence.append(f"ENTERPRISE ACCOUNT: SLA 2hr response time applies")
            actions.append("Escalate to Enterprise support queue if not resolved in 30 min")

        if not evidence:
            evidence.append(f"Account in good standing: {status}, {tier} tier, joined {raw_data.get('join_date')}")
            evidence.append(f"Total lifetime spend: ${raw_data.get('total_spend_usd', 0):.2f}")
            actions.append("Provide standard account support")
            confidence = 0.65

        root_cause = llm_result.content if llm_result else "Account state issue identified via CRM"

        return AgentFinding(
            ticket_id=ticket_id,
            agent_name=self.name,
            summary=f"Account investigation complete for {raw_data.get('customer_name')} ({tier}).",
            evidence=evidence,
            confidence=confidence,
            actions_available=actions,
            root_cause=root_cause,
            raw_data={
                "sub_type": sub_type,
                "status": status,
                "plan": raw_data.get("subscription_status"),
                "date": "September 10, 2026",
            },
        )
