"""
Logging Management for Claude Agents Orchestration System.

This module provides a comprehensive 5-level logging system:
- Event logs: Agent invocations, token usage, latency
- Decision logs: Agent reasoning and choices
- Trace logs: Detailed execution traces
- Error logs: Exceptions and stack traces
- Audit logs: Compliance-ready records with 7-year retention
"""

import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from orchestrator.config import ConfigManager, LoggingConfig


class LogLevel(str, Enum):
    """Log levels for the system."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(str, Enum):
    """Categories for structured logging."""

    EVENT = "event"
    DECISION = "decision"
    TRACE = "trace"
    ERROR = "error"
    AUDIT = "audit"


@dataclass
class EventLog:
    """Structure for event logs (agent invocations, token usage, latency)."""

    timestamp: str
    category: str = LogCategory.EVENT.value
    agent_name: str = ""
    event_type: str = ""
    phase: int = 0
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: float = 0.0
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DecisionLog:
    """Structure for decision logs (agent reasoning)."""

    timestamp: str
    category: str = LogCategory.DECISION.value
    agent_name: str = ""
    decision: str = ""
    reasoning: str = ""
    alternatives: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TraceLog:
    """Structure for trace logs (execution traces)."""

    timestamp: str
    category: str = LogCategory.TRACE.value
    trace_id: str = ""
    span_id: str = ""
    parent_span_id: Optional[str] = None
    operation: str = ""
    duration_ms: float = 0.0
    status: str = "ok"
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ErrorLog:
    """Structure for error logs (exceptions and recovery)."""

    timestamp: str
    category: str = LogCategory.ERROR.value
    error_type: str = ""
    error_message: str = ""
    stack_trace: str = ""
    agent_name: str = ""
    phase: int = 0
    recovery_attempted: bool = False
    recovery_successful: bool = False
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AuditLog:
    """Structure for audit logs (compliance records)."""

    timestamp: str
    category: str = LogCategory.AUDIT.value
    user_id: str = ""
    action: str = ""
    resource: str = ""
    resource_id: str = ""
    result: str = ""  # success, failure, denied
    ip_address: str = ""
    user_agent: str = ""
    request_id: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def json_serializer(record: Dict[str, Any]) -> str:
    """Serialize log record to JSON."""

    def serialize(obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return str(obj)

    subset = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
    }

    # Add extra data if present
    if "extra" in record:
        for key, value in record["extra"].items():
            if key not in ["__json_data__"]:
                subset[key] = serialize(value)

    return json.dumps(subset, default=serialize)


class LoggerManager:
    """
    Centralized logging manager for the orchestration system.

    Provides 5-level logging:
    - Event logs: Agent invocations, token usage, latency
    - Decision logs: Agent reasoning and choices
    - Trace logs: Detailed execution traces
    - Error logs: Exceptions and stack traces
    - Audit logs: Compliance-ready records

    Example:
        logger_manager = LoggerManager(config)
        logger_manager.event("ConceptDesigner", "invocation", phase=1, tokens_input=100)
        logger_manager.decision("ConceptDesigner", "Chose React", reasoning="...")
        logger_manager.error("Backend", "Connection failed", error=exception)
        logger_manager.audit("user123", "create_project", "project", result="success")
    """

    def __init__(self, config: ConfigManager):
        """
        Initialize the logger manager.

        Args:
            config: Configuration manager instance
        """
        self._config = config
        self._logging_config = config.logging
        self._log_dir = Path(self._logging_config.directory)

        # Create log directory
        self._log_dir.mkdir(parents=True, exist_ok=True)

        # Configure loguru
        self._configure_loguru()

        # Track active traces
        self._active_traces: Dict[str, TraceLog] = {}

    def _configure_loguru(self) -> None:
        """Configure loguru handlers for different log types."""

        # Remove default handler
        logger.remove()

        # Console handler
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

        if self._logging_config.format == "json":
            logger.add(
                sys.stderr,
                format=json_serializer,
                level=self._logging_config.level,
                colorize=False,
            )
        else:
            logger.add(
                sys.stderr,
                format=log_format,
                level=self._logging_config.level,
                colorize=True,
            )

        # File handlers for each category
        log_configs = [
            (LogCategory.EVENT, "events.log"),
            (LogCategory.DECISION, "decisions.log"),
            (LogCategory.TRACE, "traces.log"),
            (LogCategory.ERROR, "errors.log"),
        ]

        for category, filename in log_configs:
            logger.add(
                self._log_dir / filename,
                format=json_serializer,
                level=self._logging_config.level,
                rotation=self._logging_config.rotation,
                retention=self._logging_config.retention,
                filter=lambda record, cat=category: record["extra"].get("category") == cat.value,
                compression="gz",
            )

        # Audit log with extended retention
        logger.add(
            self._log_dir / "audit.log",
            format=json_serializer,
            level="INFO",
            rotation="1 day",
            retention=self._logging_config.audit_retention,
            filter=lambda record: record["extra"].get("category") == LogCategory.AUDIT.value,
            compression="gz",
        )

    def _timestamp(self) -> str:
        """Get current UTC timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()

    def event(
        self,
        agent_name: str,
        event_type: str,
        phase: int = 0,
        tokens_input: int = 0,
        tokens_output: int = 0,
        latency_ms: float = 0.0,
        success: bool = True,
        **metadata: Any,
    ) -> None:
        """
        Log an event (agent invocation, token usage, etc.).

        Args:
            agent_name: Name of the agent
            event_type: Type of event (invocation, completion, etc.)
            phase: Current phase number
            tokens_input: Input tokens used
            tokens_output: Output tokens generated
            latency_ms: Operation latency in milliseconds
            success: Whether the event was successful
            **metadata: Additional metadata
        """
        log_entry = EventLog(
            timestamp=self._timestamp(),
            agent_name=agent_name,
            event_type=event_type,
            phase=phase,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            latency_ms=latency_ms,
            success=success,
            metadata=metadata,
        )

        logger.bind(category=LogCategory.EVENT.value, **log_entry.to_dict()).info(
            f"[{agent_name}] {event_type} - Phase {phase}"
        )

    def decision(
        self,
        agent_name: str,
        decision: str,
        reasoning: str = "",
        alternatives: Optional[List[str]] = None,
        confidence_score: float = 0.0,
        **context: Any,
    ) -> None:
        """
        Log a decision made by an agent.

        Args:
            agent_name: Name of the agent making the decision
            decision: The decision made
            reasoning: Explanation for the decision
            alternatives: Alternative options considered
            confidence_score: Confidence in the decision (0-1)
            **context: Additional context
        """
        log_entry = DecisionLog(
            timestamp=self._timestamp(),
            agent_name=agent_name,
            decision=decision,
            reasoning=reasoning,
            alternatives=alternatives or [],
            confidence_score=confidence_score,
            context=context,
        )

        logger.bind(category=LogCategory.DECISION.value, **log_entry.to_dict()).info(
            f"[{agent_name}] Decision: {decision[:100]}"
        )

    def trace_start(
        self,
        trace_id: str,
        span_id: str,
        operation: str,
        parent_span_id: Optional[str] = None,
        **attributes: Any,
    ) -> None:
        """
        Start a trace span.

        Args:
            trace_id: Unique trace identifier
            span_id: Unique span identifier
            operation: Name of the operation
            parent_span_id: Parent span ID (if nested)
            **attributes: Additional attributes
        """
        log_entry = TraceLog(
            timestamp=self._timestamp(),
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation=operation,
            status="started",
            attributes=attributes,
        )

        self._active_traces[span_id] = log_entry

        logger.bind(category=LogCategory.TRACE.value, **log_entry.to_dict()).debug(
            f"[TRACE START] {operation} ({span_id})"
        )

    def trace_end(
        self, span_id: str, status: str = "ok", duration_ms: float = 0.0, **attributes: Any
    ) -> None:
        """
        End a trace span.

        Args:
            span_id: Span identifier to end
            status: Final status (ok, error, cancelled)
            duration_ms: Total duration in milliseconds
            **attributes: Additional attributes
        """
        if span_id in self._active_traces:
            log_entry = self._active_traces.pop(span_id)
            log_entry.status = status
            log_entry.duration_ms = duration_ms
            log_entry.attributes.update(attributes)
            log_entry.timestamp = self._timestamp()

            logger.bind(category=LogCategory.TRACE.value, **log_entry.to_dict()).debug(
                f"[TRACE END] {log_entry.operation} ({span_id}) - {duration_ms:.2f}ms"
            )

    def error(
        self,
        agent_name: str,
        error_message: str,
        error: Optional[Exception] = None,
        phase: int = 0,
        recovery_attempted: bool = False,
        recovery_successful: bool = False,
        **context: Any,
    ) -> None:
        """
        Log an error.

        Args:
            agent_name: Name of the agent that encountered the error
            error_message: Error description
            error: Exception object (if available)
            phase: Current phase number
            recovery_attempted: Whether recovery was attempted
            recovery_successful: Whether recovery succeeded
            **context: Additional context
        """
        import traceback

        stack_trace = ""
        error_type = "UnknownError"

        if error:
            error_type = type(error).__name__
            stack_trace = traceback.format_exc()

        log_entry = ErrorLog(
            timestamp=self._timestamp(),
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            agent_name=agent_name,
            phase=phase,
            recovery_attempted=recovery_attempted,
            recovery_successful=recovery_successful,
            context=context,
        )

        logger.bind(category=LogCategory.ERROR.value, **log_entry.to_dict()).error(
            f"[{agent_name}] {error_type}: {error_message}"
        )

    def audit(
        self,
        user_id: str,
        action: str,
        resource: str,
        resource_id: str = "",
        result: str = "success",
        ip_address: str = "",
        user_agent: str = "",
        request_id: str = "",
        **details: Any,
    ) -> None:
        """
        Log an audit event (compliance record).

        Args:
            user_id: User performing the action
            action: Action performed
            resource: Resource type affected
            resource_id: Specific resource ID
            result: Result of the action (success, failure, denied)
            ip_address: Client IP address
            user_agent: Client user agent
            request_id: Request correlation ID
            **details: Additional details
        """
        log_entry = AuditLog(
            timestamp=self._timestamp(),
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            result=result,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            details=details,
        )

        logger.bind(category=LogCategory.AUDIT.value, **log_entry.to_dict()).info(
            f"[AUDIT] {user_id} {action} {resource}/{resource_id} -> {result}"
        )

    def debug(self, source: str, message: str, **extra: Any) -> None:
        """Log a debug message."""
        logger.bind(source=source, **extra).debug(message)

    def info(self, source: str, message: str, **extra: Any) -> None:
        """Log an info message."""
        logger.bind(source=source, **extra).info(message)

    def warning(self, source: str, message: str, **extra: Any) -> None:
        """Log a warning message."""
        logger.bind(source=source, **extra).warning(message)

    def critical(self, source: str, message: str, **extra: Any) -> None:
        """Log a critical message."""
        logger.bind(source=source, **extra).critical(message)

    def get_log_file_path(self, category: LogCategory) -> Path:
        """Get the path to a specific log file."""
        filenames = {
            LogCategory.EVENT: "events.log",
            LogCategory.DECISION: "decisions.log",
            LogCategory.TRACE: "traces.log",
            LogCategory.ERROR: "errors.log",
            LogCategory.AUDIT: "audit.log",
        }
        return self._log_dir / filenames[category]

    def rotate_logs(self) -> None:
        """Manually trigger log rotation."""
        logger.complete()
