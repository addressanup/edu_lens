"""
Test Suite for Speech Recognition Components

Tests for child speech recognition including:
- Basic transcription accuracy
- Child speech adaptations
- Educational vocabulary
- Streaming performance
- Noise robustness
"""

import asyncio
import time
from pathlib import Path
from typing import List

import numpy as np
import pytest

from src.audio.speech_recognizer import (
    SpeechRecognizer,
    SpeechConfig,
    TranscriptionResult,
    StreamingTranscriber,
    LanguageHint,
    TranscriptionMode,
)
from src.audio.child_speech_adapter import (
    ChildSpeechAdapter,
    AgeGroup,
    MultiAgeAdapter,
    ACOUSTIC_PROFILES,
)
from src.audio.educational_vocabulary import (
    EducationalVocabulary,
    VocabularyContextManager,
    Subject,
)


class TestSpeechRecognizer:
    """Test suite for SpeechRecognizer class."""

    @pytest.fixture
    async def recognizer(self):
        """Create speech recognizer for testing."""
        config = SpeechConfig(
            model_size="base",  # Use base model for testing
            device="cpu",
            language="en",
            child_mode=True,
        )
        recognizer = SpeechRecognizer(config)
        await recognizer.initialize()
        yield recognizer
        await recognizer.close()

    @pytest.fixture
    def sample_audio(self):
        """Generate sample audio for testing."""
        # Generate 3 seconds of sine wave (simulating audio)
        sample_rate = 16000
        duration = 3.0
        frequency = 440  # A4 note

        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = np.sin(2 * np.pi * frequency * t).astype(np.float32) * 0.3

        return audio

    @pytest.fixture
    def sample_audio_file(self, tmp_path):
        """Create a temporary audio file for testing."""
        import wave

        file_path = tmp_path / "test_audio.wav"

        # Generate sample audio
        sample_rate = 16000
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = np.sin(2 * np.pi * 440 * t).astype(np.float32) * 0.3

        # Convert to int16
        audio_int16 = (audio * 32767).astype(np.int16)

        # Write WAV file
        with wave.open(str(file_path), 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())

        return file_path

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test recognizer initialization."""
        config = SpeechConfig(model_size="tiny")  # Use tiny model for fast tests
        recognizer = SpeechRecognizer(config)

        assert not recognizer._is_initialized

        await recognizer.initialize()

        assert recognizer._is_initialized
        assert recognizer.model is not None

        await recognizer.close()

    @pytest.mark.asyncio
    async def test_transcribe_audio_array(self, recognizer, sample_audio):
        """Test transcription with numpy array input."""
        result = await recognizer.transcribe(sample_audio)

        assert isinstance(result, TranscriptionResult)
        assert isinstance(result.text, str)
        assert 0.0 <= result.confidence <= 1.0
        assert result.language == "en"
        assert result.processing_time > 0

    @pytest.mark.asyncio
    async def test_transcribe_audio_file(self, recognizer, sample_audio_file):
        """Test transcription with audio file input."""
        result = await recognizer.transcribe(str(sample_audio_file))

        assert isinstance(result, TranscriptionResult)
        assert isinstance(result.text, str)

    @pytest.mark.asyncio
    async def test_word_timestamps(self, recognizer, sample_audio):
        """Test word-level timestamp extraction."""
        result = await recognizer.transcribe(sample_audio)

        # Check that word timestamps are included if available
        if result.word_timestamps:
            for wt in result.word_timestamps:
                assert wt.start >= 0
                assert wt.end > wt.start
                assert 0.0 <= wt.confidence <= 1.0
                assert len(wt.word) > 0

    @pytest.mark.asyncio
    async def test_confidence_scores(self, recognizer, sample_audio):
        """Test per-word confidence scores."""
        result = await recognizer.transcribe(sample_audio)

        confidence_scores = recognizer.get_confidence_scores(result)
        assert isinstance(confidence_scores, dict)

        for word, confidence in confidence_scores.items():
            assert isinstance(word, str)
            assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_vocabulary_boost(self, recognizer):
        """Test vocabulary boosting."""
        vocabulary = ["mathematics", "addition", "subtraction", "geometry"]

        recognizer.set_vocabulary_boost(vocabulary)

        assert recognizer.config.vocabulary_boost == vocabulary
        assert len(recognizer._vocabulary_prompt) > 0

    @pytest.mark.asyncio
    async def test_language_detection(self, recognizer, sample_audio):
        """Test language detection."""
        language, confidence = await recognizer.detect_language(sample_audio)

        assert isinstance(language, str)
        assert len(language) == 2  # ISO language code
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_streaming_transcription(self, recognizer):
        """Test streaming transcription."""
        # Create async generator of audio chunks
        async def audio_stream():
            sample_rate = 16000
            chunk_duration = 1.0  # 1 second chunks

            for i in range(3):  # Stream 3 chunks
                t = np.linspace(0, chunk_duration, int(sample_rate * chunk_duration))
                chunk = np.sin(2 * np.pi * 440 * t).astype(np.float32) * 0.3
                yield chunk
                await asyncio.sleep(0.1)  # Simulate real-time streaming

        results = []
        async for result in recognizer.transcribe_streaming(audio_stream()):
            results.append(result)

        assert len(results) > 0
        for result in results:
            assert isinstance(result, TranscriptionResult)


class TestChildSpeechAdapter:
    """Test suite for ChildSpeechAdapter class."""

    @pytest.fixture
    def adapter(self):
        """Create child speech adapter for testing."""
        return ChildSpeechAdapter(age_group=AgeGroup.GENERAL)

    @pytest.fixture
    def sample_audio(self):
        """Generate sample audio for testing."""
        sample_rate = 16000
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration))

        # Simulate child voice with higher frequency
        frequency = 280  # Child-like pitch
        audio = np.sin(2 * np.pi * frequency * t).astype(np.float32) * 0.3

        return audio

    def test_initialization(self, adapter):
        """Test adapter initialization."""
        assert adapter.age_group == AgeGroup.GENERAL
        assert adapter.profile == ACOUSTIC_PROFILES[AgeGroup.GENERAL]
        assert adapter.sample_rate == 16000

    def test_acoustic_profiles(self):
        """Test acoustic profile definitions."""
        for age_group in AgeGroup:
            if age_group == AgeGroup.GENERAL:
                continue

            profile = ACOUSTIC_PROFILES.get(age_group)
            assert profile is not None
            assert profile.f0_mean > 0
            assert profile.formant_shift_factor > 1.0
            assert profile.speaking_rate_wpm > 0

    def test_acoustic_adaptation(self, adapter, sample_audio):
        """Test acoustic model adaptation."""
        adapted = adapter.adapt_acoustic_model(sample_audio)

        assert isinstance(adapted, np.ndarray)
        assert adapted.shape == sample_audio.shape
        assert adapted.dtype == np.float32

    def test_vtln_adaptation(self, adapter, sample_audio):
        """Test VTLN (Vocal Tract Length Normalization)."""
        adapted = adapter._apply_vtln(sample_audio)

        assert isinstance(adapted, np.ndarray)
        assert len(adapted) == len(sample_audio)

    def test_speaking_rate_normalization(self, adapter, sample_audio):
        """Test speaking rate normalization."""
        normalized = adapter.normalize_speaking_rate(sample_audio, target_wpm=120.0)

        assert isinstance(normalized, np.ndarray)
        # Length may differ due to time stretching
        assert len(normalized) > 0

    def test_disfluency_handling(self, adapter):
        """Test disfluency detection and removal."""
        text_with_disfluencies = "um I think uh the answer is um five plus three equals uh eight"
        cleaned = adapter.handle_disfluencies(text_with_disfluencies)

        assert "um" not in cleaned.lower()
        assert "uh" not in cleaned.lower()
        assert "answer" in cleaned.lower()
        assert "eight" in cleaned.lower()

    def test_repetition_handling(self, adapter):
        """Test handling of word repetitions."""
        text_with_repetitions = "the the answer is is five five"
        cleaned = adapter.handle_disfluencies(text_with_repetitions)

        # Should remove consecutive duplicates
        words = cleaned.split()
        for i in range(len(words) - 1):
            assert words[i] != words[i + 1]

    def test_child_vocabulary_boost(self, adapter):
        """Test child-specific pronunciation variants."""
        base_vocab = ["three", "library", "because", "probably"]
        enhanced = adapter.boost_child_vocabulary(base_vocab)

        assert len(enhanced) > len(base_vocab)
        # Should include original and variants
        assert "three" in enhanced
        # May include variants like "free", "twee", etc.

    def test_confidence_adjustment(self, adapter):
        """Test confidence score adjustment for child speech."""
        base_confidence = 0.75
        adjusted = adapter.estimate_confidence_adjustment(base_confidence)

        assert adjusted >= base_confidence  # Should boost confidence
        assert adjusted <= 1.0

    def test_age_group_detection(self, adapter, sample_audio):
        """Test age group detection from audio."""
        detected_age, confidence = adapter.detect_age_group(sample_audio)

        assert isinstance(detected_age, AgeGroup)
        assert 0.0 <= confidence <= 1.0

    def test_f0_estimation(self, adapter, sample_audio):
        """Test fundamental frequency estimation."""
        f0 = adapter._estimate_f0(sample_audio)

        assert f0 > 0
        # Should be in reasonable range for child speech
        assert 150 <= f0 <= 450

    def test_preprocess_audio(self, adapter, sample_audio):
        """Test complete audio preprocessing pipeline."""
        processed = adapter.preprocess_audio(sample_audio)

        assert isinstance(processed, np.ndarray)
        assert len(processed) > 0

    def test_postprocess_transcription(self, adapter):
        """Test transcription post-processing."""
        text = "um the answer is is five plus um three equals eight"
        confidence = 0.80

        processed_text, adjusted_confidence = adapter.postprocess_transcription(text, confidence)

        assert len(processed_text) < len(text)  # Should remove disfluencies
        assert adjusted_confidence >= confidence


class TestMultiAgeAdapter:
    """Test suite for MultiAgeAdapter class."""

    @pytest.fixture
    def multi_adapter(self):
        """Create multi-age adapter for testing."""
        return MultiAgeAdapter()

    @pytest.fixture
    def sample_audio(self):
        """Generate sample audio for testing."""
        sample_rate = 16000
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = np.sin(2 * np.pi * 250 * t).astype(np.float32) * 0.3
        return audio

    def test_initialization(self, multi_adapter):
        """Test multi-age adapter initialization."""
        assert len(multi_adapter.adapters) > 0
        assert multi_adapter.default_adapter is not None

    def test_adapt_with_auto_detection(self, multi_adapter, sample_audio):
        """Test adaptation with automatic age detection."""
        adapted = multi_adapter.adapt_audio(sample_audio)

        assert isinstance(adapted, np.ndarray)
        assert len(adapted) > 0

    def test_adapt_with_specified_age(self, multi_adapter, sample_audio):
        """Test adaptation with specified age group."""
        adapted = multi_adapter.adapt_audio(sample_audio, age_group=AgeGroup.EARLY_ELEMENTARY)

        assert isinstance(adapted, np.ndarray)
        assert len(adapted) > 0


class TestEducationalVocabulary:
    """Test suite for EducationalVocabulary class."""

    @pytest.fixture
    def vocab_manager(self):
        """Create vocabulary manager for testing."""
        return EducationalVocabulary()

    def test_initialization(self, vocab_manager):
        """Test vocabulary manager initialization."""
        assert len(vocab_manager.vocabulary) > 0
        assert Subject.MATHEMATICS in vocab_manager.vocabulary
        assert Subject.SCIENCE in vocab_manager.vocabulary
        assert Subject.READING in vocab_manager.vocabulary

    def test_get_subject_vocabulary(self, vocab_manager):
        """Test retrieving subject-specific vocabulary."""
        math_vocab = vocab_manager.get_subject_vocabulary(Subject.MATHEMATICS)

        assert len(math_vocab) > 0
        assert "addition" in math_vocab
        assert "multiply" in math_vocab
        assert "fraction" in math_vocab

    def test_get_math_vocabulary(self, vocab_manager):
        """Test math vocabulary retrieval."""
        # Get all math vocabulary
        all_math = vocab_manager.get_math_vocabulary()
        assert len(all_math) > 0

        # Get specific category
        operations = vocab_manager.get_math_vocabulary("operations")
        assert "add" in operations
        assert "subtract" in operations
        assert "multiply" in operations

    def test_get_science_vocabulary(self, vocab_manager):
        """Test science vocabulary retrieval."""
        # Get specific category
        life_science = vocab_manager.get_science_vocabulary("life_science")
        assert "animal" in life_science
        assert "plant" in life_science
        assert "organism" in life_science

    def test_get_reading_vocabulary(self, vocab_manager):
        """Test reading vocabulary retrieval."""
        literary = vocab_manager.get_reading_vocabulary("literary_terms")
        assert "story" in literary
        assert "character" in literary
        assert "plot" in literary

    def test_spoken_forms(self, vocab_manager):
        """Test mathematical symbol spoken forms."""
        plus_forms = vocab_manager.get_spoken_forms("+")
        assert "plus" in plus_forms
        assert "add" in plus_forms

        equals_forms = vocab_manager.get_spoken_forms("=")
        assert "equals" in equals_forms

    def test_custom_vocabulary(self, vocab_manager):
        """Test adding custom vocabulary."""
        custom_terms = ["quantum", "photosynthesis", "algorithm"]
        vocab_manager.add_custom_vocabulary(Subject.SCIENCE, custom_terms)

        science_vocab = vocab_manager.get_subject_vocabulary(Subject.SCIENCE)
        for term in custom_terms:
            assert term in science_vocab

    def test_boost_prompt_creation(self, vocab_manager):
        """Test vocabulary boost prompt creation."""
        prompt = vocab_manager.create_boost_prompt(
            subjects=[Subject.MATHEMATICS],
            max_terms=20
        )

        assert len(prompt) > 0
        assert "Educational terms:" in prompt

    def test_is_educational_term(self, vocab_manager):
        """Test educational term detection."""
        assert vocab_manager.is_educational_term("addition")
        assert vocab_manager.is_educational_term("photosynthesis")
        assert not vocab_manager.is_educational_term("xyzabc123")

    def test_suggest_corrections(self, vocab_manager):
        """Test vocabulary correction suggestions."""
        suggestions = vocab_manager.suggest_corrections("additon")  # Misspelled
        assert len(suggestions) > 0
        # Should suggest "addition"


class TestVocabularyContextManager:
    """Test suite for VocabularyContextManager class."""

    @pytest.fixture
    def context_manager(self):
        """Create vocabulary context manager for testing."""
        return VocabularyContextManager()

    def test_initialization(self, context_manager):
        """Test context manager initialization."""
        assert context_manager.vocab_manager is not None
        assert context_manager.current_context is None

    def test_set_context(self, context_manager):
        """Test setting vocabulary context."""
        context_manager.set_context(Subject.MATHEMATICS)

        assert context_manager.current_context == Subject.MATHEMATICS
        assert Subject.MATHEMATICS in context_manager.context_history

    def test_get_context_vocabulary(self, context_manager):
        """Test retrieving context-specific vocabulary."""
        context_manager.set_context(Subject.SCIENCE)
        vocab = context_manager.get_context_vocabulary(max_terms=50)

        assert len(vocab) > 0
        assert len(vocab) <= 50

    def test_create_context_prompt(self, context_manager):
        """Test creating context-appropriate prompt."""
        context_manager.set_context(Subject.MATHEMATICS)
        prompt = context_manager.create_context_prompt()

        assert len(prompt) > 0

    def test_clear_context(self, context_manager):
        """Test clearing context."""
        context_manager.set_context(Subject.READING)
        context_manager.clear_context()

        assert context_manager.current_context is None


class TestIntegration:
    """Integration tests combining multiple components."""

    @pytest.mark.asyncio
    async def test_recognizer_with_adapter(self):
        """Test speech recognizer with child speech adapter."""
        # Create recognizer
        config = SpeechConfig(model_size="tiny", child_mode=True)
        recognizer = SpeechRecognizer(config)
        await recognizer.initialize()

        # Create adapter
        adapter = ChildSpeechAdapter(age_group=AgeGroup.GENERAL)

        # Generate sample audio
        sample_rate = 16000
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = np.sin(2 * np.pi * 280 * t).astype(np.float32) * 0.3

        # Preprocess with adapter
        adapted_audio = adapter.preprocess_audio(audio)

        # Transcribe
        result = await recognizer.transcribe(adapted_audio)

        # Post-process with adapter
        processed_text, adjusted_confidence = adapter.postprocess_transcription(
            result.text, result.confidence
        )

        assert isinstance(processed_text, str)
        assert adjusted_confidence >= result.confidence

        await recognizer.close()

    @pytest.mark.asyncio
    async def test_recognizer_with_vocabulary(self):
        """Test speech recognizer with educational vocabulary."""
        # Create recognizer
        config = SpeechConfig(model_size="tiny")
        recognizer = SpeechRecognizer(config)
        await recognizer.initialize()

        # Get educational vocabulary
        vocab_manager = EducationalVocabulary()
        math_vocab = vocab_manager.get_math_vocabulary()

        # Set vocabulary boost
        recognizer.set_vocabulary_boost(math_vocab[:50])

        # Generate sample audio
        sample_rate = 16000
        t = np.linspace(0, 2.0, int(sample_rate * 2.0))
        audio = np.sin(2 * np.pi * 440 * t).astype(np.float32) * 0.3

        # Transcribe
        result = await recognizer.transcribe(audio)

        assert isinstance(result, TranscriptionResult)

        await recognizer.close()


class TestAccuracy:
    """Accuracy tests for different age groups and conditions."""

    @pytest.mark.parametrize("age_group", [
        AgeGroup.EARLY_ELEMENTARY,
        AgeGroup.LATE_ELEMENTARY,
        AgeGroup.PRE_TEEN,
    ])
    def test_age_group_adaptations(self, age_group):
        """Test adaptations for different age groups."""
        adapter = ChildSpeechAdapter(age_group=age_group)

        # Verify correct profile is loaded
        assert adapter.profile == ACOUSTIC_PROFILES[age_group]

        # Verify F0 ranges are appropriate for age
        if age_group == AgeGroup.EARLY_ELEMENTARY:
            assert adapter.profile.f0_mean > 260
        elif age_group == AgeGroup.PRE_TEEN:
            assert adapter.profile.f0_mean < 250

    @pytest.mark.asyncio
    async def test_educational_vocabulary_accuracy(self):
        """Test recognition accuracy with educational vocabulary."""
        vocab_manager = EducationalVocabulary()

        # Test that all vocabulary categories are present
        math_vocab = vocab_manager.get_math_vocabulary()
        assert len(math_vocab) >= 50  # Should have substantial vocabulary

        science_vocab = vocab_manager.get_science_vocabulary()
        assert len(science_vocab) >= 50

        reading_vocab = vocab_manager.get_reading_vocabulary()
        assert len(reading_vocab) >= 30


class TestPerformance:
    """Performance and benchmarking tests."""

    @pytest.mark.asyncio
    async def test_transcription_latency(self):
        """Test transcription latency."""
        config = SpeechConfig(model_size="tiny")
        recognizer = SpeechRecognizer(config)
        await recognizer.initialize()

        # Generate short audio clip
        sample_rate = 16000
        duration = 3.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = np.sin(2 * np.pi * 440 * t).astype(np.float32) * 0.3

        # Measure transcription time
        start_time = time.time()
        result = await recognizer.transcribe(audio)
        elapsed = time.time() - start_time

        # Check that processing is reasonably fast
        assert elapsed < 10.0  # Should process 3s audio in under 10s
        assert result.processing_time > 0

        await recognizer.close()

    def test_adaptation_performance(self):
        """Test performance of audio adaptations."""
        adapter = ChildSpeechAdapter()

        # Generate audio
        sample_rate = 16000
        duration = 5.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = np.sin(2 * np.pi * 280 * t).astype(np.float32) * 0.3

        # Measure adaptation time
        start_time = time.time()
        adapted = adapter.preprocess_audio(audio)
        elapsed = time.time() - start_time

        # Should be fast
        assert elapsed < 2.0  # Process 5s audio in under 2s
        assert len(adapted) > 0


class TestNoiseRobustness:
    """Tests for noise robustness."""

    @pytest.fixture
    def clean_audio(self):
        """Generate clean audio signal."""
        sample_rate = 16000
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        return np.sin(2 * np.pi * 440 * t).astype(np.float32) * 0.3

    @pytest.fixture
    def noisy_audio(self, clean_audio):
        """Generate noisy audio signal."""
        noise = np.random.randn(len(clean_audio)).astype(np.float32) * 0.05
        return clean_audio + noise

    @pytest.mark.asyncio
    async def test_noise_handling(self, noisy_audio):
        """Test recognition with noisy audio."""
        config = SpeechConfig(model_size="tiny")
        recognizer = SpeechRecognizer(config)
        await recognizer.initialize()

        result = await recognizer.transcribe(noisy_audio)

        # Should still produce result even with noise
        assert isinstance(result, TranscriptionResult)

        await recognizer.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
