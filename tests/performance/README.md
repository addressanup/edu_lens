# EduLens Performance Test Suite

Comprehensive performance benchmarks and stress tests for the EduLens project.

## Overview

This performance test suite measures and validates system performance across five key areas:

1. **Latency Benchmarks** - Response time measurements
2. **Memory Usage** - Memory profiling and leak detection
3. **Throughput** - Processing capacity and concurrency
4. **Resource Usage** - CPU, GPU, disk, and network utilization
5. **Stress Tests** - System stability under load

## Performance Targets

### Latency Targets
- OCR Processing: <500ms
- ASR Transcription: <300ms
- TTS Synthesis: <400ms
- AI Response: <1000ms
- End-to-End: <2000ms

### Memory Targets
- Baseline Footprint: <100MB
- OCR Peak: <150MB
- ASR Peak: <200MB
- TTS Peak: <100MB
- Memory Leak: <10MB per 1000 operations

### Throughput Targets
- OCR FPS: ≥2.0
- ASR Realtime Factor: <0.3
- TTS Words/Second: ≥10
- Concurrent Requests: ≥5

## Installation

Install test dependencies:

```bash
# Core dependencies
pip install pytest pytest-asyncio pytest-timeout

# Performance testing
pip install pytest-benchmark psutil memory_profiler

# Optional (for detailed profiling)
pip install py-spy
```

## Running Tests

### Quick Start

Run all performance benchmarks:

```bash
cd /Users/anuppandey/Desktop/edu_lens/tests/performance
python benchmarks.py
```

### Run Specific Test Suites

```bash
# Latency benchmarks only
pytest test_latency_benchmarks.py --performance -v

# Memory tests only
pytest test_memory_usage.py --performance -v

# Throughput tests
pytest test_throughput.py --performance -v

# Resource usage tests
pytest test_resource_usage.py --performance -v

# Stress tests (slow)
pytest test_stress.py --performance --slow -v
```

### Benchmark Runner Options

```bash
# Generate HTML report
python benchmarks.py --format html --output-dir ./results

# Quick mode (skip slow tests)
python benchmarks.py --quick

# Verbose output
python benchmarks.py --verbose

# Compare against baseline
python benchmarks.py --compare baseline.json

# Save new baseline
python benchmarks.py --save-baseline
```

## Test Files

### 1. test_latency_benchmarks.py

Tests response time across all major operations:

- **OCR Latency**: Cold start, warm, preprocessing, text recognition
- **ASR Latency**: Transcription, streaming, model loading
- **TTS Latency**: Short/medium text, cache hits
- **AI Response Latency**: Simple queries, context handling
- **E2E Latency**: Complete voice query flow, OCR query flow
- **Percentile Analysis**: P50, P95, P99 measurements

**Key Tests:**
- `test_ocr_cold_start_latency` - Initial OCR processing time
- `test_asr_realtime_factor` - ASR speed vs audio duration
- `test_e2e_voice_query_latency` - Complete interaction latency

### 2. test_memory_usage.py

Memory profiling and leak detection:

- **Baseline Memory**: Component initialization footprint
- **Peak Memory**: Maximum usage during operations
- **Memory Leaks**: Growth over repeated operations
- **Long-Running**: Stability over extended sessions

**Key Tests:**
- `test_ocr_memory_leak` - Detect OCR memory leaks
- `test_asr_peak_memory` - ASR peak memory usage
- `test_memory_stability_extended` - 5-minute stability test

### 3. test_throughput.py

Processing capacity and concurrent handling:

- **FPS Testing**: Frames per second for OCR
- **Batch Processing**: Efficient batch handling
- **Concurrent Requests**: Multiple simultaneous operations
- **Queue Depth**: Queue handling and backpressure

**Key Tests:**
- `test_ocr_fps_sequential` - OCR processing speed
- `test_asr_concurrent_processing` - ASR concurrency
- `test_request_queue_handling` - Queue management

### 4. test_resource_usage.py

System resource utilization:

- **CPU Utilization**: Per-operation CPU usage
- **GPU Utilization**: GPU acceleration (if available)
- **Disk I/O**: Read/write throughput
- **Network Bandwidth**: API call efficiency
- **Battery Impact**: Power consumption estimation

**Key Tests:**
- `test_ocr_cpu_usage` - OCR CPU utilization
- `test_disk_io` - Disk I/O patterns
- `test_battery_drain_ocr` - Battery impact estimation

### 5. test_stress.py

System stability and resilience:

- **Extended Operation**: 1+ hour continuous operation
- **Rapid Bursts**: High-frequency request handling
- **Recovery**: Recovery from overload conditions
- **Edge Cases**: Empty inputs, corrupted data, extreme sizes

**Key Tests:**
- `test_ocr_extended_operation` - 1-hour stability test
- `test_concurrent_burst_handling` - Burst resilience
- `test_recovery_from_overload` - Graceful degradation

## Configuration

### conftest.py

Provides specialized fixtures:

- `perf_timer` - High-precision timing
- `memory_profiler` - Memory profiling context manager
- `perf_collector` - Performance metric collection
- `resource_monitor` - System resource monitoring
- `benchmark_comparator` - Baseline comparison

### Custom Markers

```python
@pytest.mark.performance  # Performance test
@pytest.mark.slow         # Slow-running test
@pytest.mark.benchmark    # Benchmark test
```

## Usage Examples

### Basic Performance Test

```python
import pytest
from conftest import PerformanceTimer

def test_my_operation(perf_timer):
    timer = perf_timer("my_operation")
    timer.start()

    # Your operation here
    result = perform_operation()

    timing = timer.stop()
    assert timing.duration_ms < 500  # Must be <500ms
```

### Memory Profiling

```python
from conftest import MemoryProfiler

def test_memory_usage(memory_profiler):
    profiler = memory_profiler("my_operation")

    with profiler:
        # Your operation here
        result = perform_operation()

    stats = profiler.stop()
    assert stats["delta_rss_mb"] < 10  # Max 10MB growth
```

### Async Benchmarking

```python
import pytest
from conftest import async_benchmark

@pytest.mark.asyncio
async def test_async_operation():
    @async_benchmark(iterations=10)
    async def operation():
        return await my_async_function()

    result, stats = await operation()
    assert stats["mean_ms"] < 300
```

## Report Generation

The benchmark runner generates three report formats:

### 1. JSON Report
```bash
python benchmarks.py --format json
# Output: benchmark_results/benchmark_report.json
```

Detailed machine-readable results for CI/CD integration.

### 2. Markdown Report
```bash
python benchmarks.py --format markdown
# Output: benchmark_results/benchmark_report.md
```

Human-readable summary with tables and metrics.

### 3. HTML Report
```bash
python benchmarks.py --format html
# Output: benchmark_results/benchmark_report.html
```

Interactive dashboard with charts and visualizations.

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Performance Tests

on: [push, pull_request]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
      - name: Run performance tests
        run: |
          cd tests/performance
          python benchmarks.py --quick --format json
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: performance-results
          path: tests/performance/benchmark_results/
```

## Interpreting Results

### Latency Results

- **P50 (Median)**: Should meet target
- **P95**: Can be 30% over target
- **P99**: Can be 50% over target

### Memory Results

- **Baseline**: Initial memory footprint
- **Peak**: Maximum during operations
- **Growth Rate**: Should be <10MB per 1000 operations

### Resource Results

- **CPU %**: Should be <80% average
- **Memory %**: Should be stable over time
- **Disk I/O**: Should be minimal for in-memory operations

## Troubleshooting

### Tests Timing Out

```bash
# Increase timeout
pytest test_stress.py --performance --timeout=7200
```

### Memory Tests Failing

```bash
# Run with memory cleanup
pytest test_memory_usage.py --performance -v --tb=short
```

### Missing Dependencies

```bash
# Install all performance dependencies
pip install pytest pytest-asyncio pytest-timeout pytest-benchmark psutil
```

## Performance Optimization Tips

Based on benchmark results:

1. **Cache Results**: TTS cache improves throughput 50x
2. **Batch Processing**: 1.5x throughput improvement
3. **Parallel Processing**: Use ThreadPoolExecutor for OCR
4. **Memory Management**: Regular gc.collect() prevents leaks
5. **Warmup**: First run is slower due to model loading

## Baseline Management

### Create Baseline

```bash
python benchmarks.py --save-baseline --output-dir ./baselines/v1.0
```

### Compare Against Baseline

```bash
python benchmarks.py --compare ./baselines/v1.0/baseline.json
```

### Update Baseline

```bash
# After verifying performance improvements
python benchmarks.py --save-baseline --output-dir ./baselines/v1.1
```

## Contact

For issues or questions about performance testing:

- Testing Agent: TST-001
- Task: TST-001-T4 (Performance Test Suite)
- Project: EduLens

## License

Part of the EduLens project - see main project README for license information.
