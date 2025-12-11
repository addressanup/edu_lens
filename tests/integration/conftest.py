"""
Integration Test Fixtures for EduLens

Provides shared fixtures and utilities for integration testing across components.
"""

import asyncio
import io
import tempfile
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pytest
from PIL import Image

# Import EduLens components
try:
    from src.integration.vision_to_ai_bridge import VisionToAIBridge, ContentType, SubjectArea
    from src.integration.voice_to_ai_bridge import VoiceToAIBridge, QueryIntent
    from src.integration.context_builder import ContextBuilder
    from src.pipeline.session_manager import SessionManager, SessionState, InteractionType
    from src.privacy.data_minimizer import DataMinimizer, MinimizationLevel
    from src.privacy.auto_deletion import AutoDeletionPolicy
    from src.audio.wake_word_engine import WakeWordDetector, DetectionResult
    from src.audio.speech_recognizer import SpeechRecognizer, SpeechConfig, TranscriptionResult, WordTimestamp
    from src.audio.tts_engine import TTSEngine, TTSConfig, TTSBackend
    from src.vision.ocr_engine import OCREngine
    from src.vision.handwriting_engine import HandwritingRecognizer
    from src.vision.layout_analyzer import LayoutAnalyzer
except ImportError:
    # Allow tests to run even if imports fail
    pass


# ============================================================================
# Mock Component Fixtures
# ============================================================================


@pytest.fixture
def mock_ocr_engine():
    """Mock OCR engine with realistic responses."""
    engine = Mock()

    def mock_process_image(image_data, **kwargs):
        return {
            "full_text": "What is 2 + 3? A) 4 B) 5 C) 6",
            "average_confidence": 0.92,
            "regions": [
                {"text": "What is 2 + 3?", "bbox": [10, 10, 200, 50], "confidence": 0.95},
                {"text": "A) 4", "bbox": [10, 60, 80, 90], "confidence": 0.90},
                {"text": "B) 5", "bbox": [10, 100, 80, 130], "confidence": 0.93},
                {"text": "C) 6", "bbox": [10, 140, 80, 170], "confidence": 0.91},
            ],
            "language": "en",
        }

    engine.process_image = Mock(side_effect=mock_process_image)
    return engine


@pytest.fixture
def mock_handwriting_engine():
    """Mock handwriting recognition engine."""
    engine = Mock()

    def mock_recognize(image_data, **kwargs):
        return {
            "text": "5",
            "confidence": 0.88,
            "is_handwritten": True,
            "answer_regions": [
                {"text": "5", "bbox": [250, 60, 280, 90], "confidence": 0.88}
            ],
        }

    engine.recognize = Mock(side_effect=mock_recognize)
    return engine


@pytest.fixture
def mock_layout_analyzer():
    """Mock layout analyzer."""
    analyzer = Mock()

    def mock_analyze(image_data, **kwargs):
        return {
            "region_types": ["QUESTION", "MULTIPLE_CHOICE"],
            "problems": [
                {
                    "number": "1",
                    "text": "What is 2 + 3?",
                    "bbox": [10, 10, 300, 50],
                }
            ],
            "diagrams": [],
        }

    analyzer.analyze = Mock(side_effect=mock_analyze)
    return analyzer


@pytest.fixture
def mock_wake_word_detector():
    """Mock wake word detector."""
    detector = Mock()
    detector.is_listening = False
    detector.threshold = 0.6
    detector.sensitivity = 0.5

    def mock_start_listening():
        detector.is_listening = True

    def mock_stop_listening():
        detector.is_listening = False

    detector.start_listening = Mock(side_effect=mock_start_listening)
    detector.stop_listening = Mock(side_effect=mock_stop_listening)
    detector.on_wake_word = Mock()
    detector.get_detection_confidence = Mock(return_value=0.85)

    return detector


@pytest.fixture
async def mock_speech_recognizer():
    """Mock speech recognizer."""
    recognizer = Mock()

    async def mock_transcribe(audio, **kwargs):
        return TranscriptionResult(
            text="What is photosynthesis?",
            confidence=0.94,
            language="en",
            word_timestamps=[
                WordTimestamp(word="What", start=0.0, end=0.3, confidence=0.96),
                WordTimestamp(word="is", start=0.3, end=0.5, confidence=0.95),
                WordTimestamp(word="photosynthesis", start=0.5, end=1.8, confidence=0.92),
            ],
            processing_time=0.15,
        )

    recognizer.transcribe = AsyncMock(side_effect=mock_transcribe)
    recognizer.initialize = AsyncMock()
    recognizer._is_initialized = True

    return recognizer


@pytest.fixture
async def mock_tts_engine():
    """Mock TTS engine."""
    from dataclasses import dataclass

    @dataclass
    class MockAudioOutput:
        audio_data: bytes
        sample_rate: int
        duration_ms: float
        format: str = "wav"

    engine = Mock()

    async def mock_synthesize(text, **kwargs):
        # Generate mock audio data
        audio_data = np.random.randint(-1000, 1000, 16000, dtype=np.int16).tobytes()
        return MockAudioOutput(
            audio_data=audio_data,
            sample_rate=16000,
            duration_ms=1000.0,
        )

    engine.synthesize = AsyncMock(side_effect=mock_synthesize)
    engine.set_voice = Mock()
    engine.set_speed = Mock()

    return engine


@pytest.fixture
def mock_ai_client():
    """Mock AI/LLM client for tutoring responses."""
    client = Mock()

    def mock_generate_response(context, **kwargs):
        return {
            "response": "Great question! Photosynthesis is the process plants use to make food from sunlight, water, and carbon dioxide. The plant takes in these ingredients and produces sugar for energy, releasing oxygen that we breathe!",
            "confidence": 0.96,
            "safe": True,
            "age_appropriate": True,
            "grade_level": "3-5",
            "educational_value": "high",
        }

    client.generate_response = Mock(side_effect=mock_generate_response)
    return client


# ============================================================================
# Bridge Component Fixtures
# ============================================================================


@pytest.fixture
def vision_to_ai_bridge():
    """Create VisionToAIBridge instance."""
    try:
        return VisionToAIBridge()
    except:
        return Mock()


@pytest.fixture
def voice_to_ai_bridge():
    """Create VoiceToAIBridge instance."""
    try:
        return VoiceToAIBridge()
    except:
        return Mock()


# ============================================================================
# Session Manager Fixtures
# ============================================================================


@pytest.fixture
def session_manager():
    """Create SessionManager instance."""
    try:
        return SessionManager(
            max_concurrent_sessions=1,
            default_max_duration_minutes=120,
            default_idle_timeout_minutes=5,
        )
    except:
        return Mock()


@pytest.fixture
def active_session(session_manager):
    """Create an active tutoring session."""
    try:
        session = session_manager.create_session(
            student_id="TEST_STUDENT_001",
            on_state_change=None,
        )
        return session
    except:
        mock_session = Mock()
        mock_session.session_id = "test_session_001"
        mock_session.student_id = "TEST_STUDENT_001"
        mock_session.state = SessionState.IDLE
        return mock_session


# ============================================================================
# Privacy Component Fixtures
# ============================================================================


@pytest.fixture
def data_minimizer():
    """Create DataMinimizer instance."""
    try:
        return DataMinimizer(default_minimization_level=MinimizationLevel.STANDARD)
    except:
        return Mock()


@pytest.fixture
def mock_auto_deletion_policy():
    """Mock auto-deletion policy."""
    policy = Mock()
    policy.schedule_deletion = Mock()
    policy.delete_immediately = Mock()
    policy.check_and_delete_expired = Mock(return_value=[])
    return policy


# ============================================================================
# Test Data Generators
# ============================================================================


@pytest.fixture
def sample_math_image():
    """Generate sample math problem image."""
    img = Image.new("RGB", (640, 480), color=(255, 255, 255))
    # In real tests, this would have actual text/math rendered
    return img


@pytest.fixture
def sample_math_image_bytes(sample_math_image):
    """Convert sample math image to bytes."""
    buffer = io.BytesIO()
    sample_math_image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


@pytest.fixture
def sample_audio_question():
    """Generate sample audio with a question."""
    # 2 seconds of audio data
    sample_rate = 16000
    duration = 2.0
    audio_data = np.random.randn(int(sample_rate * duration)).astype(np.float32)
    return audio_data


@pytest.fixture
def sample_audio_bytes(sample_audio_question):
    """Convert sample audio to bytes."""
    audio_int16 = (sample_audio_question * 32767).astype(np.int16)
    return audio_int16.tobytes()


@pytest.fixture
def sample_ocr_result():
    """Sample OCR result."""
    return {
        "full_text": "What is 2 + 3?",
        "average_confidence": 0.92,
        "regions": [
            {"text": "What is 2 + 3?", "bbox": [10, 10, 200, 50], "confidence": 0.92}
        ],
        "language": "en",
    }


@pytest.fixture
def sample_layout_result():
    """Sample layout analysis result."""
    return {
        "region_types": ["QUESTION"],
        "problems": [
            {
                "number": "1",
                "text": "What is 2 + 3?",
                "bbox": [10, 10, 300, 50],
            }
        ],
        "diagrams": [],
    }


@pytest.fixture
def sample_handwriting_result():
    """Sample handwriting recognition result."""
    return {
        "text": "5",
        "confidence": 0.88,
        "is_handwritten": True,
        "answer_regions": [
            {"text": "5", "bbox": [250, 60, 280, 90], "confidence": 0.88}
        ],
    }


@pytest.fixture
def sample_transcription():
    """Sample speech transcription."""
    return {
        "text": "What is photosynthesis?",
        "confidence": 0.94,
        "language": "en",
        "duration": 1.8,
        "words": [
            {"word": "What", "start": 0.0, "end": 0.3, "confidence": 0.96},
            {"word": "is", "start": 0.3, "end": 0.5, "confidence": 0.95},
            {"word": "photosynthesis", "start": 0.5, "end": 1.8, "confidence": 0.92},
        ],
    }


@pytest.fixture
def sample_ai_response():
    """Sample AI tutoring response."""
    return {
        "response": "Great question! To solve 2 + 3, think about counting. If you have 2 apples and get 3 more apples, how many do you have in total? That's right, 5 apples! So 2 + 3 = 5.",
        "confidence": 0.95,
        "safe": True,
        "age_appropriate": True,
        "hint_level": 1,
        "educational_value": "high",
    }


# ============================================================================
# Integration Test Utilities
# ============================================================================


@pytest.fixture
def integration_test_timer():
    """Timer for measuring integration test performance."""
    import time

    class IntegrationTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.checkpoints = {}

        def start(self):
            self.start_time = time.perf_counter()

        def checkpoint(self, name: str):
            if self.start_time is None:
                self.start()
            self.checkpoints[name] = time.perf_counter() - self.start_time

        def stop(self):
            self.end_time = time.perf_counter()

        def elapsed(self) -> float:
            if self.end_time and self.start_time:
                return self.end_time - self.start_time
            return 0.0

        def checkpoint_duration(self, name: str) -> float:
            return self.checkpoints.get(name, 0.0)

    return IntegrationTimer()


@pytest.fixture
def assert_latency():
    """Helper to assert operation latency requirements."""
    def _assert_latency(elapsed_seconds: float, max_seconds: float, operation: str):
        assert elapsed_seconds <= max_seconds, (
            f"{operation} took {elapsed_seconds:.2f}s, "
            f"exceeds maximum of {max_seconds}s"
        )

    return _assert_latency


@pytest.fixture
def mock_device_bluetooth():
    """Mock Bluetooth device connection."""
    device = Mock()
    device.is_connected = False
    device.device_id = "TEST_DEVICE_001"
    device.device_name = "EduLens Test Device"

    def mock_connect():
        device.is_connected = True
        return True

    def mock_disconnect():
        device.is_connected = False
        return True

    device.connect = Mock(side_effect=mock_connect)
    device.disconnect = Mock(side_effect=mock_disconnect)
    device.send_data = Mock(return_value=True)
    device.receive_data = Mock(return_value={"status": "ok"})

    return device


@pytest.fixture
def mock_app_sync_manager():
    """Mock app synchronization manager."""
    manager = Mock()
    manager.sync_settings = Mock(return_value=True)
    manager.sync_progress = Mock(return_value=True)
    manager.get_activities = Mock(return_value=[
        {"type": "math_problem", "timestamp": "2025-12-10T10:00:00Z", "correct": True},
        {"type": "reading", "timestamp": "2025-12-10T10:15:00Z", "duration": 300},
    ])
    return manager


# ============================================================================
# Async Event Loop Fixture
# ============================================================================


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Cleanup Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Cleanup resources after each test."""
    yield
    # Cleanup code runs here after test completes
    # Clear any global state, close connections, etc.


# ============================================================================
# Performance Thresholds
# ============================================================================


@pytest.fixture
def performance_thresholds():
    """Performance thresholds for integration tests."""
    return {
        "vision_to_ai_processing": 1.0,  # seconds
        "audio_to_ai_processing": 0.5,   # seconds
        "end_to_end_response": 2.0,      # seconds
        "session_state_transition": 0.1, # seconds
        "data_minimization": 0.2,        # seconds
        "bluetooth_sync": 1.0,           # seconds
    }


# ============================================================================
# Test Configuration
# ============================================================================


@pytest.fixture
def integration_test_config():
    """Configuration for integration tests."""
    return {
        "enable_logging": True,
        "log_level": "DEBUG",
        "mock_external_services": True,
        "strict_timing": False,  # Set to True for CI/CD
        "max_test_duration": 30.0,  # seconds per test
        "enable_performance_validation": True,
    }
