"""
EduLens Audio Processing Module

Provides wake word detection, audio capture, feature extraction,
speech recognition, and text-to-speech optimized for children (ages 6-12).
"""

from .audio_capture import (
    AudioConfig,
    AudioBuffer,
    MicrophoneStream,
    AsyncMicrophoneStream,
    convert_audio_format,
    normalize_audio,
    apply_pre_emphasis
)

from .feature_extraction import (
    MFCCExtractor,
    VoiceActivityDetector,
    NoiseEstimator,
    FeatureNormalizer,
    extract_delta_features,
    extract_delta_delta_features,
    combine_features
)

from .wake_word_engine import (
    WakeWordDetector,
    AsyncWakeWordDetector,
    AudioStreamProcessor,
    DetectionResult,
    DetectionStats,
    DetectionMode
)

from .speech_recognizer import (
    SpeechRecognizer,
    SpeechConfig,
    TranscriptionResult,
    WordTimestamp,
    StreamingTranscriber,
    TranscriptionMode,
    LanguageHint,
)

from .child_speech_adapter import (
    ChildSpeechAdapter,
    MultiAgeAdapter,
    AgeGroup,
    ChildAcousticProfile,
    ACOUSTIC_PROFILES,
)

from .educational_vocabulary import (
    EducationalVocabulary,
    VocabularyContextManager,
    VocabularyTerm,
    Subject,
    GradeLevel,
    MATH_VOCABULARY,
    SCIENCE_VOCABULARY,
    READING_VOCABULARY,
    GENERAL_VOCABULARY,
)

from .tts_engine import (
    TTSEngine,
    TTSConfig,
    TTSBackend,
    TTSBackendInterface,
    AudioOutput,
    SpeakingRate,
    EmphasisLevel,
)

from .voice_persona import (
    VoicePersona,
    VoiceCharacteristics,
    EmotionalTone,
    EmotionalProfile,
    AgeGroup as VoiceAgeGroup,
    VoiceGender,
    VoicePersonaLibrary,
    PersonaManager,
)

from .pronunciation_rules import (
    MathPronunciationEngine,
    SciencePronunciationEngine,
    PhoneticOverrideEngine,
    PronunciationRulesEngine,
    PronunciationRule,
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
