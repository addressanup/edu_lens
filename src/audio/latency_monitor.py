"""
Latency Monitor for EduLens Audio Pipeline

Tracks end-to-end latency and individual stage timings to ensure
sub-2-second response time from speech end to response start.
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Pipeline stages for latency tracking."""
    WAKE_WORD_DETECTION = "wake_word_detection"
    SPEECH_START = "speech_start"
    SPEECH_END = "speech_end"
    ASR_START = "asr_start"
    ASR_END = "asr_end"
    NLU_START = "nlu_start"
    NLU_END = "nlu_end"
    RESPONSE_GENERATION = "response_generation"
    TTS_START = "tts_start"
    TTS_END = "tts_end"
    PLAYBACK_START = "playback_start"
    PLAYBACK_END = "playback_end"


@dataclass
class Checkpoint:
    """Single timing checkpoint."""
    stage: PipelineStage
    timestamp: float
    metadata: Dict = field(default_factory=dict)

    @property
    def stage_name(self) -> str:
        """Get human-readable stage name."""
        return self.stage.value


@dataclass
class LatencyMetrics:
    """Latency metrics for a complete pipeline execution."""
    session_id: str
    total_latency: float  # Total end-to-end (ms)
    stage_latencies: Dict[str, float]  # Per-stage latencies (ms)
    checkpoints: List[Checkpoint]
    start_time: float
    end_time: float
    exceeded_threshold: bool = False

    @property
    def duration(self) -> float:
        """Total duration in seconds."""
        return (self.end_time - self.start_time)

    def get_stage_latency(self, stage: PipelineStage) -> Optional[float]:
        """Get latency for specific stage (ms)."""
        return self.stage_latencies.get(stage.value)

    def get_breakdown(self) -> Dict[str, float]:
        """Get percentage breakdown of latencies."""
        if self.total_latency == 0:
            return {}

        return {
            stage: (latency / self.total_latency) * 100
            for stage, latency in self.stage_latencies.items()
        }


@dataclass
class LatencyStats:
    """Aggregate latency statistics."""
    total_sessions: int = 0
    avg_latency: float = 0.0
    min_latency: float = float('inf')
    max_latency: float = 0.0
    p50_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0
    threshold_violations: int = 0
    violation_rate: float = 0.0

    # Per-stage statistics
    stage_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)


class LatencyMonitor:
    """
    Monitor and track pipeline latency.

    Tracks timing through all pipeline stages and provides:
    - Real-time latency measurement
    - Stage-by-stage breakdown
    - Threshold violation alerts
    - Historical statistics
    """

    def __init__(
        self,
        threshold_ms: float = 2000.0,
        alert_callback: Optional[Callable[[LatencyMetrics], None]] = None,
        history_size: int = 100
    ):
        """
        Initialize latency monitor.

        Args:
            threshold_ms: Latency threshold in milliseconds
            alert_callback: Callback when threshold exceeded
            history_size: Number of sessions to keep in history
        """
        self.threshold_ms = threshold_ms
        self.alert_callback = alert_callback
        self.history_size = history_size

        # Active sessions (session_id -> checkpoints)
        self._active_sessions: Dict[str, List[Checkpoint]] = {}
        self._session_start_times: Dict[str, float] = {}

        # Historical data
        self._history: deque = deque(maxlen=history_size)
        self._latency_buffer: deque = deque(maxlen=history_size)

        # Statistics
        self._stats = LatencyStats()
        self._stage_times: Dict[str, List[float]] = defaultdict(list)

        logger.info(f"Initialized LatencyMonitor with {threshold_ms}ms threshold")

    def start_timer(self, session_id: str) -> None:
        """
        Start timing a new session.

        Args:
            session_id: Unique session identifier
        """
        current_time = time.time()
        self._active_sessions[session_id] = []
        self._session_start_times[session_id] = current_time

        logger.debug(f"Started timing session: {session_id}")

    def record_checkpoint(
        self,
        session_id: str,
        stage: PipelineStage,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Record a pipeline stage checkpoint.

        Args:
            session_id: Session identifier
            stage: Pipeline stage
            metadata: Optional metadata for checkpoint
        """
        if session_id not in self._active_sessions:
            logger.warning(f"Unknown session: {session_id}")
            return

        checkpoint = Checkpoint(
            stage=stage,
            timestamp=time.time(),
            metadata=metadata or {}
        )

        self._active_sessions[session_id].append(checkpoint)

        logger.debug(
            f"Checkpoint [{session_id}] {stage.value}: "
            f"{(checkpoint.timestamp - self._session_start_times[session_id]) * 1000:.1f}ms"
        )

    def get_total_latency(self, session_id: str) -> Optional[float]:
        """
        Get total latency for session so far.

        Args:
            session_id: Session identifier

        Returns:
            Latency in milliseconds, or None if session not found
        """
        if session_id not in self._active_sessions:
            return None

        if not self._active_sessions[session_id]:
            return 0.0

        start_time = self._session_start_times[session_id]
        current_time = time.time()

        return (current_time - start_time) * 1000

    def get_breakdown(self, session_id: str) -> Dict[str, float]:
        """
        Get latency breakdown by stage.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary of stage -> latency (ms)
        """
        if session_id not in self._active_sessions:
            return {}

        checkpoints = self._active_sessions[session_id]
        if len(checkpoints) < 2:
            return {}

        breakdown = {}
        for i in range(1, len(checkpoints)):
            prev_checkpoint = checkpoints[i - 1]
            curr_checkpoint = checkpoints[i]

            stage_name = f"{prev_checkpoint.stage.value}_to_{curr_checkpoint.stage.value}"
            latency = (curr_checkpoint.timestamp - prev_checkpoint.timestamp) * 1000

            breakdown[stage_name] = latency

        return breakdown

    def end_timer(self, session_id: str) -> LatencyMetrics:
        """
        End timing and compute metrics.

        Args:
            session_id: Session identifier

        Returns:
            LatencyMetrics for the session
        """
        if session_id not in self._active_sessions:
            logger.warning(f"Unknown session: {session_id}")
            return self._create_empty_metrics(session_id)

        # Get session data
        checkpoints = self._active_sessions[session_id]
        start_time = self._session_start_times[session_id]
        end_time = time.time()

        # Calculate total latency
        total_latency = (end_time - start_time) * 1000  # ms

        # Calculate stage latencies
        stage_latencies = self._calculate_stage_latencies(checkpoints)

        # Check threshold
        exceeded_threshold = total_latency > self.threshold_ms

        # Create metrics
        metrics = LatencyMetrics(
            session_id=session_id,
            total_latency=total_latency,
            stage_latencies=stage_latencies,
            checkpoints=checkpoints,
            start_time=start_time,
            end_time=end_time,
            exceeded_threshold=exceeded_threshold
        )

        # Update statistics
        self._update_statistics(metrics)

        # Add to history
        self._history.append(metrics)
        self._latency_buffer.append(total_latency)

        # Clean up session
        del self._active_sessions[session_id]
        del self._session_start_times[session_id]

        # Alert if threshold exceeded
        if exceeded_threshold:
            logger.warning(
                f"Latency threshold exceeded for session {session_id}: "
                f"{total_latency:.1f}ms > {self.threshold_ms}ms"
            )
            if self.alert_callback:
                try:
                    self.alert_callback(metrics)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")

        logger.info(
            f"Session {session_id} completed: {total_latency:.1f}ms total latency"
        )

        return metrics

    def get_statistics(self) -> LatencyStats:
        """
        Get aggregate latency statistics.

        Returns:
            LatencyStats with current statistics
        """
        return self._stats

    def get_recent_sessions(self, count: int = 10) -> List[LatencyMetrics]:
        """
        Get recent session metrics.

        Args:
            count: Number of recent sessions to return

        Returns:
            List of recent LatencyMetrics
        """
        return list(self._history)[-count:]

    def get_percentile(self, percentile: float) -> float:
        """
        Get latency percentile.

        Args:
            percentile: Percentile (0-100)

        Returns:
            Latency at percentile (ms)
        """
        if not self._latency_buffer:
            return 0.0

        return float(np.percentile(list(self._latency_buffer), percentile))

    def is_healthy(self) -> bool:
        """
        Check if pipeline is meeting latency targets.

        Returns:
            True if healthy (p95 < threshold), False otherwise
        """
        if self._stats.total_sessions < 5:
            # Need minimum samples
            return True

        return self._stats.p95_latency < self.threshold_ms

    def reset_statistics(self) -> None:
        """Reset all statistics."""
        self._stats = LatencyStats()
        self._stage_times.clear()
        logger.info("Reset latency statistics")

    def _calculate_stage_latencies(
        self,
        checkpoints: List[Checkpoint]
    ) -> Dict[str, float]:
        """
        Calculate latencies between stages.

        Args:
            checkpoints: List of checkpoints

        Returns:
            Dictionary of stage -> latency (ms)
        """
        latencies = {}

        for i in range(1, len(checkpoints)):
            prev_checkpoint = checkpoints[i - 1]
            curr_checkpoint = checkpoints[i]

            # Calculate latency for this transition
            stage_name = f"{prev_checkpoint.stage.value}_to_{curr_checkpoint.stage.value}"
            latency = (curr_checkpoint.timestamp - prev_checkpoint.timestamp) * 1000

            latencies[stage_name] = latency

            # Also record individual stage latencies
            latencies[curr_checkpoint.stage.value] = latency

        return latencies

    def _update_statistics(self, metrics: LatencyMetrics) -> None:
        """
        Update aggregate statistics.

        Args:
            metrics: Latest session metrics
        """
        # Update total sessions
        self._stats.total_sessions += 1

        # Update latency stats
        total = metrics.total_latency
        n = self._stats.total_sessions

        self._stats.avg_latency = (
            (self._stats.avg_latency * (n - 1) + total) / n
        )
        self._stats.min_latency = min(self._stats.min_latency, total)
        self._stats.max_latency = max(self._stats.max_latency, total)

        # Update threshold violations
        if metrics.exceeded_threshold:
            self._stats.threshold_violations += 1

        self._stats.violation_rate = (
            self._stats.threshold_violations / self._stats.total_sessions
        )

        # Update percentiles (if we have enough samples)
        if len(self._latency_buffer) >= 10:
            self._stats.p50_latency = self.get_percentile(50)
            self._stats.p95_latency = self.get_percentile(95)
            self._stats.p99_latency = self.get_percentile(99)

        # Update per-stage statistics
        for stage_name, latency in metrics.stage_latencies.items():
            self._stage_times[stage_name].append(latency)

            if stage_name not in self._stats.stage_stats:
                self._stats.stage_stats[stage_name] = {
                    'avg': 0.0,
                    'min': float('inf'),
                    'max': 0.0
                }

            stage_times = self._stage_times[stage_name]
            self._stats.stage_stats[stage_name] = {
                'avg': float(np.mean(stage_times)),
                'min': float(np.min(stage_times)),
                'max': float(np.max(stage_times)),
                'p95': float(np.percentile(stage_times, 95)) if len(stage_times) >= 10 else 0.0
            }

    def _create_empty_metrics(self, session_id: str) -> LatencyMetrics:
        """
        Create empty metrics for invalid session.

        Args:
            session_id: Session identifier

        Returns:
            Empty LatencyMetrics
        """
        current_time = time.time()
        return LatencyMetrics(
            session_id=session_id,
            total_latency=0.0,
            stage_latencies={},
            checkpoints=[],
            start_time=current_time,
            end_time=current_time
        )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"LatencyMonitor("
            f"sessions={self._stats.total_sessions}, "
            f"avg={self._stats.avg_latency:.1f}ms, "
            f"p95={self._stats.p95_latency:.1f}ms, "
            f"violations={self._stats.violation_rate * 100:.1f}%"
            f")"
        )


class AsyncLatencyMonitor:
    """
    Async wrapper for LatencyMonitor.

    Provides async event notifications for latency alerts.
    """

    def __init__(
        self,
        threshold_ms: float = 2000.0,
        history_size: int = 100
    ):
        """
        Initialize async latency monitor.

        Args:
            threshold_ms: Latency threshold in milliseconds
            history_size: Number of sessions to keep in history
        """
        self._monitor = LatencyMonitor(
            threshold_ms=threshold_ms,
            alert_callback=self._on_alert,
            history_size=history_size
        )
        self._alert_queue: asyncio.Queue = asyncio.Queue()
        self._callbacks: List[Callable] = []

    def start_timer(self, session_id: str) -> None:
        """Start timing a session."""
        self._monitor.start_timer(session_id)

    def record_checkpoint(
        self,
        session_id: str,
        stage: PipelineStage,
        metadata: Optional[Dict] = None
    ) -> None:
        """Record a checkpoint."""
        self._monitor.record_checkpoint(session_id, stage, metadata)

    def get_total_latency(self, session_id: str) -> Optional[float]:
        """Get total latency so far."""
        return self._monitor.get_total_latency(session_id)

    def get_breakdown(self, session_id: str) -> Dict[str, float]:
        """Get latency breakdown."""
        return self._monitor.get_breakdown(session_id)

    def end_timer(self, session_id: str) -> LatencyMetrics:
        """End timing and get metrics."""
        return self._monitor.end_timer(session_id)

    def get_statistics(self) -> LatencyStats:
        """Get aggregate statistics."""
        return self._monitor.get_statistics()

    def is_healthy(self) -> bool:
        """Check if pipeline is healthy."""
        return self._monitor.is_healthy()

    async def wait_for_alert(self, timeout: float = None) -> Optional[LatencyMetrics]:
        """
        Wait for next latency alert.

        Args:
            timeout: Maximum time to wait (seconds)

        Returns:
            LatencyMetrics that triggered alert, or None on timeout
        """
        try:
            if timeout:
                metrics = await asyncio.wait_for(
                    self._alert_queue.get(),
                    timeout=timeout
                )
            else:
                metrics = await self._alert_queue.get()

            return metrics

        except asyncio.TimeoutError:
            return None

    def register_callback(self, callback: Callable[[LatencyMetrics], None]) -> None:
        """
        Register callback for latency alerts.

        Args:
            callback: Callback function
        """
        self._callbacks.append(callback)

    def _on_alert(self, metrics: LatencyMetrics) -> None:
        """
        Handle latency alert.

        Args:
            metrics: Metrics that triggered alert
        """
        # Put in queue
        try:
            self._alert_queue.put_nowait(metrics)
        except asyncio.QueueFull:
            logger.warning("Alert queue full, dropping alert")

        # Notify callbacks
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(metrics))
                else:
                    callback(metrics)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")

    def reset_statistics(self) -> None:
        """Reset statistics."""
        self._monitor.reset_statistics()

    def __repr__(self) -> str:
        """String representation."""
        return repr(self._monitor)
