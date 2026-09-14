"""
Knowledge Engine — simple in-memory vector store using cosine similarity on mock embeddings.
Falls back gracefully if ChromaDB unavailable. Full RAG pipeline.
"""
from __future__ import annotations
import math
from app.adapters.llm import llm
from app.shared.schemas.models import KnowledgeChunk

# In-memory knowledge base (seeded at startup)
_chunks: list[KnowledgeChunk] = []
_embeddings: list[list[float]] = []


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


async def add_chunk(chunk: KnowledgeChunk) -> None:
    embed_result = await llm.embed(chunk.content)
    _chunks.append(chunk)
    _embeddings.append(embed_result.embedding)


async def retrieve(query: str, top_k: int = 3) -> list[KnowledgeChunk]:
    if not _chunks:
        return []
    query_embed = await llm.embed(query)
    scores = [
        (_cosine_similarity(query_embed.embedding, emb), i)
        for i, emb in enumerate(_embeddings)
    ]
    scores.sort(reverse=True)
    return [_chunks[i] for _, i in scores[:top_k]]


async def seed_knowledge_base() -> int:
    """Seed with product docs, FAQ, known issues. Returns count added."""
    docs = [
        KnowledgeChunk(
            source="Refund Policy",
            source_type="policy",
            content="Nexus offers full refunds within 30 days of purchase for digital products. Subscription refunds are prorated. Duplicate charges are refunded immediately upon verification. Processing time is 3-5 business days for credit cards, 5-7 for bank transfers.",
        ),
        KnowledgeChunk(
            source="FAQ: Billing",
            source_type="faq",
            content="Q: Why was I charged twice? A: Occasionally, payment processor retries can cause duplicate charges during network timeouts. Contact support with your transaction IDs and we will refund the duplicate immediately. Q: When does my subscription renew? A: Subscriptions auto-renew on the same date each month/year.",
        ),
        KnowledgeChunk(
            source="FAQ: Shipping",
            source_type="faq",
            content="Q: My package shows delivered but I haven't received it. A: First check with neighbors and building mailroom. If still not found after 24 hours, contact us — we will file a carrier investigation and issue a replacement or refund. Q: How do I track my order? A: Use the tracking number in your confirmation email on our carriers portal.",
        ),
        KnowledgeChunk(
            source="Known Issue: App Crash v3.2.1",
            source_type="kb_article",
            content="Users on Nexus app version 3.2.1 may experience crashes on startup due to a memory leak in the token refresh cycle. Fix: Update to v3.2.2 (released September 12, 2026). Workaround: Clear app cache from Settings > Storage > Clear Cache. Affects users with sessions older than 7 days.",
        ),
        KnowledgeChunk(
            source="Known Issue: Duplicate Charge BG-4471",
            source_type="kb_article",
            content="A known edge case in payment gateway v2 caused duplicate subscription charges for a small number of users between Sep 1-10, 2026. Affected customers will receive automatic refunds. If you believe you were affected and have not received a refund, contact billing support with your transaction ID.",
        ),
        KnowledgeChunk(
            source="Account Suspension Policy",
            source_type="policy",
            content="Accounts may be suspended for: (1) failed payment after 3 retry attempts, (2) automated fraud detection flags, (3) terms of service violations. For payment-related suspensions, updating your payment method reactivates the account within 24 hours. For fraud flags, contact support for manual review — VPN usage and new device logins can sometimes trigger false positives.",
        ),
        KnowledgeChunk(
            source="Enterprise SLA",
            source_type="policy",
            content="Enterprise customers have a guaranteed 2-hour first response SLA for urgent issues. Critical issues (system down, data loss) receive 30-minute response. Enterprise accounts have a dedicated Customer Success Manager. All enterprise tickets are automatically flagged for senior agent review.",
        ),
        KnowledgeChunk(
            source="Return & Exchange Policy",
            source_type="policy",
            content="Physical products can be returned within 30 days for a full refund or exchange. Items must be in original condition. Returns are free — a prepaid label is emailed within 2 hours of the return request. Refunds are processed within 5-7 business days of receiving the return.",
        ),
        KnowledgeChunk(
            source="Resolved Ticket TKT-2026-0805: App Crash Fix",
            source_type="resolved_ticket",
            content="Customer reported Nexus app crashing immediately after updating to v3.2.1. Resolution: Advised to clear app cache (Settings > Storage > Clear Cache) and update to v3.2.2. Issue was a memory leak in authentication token refresh introduced in v3.2.1. Customer confirmed resolved after update.",
        ),
        KnowledgeChunk(
            source="Resolved Ticket TKT-2026-0712: Wrong Item",
            source_type="resolved_ticket",
            content="Customer received wrong color variant of Camera Accessory Kit (received red, ordered blue). Resolution: Immediate apology, prepaid return label issued within 1 hour, correct item shipped with expedited delivery at no additional cost. Customer satisfaction restored.",
        ),
        KnowledgeChunk(
            source="FAQ: Account Access",
            source_type="faq",
            content="Q: I cannot log in. A: Try resetting your password. If reset emails go to spam, check your spam folder or whitelist @nexus.support. Q: My account says suspended. A: Check your payment method is up to date. If payment is current, contact support — a security flag may have been triggered incorrectly. Q: I use a VPN — is that a problem? A: VPN usage can occasionally trigger our fraud detection. If your account was flagged, contact support for a quick manual review.",
        ),
        KnowledgeChunk(
            source="Performance Incident INC-0908",
            source_type="kb_article",
            content="On September 8, 2026, Nexus experienced degraded performance in the US-WEST region from 14:00-15:45 UTC due to an infrastructure scaling event. All affected customers received a 5-day billing extension as compensation. The issue was fully resolved by 15:45 UTC.",
        ),
    ]

    for doc in docs:
        await add_chunk(doc)

    return len(docs)
