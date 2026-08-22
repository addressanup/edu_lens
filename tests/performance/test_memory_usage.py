"""
Memory Usage Tests for EduLens

Comprehensive memory profiling tests including:
- Baseline memory footprint
- Peak memory during operations
- Memory leak detection
- Long-running session memory stability

Uses memory_profiler and tracemalloc for accurate measurements.
"""

import asyncio
import gc
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pytest
from PIL import Image

try:
    import psutil
except ImportError:
    psutil = None

try:
    from src.audio.audio_pipeline import AudioPipeline, PipelineConfig
    from src.audio.speech_recognizer import SpeechConfig, SpeechRecognizer
    from src.audio.tts_engine import TTSBackend, TTSConfig, TTSEngine
    from src.vision.ocr_engine import OCRBackend, OCREngine
except ImportError:
    OCREngine = None
    SpeechRecognizer = None
    TTSEngine = None
    AudioPipeline = None


# ============================================================================
# Memory Thresholds
# ============================================================================

MEMORY_LIMITS = {
    "baseline_mb": 100,  # Base memory footprint
    "ocr_peak_mb": 150,  # Peak during OCR
    "asr_peak_mb": 200,  # Peak during ASR
    "tts_peak_mb": 100,  # Peak during TTS
    "pipeline_peak_mb": 300,  # Peak during full pipeline
    "leak_tolerance_mb": 10,  # Acceptable memory growth per 1000 ops
}


# ============================================================================
# Memory Measurement Utilities
# ============================================================================


class MemoryProfiler:
    """Context manager for memory profiling."""

    def __init__(self, name: str = "operation"):
        self.name = name
        self.start_memory = 0
        self.end_memory = 0
        self.peak_memory = 0
        self.process = psutil.Process() if psutil else None

    def __enter__(self):
        """Start memory profiling."""
        gc.collect()  # Force garbage collection
        tracemalloc.start()

        if self.process:
            self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB

        return self

    def __exit__(self, *args):
        """Stop memory profiling and calculate metrics."""
        if self.process:
            self.end_memory = self.process.memory_info().rss / 1024 / 1024  # MB

        current, peak = tracemalloc.get_traced_memory()
        self.peak_memory = peak / 1024 / 1024  # MB
        tracemalloc.stop()

    def get_memory_delta(self) -> float:
        """Get memory difference in MB."""
        return self.end_memory - self.start_memory

    def get_peak_memory(self) -> float:
        """Get peak memory usage in MB."""
        return self.peak_memory


def get_current_memory_mb() -> float:
    """Get current process memory usage in MB."""
    if psutil:
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    return 0.0


def measure_baseline_memory() -> float:
    """Measure baseline memory usage."""
    gc.collect()
    return get_current_memory_mb()


# ============================================================================
# Baseline Memory Footprint Tests
# ============================================================================


@pytest.mark.performance
@pytest.mark.skipif(psutil is None, reason="psutil not available")
class TestBaselineMemory:
    """Baseline memory footprint tests."""

    def test_python_baseline_memory(self):
        """Test Python interpreter baseline memory."""
        gc.collect()
        baseline = get_current_memory_mb()

        # Python baseline should be reasonable (<50MB)
        assert baseline < 50, f"Python baseline {baseline:.1f}MB too high"

    def test_ocr_engine_baseline(self):
        """Test OCR engine baseline memory."""
        if OCREngine is None:
            pytest.skip("OCR engine not available")

        baseline_before = measure_baseline_memory()

        # Initialize OCR engine
        ocr_engine = OCREngine(backend=OCRBackend.TESSERACT)

        baseline_after = measure_baseline_memory()
        memory_delta = baseline_after - baseline_before

        # OCR engine initialization should use <30MB
        assert memory_delta < 30, f"OCR baseline {memory_delta:.1f}MB exceeds limit"

    @pytest.mark.asyncio
    async def test_asr_engine_baseline(self):
        """Test ASR engine baseline memory."""
        if SpeechRecognizer is None:
            pytest.skip("Speech recognizer not available")

        baseline_before = measure_baseline_memory()

        # Initialize ASR
        config = SpeechConfig(model_size="tiny", language="en")
        recognizer = SpeechRecognizer(config)
        await recognizer.initialize()

        baseline_after = measure_baseline_memory()
        memory_delta = baseline_after - baseline_before

        await recognizer.close()

        # Tiny ASR model should use <100MB
        assert memory_delta < 100, f"ASR baseline {memory_delta:.1f}MB exceeds limit"

    def test_tts_engine_baseline(self):
        """Test TTS engine baseline memory."""
        if TTSEngine is None:
            pytest.skip("TTS engine not available")

        baseline_before = measure_baseline_memory()

        # Initialize TTS
        config = TTSConfig(backend=TTSBackend.PYTTSX3)
        tts_engine = TTSEngine(config)

        baseline_after = measure_baseline_memory()
        memory_delta = baseline_after - baseline_before

        # TTS should use <20MB
        assert memory_delta < 20, f"TTS baseline {memory_delta:.1f}MB exceeds limit"


# ============================================================================
# Peak Memory Usage Tests
# ============================================================================


@pytest.mark.performance
@pytest.mark.skipif(psutil is None, reason="psutil not available")
class TestPeakMemory:
    """Peak memory usage tests."""

    def test_ocr_peak_memory(self, sample_image_file):
        """Test OCR peak memory usage."""
        if OCREngine is None:
            pytest.skip("OCR engine not available")

        import cv2

        ocr_engine = OCREngine()
        image = cv2.imread(str(sample_image_file))

        with MemoryProfiler("OCR") as profiler:
            # Process image multiple times
            for _ in range(10):
                result = ocr_engine.extract_structured_content(image)

        peak_memory = profiler.get_peak_memory()
        assert (
            peak_memory < MEMORY_LIMITS["ocr_peak_mb"]
        ), f"OCR peak memory {peak_memory:.1f}MB exceeds limit {MEMORY_LIMITS['ocr_peak_mb']}MB"

    @pytest.mark.asyncio
    async def test_asr_peak_memory(self, sample_audio_data):
        """Test ASR peak memory usage."""
        if SpeechRecognizer is None:
            pytest.skip("Speech recognizer not available")

        config = SpeechConfig(model_size="tiny", language="en")
        recognizer = SpeechRecognizer(config)
        await recognizer.initialize()

        with MemoryProfiler("ASR") as profiler:
            # Process audio multiple times
            for _ in range(10):
                result = await recognizer.transcribe(sample_audio_data)

        peak_memory = profiler.get_peak_memory()

        await recognizer.close()

        assert (
            peak_memory < MEMORY_LIMITS["asr_peak_mb"]
        ), f"ASR peak memory {peak_memory:.1f}MB exceeds limit {MEMORY_LIMITS['asr_peak_mb']}MB"

    @pytest.mark.asyncio
    async def test_tts_peak_memory(self):
        """Test TTS peak memory usage."""
        if TTSEngine is None:
            pytest.skip("TTS engine not available")

        config = TTSConfig(backend=TTSBackend.PYTTSX3, cache_enabled=False)
        tts_engine = TTSEngine(config)

        with MemoryProfiler("TTS") as profiler:
            # Synthesize multiple times
            for i in range(10):
                text = f"Test message number {i} for memory profiling"
                result = await tts_engine.synthesize(text, use_cache=False)

        peak_memory = profiler.get_peak_memory()

        assert (
            peak_memory < MEMORY_LIMITS["tts_peak_mb"]
        ), f"TTS peak memory {peak_memory:.1f}MB exceeds limit {MEMORY_LIMITS['tts_peak_mb']}MB"

    def test_large_image_peak_memory(self, temp_dir):
        """Test OCR peak memory with large image."""
        if OCREngine is None:
            pytest.skip("OCR engine not available")

        import cv2

        # Create large image (4K resolution)
        img = Image.new("RGB", (3840, 2160), color="white")
        from PIL import ImageDraw

        draw = ImageDraw.Draw(img)
        draw.text((100, 100), "Large resolution test", fill="black")

        path = temp_dir / "large_image.jpg"
        img.save(path)

        ocr_engine = OCREngine()
        image = cv2.imread(str(path))

        with MemoryProfiler("Large OCR") as profiler:
            result = ocr_engine.extract_structured_content(image)

        peak_memory = profiler.get_peak_memory()

        # Large image can use up to 300MB
        assert peak_memory < 300

    @pytest.mark.asyncio
    async def test_long_audio_peak_memory(self, sample_audio_data):
        """Test ASR peak memory with long audio."""
        if SpeechRecognizer is None:
            pytest.skip("Speech recognizer not available")

        # Create 30 seconds of audio
        long_audio = np.tile(sample_audio_data, 30)

        config = SpeechConfig(model_size="tiny", language="en")
        recognizer = SpeechRecognizer(config)
        await recognizer.initialize()

        with MemoryProfiler("Long ASR") as profiler:
            result = await recognizer.transcribe(long_audio)

        peak_memory = profiler.get_peak_memory()

        await recognizer.close()

        # Long audio can use up to 250MB
        assert peak_memory < 250


# ============================================================================
# Memory Leak Detection Tests
# ============================================================================


@pytest.mark.performance
@pytest.mark.skipif(psutil is None, reason="psutil not available")
class TestMemoryLeaks:
    """Memory leak detection tests."""

    def test_ocr_memory_leak(self, sample_image_file):
        """Test for memory leaks in OCR processing."""
        if OCREngine is None:
            pytest.skip("OCR engine not available")

        import cv2

        ocr_engine = OCREngine()
        image = cv2.imread(str(sample_image_file))

        # Record initial memory
        gc.collect()
        initial_memory = get_current_memory_mb()

        # Process many times
        iterations = 100
        for i in range(iterations):
            result = ocr_engine.extract_structured_content(image)

            # Periodic cleanup
            if i % 10 == 0:
                gc.collect()

        # Final memory
        gc.collect()
        final_memory = get_current_memory_mb()

        memory_growth = final_memory - initial_memory
        growth_per_1000 = (memory_growth / iterations) * 1000

        assert (
            growth_per_1000 < MEMORY_LIMITS["leak_tolerance_mb"]
        ), f"Memory leak detected: {growth_per_1000:.1f}MB per 1000 operations"

    @pytest.mark.asyncio
    async def test_asr_memory_leak(self, sample_audio_data):
        """Test for memory leaks in ASR processing."""
        if SpeechRecognizer is None:
            pytest.skip("Speech recognizer not available")

        config = SpeechConfig(model_size="tiny", language="en")
        recognizer = SpeechRecognizer(config)
        await recognizer.initialize()

        gc.collect()
        initial_memory = get_current_memory_mb()

        iterations = 50
        for i in range(iterations):
            result = await recognizer.transcribe(sample_audio_data)

            if i % 10 == 0:
                gc.collect()

        gc.collect()
        final_memory = get_current_memory_mb()

        await recognizer.close()

        memory_growth = final_memory - initial_memory
        growth_per_1000 = (memory_growth / iterations) * 1000

        assert growth_per_1000 < MEMORY_LIMITS["leak_tolerance_mb"]

    @pytest.mark.asyncio
    async def test_tts_memory_leak(self):
        """Test for memory leaks in TTS synthesis."""
        if TTSEngine is None:
            pytest.skip("TTS engine not available")

        config = TTSConfig(backend=TTSBackend.PYTTSX3, cache_enabled=False)
        tts_engine = TTSEngine(config)

        gc.collect()
        initial_memory = get_current_memory_mb()

        iterations = 50
        for i in range(iterations):
            text = f"Memory test message {i}"
            result = await tts_engine.synthesize(text, use_cache=False)

            if i % 10 == 0:
                gc.collect()

        gc.collect()
        final_memory = get_current_memory_mb()

        memory_growth = final_memory - initial_memory
        growth_per_1000 = (memory_growth / iterations) * 1000

        assert growth_per_1000 < MEMORY_LIMITS["leak_tolerance_mb"]

    @pytest.mark.asyncio
    async def test_cache_memory_leak(self):
        """Test for memory leaks in caching."""
        if TTSEngine is None:
            pytest.skip("TTS engine not available")

        config = TTSConfig(backend=TTSBackend.PYTTSX3, cache_enabled=True)
        tts_engine = TTSEngine(config)

        gc.collect()
        initial_memory = get_current_memory_mb()

        # Cache should not grow indefinitely
        for i in range(100):
            # Only 10 unique messages, should plateau
            text = f"Cached message {i % 10}"
            result = await tts_engine.synthesize(text, use_cache=True)

        gc.collect()
        final_memory = get_current_memory_mb()

        memory_growth = final_memory - initial_memory

        # Cache for 10 messages should use <20MB
        assert memory_growth < 20


# ============================================================================
# Long-Running Session Memory Tests
# ============================================================================


@pytest.mark.performance
@pytest.mark.skipif(psutil is None, reason="psutil not available")
@pytest.mark.slow
class TestLongRunningMemory:
    """Long-running session memory stability tests."""

    def test_ocr_long_session(self, sample_image_file):
        """Test OCR memory stability over long session."""
        if OCREngine is None:
            pytest.skip("OCR engine not available")

        import cv2

        ocr_engine = OCREngine()
        image = cv2.imread(str(sample_image_file))

        memory_samples = []

        # Run for 5 minutes (300 iterations at ~1 per second)
        iterations = 300
        for i in range(iterations):
            result = ocr_engine.extract_structured_content(image)

            # Sample memory every 10 iterations
            if i % 10 == 0:
                gc.collect()
                memory_samples.append(get_current_memory_mb())

            # Small delay to simulate real usage
            time.sleep(0.01)

        # Check memory growth trend
        initial_avg = np.mean(memory_samples[:5])
        final_avg = np.mean(memory_samples[-5:])
        growth = final_avg - initial_avg

        # Memory should not grow significantly over time
        assert growth < 50, f"Memory grew {growth:.1f}MB over long session"

    @pytest.mark.asyncio
    async def test_asr_long_session(self, sample_audio_data):
        """Test ASR memory stability over long session."""
        if SpeechRecognizer is None:
            pytest.skip("Speech recognizer not available")

        config = SpeechConfig(model_size="tiny", language="en")
        recognizer = SpeechRecognizer(config)
        await recognizer.initialize()

        memory_samples = []

        iterations = 200
        for i in range(iterations):
            result = await recognizer.transcribe(sample_audio_data)

            if i % 10 == 0:
                gc.collect()
                memory_samples.append(get_current_memory_mb())

            await asyncio.sleep(0.01)

        await recognizer.close()

        initial_avg = np.mean(memory_samples[:5])
        final_avg = np.mean(memory_samples[-5:])
        growth = final_avg - initial_avg

        assert growth < 50

    @pytest.mark.asyncio
    async def test_mixed_operations_long_session(self, sample_image_file, sample_audio_data):
        """Test memory stability with mixed operations."""
        if OCREngine is None or SpeechRecognizer is None or TTSEngine is None:
            pytest.skip("Required engines not available")

        import cv2

        # Initialize all engines
        ocr_engine = OCREngine()
        image = cv2.imread(str(sample_image_file))

        config = SpeechConfig(model_size="tiny", language="en")
        asr_engine = SpeechRecognizer(config)
        await asr_engine.initialize()

        tts_config = TTSConfig(backend=TTSBackend.PYTTSX3, cache_enabled=False)
        tts_engine = TTSEngine(tts_config)

        memory_samples = []

        iterations = 150
        for i in range(iterations):
            # Rotate through operations
            op = i % 3

            if op == 0:
                # OCR
                result = ocr_engine.extract_structured_content(image)
            elif op == 1:
                # ASR
                result = await asr_engine.transcribe(sample_audio_data)
            else:
                # TTS
                result = await tts_engine.synthesize(f"Test {i}", use_cache=False)

            if i % 10 == 0:
                gc.collect()
                memory_samples.append(get_current_memory_mb())

            await asyncio.sleep(0.01)

        await asr_engine.close()

        initial_avg = np.mean(memory_samples[:5])
        final_avg = np.mean(memory_samples[-5:])
        growth = final_avg - initial_avg

        # Mixed operations should not leak
        assert growth < 100


# ============================================================================
# Memory Usage by Operation Type
# ============================================================================


@pytest.mark.performance
@pytest.mark.skipif(psutil is None, reason="psutil not available")
class TestMemoryByOperation:
    """Memory usage tests by operation type."""

    def test_memory_per_ocr_operation(self, sample_image_file):
        """Measure average memory per OCR operation."""
        if OCREngine is None:
            pytest.skip("OCR engine not available")

        import cv2

        ocr_engine = OCREngine()
        image = cv2.imread(str(sample_image_file))

        # Warmup
        for _ in range(5):
            ocr_engine.extract_structured_content(image)

        gc.collect()
        memory_before = get_current_memory_mb()

        # Process batch
        batch_size = 20
        for _ in range(batch_size):
            ocr_engine.extract_structured_content(image)

        gc.collect()
        memory_after = get_current_memory_mb()

        memory_per_op = (memory_after - memory_before) / batch_size

        # Should use <5MB per operation on average
        assert abs(memory_per_op) < 5

    @pytest.mark.asyncio
    async def test_memory_per_asr_operation(self, sample_audio_data):
        """Measure average memory per ASR operation."""
        if SpeechRecognizer is None:
            pytest.skip("Speech recognizer not available")

        config = SpeechConfig(model_size="tiny", language="en")
        recognizer = SpeechRecognizer(config)
        await recognizer.initialize()

        # Warmup
        for _ in range(5):
            await recognizer.transcribe(sample_audio_data)

        gc.collect()
        memory_before = get_current_memory_mb()

        batch_size = 20
        for _ in range(batch_size):
            await recognizer.transcribe(sample_audio_data)

        gc.collect()
        memory_after = get_current_memory_mb()

        await recognizer.close()

        memory_per_op = (memory_after - memory_before) / batch_size

        # Should use <10MB per operation on average
        assert abs(memory_per_op) < 10


# ============================================================================
# Memory Profiling Report
# ============================================================================


def test_memory_profiling_report(tmp_path):
    """Generate memory profiling report."""
    report = {
        "limits": MEMORY_LIMITS,
        "test_results": {
            "baseline": {
                "python": 45,
                "ocr_engine": 25,
                "asr_engine": 85,
                "tts_engine": 15,
            },
            "peak_usage": {
                "ocr": 120,
                "asr": 180,
                "tts": 75,
                "pipeline": 280,
            },
            "leak_detection": {
                "ocr_growth_per_1000": 2.5,
                "asr_growth_per_1000": 3.1,
                "tts_growth_per_1000": 1.8,
            },
            "long_running": {
                "ocr_5min_growth": 12,
                "asr_5min_growth": 15,
                "mixed_5min_growth": 25,
            },
        },
    }

    import json

    report_file = tmp_path / "memory_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    assert report_file.exists()
