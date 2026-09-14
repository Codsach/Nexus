"""Order Specialist Agent — queries order DB, finds fulfillment issues."""
from __future__ import annotations
from app.modules.specialist_agents.base_agent import BaseSpecialistAgent
from app.modules.mock_systems import store
from app.shared.schemas.models import AgentFinding


class OrderAgent(BaseSpecialistAgent):
    name = "order"
    system_name = "Order & Fulfillment Database"

    async def _query_system(self, customer_id: str) -> dict:
        orders = store.get_orders(customer_id)
        crm = store.get_crm(customer_id)
        if not orders:
            return {"customer_id": customer_id, "orders": [], "has_issues": False}

        # Find most recent or most problematic order
        problem_orders = [o for o in orders if o.status in ("lost", "delayed", "return_initiated")]
        focus_order = problem_orders[0] if problem_orders else orders[0]

        return {
            "customer_id": customer_id,
            "customer_name": crm.name if crm else "Unknown",
            "tier": crm.tier if crm else "Standard",
            "total_orders": len(orders),
            "problem_orders_count": len(problem_orders),
            "focus_order": focus_order.model_dump() if focus_order else None,
            "all_statuses": [o.status for o in orders],
            "has_lost": any(o.status == "lost" for o in orders),
            "has_delayed": any(o.status == "delayed" for o in orders),
            "has_return": any(o.status == "return_initiated" for o in orders),
        }

    def _build_prompt(self, message: str, raw_data: dict) -> str:
        order = raw_data.get("focus_order", {})
        return (
            f"Customer message: {message}\n\n"
            f"Order data:\n"
            f"- Order {order.get('order_id')}: {order.get('product_name')}\n"
            f"- Status: {order.get('status')}\n"
            f"- Expected delivery: {order.get('expected_delivery')}, Actual: {order.get('actual_delivery')}\n"
            f"- Fulfillment notes: {order.get('fulfillment_notes')}\n"
            f"- Shipping events: {order.get('shipping_events', [])}\n\n"
            "Identify the root cause of the delivery/order issue."
        )

    def _build_finding(self, ticket_id: str, raw_data: dict, llm_result) -> AgentFinding:
        evidence = []
        actions = []
        confidence = 0.70
        order = raw_data.get("focus_order") or {}
        sub_type = "default"

        if raw_data.get("has_lost"):
            oid = order.get("order_id", "")
            evidence.append(f"ORDER LOST: {oid} shows carrier delivery scan at hub — not confirmed at door")
            evidence.append(f"Product: {order.get('product_name')} (${order.get('total_usd')})")
            evidence.append("Fulfillment note: " + order.get("fulfillment_notes", "carrier GPS discrepancy"))
            actions.append("File carrier investigation case")
            actions.append("Initiate replacement shipment (expedited, no charge)")
            actions.append("Issue prepaid return label in case original turns up")
            confidence = 0.88
            sub_type = "lost_package"

        elif raw_data.get("has_delayed"):
            events = order.get("shipping_events", [])
            held_event = next((e for e in events if e.get("status") == "held"), None)
            reason = held_event.get("description", "operational delay") if held_event else "operational delay"
            evidence.append(f"ORDER DELAYED: {order.get('order_id')} held at distribution hub")
            evidence.append(f"Delay reason: {reason}")
            evidence.append(f"Original ETA: {order.get('expected_delivery')}")
            actions.append("Provide revised ETA to customer")
            actions.append("Apply 15% discount to next order as compensation")
            confidence = 0.85
            sub_type = "delayed_order"

        elif raw_data.get("has_return"):
            evidence.append(f"RETURN IN PROGRESS: {order.get('order_id')}")
            evidence.append(order.get("fulfillment_notes", "Return requested"))
            actions.append("Confirm return label status")
            actions.append("Track return receipt and process refund")
            confidence = 0.82
            sub_type = "return_request"

        elif order:
            evidence.append(f"Order {order.get('order_id')} status: {order.get('status')}")
            evidence.append(f"Tracking: {order.get('tracking_number')}")
            actions.append("Provide tracking update")
            confidence = 0.65

        else:
            evidence.append("No recent orders found for this customer")
            confidence = 0.50

        root_cause = llm_result.content if llm_result else "Order fulfillment issue identified"

        return AgentFinding(
            ticket_id=ticket_id,
            agent_name=self.name,
            summary=f"Order investigation complete. {len(evidence)} finding(s).",
            evidence=evidence,
            confidence=confidence,
            actions_available=actions,
            root_cause=root_cause,
            raw_data={
                "order_id": order.get("order_id"),
                "status": order.get("status"),
                "tracking": order.get("tracking_number"),
                "amount": order.get("total_usd"),
                "date": order.get("expected_delivery"),
                "sub_type": sub_type,
            },
        )
