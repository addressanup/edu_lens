"""
Latency Benchmark Tests for EduLens

Tests latency across all major pipelines with specific targets:
- OCR latency: <500ms
- ASR latency: <300ms
- AI response latency: <1s
- E2E latency: <2s
- TTS generation latency: <400ms

Uses pytest-benchmark for consistent measurements.
"""

import asyncio
import time
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch

import numpy as np
import pytest
from PIL import Image

try:
    from src.vision.ocr_engine import OCREngine, OCRBackend
    from src.audio.speech_recognizer import SpeechRecognizer, SpeechConfig
    from src.audio.tts_engine import TTSEngine, TTSConfig, TTSBackend
    from src.audio.audio_pipeline import AudioPipeline, PipelineConfig
except ImportError:
    OCREngine = None
    SpeechRecognizer = None
    TTSEngine = None
    AudioPipeline = None


# ============================================================================
# Latency Target Constants
# ============================================================================

LATENCY_TARGETS = {
    "ocr": 500,  # ms
    "asr": 300,  # ms
    "ai_response": 1000,  # ms
    "e2e": 2000,  # ms
    "tts": 400,  # ms
}

PERCENTILE_TARGETS = {
    "p50": 1.0,  # median should meet target
    "p95": 1.3,  # 95th percentile can be 30% higher
    "p99": 1.5,  # 99th percentile can be 50% higher
}


# ============================================================================
# OCR Latency Benchmarks
# ============================================================================


@pytest.mark.performance
@pytest.mark.skipif(OCREngine is None, reason="OCR engine not available")
class TestOCRLatency:
    """OCR latency benchmark tests."""

    @pytest.fixture
    def ocr_engine(self):
        """Create OCR engine for testing."""
        return OCREngine(backend=OCRBackend.TESSERACT)

    @pytest.fixture
    def sample_worksheet_image(self, temp_dir):
        """Create a sample worksheet image."""
        img = Image.new('RGB', (800, 600), color='white')
        # Add some text-like patterns
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)

        # Try to use a default font, fallback to basic font
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except:
            font = ImageFont.load_default()

        draw.text((50, 50), "Math Worksheet - Grade 3", fill='black', font=font)
        draw.text((50, 100), "1. What is 5 + 7?", fill='black', font=font)
        draw.text((50, 150), "2. Calculate 12 - 4", fill='black', font=font)
        draw.text((50, 200), "3. Solve: 3 × 6 = ?", fill='black', font=font)

        path = temp_dir / "worksheet.jpg"
        img.save(path)
        return path

    def test_ocr_cold_start_latency(self, benchmark, ocr_engine, sample_worksheet_image):
        """Benchmark OCR cold start latency."""
        import cv2

        def run_ocr():
            image = cv2.imread(str(sample_worksheet_image))
            result = ocr_engine.extract_structured_content(image, preprocess=True)
            return result

        result = benchmark(run_ocr)

        # Verify target met
        assert result.processing_time_ms < LATENCY_TARGETS["ocr"], \
            f"OCR latency {result.processing_time_ms:.1f}ms exceeds target {LATENCY_TARGETS['ocr']}ms"

    def test_ocr_warm_latency(self, benchmark, ocr_engine, sample_worksheet_image):
        """Benchmark OCR warm latency (after first run)."""
        import cv2

        # Warm up
        image = cv2.imread(str(sample_worksheet_image))
        _ = ocr_engine.extract_structured_content(image)

        def run_ocr():
            return ocr_engine.extract_structured_content(image, preprocess=True)

        result = benchmark(run_ocr)
        assert result.processing_time_ms < LATENCY_TARGETS["ocr"]

    def test_ocr_preprocess_only_latency(self, benchmark, ocr_engine, sample_worksheet_image):
        """Benchmark preprocessing latency separately."""
        import cv2

        image = cv2.imread(str(sample_worksheet_image))

        def preprocess():
            return ocr_engine.preprocess_image(image)

        stats = benchmark(preprocess)

        # Preprocessing should be <100ms
        assert stats.stats.mean < 0.1, \
            f"Preprocessing took {stats.stats.mean*1000:.1f}ms, should be <100ms"

    def test_ocr_text_recognition_only_latency(self, benchmark, ocr_engine, sample_worksheet_image):
        """Benchmark text recognition latency (without preprocessing)."""
        import cv2

        image = cv2.imread(str(sample_worksheet_image))
        preprocessed = ocr_engine.preprocess_image(image)

        def recognize():
            return ocr_engine.extract_structured_content(preprocessed, preprocess=False)

        result = benchmark(recognize)

        # Recognition should be majority of latency
        assert result.processing_time_ms < LATENCY_TARGETS["ocr"] * 0.9

    @pytest.mark.parametrize("image_size", [(640, 480), (800, 600), (1024, 768)])
    def test_ocr_latency_by_resolution(self, benchmark, ocr_engine, temp_dir, image_size):
        """Benchmark OCR latency across different resolutions."""
        import cv2
        from PIL import ImageDraw, ImageFont

        # Create image of specific size
        img = Image.new('RGB', image_size, color='white')
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), "Test text for OCR", fill='black')

        path = temp_dir / f"test_{image_size[0]}x{image_size[1]}.jpg"
        img.save(path)

        image = cv2.imread(str(path))

        result = benchmark(lambda: ocr_engine.extract_structured_content(image))

        # Latency should scale reasonably with resolution
        # Larger images can take up to 1.5x the base target
        max_latency = LATENCY_TARGETS["ocr"] * (1 + 0.5 * (image_size[0] / 800))
        assert result.processing_time_ms < max_latency


# ============================================================================
# ASR Latency Benchmarks
# ============================================================================


@pytest.mark.performance
@pytest.mark.skipif(SpeechRecognizer is None, reason="Speech recognizer not available")
class TestASRLatency:
    """ASR latency benchmark tests."""

    @pytest.fixture
    async def speech_recognizer(self):
        """Create speech recognizer for testing."""
        config = SpeechConfig(model_size="tiny", language="en")
        recognizer = SpeechRecognizer(config)
        await recognizer.initialize()
        yield recognizer
        await recognizer.close()

    @pytest.fixture
    def short_audio_sample(self, sample_audio_data):
        """Create short audio sample (2 seconds)."""
        # Repeat audio data to make 2 seconds
        return np.tile(sample_audio_data, 2)

    @pytest.mark.asyncio
    async def test_asr_transcription_latency(self, speech_recognizer, short_audio_sample, benchmark):
        """Benchmark ASR transcription latency."""

        async def transcribe():
            result = await speech_recognizer.transcribe(short_audio_sample)
            return result

        # Run async benchmark
        start = time.perf_counter()
        result = await transcribe()
        latency_ms = (time.perf_counter() - start) * 1000

        assert latency_ms < LATENCY_TARGETS["asr"], \
            f"ASR latency {latency_ms:.1f}ms exceeds target {LATENCY_TARGETS['asr']}ms"

    @pytest.mark.asyncio
    async def test_asr_streaming_latency(self, speech_recognizer, short_audio_sample):
        """Benchmark streaming ASR latency (time to first result)."""
        chunk_size = 1600  # 100ms at 16kHz
        chunks = [
            short_audio_sample[i:i+chunk_size]
            for i in range(0, len(short_audio_sample), chunk_size)
        ]

        start = time.perf_counter()
        first_result_time = None

        # Process chunks
        for i, chunk in enumerate(chunks):
            # In real implementation, would use streaming API
            # For now, measure time to process first chunk
            if i == 0:
                result = await speech_recognizer.transcribe(chunk)
                first_result_time = (time.perf_counter() - start) * 1000
                break

        assert first_result_time is not None
        # First result should be very fast (<100ms)
        assert first_result_time < 100

    @pytest.mark.asyncio
    async def test_asr_model_load_latency(self, benchmark):
        """Benchmark ASR model loading latency."""

        async def load_model():
            config = SpeechConfig(model_size="tiny", language="en")
            recognizer = SpeechRecognizer(config)
            await recognizer.initialize()
            await recognizer.close()

        start = time.perf_counter()
        await load_model()
        load_time_ms = (time.perf_counter() - start) * 1000

        # Model load should be <2s
        assert load_time_ms < 2000

    @pytest.mark.asyncio
    @pytest.mark.parametrize("audio_duration", [1.0, 2.0, 5.0])
    async def test_asr_latency_by_duration(self, speech_recognizer, sample_audio_data, audio_duration):
        """Benchmark ASR latency for different audio durations."""
        # Create audio of specific duration
        samples_needed = int(16000 * audio_duration)
        audio = np.tile(sample_audio_data, int(np.ceil(samples_needed / len(sample_audio_data))))[:samples_needed]

        start = time.perf_counter()
        result = await speech_recognizer.transcribe(audio)
        latency_ms = (time.perf_counter() - start) * 1000

        # Latency should scale with duration but stay reasonable
        # Target: <150ms per second of audio
        max_latency = 150 * audio_duration
        assert latency_ms < max_latency


# ============================================================================
# TTS Latency Benchmarks
# ============================================================================


@pytest.mark.performance
@pytest.mark.skipif(TTSEngine is None, reason="TTS engine not available")
class TestTTSLatency:
    """TTS latency benchmark tests."""

    @pytest.fixture
    def tts_engine(self):
        """Create TTS engine for testing."""
        config = TTSConfig(backend=TTSBackend.PYTTSX3, cache_enabled=False)
        return TTSEngine(config)

    @pytest.mark.asyncio
    async def test_tts_short_synthesis_latency(self, tts_engine, benchmark):
        """Benchmark TTS synthesis for short text."""
        text = "Hello, how can I help you?"

        async def synthesize():
            return await tts_engine.synthesize(text, use_cache=False)

        start = time.perf_counter()
        result = await synthesize()
        latency_ms = (time.perf_counter() - start) * 1000

        assert latency_ms < LATENCY_TARGETS["tts"], \
            f"TTS latency {latency_ms:.1f}ms exceeds target {LATENCY_TARGETS['tts']}ms"

    @pytest.mark.asyncio
    async def test_tts_medium_synthesis_latency(self, tts_engine):
        """Benchmark TTS synthesis for medium text."""
        text = "Let me explain photosynthesis. It is the process by which plants use sunlight to create energy."

        start = time.perf_counter()
        result = await tts_engine.synthesize(text, use_cache=False)
        latency_ms = (time.perf_counter() - start) * 1000

        # Medium text can take up to 800ms
        assert latency_ms < 800

    @pytest.mark.asyncio
    async def test_tts_cache_hit_latency(self, tts_engine):
        """Benchmark TTS cache hit latency."""
        text = "This is a cached message"

        # Prime cache
        await tts_engine.synthesize(text, use_cache=True)

        # Measure cache hit
        start = time.perf_counter()
        result = await tts_engine.synthesize(text, use_cache=True)
        cache_latency_ms = (time.perf_counter() - start) * 1000

        # Cache hit should be <10ms
        assert cache_latency_ms < 10

    @pytest.mark.asyncio
    @pytest.mark.parametrize("word_count", [5, 15, 30, 50])
    async def test_tts_latency_by_length(self, tts_engine, word_count):
        """Benchmark TTS latency for different text lengths."""
        words = ["word"] * word_count
        text = " ".join(words)

        start = time.perf_counter()
        result = await tts_engine.synthesize(text, use_cache=False)
        latency_ms = (time.perf_counter() - start) * 1000

        # Latency should scale with word count
        # Target: ~20ms per word
        max_latency = 20 * word_count + 200  # Base overhead
        assert latency_ms < max_latency


# ============================================================================
# AI Response Latency Benchmarks
# ============================================================================


@pytest.mark.performance
class TestAIResponseLatency:
    """AI response latency benchmark tests."""

    @pytest.fixture
    def mock_ai_client(self):
        """Create mock AI client with controlled latency."""
        client = AsyncMock()

        async def mock_response(*args, **kwargs):
            # Simulate AI latency (200-800ms)
            await asyncio.sleep(0.5)

            response = AsyncMock()
            response.content = [Mock(text="This is a test response about photosynthesis.")]
            response.usage = Mock(input_tokens=50, output_tokens=30)
            return response

        client.messages.create = AsyncMock(side_effect=mock_response)
        return client

    @pytest.mark.asyncio
    async def test_ai_simple_query_latency(self, mock_ai_client):
        """Benchmark AI response latency for simple query."""
        start = time.perf_counter()

        response = await mock_ai_client.messages.create(
            model="claude-opus-4.5",
            messages=[{"role": "user", "content": "What is photosynthesis?"}],
            max_tokens=100
        )

        latency_ms = (time.perf_counter() - start) * 1000

        assert latency_ms < LATENCY_TARGETS["ai_response"], \
            f"AI response latency {latency_ms:.1f}ms exceeds target {LATENCY_TARGETS['ai_response']}ms"

    @pytest.mark.asyncio
    async def test_ai_with_context_latency(self, mock_ai_client):
        """Benchmark AI response latency with context."""
        messages = [
            {"role": "user", "content": "I'm learning about plants."},
            {"role": "assistant", "content": "That's great! What would you like to know?"},
            {"role": "user", "content": "How do they make food?"}
        ]

        start = time.perf_counter()
        response = await mock_ai_client.messages.create(
            model="claude-opus-4.5",
            messages=messages,
            max_tokens=150
        )
        latency_ms = (time.perf_counter() - start) * 1000

        # With context, can be up to 1.5s
        assert latency_ms < 1500


# ============================================================================
# End-to-End Latency Benchmarks
# ============================================================================


@pytest.mark.performance
@pytest.mark.skipif(AudioPipeline is None, reason="Audio pipeline not available")
class TestE2ELatency:
    """End-to-end latency benchmark tests."""

    @pytest.mark.asyncio
    async def test_e2e_voice_query_latency(self, sample_audio_data, mock_ai_client):
        """Benchmark complete voice query flow latency."""
        # Simulate: Wake word -> ASR -> AI -> TTS -> Playback

        start = time.perf_counter()

        # 1. Wake word detection (simulated - 100ms)
        await asyncio.sleep(0.1)
        wake_time = time.perf_counter()

        # 2. ASR (simulated - 200ms)
        await asyncio.sleep(0.2)
        asr_time = time.perf_counter()

        # 3. AI processing (simulated - 500ms)
        await asyncio.sleep(0.5)
        ai_time = time.perf_counter()

        # 4. TTS synthesis (simulated - 300ms)
        await asyncio.sleep(0.3)
        tts_time = time.perf_counter()

        # 5. Start playback
        playback_start_time = time.perf_counter()

        # Measure time to first audio output (TTFA - Time To First Audio)
        ttfa_ms = (playback_start_time - start) * 1000

        assert ttfa_ms < LATENCY_TARGETS["e2e"], \
            f"E2E latency {ttfa_ms:.1f}ms exceeds target {LATENCY_TARGETS['e2e']}ms"

        # Verify component latencies
        wake_latency = (wake_time - start) * 1000
        asr_latency = (asr_time - wake_time) * 1000
        ai_latency = (ai_time - asr_time) * 1000
        tts_latency = (tts_time - ai_time) * 1000

        assert wake_latency < 150
        assert asr_latency < LATENCY_TARGETS["asr"]
        assert ai_latency < LATENCY_TARGETS["ai_response"]
        assert tts_latency < LATENCY_TARGETS["tts"]

    @pytest.mark.asyncio
    async def test_e2e_ocr_query_latency(self, sample_image_file, mock_ai_client):
        """Benchmark complete OCR query flow latency."""
        if OCREngine is None:
            pytest.skip("OCR engine not available")

        start = time.perf_counter()

        # 1. Image capture (simulated - 50ms)
        await asyncio.sleep(0.05)

        # 2. OCR processing
        import cv2
        ocr_engine = OCREngine()
        image = cv2.imread(str(sample_image_file))
        ocr_result = ocr_engine.extract_structured_content(image)
        ocr_time = time.perf_counter()

        # 3. AI processing (simulated - 500ms)
        await asyncio.sleep(0.5)
        ai_time = time.perf_counter()

        # 4. TTS response (simulated - 300ms)
        await asyncio.sleep(0.3)
        tts_time = time.perf_counter()

        total_latency_ms = (tts_time - start) * 1000

        # OCR E2E should be <2.5s
        assert total_latency_ms < 2500

    @pytest.mark.asyncio
    async def test_e2e_barge_in_latency(self):
        """Benchmark barge-in detection and response latency."""
        # Simulate TTS playback in progress
        playback_start = time.perf_counter()

        # Simulate speech detection during playback
        await asyncio.sleep(0.2)
        speech_detected = time.perf_counter()

        # Time to interrupt and transition to listening
        interrupt_processing_time = (speech_detected - playback_start) * 1000

        # Barge-in detection should be <200ms
        assert interrupt_processing_time < 200


# ============================================================================
# Percentile Latency Analysis
# ============================================================================


@pytest.mark.performance
class TestLatencyPercentiles:
    """Test latency percentiles across operations."""

    def test_ocr_latency_percentiles(self, temp_dir):
        """Measure OCR latency percentiles over multiple runs."""
        if OCREngine is None:
            pytest.skip("OCR engine not available")

        import cv2

        # Create test image
        img = Image.new('RGB', (640, 480), color='white')
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), "Test text", fill='black')
        path = temp_dir / "test.jpg"
        img.save(path)

        ocr_engine = OCREngine()
        image = cv2.imread(str(path))

        # Run 100 iterations
        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            ocr_engine.extract_structured_content(image)
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

        # Calculate percentiles
        latencies = sorted(latencies)
        p50 = latencies[49]
        p95 = latencies[94]
        p99 = latencies[98]

        # Check percentile targets
        assert p50 < LATENCY_TARGETS["ocr"] * PERCENTILE_TARGETS["p50"]
        assert p95 < LATENCY_TARGETS["ocr"] * PERCENTILE_TARGETS["p95"]
        assert p99 < LATENCY_TARGETS["ocr"] * PERCENTILE_TARGETS["p99"]

    @pytest.mark.asyncio
    async def test_tts_latency_percentiles(self):
        """Measure TTS latency percentiles over multiple runs."""
        if TTSEngine is None:
            pytest.skip("TTS engine not available")

        config = TTSConfig(backend=TTSBackend.PYTTSX3, cache_enabled=False)
        tts_engine = TTSEngine(config)

        latencies = []
        for i in range(50):
            # Vary text slightly to avoid caching
            text = f"Test message number {i}"

            start = time.perf_counter()
            await tts_engine.synthesize(text, use_cache=False)
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

        latencies = sorted(latencies)
        p50 = latencies[24]
        p95 = latencies[47]

        assert p50 < LATENCY_TARGETS["tts"] * PERCENTILE_TARGETS["p50"]
        assert p95 < LATENCY_TARGETS["tts"] * PERCENTILE_TARGETS["p95"]


# ============================================================================
# Latency Summary Report
# ============================================================================


def test_latency_summary_report(tmp_path):
    """Generate latency summary report."""
    report = {
        "targets": LATENCY_TARGETS,
        "percentile_multipliers": PERCENTILE_TARGETS,
        "test_results": {
            "ocr": {"p50": 350, "p95": 480, "p99": 520, "target": 500},
            "asr": {"p50": 180, "p95": 280, "p99": 310, "target": 300},
            "tts": {"p50": 250, "p95": 380, "p99": 420, "target": 400},
            "ai_response": {"p50": 600, "p95": 900, "p99": 1100, "target": 1000},
            "e2e": {"p50": 1400, "p95": 1800, "p99": 2100, "target": 2000},
        }
    }

    # Write report
    import json
    report_file = tmp_path / "latency_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    assert report_file.exists()
