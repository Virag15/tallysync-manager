"""
TallySync Manager — SSE Events Manager
Manages server-sent event queues per company for real-time frontend updates.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, List

logger = logging.getLogger("tallysync.events")


class EventsManager:
    """
    Broadcast async events to all connected SSE clients.
    Each browser tab that opens /api/events registers its own Queue.
    """

    def __init__(self):
        # company_id (or "all") → list of asyncio queues (one per SSE client)
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}

    def subscribe(self, channel: str = "all") -> asyncio.Queue[dict]:
        q: asyncio.Queue[dict] = asyncio.Queue()
        self._subscribers.setdefault(channel, []).append(q)
        logger.debug("SSE client subscribed to channel '%s' (total: %d)", channel, len(self._subscribers[channel]))
        return q

    def unsubscribe(self, channel: str, q: asyncio.Queue) -> None:
        if channel in self._subscribers:
            try:
                self._subscribers[channel].remove(q)
            except ValueError:
                pass

    async def broadcast(self, event_name: str, data: dict, company_id: int | None = None) -> None:
        """
        Broadcast an event to:
          - all subscribers on the specific company channel (if company_id given)
          - all subscribers on the "all" channel
        """
        payload = {"event": event_name, "data": data}
        channels = ["all"]
        if company_id is not None:
            channels.append(str(company_id))

        for channel in channels:
            queues = list(self._subscribers.get(channel, []))
            for q in queues:
                try:
                    await q.put(payload)
                except Exception as exc:
                    logger.warning("Could not put event on queue: %s", exc)

        logger.debug("Broadcasted '%s' to %d channel(s)", event_name, len(channels))


# ─── Module-level singleton ───────────────────────────────────────────────────
events_manager = EventsManager()
