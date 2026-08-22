"""
Error Recovery for Claude Agents Orchestration System.

This module implements a 3-level error recovery system:
- Level 1: Agent retry (3 attempts, 10 min timeout)
- Level 2: Phase rollback (2 attempts, 30 min timeout)
- Level 3: Full rollback (human intervention required)
"""

import asyncio
import json
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class RecoveryLevel(str, Enum):
    """Error recovery levels."""

    LEVEL_1_RETRY = "level_1_retry"
    LEVEL_2_ROLLBACK = "level_2_rollback"
    LEVEL_3_FULL_ROLLBACK = "level_3_full_rollback"


class RecoveryStatus(str, Enum):
    """Status of recovery attempt."""

    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ESCALATED = "escalated"
    HUMAN_REQUIRED = "human_required"


class ErrorCategory(str, Enum):
    """Categories of errors for recovery matching."""

    TRANSIENT = "transient"  # Network issues, timeouts
    RESOURCE = "resource"  # Memory, disk, quota
    CONFIGURATION = "configuration"  # Config errors
    DEPENDENCY = "dependency"  # External service failures
    LOGIC = "logic"  # Business logic errors
    SECURITY = "security"  # Security violations
    UNKNOWN = "unknown"  # Uncategorized errors


@dataclass
class ErrorSignature:
    """
    Error signature for matching and cataloging errors.

    Used to identify similar errors and apply appropriate recovery strategies.
    """

    error_type: str
    error_pattern: str
    category: ErrorCategory
    recovery_level: RecoveryLevel
    resolution_steps: List[str] = field(default_factory=list)
    requires_human: bool = False


@dataclass
class ErrorRecord:
    """Record of an error occurrence."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    error_type: str = ""
    error_message: str = ""
    stack_trace: str = ""
    agent_name: str = ""
    phase: int = 0
    category: ErrorCategory = ErrorCategory.UNKNOWN
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "agent_name": self.agent_name,
            "phase": self.phase,
            "category": self.category.value,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RecoveryAttempt:
    """Record of a recovery attempt."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    error_id: str = ""
    level: RecoveryLevel = RecoveryLevel.LEVEL_1_RETRY
    attempt_number: int = 1
    max_attempts: int = 3
    status: RecoveryStatus = RecoveryStatus.IN_PROGRESS
    action_taken: str = ""
    result_message: str = ""
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "error_id": self.error_id,
            "level": self.level.value,
            "attempt_number": self.attempt_number,
            "max_attempts": self.max_attempts,
            "status": self.status.value,
            "action_taken": self.action_taken,
            "result_message": self.result_message,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class RecoveryResult:
    """Result of a recovery operation."""

    success: bool
    level: RecoveryLevel
    attempts: List[RecoveryAttempt]
    final_status: RecoveryStatus
    error_record: ErrorRecord
    checkpoint_id: Optional[str] = None
    message: str = ""
    requires_human: bool = False
    suggested_actions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "level": self.level.value,
            "attempts": [a.to_dict() for a in self.attempts],
            "final_status": self.final_status.value,
            "error_record": self.error_record.to_dict(),
            "checkpoint_id": self.checkpoint_id,
            "message": self.message,
            "requires_human": self.requires_human,
            "suggested_actions": self.suggested_actions,
        }


# Error catalog with known error patterns and resolutions
ERROR_CATALOG: List[ErrorSignature] = [
    # Transient errors
    ErrorSignature(
        error_type="ConnectionError",
        error_pattern="connection.*refused|connection.*timeout",
        category=ErrorCategory.TRANSIENT,
        recovery_level=RecoveryLevel.LEVEL_1_RETRY,
        resolution_steps=["Wait and retry", "Check network connectivity"],
    ),
    ErrorSignature(
        error_type="TimeoutError",
        error_pattern="timeout|timed out",
        category=ErrorCategory.TRANSIENT,
        recovery_level=RecoveryLevel.LEVEL_1_RETRY,
        resolution_steps=["Increase timeout", "Retry with backoff"],
    ),
    # Resource errors
    ErrorSignature(
        error_type="MemoryError",
        error_pattern="out of memory|memory.*exceeded",
        category=ErrorCategory.RESOURCE,
        recovery_level=RecoveryLevel.LEVEL_2_ROLLBACK,
        resolution_steps=["Free memory", "Reduce batch size", "Scale resources"],
    ),
    ErrorSignature(
        error_type="QuotaExceeded",
        error_pattern="quota.*exceeded|rate.*limit",
        category=ErrorCategory.RESOURCE,
        recovery_level=RecoveryLevel.LEVEL_1_RETRY,
        resolution_steps=["Wait for quota reset", "Implement throttling"],
    ),
    # Configuration errors
    ErrorSignature(
        error_type="ConfigurationError",
        error_pattern="invalid.*config|missing.*config",
        category=ErrorCategory.CONFIGURATION,
        recovery_level=RecoveryLevel.LEVEL_3_FULL_ROLLBACK,
        resolution_steps=["Review configuration", "Fix config values"],
        requires_human=True,
    ),
    # Dependency errors
    ErrorSignature(
        error_type="DependencyError",
        error_pattern="service.*unavailable|dependency.*failed",
        category=ErrorCategory.DEPENDENCY,
        recovery_level=RecoveryLevel.LEVEL_2_ROLLBACK,
        resolution_steps=["Check dependency status", "Use fallback"],
    ),
    # Security errors
    ErrorSignature(
        error_type="SecurityError",
        error_pattern="unauthorized|forbidden|authentication.*failed",
        category=ErrorCategory.SECURITY,
        recovery_level=RecoveryLevel.LEVEL_3_FULL_ROLLBACK,
        resolution_steps=["Review credentials", "Check permissions"],
        requires_human=True,
    ),
]


class ErrorRecovery:
    """
    3-level error recovery system.

    Level 1: Agent-level retry
    - 3 attempts maximum
    - 10 minute timeout per attempt
    - Exponential backoff

    Level 2: Phase rollback
    - 2 attempts maximum
    - 30 minute timeout
    - Cleans up phase artifacts
    - Restarts from last checkpoint

    Level 3: Full rollback
    - Complete cleanup
    - Human intervention required
    - Creates detailed incident report

    Example:
        recovery = ErrorRecovery(config)

        # Attempt recovery
        result = await recovery.recover(
            error=exception,
            agent_name="BackendEngineer",
            phase=4,
            context={"task_id": "t1"},
        )

        if result.success:
            # Continue execution
            pass
        elif result.requires_human:
            # Notify human operator
            pass
    """

    def __init__(
        self,
        level1_max_attempts: int = 3,
        level1_timeout_minutes: int = 10,
        level2_max_attempts: int = 2,
        level2_timeout_minutes: int = 30,
        level3_require_human: bool = True,
    ):
        """
        Initialize error recovery system.

        Args:
            level1_max_attempts: Max retry attempts for level 1
            level1_timeout_minutes: Timeout per level 1 attempt
            level2_max_attempts: Max rollback attempts for level 2
            level2_timeout_minutes: Timeout per level 2 attempt
            level3_require_human: Whether level 3 requires human intervention
        """
        self.level1_max_attempts = level1_max_attempts
        self.level1_timeout_minutes = level1_timeout_minutes
        self.level2_max_attempts = level2_max_attempts
        self.level2_timeout_minutes = level2_timeout_minutes
        self.level3_require_human = level3_require_human

        # State tracking
        self._error_history: List[ErrorRecord] = []
        self._recovery_history: List[RecoveryAttempt] = []
        self._checkpoints: Dict[str, Dict[str, Any]] = {}

        # Callbacks for integration
        self._rollback_handlers: Dict[int, Callable] = {}
        self._cleanup_handlers: List[Callable] = []

    def categorize_error(self, error: Exception) -> ErrorSignature:
        """
        Categorize an error and determine recovery strategy.

        Args:
            error: Exception to categorize

        Returns:
            ErrorSignature with recovery information
        """
        import re

        error_type = type(error).__name__
        error_message = str(error).lower()

        # Check against catalog
        for signature in ERROR_CATALOG:
            if signature.error_type == error_type:
                return signature
            if re.search(signature.error_pattern, error_message):
                return signature

        # Default unknown error
        return ErrorSignature(
            error_type=error_type,
            error_pattern="",
            category=ErrorCategory.UNKNOWN,
            recovery_level=RecoveryLevel.LEVEL_1_RETRY,
            resolution_steps=["Review error logs", "Retry operation"],
        )

    def create_error_record(
        self,
        error: Exception,
        agent_name: str,
        phase: int,
        context: Optional[Dict[str, Any]] = None,
    ) -> ErrorRecord:
        """Create an error record for tracking."""
        signature = self.categorize_error(error)

        record = ErrorRecord(
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            agent_name=agent_name,
            phase=phase,
            category=signature.category,
            context=context or {},
        )

        self._error_history.append(record)
        return record

    def save_checkpoint(
        self,
        checkpoint_id: str,
        phase: int,
        state: Dict[str, Any],
    ) -> None:
        """
        Save a checkpoint for potential rollback.

        Args:
            checkpoint_id: Unique checkpoint identifier
            phase: Current phase number
            state: State data to save
        """
        self._checkpoints[checkpoint_id] = {
            "phase": phase,
            "state": state,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a saved checkpoint."""
        return self._checkpoints.get(checkpoint_id)

    def register_rollback_handler(
        self,
        phase: int,
        handler: Callable[[Dict[str, Any]], Any],
    ) -> None:
        """
        Register a rollback handler for a phase.

        Args:
            phase: Phase number
            handler: Async function to handle rollback
        """
        self._rollback_handlers[phase] = handler

    def register_cleanup_handler(
        self,
        handler: Callable[[ErrorRecord], Any],
    ) -> None:
        """Register a cleanup handler for level 3 rollback."""
        self._cleanup_handlers.append(handler)

    async def _level_1_retry(
        self,
        operation: Callable,
        error_record: ErrorRecord,
        context: Dict[str, Any],
    ) -> Tuple[bool, List[RecoveryAttempt], Optional[Any]]:
        """
        Execute level 1 recovery (agent retry).

        Args:
            operation: Operation to retry
            error_record: Error that triggered recovery
            context: Operation context

        Returns:
            Tuple of (success, attempts, result)
        """
        attempts = []
        result = None

        for attempt_num in range(1, self.level1_max_attempts + 1):
            attempt = RecoveryAttempt(
                error_id=error_record.id,
                level=RecoveryLevel.LEVEL_1_RETRY,
                attempt_number=attempt_num,
                max_attempts=self.level1_max_attempts,
                action_taken=f"Retry attempt {attempt_num}/{self.level1_max_attempts}",
            )

            try:
                # Exponential backoff
                if attempt_num > 1:
                    wait_seconds = min(2**attempt_num, 60)
                    await asyncio.sleep(wait_seconds)

                # Execute with timeout
                timeout = self.level1_timeout_minutes * 60
                result = await asyncio.wait_for(
                    (
                        operation(**context)
                        if asyncio.iscoroutinefunction(operation)
                        else asyncio.get_event_loop().run_in_executor(
                            None, lambda: operation(**context)
                        )
                    ),
                    timeout=timeout,
                )

                attempt.status = RecoveryStatus.SUCCESS
                attempt.result_message = "Operation succeeded"
                attempt.completed_at = datetime.now(timezone.utc)
                attempt.duration_seconds = (
                    attempt.completed_at - attempt.started_at
                ).total_seconds()
                attempts.append(attempt)

                return True, attempts, result

            except asyncio.TimeoutError:
                attempt.status = RecoveryStatus.FAILED
                attempt.result_message = f"Timeout after {self.level1_timeout_minutes} minutes"

            except Exception as e:
                attempt.status = RecoveryStatus.FAILED
                attempt.result_message = f"{type(e).__name__}: {str(e)}"

            attempt.completed_at = datetime.now(timezone.utc)
            attempt.duration_seconds = (attempt.completed_at - attempt.started_at).total_seconds()
            attempts.append(attempt)
            self._recovery_history.append(attempt)

        return False, attempts, None

    async def _level_2_rollback(
        self,
        error_record: ErrorRecord,
        checkpoint_id: Optional[str] = None,
    ) -> Tuple[bool, List[RecoveryAttempt]]:
        """
        Execute level 2 recovery (phase rollback).

        Args:
            error_record: Error that triggered recovery
            checkpoint_id: Checkpoint to rollback to

        Returns:
            Tuple of (success, attempts)
        """
        attempts = []

        for attempt_num in range(1, self.level2_max_attempts + 1):
            attempt = RecoveryAttempt(
                error_id=error_record.id,
                level=RecoveryLevel.LEVEL_2_ROLLBACK,
                attempt_number=attempt_num,
                max_attempts=self.level2_max_attempts,
                action_taken=f"Phase rollback attempt {attempt_num}/{self.level2_max_attempts}",
            )

            try:
                # Get rollback handler for the phase
                handler = self._rollback_handlers.get(error_record.phase)

                if handler:
                    # Get checkpoint state
                    checkpoint_state = {}
                    if checkpoint_id:
                        checkpoint_data = self.get_checkpoint(checkpoint_id)
                        if checkpoint_data:
                            checkpoint_state = checkpoint_data.get("state", {})

                    # Execute rollback with timeout
                    timeout = self.level2_timeout_minutes * 60
                    if asyncio.iscoroutinefunction(handler):
                        await asyncio.wait_for(
                            handler(checkpoint_state),
                            timeout=timeout,
                        )
                    else:
                        await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(
                                None, lambda: handler(checkpoint_state)
                            ),
                            timeout=timeout,
                        )

                    attempt.status = RecoveryStatus.SUCCESS
                    attempt.result_message = "Phase rollback completed"
                else:
                    attempt.status = RecoveryStatus.SUCCESS
                    attempt.result_message = "No rollback handler (no cleanup needed)"

                attempt.completed_at = datetime.now(timezone.utc)
                attempt.duration_seconds = (
                    attempt.completed_at - attempt.started_at
                ).total_seconds()
                attempts.append(attempt)

                return True, attempts

            except asyncio.TimeoutError:
                attempt.status = RecoveryStatus.FAILED
                attempt.result_message = (
                    f"Rollback timeout after {self.level2_timeout_minutes} minutes"
                )

            except Exception as e:
                attempt.status = RecoveryStatus.FAILED
                attempt.result_message = f"Rollback failed: {type(e).__name__}: {str(e)}"

            attempt.completed_at = datetime.now(timezone.utc)
            attempt.duration_seconds = (attempt.completed_at - attempt.started_at).total_seconds()
            attempts.append(attempt)
            self._recovery_history.append(attempt)

        return False, attempts

    async def _level_3_full_rollback(
        self,
        error_record: ErrorRecord,
    ) -> Tuple[bool, List[RecoveryAttempt]]:
        """
        Execute level 3 recovery (full rollback).

        Args:
            error_record: Error that triggered recovery

        Returns:
            Tuple of (success, attempts)
        """
        attempt = RecoveryAttempt(
            error_id=error_record.id,
            level=RecoveryLevel.LEVEL_3_FULL_ROLLBACK,
            attempt_number=1,
            max_attempts=1,
            action_taken="Full system rollback",
        )

        try:
            # Execute all cleanup handlers
            for handler in self._cleanup_handlers:
                if asyncio.iscoroutinefunction(handler):
                    await handler(error_record)
                else:
                    await asyncio.get_event_loop().run_in_executor(
                        None, lambda: handler(error_record)
                    )

            attempt.status = (
                RecoveryStatus.HUMAN_REQUIRED
                if self.level3_require_human
                else RecoveryStatus.SUCCESS
            )
            attempt.result_message = (
                "Full rollback completed - human review required"
                if self.level3_require_human
                else "Full rollback completed"
            )

        except Exception as e:
            attempt.status = RecoveryStatus.FAILED
            attempt.result_message = f"Full rollback failed: {type(e).__name__}: {str(e)}"

        attempt.completed_at = datetime.now(timezone.utc)
        attempt.duration_seconds = (attempt.completed_at - attempt.started_at).total_seconds()
        self._recovery_history.append(attempt)

        return not self.level3_require_human and attempt.status == RecoveryStatus.SUCCESS, [attempt]

    async def recover(
        self,
        error: Exception,
        agent_name: str,
        phase: int,
        context: Optional[Dict[str, Any]] = None,
        operation: Optional[Callable] = None,
        checkpoint_id: Optional[str] = None,
    ) -> RecoveryResult:
        """
        Execute error recovery starting from appropriate level.

        Args:
            error: Exception that occurred
            agent_name: Name of the agent that failed
            phase: Current phase number
            context: Operation context
            operation: Operation to retry (for level 1)
            checkpoint_id: Checkpoint ID for rollback

        Returns:
            RecoveryResult with outcome and details
        """
        # Create error record
        error_record = self.create_error_record(error, agent_name, phase, context)

        # Determine starting level based on error category
        signature = self.categorize_error(error)
        starting_level = signature.recovery_level

        all_attempts = []
        success = False
        final_status = RecoveryStatus.FAILED
        requires_human = False
        suggested_actions = signature.resolution_steps.copy()

        # Level 1: Retry
        if starting_level == RecoveryLevel.LEVEL_1_RETRY and operation:
            success, attempts, _ = await self._level_1_retry(operation, error_record, context or {})
            all_attempts.extend(attempts)

            if success:
                final_status = RecoveryStatus.SUCCESS
                return RecoveryResult(
                    success=True,
                    level=RecoveryLevel.LEVEL_1_RETRY,
                    attempts=all_attempts,
                    final_status=final_status,
                    error_record=error_record,
                    checkpoint_id=checkpoint_id,
                    message="Recovery successful after retry",
                )

            # Escalate to level 2
            starting_level = RecoveryLevel.LEVEL_2_ROLLBACK

        # Level 2: Phase rollback
        if starting_level == RecoveryLevel.LEVEL_2_ROLLBACK:
            success, attempts = await self._level_2_rollback(error_record, checkpoint_id)
            all_attempts.extend(attempts)

            if success:
                final_status = RecoveryStatus.SUCCESS
                return RecoveryResult(
                    success=True,
                    level=RecoveryLevel.LEVEL_2_ROLLBACK,
                    attempts=all_attempts,
                    final_status=final_status,
                    error_record=error_record,
                    checkpoint_id=checkpoint_id,
                    message="Recovery successful after phase rollback",
                )

            # Escalate to level 3
            starting_level = RecoveryLevel.LEVEL_3_FULL_ROLLBACK

        # Level 3: Full rollback
        if starting_level == RecoveryLevel.LEVEL_3_FULL_ROLLBACK:
            success, attempts = await self._level_3_full_rollback(error_record)
            all_attempts.extend(attempts)

            if success:
                final_status = RecoveryStatus.SUCCESS
            else:
                final_status = RecoveryStatus.HUMAN_REQUIRED
                requires_human = True

        return RecoveryResult(
            success=success,
            level=starting_level,
            attempts=all_attempts,
            final_status=final_status,
            error_record=error_record,
            checkpoint_id=checkpoint_id,
            message=(
                "Full rollback completed - human intervention required"
                if requires_human
                else "Recovery completed"
            ),
            requires_human=requires_human,
            suggested_actions=suggested_actions,
        )

    def get_error_history(self, limit: int = 100) -> List[ErrorRecord]:
        """Get recent error history."""
        return self._error_history[-limit:]

    def get_recovery_history(self, limit: int = 100) -> List[RecoveryAttempt]:
        """Get recent recovery attempt history."""
        return self._recovery_history[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        total_recoveries = len(self._recovery_history)
        successful = sum(1 for r in self._recovery_history if r.status == RecoveryStatus.SUCCESS)

        by_level = {level.value: 0 for level in RecoveryLevel}
        for attempt in self._recovery_history:
            by_level[attempt.level.value] += 1

        return {
            "total_errors": len(self._error_history),
            "total_recovery_attempts": total_recoveries,
            "successful_recoveries": successful,
            "success_rate": successful / total_recoveries if total_recoveries > 0 else 0,
            "attempts_by_level": by_level,
        }
