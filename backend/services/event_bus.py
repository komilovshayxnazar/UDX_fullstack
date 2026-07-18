"""
event_bus.py — In-process async event bus.

Usage:
    # publish
    await event_bus.publish("payment.completed", {"user_id": ..., "amount": ...})

    # subscribe (at startup)
    @event_bus.on("payment.completed")
    async def handle_payment(payload: dict): ...

Architecture note:
    This is an in-process implementation suitable for a monolith.
    To migrate to microservices, replace publish() with a message broker
    call (RabbitMQ / Kafka / Redis Streams) — subscribers stay unchanged.
"""

import asyncio
import logging
from collections import defaultdict
from typing import Callable, Any

logger = logging.getLogger("event_bus")


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def on(self, event: str):
        """Decorator to register an async handler for an event."""
        def decorator(fn: Callable):
            self._handlers[event].append(fn)
            return fn
        return decorator

    async def publish(self, event: str, payload: dict):
        """Fire all handlers for the event. Errors are logged, not raised."""
        handlers = self._handlers.get(event, [])
        if not handlers:
            return
        tasks = [asyncio.create_task(self._safe_call(h, payload)) for h in handlers]
        await asyncio.gather(*tasks)

    @staticmethod
    async def _safe_call(handler: Callable, payload: dict):
        try:
            await handler(payload)
        except Exception as e:
            logger.error(f"Event handler {handler.__name__} failed: {e}")


event_bus = EventBus()
