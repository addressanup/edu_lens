"""
Performance Test Fixtures and Utilities for EduLens

Provides specialized fixtures and utilities for performance testing:
- Timing utilities and decorators
- Memory profiling helpers
- Benchmark decorators
- Performance data collection
- Test result reporting
"""

import asyncio
import functools
import gc
import time
import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Generator

import numpy as np
import pytest


# ============================================================================
# Performance Timing Utilities
# ============================================================================


@dataclass
class TimingResult:
    """Result of a timing measurement."""
    operation: str
    duration_ms: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceTimer:
    """High-precision performance timer."""

    def __init__(self, name: str = "operation"):
        self.name = name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.laps: List[float] = []

    def start(self) -> None:
        """Start the timer."""
        self.start_time = time.perf_counter()
        self.laps = []

    def lap(self, label: str = "") -> float:
        """Record a lap time."""
        if self.start_time is None:
            raise RuntimeError("Timer not started")

        lap_time = time.perf_counter()
        lap_duration = (lap_time - self.start_time) * 1000
        self.laps.append((label, lap_duration))
        return lap_duration

    def stop(self) -> TimingResult:
        """Stop the timer and return result."""
        if self.start_time is None:
            raise RuntimeError("Timer not started")

        self.end_time = time.perf_counter()
        duration_ms = (self.end_time - self.start_time) * 1000

        return TimingResult(
            operation=self.name,
            duration_ms=duration_ms,
            timestamp=self.start_time,
            metadata={"laps": self.laps}
        )

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, *args):
        """Context manager exit."""
        self.stop()

    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        if self.start_time is None:
            return 0.0
        current = time.perf_counter()
        return (current - self.start_time) * 1000


@pytest.fixture
def perf_timer():
    """Fixture providing performance timer."""
    return PerformanceTimer


@pytest.fixture
def timer():
    """Simple timer fixture."""
    class SimpleTimer:
        def __init__(self):
            self.start_time = None
            self.elapsed = None

        def __enter__(self):
            self.start_time = time.perf_counter()
            return self

        def __exit__(self, *args):
            self.elapsed = time.perf_counter() - self.start_time

        def elapsed_ms(self) -> float:
            return self.elapsed * 1000 if self.elapsed else 0

    return SimpleTimer()


# ============================================================================
# Memory Profiling Utilities
# ============================================================================


@dataclass
class MemorySnapshot:
    """Memory usage snapshot."""
    timestamp: float
    rss_mb: float
    vms_mb: float
    percent: float
    traced_mb: float = 0.0


class MemoryProfiler:
    """Memory profiling utility."""

    def __init__(self, name: str = "operation"):
        self.name = name
        self.snapshots: List[MemorySnapshot] = []
        self.start_snapshot: Optional[MemorySnapshot] = None
        self.end_snapshot: Optional[MemorySnapshot] = None

        try:
            import psutil
            self.process = psutil.Process()
            self.psutil_available = True
        except ImportError:
            self.process = None
            self.psutil_available = False

    def start(self) -> None:
        """Start memory profiling."""
        gc.collect()
        tracemalloc.start()

        if self.psutil_available:
            mem_info = self.process.memory_info()
            mem_percent = self.process.memory_percent()

            self.start_snapshot = MemorySnapshot(
                timestamp=time.time(),
                rss_mb=mem_info.rss / 1024 / 1024,
                vms_mb=mem_info.vms / 1024 / 1024,
                percent=mem_percent
            )

    def snapshot(self) -> MemorySnapshot:
        """Take a memory snapshot."""
        if not self.psutil_available:
            return MemorySnapshot(
                timestamp=time.time(),
                rss_mb=0,
                vms_mb=0,
                percent=0
            )

        mem_info = self.process.memory_info()
        mem_percent = self.process.memory_percent()

        current, peak = tracemalloc.get_traced_memory()

        snapshot = MemorySnapshot(
            timestamp=time.time(),
            rss_mb=mem_info.rss / 1024 / 1024,
            vms_mb=mem_info.vms / 1024 / 1024,
            percent=mem_percent,
            traced_mb=current / 1024 / 1024
        )

        self.snapshots.append(snapshot)
        return snapshot

    def stop(self) -> Dict[str, Any]:
        """Stop profiling and return statistics."""
        if self.psutil_available:
            mem_info = self.process.memory_info()
            mem_percent = self.process.memory_percent()

            self.end_snapshot = MemorySnapshot(
                timestamp=time.time(),
                rss_mb=mem_info.rss / 1024 / 1024,
                vms_mb=mem_info.vms / 1024 / 1024,
                percent=mem_percent
            )

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        stats = {
            "name": self.name,
            "peak_traced_mb": peak / 1024 / 1024,
        }

        if self.start_snapshot and self.end_snapshot:
            stats.update({
                "start_rss_mb": self.start_snapshot.rss_mb,
                "end_rss_mb": self.end_snapshot.rss_mb,
                "delta_rss_mb": self.end_snapshot.rss_mb - self.start_snapshot.rss_mb,
                "peak_rss_mb": max(s.rss_mb for s in self.snapshots) if self.snapshots else self.end_snapshot.rss_mb,
            })

        return stats

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, *args):
        """Context manager exit."""
        self.stop()


@pytest.fixture
def memory_profiler():
    """Fixture providing memory profiler."""
    return MemoryProfiler


# ============================================================================
# Benchmark Decorators
# ============================================================================


def benchmark(
    name: Optional[str] = None,
    iterations: int = 1,
    warmup: int = 0,
    track_memory: bool = False
):
    """
    Decorator to benchmark a function.

    Args:
        name: Benchmark name
        iterations: Number of iterations to run
        warmup: Number of warmup iterations
        track_memory: Whether to track memory usage
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            bench_name = name or func.__name__

            # Warmup
            for _ in range(warmup):
                func(*args, **kwargs)

            # Benchmark
            timings = []
            memory_stats = None

            if track_memory:
                mem_profiler = MemoryProfiler(bench_name)
                mem_profiler.start()

            for _ in range(iterations):
                start = time.perf_counter()
                result = func(*args, **kwargs)
                duration = (time.perf_counter() - start) * 1000
                timings.append(duration)

                if track_memory:
                    mem_profiler.snapshot()

            if track_memory:
                memory_stats = mem_profiler.stop()

            stats = {
                "name": bench_name,
                "iterations": iterations,
                "mean_ms": np.mean(timings),
                "median_ms": np.median(timings),
                "std_ms": np.std(timings),
                "min_ms": np.min(timings),
                "max_ms": np.max(timings),
            }

            if memory_stats:
                stats["memory"] = memory_stats

            return result, stats

        return wrapper
    return decorator


def async_benchmark(
    name: Optional[str] = None,
    iterations: int = 1,
    warmup: int = 0
):
    """
    Decorator to benchmark an async function.

    Args:
        name: Benchmark name
        iterations: Number of iterations
        warmup: Number of warmup iterations
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            bench_name = name or func.__name__

            # Warmup
            for _ in range(warmup):
                await func(*args, **kwargs)

            # Benchmark
            timings = []

            for _ in range(iterations):
                start = time.perf_counter()
                result = await func(*args, **kwargs)
                duration = (time.perf_counter() - start) * 1000
                timings.append(duration)

            stats = {
                "name": bench_name,
                "iterations": iterations,
                "mean_ms": np.mean(timings),
                "median_ms": np.median(timings),
                "std_ms": np.std(timings),
                "min_ms": np.min(timings),
                "max_ms": np.max(timings),
            }

            return result, stats

        return wrapper
    return decorator


# ============================================================================
# Performance Data Collection
# ============================================================================


class PerformanceCollector:
    """Collect performance metrics during tests."""

    def __init__(self):
        self.metrics: List[Dict[str, Any]] = []

    def record(
        self,
        operation: str,
        duration_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a performance metric."""
        metric = {
            "operation": operation,
            "duration_ms": duration_ms,
            "timestamp": time.time(),
        }

        if metadata:
            metric.update(metadata)

        self.metrics.append(metric)

    def get_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics for an operation."""
        if operation:
            durations = [m["duration_ms"] for m in self.metrics if m["operation"] == operation]
        else:
            durations = [m["duration_ms"] for m in self.metrics]

        if not durations:
            return {}

        return {
            "count": len(durations),
            "mean_ms": np.mean(durations),
            "median_ms": np.median(durations),
            "std_ms": np.std(durations),
            "min_ms": np.min(durations),
            "max_ms": np.max(durations),
            "p95_ms": np.percentile(durations, 95),
            "p99_ms": np.percentile(durations, 99),
        }

    def export(self, path: Path) -> None:
        """Export metrics to JSON file."""
        import json

        with open(path, 'w') as f:
            json.dump({
                "metrics": self.metrics,
                "summary": self.get_stats(),
            }, f, indent=2)


@pytest.fixture
def perf_collector():
    """Fixture providing performance collector."""
    return PerformanceCollector()


# ============================================================================
# Benchmark Comparison Utilities
# ============================================================================


class BenchmarkComparator:
    """Compare benchmark results against baselines."""

    def __init__(self, baseline_path: Optional[Path] = None):
        self.baseline_path = baseline_path
        self.baseline_data = self._load_baseline() if baseline_path else {}

    def _load_baseline(self) -> Dict[str, Any]:
        """Load baseline data from file."""
        import json

        if self.baseline_path and self.baseline_path.exists():
            with open(self.baseline_path, 'r') as f:
                return json.load(f)
        return {}

    def compare(
        self,
        operation: str,
        current_ms: float,
        tolerance: float = 0.1
    ) -> Dict[str, Any]:
        """
        Compare current result against baseline.

        Args:
            operation: Operation name
            current_ms: Current duration in milliseconds
            tolerance: Acceptable degradation (0.1 = 10%)

        Returns:
            Comparison result
        """
        baseline_ms = self.baseline_data.get(operation, {}).get("mean_ms")

        if baseline_ms is None:
            return {
                "status": "no_baseline",
                "current_ms": current_ms,
            }

        delta_ms = current_ms - baseline_ms
        delta_percent = (delta_ms / baseline_ms) * 100

        passed = delta_percent <= (tolerance * 100)

        return {
            "status": "passed" if passed else "regressed",
            "current_ms": current_ms,
            "baseline_ms": baseline_ms,
            "delta_ms": delta_ms,
            "delta_percent": delta_percent,
            "tolerance_percent": tolerance * 100,
        }


@pytest.fixture
def benchmark_comparator(tmp_path):
    """Fixture providing benchmark comparator."""
    baseline_path = tmp_path / "baseline.json"
    return BenchmarkComparator(baseline_path)


# ============================================================================
# Test Markers and Configuration
# ============================================================================


def pytest_configure(config):
    """Configure pytest with performance test markers."""
    config.addinivalue_line(
        "markers",
        "performance: Performance tests (use --performance to run)"
    )
    config.addinivalue_line(
        "markers",
        "slow: Slow performance tests (use --slow to run)"
    )
    config.addinivalue_line(
        "markers",
        "benchmark: Benchmark tests (use --benchmark to run)"
    )


def pytest_addoption(parser):
    """Add command line options for performance tests."""
    parser.addoption(
        "--performance",
        action="store_true",
        default=False,
        help="Run performance tests"
    )
    parser.addoption(
        "--slow",
        action="store_true",
        default=False,
        help="Run slow performance tests"
    )
    parser.addoption(
        "--benchmark",
        action="store_true",
        default=False,
        help="Run benchmark tests"
    )
    parser.addoption(
        "--save-baseline",
        action="store",
        default=None,
        help="Save benchmark results as baseline"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on command line options."""
    if not config.getoption("--performance"):
        skip_perf = pytest.mark.skip(reason="need --performance option to run")
        for item in items:
            if "performance" in item.keywords:
                item.add_marker(skip_perf)

    if not config.getoption("--slow"):
        skip_slow = pytest.mark.skip(reason="need --slow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


# ============================================================================
# Resource Monitoring Fixtures
# ============================================================================


@pytest.fixture
def resource_monitor():
    """Fixture providing resource monitoring."""
    try:
        import psutil

        class ResourceMonitor:
            def __init__(self):
                self.process = psutil.Process()
                self.samples = []

            def sample(self):
                """Take a resource usage sample."""
                self.samples.append({
                    "timestamp": time.time(),
                    "cpu_percent": self.process.cpu_percent(),
                    "memory_mb": self.process.memory_info().rss / 1024 / 1024,
                    "threads": self.process.num_threads(),
                })

            def get_stats(self):
                """Get statistics from samples."""
                if not self.samples:
                    return {}

                cpu_values = [s["cpu_percent"] for s in self.samples]
                mem_values = [s["memory_mb"] for s in self.samples]

                return {
                    "cpu": {
                        "mean": np.mean(cpu_values),
                        "max": np.max(cpu_values),
                        "min": np.min(cpu_values),
                    },
                    "memory": {
                        "mean": np.mean(mem_values),
                        "max": np.max(mem_values),
                        "min": np.min(mem_values),
                    }
                }

        return ResourceMonitor()

    except ImportError:
        pytest.skip("psutil not available")


# ============================================================================
# Latency Assertion Helpers
# ============================================================================


def assert_latency(
    duration_ms: float,
    target_ms: float,
    operation: str = "operation",
    tolerance: float = 0.0
):
    """
    Assert that latency meets target.

    Args:
        duration_ms: Actual duration in milliseconds
        target_ms: Target duration in milliseconds
        operation: Operation name for error message
        tolerance: Acceptable overage (0.1 = 10%)
    """
    max_allowed = target_ms * (1 + tolerance)

    assert duration_ms <= max_allowed, (
        f"{operation} latency {duration_ms:.1f}ms exceeds target "
        f"{target_ms:.1f}ms (max allowed: {max_allowed:.1f}ms)"
    )


@pytest.fixture
def assert_latency_helper():
    """Fixture providing latency assertion helper."""
    return assert_latency


# ============================================================================
# Performance Test Utilities
# ============================================================================


@contextmanager
def measure_time(name: str = "operation") -> Generator[Dict[str, Any], None, None]:
    """
    Context manager to measure execution time.

    Args:
        name: Operation name

    Yields:
        Dict with timing information
    """
    result = {"name": name, "start": time.perf_counter()}

    try:
        yield result
    finally:
        result["end"] = time.perf_counter()
        result["duration_ms"] = (result["end"] - result["start"]) * 1000


@pytest.fixture
def measure():
    """Fixture providing time measurement context manager."""
    return measure_time


# ============================================================================
# Percentile Calculation Helpers
# ============================================================================


def calculate_percentiles(
    values: List[float],
    percentiles: List[int] = [50, 90, 95, 99]
) -> Dict[str, float]:
    """
    Calculate percentiles for a list of values.

    Args:
        values: List of numeric values
        percentiles: Percentiles to calculate

    Returns:
        Dict mapping percentile to value
    """
    if not values:
        return {}

    return {
        f"p{p}": np.percentile(values, p)
        for p in percentiles
    }


@pytest.fixture
def calc_percentiles():
    """Fixture providing percentile calculation helper."""
    return calculate_percentiles
