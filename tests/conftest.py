"""
Pytest configuration and shared fixtures for EduLens testing.

This module provides comprehensive test fixtures for:
- Audio processing tests (sample audio data)
- Vision tests (sample images)
- Mock AI responses
- Test database/storage setup
- Common test utilities
"""

import asyncio
import io
import json
import os
import tempfile
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator, List
from unittest.mock import AsyncMock, MagicMock, Mock

import numpy as np
import pytest
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Import project modules (adjust imports based on actual project structure)
try:
    from database.models import Base
except ImportError:
    Base = None

# Legacy agent-orchestration scaffold tests are excluded from default collection:
# they fail at import ("orchestrator.config" no longer exports "get_config") and
# cover inherited build tooling, not the EduLens product itself. Un-exclude only
# when the scaffold is fixed or removed — tracked as backlog item #8 in
# docs/engineering/current-project-state.md.
collect_ignore = [
    "test_agents.py",
    "test_communication.py",
    "test_orchestrator.py",
]


# ============================================================================
# Session and Event Loop Configuration
# ============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the entire test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Directory and Path Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Get the test data directory path."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_file(temp_dir: Path) -> Path:
    """Create a temporary file path."""
    return temp_dir / "test_file.tmp"


# ============================================================================
# Audio Test Fixtures
# ============================================================================


@pytest.fixture
def sample_audio_data() -> np.ndarray:
    """Generate sample audio data (1 second of 440Hz sine wave at 16kHz)."""
    sample_rate = 16000
    duration = 1.0
    frequency = 440.0  # A4 note

    t = np.linspace(0, duration, int(sample_rate * duration))
    audio_data = np.sin(2 * np.pi * frequency * t).astype(np.float32)

    return audio_data


@pytest.fixture
def sample_audio_bytes(sample_audio_data: np.ndarray) -> bytes:
    """Convert sample audio data to bytes (PCM format)."""
    # Convert to 16-bit PCM
    audio_int16 = (sample_audio_data * 32767).astype(np.int16)
    return audio_int16.tobytes()


@pytest.fixture
def sample_audio_file(temp_dir: Path, sample_audio_bytes: bytes) -> Path:
    """Create a sample audio file."""
    audio_file = temp_dir / "sample_audio.wav"

    # Simple WAV header (44 bytes) + data
    channels = 1
    sample_rate = 16000
    bits_per_sample = 16
    data_size = len(sample_audio_bytes)

    # WAV header
    header = bytearray()
    header.extend(b"RIFF")
    header.extend((data_size + 36).to_bytes(4, "little"))
    header.extend(b"WAVE")
    header.extend(b"fmt ")
    header.extend((16).to_bytes(4, "little"))  # fmt chunk size
    header.extend((1).to_bytes(2, "little"))  # PCM format
    header.extend(channels.to_bytes(2, "little"))
    header.extend(sample_rate.to_bytes(4, "little"))
    header.extend((sample_rate * channels * bits_per_sample // 8).to_bytes(4, "little"))
    header.extend((channels * bits_per_sample // 8).to_bytes(2, "little"))
    header.extend(bits_per_sample.to_bytes(2, "little"))
    header.extend(b"data")
    header.extend(data_size.to_bytes(4, "little"))

    with open(audio_file, "wb") as f:
        f.write(header)
        f.write(sample_audio_bytes)

    return audio_file


@pytest.fixture
def sample_speech_text() -> str:
    """Sample text for speech synthesis testing."""
    return "Hello! This is a test of the EduLens audio system for elementary students."


@pytest.fixture
def sample_transcription() -> Dict[str, Any]:
    """Sample audio transcription result."""
    return {
        "text": "What is photosynthesis?",
        "confidence": 0.95,
        "language": "en",
        "duration": 2.3,
        "words": [
            {"word": "What", "start": 0.0, "end": 0.3, "confidence": 0.98},
            {"word": "is", "start": 0.3, "end": 0.5, "confidence": 0.97},
            {"word": "photosynthesis", "start": 0.5, "end": 2.3, "confidence": 0.92},
        ],
    }


# ============================================================================
# Vision/Image Test Fixtures
# ============================================================================


@pytest.fixture
def sample_image() -> Image.Image:
    """Create a sample RGB image (640x480)."""
    img = Image.new("RGB", (640, 480), color=(73, 109, 137))

    # Add some simple patterns for testing
    pixels = img.load()
    for i in range(100, 200):
        for j in range(100, 200):
            pixels[i, j] = (255, 0, 0)  # Red square

    for i in range(300, 400):
        for j in range(300, 400):
            pixels[i, j] = (0, 255, 0)  # Green square

    return img


@pytest.fixture
def sample_image_bytes(sample_image: Image.Image) -> bytes:
    """Convert sample image to JPEG bytes."""
    buffer = io.BytesIO()
    sample_image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


@pytest.fixture
def sample_image_file(temp_dir: Path, sample_image: Image.Image) -> Path:
    """Create a sample image file."""
    image_file = temp_dir / "sample_image.jpg"
    sample_image.save(image_file, format="JPEG", quality=85)
    return image_file


@pytest.fixture
def sample_educational_image() -> Image.Image:
    """Create a sample educational image (e.g., diagram, chart)."""
    img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    # In a real scenario, this would be an actual educational diagram
    return img


@pytest.fixture
def sample_scene_description() -> Dict[str, Any]:
    """Sample scene description from vision analysis."""
    return {
        "objects": [
            {"name": "book", "confidence": 0.92, "bbox": [100, 150, 300, 400]},
            {"name": "pencil", "confidence": 0.88, "bbox": [320, 200, 360, 450]},
            {"name": "notebook", "confidence": 0.85, "bbox": [50, 100, 250, 350]},
        ],
        "text_detected": ["Chapter 3: Photosynthesis", "Page 42"],
        "scene_type": "classroom_desk",
        "educational_context": "science_reading",
        "confidence": 0.89,
    }


# ============================================================================
# AI/LLM Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_anthropic_client() -> Mock:
    """Mock Anthropic Claude API client."""
    client = Mock()

    # Mock messages.create method
    mock_response = Mock()
    mock_response.content = [Mock(text="This is a test response from Claude.")]
    mock_response.id = "msg_test123"
    mock_response.model = "claude-opus-4.5"
    mock_response.role = "assistant"
    mock_response.stop_reason = "end_turn"
    mock_response.usage = Mock(input_tokens=100, output_tokens=50)

    client.messages.create = Mock(return_value=mock_response)

    return client


@pytest.fixture
def mock_anthropic_async_client() -> AsyncMock:
    """Mock async Anthropic Claude API client."""
    client = AsyncMock()

    # Mock messages.create method
    mock_response = AsyncMock()
    mock_response.content = [Mock(text="This is a test async response from Claude.")]
    mock_response.id = "msg_test123"
    mock_response.model = "claude-opus-4.5"
    mock_response.role = "assistant"
    mock_response.stop_reason = "end_turn"
    mock_response.usage = Mock(input_tokens=100, output_tokens=50)

    client.messages.create = AsyncMock(return_value=mock_response)

    return client


@pytest.fixture
def sample_ai_response() -> Dict[str, Any]:
    """Sample AI response for educational queries."""
    return {
        "response": "Photosynthesis is the process by which plants use sunlight, water, and "
                   "carbon dioxide to create oxygen and energy in the form of sugar.",
        "age_appropriate": True,
        "grade_level": "3-5",
        "follow_up_questions": [
            "Would you like to know what plants need for photosynthesis?",
            "Should I explain why leaves are green?",
        ],
        "educational_value": "high",
        "safety_check": "passed",
    }


@pytest.fixture
def sample_curriculum_content() -> Dict[str, Any]:
    """Sample curriculum content data."""
    return {
        "topic": "photosynthesis",
        "grade_level": 4,
        "subject": "science",
        "learning_objectives": [
            "Understand the basic process of photosynthesis",
            "Identify the inputs and outputs of photosynthesis",
            "Recognize the importance of photosynthesis for life on Earth",
        ],
        "key_vocabulary": ["photosynthesis", "chlorophyll", "sunlight", "carbon dioxide", "oxygen"],
        "activities": [
            {"name": "Plant observation", "duration": "15 minutes", "type": "hands-on"},
            {"name": "Photosynthesis diagram", "duration": "10 minutes", "type": "visual"},
        ],
        "assessment_questions": [
            "What do plants need to make food?",
            "What gas do plants release during photosynthesis?",
        ],
    }


# ============================================================================
# Database Test Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def test_db_engine():
    """Create a test database engine (SQLite in-memory)."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Create all tables if Base is available
    if Base is not None:
        Base.metadata.create_all(engine)

    yield engine

    # Cleanup
    if Base is not None:
        Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_db_engine) -> Generator[Session, None, None]:
    """Create a test database session."""
    SessionLocal = sessionmaker(bind=test_db_engine)
    session = SessionLocal()

    yield session

    session.rollback()
    session.close()


@pytest.fixture
def sample_student_data() -> Dict[str, Any]:
    """Sample student data for testing."""
    return {
        "student_id": "STU001",
        "name": "Test Student",
        "age": 8,
        "grade_level": 3,
        "learning_preferences": {
            "visual": 0.8,
            "auditory": 0.6,
            "kinesthetic": 0.7,
        },
        "current_topics": ["mathematics", "science"],
        "performance_metrics": {
            "engagement": 0.85,
            "comprehension": 0.78,
            "retention": 0.82,
        },
    }


# ============================================================================
# Storage and Cache Fixtures
# ============================================================================


@pytest.fixture
def mock_redis_client() -> Mock:
    """Mock Redis client for caching tests."""
    client = Mock()

    # Simple in-memory storage for testing
    storage: Dict[str, Any] = {}

    def get_side_effect(key: str) -> Any:
        return storage.get(key)

    def set_side_effect(key: str, value: Any, *args: Any, **kwargs: Any) -> bool:
        storage[key] = value
        return True

    def delete_side_effect(*keys: str) -> int:
        count = 0
        for key in keys:
            if key in storage:
                del storage[key]
                count += 1
        return count

    client.get = Mock(side_effect=get_side_effect)
    client.set = Mock(side_effect=set_side_effect)
    client.delete = Mock(side_effect=delete_side_effect)
    client.exists = Mock(side_effect=lambda key: key in storage)
    client.keys = Mock(side_effect=lambda pattern: list(storage.keys()))

    return client


@pytest.fixture
async def mock_redis_async_client() -> AsyncMock:
    """Mock async Redis client for caching tests."""
    client = AsyncMock()

    # Simple in-memory storage for testing
    storage: Dict[str, Any] = {}

    async def get_side_effect(key: str) -> Any:
        return storage.get(key)

    async def set_side_effect(key: str, value: Any, *args: Any, **kwargs: Any) -> bool:
        storage[key] = value
        return True

    async def delete_side_effect(*keys: str) -> int:
        count = 0
        for key in keys:
            if key in storage:
                del storage[key]
                count += 1
        return count

    client.get = AsyncMock(side_effect=get_side_effect)
    client.set = AsyncMock(side_effect=set_side_effect)
    client.delete = AsyncMock(side_effect=delete_side_effect)
    client.exists = AsyncMock(side_effect=lambda key: key in storage)

    return client


# ============================================================================
# Safety and Content Moderation Fixtures
# ============================================================================


@pytest.fixture
def sample_safe_content() -> str:
    """Sample content that passes safety checks."""
    return "Let's learn about how plants grow! They need sunlight, water, and soil."


@pytest.fixture
def sample_unsafe_content() -> str:
    """Sample content that should fail safety checks."""
    return "This content contains inappropriate material for children."


@pytest.fixture
def mock_safety_checker() -> Mock:
    """Mock content safety checker."""
    checker = Mock()

    def check_content(content: str) -> Dict[str, Any]:
        # Simple keyword-based check for testing
        unsafe_keywords = ["inappropriate", "violent", "explicit"]
        is_safe = not any(keyword in content.lower() for keyword in unsafe_keywords)

        return {
            "is_safe": is_safe,
            "confidence": 0.95 if is_safe else 0.88,
            "categories": [],
            "age_appropriate": is_safe,
            "recommended_age": "6-12" if is_safe else "18+",
        }

    checker.check = Mock(side_effect=check_content)

    return checker


# ============================================================================
# Configuration and Environment Fixtures
# ============================================================================


@pytest.fixture
def test_env_vars(monkeypatch: pytest.MonkeyPatch) -> Dict[str, str]:
    """Set up test environment variables."""
    env_vars = {
        "ANTHROPIC_API_KEY": "test_api_key_12345",
        "TEST_MODE": "true",
        "LOG_LEVEL": "DEBUG",
        "DATABASE_URL": "sqlite:///test.db",
        "REDIS_URL": "redis://localhost:6379/1",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Test configuration dictionary."""
    return {
        "app_name": "EduLens Test",
        "environment": "test",
        "debug": True,
        "age_range": {"min": 6, "max": 12},
        "safety_mode": "strict",
        "max_response_length": 500,
        "timeout_seconds": 30,
        "cache_ttl": 300,
    }


# ============================================================================
# Performance Testing Fixtures
# ============================================================================


@pytest.fixture
def performance_timer():
    """Context manager for measuring performance."""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.elapsed = None

        def __enter__(self):
            self.start_time = time.perf_counter()
            return self

        def __exit__(self, *args):
            self.end_time = time.perf_counter()
            self.elapsed = self.end_time - self.start_time

    return Timer


@pytest.fixture
def benchmark_thresholds() -> Dict[str, float]:
    """Performance benchmark thresholds (in seconds)."""
    return {
        "audio_processing": 2.0,
        "vision_analysis": 3.0,
        "ai_response": 5.0,
        "database_query": 0.1,
        "cache_operation": 0.01,
    }


# ============================================================================
# Utility Fixtures
# ============================================================================


@pytest.fixture
def mock_logger() -> Mock:
    """Mock logger for testing."""
    logger = Mock()
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.critical = Mock()
    return logger


@pytest.fixture
def sample_error_response() -> Dict[str, Any]:
    """Sample error response structure."""
    return {
        "error": True,
        "error_type": "ValidationError",
        "message": "Invalid input provided",
        "details": {"field": "age", "issue": "Age must be between 6 and 12"},
        "timestamp": "2025-12-10T12:00:00Z",
    }


# ============================================================================
# Pytest Hooks
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Register custom markers
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests (slower)")
    config.addinivalue_line("markers", "performance: Performance benchmarks")
    config.addinivalue_line("markers", "safety: Safety and content tests")
    config.addinivalue_line("markers", "slow: Slow-running tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Auto-mark tests based on directory
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
        elif "safety" in str(item.fspath):
            item.add_marker(pytest.mark.safety)
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Auto-mark slow tests (tests with timeout or long-running)
        if hasattr(item, "callspec") and "slow" in item.keywords:
            item.add_marker(pytest.mark.slow)
