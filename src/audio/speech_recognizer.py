"""
Speech Recognition Engine for EduLens

Implements ASR (Automatic Speech Recognition) optimized for children's speech
patterns (ages 6-12) with support for educational vocabulary and real-time
transcription.

Uses OpenAI Whisper as the backend ASR engine with custom optimizations for
child speech and educational contexts.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, AsyncIterator, Union

import numpy as np
import torch
import whisper
from whisper.audio import SAMPLE_RATE, N_FRAMES, HOP_LENGTH, log_mel_spectrogram

logger = logging.getLogger(__name__)


class TranscriptionMode(Enum):
    """Transcription processing modes."""
    BATCH = "batch"  # Process complete audio files
    STREAMING = "streaming"  # Real-time streaming transcription
    BUFFERED = "buffered"  # Buffered streaming with context


class LanguageHint(Enum):
    """Language hints for transcription."""
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    CHINESE = "zh"
    HINDI = "hi"       # Hindi for India market
    NEPALESE = "ne"    # Nepalese/Nepali
    AUTO = None  # Auto-detect language


# Supported languages for EduLens multi-language support
SUPPORTED_LANGUAGES = {"en", "es", "fr", "de", "zh", "hi", "ne"}


@dataclass
class WordTimestamp:
    """Word-level timestamp information."""
    word: str
    start: float  # Start time in seconds
    end: float  # End time in seconds
    confidence: float  # Word confidence score (0.0-1.0)

    @property
    def duration(self) -> float:
        """Get word duration in seconds."""
        return self.end - self.start


@dataclass
class TranscriptionResult:
    """Result from speech recognition."""
    text: str  # Transcribed text
    confidence: float  # Overall confidence score
    language: str  # Detected/specified language
    word_timestamps: List[WordTimestamp] = field(default_factory=list)
    processing_time: float = 0.0  # Processing time in seconds
    metadata: Dict = field(default_factory=dict)  # Additional metadata

    @property
    def words(self) -> List[str]:
        """Get list of words."""
        return self.text.split()

    @property
    def duration(self) -> float:
        """Get total audio duration from timestamps."""
        if not self.word_timestamps:
            return 0.0
        return self.word_timestamps[-1].end if self.word_timestamps else 0.0


@dataclass
class SpeechConfig:
    """Configuration for speech recognition."""
    # Model settings
    model_size: str = "base"  # tiny, base, small, medium, large
    device: str = "cpu"  # cpu, cuda
    compute_type: str = "int8"  # float16, int8

    # Language settings
    language: Optional[str] = "en"  # None for auto-detect
    task: str = "transcribe"  # transcribe or translate

    # Transcription settings
    beam_size: int = 5  # Beam search size
    best_of: int = 5  # Number of candidates
    temperature: float = 0.0  # Sampling temperature (0.0 = greedy)

    # Audio processing
    sample_rate: int = 16000  # Audio sample rate (Hz)
    chunk_duration: float = 30.0  # Chunk duration for streaming (seconds)
    overlap_duration: float = 1.0  # Overlap between chunks (seconds)

    # Word-level timestamps
    word_timestamps: bool = True  # Enable word-level timestamps

    # Vocabulary boosting
    initial_prompt: Optional[str] = None  # Context/vocabulary hints
    vocabulary_boost: List[str] = field(default_factory=list)

    # Child speech optimizations
    child_mode: bool = True  # Enable child speech adaptations
    age_group: str = "6-12"  # Target age group

    # Performance
    num_threads: int = 4  # CPU threads
    batch_size: int = 1  # Batch size for processing

    # Quality settings
    condition_on_previous_text: bool = True  # Use previous context
    compression_ratio_threshold: float = 2.4  # Compression ratio limit
    logprob_threshold: float = -1.0  # Log probability threshold
    no_speech_threshold: float = 0.6  # No-speech probability threshold


class SpeechRecognizer:
    """
    Main speech recognition engine using Whisper.

    Provides batch and streaming transcription with optimizations for
    children's speech patterns and educational vocabulary.
    """

    def __init__(self, config: Optional[SpeechConfig] = None):
        """
        Initialize speech recognizer.

        Args:
            config: Speech recognition configuration
        """
        self.config = config or SpeechConfig()
        self.model: Optional[whisper.Whisper] = None
        self._is_initialized = False
        self._vocabulary_prompt = ""

        logger.info(f"Initializing SpeechRecognizer with model: {self.config.model_size}")

    async def initialize(self) -> None:
        """Initialize the speech recognition model."""
        if self._is_initialized:
            return

        try:
            # Load Whisper model
            logger.info(f"Loading Whisper model: {self.config.model_size}")
            self.model = await asyncio.to_thread(
                whisper.load_model,
                self.config.model_size,
                device=self.config.device
            )

            # Set number of threads for CPU inference
            if self.config.device == "cpu":
                torch.set_num_threads(self.config.num_threads)

            # Build vocabulary prompt
            self._build_vocabulary_prompt()

            self._is_initialized = True
            logger.info("SpeechRecognizer initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize SpeechRecognizer: {e}")
            raise

    def _build_vocabulary_prompt(self) -> None:
        """Build vocabulary prompt from boosted words."""
        if self.config.vocabulary_boost:
            # Create a prompt that includes boosted vocabulary
            vocab_text = ", ".join(self.config.vocabulary_boost[:50])  # Limit length
            self._vocabulary_prompt = f"Educational context: {vocab_text}"

        if self.config.initial_prompt:
            if self._vocabulary_prompt:
                self._vocabulary_prompt = f"{self.config.initial_prompt}. {self._vocabulary_prompt}"
            else:
                self._vocabulary_prompt = self.config.initial_prompt

    async def transcribe(
        self,
        audio: Union[np.ndarray, str, Path],
        language: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio to text (batch mode).

        Args:
            audio: Audio data as numpy array or path to audio file
            language: Language code (overrides config)
            temperature: Sampling temperature (overrides config)

        Returns:
            TranscriptionResult with text and metadata
        """
        if not self._is_initialized:
            await self.initialize()

        start_time = time.time()

        try:
            # Load audio if path provided
            if isinstance(audio, (str, Path)):
                audio = await asyncio.to_thread(whisper.load_audio, str(audio))
                audio = whisper.pad_or_trim(audio)

            # Ensure audio is in correct format
            if isinstance(audio, np.ndarray):
                if audio.dtype != np.float32:
                    audio = audio.astype(np.float32)

                # Normalize audio
                if audio.max() > 1.0:
                    audio = audio / 32768.0  # Convert from int16 range

            # Prepare transcription options
            options = {
                "language": language or self.config.language,
                "task": self.config.task,
                "beam_size": self.config.beam_size,
                "best_of": self.config.best_of,
                "temperature": temperature if temperature is not None else self.config.temperature,
                "word_timestamps": self.config.word_timestamps,
                "condition_on_previous_text": self.config.condition_on_previous_text,
                "compression_ratio_threshold": self.config.compression_ratio_threshold,
                "logprob_threshold": self.config.logprob_threshold,
                "no_speech_threshold": self.config.no_speech_threshold,
            }

            # Add vocabulary prompt if available
            if self._vocabulary_prompt:
                options["initial_prompt"] = self._vocabulary_prompt

            # Transcribe
            result = await asyncio.to_thread(
                self.model.transcribe,
                audio,
                **options
            )

            # Extract word timestamps
            word_timestamps = self._extract_word_timestamps(result)

            # Calculate overall confidence
            confidence = self._calculate_confidence(result)

            processing_time = time.time() - start_time

            return TranscriptionResult(
                text=result["text"].strip(),
                confidence=confidence,
                language=result.get("language", options["language"]),
                word_timestamps=word_timestamps,
                processing_time=processing_time,
                metadata={
                    "segments": result.get("segments", []),
                    "no_speech_prob": result.get("no_speech_prob", 0.0),
                }
            )

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    async def transcribe_streaming(
        self,
        audio_stream: AsyncIterator[np.ndarray],
        language: Optional[str] = None,
    ) -> AsyncIterator[TranscriptionResult]:
        """
        Transcribe audio in real-time streaming mode.

        Args:
            audio_stream: Async iterator yielding audio chunks
            language: Language code (overrides config)

        Yields:
            TranscriptionResult for each processed chunk
        """
        if not self._is_initialized:
            await self.initialize()

        chunk_samples = int(self.config.chunk_duration * self.config.sample_rate)
        overlap_samples = int(self.config.overlap_duration * self.config.sample_rate)

        buffer = np.array([], dtype=np.float32)
        previous_text = ""

        async for audio_chunk in audio_stream:
            # Append to buffer
            buffer = np.append(buffer, audio_chunk)

            # Process when buffer is large enough
            if len(buffer) >= chunk_samples:
                # Extract chunk with overlap
                chunk = buffer[:chunk_samples]

                # Keep overlap for next iteration
                buffer = buffer[chunk_samples - overlap_samples:]

                # Transcribe chunk
                try:
                    result = await self.transcribe(
                        chunk,
                        language=language,
                    )

                    # Filter out repeated text from overlap
                    result.text = self._filter_overlap_text(result.text, previous_text)
                    previous_text = result.text

                    yield result

                except Exception as e:
                    logger.warning(f"Streaming transcription chunk failed: {e}")
                    continue

        # Process remaining buffer
        if len(buffer) > self.config.sample_rate:  # At least 1 second
            try:
                result = await self.transcribe(buffer, language=language)
                result.text = self._filter_overlap_text(result.text, previous_text)
                yield result
            except Exception as e:
                logger.warning(f"Final chunk transcription failed: {e}")

    def _extract_word_timestamps(self, result: Dict) -> List[WordTimestamp]:
        """Extract word-level timestamps from Whisper result."""
        word_timestamps = []

        if "segments" in result:
            for segment in result["segments"]:
                if "words" in segment:
                    for word_info in segment["words"]:
                        word_timestamps.append(WordTimestamp(
                            word=word_info.get("word", "").strip(),
                            start=word_info.get("start", 0.0),
                            end=word_info.get("end", 0.0),
                            confidence=word_info.get("probability", 1.0),
                        ))

        return word_timestamps

    def _calculate_confidence(self, result: Dict) -> float:
        """Calculate overall confidence score."""
        if "segments" in result:
            confidences = []
            for segment in result["segments"]:
                # Use average log probability as confidence proxy
                if "avg_logprob" in segment:
                    # Convert log probability to probability (roughly)
                    confidence = np.exp(segment["avg_logprob"])
                    confidences.append(confidence)

            if confidences:
                return float(np.mean(confidences))

        return 0.9  # Default high confidence

    def _filter_overlap_text(self, current_text: str, previous_text: str) -> str:
        """Filter out repeated text from overlapping audio chunks."""
        if not previous_text:
            return current_text

        # Simple overlap filtering - remove duplicate suffix/prefix
        prev_words = previous_text.split()
        curr_words = current_text.split()

        # Find overlap
        max_overlap = min(len(prev_words), len(curr_words), 10)  # Check up to 10 words

        for overlap_len in range(max_overlap, 0, -1):
            if prev_words[-overlap_len:] == curr_words[:overlap_len]:
                # Remove overlap from current text
                return " ".join(curr_words[overlap_len:])

        return current_text

    def get_word_timestamps(self, result: TranscriptionResult) -> List[WordTimestamp]:
        """
        Get word-level timing information.

        Args:
            result: TranscriptionResult from transcription

        Returns:
            List of WordTimestamp objects
        """
        return result.word_timestamps

    def get_confidence_scores(self, result: TranscriptionResult) -> Dict[str, float]:
        """
        Get per-word confidence scores.

        Args:
            result: TranscriptionResult from transcription

        Returns:
            Dictionary mapping words to confidence scores
        """
        return {
            wt.word: wt.confidence
            for wt in result.word_timestamps
        }

    def set_vocabulary_boost(self, vocabulary: List[str]) -> None:
        """
        Set vocabulary words to boost during recognition.

        Args:
            vocabulary: List of words/phrases to boost
        """
        self.config.vocabulary_boost = vocabulary
        self._build_vocabulary_prompt()
        logger.info(f"Updated vocabulary boost with {len(vocabulary)} terms")

    async def detect_language(self, audio: Union[np.ndarray, str, Path]) -> Tuple[str, float]:
        """
        Detect the language of audio.

        Args:
            audio: Audio data as numpy array or path to audio file

        Returns:
            Tuple of (language_code, confidence)
        """
        if not self._is_initialized:
            await self.initialize()

        try:
            # Load audio if path provided
            if isinstance(audio, (str, Path)):
                audio = await asyncio.to_thread(whisper.load_audio, str(audio))
                audio = whisper.pad_or_trim(audio)

            # Detect language
            mel = log_mel_spectrogram(audio)
            _, probs = self.model.detect_language(mel)

            # Get most likely language
            detected_lang = max(probs, key=probs.get)
            confidence = probs[detected_lang]

            return detected_lang, confidence

        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return "en", 0.5  # Default to English

    async def close(self) -> None:
        """Clean up resources."""
        if self.model is not None:
            del self.model
            self.model = None

            # Clear CUDA cache if using GPU
            if self.config.device == "cuda":
                torch.cuda.empty_cache()

        self._is_initialized = False
        logger.info("SpeechRecognizer closed")


class StreamingTranscriber:
    """
    Simplified streaming transcriber for real-time applications.

    Optimized for low-latency real-time transcription with smaller
    processing windows.
    """

    def __init__(
        self,
        recognizer: SpeechRecognizer,
        chunk_duration: float = 5.0,  # Shorter chunks for lower latency
        overlap_duration: float = 0.5,
    ):
        """
        Initialize streaming transcriber.

        Args:
            recognizer: SpeechRecognizer instance
            chunk_duration: Duration of each chunk in seconds
            overlap_duration: Overlap between chunks in seconds
        """
        self.recognizer = recognizer
        self.chunk_duration = chunk_duration
        self.overlap_duration = overlap_duration
        self.sample_rate = recognizer.config.sample_rate

    async def transcribe_stream(
        self,
        audio_queue: asyncio.Queue,
        stop_event: asyncio.Event,
    ) -> AsyncIterator[TranscriptionResult]:
        """
        Transcribe from an audio queue in real-time.

        Args:
            audio_queue: Queue containing audio chunks
            stop_event: Event to signal stop

        Yields:
            TranscriptionResult for each processed chunk
        """
        chunk_samples = int(self.chunk_duration * self.sample_rate)
        overlap_samples = int(self.overlap_duration * self.sample_rate)

        buffer = np.array([], dtype=np.float32)

        while not stop_event.is_set():
            try:
                # Get audio from queue with timeout
                audio_chunk = await asyncio.wait_for(
                    audio_queue.get(),
                    timeout=0.1
                )

                buffer = np.append(buffer, audio_chunk)

                # Process when buffer is large enough
                if len(buffer) >= chunk_samples:
                    chunk = buffer[:chunk_samples]
                    buffer = buffer[chunk_samples - overlap_samples:]

                    # Transcribe
                    result = await self.recognizer.transcribe(chunk)
                    yield result

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Streaming transcription error: {e}")
                continue
