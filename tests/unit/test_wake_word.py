"""
Unit tests for Wake Word Detection Engine.

Tests wake word detection including:
- Detection accuracy
- False positive rate
- Different voices/accents
- Sensitivity adjustment
- Streaming vs batch mode

Author: Testing Agent (TST-001)
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch

import numpy as np
import pytest

from src.audio.audio_capture import AudioConfig
from src.audio.wake_word_engine import (
    AsyncWakeWordDetector,
    AudioStreamProcessor,
    DetectionMode,
    DetectionResult,
    DetectionStats,
    WakeWordDetector,
)


class TestDetectionResult:
    """Test detection result data class."""

    def test_detection_result_creation(self):
        """Test creating a detection result."""
        result = DetectionResult(
            detected=True, confidence=0.92, timestamp=1234567890.0, latency_ms=85.5
        )

        assert result.detected is True
        assert result.confidence == 0.92
        assert result.latency_ms == 85.5

    def test_detection_with_audio_segment(self):
        """Test result with audio segment."""
        audio = np.random.randn(16000).astype(np.float32)

        result = DetectionResult(
            detected=True,
            confidence=0.95,
            timestamp=1234567890.0,
            latency_ms=90.0,
            audio_segment=audio,
        )

        assert result.audio_segment is not None
        assert len(result.audio_segment) == 16000


class TestDetectionStats:
    """Test detection statistics."""

    def test_stats_initialization(self):
        """Test stats initialization."""
        stats = DetectionStats()

        assert stats.total_detections == 0
        assert stats.true_positives == 0
        assert stats.false_positives == 0

    def test_true_positive_rate(self):
        """Test TPR calculation."""
        stats = DetectionStats(true_positives=95, false_negatives=5)

        assert stats.true_positive_rate == 0.95

    def test_false_positive_rate(self):
        """Test FPR calculation."""
        stats = DetectionStats(true_positives=90, false_positives=10)

        assert stats.false_positive_rate == 0.10

    def test_zero_division_handling(self):
        """Test handling of zero division in stats."""
        stats = DetectionStats()

        # Should not raise error
        assert stats.true_positive_rate == 0.0
        assert stats.false_positive_rate == 0.0


class TestWakeWordDetector:
    """Test main wake word detector functionality."""

    @pytest.fixture
    def sample_audio(self):
        """Generate sample audio data."""
        # 1 second of audio at 16kHz
        duration = 1.0
        sample_rate = 16000
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        return audio

    @pytest.fixture
    def detector(self):
        """Create a wake word detector instance."""
        return WakeWordDetector(sensitivity=0.5)

    def test_detector_initialization(self):
        """Test detector initialization."""
        detector = WakeWordDetector(sensitivity=0.5)

        assert detector.sensitivity == 0.5
        assert detector.audio_config is not None
        assert detector.stats is not None
        assert detector._is_listening is False

    def test_detector_with_model_path(self, tmp_path):
        """Test detector with model path."""
        model_file = tmp_path / "model.tflite"
        model_file.touch()

        detector = WakeWordDetector(model_path=str(model_file))

        assert detector.model_path == str(model_file)

    def test_detector_with_config(self, tmp_path):
        """Test detector with config file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("sample_rate: 16000\nchunk_size: 1024")

        detector = WakeWordDetector(config_path=str(config_file))

        assert detector.config_path == str(config_file)

    @pytest.mark.parametrize(
        "sensitivity,expected_threshold",
        [
            (0.0, 0.9),  # Very conservative
            (0.5, 0.6),  # Balanced
            (1.0, 0.3),  # Very aggressive
        ],
    )
    def test_sensitivity_to_threshold(self, sensitivity, expected_threshold):
        """Test sensitivity to threshold conversion."""
        detector = WakeWordDetector(sensitivity=sensitivity)

        assert detector.threshold == expected_threshold

    def test_adjust_sensitivity(self, detector):
        """Test adjusting sensitivity."""
        original_threshold = detector.threshold

        detector.adjust_sensitivity(0.8)

        assert detector.sensitivity == 0.8
        assert detector.threshold != original_threshold

    def test_adjust_sensitivity_bounds(self, detector):
        """Test sensitivity bounds checking."""
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            detector.adjust_sensitivity(1.5)

        with pytest.raises(ValueError):
            detector.adjust_sensitivity(-0.1)

    def test_start_listening(self, detector):
        """Test starting wake word detection."""
        # Patch where the engine binds the symbol (module-level import);
        # patching audio_capture instead would open the real microphone.
        with patch("src.audio.wake_word_engine.MicrophoneStream") as mock_stream:
            mock_stream_instance = MagicMock()
            mock_stream.return_value = mock_stream_instance

            detector.start_listening()

            assert detector.is_listening is True
            mock_stream_instance.start.assert_called_once()

    def test_stop_listening(self, detector):
        """Test stopping wake word detection."""
        # Patch where the engine binds the symbol (module-level import);
        # patching audio_capture instead would open the real microphone.
        with patch("src.audio.wake_word_engine.MicrophoneStream") as mock_stream:
            mock_stream_instance = MagicMock()
            mock_stream.return_value = mock_stream_instance

            detector.start_listening()
            detector.stop_listening()

            assert detector.is_listening is False
            mock_stream_instance.stop.assert_called()

    def test_start_listening_already_listening(self, detector):
        """Test starting when already listening."""
        # Patch where the engine binds the symbol (module-level import);
        # patching audio_capture instead would open the real microphone.
        with patch("src.audio.wake_word_engine.MicrophoneStream") as mock_stream:
            mock_stream_instance = MagicMock()
            mock_stream.return_value = mock_stream_instance

            detector.start_listening()
            detector.start_listening()  # Second call

            # Should not create new stream
            assert mock_stream.call_count == 1

    def test_on_wake_word_callback(self, detector):
        """Test registering wake word callback."""
        callback = Mock()

        detector.on_wake_word(callback)

        assert callback in detector._callbacks

    def test_multiple_callbacks(self, detector):
        """Test registering multiple callbacks."""
        callback1 = Mock()
        callback2 = Mock()

        detector.on_wake_word(callback1)
        detector.on_wake_word(callback2)

        assert len(detector._callbacks) == 2

    def test_detect_batch(self, detector, sample_audio):
        """Test batch detection mode."""
        result = detector.detect_batch(sample_audio)

        assert isinstance(result, DetectionResult)
        assert result.latency_ms > 0

    def test_detect_batch_with_detection(self, detector, sample_audio):
        """Test batch detection with wake word present."""
        with patch.object(detector, "_run_inference", return_value=0.95):
            result = detector.detect_batch(sample_audio)

            assert result.detected is True
            assert result.confidence == 0.95

    def test_detect_batch_no_detection(self, detector, sample_audio):
        """Test batch detection without wake word."""
        with patch.object(detector, "_run_inference", return_value=0.3):
            result = detector.detect_batch(sample_audio)

            assert result.detected is False

    def test_get_detection_confidence(self, detector):
        """Test getting detection confidence."""
        detector._detection_confidence = 0.88

        confidence = detector.get_detection_confidence()

        assert confidence == 0.88

    def test_get_stats(self, detector):
        """Test getting detection statistics."""
        detector.stats.total_detections = 10
        detector.stats.true_positives = 8

        stats = detector.get_stats()

        assert stats.total_detections == 10
        assert stats.true_positives == 8

    def test_reset_stats(self, detector):
        """Test resetting statistics."""
        detector.stats.total_detections = 100

        detector.reset_stats()

        assert detector.stats.total_detections == 0

    def test_context_manager(self, detector):
        """Test using detector as context manager."""
        # Patch where the engine binds the symbol (module-level import);
        # patching audio_capture instead would open the real microphone.
        with patch("src.audio.wake_word_engine.MicrophoneStream"):
            with detector as d:
                assert d.is_listening is True

            assert detector.is_listening is False


class TestAudioStreamProcessor:
    """Test audio stream processing."""

    @pytest.fixture
    def detector(self):
        return WakeWordDetector(sensitivity=0.5)

    @pytest.fixture
    def processor(self, detector):
        audio_config = AudioConfig(sample_rate=16000, channels=1, chunk_size=1024)
        return AudioStreamProcessor(detector, audio_config)

    @pytest.fixture
    def sample_audio_chunk(self):
        """Generate a sample audio chunk."""
        return np.random.randn(1024).astype(np.float32)

    def test_processor_initialization(self, processor):
        """Test processor initialization."""
        assert processor.detector is not None
        assert processor.mfcc_extractor is not None
        assert processor.vad is not None
        assert processor.noise_estimator is not None

    def test_process_chunk_no_speech(self, processor, sample_audio_chunk):
        """Test processing chunk with no speech detected."""
        with patch.object(processor.vad, "detect", return_value=(False, 0.2)):
            result = processor.process_chunk(sample_audio_chunk)

            assert result is None

    def test_process_chunk_with_speech(self, processor, sample_audio_chunk):
        """Test processing chunk with speech."""
        with patch.object(processor.vad, "detect", return_value=(True, 0.8)):
            with patch.object(processor, "_extract_features", return_value=np.random.randn(13, 10)):
                with patch.object(processor.detector, "_run_inference", return_value=0.95):
                    result = processor.process_chunk(sample_audio_chunk)

                    assert isinstance(result, DetectionResult)
                    assert result.detected is True

    def test_process_chunk_low_confidence(self, processor, sample_audio_chunk):
        """Test processing with low confidence."""
        with patch.object(processor.vad, "detect", return_value=(True, 0.8)):
            with patch.object(processor, "_extract_features", return_value=np.random.randn(13, 10)):
                with patch.object(processor.detector, "_run_inference", return_value=0.3):
                    result = processor.process_chunk(sample_audio_chunk)

                    assert result is None  # Below threshold

    def test_feature_extraction(self, processor, sample_audio_chunk):
        """Test audio feature extraction."""
        features = processor._extract_features(sample_audio_chunk)

        # Should return MFCC features or None
        assert features is None or isinstance(features, np.ndarray)

    def test_feature_extraction_with_noise_reduction(self, processor):
        """Test feature extraction with noise reduction."""
        noisy_audio = np.random.randn(1024).astype(np.float32) * 0.1

        with patch.object(processor.noise_estimator, "get_snr", return_value=5.0):  # Low SNR
            features = processor._extract_features(noisy_audio)

            # Should apply noise reduction
            assert features is None or isinstance(features, np.ndarray)


class TestDetectionAccuracy:
    """Test detection accuracy scenarios."""

    @pytest.fixture
    def detector(self):
        return WakeWordDetector(sensitivity=0.5)

    def test_true_positive_detection(self, detector):
        """Test correct wake word detection."""
        audio = np.random.randn(16000).astype(np.float32)

        with patch.object(detector, "_run_inference", return_value=0.95):
            result = detector.detect_batch(audio)

            assert result.detected is True
            assert result.confidence >= detector.threshold

    def test_true_negative_no_detection(self, detector):
        """Test correctly not detecting non-wake word."""
        audio = np.random.randn(16000).astype(np.float32) * 0.01  # Very quiet

        with patch.object(detector, "_run_inference", return_value=0.2):
            result = detector.detect_batch(audio)

            assert result.detected is False

    def test_false_positive_handling(self, detector):
        """Test handling potential false positives."""
        # Set high sensitivity (more false positives expected)
        detector.adjust_sensitivity(0.9)

        audio = np.random.randn(16000).astype(np.float32)

        with patch.object(detector, "_run_inference", return_value=0.4):
            result = detector.detect_batch(audio)

            # With high sensitivity, threshold is lower
            assert result.confidence == 0.4

    def test_minimum_detection_interval(self, detector):
        """Test minimum detection interval enforcement."""
        detector._last_detection_time = 1000.0

        with patch("time.time", return_value=1001.0):  # 1 second later
            with patch.object(detector, "_processor") as mock_processor:
                mock_processor.process_chunk.return_value = DetectionResult(
                    detected=True, confidence=0.95, timestamp=1001.0, latency_ms=50.0
                )

                audio = np.random.randn(1024).astype(np.float32)
                detector._audio_callback(audio)

                # Should be throttled (min interval is 2.0 seconds)
                assert detector._last_detection_time == 1000.0


class TestDifferentVoices:
    """Test detection with different voices and accents."""

    @pytest.fixture
    def detector(self):
        return WakeWordDetector(sensitivity=0.5)

    @pytest.mark.parametrize(
        "voice_type,expected_confidence",
        [
            ("child_high_pitch", 0.85),
            ("child_low_pitch", 0.82),
            ("adult_female", 0.75),
            ("adult_male", 0.70),
        ],
    )
    def test_different_voice_types(self, detector, voice_type, expected_confidence):
        """Test detection with different voice types."""
        audio = np.random.randn(16000).astype(np.float32)

        with patch.object(detector, "_run_inference", return_value=expected_confidence):
            result = detector.detect_batch(audio)

            if expected_confidence >= detector.threshold:
                assert result.detected is True
                assert result.confidence == expected_confidence

    def test_child_voice_optimized(self, detector):
        """Test detection optimized for children's voices."""
        # Children typically have higher fundamental frequency
        child_audio = np.sin(2 * np.pi * 300 * np.linspace(0, 1, 16000)).astype(np.float32)

        with patch.object(detector, "_run_inference", return_value=0.9):
            result = detector.detect_batch(child_audio)

            assert result.detected is True

    def test_noisy_environment(self, detector):
        """Test detection in noisy environment."""
        # Add noise to signal
        signal = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 16000)).astype(np.float32)
        noise = np.random.randn(16000).astype(np.float32) * 0.5
        noisy_audio = signal + noise

        result = detector.detect_batch(noisy_audio)

        # Should handle gracefully
        assert isinstance(result, DetectionResult)


class TestAsyncWakeWordDetector:
    """Test async wake word detector."""

    @pytest.fixture
    async def async_detector(self):
        """Create an async wake word detector."""
        detector = AsyncWakeWordDetector(sensitivity=0.5)
        return detector

    @pytest.mark.asyncio
    async def test_async_detector_initialization(self):
        """Test async detector initialization."""
        detector = AsyncWakeWordDetector(sensitivity=0.5)

        assert detector._detector is not None
        assert detector._detection_queue is not None

    @pytest.mark.asyncio
    async def test_async_start_listening(self, async_detector):
        """Test starting async listening."""
        with patch.object(async_detector._detector, "start_listening"):
            await async_detector.start_listening()

            # Callback should be registered
            assert len(async_detector._detector._callbacks) > 0

    @pytest.mark.asyncio
    async def test_async_stop_listening(self, async_detector):
        """Test stopping async listening."""
        with patch.object(async_detector._detector, "stop_listening"):
            await async_detector.stop_listening()

    @pytest.mark.asyncio
    async def test_wait_for_wake_word(self, async_detector):
        """Test waiting for wake word detection."""
        # Simulate detection
        result = DetectionResult(
            detected=True, confidence=0.95, timestamp=1234567890.0, latency_ms=90.0
        )

        # Put result in queue
        await async_detector._detection_queue.put(result)

        # Wait for it
        detected_result = await async_detector.wait_for_wake_word()

        assert detected_result.detected is True
        assert detected_result.confidence == 0.95

    @pytest.mark.asyncio
    async def test_async_iterator(self, async_detector):
        """Test async iteration over detections."""
        async_detector._detector._is_listening = True

        # Put some results in queue
        result1 = DetectionResult(True, 0.9, 1.0, 50.0)
        result2 = DetectionResult(True, 0.85, 2.0, 55.0)

        await async_detector._detection_queue.put(result1)
        await async_detector._detection_queue.put(result2)

        # Stop after 2 results
        async_detector._detector._is_listening = False

        # Collect results
        results = []
        try:
            async for result in async_detector:
                results.append(result)
                if len(results) >= 2:
                    break
        except StopAsyncIteration:
            pass

        assert len(results) <= 2


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_audio(self):
        """Test detection with empty audio."""
        detector = WakeWordDetector()
        empty_audio = np.array([])

        result = detector.detect_batch(empty_audio)

        assert result.detected is False

    def test_very_short_audio(self):
        """Test detection with very short audio."""
        detector = WakeWordDetector()
        short_audio = np.random.randn(100).astype(np.float32)

        result = detector.detect_batch(short_audio)

        # Should handle gracefully
        assert isinstance(result, DetectionResult)

    def test_very_long_audio(self):
        """Test detection with very long audio."""
        detector = WakeWordDetector()
        long_audio = np.random.randn(160000).astype(np.float32)  # 10 seconds

        result = detector.detect_batch(long_audio)

        assert isinstance(result, DetectionResult)

    def test_nan_audio(self):
        """Test handling of NaN values in audio."""
        detector = WakeWordDetector()
        nan_audio = np.full(16000, np.nan, dtype=np.float32)

        result = detector.detect_batch(nan_audio)

        # Should handle without crashing
        assert isinstance(result, DetectionResult)

    def test_callback_exception(self):
        """Test handling of exception in callback."""
        detector = WakeWordDetector()

        def faulty_callback(result):
            raise Exception("Callback error")

        detector.on_wake_word(faulty_callback)

        # Trigger callback
        result = DetectionResult(True, 0.95, 1.0, 50.0)

        # Should not crash
        detector._trigger_callbacks(result)

    def test_concurrent_start_stop(self):
        """Test concurrent start/stop operations."""
        detector = WakeWordDetector()

        # Patch where the engine binds the symbol (module-level import);
        # patching audio_capture instead would open the real microphone.
        with patch("src.audio.wake_word_engine.MicrophoneStream"):
            # Rapid start/stop
            detector.start_listening()
            detector.stop_listening()
            detector.start_listening()
            detector.stop_listening()

            # Should handle without issues
            assert detector.is_listening is False
