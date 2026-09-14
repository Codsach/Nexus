"""
In-process async event bus for the reasoning trace.
Each ticket gets its own asyncio.Queue. The SSE endpoint subscribes and drains it.
"""
from __future__ import annotations
import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator

from app.shared.schemas.models import TraceEvent, TraceEventType


_queues: dict[str, list[asyncio.Queue]] = {}


def _get_queues(ticket_id: str) -> list[asyncio.Queue]:
    return _queues.setdefault(ticket_id, [])


async def emit(event: TraceEvent) -> None:
    """Publish a trace event to all subscribers for this ticket."""
    queues = _get_queues(event.ticket_id)
    for q in queues:
        await q.put(event)


async def subscribe(ticket_id: str) -> AsyncGenerator[TraceEvent, None]:
    """Subscribe to trace events for a ticket via async generator (used by SSE endpoint)."""
    q: asyncio.Queue = asyncio.Queue()
    _get_queues(ticket_id).append(q)
    try:
        while True:
            event = await asyncio.wait_for(q.get(), timeout=30.0)
            if event is None:  # sentinel: stream closed
                break
            yield event
    except asyncio.TimeoutError:
        pass  # client will reconnect
    finally:
        queues = _get_queues(ticket_id)
        if q in queues:
            queues.remove(q)


async def close_stream(ticket_id: str) -> None:
    """Send sentinel to all subscribers to signal end of stream."""
    queues = _get_queues(ticket_id)
    for q in queues:
        await q.put(None)
    _queues.pop(ticket_id, None)


def make_event(
    ticket_id: str,
    event_type: TraceEventType,
    message: str,
    agent_name: str | None = None,
    **payload,
) -> TraceEvent:
    return TraceEvent(
        ticket_id=ticket_id,
        event_type=event_type,
        message=message,
        agent_name=agent_name,
        payload=payload,
    )
