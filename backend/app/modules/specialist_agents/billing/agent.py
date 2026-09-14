"""
Billing Specialist Agent.
Queries the billing ledger, identifies anomalies (duplicate charges, overcharges, failed payments).
"""
from __future__ import annotations
from app.modules.specialist_agents.base_agent import BaseSpecialistAgent
from app.modules.mock_systems import store
from app.shared.schemas.models import AgentFinding


class BillingAgent(BaseSpecialistAgent):
    name = "billing"
    system_name = "Billing Ledger"

    async def _query_system(self, customer_id: str) -> dict:
        billing = store.get_billing(customer_id)
        crm = store.get_crm(customer_id)
        if not billing:
            return {"error": "no_billing_record", "customer_id": customer_id}

        txns = billing.transactions
        amounts = [t.amount_usd for t in txns]

        # Detect anomalies
        duplicate_pairs = []
        for i, t1 in enumerate(txns):
            for t2 in txns[i+1:]:
                if (t1.amount_usd == t2.amount_usd and
                    t1.date == t2.date and
                    t1.status == "completed" and t2.status == "completed"):
                    duplicate_pairs.append((t1.transaction_id, t2.transaction_id, t1.amount_usd, t1.date))

        return {
            "customer_id": customer_id,
            "customer_name": crm.name if crm else "Unknown",
            "tier": crm.tier if crm else "Standard",
            "plan": billing.subscription_plan,
            "subscription_status": billing.subscription_status,
            "next_billing_date": billing.next_billing_date,
            "payment_method": billing.payment_method,
            "total_refunds": billing.total_refunds_usd,
            "disputed_charges": billing.disputed_charges,
            "recent_transactions": [t.model_dump() for t in txns[:6]],
            "duplicate_charge_pairs": duplicate_pairs,
            "has_failed_payment": any(t.status == "failed" for t in txns),
            "has_disputed_charges": len(billing.disputed_charges) > 0,
        }

    def _build_prompt(self, message: str, raw_data: dict) -> str:
        return (
            f"Customer message: {message}\n\n"
            f"Billing ledger data:\n"
            f"- Plan: {raw_data.get('plan')} ({raw_data.get('subscription_status')})\n"
            f"- Duplicate charges detected: {raw_data.get('duplicate_charge_pairs', [])}\n"
            f"- Disputed charges: {raw_data.get('disputed_charges', [])}\n"
            f"- Failed payments: {raw_data.get('has_failed_payment')}\n"
            f"- Recent transactions: {raw_data.get('recent_transactions', [])[:3]}\n\n"
            "Identify the root cause of the billing issue."
        )

    def _build_finding(self, ticket_id: str, raw_data: dict, llm_result) -> AgentFinding:
        evidence = []
        actions = []
        confidence = 0.70

        duplicates = raw_data.get("duplicate_charge_pairs", [])
        if duplicates:
            txn1, txn2, amount, date = duplicates[0]
            evidence.append(f"DUPLICATE CHARGE: Two transactions of ${amount} on {date} ({txn1}, {txn2})")
            evidence.append(f"Both transactions have status 'completed' — customer was double-billed")
            actions.append(f"Refund duplicate charge: ${amount} (transaction {txn2})")
            actions.append("Add $10 service credit as apology")
            confidence = 0.94

        if raw_data.get("has_failed_payment"):
            evidence.append("PAYMENT FAILURE: Most recent charge failed — possible expired card")
            actions.append("Prompt customer to update payment method")
            confidence = max(confidence, 0.90)

        if raw_data.get("has_disputed_charges"):
            disputed = raw_data.get("disputed_charges", [])
            evidence.append(f"DISPUTED CHARGES on account: {', '.join(disputed)}")
            actions.append("Review disputed transactions with billing team")
            confidence = max(confidence, 0.85)

        if raw_data.get("total_refunds", 0) > 0:
            evidence.append(f"Prior refunds on account: ${raw_data['total_refunds']:.2f}")

        if not evidence:
            evidence.append(f"No billing anomalies detected. Plan: {raw_data.get('plan')}, Status: {raw_data.get('subscription_status')}")
            actions.append("Provide billing statement on request")
            confidence = 0.65

        root_cause = llm_result.content if llm_result else "Billing anomaly identified in transaction history"

        return AgentFinding(
            ticket_id=ticket_id,
            agent_name=self.name,
            summary=f"Billing investigation complete for {raw_data.get('customer_name', 'customer')}. "
                    f"{len(evidence)} finding(s) identified.",
            evidence=evidence,
            confidence=confidence,
            actions_available=actions,
            root_cause=root_cause,
            raw_data={
                "plan": raw_data.get("plan"),
                "subscription_status": raw_data.get("subscription_status"),
                "duplicate_charges": len(duplicates) > 0,
                "amount": duplicates[0][2] if duplicates else None,
                "date": duplicates[0][3] if duplicates else None,
                "sub_type": "duplicate_charge" if duplicates else (
                    "billing_question" if not raw_data.get("has_failed_payment") else "failed_payment"
                ),
            },
        )
