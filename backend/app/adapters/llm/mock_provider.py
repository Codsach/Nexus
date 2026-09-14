"""
Intelligent Mock LLM Provider.

Produces realistic, deterministic, domain-aware reasoning text.
Simulates Qwen's chain-of-thought style. No API key required.
The demo is fully functional with this provider.
"""
from __future__ import annotations
import hashlib
import math
import re
from typing import Any

from app.adapters.llm.base import (
    LLMProvider,
    ClassificationResult,
    CompletionResult,
    EmbeddingResult,
)


# ---------------------------------------------------------------------------
# Keyword-driven classification rules (deterministic)
# ---------------------------------------------------------------------------

BILLING_KEYWORDS = [
    "charge", "charged", "bill", "billing", "payment", "refund", "invoice",
    "subscription", "fee", "overcharged", "duplicate", "credit card", "amount",
    "transaction", "receipt", "price", "cost", "money", "paid", "pay",
]
ORDER_KEYWORDS = [
    "order", "delivery", "package", "shipping", "shipped", "tracking",
    "arrived", "missing", "lost", "return", "refund", "item", "product",
    "warehouse", "dispatch", "courier", "parcel", "delayed", "not received",
]
TECHNICAL_KEYWORDS = [
    "error", "bug", "crash", "not working", "broken", "issue", "problem",
    "app", "software", "login", "password", "account access", "feature",
    "slow", "performance", "loading", "update", "version", "install",
]
ACCOUNT_KEYWORDS = [
    "account", "profile", "email", "username", "suspended", "locked",
    "access", "permission", "plan", "upgrade", "downgrade", "cancel",
    "tier", "membership", "settings", "data", "privacy",
]

NEGATIVE_KEYWORDS = [
    "angry", "frustrated", "terrible", "worst", "unacceptable", "disgusting",
    "furious", "horrible", "awful", "ridiculous", "scam", "fraud",
]
URGENCY_KEYWORDS = {
    "critical": ["urgent", "immediately", "asap", "emergency", "critical", "right now", "today"],
    "high": ["important", "soon", "quickly", "need help", "please help", "frustrated", "angry"],
    "medium": ["wondering", "question", "issue", "problem", "help"],
}


def _score_keywords(text: str, keywords: list[str]) -> int:
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw in text_lower)


def _classify_intent(text: str) -> tuple[str, float]:
    scores = {
        "billing": _score_keywords(text, BILLING_KEYWORDS),
        "order": _score_keywords(text, ORDER_KEYWORDS),
        "technical": _score_keywords(text, TECHNICAL_KEYWORDS),
        "account": _score_keywords(text, ACCOUNT_KEYWORDS),
    }
    total = sum(scores.values())
    if total == 0:
        return "unknown", 0.5

    top = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    first, second = top[0], top[1]

    if first[1] > 0 and second[1] > 0 and second[1] >= first[1] * 0.6:
        return "multi", round(0.7 + min(first[1], 3) * 0.05, 2)

    if first[1] == 0:
        return "unknown", 0.5

    confidence = round(min(0.95, 0.65 + first[1] * 0.08), 2)
    return first[0], confidence


def _classify_urgency(text: str) -> str:
    text_lower = text.lower()
    for level in ("critical", "high", "medium"):
        if any(kw in text_lower for kw in URGENCY_KEYWORDS[level]):
            return level
    return "low"


def _classify_sentiment(text: str) -> str:
    text_lower = text.lower()
    neg_score = _score_keywords(text, NEGATIVE_KEYWORDS)
    if neg_score >= 2:
        return "very_negative"
    if neg_score == 1:
        return "negative"
    if any(w in text_lower for w in ["please", "help", "wondering", "question"]):
        return "neutral"
    return "neutral"


# ---------------------------------------------------------------------------
# Response templates
# ---------------------------------------------------------------------------

BILLING_RESPONSES = {
    "duplicate_charge": (
        "I've reviewed your billing history and confirmed the duplicate charge. "
        "I can see two transactions of ${amount} processed on {date}. "
        "I'm initiating a full refund for the duplicate charge of ${amount}, "
        "which should appear on your statement within 3-5 business days. "
        "I've also added a $10 service credit to your account as an apology for the inconvenience. "
        "Your subscription remains active and your billing cycle is unchanged."
    ),
    "refund_request": (
        "I've located your account and reviewed the charge in question. "
        "Based on our refund policy and the circumstances you've described, "
        "I'm approving a refund of ${amount}. "
        "This will be processed within 5-7 business days. "
        "You'll receive a confirmation email at your registered address."
    ),
    "billing_question": (
        "I've reviewed your billing history. Your current plan is {plan} at ${amount}/month. "
        "Your last charge was on {date} and your next billing date is {next_date}. "
        "If you have any questions about specific charges, I'm happy to provide a detailed breakdown."
    ),
    "default": (
        "I've reviewed your billing account thoroughly. "
        "Your account is in good standing with {plan} subscription. "
        "I can see your recent transaction history and everything appears correct. "
        "Please let me know if you'd like clarification on any specific charge."
    ),
}

ORDER_RESPONSES = {
    "lost_package": (
        "I've investigated your order #{order_id} thoroughly. "
        "According to our shipping records, your package was marked as delivered on {date}, "
        "but I understand you haven't received it. "
        "I've filed an investigation with our carrier and initiated a replacement shipment. "
        "Your replacement order will be expedited (2-day shipping) at no additional cost. "
        "You'll receive a new tracking number within 24 hours."
    ),
    "delayed_order": (
        "I've checked your order #{order_id} status. There's been a delay at our {location} "
        "fulfillment center due to high demand. Your package is scheduled to arrive by {date}. "
        "As compensation for the inconvenience, I've applied a 15% discount to your next order. "
        "I'll send you a priority tracking update via email."
    ),
    "return_request": (
        "I've processed your return request for order #{order_id}. "
        "You'll receive a prepaid return label at your email within 2 hours. "
        "Once we receive the item, your refund of ${amount} will be processed within 3-5 business days."
    ),
    "default": (
        "I've looked up your order and can see it's currently {status}. "
        "Your tracking number is {tracking}. "
        "If you're experiencing any issues, I've flagged your order for priority review."
    ),
}

TECHNICAL_RESPONSES = {
    "login_issue": (
        "I've reviewed your account access logs. "
        "It appears there were multiple failed login attempts which triggered our security lockout. "
        "I've reset the lockout and sent a password reset link to your registered email. "
        "The link expires in 24 hours. If you continue having issues, I can set up a temporary access code."
    ),
    "app_error": (
        "Thank you for the detailed description of the error. "
        "This is a known issue affecting a small number of users on version {version}. "
        "Our engineering team released a fix in version {new_version} — please update the app. "
        "As an immediate workaround, clearing your app cache should resolve the issue. "
        "I've flagged your account for a follow-up to ensure the fix worked."
    ),
    "performance": (
        "I can see from our system logs that there was degraded performance affecting your region "
        "between {start_time} and {end_time}. The issue has been resolved. "
        "I've added a 5-day extension to your current billing cycle as compensation."
    ),
    "default": (
        "I've reviewed the technical issue you're experiencing. "
        "Based on the symptoms you described, this appears to be related to a recent platform update. "
        "I've escalated this to our technical team with high priority and they'll be in touch within 2 hours. "
        "In the meantime, please try: clearing your cache, updating the app, and restarting your device."
    ),
}

ACCOUNT_RESPONSES = {
    "suspended": (
        "I've reviewed your account. It was suspended due to a payment processing issue "
        "on {date} — this was not due to any violation on your part. "
        "I've cleared the suspension flag and reactivated your account immediately. "
        "You should regain full access within 5 minutes. I apologize for the inconvenience."
    ),
    "upgrade": (
        "I've reviewed your account and usage patterns. "
        "Based on your current usage, upgrading to {new_plan} would give you {benefits}. "
        "I can process the upgrade now and prorate the cost — you'd pay ${amount} for the remainder of this cycle. "
        "Would you like me to proceed?"
    ),
    "default": (
        "I've reviewed your account details. Your account is currently {status} on the {plan} plan. "
        "All your settings and data are intact. "
        "Please let me know if there's anything specific you'd like me to help with on your account."
    ),
}

ESCALATION_RESPONSES = [
    "I understand this is a frustrating situation, and I want to make sure you get the best possible resolution. "
    "I'm transferring your case to our senior support specialist who has full authority to resolve complex billing matters. "
    "I've prepared a complete handoff summary so you won't need to repeat yourself. "
    "A specialist will contact you within 2 hours.",

    "Given the complexity of your situation, I'm escalating this to our dedicated customer success team. "
    "I've documented everything — your history, what's been tried, and my recommendation for resolution. "
    "You'll be contacted by a senior agent within 1 business hour who can take immediate action.",
]

MULTI_DOMAIN_RESPONSES = (
    "I've completed a thorough investigation across both your billing and order records. "
    "Here's what I found: {billing_finding} Additionally, regarding your order: {order_finding} "
    "I'm addressing both issues simultaneously. {combined_action}"
)

REASONING_STEPS = {
    "billing": [
        "Retrieving customer billing ledger from financial system",
        "Scanning transaction history for anomalies (last 90 days)",
        "Cross-referencing subscription state with charge dates",
        "Checking refund history and dispute flags",
        "Calculating net charges vs. expected amounts",
        "Identifying root cause of billing discrepancy",
        "Determining appropriate resolution action",
    ],
    "order": [
        "Querying order management system for customer's recent orders",
        "Retrieving full shipping timeline and carrier events",
        "Checking fulfillment center logs for processing issues",
        "Verifying delivery confirmation against carrier data",
        "Assessing package status and insurance eligibility",
        "Determining whether replacement or refund is appropriate",
    ],
    "technical": [
        "Checking system incident logs for reported issues",
        "Searching knowledge base for similar error reports",
        "Reviewing customer's account version and platform",
        "Cross-referencing with known bugs in current release",
        "Identifying affected user segment and severity",
        "Formulating resolution path from KB articles",
    ],
    "account": [
        "Retrieving full account history and status flags",
        "Reviewing account activity timeline",
        "Checking for automated flags or security triggers",
        "Verifying tier and plan entitlements",
        "Assessing account health score and churn risk",
        "Determining appropriate corrective action",
    ],
    "classification": [
        "Parsing customer message for intent signals",
        "Scoring against domain keyword vectors (billing/order/technical/account)",
        "Evaluating urgency indicators and sentiment markers",
        "Checking customer history for context",
        "Finalizing intent classification with confidence score",
    ],
    "escalation": [
        "Aggregating confidence scores from all specialist agents",
        "Evaluating against escalation thresholds (confidence < 0.65, or Enterprise tier, or critical urgency)",
        "Reviewing customer sentiment trend over ticket history",
        "Generating structured handoff packet for human agent",
        "Routing to appropriate human queue via orchestration layer",
    ],
}


def _make_pseudo_embedding(text: str, dim: int = 384) -> list[float]:
    """Deterministic pseudo-embedding via hashing. Good enough for demo similarity matching."""
    h = hashlib.sha256(text.encode()).digest()
    seed = int.from_bytes(h[:4], "big")
    result = []
    for i in range(dim):
        seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
        val = (seed / 0xFFFFFFFF) * 2 - 1  # [-1, 1]
        result.append(round(val, 6))
    # Normalize
    mag = math.sqrt(sum(x * x for x in result))
    return [round(x / mag, 6) for x in result]


class MockLLMProvider(LLMProvider):
    """
    Intelligent deterministic mock that produces realistic, domain-aware reasoning.
    No API key required. Perfect for the prototype demo.
    """

    async def classify(self, text: str, context: dict[str, Any] | None = None) -> ClassificationResult:
        intent, confidence = _classify_intent(text)
        urgency = _classify_urgency(text)
        sentiment = _classify_sentiment(text)

        intent_descriptions = {
            "billing": "billing or payment issue",
            "order": "order or delivery issue",
            "technical": "technical or software issue",
            "account": "account management issue",
            "multi": "multi-domain issue spanning billing and order systems",
            "unknown": "unclassified issue requiring general support",
        }

        reasoning = (
            f"Analyzed message for domain signals. "
            f"Detected {intent_descriptions.get(intent, intent)} with {confidence:.0%} confidence. "
            f"Urgency assessed as '{urgency}' based on language patterns. "
            f"Customer sentiment appears '{sentiment}'."
        )

        return ClassificationResult(
            intent=intent,
            urgency=urgency,
            sentiment=sentiment,
            confidence=confidence,
            reasoning=reasoning,
        )

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> CompletionResult:
        ctx = context or {}
        task_type = ctx.get("task_type", "general")
        domain = ctx.get("domain", "billing")

        # Select appropriate reasoning steps
        steps = REASONING_STEPS.get(domain, REASONING_STEPS["billing"])

        if task_type == "customer_response":
            content, confidence = self._generate_customer_response(ctx)
        elif task_type == "root_cause_analysis":
            content, confidence = self._generate_root_cause(ctx)
        elif task_type == "handoff_packet":
            content, confidence = self._generate_handoff(ctx)
        elif task_type == "cluster_narrative":
            content, confidence = self._generate_cluster_narrative(ctx)
        elif task_type == "escalation_justification":
            content, confidence = self._generate_escalation_justification(ctx)
        else:
            content = "Analysis complete. Please see the structured findings above."
            confidence = 0.75

        return CompletionResult(
            content=content,
            reasoning_steps=steps[:5],
            confidence=confidence,
            citations=ctx.get("citation_ids", []),
        )

    def _generate_customer_response(self, ctx: dict) -> tuple[str, float]:
        domain = ctx.get("domain", "billing")
        findings = ctx.get("findings", {})
        customer = ctx.get("customer", {})
        tier = customer.get("tier", "Standard")

        tier_prefix = ""
        if tier == "Enterprise":
            tier_prefix = "As a valued Enterprise customer, "
        elif tier == "Premium":
            tier_prefix = "As a Premium member, "

        if domain == "billing":
            sub_type = ctx.get("sub_type", "default")
            template = BILLING_RESPONSES.get(sub_type, BILLING_RESPONSES["default"])
            content = tier_prefix + template.format(
                amount=findings.get("amount", "29.99"),
                date=findings.get("date", "September 1, 2026"),
                plan=findings.get("plan", "Premium"),
                next_date=findings.get("next_date", "October 1, 2026"),
            )
            return content, 0.88

        elif domain == "order":
            sub_type = ctx.get("sub_type", "default")
            template = ORDER_RESPONSES.get(sub_type, ORDER_RESPONSES["default"])
            content = tier_prefix + template.format(
                order_id=findings.get("order_id", "ORD-2026-001"),
                date=findings.get("date", "September 10, 2026"),
                location=findings.get("location", "Chicago"),
                amount=findings.get("amount", "89.99"),
                tracking=findings.get("tracking", "1Z999AA10123456784"),
                status=findings.get("status", "in transit"),
            )
            return content, 0.85

        elif domain == "technical":
            sub_type = ctx.get("sub_type", "default")
            template = TECHNICAL_RESPONSES.get(sub_type, TECHNICAL_RESPONSES["default"])
            content = tier_prefix + template.format(
                version=findings.get("version", "3.2.1"),
                new_version=findings.get("new_version", "3.2.2"),
                start_time=findings.get("start_time", "2:00 PM UTC"),
                end_time=findings.get("end_time", "3:45 PM UTC"),
            )
            return content, 0.82

        elif domain == "account":
            sub_type = ctx.get("sub_type", "default")
            template = ACCOUNT_RESPONSES.get(sub_type, ACCOUNT_RESPONSES["default"])
            content = tier_prefix + template.format(
                date=findings.get("date", "September 5, 2026"),
                plan=findings.get("plan", "Premium"),
                status=findings.get("status", "active"),
                new_plan=findings.get("new_plan", "Enterprise"),
                benefits=findings.get("benefits", "unlimited API calls and priority support"),
                amount=findings.get("amount", "49.99"),
            )
            return content, 0.83

        elif domain == "multi":
            content = (
                f"{tier_prefix}I've completed a thorough cross-system investigation. "
                "My billing analysis found that {billing_issue}. Simultaneously, your order investigation revealed {order_issue}. "
                "I'm resolving both issues right now: {resolution}."
            ).format(
                billing_issue=findings.get("billing_summary", "your account is in good standing"),
                order_issue=findings.get("order_summary", "your package is being tracked"),
                resolution=findings.get("resolution", "both matters are being addressed with priority"),
            )
            return content, 0.80

        return "I've investigated your issue thoroughly and am working on a resolution.", 0.70

    def _generate_root_cause(self, ctx: dict) -> tuple[str, float]:
        domain = ctx.get("domain", "billing")
        raw_data = ctx.get("raw_data", {})

        analyses = {
            "billing": (
                "Root cause identified: Duplicate charge event due to payment processor retry logic "
                "triggering twice on a network timeout. The subscription renewal webhook was received twice "
                "within a 300ms window, causing the billing system to create two identical transactions. "
                "This is a known edge case in our payment gateway integration (Bug #BG-4471). "
                "Action: Issue full refund for duplicate transaction; flag account for enhanced billing protection.",
                0.91,
            ),
            "order": (
                "Root cause identified: Package marked as 'delivered' by carrier scan at distribution hub "
                "rather than final delivery address. Carrier GPS data shows last scan at regional hub 2.3 miles "
                "from customer address. This is a carrier-side misdelivery or lost-in-transit scenario. "
                "Action: Open carrier investigation case #CI-2026-8834; initiate replacement shipment under insurance coverage.",
                0.87,
            ),
            "technical": (
                "Root cause identified: Memory leak in authentication token refresh cycle introduced in v3.2.1 "
                "(deployed September 8, 2026). Affects users with sessions older than 7 days. "
                "The token validation cache exceeds allocation limit causing forced logout loop. "
                "Fix deployed in v3.2.2 (September 12, 2026). "
                "Action: Force session refresh for affected account; send update notification.",
                0.89,
            ),
            "account": (
                "Root cause identified: Account suspension triggered by automated fraud detection system "
                "flagging a login from a new IP geolocation (VPN usage). The security score threshold was "
                "exceeded due to 3 simultaneous risk signals: new device, new location, unusual session time. "
                "False positive — no actual fraud detected. "
                "Action: Clear suspension, whitelist current IP range, send security review summary.",
                0.85,
            ),
        }
        return analyses.get(domain, ("Issue investigated. Root cause under analysis.", 0.65))

    def _generate_handoff(self, ctx: dict) -> tuple[str, float]:
        findings = ctx.get("findings_summary", [])
        customer = ctx.get("customer", {})
        content = (
            f"ESCALATION HANDOFF — Ticket requires senior agent review.\n\n"
            f"Customer: {customer.get('name', 'Customer')} ({customer.get('tier', 'Standard')} tier)\n"
            f"Issue: {ctx.get('issue_summary', 'Complex multi-system issue')}\n\n"
            f"Investigation completed: {', '.join(ctx.get('systems_checked', ['CRM', 'Billing']))}\n"
            f"Key findings: {'; '.join(findings[:3]) if findings else 'See attached agent findings'}\n\n"
            f"Recommended action: {ctx.get('recommended_action', 'Full account review and compensation offer')}\n"
            f"Customer sentiment: {ctx.get('sentiment', 'negative')} — handle with priority empathy."
        )
        return content, 0.78

    def _generate_cluster_narrative(self, ctx: dict) -> tuple[str, float]:
        cluster = ctx.get("cluster_label", "Billing Disputes")
        count = ctx.get("ticket_count", 0)
        trend = ctx.get("trend", "rising")
        content = (
            f"The '{cluster}' cluster has seen {count} tickets {'and is trending upward' if trend == 'rising' else 'with stable volume'} "
            f"over the past 30 days. This pattern suggests a systemic issue rather than isolated incidents. "
            f"Primary driver: {'payment processor reliability issues during peak hours' if 'Billing' in cluster else 'shipping carrier delays in the midwest region'}. "
            f"Recommended action: {'Review payment gateway SLA and implement retry deduplication' if 'Billing' in cluster else 'Diversify carrier partnerships and improve delivery ETA accuracy'}."
        )
        return content, 0.80

    def _generate_escalation_justification(self, ctx: dict) -> tuple[str, float]:
        confidence = ctx.get("agent_confidence", 0.55)
        reasons = ctx.get("escalation_reasons", [])
        content = (
            f"Escalation justified. Combined agent confidence: {confidence:.0%} (threshold: 65%). "
            f"Escalation triggers: {'; '.join(reasons) if reasons else 'low confidence across multiple domains'}. "
            f"Human review required to apply manual compensation, override billing system limits, "
            f"or access carrier dispute portal with agent credentials."
        )
        return content, 0.75

    async def embed(self, text: str) -> EmbeddingResult:
        return EmbeddingResult(
            embedding=_make_pseudo_embedding(text),
            model="mock-minilm-l6",
        )
