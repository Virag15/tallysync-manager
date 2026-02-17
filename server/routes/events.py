"""
TallySync Manager — SSE Events Route
Streams real-time sync events to connected browser clients.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Request, Query
from sse_starlette.sse import EventSourceResponse

from events_manager import events_manager

logger = logging.getLogger("tallysync.routes.events")
router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("")
async def sse_stream(
    request: Request,
    company_id: Optional[str] = Query(None, description="Subscribe to a specific company, or 'all'"),
):
    """
    SSE endpoint. Browser keeps this connection open.
    Receives 'sync_complete' and 'sync_error' events.
    """
    channel = str(company_id) if company_id else "all"
    queue = events_manager.subscribe(channel)
    logger.debug("SSE client connected on channel '%s'", channel)

    async def stream():
        try:
            # Send an initial heartbeat so the browser knows we're connected
            yield {"event": "connected", "data": json.dumps({"channel": channel})}
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=25)
                    yield {
                        "event": payload["event"],
                        "data":  json.dumps(payload["data"]),
                    }
                except asyncio.TimeoutError:
                    # Send a keep-alive comment every 25s
                    yield {"event": "heartbeat", "data": "{}"}
        except asyncio.CancelledError:
            pass
        finally:
            events_manager.unsubscribe(channel, queue)
            logger.debug("SSE client disconnected from channel '%s'", channel)

    return EventSourceResponse(stream())
