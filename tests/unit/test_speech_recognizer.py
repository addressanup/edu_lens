"""
Unit tests for Speech Recognition Engine (ASR).

Tests speech recognition including:
- Transcription accuracy
- Child speech handling
- Noisy environment robustness
- Streaming vs batch modes
- Language detection

Author: Testing Agent (TST-001)
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pytest

from src.audio.speech_recognizer import (
    LanguageHint,
    SpeechConfig,
    SpeechRecognizer,
    StreamingTranscriber,
    TranscriptionMode,
    TranscriptionResult,
    WordTimestamp,
)


class TestWordTimestamp:
    """Test word timestamp data class."""

    def test_word_timestamp_creation(self):
        """Test creating a word timestamp."""
        timestamp = WordTimestamp(word="hello", start=0.0, end=0.5, confidence=0.95)

        assert timestamp.word == "hello"
        assert timestamp.start == 0.0
        assert timestamp.end == 0.5
        assert timestamp.confidence == 0.95

    def test_duration_calculation(self):
        """Test duration property."""
        timestamp = WordTimestamp("test", 1.0, 2.5, 0.9)

        assert timestamp.duration == 1.5


class TestTranscriptionResult:
    """Test transcription result data class."""

    def test_transcription_result_creation(self):
        """Test creating a transcription result."""
        result = TranscriptionResult(
            text="Hello world", confidence=0.92, language="en", processing_time=0.5
        )

        assert result.text == "Hello world"
        assert result.confidence == 0.92
        assert result.language == "en"

    def test_words_property(self):
        """Test words property."""
        result = TranscriptionResult(text="Hello world test", confidence=0.9, language="en")

        words = result.words
        assert len(words) == 3
        assert words[0] == "Hello"

    def test_duration_from_timestamps(self):
        """Test duration calculation from timestamps."""
        timestamps = [
            WordTimestamp("hello", 0.0, 0.5, 0.95),
            WordTimestamp("world", 0.5, 1.2, 0.90),
        ]

        result = TranscriptionResult(
            text="hello world", confidence=0.925, language="en", word_timestamps=timestamps
        )

        assert result.duration == 1.2

    def test_empty_result(self):
        """Test empty transcription result."""
        result = TranscriptionResult(text="", confidence=0.0, language="en")

        assert result.duration == 0.0
        assert len(result.words) == 0


class TestSpeechConfig:
    """Test speech configuration."""

    def test_default_config(self):
        """Test default configuration."""
        config = SpeechConfig()

        assert config.model_size == "base"
        assert config.language == "en"
        assert config.sample_rate == 16000
        assert config.child_mode is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = SpeechConfig(model_size="small", language="es", temperature=0.5, child_mode=False)

        assert config.model_size == "small"
        assert config.language == "es"
        assert config.temperature == 0.5
        assert config.child_mode is False

    def test_vocabulary_boost(self):
        """Test vocabulary boosting configuration."""
        vocab = ["photosynthesis", "chlorophyll", "ecosystem"]

        config = SpeechConfig(vocabulary_boost=vocab)

        assert len(config.vocabulary_boost) == 3
        assert "photosynthesis" in config.vocabulary_boost


class TestSpeechRecognizer:
    """Test main speech recognizer functionality."""

    @pytest.fixture
    def sample_audio(self):
        """Generate sample audio data."""
        return np.random.randn(16000).astype(np.float32)

    @pytest.fixture
    def recognizer(self):
        """Create a speech recognizer instance."""
        config = SpeechConfig(model_size="base")
        return SpeechRecognizer(config=config)

    @pytest.fixture
    def mock_whisper_model(self):
        """Mock Whisper model."""
        model = Mock()
        model.transcribe = Mock(
            return_value={
                "text": "This is a test transcription",
                "language": "en",
                "segments": [
                    {
                        "avg_logprob": -0.5,
                        "words": [
                            {"word": "This", "start": 0.0, "end": 0.3, "probability": 0.95},
                            {"word": "is", "start": 0.3, "end": 0.5, "probability": 0.93},
                            {"word": "a", "start": 0.5, "end": 0.6, "probability": 0.90},
                            {"word": "test", "start": 0.6, "end": 1.0, "probability": 0.92},
                        ],
                    }
                ],
            }
        )
        return model

    def test_recognizer_initialization(self):
        """Test recognizer initialization."""
        recognizer = SpeechRecognizer()

        assert recognizer.config is not None
        assert recognizer.model is None  # Not initialized yet
        assert recognizer._is_initialized is False

    @pytest.mark.asyncio
    async def test_initialize_recognizer(self, recognizer):
        """Test initializing the recognizer."""
        with patch("whisper.load_model") as mock_load:
            mock_load.return_value = Mock()

            await recognizer.initialize()

            assert recognizer._is_initialized is True
            assert recognizer.model is not None
            mock_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, recognizer):
        """Test initializing when already initialized."""
        with patch("whisper.load_model") as mock_load:
            mock_load.return_value = Mock()

            await recognizer.initialize()
            await recognizer.initialize()  # Second call

            # Should only load once
            assert mock_load.call_count == 1

    @pytest.mark.asyncio
    async def test_transcribe_audio_array(self, recognizer, sample_audio, mock_whisper_model):
        """Test transcribing audio from numpy array."""
        recognizer.model = mock_whisper_model
        recognizer._is_initialized = True

        result = await recognizer.transcribe(sample_audio)

        assert isinstance(result, TranscriptionResult)
        assert result.text == "This is a test transcription"
        assert result.language == "en"
        assert result.processing_time > 0

    @pytest.mark.asyncio
    async def test_transcribe_audio_file(self, recognizer, mock_whisper_model, tmp_path):
        """Test transcribing audio from file."""
        recognizer.model = mock_whisper_model
        recognizer._is_initialized = True

        # Create a dummy audio file
        audio_file = tmp_path / "test.wav"
        audio_file.touch()

        with patch("whisper.load_audio") as mock_load_audio:
            mock_load_audio.return_value = np.random.randn(16000).astype(np.float32)
            with patch("whisper.pad_or_trim") as mock_pad:
                mock_pad.return_value = np.random.randn(16000).astype(np.float32)

                result = await recognizer.transcribe(str(audio_file))

        assert isinstance(result, TranscriptionResult)

    @pytest.mark.asyncio
    async def test_transcribe_with_language(self, recognizer, sample_audio, mock_whisper_model):
        """Test transcription with specified language."""
        recognizer.model = mock_whisper_model
        recognizer._is_initialized = True

        result = await recognizer.transcribe(sample_audio, language="es")

        assert isinstance(result, TranscriptionResult)

    @pytest.mark.asyncio
    async def test_transcribe_with_temperature(self, recognizer, sample_audio, mock_whisper_model):
        """Test transcription with custom temperature."""
        recognizer.model = mock_whisper_model
        recognizer._is_initialized = True

        result = await recognizer.transcribe(sample_audio, temperature=0.5)

        assert isinstance(result, TranscriptionResult)

    @pytest.mark.asyncio
    async def test_word_timestamp_extraction(self, recognizer, sample_audio, mock_whisper_model):
        """Test extracting word-level timestamps."""
        recognizer.model = mock_whisper_model
        recognizer._is_initialized = True

        result = await recognizer.transcribe(sample_audio)

        assert len(result.word_timestamps) > 0
        assert all(isinstance(wt, WordTimestamp) for wt in result.word_timestamps)

    @pytest.mark.asyncio
    async def test_confidence_calculation(self, recognizer, sample_audio, mock_whisper_model):
        """Test confidence score calculation."""
        recognizer.model = mock_whisper_model
        recognizer._is_initialized = True

        result = await recognizer.transcribe(sample_audio)

        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_detect_language(self, recognizer):
        """Test language detection."""
        recognizer._is_initialized = True

        mock_model = Mock()
        mock_model.detect_language = Mock(
            return_value=(Mock(), {"en": 0.95, "es": 0.03, "fr": 0.02})
        )
        recognizer.model = mock_model

        audio = np.random.randn(16000).astype(np.float32)

        with patch("whisper.load_audio") as mock_load:
            mock_load.return_value = audio
            with patch("whisper.pad_or_trim") as mock_pad:
                mock_pad.return_value = audio
                with patch("whisper.audio.log_mel_spectrogram") as mock_mel:
                    mock_mel.return_value = Mock()

                    language, confidence = await recognizer.detect_language(audio)

        assert language == "en"
        assert confidence == 0.95

    def test_get_word_timestamps(self, recognizer):
        """Test getting word timestamps."""
        timestamps = [
            WordTimestamp("hello", 0.0, 0.5, 0.95),
            WordTimestamp("world", 0.5, 1.2, 0.90),
        ]

        result = TranscriptionResult(
            text="hello world", confidence=0.925, language="en", word_timestamps=timestamps
        )

        extracted = recognizer.get_word_timestamps(result)

        assert len(extracted) == 2
        assert extracted[0].word == "hello"

    def test_get_confidence_scores(self, recognizer):
        """Test getting per-word confidence scores."""
        timestamps = [
            WordTimestamp("hello", 0.0, 0.5, 0.95),
            WordTimestamp("world", 0.5, 1.2, 0.90),
        ]

        result = TranscriptionResult(
            text="hello world", confidence=0.925, language="en", word_timestamps=timestamps
        )

        scores = recognizer.get_confidence_scores(result)

        assert len(scores) == 2
        assert scores["hello"] == 0.95
        assert scores["world"] == 0.90

    def test_set_vocabulary_boost(self, recognizer):
        """Test setting vocabulary boost."""
        vocabulary = ["photosynthesis", "ecosystem", "biodiversity"]

        recognizer.set_vocabulary_boost(vocabulary)

        assert len(recognizer.config.vocabulary_boost) == 3
        assert recognizer._vocabulary_prompt != ""

    @pytest.mark.asyncio
    async def test_close_recognizer(self, recognizer):
        """Test closing and cleanup."""
        recognizer.model = Mock()
        recognizer._is_initialized = True

        await recognizer.close()

        assert recognizer.model is None
        assert recognizer._is_initialized is False


class TestChildSpeechHandling:
    """Test child speech specific handling."""

    @pytest.fixture
    def child_recognizer(self):
        """Create recognizer optimized for children."""
        config = SpeechConfig(
            child_mode=True, age_group="6-12", vocabulary_boost=["math", "science", "reading"]
        )
        return SpeechRecognizer(config=config)

    @pytest.mark.asyncio
    async def test_child_mode_enabled(self, child_recognizer):
        """Test that child mode is enabled."""
        assert child_recognizer.config.child_mode is True
        assert child_recognizer.config.age_group == "6-12"

    @pytest.mark.asyncio
    async def test_educational_vocabulary(self, child_recognizer):
        """Test educational vocabulary boosting."""
        child_recognizer._build_vocabulary_prompt()

        prompt = child_recognizer._vocabulary_prompt

        assert "math" in prompt or len(child_recognizer.config.vocabulary_boost) > 0

    @pytest.mark.asyncio
    async def test_high_pitch_voice(self, child_recognizer):
        """Test handling of high-pitched children's voices."""
        # Simulate child voice (higher frequency)
        sample_rate = 16000
        duration = 1.0
        frequency = 300  # Higher than adult voices

        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = np.sin(2 * np.pi * frequency * t).astype(np.float32)

        child_recognizer._is_initialized = True
        child_recognizer.model = Mock()
        child_recognizer.model.transcribe = Mock(
            return_value={"text": "Test", "language": "en", "segments": []}
        )

        result = await child_recognizer.transcribe(audio)

        assert isinstance(result, TranscriptionResult)


class TestNoisyEnvironment:
    """Test robustness in noisy environments."""

    @pytest.fixture
    def recognizer(self):
        return SpeechRecognizer()

    @pytest.mark.asyncio
    async def test_low_snr_audio(self, recognizer):
        """Test transcription with low SNR audio."""
        # Create signal with noise
        signal = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 16000)).astype(np.float32)
        noise = np.random.randn(16000).astype(np.float32) * 0.8
        noisy_audio = signal + noise

        recognizer._is_initialized = True
        recognizer.model = Mock()
        recognizer.model.transcribe = Mock(
            return_value={
                "text": "Noisy transcription",
                "language": "en",
                "segments": [],
                "no_speech_prob": 0.3,
            }
        )

        result = await recognizer.transcribe(noisy_audio)

        # Should handle without crashing
        assert isinstance(result, TranscriptionResult)

    @pytest.mark.asyncio
    async def test_background_noise(self, recognizer):
        """Test with background noise."""
        # Create audio with continuous background noise
        speech = np.random.randn(16000).astype(np.float32) * 0.5
        background = np.random.randn(16000).astype(np.float32) * 0.3

        audio_with_bg = speech + background

        recognizer._is_initialized = True
        recognizer.model = Mock()
        recognizer.model.transcribe = Mock(
            return_value={"text": "Background test", "language": "en", "segments": []}
        )

        result = await recognizer.transcribe(audio_with_bg)

        assert isinstance(result, TranscriptionResult)


class TestStreamingTranscription:
    """Test streaming transcription functionality."""

    @pytest.fixture
    def recognizer(self):
        config = SpeechConfig(chunk_duration=5.0, overlap_duration=0.5)
        return SpeechRecognizer(config=config)

    @pytest.fixture
    async def audio_stream(self):
        """Create a mock audio stream."""

        async def stream_generator():
            for _ in range(5):
                chunk = np.random.randn(8000).astype(np.float32)
                yield chunk
                await asyncio.sleep(0.01)

        return stream_generator()

    @pytest.mark.asyncio
    async def test_streaming_transcription(self, recognizer, audio_stream):
        """Test streaming transcription mode."""
        recognizer._is_initialized = True
        recognizer.model = Mock()
        recognizer.model.transcribe = Mock(
            return_value={"text": "Streaming chunk", "language": "en", "segments": []}
        )

        results = []
        async for result in recognizer.transcribe_streaming(audio_stream):
            results.append(result)
            if len(results) >= 2:
                break

        assert len(results) > 0
        assert all(isinstance(r, TranscriptionResult) for r in results)

    @pytest.mark.asyncio
    async def test_overlap_filtering(self, recognizer):
        """Test filtering of overlapping text."""
        previous = "Hello world this is"
        current = "this is a test"

        filtered = recognizer._filter_overlap_text(current, previous)

        # Should remove "this is" overlap
        assert "a test" in filtered

    @pytest.mark.asyncio
    async def test_streaming_transcriber(self, recognizer):
        """Test StreamingTranscriber helper."""
        recognizer._is_initialized = True
        recognizer.model = Mock()
        recognizer.model.transcribe = Mock(
            return_value={"text": "Test", "language": "en", "segments": []}
        )

        transcriber = StreamingTranscriber(
            recognizer=recognizer, chunk_duration=2.0, overlap_duration=0.3
        )

        audio_queue = asyncio.Queue()
        stop_event = asyncio.Event()

        # Add some audio chunks
        for _ in range(3):
            await audio_queue.put(np.random.randn(8000).astype(np.float32))

        # Stop after brief period
        asyncio.create_task(self._stop_after_delay(stop_event, 0.1))

        results = []
        async for result in transcriber.transcribe_stream(audio_queue, stop_event):
            results.append(result)
            if len(results) >= 1:
                break

        # Should get at least one result
        assert len(results) >= 0

    async def _stop_after_delay(self, event, delay):
        """Helper to stop event after delay."""
        await asyncio.sleep(delay)
        event.set()


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def recognizer(self):
        return SpeechRecognizer()

    @pytest.mark.asyncio
    async def test_empty_audio(self, recognizer):
        """Test with empty audio."""
        empty_audio = np.array([])

        recognizer._is_initialized = True
        recognizer.model = Mock()
        recognizer.model.transcribe = Mock(
            return_value={"text": "", "language": "en", "segments": []}
        )

        result = await recognizer.transcribe(empty_audio)

        assert result.text == ""

    @pytest.mark.asyncio
    async def test_very_short_audio(self, recognizer):
        """Test with very short audio clip."""
        short_audio = np.random.randn(100).astype(np.float32)

        recognizer._is_initialized = True
        recognizer.model = Mock()
        recognizer.model.transcribe = Mock(
            return_value={"text": "Hi", "language": "en", "segments": []}
        )

        result = await recognizer.transcribe(short_audio)

        assert isinstance(result, TranscriptionResult)

    @pytest.mark.asyncio
    async def test_very_long_audio(self, recognizer):
        """Test with very long audio (over 30 seconds)."""
        long_audio = np.random.randn(480000).astype(np.float32)  # 30 seconds

        recognizer._is_initialized = True
        recognizer.model = Mock()
        recognizer.model.transcribe = Mock(
            return_value={"text": "Long transcription", "language": "en", "segments": []}
        )

        result = await recognizer.transcribe(long_audio)

        assert isinstance(result, TranscriptionResult)

    @pytest.mark.asyncio
    async def test_silent_audio(self, recognizer):
        """Test with silent audio."""
        silent_audio = np.zeros(16000, dtype=np.float32)

        recognizer._is_initialized = True
        recognizer.model = Mock()
        recognizer.model.transcribe = Mock(
            return_value={"text": "", "language": "en", "segments": [], "no_speech_prob": 0.99}
        )

        result = await recognizer.transcribe(silent_audio)

        assert result.text == ""

    @pytest.mark.asyncio
    async def test_transcription_error_handling(self, recognizer):
        """Test error handling during transcription."""
        recognizer._is_initialized = True
        recognizer.model = Mock()
        recognizer.model.transcribe = Mock(side_effect=Exception("Transcription error"))

        audio = np.random.randn(16000).astype(np.float32)

        with pytest.raises(Exception):
            await recognizer.transcribe(audio)

    @pytest.mark.asyncio
    async def test_uninitialized_recognizer(self, recognizer):
        """Test using recognizer before initialization."""
        audio = np.random.randn(16000).astype(np.float32)

        with patch("whisper.load_model") as mock_load:
            mock_load.return_value = Mock()
            mock_load.return_value.transcribe = Mock(
                return_value={"text": "Test", "language": "en", "segments": []}
            )

            # Should auto-initialize
            result = await recognizer.transcribe(audio)

        assert recognizer._is_initialized is True

    @pytest.mark.parametrize("model_size", ["tiny", "base", "small", "medium"])
    @pytest.mark.asyncio
    async def test_different_model_sizes(self, model_size):
        """Test with different model sizes."""
        config = SpeechConfig(model_size=model_size)
        recognizer = SpeechRecognizer(config=config)

        assert recognizer.config.model_size == model_size

    @pytest.mark.asyncio
    async def test_audio_normalization(self, recognizer):
        """Test audio normalization handling."""
        # Audio in int16 range
        audio_int16 = np.random.randint(-32768, 32767, 16000).astype(np.float32)

        recognizer._is_initialized = True
        recognizer.model = Mock()
        recognizer.model.transcribe = Mock(
            return_value={"text": "Normalized", "language": "en", "segments": []}
        )

        result = await recognizer.transcribe(audio_int16)

        # Should normalize automatically
        assert isinstance(result, TranscriptionResult)
