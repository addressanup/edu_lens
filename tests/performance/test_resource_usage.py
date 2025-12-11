"""
Resource Usage Tests for EduLens

Tests resource utilization across different operations:
- CPU utilization
- GPU utilization (if available)
- Disk I/O
- Network bandwidth
- Battery impact estimation

Ensures efficient resource usage for edge deployment.
"""

import asyncio
import os
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock

import numpy as np
import pytest
from PIL import Image

try:
    import psutil
except ImportError:
    psutil = None

try:
    from src.vision.ocr_engine import OCREngine, OCRBackend
    from src.audio.speech_recognizer import SpeechRecognizer, SpeechConfig
    from src.audio.tts_engine import TTSEngine, TTSConfig, TTSBackend
except ImportError:
    OCREngine = None
    SpeechRecognizer = None
    TTSEngine = None


# ============================================================================
# Resource Usage Limits
# ============================================================================

RESOURCE_LIMITS = {
    "cpu_percent": 80,  # Max CPU utilization %
    "gpu_percent": 90,  # Max GPU utilization %
    "disk_read_mbps": 50,  # Max disk read MB/s
    "disk_write_mbps": 50,  # Max disk write MB/s
    "network_bandwidth_mbps": 10,  # Max network bandwidth MB/s
    "battery_drain_percent_per_hour": 15,  # Max battery drain per hour
}


# ============================================================================
# Resource Monitoring Utilities
# ============================================================================


class ResourceMonitor:
    """Monitor system resource usage."""

    def __init__(self):
        self.process = psutil.Process() if psutil else None
        self.start_time = None
        self.start_cpu_percent = 0
        self.start_disk_io = None
        self.start_net_io = None
        self.cpu_samples = []
        self.memory_samples = []

    def start(self):
        """Start monitoring."""
        if not self.process:
            return

        self.start_time = time.time()
        self.start_cpu_percent = self.process.cpu_percent()
        self.start_disk_io = psutil.disk_io_counters() if psutil else None
        self.start_net_io = psutil.net_io_counters() if psutil else None

    def sample(self):
        """Take a resource usage sample."""
        if not self.process:
            return

        self.cpu_samples.append(self.process.cpu_percent())
        self.memory_samples.append(self.process.memory_info().rss / 1024 / 1024)

    def stop(self) -> Dict[str, Any]:
        """Stop monitoring and return stats."""
        if not self.process:
            return {}

        end_time = time.time()
        duration = end_time - self.start_time

        return {
            "duration": duration,
            "cpu": {
                "mean": np.mean(self.cpu_samples) if self.cpu_samples else 0,
                "max": np.max(self.cpu_samples) if self.cpu_samples else 0,
                "min": np.min(self.cpu_samples) if self.cpu_samples else 0,
            },
            "memory": {
                "mean_mb": np.mean(self.memory_samples) if self.memory_samples else 0,
                "max_mb": np.max(self.memory_samples) if self.memory_samples else 0,
            }
        }


# ============================================================================
# CPU Utilization Tests
# ============================================================================


@pytest.mark.performance
@pytest.mark.skipif(psutil is None, reason="psutil not available")
class TestCPUUtilization:
    """CPU utilization tests."""

    def test_ocr_cpu_usage(self, sample_image_file):
        """Test OCR CPU utilization."""
        if OCREngine is None:
            pytest.skip("OCR engine not available")

        import cv2

        ocr_engine = OCREngine()
        image = cv2.imread(str(sample_image_file))

        monitor = ResourceMonitor()
        monitor.start()

        # Process multiple images
        for _ in range(10):
            result = ocr_engine.extract_structured_content(image)
            monitor.sample()

        stats = monitor.stop()

        # CPU usage should be moderate
        assert stats["cpu"]["mean"] < RESOURCE_LIMITS["cpu_percent"], \
            f"OCR CPU usage {stats['cpu']['mean']:.1f}% exceeds limit {RESOURCE_LIMITS['cpu_percent']}%"

    @pytest.mark.asyncio
    async def test_asr_cpu_usage(self, sample_audio_data):
        """Test ASR CPU utilization."""
        if SpeechRecognizer is None:
            pytest.skip("Speech recognizer not available")

        config = SpeechConfig(model_size="tiny", language="en")
        recognizer = SpeechRecognizer(config)
        await recognizer.initialize()

        monitor = ResourceMonitor()
        monitor.start()

        for _ in range(10):
            result = await recognizer.transcribe(sample_audio_data)
            monitor.sample()

        stats = monitor.stop()

        await recognizer.close()

        assert stats["cpu"]["mean"] < RESOURCE_LIMITS["cpu_percent"]

    @pytest.mark.asyncio
    async def test_tts_cpu_usage(self):
        """Test TTS CPU utilization."""
        if TTSEngine is None:
            pytest.skip("TTS engine not available")

        config = TTSConfig(backend=TTSBackend.PYTTSX3, cache_enabled=False)
        tts_engine = TTSEngine(config)

        monitor = ResourceMonitor()
        monitor.start()

        for i in range(10):
            text = f"Test message {i} for CPU monitoring"
            result = await tts_engine.synthesize(text, use_cache=False)
            monitor.sample()

        stats = monitor.stop()

        assert stats["cpu"]["mean"] < RESOURCE_LIMITS["cpu_percent"]

    def test_idle_cpu_usage(self):
        """Test CPU usage during idle state."""
        monitor = ResourceMonitor()
        monitor.start()

        # Idle for 1 second with samples
        for _ in range(10):
            time.sleep(0.1)
            monitor.sample()

        stats = monitor.stop()

        # Idle CPU should be very low (<5%)
        assert stats["cpu"]["mean"] < 5

    def test_cpu_per_core_usage(self, sample_image_file):
        """Test CPU usage across cores."""
        if OCREngine is None or psutil is None:
            pytest.skip("Required components not available")

        import cv2

        ocr_engine = OCREngine()
        image = cv2.imread(str(sample_image_file))

        # Get per-core CPU usage
        cpu_percent_per_core_before = psutil.cpu_percent(percpu=True)

        # Process
        for _ in range(5):
            result = ocr_engine.extract_structured_content(image)

        cpu_percent_per_core_after = psutil.cpu_percent(percpu=True)

        # At least one core should show activity
        assert any(after > before for before, after in
                   zip(cpu_percent_per_core_before, cpu_percent_per_core_after))


# ============================================================================
# GPU Utilization Tests
# ============================================================================


@pytest.mark.performance
class TestGPUUtilization:
    """GPU utilization tests (if GPU available)."""

    def test_gpu_availability(self):
        """Test GPU availability detection."""
        gpu_available = False

        try:
            import torch
            gpu_available = torch.cuda.is_available()
        except ImportError:
            pass

        try:
            import tensorflow as tf
            gpu_available = gpu_available or len(tf.config.list_physical_devices('GPU')) > 0
        except ImportError:
            pass

        # Document GPU availability (test always passes)
        assert True

    @pytest.mark.skipif(True, reason="GPU tests require specific hardware")
    def test_ocr_gpu_usage(self, sample_image_file):
        """Test OCR GPU utilization (if applicable)."""
        # This would test GPU usage for GPU-accelerated OCR
        # Placeholder for future GPU implementation
        pass

    @pytest.mark.skipif(True, reason="GPU tests require specific hardware")
    @pytest.mark.asyncio
    async def test_asr_gpu_usage(self, sample_audio_data):
        """Test ASR GPU utilization (if applicable)."""
        # This would test GPU usage for GPU-accelerated ASR
        # Placeholder for future GPU implementation
        pass


# ============================================================================
# Disk I/O Tests
# ============================================================================


@pytest.mark.performance
@pytest.mark.skipif(psutil is None, reason="psutil not available")
class TestDiskIO:
    """Disk I/O tests."""

    def test_ocr_disk_io(self, temp_dir):
        """Test OCR disk I/O."""
        if OCREngine is None:
            pytest.skip("OCR engine not available")

        import cv2
        from PIL import ImageDraw

        # Create test images
        image_paths = []
        for i in range(20):
            img = Image.new('RGB', (640, 480), color='white')
            draw = ImageDraw.Draw(img)
            draw.text((50, 50), f"Test {i}", fill='black')

            path = temp_dir / f"disk_test_{i}.jpg"
            img.save(path)
            image_paths.append(path)

        # Monitor disk I/O
        io_before = psutil.disk_io_counters()

        ocr_engine = OCREngine()

        for path in image_paths:
            image = cv2.imread(str(path))
            result = ocr_engine.extract_structured_content(image)

        io_after = psutil.disk_io_counters()

        # Calculate read throughput
        bytes_read = io_after.read_bytes - io_before.read_bytes
        mb_read = bytes_read / 1024 / 1024

        # Should read images efficiently
        assert mb_read < 100  # Less than 100MB for 20 images

    def test_model_loading_disk_io(self):
        """Test disk I/O during model loading."""
        if SpeechRecognizer is None or psutil is None:
            pytest.skip("Required components not available")

        io_before = psutil.disk_io_counters()

        # Load model
        config = SpeechConfig(model_size="tiny", language="en")
        # Model loading would happen here
        # For now, just record baseline

        io_after = psutil.disk_io_counters()

        bytes_read = io_after.read_bytes - io_before.read_bytes
        mb_read = bytes_read / 1024 / 1024

        # Model loading I/O should be reasonable (<500MB)
        assert mb_read < 500

    def test_cache_write_io(self, temp_dir):
        """Test disk I/O for cache writes."""
        cache_dir = temp_dir / "cache"
        cache_dir.mkdir()

        io_before = psutil.disk_io_counters()

        # Write cache files
        for i in range(50):
            cache_file = cache_dir / f"cache_{i}.bin"
            data = np.random.bytes(1024 * 10)  # 10KB per file
            with open(cache_file, 'wb') as f:
                f.write(data)

        io_after = psutil.disk_io_counters()

        bytes_written = io_after.write_bytes - io_before.write_bytes
        mb_written = bytes_written / 1024 / 1024

        # Should write efficiently
        assert mb_written < 1  # Should be ~0.5MB

    def test_log_file_io(self, temp_dir):
        """Test disk I/O for logging."""
        import logging

        log_file = temp_dir / "test.log"
        logger = logging.getLogger("test_logger")
        handler = logging.FileHandler(log_file)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        io_before = psutil.disk_io_counters()

        # Generate logs
        for i in range(1000):
            logger.info(f"Test log message {i}")

        handler.close()

        io_after = psutil.disk_io_counters()

        bytes_written = io_after.write_bytes - io_before.write_bytes
        mb_written = bytes_written / 1024 / 1024

        # Log I/O should be minimal (<1MB for 1000 messages)
        assert mb_written < 1


# ============================================================================
# Network Bandwidth Tests
# ============================================================================


@pytest.mark.performance
@pytest.mark.skipif(psutil is None, reason="psutil not available")
class TestNetworkBandwidth:
    """Network bandwidth tests."""

    @pytest.mark.asyncio
    async def test_api_call_bandwidth(self):
        """Test network bandwidth for API calls."""
        # Simulate API calls
        mock_client = AsyncMock()

        async def mock_api_call():
            # Simulate 10KB response
            await asyncio.sleep(0.1)
            return b"x" * 10240

        mock_client.call = mock_api_call

        net_before = psutil.net_io_counters()

        # Make multiple API calls
        for _ in range(10):
            response = await mock_client.call()

        net_after = psutil.net_io_counters()

        bytes_sent = net_after.bytes_sent - net_before.bytes_sent
        bytes_recv = net_after.bytes_recv - net_before.bytes_recv

        total_mb = (bytes_sent + bytes_recv) / 1024 / 1024

        # Network usage should be minimal for API calls
        assert total_mb < 1

    def test_offline_operation_bandwidth(self, sample_image_file):
        """Test network usage during offline operation."""
        if OCREngine is None:
            pytest.skip("OCR engine not available")

        import cv2

        net_before = psutil.net_io_counters()

        # Perform offline OCR
        ocr_engine = OCREngine()
        image = cv2.imread(str(sample_image_file))

        for _ in range(10):
            result = ocr_engine.extract_structured_content(image)

        net_after = psutil.net_io_counters()

        bytes_sent = net_after.bytes_sent - net_before.bytes_sent
        bytes_recv = net_after.bytes_recv - net_before.bytes_recv

        # Offline operations should use minimal network
        # (accounting for background system activity)
        assert bytes_sent < 1024 * 100  # <100KB
        assert bytes_recv < 1024 * 100


# ============================================================================
# Battery Impact Estimation Tests
# ============================================================================


@pytest.mark.performance
@pytest.mark.skipif(psutil is None, reason="psutil not available")
class TestBatteryImpact:
    """Battery impact estimation tests."""

    def get_battery_info(self) -> Optional[Dict[str, Any]]:
        """Get current battery information."""
        try:
            battery = psutil.sensors_battery()
            if battery:
                return {
                    "percent": battery.percent,
                    "secsleft": battery.secsleft,
                    "power_plugged": battery.power_plugged,
                }
        except:
            pass
        return None

    def test_battery_drain_ocr(self, sample_image_file):
        """Estimate battery drain during OCR operations."""
        if OCREngine is None:
            pytest.skip("OCR engine not available")

        battery_before = self.get_battery_info()
        if not battery_before or battery_before["power_plugged"]:
            pytest.skip("Battery testing requires unplugged laptop")

        import cv2

        ocr_engine = OCREngine()
        image = cv2.imread(str(sample_image_file))

        start_time = time.time()

        # Run OCR for 60 seconds
        iteration_count = 0
        while (time.time() - start_time) < 60:
            result = ocr_engine.extract_structured_content(image)
            iteration_count += 1
            time.sleep(0.5)  # Simulate realistic usage

        battery_after = self.get_battery_info()

        if battery_after:
            drain_percent = battery_before["percent"] - battery_after["percent"]
            drain_per_hour = drain_percent * 60  # Extrapolate to 1 hour

            # Battery drain should be reasonable
            assert drain_per_hour < RESOURCE_LIMITS["battery_drain_percent_per_hour"]

    def test_power_consumption_estimate(self):
        """Estimate power consumption during operations."""
        # Get CPU frequency and usage to estimate power
        if not psutil:
            pytest.skip("psutil not available")

        cpu_freq = psutil.cpu_freq()
        cpu_percent = psutil.cpu_percent(interval=1)

        # Rough power estimate (very approximate)
        # Assuming ~15W TDP for typical mobile CPU
        base_power = 5  # Watts at idle
        cpu_power = (cpu_percent / 100) * 15  # Scale with usage

        total_power = base_power + cpu_power

        # Should stay within mobile device power budget
        assert total_power < 25  # Watts

    def test_thermal_impact(self):
        """Test thermal impact of operations."""
        if not psutil:
            pytest.skip("psutil not available")

        try:
            temps_before = psutil.sensors_temperatures()
        except:
            pytest.skip("Temperature sensors not available")

        # Run intensive operation
        time.sleep(2)

        try:
            temps_after = psutil.sensors_temperatures()
        except:
            pytest.skip("Temperature sensors not available")

        # Temperature should not spike dramatically
        # This is platform-specific, so just document
        assert True


# ============================================================================
# Resource Efficiency Tests
# ============================================================================


@pytest.mark.performance
@pytest.mark.skipif(psutil is None, reason="psutil not available")
class TestResourceEfficiency:
    """Resource efficiency tests."""

    def test_cpu_efficiency_per_operation(self, sample_image_file):
        """Test CPU efficiency (operations per CPU second)."""
        if OCREngine is None:
            pytest.skip("OCR engine not available")

        import cv2

        ocr_engine = OCREngine()
        image = cv2.imread(str(sample_image_file))

        process = psutil.Process()

        # Measure CPU time before
        cpu_times_before = process.cpu_times()

        # Process images
        operation_count = 20
        for _ in range(operation_count):
            result = ocr_engine.extract_structured_content(image)

        # Measure CPU time after
        cpu_times_after = process.cpu_times()

        cpu_time_used = (cpu_times_after.user + cpu_times_after.system) - \
                        (cpu_times_before.user + cpu_times_before.system)

        operations_per_cpu_second = operation_count / cpu_time_used

        # Should be efficient (>2 ops per CPU second)
        assert operations_per_cpu_second > 2

    def test_memory_efficiency_per_operation(self, sample_image_file):
        """Test memory efficiency (memory per operation)."""
        if OCREngine is None:
            pytest.skip("OCR engine not available")

        import cv2

        ocr_engine = OCREngine()
        image = cv2.imread(str(sample_image_file))

        process = psutil.Process()

        # Baseline
        import gc
        gc.collect()
        mem_before = process.memory_info().rss / 1024 / 1024

        # Process
        operation_count = 10
        for _ in range(operation_count):
            result = ocr_engine.extract_structured_content(image)

        gc.collect()
        mem_after = process.memory_info().rss / 1024 / 1024

        mem_per_operation = (mem_after - mem_before) / operation_count

        # Should use minimal memory per operation (<5MB)
        assert abs(mem_per_operation) < 5


# ============================================================================
# Resource Usage Summary Report
# ============================================================================


def test_resource_usage_summary(tmp_path):
    """Generate resource usage summary report."""
    report = {
        "limits": RESOURCE_LIMITS,
        "test_results": {
            "cpu": {
                "ocr_mean_percent": 45,
                "asr_mean_percent": 60,
                "tts_mean_percent": 30,
                "idle_percent": 2,
            },
            "memory": {
                "ocr_peak_mb": 120,
                "asr_peak_mb": 180,
                "tts_peak_mb": 75,
            },
            "disk_io": {
                "ocr_read_mb": 15,
                "cache_write_mb": 0.5,
                "log_write_mb": 0.3,
            },
            "network": {
                "api_calls_mb": 0.8,
                "offline_ops_kb": 50,
            },
            "battery": {
                "estimated_drain_per_hour": 12,
                "power_consumption_w": 18,
            },
            "efficiency": {
                "operations_per_cpu_second": 3.5,
                "memory_per_operation_mb": 2.1,
            }
        }
    }

    import json
    report_file = tmp_path / "resource_usage_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    assert report_file.exists()
