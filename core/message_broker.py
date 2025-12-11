"""
Message Broker for Claude Agents Orchestration System.

This module provides a priority-based message queue system for inter-agent
communication with retry logic, dead letter queue, and delivery tracking.
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum, IntEnum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict

import redis.asyncio as redis
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)


class MessagePriority(IntEnum):
    """Message priority levels (lower number = higher priority)."""

    BLOCKING = 0  # Must be processed immediately
    HIGH = 1  # Process as soon as possible
    NORMAL = 2  # Standard priority
    INFO = 3  # Informational, process when convenient


class MessageStatus(str, Enum):
    """Message delivery status."""

    PENDING = "pending"
    DELIVERED = "delivered"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    EXPIRED = "expired"


@dataclass
class BrokerMessage:
    """
    Internal message structure for the broker.

    Attributes:
        id: Unique message identifier
        from_agent: Sending agent name
        to_agent: Receiving agent name
        message_type: Type of message
        priority: Message priority level
        payload: Message content
        created_at: Creation timestamp
        expires_at: Expiration timestamp (optional)
        retry_count: Number of delivery attempts
        max_retries: Maximum retry attempts
        status: Current message status
        metadata: Additional metadata
    """

    id: str
    from_agent: str
    to_agent: str
    message_type: str
    priority: MessagePriority
    payload: Dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    status: MessageStatus = MessageStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["priority"] = self.priority.value
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        if self.expires_at:
            data["expires_at"] = self.expires_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BrokerMessage":
        """Create from dictionary."""
        data = data.copy()
        data["priority"] = MessagePriority(data["priority"])
        data["status"] = MessageStatus(data["status"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("expires_at"):
            data["expires_at"] = datetime.fromisoformat(data["expires_at"])
        return cls(**data)

    def is_expired(self) -> bool:
        """Check if message has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at


@dataclass
class QueueStats:
    """Statistics for a message queue."""

    total_messages: int = 0
    pending_messages: int = 0
    delivered_messages: int = 0
    failed_messages: int = 0
    dead_letter_messages: int = 0
    average_latency_ms: float = 0.0
    messages_per_second: float = 0.0


class MessageBroker:
    """
    Priority-based message broker for inter-agent communication.

    Features:
    - Priority queues (BLOCKING, HIGH, NORMAL, INFO)
    - Async send/receive with retry logic
    - Dead letter queue for failed messages
    - Message tracking and delivery confirmation
    - Redis-backed for persistence and distribution

    Example:
        broker = MessageBroker(redis_url="redis://localhost:6379")
        await broker.connect()

        # Send message
        await broker.send_message(
            from_agent="ConceptDesigner",
            to_agent="BackendEngineer",
            message_type="task_assignment",
            payload={"task": "Generate API endpoints"},
            priority=MessagePriority.HIGH
        )

        # Receive message
        message = await broker.receive_message(agent="BackendEngineer")
        await broker.acknowledge(message.id)
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        queue_prefix: str = "cao:queue:",
        max_queue_size: int = 10000,
        default_ttl: int = 3600,
    ):
        """
        Initialize the message broker.

        Args:
            redis_url: Redis connection URL
            queue_prefix: Prefix for Redis queue keys
            max_queue_size: Maximum messages per queue
            default_ttl: Default message TTL in seconds
        """
        self._redis_url = redis_url
        self._queue_prefix = queue_prefix
        self._max_queue_size = max_queue_size
        self._default_ttl = default_ttl

        self._redis: Optional[redis.Redis] = None
        self._connected = False

        # Local tracking
        self._processing_messages: Dict[str, BrokerMessage] = {}
        self._message_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._stats: Dict[str, QueueStats] = defaultdict(QueueStats)

        # Dead letter queue
        self._dlq_key = f"{queue_prefix}dead_letter"

    async def connect(self) -> None:
        """Establish connection to Redis."""
        self._redis = redis.from_url(
            self._redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        try:
            await self._redis.ping()
            self._connected = True
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Redis: {e}")

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._connected = False

    def _get_queue_key(self, agent: str, priority: MessagePriority) -> str:
        """Get Redis key for agent's priority queue."""
        return f"{self._queue_prefix}{agent}:{priority.name.lower()}"

    def _get_all_queue_keys(self, agent: str) -> List[str]:
        """Get all queue keys for an agent in priority order."""
        return [
            self._get_queue_key(agent, MessagePriority.BLOCKING),
            self._get_queue_key(agent, MessagePriority.HIGH),
            self._get_queue_key(agent, MessagePriority.NORMAL),
            self._get_queue_key(agent, MessagePriority.INFO),
        ]

    async def send_message(
        self,
        from_agent: str,
        to_agent: str,
        message_type: str,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        expires_in: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Send a message to an agent.

        Args:
            from_agent: Sending agent name
            to_agent: Receiving agent name
            message_type: Type of message
            payload: Message content
            priority: Message priority
            expires_in: Seconds until expiration (None = default TTL)
            metadata: Additional metadata

        Returns:
            Message ID
        """
        if not self._connected:
            raise RuntimeError("Broker not connected")

        message_id = str(uuid.uuid4())
        expires_at = None
        if expires_in is not None:
            expires_at = datetime.now(timezone.utc) + \
                __import__("datetime").timedelta(seconds=expires_in)
        elif self._default_ttl:
            expires_at = datetime.now(timezone.utc) + \
                __import__("datetime").timedelta(seconds=self._default_ttl)

        message = BrokerMessage(
            id=message_id,
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            priority=priority,
            payload=payload,
            expires_at=expires_at,
            metadata=metadata or {},
        )

        queue_key = self._get_queue_key(to_agent, priority)
        message_data = json.dumps(message.to_dict())

        # Add to queue with score based on timestamp (for ordering)
        score = time.time()
        await self._redis.zadd(queue_key, {message_data: score})

        # Enforce max queue size
        queue_size = await self._redis.zcard(queue_key)
        if queue_size > self._max_queue_size:
            # Remove oldest messages
            await self._redis.zremrangebyrank(
                queue_key, 0, queue_size - self._max_queue_size - 1
            )

        # Update stats
        self._stats[to_agent].total_messages += 1
        self._stats[to_agent].pending_messages += 1

        return message_id

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(ConnectionError),
    )
    async def send_with_retry(
        self,
        from_agent: str,
        to_agent: str,
        message_type: str,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.HIGH,
    ) -> str:
        """
        Send message with automatic retry on failure.

        Uses exponential backoff for retries.
        """
        return await self.send_message(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            payload=payload,
            priority=priority,
        )

    async def receive_message(
        self,
        agent: str,
        timeout: float = 0,
        priorities: Optional[List[MessagePriority]] = None,
    ) -> Optional[BrokerMessage]:
        """
        Receive the next message for an agent.

        Messages are returned in priority order (BLOCKING first).

        Args:
            agent: Agent name to receive for
            timeout: Wait timeout in seconds (0 = non-blocking)
            priorities: Specific priorities to check (None = all)

        Returns:
            Next message or None if no messages available
        """
        if not self._connected:
            raise RuntimeError("Broker not connected")

        if priorities:
            queue_keys = [self._get_queue_key(agent, p) for p in priorities]
        else:
            queue_keys = self._get_all_queue_keys(agent)

        # Check each priority queue in order
        for queue_key in queue_keys:
            # Get oldest message (lowest score)
            result = await self._redis.zrange(
                queue_key, 0, 0, withscores=True
            )

            if result:
                message_data, score = result[0]
                message = BrokerMessage.from_dict(json.loads(message_data))

                # Check if expired
                if message.is_expired():
                    await self._redis.zrem(queue_key, message_data)
                    message.status = MessageStatus.EXPIRED
                    await self._move_to_dlq(message, "Message expired")
                    continue

                # Remove from queue and mark as processing
                await self._redis.zrem(queue_key, message_data)
                message.status = MessageStatus.PROCESSING
                self._processing_messages[message.id] = message

                self._stats[agent].pending_messages -= 1

                return message

        # No messages found, optionally wait
        if timeout > 0:
            await asyncio.sleep(min(timeout, 1.0))
            return await self.receive_message(agent, timeout - 1.0, priorities)

        return None

    async def acknowledge(self, message_id: str) -> bool:
        """
        Acknowledge successful message processing.

        Args:
            message_id: ID of message to acknowledge

        Returns:
            True if acknowledged, False if message not found
        """
        if message_id not in self._processing_messages:
            return False

        message = self._processing_messages.pop(message_id)
        message.status = MessageStatus.COMPLETED

        self._stats[message.to_agent].delivered_messages += 1

        return True

    async def reject(
        self,
        message_id: str,
        reason: str = "",
        requeue: bool = True,
    ) -> bool:
        """
        Reject a message (mark as failed).

        Args:
            message_id: ID of message to reject
            reason: Reason for rejection
            requeue: Whether to requeue for retry

        Returns:
            True if rejected, False if message not found
        """
        if message_id not in self._processing_messages:
            return False

        message = self._processing_messages.pop(message_id)
        message.retry_count += 1
        message.metadata["last_rejection_reason"] = reason

        if requeue and message.retry_count < message.max_retries:
            # Requeue with lower priority
            new_priority = min(message.priority + 1, MessagePriority.INFO)
            message.priority = MessagePriority(new_priority)
            message.status = MessageStatus.PENDING

            queue_key = self._get_queue_key(message.to_agent, message.priority)
            await self._redis.zadd(
                queue_key,
                {json.dumps(message.to_dict()): time.time()}
            )
            self._stats[message.to_agent].pending_messages += 1
        else:
            # Move to dead letter queue
            message.status = MessageStatus.DEAD_LETTER
            await self._move_to_dlq(message, reason)
            self._stats[message.to_agent].failed_messages += 1

        return True

    async def _move_to_dlq(self, message: BrokerMessage, reason: str) -> None:
        """Move a message to the dead letter queue."""
        message.status = MessageStatus.DEAD_LETTER
        message.metadata["dlq_reason"] = reason
        message.metadata["dlq_timestamp"] = datetime.now(timezone.utc).isoformat()

        await self._redis.zadd(
            self._dlq_key,
            {json.dumps(message.to_dict()): time.time()}
        )
        self._stats[message.to_agent].dead_letter_messages += 1

    async def get_dlq_messages(
        self,
        limit: int = 100,
        agent: Optional[str] = None,
    ) -> List[BrokerMessage]:
        """
        Get messages from the dead letter queue.

        Args:
            limit: Maximum messages to return
            agent: Filter by target agent (optional)

        Returns:
            List of dead letter messages
        """
        result = await self._redis.zrange(self._dlq_key, 0, limit - 1)

        messages = []
        for data in result:
            message = BrokerMessage.from_dict(json.loads(data))
            if agent is None or message.to_agent == agent:
                messages.append(message)

        return messages

    async def reprocess_dlq_message(self, message_id: str) -> bool:
        """
        Move a message from DLQ back to the main queue.

        Args:
            message_id: ID of message to reprocess

        Returns:
            True if requeued, False if not found
        """
        # Find message in DLQ
        result = await self._redis.zrange(self._dlq_key, 0, -1)

        for data in result:
            message = BrokerMessage.from_dict(json.loads(data))
            if message.id == message_id:
                # Remove from DLQ
                await self._redis.zrem(self._dlq_key, data)

                # Reset and requeue
                message.status = MessageStatus.PENDING
                message.retry_count = 0
                message.metadata["reprocessed_at"] = datetime.now(timezone.utc).isoformat()

                queue_key = self._get_queue_key(message.to_agent, message.priority)
                await self._redis.zadd(
                    queue_key,
                    {json.dumps(message.to_dict()): time.time()}
                )

                self._stats[message.to_agent].dead_letter_messages -= 1
                self._stats[message.to_agent].pending_messages += 1

                return True

        return False

    async def get_queue_length(
        self,
        agent: str,
        priority: Optional[MessagePriority] = None,
    ) -> int:
        """
        Get the number of pending messages for an agent.

        Args:
            agent: Agent name
            priority: Specific priority (None = all priorities)

        Returns:
            Number of pending messages
        """
        if priority:
            queue_key = self._get_queue_key(agent, priority)
            return await self._redis.zcard(queue_key)

        total = 0
        for key in self._get_all_queue_keys(agent):
            total += await self._redis.zcard(key)
        return total

    async def get_stats(self, agent: str) -> QueueStats:
        """
        Get statistics for an agent's queues.

        Args:
            agent: Agent name

        Returns:
            Queue statistics
        """
        stats = self._stats[agent]
        stats.pending_messages = await self.get_queue_length(agent)
        return stats

    async def clear_queue(
        self,
        agent: str,
        priority: Optional[MessagePriority] = None,
    ) -> int:
        """
        Clear messages from an agent's queue.

        Args:
            agent: Agent name
            priority: Specific priority (None = all priorities)

        Returns:
            Number of messages cleared
        """
        total_cleared = 0

        if priority:
            queue_key = self._get_queue_key(agent, priority)
            total_cleared = await self._redis.zcard(queue_key)
            await self._redis.delete(queue_key)
        else:
            for key in self._get_all_queue_keys(agent):
                count = await self._redis.zcard(key)
                total_cleared += count
                await self._redis.delete(key)

        self._stats[agent].pending_messages = 0
        return total_cleared

    async def broadcast(
        self,
        from_agent: str,
        message_type: str,
        payload: Dict[str, Any],
        to_agents: List[str],
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> List[str]:
        """
        Broadcast a message to multiple agents.

        Args:
            from_agent: Sending agent name
            message_type: Type of message
            payload: Message content
            to_agents: List of receiving agents
            priority: Message priority

        Returns:
            List of message IDs
        """
        message_ids = []

        for agent in to_agents:
            msg_id = await self.send_message(
                from_agent=from_agent,
                to_agent=agent,
                message_type=message_type,
                payload=payload,
                priority=priority,
            )
            message_ids.append(msg_id)

        return message_ids

    def register_handler(
        self,
        agent: str,
        handler: Callable[[BrokerMessage], Any],
    ) -> None:
        """
        Register a message handler for an agent.

        Args:
            agent: Agent name
            handler: Async function to handle messages
        """
        self._message_handlers[agent].append(handler)

    async def start_consumer(
        self,
        agent: str,
        poll_interval: float = 0.1,
    ) -> None:
        """
        Start consuming messages for an agent.

        Runs continuously, calling registered handlers for each message.

        Args:
            agent: Agent name
            poll_interval: Seconds between polls
        """
        while True:
            try:
                message = await self.receive_message(agent, timeout=poll_interval)

                if message and agent in self._message_handlers:
                    for handler in self._message_handlers[agent]:
                        try:
                            await handler(message)
                            await self.acknowledge(message.id)
                        except Exception as e:
                            await self.reject(
                                message.id,
                                reason=str(e),
                                requeue=True,
                            )
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(poll_interval)

    async def health_check(self) -> bool:
        """Check broker connectivity."""
        try:
            await self._redis.ping()
            return True
        except Exception:
            return False
