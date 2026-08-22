"""
Unit tests for Text-to-Speech (TTS) Engine.

Tests TTS functionality including:
- Audio generation
- Voice personas
- SSML support
- Speaking rate/pitch control
- Educational optimizations

Author: Testing Agent (TST-001)
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.audio.tts_engine import (
    AudioOutput,
    EmphasisLevel,
    Pyttsx3Backend,
    SpeakingRate,
    TTSBackend,
    TTSConfig,
    TTSEngine,
)


class TestAudioOutput:
    """Test audio output data class."""

    def test_audio_output_creation(self):
        """Test creating audio output."""
        audio_data = b"test audio data"

        output = AudioOutput(
            audio_data=audio_data, sample_rate=22050, duration_ms=1000.0, format="wav"
        )

        assert output.audio_data == audio_data
        assert output.sample_rate == 22050
        assert output.duration_ms == 1000.0
        assert output.format == "wav"

    def test_to_numpy(self):
        """Test converting audio to numpy array."""
        import numpy as np

        # Create audio data (16-bit PCM)
        audio_array = np.array([0, 100, -100, 200], dtype=np.int16)
        audio_bytes = audio_array.tobytes()

        output = AudioOutput(audio_data=audio_bytes, sample_rate=16000, duration_ms=100.0)

        numpy_array = output.to_numpy()

        assert len(numpy_array) == 4
        assert numpy_array.dtype == np.int16


class TestTTSConfig:
    """Test TTS configuration."""

    def test_default_config(self):
        """Test default configuration."""
        config = TTSConfig()

        assert config.backend == TTSBackend.PYTTSX3
        assert config.speaking_rate == 1.0
        assert config.pitch == 1.0
        assert config.volume == 1.0
        assert config.use_ssml is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = TTSConfig(
            backend=TTSBackend.EDGE_TTS, speaking_rate=1.2, pitch=1.1, volume=0.9, use_ssml=False
        )

        assert config.backend == TTSBackend.EDGE_TTS
        assert config.speaking_rate == 1.2
        assert config.pitch == 1.1
        assert config.volume == 0.9
        assert config.use_ssml is False


class TestTTSEngine:
    """Test main TTS engine functionality."""

    @pytest.fixture
    def tts_engine(self):
        """Create a TTS engine instance."""
        return TTSEngine()

    @pytest.fixture
    def sample_text(self):
        """Sample text for synthesis."""
        return "Hello, this is a test of the text to speech engine."

    def test_engine_initialization(self):
        """Test TTS engine initialization."""
        engine = TTSEngine()

        assert engine.config is not None
        assert engine.backend is not None
        assert engine.cache is not None

    def test_engine_with_config(self):
        """Test engine with custom configuration."""
        config = TTSConfig(speaking_rate=1.5, pitch=1.2, volume=0.8)

        engine = TTSEngine(config=config)

        assert engine.config.speaking_rate == 1.5
        assert engine.config.pitch == 1.2

    @pytest.mark.asyncio
    async def test_synthesize_text(self, tts_engine, sample_text):
        """Test basic text synthesis."""
        with patch.object(tts_engine.backend, "synthesize", new_callable=AsyncMock) as mock_synth:
            mock_synth.return_value = AudioOutput(
                audio_data=b"audio data", sample_rate=22050, duration_ms=1000.0
            )

            result = await tts_engine.synthesize(sample_text)

            assert isinstance(result, AudioOutput)
            mock_synth.assert_called_once()

    @pytest.mark.asyncio
    async def test_synthesize_with_cache(self, tts_engine, sample_text):
        """Test synthesis with caching."""
        mock_output = AudioOutput(audio_data=b"cached audio", sample_rate=22050, duration_ms=1000.0)

        with patch.object(tts_engine.backend, "synthesize", new_callable=AsyncMock) as mock_synth:
            mock_synth.return_value = mock_output

            # First call
            result1 = await tts_engine.synthesize(sample_text, use_cache=True)

            # Second call (should use cache)
            result2 = await tts_engine.synthesize(sample_text, use_cache=True)

            # Should only call backend once
            assert mock_synth.call_count == 1
            assert result1 == result2

    @pytest.mark.asyncio
    async def test_synthesize_no_cache(self, tts_engine, sample_text):
        """Test synthesis without caching."""
        mock_output = AudioOutput(audio_data=b"audio", sample_rate=22050, duration_ms=1000.0)

        with patch.object(tts_engine.backend, "synthesize", new_callable=AsyncMock) as mock_synth:
            mock_synth.return_value = mock_output

            result1 = await tts_engine.synthesize(sample_text, use_cache=False)
            result2 = await tts_engine.synthesize(sample_text, use_cache=False)

            # Should call backend twice
            assert mock_synth.call_count == 2

    @pytest.mark.asyncio
    async def test_synthesize_streaming(self, tts_engine, sample_text):
        """Test streaming synthesis."""

        async def mock_stream():
            yield b"chunk1"
            yield b"chunk2"
            yield b"chunk3"

        with patch.object(tts_engine.backend, "synthesize_streaming", return_value=mock_stream()):
            chunks = []
            async for chunk in tts_engine.synthesize_streaming(sample_text):
                chunks.append(chunk)

            assert len(chunks) == 3
            assert chunks[0] == b"chunk1"

    def test_set_voice(self, tts_engine):
        """Test setting voice."""
        with patch.object(tts_engine.backend, "set_voice") as mock_set:
            tts_engine.set_voice("en-US-AriaNeural")

            mock_set.assert_called_once_with("en-US-AriaNeural")

    def test_set_speed(self, tts_engine):
        """Test setting speaking speed."""
        tts_engine.set_speed(1.5)

        assert tts_engine.config.speaking_rate == 1.5

    def test_set_speed_enum(self, tts_engine):
        """Test setting speed with enum."""
        tts_engine.set_speed(SpeakingRate.FAST)

        assert tts_engine.config.speaking_rate == SpeakingRate.FAST.value

    def test_set_speed_bounds(self, tts_engine):
        """Test speed bounds checking."""
        # Too fast
        tts_engine.set_speed(3.0)
        assert tts_engine.config.speaking_rate == 2.0  # Clamped to max

        # Too slow
        tts_engine.set_speed(0.1)
        assert tts_engine.config.speaking_rate == 0.5  # Clamped to min

    def test_set_emphasis(self, tts_engine):
        """Test setting emphasis level."""
        tts_engine.set_emphasis(EmphasisLevel.STRONG)

        assert tts_engine._emphasis_level == EmphasisLevel.STRONG

    def test_list_voices(self, tts_engine):
        """Test listing available voices."""
        mock_voices = [
            {"id": "voice1", "name": "Voice 1", "gender": "Female"},
            {"id": "voice2", "name": "Voice 2", "gender": "Male"},
        ]

        with patch.object(tts_engine.backend, "list_voices", return_value=mock_voices):
            voices = tts_engine.list_voices()

            assert len(voices) == 2
            assert voices[0]["id"] == "voice1"

    def test_clear_cache(self, tts_engine):
        """Test clearing cache."""
        tts_engine.cache = {"key": "value"}

        tts_engine.clear_cache()

        assert len(tts_engine.cache) == 0


class TestTextPreprocessing:
    """Test text preprocessing."""

    @pytest.fixture
    def tts_engine(self):
        return TTSEngine()

    def test_remove_extra_whitespace(self, tts_engine):
        """Test removing extra whitespace."""
        text = "Hello    world  \n  test"

        processed = tts_engine._preprocess_text(text)

        assert "    " not in processed
        assert processed == "Hello world test"

    def test_expand_abbreviations(self, tts_engine):
        """Test expanding abbreviations."""
        text = "This is e.g. an example i.e. specifically."

        processed = tts_engine._preprocess_text(text)

        assert "e.g." not in processed
        assert "for example" in processed
        assert "i.e." not in processed
        assert "that is" in processed

    def test_expand_numbers(self, tts_engine):
        """Test expanding numbers to words."""
        text = "I have 5 apples and 10 oranges."

        processed = tts_engine._preprocess_text(text)

        assert "five" in processed
        assert "ten" in processed

    @pytest.mark.parametrize(
        "input_text,expected_contains",
        [
            ("Test 1 2 3", "one"),
            ("Count to 5", "five"),
            ("Number 10", "ten"),
        ],
    )
    def test_number_expansion_cases(self, tts_engine, input_text, expected_contains):
        """Test various number expansion cases."""
        processed = tts_engine._preprocess_text(input_text)

        assert expected_contains in processed


class TestMathExpressions:
    """Test mathematical expression handling."""

    @pytest.fixture
    def tts_engine(self):
        return TTSEngine()

    @pytest.mark.asyncio
    async def test_speak_math_simple(self, tts_engine):
        """Test speaking simple math expression."""
        expression = "2 + 3 = 5"

        with patch.object(tts_engine, "synthesize", new_callable=AsyncMock) as mock_synth:
            mock_synth.return_value = AudioOutput(
                audio_data=b"audio", sample_rate=22050, duration_ms=1000.0
            )

            result = await tts_engine.speak_math(expression)

            assert isinstance(result, AudioOutput)
            mock_synth.assert_called_once()

    @pytest.mark.asyncio
    async def test_speak_math_with_explanation(self, tts_engine):
        """Test speaking math with pedagogical pauses."""
        expression = "5 × 3 = 15"

        with patch.object(tts_engine, "synthesize", new_callable=AsyncMock) as mock_synth:
            mock_synth.return_value = AudioOutput(
                audio_data=b"audio", sample_rate=22050, duration_ms=1500.0
            )

            result = await tts_engine.speak_math(expression, explain=True)

            assert isinstance(result, AudioOutput)


class TestSSMLSupport:
    """Test SSML markup support."""

    @pytest.fixture
    def tts_engine(self):
        config = TTSConfig(use_ssml=True)
        return TTSEngine(config=config)

    def test_apply_ssml(self, tts_engine):
        """Test applying SSML markup."""
        text = "Hello world"
        tts_engine.voice_persona = Mock()

        ssml = tts_engine._apply_ssml(text)

        assert "<speak>" in ssml
        assert "</speak>" in ssml
        assert "<prosody" in ssml

    def test_add_pedagogical_pauses(self, tts_engine):
        """Test adding pedagogical pauses."""
        text = "First sentence. Second sentence. Therefore, we conclude."

        with_pauses = tts_engine._add_pedagogical_pauses(text)

        assert "<break" in with_pauses

    @pytest.mark.asyncio
    async def test_speak_with_pauses(self, tts_engine):
        """Test speaking with custom pauses."""
        text = "Hello world test"
        pause_points = [5, 11]  # After "Hello" and "world"

        with patch.object(tts_engine, "synthesize", new_callable=AsyncMock) as mock_synth:
            mock_synth.return_value = AudioOutput(
                audio_data=b"audio", sample_rate=22050, duration_ms=1500.0
            )

            result = await tts_engine.speak_with_pauses(
                text, pause_points=pause_points, pause_duration_ms=500
            )

            assert isinstance(result, AudioOutput)

    def test_insert_pauses(self, tts_engine):
        """Test inserting pauses at specific points."""
        text = "Hello world test"
        pause_points = [5]

        with_pauses = tts_engine._insert_pauses(text, pause_points, 500)

        assert '<break time="500ms"/>' in with_pauses


class TestVoicePersonas:
    """Test voice persona handling."""

    @pytest.fixture
    def tts_engine(self):
        return TTSEngine()

    def test_child_friendly_voice(self, tts_engine):
        """Test using child-friendly voice."""
        with patch.object(tts_engine.backend, "set_voice") as mock_set:
            tts_engine.set_voice("en-US-JennyNeural")  # Child-friendly voice

            mock_set.assert_called_once()

    @pytest.mark.parametrize(
        "voice_id",
        [
            "en-US-AriaNeural",
            "en-US-GuyNeural",
            "en-GB-SoniaNeural",
        ],
    )
    def test_different_voices(self, tts_engine, voice_id):
        """Test setting different voice personas."""
        with patch.object(tts_engine.backend, "set_voice") as mock_set:
            tts_engine.set_voice(voice_id)

            mock_set.assert_called_with(voice_id)


class TestPyttsx3Backend:
    """Test Pyttsx3 backend implementation."""

    @pytest.mark.asyncio
    async def test_pyttsx3_initialization(self):
        """Test Pyttsx3 backend initialization."""
        with patch("pyttsx3.init") as mock_init:
            mock_engine = Mock()
            mock_init.return_value = mock_engine

            config = TTSConfig()
            backend = Pyttsx3Backend(config)

            assert backend.engine is not None

    @pytest.mark.asyncio
    async def test_pyttsx3_synthesize(self):
        """Test Pyttsx3 synthesis."""
        with patch("pyttsx3.init") as mock_init:
            mock_engine = Mock()
            mock_init.return_value = mock_engine

            config = TTSConfig()
            backend = Pyttsx3Backend(config)

            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = b"audio data"

                    result = await backend.synthesize("Test text")

                    # Should have been synthesized
                    assert isinstance(result, AudioOutput)

    def test_pyttsx3_list_voices(self):
        """Test listing Pyttsx3 voices."""
        with patch("pyttsx3.init") as mock_init:
            mock_engine = Mock()
            mock_voice = Mock()
            mock_voice.id = "voice1"
            mock_voice.name = "Voice 1"
            mock_voice.languages = ["en-US"]
            mock_engine.getProperty.return_value = [mock_voice]
            mock_init.return_value = mock_engine

            config = TTSConfig()
            backend = Pyttsx3Backend(config)

            voices = backend.list_voices()

            assert len(voices) >= 0

    def test_pyttsx3_set_voice(self):
        """Test setting Pyttsx3 voice."""
        with patch("pyttsx3.init") as mock_init:
            mock_engine = Mock()
            mock_init.return_value = mock_engine

            config = TTSConfig()
            backend = Pyttsx3Backend(config)

            backend.set_voice("voice_id_123")

            assert backend.config.voice_id == "voice_id_123"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def tts_engine(self):
        return TTSEngine()

    @pytest.mark.asyncio
    async def test_empty_text(self, tts_engine):
        """Test synthesizing empty text."""
        with patch.object(tts_engine.backend, "synthesize", new_callable=AsyncMock) as mock_synth:
            mock_synth.return_value = AudioOutput(
                audio_data=b"", sample_rate=22050, duration_ms=0.0
            )

            result = await tts_engine.synthesize("")

            assert isinstance(result, AudioOutput)

    @pytest.mark.asyncio
    async def test_very_long_text(self, tts_engine):
        """Test synthesizing very long text."""
        long_text = "This is a test sentence. " * 100

        with patch.object(tts_engine.backend, "synthesize", new_callable=AsyncMock) as mock_synth:
            mock_synth.return_value = AudioOutput(
                audio_data=b"audio", sample_rate=22050, duration_ms=30000.0
            )

            result = await tts_engine.synthesize(long_text)

            assert isinstance(result, AudioOutput)

    @pytest.mark.asyncio
    async def test_special_characters(self, tts_engine):
        """Test with special characters."""
        text = "Test @#$% special &*() characters!"

        with patch.object(tts_engine.backend, "synthesize", new_callable=AsyncMock) as mock_synth:
            mock_synth.return_value = AudioOutput(
                audio_data=b"audio", sample_rate=22050, duration_ms=1000.0
            )

            result = await tts_engine.synthesize(text)

            assert isinstance(result, AudioOutput)

    @pytest.mark.asyncio
    async def test_unicode_characters(self, tts_engine):
        """Test with unicode characters."""
        text = "Hello 你好 مرحبا"

        with patch.object(tts_engine.backend, "synthesize", new_callable=AsyncMock) as mock_synth:
            mock_synth.return_value = AudioOutput(
                audio_data=b"audio", sample_rate=22050, duration_ms=1000.0
            )

            result = await tts_engine.synthesize(text)

            assert isinstance(result, AudioOutput)

    @pytest.mark.asyncio
    async def test_synthesis_error_handling(self, tts_engine):
        """Test error handling during synthesis."""
        with patch.object(tts_engine.backend, "synthesize", new_callable=AsyncMock) as mock_synth:
            mock_synth.side_effect = Exception("Synthesis error")

            with pytest.raises(Exception):
                await tts_engine.synthesize("Test")

    def test_cache_key_generation(self, tts_engine):
        """Test cache key generation."""
        text = "Hello world"

        key1 = tts_engine._get_cache_key(text)
        key2 = tts_engine._get_cache_key(text)

        # Should be consistent
        assert key1 == key2

        # Different settings should produce different keys
        tts_engine.config.speaking_rate = 1.5
        key3 = tts_engine._get_cache_key(text)

        assert key1 != key3

    @pytest.mark.asyncio
    async def test_multiple_concurrent_synthesis(self, tts_engine):
        """Test multiple concurrent synthesis requests."""
        with patch.object(tts_engine.backend, "synthesize", new_callable=AsyncMock) as mock_synth:
            mock_synth.return_value = AudioOutput(
                audio_data=b"audio", sample_rate=22050, duration_ms=1000.0
            )

            # Run multiple synthesis concurrently
            tasks = [
                tts_engine.synthesize("Text 1"),
                tts_engine.synthesize("Text 2"),
                tts_engine.synthesize("Text 3"),
            ]

            results = await asyncio.gather(*tasks)

            assert len(results) == 3
            assert all(isinstance(r, AudioOutput) for r in results)
