"""
Communication Protocol for Claude Agents Orchestration System.

This module defines the message format, types, and validation for
inter-agent communication within the orchestration system.
"""

import hashlib
import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field, ValidationError, validator


class MessageType(str, Enum):
    """Types of messages exchanged between agents."""

    # Control messages
    TASK_ASSIGNMENT = "task_assignment"  # Assign task to agent
    TASK_COMPLETE = "task_complete"  # Task completion notification
    TASK_FAILED = "task_failed"  # Task failure notification

    # Data messages
    DATA_REQUEST = "data_request"  # Request data from another agent
    DATA_RESPONSE = "data_response"  # Response with requested data
    DATA_UPDATE = "data_update"  # Notify of data changes

    # Status messages
    STATUS_UPDATE = "status_update"  # Agent status update
    HEARTBEAT = "heartbeat"  # Agent health check

    # Coordination messages
    HANDOFF = "handoff"  # Hand off work to another agent
    DEPENDENCY_WAIT = "dependency_wait"  # Waiting for dependency
    DEPENDENCY_READY = "dependency_ready"  # Dependency is ready

    # Error messages
    ERROR_REPORT = "error_report"  # Report an error
    RECOVERY_REQUEST = "recovery_request"  # Request error recovery
    RECOVERY_COMPLETE = "recovery_complete"  # Recovery completed

    # Validation messages
    VALIDATION_REQUEST = "validation_request"  # Request validation
    VALIDATION_RESULT = "validation_result"  # Validation result


class MessagePriority(str, Enum):
    """Priority levels for messages."""

    BLOCKING = "blocking"  # Must be processed immediately
    HIGH = "high"  # High priority
    NORMAL = "normal"  # Normal priority
    INFO = "info"  # Informational, low priority


class PayloadSchema(BaseModel):
    """Base schema for message payloads."""

    class Config:
        extra = "allow"


class TaskAssignmentPayload(PayloadSchema):
    """Payload for task assignment messages."""

    task_id: str
    task_type: str
    description: str
    requirements: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    deadline: Optional[datetime] = None
    dependencies: List[str] = Field(default_factory=list)


class TaskCompletePayload(PayloadSchema):
    """Payload for task completion messages."""

    task_id: str
    result: Dict[str, Any]
    artifacts: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    summary: str = ""


class TaskFailedPayload(PayloadSchema):
    """Payload for task failure messages."""

    task_id: str
    error_type: str
    error_message: str
    stack_trace: str = ""
    recoverable: bool = True
    suggested_action: str = ""


class DataRequestPayload(PayloadSchema):
    """Payload for data request messages."""

    request_id: str
    data_type: str
    query: Dict[str, Any] = Field(default_factory=dict)
    filters: Dict[str, Any] = Field(default_factory=dict)
    format: str = "json"


class DataResponsePayload(PayloadSchema):
    """Payload for data response messages."""

    request_id: str
    data_type: str
    data: Any
    total_count: int = 0
    page: int = 1
    has_more: bool = False


class StatusUpdatePayload(PayloadSchema):
    """Payload for status update messages."""

    status: str  # idle, busy, error, paused
    current_task: Optional[str] = None
    progress: float = 0.0  # 0.0 to 1.0
    metrics: Dict[str, Any] = Field(default_factory=dict)


class ValidationRequestPayload(PayloadSchema):
    """Payload for validation request messages."""

    gate_name: str
    phase: int
    artifacts: List[str] = Field(default_factory=list)
    criteria: Dict[str, Any] = Field(default_factory=dict)


class ValidationResultPayload(PayloadSchema):
    """Payload for validation result messages."""

    gate_name: str
    phase: int
    passed: bool
    confidence_score: float
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class ErrorReportPayload(PayloadSchema):
    """Payload for error report messages."""

    error_id: str
    error_type: str
    error_message: str
    severity: str = "error"  # warning, error, critical
    context: Dict[str, Any] = Field(default_factory=dict)
    stack_trace: str = ""


# Payload schema mapping
PAYLOAD_SCHEMAS: Dict[MessageType, type] = {
    MessageType.TASK_ASSIGNMENT: TaskAssignmentPayload,
    MessageType.TASK_COMPLETE: TaskCompletePayload,
    MessageType.TASK_FAILED: TaskFailedPayload,
    MessageType.DATA_REQUEST: DataRequestPayload,
    MessageType.DATA_RESPONSE: DataResponsePayload,
    MessageType.STATUS_UPDATE: StatusUpdatePayload,
    MessageType.VALIDATION_REQUEST: ValidationRequestPayload,
    MessageType.VALIDATION_RESULT: ValidationResultPayload,
    MessageType.ERROR_REPORT: ErrorReportPayload,
}


@dataclass
class Message:
    """
    Message structure for inter-agent communication.

    Attributes:
        id: Unique message identifier
        from_agent: Name of sending agent
        to_agent: Name of receiving agent
        message_type: Type of message
        priority: Message priority level
        payload: Message content
        signature: SHA256 signature for integrity
        correlation_id: ID for correlating related messages
        reply_to: Message ID this is replying to
        timestamp: Message creation timestamp
        metadata: Additional message metadata
    """

    from_agent: str
    to_agent: str
    message_type: MessageType
    payload: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    signature: str = ""
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Generate signature after initialization."""
        if not self.signature:
            self.signature = self._generate_signature()

    def _generate_signature(self) -> str:
        """Generate SHA256 signature for the message."""
        content = {
            "id": self.id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "message_type": (
                self.message_type.value
                if isinstance(self.message_type, Enum)
                else self.message_type
            ),
            "payload": self.payload,
            "timestamp": (
                self.timestamp.isoformat()
                if isinstance(self.timestamp, datetime)
                else self.timestamp
            ),
        }
        content_str = json.dumps(content, sort_keys=True, default=str)
        return hashlib.sha256(content_str.encode()).hexdigest()

    def verify_signature(self) -> bool:
        """Verify the message signature."""
        expected = self._generate_signature()
        return self.signature == expected

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "id": self.id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "message_type": (
                self.message_type.value
                if isinstance(self.message_type, Enum)
                else self.message_type
            ),
            "priority": self.priority.value if isinstance(self.priority, Enum) else self.priority,
            "payload": self.payload,
            "signature": self.signature,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
            "timestamp": (
                self.timestamp.isoformat()
                if isinstance(self.timestamp, datetime)
                else self.timestamp
            ),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary."""
        data = data.copy()
        if isinstance(data.get("message_type"), str):
            data["message_type"] = MessageType(data["message_type"])
        if isinstance(data.get("priority"), str):
            data["priority"] = MessagePriority(data["priority"])
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)

    def create_reply(
        self,
        message_type: MessageType,
        payload: Dict[str, Any],
        priority: Optional[MessagePriority] = None,
    ) -> "Message":
        """
        Create a reply to this message.

        Args:
            message_type: Type of reply message
            payload: Reply payload
            priority: Reply priority (defaults to original)

        Returns:
            New reply message
        """
        return Message(
            from_agent=self.to_agent,
            to_agent=self.from_agent,
            message_type=message_type,
            payload=payload,
            priority=priority or self.priority,
            correlation_id=self.correlation_id or self.id,
            reply_to=self.id,
        )


class ValidationError(Exception):
    """Raised when message validation fails."""

    def __init__(self, message: str, errors: List[str]):
        super().__init__(message)
        self.errors = errors


class CommunicationProtocol:
    """
    Protocol validator for inter-agent communication.

    Provides validation for:
    - Message structure and required fields
    - Payload schema based on message type
    - Agent name format
    - Timestamp validation
    - Signature verification

    Example:
        protocol = CommunicationProtocol()

        # Validate a message
        is_valid, errors = protocol.validate_message(message)

        # Create a validated message
        message = protocol.create_message(
            from_agent="ConceptDesigner",
            to_agent="BackendEngineer",
            message_type=MessageType.TASK_ASSIGNMENT,
            payload={"task_id": "t1", "task_type": "api", "description": "..."}
        )
    """

    # Valid agent name pattern (alphanumeric, underscores, hyphens)
    AGENT_NAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{1,63}$")

    # Known agents in the system
    KNOWN_AGENTS: Set[str] = {
        "orchestrator",
        "concept_designer",
        "mcp_engineer",
        "integration_engineer",
        "backend_engineer",
        "frontend_engineer",
        "security_engineer",
        "qa_engineer",
        "devops_engineer",
    }

    def __init__(self, strict_mode: bool = False):
        """
        Initialize the protocol validator.

        Args:
            strict_mode: If True, only allow known agents
        """
        self._strict_mode = strict_mode

    def validate_agent_name(self, name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an agent name.

        Args:
            name: Agent name to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not name:
            return False, "Agent name cannot be empty"

        if not self.AGENT_NAME_PATTERN.match(name):
            return False, f"Invalid agent name format: {name}"

        if self._strict_mode and name.lower() not in self.KNOWN_AGENTS:
            return False, f"Unknown agent: {name}"

        return True, None

    def validate_payload(
        self,
        message_type: MessageType,
        payload: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        Validate message payload against schema.

        Args:
            message_type: Type of message
            payload: Payload to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Get schema for message type
        schema_class = PAYLOAD_SCHEMAS.get(message_type)

        if schema_class:
            try:
                schema_class(**payload)
            except ValidationError as e:
                for error in e.errors():
                    loc = ".".join(str(l) for l in error["loc"])
                    errors.append(f"Payload.{loc}: {error['msg']}")
            except Exception as e:
                errors.append(f"Payload validation error: {str(e)}")

        return len(errors) == 0, errors

    def validate_timestamp(
        self,
        timestamp: datetime,
        max_age_seconds: int = 3600,
        max_future_seconds: int = 60,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate message timestamp.

        Args:
            timestamp: Timestamp to validate
            max_age_seconds: Maximum age of message
            max_future_seconds: Maximum seconds in future

        Returns:
            Tuple of (is_valid, error_message)
        """
        now = datetime.now(timezone.utc)

        # Ensure timestamp is timezone-aware
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        age = (now - timestamp).total_seconds()

        if age > max_age_seconds:
            return False, f"Message too old: {age:.0f}s > {max_age_seconds}s"

        if age < -max_future_seconds:
            return False, f"Message timestamp in future: {-age:.0f}s"

        return True, None

    def validate_message(
        self,
        message: Message,
        verify_signature: bool = True,
    ) -> Tuple[bool, List[str]]:
        """
        Validate a complete message.

        Args:
            message: Message to validate
            verify_signature: Whether to verify signature

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Validate from_agent
        valid, error = self.validate_agent_name(message.from_agent)
        if not valid:
            errors.append(f"from_agent: {error}")

        # Validate to_agent
        valid, error = self.validate_agent_name(message.to_agent)
        if not valid:
            errors.append(f"to_agent: {error}")

        # Validate message type
        if not isinstance(message.message_type, MessageType):
            try:
                MessageType(message.message_type)
            except ValueError:
                errors.append(f"Invalid message_type: {message.message_type}")

        # Validate priority
        if not isinstance(message.priority, MessagePriority):
            try:
                MessagePriority(message.priority)
            except ValueError:
                errors.append(f"Invalid priority: {message.priority}")

        # Validate payload
        valid, payload_errors = self.validate_payload(message.message_type, message.payload)
        errors.extend(payload_errors)

        # Validate timestamp
        valid, error = self.validate_timestamp(message.timestamp)
        if not valid:
            errors.append(f"timestamp: {error}")

        # Verify signature
        if verify_signature and not message.verify_signature():
            errors.append("Invalid message signature")

        return len(errors) == 0, errors

    def create_message(
        self,
        from_agent: str,
        to_agent: str,
        message_type: MessageType,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """
        Create a validated message.

        Args:
            from_agent: Sending agent name
            to_agent: Receiving agent name
            message_type: Type of message
            payload: Message payload
            priority: Message priority
            correlation_id: Correlation ID for related messages
            reply_to: ID of message being replied to
            metadata: Additional metadata

        Returns:
            Validated message

        Raises:
            ValidationError: If validation fails
        """
        message = Message(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            payload=payload,
            priority=priority,
            correlation_id=correlation_id,
            reply_to=reply_to,
            metadata=metadata or {},
        )

        is_valid, errors = self.validate_message(message, verify_signature=False)

        if not is_valid:
            raise ValidationError(f"Message validation failed: {'; '.join(errors)}", errors)

        # Regenerate signature after validation
        message.signature = message._generate_signature()

        return message

    def create_task_assignment(
        self,
        from_agent: str,
        to_agent: str,
        task_id: str,
        task_type: str,
        description: str,
        requirements: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> Message:
        """Helper to create a task assignment message."""
        return self.create_message(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=MessageType.TASK_ASSIGNMENT,
            payload={
                "task_id": task_id,
                "task_type": task_type,
                "description": description,
                "requirements": requirements or {},
                "context": context or {},
            },
            priority=priority,
        )

    def create_task_complete(
        self,
        from_agent: str,
        to_agent: str,
        task_id: str,
        result: Dict[str, Any],
        artifacts: Optional[List[str]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> Message:
        """Helper to create a task completion message."""
        return self.create_message(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=MessageType.TASK_COMPLETE,
            payload={
                "task_id": task_id,
                "result": result,
                "artifacts": artifacts or [],
                "metrics": metrics or {},
            },
            correlation_id=correlation_id,
        )

    def create_error_report(
        self,
        from_agent: str,
        to_agent: str,
        error_type: str,
        error_message: str,
        severity: str = "error",
        context: Optional[Dict[str, Any]] = None,
        stack_trace: str = "",
    ) -> Message:
        """Helper to create an error report message."""
        return self.create_message(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=MessageType.ERROR_REPORT,
            payload={
                "error_id": str(uuid.uuid4()),
                "error_type": error_type,
                "error_message": error_message,
                "severity": severity,
                "context": context or {},
                "stack_trace": stack_trace,
            },
            priority=MessagePriority.HIGH if severity == "critical" else MessagePriority.NORMAL,
        )


# Example usage and utility functions


def serialize_message(message: Message) -> str:
    """Serialize a message to JSON string."""
    return json.dumps(message.to_dict(), default=str)


def deserialize_message(data: str) -> Message:
    """Deserialize a message from JSON string."""
    return Message.from_dict(json.loads(data))


async def send_and_wait_reply(
    protocol: CommunicationProtocol,
    broker,  # MessageBroker
    message: Message,
    timeout: float = 30.0,
) -> Optional[Message]:
    """
    Send a message and wait for a reply.

    Args:
        protocol: Communication protocol instance
        broker: Message broker instance
        message: Message to send
        timeout: Timeout in seconds

    Returns:
        Reply message or None if timeout
    """
    from core.message_broker import MessageBroker

    # Send the message
    await broker.send_message(
        from_agent=message.from_agent,
        to_agent=message.to_agent,
        message_type=message.message_type.value,
        payload=message.to_dict(),
        priority=message.priority.value,
    )

    # Wait for reply
    import asyncio

    start_time = asyncio.get_event_loop().time()

    while asyncio.get_event_loop().time() - start_time < timeout:
        reply = await broker.receive_message(
            agent=message.from_agent,
            timeout=1.0,
        )

        if reply and reply.metadata.get("reply_to") == message.id:
            return Message.from_dict(reply.payload)

        await asyncio.sleep(0.1)

    return None
