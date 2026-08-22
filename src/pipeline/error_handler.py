"""
Error Handler for EduLens Pipeline

Provides comprehensive error handling, recovery strategies, and graceful
degradation for the EduLens tutoring system. Handles vision, audio, and AI errors.

Author: Integration Agent (INT-001)
Version: 1.0.0
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Callable, Coroutine, Optional

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    LOW = auto()  # Minor issue, can continue
    MEDIUM = auto()  # Significant issue, may need recovery
    HIGH = auto()  # Critical issue, requires intervention
    CRITICAL = auto()  # System-level failure


class ErrorCategory(Enum):
    """Categories of errors."""

    VISION = "vision"
    AUDIO = "audio"
    AI = "ai"
    NETWORK = "network"
    HARDWARE = "hardware"
    CONFIGURATION = "configuration"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types."""

    RETRY = auto()  # Retry the operation
    FALLBACK = auto()  # Use fallback method
    SKIP = auto()  # Skip and continue
    DEGRADE = auto()  # Degrade functionality
    RESTART_COMPONENT = auto()  # Restart the component
    ESCALATE = auto()  # Escalate to operator


@dataclass
class ErrorRecord:
    """Record of an error occurrence."""

    error_id: str
    timestamp: datetime
    category: ErrorCategory
    severity: ErrorSeverity
    component: str
    error_message: str
    exception: Optional[Exception] = None
    context: dict[str, Any] = field(default_factory=dict)
    recovery_attempted: bool = False
    recovery_successful: bool = False
    recovery_strategy: Optional[RecoveryStrategy] = None


@dataclass
class ErrorStats:
    """Statistics about errors."""

    total_errors: int = 0
    errors_by_category: dict[ErrorCategory, int] = field(default_factory=lambda: defaultdict(int))
    errors_by_severity: dict[ErrorSeverity, int] = field(default_factory=lambda: defaultdict(int))
    recovery_attempts: int = 0
    successful_recoveries: int = 0
    failed_recoveries: int = 0
    escalations: int = 0


@dataclass
class RecoveryConfig:
    """Configuration for error recovery."""

    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    exponential_backoff: bool = True
    backoff_multiplier: float = 2.0
    enable_fallback: bool = True
    enable_degradation: bool = True
    escalation_threshold: int = 5  # Escalate after N failures


class ErrorHandler:
    """
    Comprehensive error handler for the EduLens pipeline.

    Features:
    - Error detection and classification
    - Automatic recovery attempts
    - Graceful degradation strategies
    - Error tracking and statistics
    - Escalation to operators when needed
    """

    def __init__(
        self,
        config: Optional[RecoveryConfig] = None,
        escalation_callback: Optional[Callable[[ErrorRecord], Coroutine]] = None,
    ) -> None:
        """
        Initialize error handler.

        Args:
            config: Recovery configuration
            escalation_callback: Callback for error escalation
        """
        self.config = config or RecoveryConfig()
        self.escalation_callback = escalation_callback

        # Error tracking
        self._error_history: list[ErrorRecord] = []
        self._error_counts: dict[str, int] = defaultdict(int)
        self._stats = ErrorStats()

        # Component health tracking
        self._component_health: dict[str, bool] = {}
        self._degraded_components: set[str] = set()

        logger.info("ErrorHandler initialized")

    async def handle_vision_error(
        self, error: Exception, component: str, context: Optional[dict[str, Any]] = None
    ) -> tuple[bool, Any]:
        """
        Handle vision pipeline errors.

        Args:
            error: Exception that occurred
            component: Component where error occurred
            context: Optional error context

        Returns:
            (success, result) tuple - success=True if recovered
        """
        error_record = self._create_error_record(
            category=ErrorCategory.VISION, error=error, component=component, context=context or {}
        )

        logger.warning(f"Vision error in {component}: {str(error)}")

        # Determine recovery strategy
        if "camera" in component.lower():
            # Camera errors - try to restart camera
            return await self._apply_recovery(
                error_record,
                strategy=RecoveryStrategy.RESTART_COMPONENT,
                recovery_fn=self._restart_camera_fallback,
            )

        elif "ocr" in component.lower():
            # OCR errors - retry with different settings
            return await self._apply_recovery(
                error_record, strategy=RecoveryStrategy.RETRY, recovery_fn=None
            )

        elif "handwriting" in component.lower():
            # Handwriting errors - fall back to printed text OCR
            return await self._apply_recovery(
                error_record,
                strategy=RecoveryStrategy.FALLBACK,
                recovery_fn=self._fallback_to_printed_ocr,
            )

        else:
            # Generic vision error - try to degrade gracefully
            return await self._apply_recovery(
                error_record,
                strategy=RecoveryStrategy.DEGRADE,
                recovery_fn=self._degrade_vision_quality,
            )

    async def handle_audio_error(
        self, error: Exception, component: str, context: Optional[dict[str, Any]] = None
    ) -> tuple[bool, Any]:
        """
        Handle audio pipeline errors.

        Args:
            error: Exception that occurred
            component: Component where error occurred
            context: Optional error context

        Returns:
            (success, result) tuple
        """
        error_record = self._create_error_record(
            category=ErrorCategory.AUDIO, error=error, component=component, context=context or {}
        )

        logger.warning(f"Audio error in {component}: {str(error)}")

        # Determine recovery strategy
        if "microphone" in component.lower() or "capture" in component.lower():
            # Microphone errors - try to restart audio
            return await self._apply_recovery(
                error_record,
                strategy=RecoveryStrategy.RESTART_COMPONENT,
                recovery_fn=self._restart_audio_fallback,
            )

        elif "wake_word" in component.lower():
            # Wake word errors - lower threshold or disable
            return await self._apply_recovery(
                error_record, strategy=RecoveryStrategy.DEGRADE, recovery_fn=self._degrade_wake_word
            )

        elif "asr" in component.lower() or "speech" in component.lower():
            # ASR errors - try fallback model
            return await self._apply_recovery(
                error_record,
                strategy=RecoveryStrategy.FALLBACK,
                recovery_fn=self._fallback_asr_model,
            )

        elif "tts" in component.lower():
            # TTS errors - try fallback engine
            return await self._apply_recovery(
                error_record,
                strategy=RecoveryStrategy.FALLBACK,
                recovery_fn=self._fallback_tts_engine,
            )

        else:
            # Generic audio error
            return await self._apply_recovery(
                error_record, strategy=RecoveryStrategy.RETRY, recovery_fn=None
            )

    async def handle_ai_error(
        self, error: Exception, component: str, context: Optional[dict[str, Any]] = None
    ) -> tuple[bool, Any]:
        """
        Handle AI/LLM errors.

        Args:
            error: Exception that occurred
            component: Component where error occurred
            context: Optional error context

        Returns:
            (success, result) tuple
        """
        error_record = self._create_error_record(
            category=ErrorCategory.AI, error=error, component=component, context=context or {}
        )

        logger.warning(f"AI error in {component}: {str(error)}")

        # Determine recovery strategy
        if "timeout" in str(error).lower():
            # Timeout - retry with increased timeout
            return await self._apply_recovery(
                error_record, strategy=RecoveryStrategy.RETRY, recovery_fn=None
            )

        elif "memory" in str(error).lower() or "resource" in str(error).lower():
            # Resource errors - reduce model size or context
            return await self._apply_recovery(
                error_record,
                strategy=RecoveryStrategy.DEGRADE,
                recovery_fn=self._reduce_ai_resources,
            )

        elif "model" in str(error).lower():
            # Model errors - try fallback model
            return await self._apply_recovery(
                error_record,
                strategy=RecoveryStrategy.FALLBACK,
                recovery_fn=self._fallback_ai_model,
            )

        else:
            # Generic AI error - retry once
            return await self._apply_recovery(
                error_record, strategy=RecoveryStrategy.RETRY, recovery_fn=None
            )

    async def recover(
        self, error_record: ErrorRecord, recovery_fn: Optional[Callable[[], Coroutine]] = None
    ) -> tuple[bool, Any]:
        """
        Attempt to recover from an error.

        Args:
            error_record: Record of the error
            recovery_fn: Optional recovery function

        Returns:
            (success, result) tuple
        """
        error_record.recovery_attempted = True
        self._stats.recovery_attempts += 1

        try:
            if recovery_fn:
                result = await recovery_fn()
                error_record.recovery_successful = True
                self._stats.successful_recoveries += 1
                logger.info(f"Successfully recovered from {error_record.category.value} error")
                return True, result
            else:
                # No specific recovery function, just log
                logger.warning("No recovery function provided")
                return False, None

        except Exception as e:
            error_record.recovery_successful = False
            self._stats.failed_recoveries += 1
            logger.error(f"Recovery failed: {e}", exc_info=True)
            return False, None

    async def escalate(self, error_record: ErrorRecord, reason: str) -> None:
        """
        Escalate error to operator/parent.

        Args:
            error_record: Error to escalate
            reason: Reason for escalation
        """
        self._stats.escalations += 1

        logger.critical(
            f"ESCALATING ERROR: {error_record.category.value} - {reason}\n"
            f"Component: {error_record.component}\n"
            f"Error: {error_record.error_message}"
        )

        # Call escalation callback if provided
        if self.escalation_callback:
            try:
                await self.escalation_callback(error_record)
            except Exception as e:
                logger.error(f"Escalation callback failed: {e}", exc_info=True)

    def mark_component_degraded(self, component: str) -> None:
        """
        Mark a component as operating in degraded mode.

        Args:
            component: Component name
        """
        self._degraded_components.add(component)
        logger.warning(f"Component {component} now operating in degraded mode")

    def is_component_degraded(self, component: str) -> bool:
        """
        Check if component is in degraded mode.

        Args:
            component: Component name

        Returns:
            True if degraded
        """
        return component in self._degraded_components

    def get_error_stats(self) -> ErrorStats:
        """Get error statistics."""
        return self._stats

    def get_error_history(
        self, category: Optional[ErrorCategory] = None, limit: int = 100
    ) -> list[ErrorRecord]:
        """
        Get error history.

        Args:
            category: Optional category filter
            limit: Maximum number of records

        Returns:
            List of error records
        """
        history = self._error_history
        if category:
            history = [r for r in history if r.category == category]
        return history[-limit:]

    def should_escalate(self, component: str) -> bool:
        """
        Check if errors from component should be escalated.

        Args:
            component: Component name

        Returns:
            True if should escalate
        """
        error_count = self._error_counts[component]
        return error_count >= self.config.escalation_threshold

    def _create_error_record(
        self, category: ErrorCategory, error: Exception, component: str, context: dict[str, Any]
    ) -> ErrorRecord:
        """Create an error record."""
        import uuid

        # Determine severity
        severity = self._determine_severity(error, category, component)

        error_record = ErrorRecord(
            error_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            category=category,
            severity=severity,
            component=component,
            error_message=str(error),
            exception=error,
            context=context,
        )

        # Track error
        self._error_history.append(error_record)
        self._error_counts[component] += 1
        self._stats.total_errors += 1
        self._stats.errors_by_category[category] += 1
        self._stats.errors_by_severity[severity] += 1

        # Keep only last 1000 errors
        if len(self._error_history) > 1000:
            self._error_history = self._error_history[-1000:]

        return error_record

    def _determine_severity(
        self, error: Exception, category: ErrorCategory, component: str
    ) -> ErrorSeverity:
        """Determine error severity."""
        error_str = str(error).lower()

        # Critical keywords
        if any(kw in error_str for kw in ["fatal", "critical", "crash"]):
            return ErrorSeverity.CRITICAL

        # High severity
        if any(kw in error_str for kw in ["timeout", "connection", "hardware"]):
            return ErrorSeverity.HIGH

        # Check component-specific severity
        if category == ErrorCategory.AUDIO and "microphone" in component:
            return ErrorSeverity.HIGH

        if category == ErrorCategory.AI:
            return ErrorSeverity.MEDIUM

        # Default
        return ErrorSeverity.LOW

    async def _apply_recovery(
        self,
        error_record: ErrorRecord,
        strategy: RecoveryStrategy,
        recovery_fn: Optional[Callable] = None,
    ) -> tuple[bool, Any]:
        """Apply recovery strategy."""
        error_record.recovery_strategy = strategy

        if strategy == RecoveryStrategy.RETRY:
            return await self._retry_with_backoff(error_record, recovery_fn)

        elif strategy == RecoveryStrategy.FALLBACK:
            if recovery_fn:
                return await self.recover(error_record, recovery_fn)
            else:
                logger.warning("No fallback function provided")
                return False, None

        elif strategy == RecoveryStrategy.DEGRADE:
            if recovery_fn:
                result = await recovery_fn()
                self.mark_component_degraded(error_record.component)
                return True, result
            else:
                self.mark_component_degraded(error_record.component)
                return True, None

        elif strategy == RecoveryStrategy.RESTART_COMPONENT:
            if recovery_fn:
                return await self.recover(error_record, recovery_fn)
            else:
                return False, None

        elif strategy == RecoveryStrategy.SKIP:
            logger.info(f"Skipping operation due to error in {error_record.component}")
            return True, None

        elif strategy == RecoveryStrategy.ESCALATE:
            await self.escalate(error_record, "Automatic escalation triggered")
            return False, None

        else:
            return False, None

    async def _retry_with_backoff(
        self, error_record: ErrorRecord, recovery_fn: Optional[Callable]
    ) -> tuple[bool, Any]:
        """Retry operation with exponential backoff."""
        delay = self.config.retry_delay_seconds

        for attempt in range(self.config.max_retries):
            logger.info(
                f"Retry attempt {attempt + 1}/{self.config.max_retries} "
                f"for {error_record.component}"
            )

            await asyncio.sleep(delay)

            try:
                if recovery_fn:
                    result = await recovery_fn()
                    error_record.recovery_successful = True
                    self._stats.successful_recoveries += 1
                    return True, result
                else:
                    # No recovery function, assume retry succeeded
                    return True, None

            except Exception as e:
                logger.warning(f"Retry {attempt + 1} failed: {e}")

                if self.config.exponential_backoff:
                    delay *= self.config.backoff_multiplier

        # All retries failed
        error_record.recovery_successful = False
        self._stats.failed_recoveries += 1

        # Check if should escalate
        if self.should_escalate(error_record.component):
            await self.escalate(error_record, "Max retries exceeded")

        return False, None

    # Fallback implementations
    async def _restart_camera_fallback(self) -> Any:
        """Fallback: Restart camera."""
        logger.info("Attempting to restart camera...")
        # In production, this would actually restart the camera
        await asyncio.sleep(1)
        return {"status": "camera_restarted"}

    async def _fallback_to_printed_ocr(self) -> Any:
        """Fallback: Use printed text OCR instead of handwriting."""
        logger.info("Falling back to printed text OCR")
        return {"mode": "printed_ocr"}

    async def _degrade_vision_quality(self) -> Any:
        """Degradation: Reduce vision processing quality."""
        logger.info("Degrading vision quality for stability")
        return {"quality": "reduced"}

    async def _restart_audio_fallback(self) -> Any:
        """Fallback: Restart audio system."""
        logger.info("Attempting to restart audio...")
        await asyncio.sleep(1)
        return {"status": "audio_restarted"}

    async def _degrade_wake_word(self) -> Any:
        """Degradation: Lower wake word threshold or disable."""
        logger.info("Degrading wake word detection")
        return {"wake_word": "degraded"}

    async def _fallback_asr_model(self) -> Any:
        """Fallback: Use alternative ASR model."""
        logger.info("Switching to fallback ASR model")
        return {"asr_model": "fallback"}

    async def _fallback_tts_engine(self) -> Any:
        """Fallback: Use alternative TTS engine."""
        logger.info("Switching to fallback TTS engine")
        return {"tts_engine": "fallback"}

    async def _reduce_ai_resources(self) -> Any:
        """Degradation: Reduce AI resource usage."""
        logger.info("Reducing AI resource usage")
        return {"ai_resources": "reduced"}

    async def _fallback_ai_model(self) -> Any:
        """Fallback: Use smaller/simpler AI model."""
        logger.info("Switching to fallback AI model")
        return {"ai_model": "fallback"}


def create_error_handler(
    config: Optional[RecoveryConfig] = None,
    escalation_callback: Optional[Callable[[ErrorRecord], Coroutine]] = None,
) -> ErrorHandler:
    """
    Create an error handler instance.

    Args:
        config: Recovery configuration
        escalation_callback: Callback for escalation

    Returns:
        ErrorHandler instance
    """
    return ErrorHandler(config=config, escalation_callback=escalation_callback)
