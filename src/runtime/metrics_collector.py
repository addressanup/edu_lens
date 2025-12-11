"""
Metrics Collector for EduLens

Collects and aggregates operational metrics for monitoring,
debugging, and analytics.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Callable

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics."""

    COUNTER = auto()      # Cumulative count
    GAUGE = auto()        # Current value
    HISTOGRAM = auto()    # Distribution
    TIMER = auto()        # Duration measurements


@dataclass
class MetricValue:
    """A single metric value."""

    name: str
    value: float
    timestamp: datetime
    labels: dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class HistogramBucket:
    """Histogram bucket for distribution metrics."""

    le: float  # Less than or equal
    count: int = 0


@dataclass
class Histogram:
    """Histogram for tracking distributions."""

    name: str
    buckets: list[HistogramBucket]
    sum: float = 0.0
    count: int = 0

    def observe(self, value: float) -> None:
        """Record an observation."""
        self.sum += value
        self.count += 1
        for bucket in self.buckets:
            if value <= bucket.le:
                bucket.count += 1


class MetricsCollector:
    """
    Collects and manages system metrics.

    Provides:
    - Counter metrics (requests, errors, etc.)
    - Gauge metrics (battery, memory, etc.)
    - Histogram metrics (latency distributions)
    - Timer metrics (operation durations)
    """

    def __init__(
        self,
        flush_interval_seconds: int = 60,
        retention_hours: int = 24,
    ) -> None:
        self.flush_interval = flush_interval_seconds
        self.retention_hours = retention_hours

        # Metric storage
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, Histogram] = {}
        self._timers: dict[str, list[float]] = defaultdict(list)

        # Time series data
        self._time_series: dict[str, list[MetricValue]] = defaultdict(list)

        # Labels for metrics
        self._labels: dict[str, dict[str, str]] = {}

        # Callbacks
        self._on_flush: Callable[[dict[str, Any]], None] | None = None

        # Background task
        self._flush_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start the metrics collector."""
        logger.info("Starting metrics collector")
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())

    async def stop(self) -> None:
        """Stop the metrics collector."""
        logger.info("Stopping metrics collector")
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Final flush
        await self._flush()

    async def _flush_loop(self) -> None:
        """Background flush loop."""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics flush error: {e}")

    async def _flush(self) -> None:
        """Flush metrics to storage/callback."""
        snapshot = self.get_snapshot()

        if self._on_flush:
            try:
                self._on_flush(snapshot)
            except Exception as e:
                logger.error(f"Metrics callback error: {e}")

        # Clean old time series data
        self._cleanup_old_data()

    def _cleanup_old_data(self) -> None:
        """Remove data older than retention period."""
        cutoff = datetime.utcnow() - timedelta(hours=self.retention_hours)

        for name in list(self._time_series.keys()):
            self._time_series[name] = [
                v for v in self._time_series[name]
                if v.timestamp > cutoff
            ]
            if not self._time_series[name]:
                del self._time_series[name]

    # Counter methods
    def increment(
        self,
        name: str,
        value: float = 1.0,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Increment a counter metric."""
        key = self._make_key(name, labels)
        self._counters[key] += value

        self._record_time_series(name, self._counters[key], MetricType.COUNTER, labels)

    def get_counter(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Get a counter value."""
        key = self._make_key(name, labels)
        return self._counters.get(key, 0.0)

    # Gauge methods
    def set_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Set a gauge metric."""
        key = self._make_key(name, labels)
        self._gauges[key] = value

        self._record_time_series(name, value, MetricType.GAUGE, labels)

    def get_gauge(self, name: str, labels: dict[str, str] | None = None) -> float | None:
        """Get a gauge value."""
        key = self._make_key(name, labels)
        return self._gauges.get(key)

    # Histogram methods
    def create_histogram(
        self,
        name: str,
        buckets: list[float] | None = None,
    ) -> None:
        """Create a histogram metric."""
        if buckets is None:
            # Default latency buckets in ms
            buckets = [10, 25, 50, 100, 250, 500, 1000, 2000, 5000, 10000]

        bucket_objects = [HistogramBucket(le=b) for b in sorted(buckets)]
        bucket_objects.append(HistogramBucket(le=float("inf")))

        self._histograms[name] = Histogram(name=name, buckets=bucket_objects)

    def observe_histogram(self, name: str, value: float) -> None:
        """Record a histogram observation."""
        if name not in self._histograms:
            self.create_histogram(name)

        self._histograms[name].observe(value)

    def get_histogram(self, name: str) -> Histogram | None:
        """Get a histogram."""
        return self._histograms.get(name)

    # Timer methods
    def record_timer(
        self,
        name: str,
        duration_ms: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record a timer measurement."""
        key = self._make_key(name, labels)
        self._timers[key].append(duration_ms)

        # Keep last 1000 measurements
        if len(self._timers[key]) > 1000:
            self._timers[key] = self._timers[key][-1000:]

        self._record_time_series(name, duration_ms, MetricType.TIMER, labels)

    def get_timer_stats(
        self,
        name: str,
        labels: dict[str, str] | None = None,
    ) -> dict[str, float] | None:
        """Get timer statistics."""
        key = self._make_key(name, labels)
        values = self._timers.get(key)

        if not values:
            return None

        sorted_values = sorted(values)
        count = len(values)

        return {
            "count": count,
            "sum": sum(values),
            "avg": sum(values) / count,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "p50": sorted_values[int(count * 0.5)],
            "p95": sorted_values[int(count * 0.95)],
            "p99": sorted_values[int(count * 0.99)],
        }

    # Helper methods
    def _make_key(self, name: str, labels: dict[str, str] | None) -> str:
        """Create a unique key for a metric with labels."""
        if not labels:
            return name

        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def _record_time_series(
        self,
        name: str,
        value: float,
        metric_type: MetricType,
        labels: dict[str, str] | None,
    ) -> None:
        """Record a time series data point."""
        metric_value = MetricValue(
            name=name,
            value=value,
            timestamp=datetime.utcnow(),
            labels=labels or {},
            metric_type=metric_type,
        )
        self._time_series[name].append(metric_value)

    def get_snapshot(self) -> dict[str, Any]:
        """Get a snapshot of all metrics."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                name: {
                    "count": h.count,
                    "sum": h.sum,
                    "avg": h.sum / h.count if h.count > 0 else 0,
                    "buckets": {b.le: b.count for b in h.buckets},
                }
                for name, h in self._histograms.items()
            },
            "timers": {
                name: self.get_timer_stats(name)
                for name in self._timers.keys()
            },
        }

    def get_time_series(
        self,
        name: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[MetricValue]:
        """Get time series data for a metric."""
        values = self._time_series.get(name, [])

        if start:
            values = [v for v in values if v.timestamp >= start]
        if end:
            values = [v for v in values if v.timestamp <= end]

        return values

    def on_flush(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Register flush callback."""
        self._on_flush = callback

    # Convenience methods for common metrics
    def record_request(
        self,
        success: bool = True,
        latency_ms: float | None = None,
    ) -> None:
        """Record a request metric."""
        self.increment("requests_total")
        if success:
            self.increment("requests_success")
        else:
            self.increment("requests_failed")

        if latency_ms is not None:
            self.observe_histogram("request_latency_ms", latency_ms)

    def record_error(self, error_type: str) -> None:
        """Record an error metric."""
        self.increment("errors_total")
        self.increment("errors_total", labels={"type": error_type})

    def update_system_metrics(
        self,
        cpu_percent: float,
        memory_mb: float,
        battery_percent: int,
        temperature_celsius: float,
    ) -> None:
        """Update system gauge metrics."""
        self.set_gauge("system_cpu_percent", cpu_percent)
        self.set_gauge("system_memory_mb", memory_mb)
        self.set_gauge("system_battery_percent", battery_percent)
        self.set_gauge("system_temperature_celsius", temperature_celsius)


# Global metrics instance
_metrics: MetricsCollector | None = None


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector."""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


def create_metrics_collector(
    flush_interval_seconds: int = 60,
    retention_hours: int = 24,
) -> MetricsCollector:
    """Factory function to create metrics collector."""
    return MetricsCollector(
        flush_interval_seconds=flush_interval_seconds,
        retention_hours=retention_hours,
    )
