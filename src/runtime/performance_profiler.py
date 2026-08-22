"""
Performance Profiler for EduLens

Monitors and profiles system performance to ensure
latency targets are met (<2s response time).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Pipeline stages for latency tracking."""

    WAKE_WORD_DETECTION = auto()
    AUDIO_CAPTURE = auto()
    SPEECH_TO_TEXT = auto()
    VISUAL_CAPTURE = auto()
    OCR_PROCESSING = auto()
    HANDWRITING_RECOGNITION = auto()
    LAYOUT_ANALYSIS = auto()
    CONTEXT_BUILDING = auto()
    AI_INFERENCE = auto()
    RESPONSE_GENERATION = auto()
    TEXT_TO_SPEECH = auto()
    AUDIO_PLAYBACK = auto()
    TOTAL_E2E = auto()


@dataclass
class LatencyMeasurement:
    """Single latency measurement."""

    stage: PipelineStage
    duration_ms: float
    timestamp: datetime
    success: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StageStats:
    """Statistics for a pipeline stage."""

    stage: PipelineStage
    count: int = 0
    total_ms: float = 0.0
    min_ms: float = float("inf")
    max_ms: float = 0.0
    failures: int = 0

    @property
    def avg_ms(self) -> float:
        """Average latency in milliseconds."""
        return self.total_ms / self.count if self.count > 0 else 0.0

    def add_measurement(self, duration_ms: float, success: bool = True) -> None:
        """Add a measurement."""
        self.count += 1
        self.total_ms += duration_ms
        self.min_ms = min(self.min_ms, duration_ms)
        self.max_ms = max(self.max_ms, duration_ms)
        if not success:
            self.failures += 1


@dataclass
class PerformanceReport:
    """Performance report for a time period."""

    start_time: datetime
    end_time: datetime
    stage_stats: dict[PipelineStage, StageStats]
    e2e_latency_avg_ms: float
    e2e_latency_p95_ms: float
    e2e_latency_p99_ms: float
    total_requests: int
    failed_requests: int
    latency_target_met_percent: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "e2e_latency_avg_ms": self.e2e_latency_avg_ms,
            "e2e_latency_p95_ms": self.e2e_latency_p95_ms,
            "e2e_latency_p99_ms": self.e2e_latency_p99_ms,
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "latency_target_met_percent": self.latency_target_met_percent,
            "stages": {
                stage.name: {
                    "avg_ms": stats.avg_ms,
                    "min_ms": stats.min_ms if stats.min_ms != float("inf") else 0,
                    "max_ms": stats.max_ms,
                    "count": stats.count,
                }
                for stage, stats in self.stage_stats.items()
            },
        }


class PerformanceProfiler:
    """
    Profiles system performance and tracks latencies.

    Ensures the system meets the <2s response latency target.
    """

    def __init__(
        self,
        latency_target_ms: float = 2000.0,
        history_size: int = 1000,
    ) -> None:
        self.latency_target_ms = latency_target_ms
        self.history_size = history_size

        # Measurements
        self._measurements: list[LatencyMeasurement] = []
        self._stage_stats: dict[PipelineStage, StageStats] = {
            stage: StageStats(stage=stage) for stage in PipelineStage
        }

        # Active timers (for async operations)
        self._active_timers: dict[str, tuple[PipelineStage, float]] = {}

        # E2E latencies for percentile calculation
        self._e2e_latencies: list[float] = []

        # Callbacks
        self._on_latency_exceeded: Callable[[PipelineStage, float], None] | None = None

        # Report period
        self._report_start = datetime.utcnow()

    def start_timer(self, timer_id: str, stage: PipelineStage) -> None:
        """Start a timer for a pipeline stage."""
        self._active_timers[timer_id] = (stage, time.perf_counter())

    def stop_timer(
        self,
        timer_id: str,
        success: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> float:
        """
        Stop a timer and record the measurement.

        Returns duration in milliseconds.
        """
        if timer_id not in self._active_timers:
            logger.warning(f"Timer {timer_id} not found")
            return 0.0

        stage, start_time = self._active_timers.pop(timer_id)
        duration_ms = (time.perf_counter() - start_time) * 1000

        self._record_measurement(stage, duration_ms, success, metadata or {})

        return duration_ms

    def record_latency(
        self,
        stage: PipelineStage,
        duration_ms: float,
        success: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a latency measurement directly."""
        self._record_measurement(stage, duration_ms, success, metadata or {})

    def _record_measurement(
        self,
        stage: PipelineStage,
        duration_ms: float,
        success: bool,
        metadata: dict[str, Any],
    ) -> None:
        """Record a measurement."""
        measurement = LatencyMeasurement(
            stage=stage,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow(),
            success=success,
            metadata=metadata,
        )

        # Add to history
        self._measurements.append(measurement)
        if len(self._measurements) > self.history_size:
            self._measurements = self._measurements[-self.history_size :]

        # Update stage stats
        self._stage_stats[stage].add_measurement(duration_ms, success)

        # Track E2E latencies
        if stage == PipelineStage.TOTAL_E2E:
            self._e2e_latencies.append(duration_ms)
            if len(self._e2e_latencies) > self.history_size:
                self._e2e_latencies = self._e2e_latencies[-self.history_size :]

            # Check target
            if duration_ms > self.latency_target_ms:
                logger.warning(
                    f"E2E latency exceeded target: {duration_ms:.0f}ms > {self.latency_target_ms}ms"
                )
                if self._on_latency_exceeded:
                    self._on_latency_exceeded(stage, duration_ms)

    def get_stage_stats(self, stage: PipelineStage) -> StageStats:
        """Get statistics for a pipeline stage."""
        return self._stage_stats[stage]

    def get_all_stats(self) -> dict[PipelineStage, StageStats]:
        """Get statistics for all stages."""
        return self._stage_stats.copy()

    def get_percentile(self, percentile: float) -> float:
        """Get latency percentile (0-100)."""
        if not self._e2e_latencies:
            return 0.0

        sorted_latencies = sorted(self._e2e_latencies)
        index = int(len(sorted_latencies) * percentile / 100)
        index = min(index, len(sorted_latencies) - 1)
        return sorted_latencies[index]

    def get_target_met_percent(self) -> float:
        """Get percentage of requests meeting latency target."""
        if not self._e2e_latencies:
            return 100.0

        met_count = sum(1 for lat in self._e2e_latencies if lat <= self.latency_target_ms)
        return (met_count / len(self._e2e_latencies)) * 100

    def generate_report(self) -> PerformanceReport:
        """Generate a performance report."""
        now = datetime.utcnow()

        e2e_stats = self._stage_stats[PipelineStage.TOTAL_E2E]

        report = PerformanceReport(
            start_time=self._report_start,
            end_time=now,
            stage_stats=self._stage_stats.copy(),
            e2e_latency_avg_ms=e2e_stats.avg_ms,
            e2e_latency_p95_ms=self.get_percentile(95),
            e2e_latency_p99_ms=self.get_percentile(99),
            total_requests=e2e_stats.count,
            failed_requests=e2e_stats.failures,
            latency_target_met_percent=self.get_target_met_percent(),
        )

        return report

    def reset_stats(self) -> None:
        """Reset all statistics."""
        self._measurements.clear()
        self._e2e_latencies.clear()
        self._stage_stats = {stage: StageStats(stage=stage) for stage in PipelineStage}
        self._report_start = datetime.utcnow()

    def on_latency_exceeded(
        self,
        callback: Callable[[PipelineStage, float], None],
    ) -> None:
        """Register callback for latency exceeded events."""
        self._on_latency_exceeded = callback

    def identify_bottleneck(self) -> PipelineStage | None:
        """Identify the stage with highest average latency."""
        max_avg = 0.0
        bottleneck = None

        for stage, stats in self._stage_stats.items():
            if stage == PipelineStage.TOTAL_E2E:
                continue
            if stats.count > 0 and stats.avg_ms > max_avg:
                max_avg = stats.avg_ms
                bottleneck = stage

        return bottleneck

    def get_latency_breakdown(self) -> dict[str, float]:
        """Get latency breakdown by stage as percentages."""
        e2e_avg = self._stage_stats[PipelineStage.TOTAL_E2E].avg_ms
        if e2e_avg <= 0:
            return {}

        breakdown = {}
        for stage, stats in self._stage_stats.items():
            if stage == PipelineStage.TOTAL_E2E:
                continue
            if stats.count > 0:
                breakdown[stage.name] = (stats.avg_ms / e2e_avg) * 100

        return breakdown


class RequestProfiler:
    """Context manager for profiling a complete request."""

    def __init__(
        self,
        profiler: PerformanceProfiler,
        request_id: str,
    ) -> None:
        self.profiler = profiler
        self.request_id = request_id
        self._start_time: float | None = None
        self._stage_times: dict[PipelineStage, float] = {}

    def __enter__(self) -> "RequestProfiler":
        """Start profiling."""
        self._start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """End profiling and record total."""
        if self._start_time is not None:
            total_ms = (time.perf_counter() - self._start_time) * 1000
            self.profiler.record_latency(
                PipelineStage.TOTAL_E2E,
                total_ms,
                success=exc_type is None,
                metadata={"request_id": self.request_id},
            )

    def mark_stage(self, stage: PipelineStage) -> None:
        """Mark completion of a stage."""
        now = time.perf_counter()

        if self._start_time is None:
            return

        # Calculate duration since last stage or start
        if self._stage_times:
            last_time = max(self._stage_times.values())
        else:
            last_time = self._start_time

        duration_ms = (now - last_time) * 1000
        self._stage_times[stage] = now

        self.profiler.record_latency(stage, duration_ms)


def create_profiler(
    latency_target_ms: float = 2000.0,
) -> PerformanceProfiler:
    """Factory function to create performance profiler."""
    return PerformanceProfiler(latency_target_ms=latency_target_ms)
