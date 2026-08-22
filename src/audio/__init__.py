"""
EduLens Audio Processing Module

Provides wake word detection, audio capture, feature extraction,
speech recognition, and text-to-speech optimized for children (ages 6-12).
"""

from .audio_capture import (
    AsyncMicrophoneStream,
    AudioBuffer,
    AudioConfig,
    MicrophoneStream,
    apply_pre_emphasis,
    convert_audio_format,
    normalize_audio,
)
from .child_speech_adapter import (
    ACOUSTIC_PROFILES,
    AgeGroup,
    ChildAcousticProfile,
    ChildSpeechAdapter,
    MultiAgeAdapter,
)
from .educational_vocabulary import (
    GENERAL_VOCABULARY,
    MATH_VOCABULARY,
    READING_VOCABULARY,
    SCIENCE_VOCABULARY,
    EducationalVocabulary,
    GradeLevel,
    Subject,
    VocabularyContextManager,
    VocabularyTerm,
)
from .feature_extraction import (
    FeatureNormalizer,
    MFCCExtractor,
    NoiseEstimator,
    VoiceActivityDetector,
    combine_features,
    extract_delta_delta_features,
    extract_delta_features,
)
from .pronunciation_rules import (
    MathPronunciationEngine,
    PhoneticOverrideEngine,
    PronunciationRule,
    PronunciationRulesEngine,
    SciencePronunciationEngine,
)
from .speech_recognizer import (
    LanguageHint,
    SpeechConfig,
    SpeechRecognizer,
    StreamingTranscriber,
    TranscriptionMode,
    TranscriptionResult,
    WordTimestamp,
)
from .tts_engine import (
    AudioOutput,
    EmphasisLevel,
    SpeakingRate,
    TTSBackend,
    TTSBackendInterface,
    TTSConfig,
    TTSEngine,
)
from .voice_persona import AgeGroup as VoiceAgeGroup
from .voice_persona import (
    EmotionalProfile,
    EmotionalTone,
    PersonaManager,
    VoiceCharacteristics,
    VoiceGender,
    VoicePersona,
    VoicePersonaLibrary,
)
from .wake_word_engine import (
    AsyncWakeWordDetector,
    AudioStreamProcessor,
    DetectionMode,
    DetectionResult,
    DetectionStats,
    WakeWordDetector,
)

__version__ = "1.2.0"

__all__ = [
    # Audio Capture
    "AudioConfig",
    "AudioBuffer",
    "MicrophoneStream",
    "AsyncMicrophoneStream",
    "convert_audio_format",
    "normalize_audio",
    "apply_pre_emphasis",
    # Feature Extraction
    "MFCCExtractor",
    "VoiceActivityDetector",
    "NoiseEstimator",
    "FeatureNormalizer",
    "extract_delta_features",
    "extract_delta_delta_features",
    "combine_features",
    # Wake Word Detection
    "WakeWordDetector",
    "AsyncWakeWordDetector",
    "AudioStreamProcessor",
    "DetectionResult",
    "DetectionStats",
    "DetectionMode",
    # Speech Recognition
    "SpeechRecognizer",
    "SpeechConfig",
    "TranscriptionResult",
    "WordTimestamp",
    "StreamingTranscriber",
    "TranscriptionMode",
    "LanguageHint",
    # Child Speech Adaptation
    "ChildSpeechAdapter",
    "MultiAgeAdapter",
    "AgeGroup",
    "ChildAcousticProfile",
    "ACOUSTIC_PROFILES",
    # Educational Vocabulary
    "EducationalVocabulary",
    "VocabularyContextManager",
    "VocabularyTerm",
    "Subject",
    "GradeLevel",
    "MATH_VOCABULARY",
    "SCIENCE_VOCABULARY",
    "READING_VOCABULARY",
    "GENERAL_VOCABULARY",
    # Text-to-Speech
    "TTSEngine",
    "TTSConfig",
    "TTSBackend",
    "TTSBackendInterface",
    "AudioOutput",
    "SpeakingRate",
    "EmphasisLevel",
    # Voice Personas
    "VoicePersona",
    "VoiceCharacteristics",
    "EmotionalTone",
    "EmotionalProfile",
    "VoiceAgeGroup",
    "VoiceGender",
    "VoicePersonaLibrary",
    "PersonaManager",
    # Pronunciation Rules
    "MathPronunciationEngine",
    "SciencePronunciationEngine",
    "PhoneticOverrideEngine",
    "PronunciationRulesEngine",
    "PronunciationRule",
]
