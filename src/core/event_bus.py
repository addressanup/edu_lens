"""
Event Bus for EduLens Inter-Component Communication

Provides a lightweight publish/subscribe mechanism for decoupled
communication between vision, audio, AI, and integration components.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Coroutine, TypeVar
from uuid import uuid4

logger = logging.getLogger(__name__)

T = TypeVar("T")


class EventType(Enum):
    """Core event types in the EduLens system."""

    # Vision events
    VISION_FRAME_CAPTURED = auto()
    VISION_TEXT_DETECTED = auto()
    VISION_DOCUMENT_RECOGNIZED = auto()
    VISION_PROBLEM_SEGMENTED = auto()

    # Audio events
    AUDIO_WAKE_WORD_DETECTED = auto()
    AUDIO_SPEECH_STARTED = auto()
    AUDIO_SPEECH_ENDED = auto()
    AUDIO_TRANSCRIPTION_READY = auto()
    AUDIO_TTS_STARTED = auto()
    AUDIO_TTS_COMPLETED = auto()

    # AI events
    AI_QUERY_RECEIVED = auto()
    AI_RESPONSE_GENERATED = auto()
    AI_CONTEXT_UPDATED = auto()
    AI_ERROR = auto()

    # System events
    SYSTEM_READY = auto()
    SYSTEM_ERROR = auto()
    SYSTEM_SHUTDOWN = auto()
    SYSTEM_LOW_BATTERY = auto()

    # Session events
    SESSION_STARTED = auto()
    SESSION_ENDED = auto()
    SESSION_PROBLEM_STARTED = auto()
    SESSION_PROBLEM_COMPLETED = auto()

    # Privacy events
    PRIVACY_CONSENT_REQUIRED = auto()
    PRIVACY_DATA_PURGED = auto()


@dataclass
class Event:
    """Represents an event in the EduLens system."""

    event_type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.name,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }


# Type alias for event handlers
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]
SyncEventHandler = Callable[[Event], None]


class EventBus:
    """
    Asynchronous event bus for EduLens component communication.

    Supports both async and sync handlers, with priority ordering
    and optional filtering.
    """

    def __init__(self) -> None:
        self._async_handlers: dict[EventType, list[tuple[int, EventHandler]]] = defaultdict(list)
        self._sync_handlers: dict[EventType, list[tuple[int, SyncEventHandler]]] = defaultdict(list)
        self._event_history: list[Event] = []
        self._history_limit: int = 1000
        self._is_running: bool = False
        self._event_queue: asyncio.Queue[Event] = asyncio.Queue()

    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
        priority: int = 0,
    ) -> None:
        """
        Subscribe an async handler to an event type.

        Args:
            event_type: The type of event to subscribe to
            handler: Async function to call when event occurs
            priority: Higher priority handlers are called first (default 0)
        """
        self._async_handlers[event_type].append((priority, handler))
        self._async_handlers[event_type].sort(key=lambda x: -x[0])
        logger.debug(f"Subscribed handler to {event_type.name}")

    def subscribe_sync(
        self,
        event_type: EventType,
        handler: SyncEventHandler,
        priority: int = 0,
    ) -> None:
        """Subscribe a synchronous handler to an event type."""
        self._sync_handlers[event_type].append((priority, handler))
        self._sync_handlers[event_type].sort(key=lambda x: -x[0])

    def unsubscribe(
        self,
        event_type: EventType,
        handler: EventHandler | SyncEventHandler,
    ) -> None:
        """Remove a handler from an event type."""
        self._async_handlers[event_type] = [
            (p, h) for p, h in self._async_handlers[event_type] if h != handler
        ]
        self._sync_handlers[event_type] = [
            (p, h) for p, h in self._sync_handlers[event_type] if h != handler
        ]

    async def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribed handlers.

        Args:
            event: The event to publish
        """
        logger.debug(f"Publishing event: {event.event_type.name}")

        # Store in history (with limit)
        self._event_history.append(event)
        if len(self._event_history) > self._history_limit:
            self._event_history = self._event_history[-self._history_limit :]

        # Call sync handlers first (in priority order)
        for _, handler in self._sync_handlers[event.event_type]:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Sync handler error for {event.event_type.name}: {e}")

        # Call async handlers (in priority order)
        for _, handler in self._async_handlers[event.event_type]:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Async handler error for {event.event_type.name}: {e}")

    def publish_sync(self, event: Event) -> None:
        """Publish an event synchronously (only calls sync handlers)."""
        logger.debug(f"Publishing sync event: {event.event_type.name}")

        self._event_history.append(event)
        if len(self._event_history) > self._history_limit:
            self._event_history = self._event_history[-self._history_limit :]

        for _, handler in self._sync_handlers[event.event_type]:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Sync handler error for {event.event_type.name}: {e}")

    async def publish_queued(self, event: Event) -> None:
        """Add event to queue for background processing."""
        await self._event_queue.put(event)

    async def start_processing(self) -> None:
        """Start processing queued events."""
        self._is_running = True
        while self._is_running:
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self.publish(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Event processing error: {e}")

    def stop_processing(self) -> None:
        """Stop processing queued events."""
        self._is_running = False

    def get_history(
        self,
        event_type: EventType | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """
        Get recent event history.

        Args:
            event_type: Filter by event type (optional)
            limit: Maximum number of events to return

        Returns:
            List of recent events
        """
        history = self._event_history
        if event_type:
            history = [e for e in history if e.event_type == event_type]
        return history[-limit:]

    def clear_history(self) -> None:
        """Clear the event history."""
        self._event_history = []


# Global event bus instance
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def create_event(
    event_type: EventType,
    source: str,
    **payload: Any,
) -> Event:
    """
    Factory function to create an event.

    Args:
        event_type: The type of event
        source: Component that created the event
        **payload: Event data as keyword arguments

    Returns:
        A new Event instance
    """
    return Event(
        event_type=event_type,
        source=source,
        payload=payload,
    )
