"""
EduLens Text-to-Speech Engine

Provides child-friendly text-to-speech with educational optimizations,
supporting multiple TTS backends for edge deployment.
"""

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional, Tuple, Union

import numpy as np

try:
    import pyttsx3

    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

try:
    from TTS.api import TTS as CoquiTTS

    COQUI_AVAILABLE = True
except ImportError:
    COQUI_AVAILABLE = False

try:
    import edge_tts

    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False


logger = logging.getLogger(__name__)


class TTSBackend(Enum):
    """Available TTS backend engines"""

    PYTTSX3 = "pyttsx3"  # Offline, cross-platform
    COQUI = "coqui"  # High-quality, offline
    EDGE_TTS = "edge"  # Microsoft Edge TTS (requires internet)
    SYSTEM = "system"  # System default


class EmphasisLevel(Enum):
    """Emphasis levels for SSML"""

    NONE = "none"
    REDUCED = "reduced"
    MODERATE = "moderate"
    STRONG = "strong"


class SpeakingRate(Enum):
    """Preset speaking rates"""

    X_SLOW = 0.5
    SLOW = 0.75
    NORMAL = 1.0
    FAST = 1.25
    X_FAST = 1.5


class SupportedLanguage(Enum):
    """Supported languages for TTS with child-friendly voices."""

    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    CHINESE = "zh"
    HINDI = "hi"
    NEPALESE = "ne"


# Child-friendly Edge TTS voices by language
# Selected for clarity, warmth, and age-appropriate tone
CHILD_FRIENDLY_VOICES: Dict[str, str] = {
    "en": "en-US-AnaNeural",  # Young female, child-friendly (US)
    "es": "es-MX-DaliaNeural",  # Mexican Spanish, friendly tone
    "fr": "fr-FR-EloiseNeural",  # French child-like voice
    "de": "de-DE-GiselaNeural",  # German young voice
    "zh": "zh-CN-XiaoxiaoNeural",  # Chinese child-friendly voice
    "hi": "hi-IN-SwaraNeural",  # Hindi female voice
    "ne": "ne-NP-HemkalaNeural",  # Nepalese female voice
}

# Fallback to English if language not found
DEFAULT_TTS_VOICE = "en-US-AnaNeural"
DEFAULT_TTS_LANGUAGE = "en"


@dataclass
class AudioOutput:
    """Audio output container"""

    audio_data: bytes
    sample_rate: int
    duration_ms: float
    format: str = "wav"

    def to_numpy(self) -> np.ndarray:
        """Convert audio bytes to numpy array"""
        return np.frombuffer(self.audio_data, dtype=np.int16)


@dataclass
class TTSConfig:
    """TTS engine configuration"""

    backend: TTSBackend = TTSBackend.PYTTSX3
    voice_id: Optional[str] = None
    language: str = "en"  # Language code (en, es, fr, de, zh, hi, ne)
    speaking_rate: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0
    sample_rate: int = 22050
    use_ssml: bool = True
    enable_streaming: bool = True
    cache_enabled: bool = True
    cache_dir: Optional[Path] = None

    def __post_init__(self):
        """Auto-select voice based on language if not specified."""
        if self.voice_id is None and self.language:
            self.voice_id = CHILD_FRIENDLY_VOICES.get(self.language, DEFAULT_TTS_VOICE)


class TTSBackendInterface(ABC):
    """Abstract interface for TTS backends"""

    @abstractmethod
    async def synthesize(self, text: str, **kwargs) -> AudioOutput:
        """Synthesize text to audio"""
        pass

    @abstractmethod
    async def synthesize_streaming(self, text: str, **kwargs) -> AsyncGenerator[bytes, None]:
        """Synthesize with streaming output"""
        pass

    @abstractmethod
    def list_voices(self) -> List[Dict[str, str]]:
        """List available voices"""
        pass

    @abstractmethod
    def set_voice(self, voice_id: str) -> None:
        """Set voice by ID"""
        pass


class Pyttsx3Backend(TTSBackendInterface):
    """Pyttsx3 TTS backend (offline, cross-platform)"""

    def __init__(self, config: TTSConfig):
        if not PYTTSX3_AVAILABLE:
            raise ImportError("pyttsx3 not installed. Install with: pip install pyttsx3")

        self.config = config
        self.engine = pyttsx3.init()
        self._configure_engine()

    def _configure_engine(self):
        """Configure pyttsx3 engine"""
        self.engine.setProperty("rate", int(150 * self.config.speaking_rate))
        self.engine.setProperty("volume", self.config.volume)

        if self.config.voice_id:
            self.engine.setProperty("voice", self.config.voice_id)

    async def synthesize(self, text: str, **kwargs) -> AudioOutput:
        """Synthesize text to audio"""
        # Save to temporary file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self._sync_synthesize(text, temp_path))

            # Read audio file
            with open(temp_path, "rb") as f:
                audio_data = f.read()

            return AudioOutput(
                audio_data=audio_data,
                sample_rate=self.config.sample_rate,
                duration_ms=len(audio_data) / self.config.sample_rate * 1000,
                format="wav",
            )
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def _sync_synthesize(self, text: str, output_path: str):
        """Synchronous synthesis"""
        self.engine.save_to_file(text, output_path)
        self.engine.runAndWait()

    async def synthesize_streaming(self, text: str, **kwargs) -> AsyncGenerator[bytes, None]:
        """Pyttsx3 doesn't support streaming, yield full audio"""
        output = await self.synthesize(text, **kwargs)
        yield output.audio_data

    def list_voices(self) -> List[Dict[str, str]]:
        """List available voices"""
        voices = self.engine.getProperty("voices")
        return [
            {
                "id": voice.id,
                "name": voice.name,
                "languages": voice.languages,
                "gender": getattr(voice, "gender", "unknown"),
            }
            for voice in voices
        ]

    def set_voice(self, voice_id: str) -> None:
        """Set voice by ID"""
        self.config.voice_id = voice_id
        self.engine.setProperty("voice", voice_id)


class EdgeTTSBackend(TTSBackendInterface):
    """Microsoft Edge TTS backend (requires internet)"""

    def __init__(self, config: TTSConfig):
        if not EDGE_TTS_AVAILABLE:
            raise ImportError("edge-tts not installed. Install with: pip install edge-tts")

        self.config = config
        self.voice = config.voice_id or "en-US-AriaNeural"

    async def synthesize(self, text: str, **kwargs) -> AudioOutput:
        """Synthesize text to audio"""
        communicate = edge_tts.Communicate(
            text,
            self.voice,
            rate=self._format_rate(self.config.speaking_rate),
            volume=self._format_volume(self.config.volume),
            pitch=self._format_pitch(self.config.pitch),
        )

        # Collect all audio chunks
        audio_chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])

        audio_data = b"".join(audio_chunks)

        return AudioOutput(
            audio_data=audio_data,
            sample_rate=self.config.sample_rate,
            duration_ms=len(audio_data) / self.config.sample_rate * 1000,
            format="mp3",
        )

    async def synthesize_streaming(self, text: str, **kwargs) -> AsyncGenerator[bytes, None]:
        """Synthesize with streaming output"""
        communicate = edge_tts.Communicate(
            text,
            self.voice,
            rate=self._format_rate(self.config.speaking_rate),
            volume=self._format_volume(self.config.volume),
            pitch=self._format_pitch(self.config.pitch),
        )

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]

    def list_voices(self) -> List[Dict[str, str]]:
        """List available voices"""
        # This requires async call, return common child-friendly voices
        return [
            {"id": "en-US-AriaNeural", "name": "Aria (US)", "gender": "Female"},
            {"id": "en-US-GuyNeural", "name": "Guy (US)", "gender": "Male"},
            {"id": "en-US-JennyNeural", "name": "Jenny (US)", "gender": "Female"},
            {"id": "en-GB-SoniaNeural", "name": "Sonia (UK)", "gender": "Female"},
            {"id": "en-GB-RyanNeural", "name": "Ryan (UK)", "gender": "Male"},
        ]

    def set_voice(self, voice_id: str) -> None:
        """Set voice by ID"""
        self.voice = voice_id
        self.config.voice_id = voice_id

    def _format_rate(self, rate: float) -> str:
        """Format rate for Edge TTS"""
        percent = int((rate - 1.0) * 100)
        return f"+{percent}%" if percent >= 0 else f"{percent}%"

    def _format_volume(self, volume: float) -> str:
        """Format volume for Edge TTS"""
        percent = int((volume - 1.0) * 100)
        return f"+{percent}%" if percent >= 0 else f"{percent}%"

    def _format_pitch(self, pitch: float) -> str:
        """Format pitch for Edge TTS"""
        hz = int((pitch - 1.0) * 10)
        return f"+{hz}Hz" if hz >= 0 else f"{hz}Hz"


class CoquiTTSBackend(TTSBackendInterface):
    """Coqui TTS backend (high-quality, offline)"""

    def __init__(self, config: TTSConfig):
        if not COQUI_AVAILABLE:
            raise ImportError("Coqui TTS not installed. Install with: pip install TTS")

        self.config = config
        self.tts = CoquiTTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")

    async def synthesize(self, text: str, **kwargs) -> AudioOutput:
        """Synthesize text to audio"""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: self.tts.tts_to_file(text=text, file_path=temp_path)
            )

            with open(temp_path, "rb") as f:
                audio_data = f.read()

            return AudioOutput(
                audio_data=audio_data,
                sample_rate=self.config.sample_rate,
                duration_ms=len(audio_data) / self.config.sample_rate * 1000,
                format="wav",
            )
        finally:
            Path(temp_path).unlink(missing_ok=True)

    async def synthesize_streaming(self, text: str, **kwargs) -> AsyncGenerator[bytes, None]:
        """Coqui doesn't support streaming, yield full audio"""
        output = await self.synthesize(text, **kwargs)
        yield output.audio_data

    def list_voices(self) -> List[Dict[str, str]]:
        """List available voices"""
        return [{"id": "ljspeech", "name": "LJSpeech", "gender": "Female"}]

    def set_voice(self, voice_id: str) -> None:
        """Set voice by ID"""
        self.config.voice_id = voice_id


class TTSEngine:
    """
    Main Text-to-Speech engine for EduLens

    Provides child-friendly TTS with:
    - Multiple backend support (offline/online)
    - SSML support for fine control
    - Educational optimizations (math, science terms)
    - Variable speed and emphasis
    - Streaming support
    """

    def __init__(
        self, config: Optional[TTSConfig] = None, voice_persona: Optional["VoicePersona"] = None
    ):
        """
        Initialize TTS engine

        Args:
            config: TTS configuration
            voice_persona: Voice persona settings
        """
        self.config = config or TTSConfig()
        self.voice_persona = voice_persona
        self.backend = self._initialize_backend()
        self.cache: Dict[str, AudioOutput] = {}

        logger.info(f"TTS Engine initialized with backend: {self.config.backend.value}")

    def _initialize_backend(self) -> TTSBackendInterface:
        """Initialize TTS backend"""
        if self.config.backend == TTSBackend.PYTTSX3:
            return Pyttsx3Backend(self.config)
        elif self.config.backend == TTSBackend.EDGE_TTS:
            return EdgeTTSBackend(self.config)
        elif self.config.backend == TTSBackend.COQUI:
            return CoquiTTSBackend(self.config)
        else:
            # Fallback to pyttsx3
            logger.warning(f"Unknown backend {self.config.backend}, using pyttsx3")
            return Pyttsx3Backend(self.config)

    def set_language(self, language: str) -> None:
        """
        Set TTS language and automatically select appropriate child-friendly voice.

        Args:
            language: Language code (en, es, fr, de, zh, hi, ne)
        """
        self.config.language = language
        self.config.voice_id = CHILD_FRIENDLY_VOICES.get(language, DEFAULT_TTS_VOICE)

        # Update backend if it supports language change
        if hasattr(self.backend, "set_language"):
            self.backend.set_language(language)

        # Clear cache when language changes
        self.cache.clear()

        logger.info(f"TTS language set to {language}, voice: {self.config.voice_id}")

    @property
    def language(self) -> str:
        """Get current TTS language."""
        return self.config.language

    async def synthesize(
        self, text: str, use_cache: bool = True, preprocess: bool = True
    ) -> AudioOutput:
        """
        Convert text to speech

        Args:
            text: Text to synthesize
            use_cache: Use cached audio if available
            preprocess: Apply text preprocessing

        Returns:
            AudioOutput with synthesized speech
        """
        # Check cache
        cache_key = self._get_cache_key(text)
        if use_cache and cache_key in self.cache:
            logger.debug(f"Cache hit for: {text[:50]}...")
            return self.cache[cache_key]

        # Preprocess text
        if preprocess:
            text = self._preprocess_text(text)

        # Apply SSML if enabled
        if self.config.use_ssml and self.voice_persona:
            text = self._apply_ssml(text)

        # Synthesize
        output = await self.backend.synthesize(text)

        # Cache result
        if use_cache and self.config.cache_enabled:
            self.cache[cache_key] = output

        return output

    async def synthesize_streaming(
        self, text: str, preprocess: bool = True
    ) -> AsyncGenerator[bytes, None]:
        """
        Synthesize with streaming output

        Args:
            text: Text to synthesize
            preprocess: Apply text preprocessing

        Yields:
            Audio data chunks
        """
        if preprocess:
            text = self._preprocess_text(text)

        if self.config.use_ssml and self.voice_persona:
            text = self._apply_ssml(text)

        async for chunk in self.backend.synthesize_streaming(text):
            yield chunk

    def set_voice(self, voice_id: str) -> None:
        """
        Select voice persona

        Args:
            voice_id: Voice identifier
        """
        self.backend.set_voice(voice_id)
        logger.info(f"Voice set to: {voice_id}")

    def set_speed(self, rate: Union[float, SpeakingRate]) -> None:
        """
        Adjust speaking rate

        Args:
            rate: Speaking rate (0.5 to 2.0) or SpeakingRate enum
        """
        if isinstance(rate, SpeakingRate):
            rate = rate.value

        self.config.speaking_rate = max(0.5, min(2.0, rate))
        logger.info(f"Speaking rate set to: {self.config.speaking_rate}")

    def set_emphasis(self, level: EmphasisLevel) -> None:
        """
        Set default emphasis level

        Args:
            level: Emphasis level
        """
        if not hasattr(self, "_emphasis_level"):
            self._emphasis_level = level
        else:
            self._emphasis_level = level

        logger.info(f"Emphasis level set to: {level.value}")

    async def speak_math(self, expression: str, explain: bool = True) -> AudioOutput:
        """
        Specialized math expression reading

        Args:
            expression: Math expression (e.g., "2 + 3 = 5")
            explain: Add explanatory pauses

        Returns:
            AudioOutput with spoken math
        """
        from .pronunciation_rules import MathPronunciationEngine

        math_engine = MathPronunciationEngine()
        spoken_text = math_engine.convert_expression(expression)

        if explain:
            spoken_text = self._add_pedagogical_pauses(spoken_text)

        return await self.synthesize(spoken_text, preprocess=False)

    async def speak_with_pauses(
        self, text: str, pause_points: Optional[List[int]] = None, pause_duration_ms: int = 500
    ) -> AudioOutput:
        """
        Add pedagogical pauses to speech

        Args:
            text: Text to speak
            pause_points: Character positions for pauses
            pause_duration_ms: Pause duration in milliseconds

        Returns:
            AudioOutput with pauses
        """
        if pause_points:
            # Insert SSML break tags
            ssml_text = self._insert_pauses(text, pause_points, pause_duration_ms)
        else:
            # Auto-detect pause points
            ssml_text = self._add_pedagogical_pauses(text)

        return await self.synthesize(ssml_text, preprocess=False)

    def list_voices(self) -> List[Dict[str, str]]:
        """
        List available voices

        Returns:
            List of voice dictionaries with id, name, etc.
        """
        return self.backend.list_voices()

    def clear_cache(self) -> None:
        """Clear audio cache"""
        self.cache.clear()
        logger.info("TTS cache cleared")

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text before synthesis"""
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Expand common abbreviations
        text = text.replace("e.g.", "for example")
        text = text.replace("i.e.", "that is")
        text = text.replace("etc.", "et cetera")

        # Handle numbers
        text = self._expand_numbers(text)

        return text

    def _expand_numbers(self, text: str) -> str:
        """Expand numbers to words for better pronunciation"""
        # Simple number expansion (can be enhanced)
        number_words = {
            "0": "zero",
            "1": "one",
            "2": "two",
            "3": "three",
            "4": "four",
            "5": "five",
            "6": "six",
            "7": "seven",
            "8": "eight",
            "9": "nine",
            "10": "ten",
        }

        for num, word in number_words.items():
            text = re.sub(r"\b" + num + r"\b", word, text)

        return text

    def _apply_ssml(self, text: str) -> str:
        """Apply SSML markup based on voice persona"""
        if not self.voice_persona:
            return text

        # Build SSML
        ssml = f"<speak>"
        ssml += f'<prosody rate="{int(self.config.speaking_rate * 100)}%" '
        ssml += f'pitch="{self._format_pitch()}" '
        ssml += f'volume="{self._format_volume()}">'
        ssml += text
        ssml += "</prosody>"
        ssml += "</speak>"

        return ssml

    def _format_pitch(self) -> str:
        """Format pitch for SSML"""
        if self.config.pitch > 1.0:
            return f"+{int((self.config.pitch - 1.0) * 50)}%"
        elif self.config.pitch < 1.0:
            return f"-{int((1.0 - self.config.pitch) * 50)}%"
        return "0%"

    def _format_volume(self) -> str:
        """Format volume for SSML"""
        levels = ["silent", "x-soft", "soft", "medium", "loud", "x-loud"]
        index = int(self.config.volume * 3)
        return levels[min(index, len(levels) - 1)]

    def _add_pedagogical_pauses(self, text: str) -> str:
        """Add pauses at key points for learning"""
        # Add pauses after:
        # - Sentences
        text = re.sub(r"([.!?])\s+", r'\1<break time="500ms"/> ', text)
        # - Key phrases
        text = re.sub(r"(therefore|because|however)\s+", r'\1<break time="300ms"/> ', text)
        # - Commas
        text = re.sub(r",\s+", r',<break time="200ms"/> ', text)

        return text

    def _insert_pauses(self, text: str, pause_points: List[int], duration_ms: int) -> str:
        """Insert pauses at specific points"""
        result = []
        last_pos = 0

        for pos in sorted(pause_points):
            result.append(text[last_pos:pos])
            result.append(f'<break time="{duration_ms}ms"/>')
            last_pos = pos

        result.append(text[last_pos:])
        return "".join(result)

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return f"{text}_{self.config.speaking_rate}_{self.config.pitch}"
