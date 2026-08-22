"""
EduLens Core Interfaces

This module defines all core interfaces, protocols, and abstract base classes
for the EduLens system. These interfaces enable loose coupling, testability,
and modularity across the architecture.

Author: Integration Agent (INT-001)
Version: 1.0.0
Date: 2025-12-10
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Optional,
    Protocol,
    TypeVar,
    runtime_checkable,
)

import numpy as np
import numpy.typing as npt

# ============================================================================
# Core Data Types
# ============================================================================


@dataclass(frozen=True)
class Timestamp:
    """Immutable timestamp with nanosecond precision"""

    value: float  # Unix epoch time with fractional seconds

    @classmethod
    def now(cls) -> "Timestamp":
        """Create timestamp for current time"""
        return cls(value=datetime.now().timestamp())

    def to_datetime(self) -> datetime:
        """Convert to Python datetime"""
        return datetime.fromtimestamp(self.value)


# ============================================================================
# Vision Pipeline Interfaces
# ============================================================================


@dataclass
class Frame:
    """Represents a single camera frame with metadata"""

    data: npt.NDArray[np.uint8]  # Image data (H, W, C)
    timestamp: Timestamp
    frame_id: int
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def shape(self) -> tuple[int, int, int]:
        """Get frame dimensions (height, width, channels)"""
        return self.data.shape

    @property
    def width(self) -> int:
        """Get frame width"""
        return self.data.shape[1]

    @property
    def height(self) -> int:
        """Get frame height"""
        return self.data.shape[0]


@dataclass
class BoundingBox:
    """Normalized bounding box coordinates (0-1 range)"""

    x1: float  # Top-left x
    y1: float  # Top-left y
    x2: float  # Bottom-right x
    y2: float  # Bottom-right y

    def __post_init__(self) -> None:
        """Validate bounding box coordinates"""
        if not (0 <= self.x1 <= 1 and 0 <= self.x2 <= 1):
            raise ValueError(f"Invalid x coordinates: x1={self.x1}, x2={self.x2}")
        if not (0 <= self.y1 <= 1 and 0 <= self.y2 <= 1):
            raise ValueError(f"Invalid y coordinates: y1={self.y1}, y2={self.y2}")
        if self.x1 >= self.x2 or self.y1 >= self.y2:
            raise ValueError("Invalid bounding box: x1 must be < x2, y1 must be < y2")

    @property
    def width(self) -> float:
        """Get normalized width"""
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        """Get normalized height"""
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        """Get normalized area"""
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        """Get center coordinates (x, y)"""
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)


@dataclass
class Detection:
    """Object detection result"""

    class_name: str
    confidence: float
    bbox: BoundingBox
    class_id: int
    features: Optional[npt.NDArray[np.float32]] = None  # Embedding vector
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TextRegion:
    """Detected text region with OCR results"""

    text: str
    bbox: BoundingBox
    confidence: float
    language: str
    metadata: dict[str, Any] = field(default_factory=dict)


class SceneType(Enum):
    """Types of scenes that can be detected"""

    CLASSROOM = "classroom"
    LABORATORY = "laboratory"
    OUTDOOR = "outdoor"
    LIBRARY = "library"
    LECTURE_HALL = "lecture_hall"
    OFFICE = "office"
    HOME = "home"
    UNKNOWN = "unknown"


@dataclass
class SceneAnalysis:
    """Comprehensive scene understanding results"""

    scene_type: SceneType
    confidence: float
    objects: list[Detection]
    text_regions: list[TextRegion]
    features: npt.NDArray[np.float32]  # Scene embedding
    description: str
    timestamp: Timestamp


class ColorSpace(Enum):
    """Supported color spaces for image processing"""

    RGB = "rgb"
    BGR = "bgr"
    GRAYSCALE = "grayscale"
    HSV = "hsv"
    LAB = "lab"


@dataclass
class PreprocessingConfig:
    """Configuration for image preprocessing"""

    target_size: Optional[tuple[int, int]] = None  # (width, height)
    color_space: ColorSpace = ColorSpace.RGB
    normalize: bool = True
    mean: tuple[float, float, float] = (0.485, 0.456, 0.406)
    std: tuple[float, float, float] = (0.229, 0.224, 0.225)
    resize_mode: str = "bilinear"  # bilinear, bicubic, nearest


class IFrameCapture(ABC):
    """Interface for camera frame capture"""

    @abstractmethod
    async def start_capture(
        self, fps: int = 30, resolution: tuple[int, int] = (1920, 1080)
    ) -> None:
        """
        Start capturing frames from camera

        Args:
            fps: Target frames per second
            resolution: Capture resolution (width, height)

        Raises:
            CameraError: If camera initialization fails
        """
        pass

    @abstractmethod
    async def stop_capture(self) -> None:
        """Stop frame capture and release camera resources"""
        pass

    @abstractmethod
    async def get_frame_stream(self) -> AsyncIterator[Frame]:
        """
        Get async iterator of captured frames

        Yields:
            Frame: Next captured frame

        Raises:
            CameraError: If capture stream fails
        """
        pass

    @abstractmethod
    async def get_latest_frame(self) -> Optional[Frame]:
        """
        Get most recent frame without blocking

        Returns:
            Latest frame or None if unavailable
        """
        pass

    @abstractmethod
    def is_capturing(self) -> bool:
        """Check if camera is currently capturing"""
        pass


class IImagePreprocessor(ABC):
    """Interface for image preprocessing operations"""

    @abstractmethod
    async def preprocess(
        self, frame: Frame, config: PreprocessingConfig
    ) -> npt.NDArray[np.float32]:
        """
        Preprocess frame for model inference

        Args:
            frame: Input frame
            config: Preprocessing configuration

        Returns:
            Preprocessed image tensor
        """
        pass

    @abstractmethod
    async def batch_preprocess(
        self, frames: list[Frame], config: PreprocessingConfig
    ) -> npt.NDArray[np.float32]:
        """
        Preprocess multiple frames in batch

        Args:
            frames: List of input frames
            config: Preprocessing configuration

        Returns:
            Batched preprocessed tensors (N, H, W, C)
        """
        pass


class IObjectDetector(ABC):
    """Interface for object detection"""

    @abstractmethod
    async def detect(
        self,
        image: npt.NDArray[np.uint8],
        confidence_threshold: float = 0.5,
        nms_threshold: float = 0.4,
    ) -> list[Detection]:
        """
        Detect objects in image

        Args:
            image: Input image
            confidence_threshold: Minimum confidence for detection
            nms_threshold: Non-maximum suppression threshold

        Returns:
            List of detected objects
        """
        pass

    @abstractmethod
    async def get_supported_classes(self) -> list[str]:
        """Get list of object classes the detector supports"""
        pass


class IOCREngine(ABC):
    """Interface for optical character recognition"""

    @abstractmethod
    async def extract_text(
        self, image: npt.NDArray[np.uint8], languages: Optional[list[str]] = None
    ) -> list[TextRegion]:
        """
        Extract text from image

        Args:
            image: Input image
            languages: Expected languages (e.g., ['en', 'es'])

        Returns:
            List of detected text regions
        """
        pass

    @abstractmethod
    async def extract_text_structured(self, image: npt.NDArray[np.uint8]) -> dict[str, Any]:
        """
        Extract structured text (tables, forms, etc.)

        Args:
            image: Input image

        Returns:
            Structured text data with layout information
        """
        pass


class ISceneAnalyzer(ABC):
    """Interface for scene understanding"""

    @abstractmethod
    async def analyze_scene(
        self, frame: Frame, include_objects: bool = True, include_text: bool = True
    ) -> SceneAnalysis:
        """
        Perform comprehensive scene analysis

        Args:
            frame: Input frame
            include_objects: Whether to detect objects
            include_text: Whether to extract text

        Returns:
            Complete scene analysis
        """
        pass


# ============================================================================
# Audio Pipeline Interfaces
# ============================================================================


@dataclass
class AudioChunk:
    """Audio data chunk with metadata"""

    data: npt.NDArray[np.float32]  # Audio samples (channels, samples)
    timestamp: Timestamp
    sample_rate: int
    channels: int
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds"""
        return self.data.shape[1] / self.sample_rate


@dataclass
class TranscriptionSegment:
    """Speech-to-text transcription result"""

    text: str
    start_time: float
    end_time: float
    confidence: float
    language: str
    speaker_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        """Get segment duration in seconds"""
        return self.end_time - self.start_time


@dataclass
class Speaker:
    """Speaker identification result"""

    speaker_id: str
    name: Optional[str] = None
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class IAudioCapture(ABC):
    """Interface for audio capture"""

    @abstractmethod
    async def start_capture(
        self, sample_rate: int = 16000, channels: int = 1, chunk_duration_ms: int = 100
    ) -> None:
        """
        Start capturing audio

        Args:
            sample_rate: Audio sample rate in Hz
            channels: Number of audio channels
            chunk_duration_ms: Duration of each audio chunk in milliseconds

        Raises:
            AudioError: If audio initialization fails
        """
        pass

    @abstractmethod
    async def stop_capture(self) -> None:
        """Stop audio capture and release resources"""
        pass

    @abstractmethod
    async def get_audio_stream(self) -> AsyncIterator[AudioChunk]:
        """
        Get stream of audio chunks

        Yields:
            AudioChunk: Next audio chunk
        """
        pass


class IAudioPreprocessor(ABC):
    """Interface for audio preprocessing"""

    @abstractmethod
    async def reduce_noise(self, audio: AudioChunk) -> AudioChunk:
        """Apply noise reduction to audio"""
        pass

    @abstractmethod
    async def normalize_volume(self, audio: AudioChunk) -> AudioChunk:
        """Normalize audio volume"""
        pass

    @abstractmethod
    async def detect_voice_activity(self, audio: AudioChunk) -> bool:
        """
        Detect if audio contains speech

        Returns:
            True if voice activity detected
        """
        pass


class ISpeechRecognizer(ABC):
    """Interface for speech recognition"""

    @abstractmethod
    async def transcribe(
        self, audio: AudioChunk, language: Optional[str] = None
    ) -> TranscriptionSegment:
        """
        Transcribe audio to text

        Args:
            audio: Audio chunk to transcribe
            language: Expected language code (e.g., 'en', 'es')

        Returns:
            Transcription result
        """
        pass

    @abstractmethod
    async def transcribe_stream(
        self, audio_stream: AsyncIterator[AudioChunk]
    ) -> AsyncIterator[TranscriptionSegment]:
        """
        Transcribe streaming audio in real-time

        Args:
            audio_stream: Stream of audio chunks

        Yields:
            Transcription segments as they become available
        """
        pass


class ISpeakerIdentifier(ABC):
    """Interface for speaker identification"""

    @abstractmethod
    async def identify_speaker(self, audio: AudioChunk) -> Speaker:
        """
        Identify speaker from audio

        Args:
            audio: Audio chunk

        Returns:
            Speaker identification result
        """
        pass

    @abstractmethod
    async def enroll_speaker(self, speaker_name: str, audio_samples: list[AudioChunk]) -> str:
        """
        Enroll new speaker for identification

        Args:
            speaker_name: Human-readable name
            audio_samples: Sample audio clips of speaker

        Returns:
            Unique speaker ID
        """
        pass


# ============================================================================
# Privacy Layer Interfaces
# ============================================================================


class PIIType(Enum):
    """Types of personally identifiable information"""

    FACE = "face"
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    ADDRESS = "address"
    NAME = "name"
    DATE_OF_BIRTH = "date_of_birth"
    LICENSE_PLATE = "license_plate"
    PASSPORT = "passport"


@dataclass
class PIIDetection:
    """Detected personally identifiable information"""

    pii_type: PIIType
    value: str
    confidence: float
    location: Optional[BoundingBox] = None  # For visual PII
    start_offset: Optional[int] = None  # For text PII
    end_offset: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RedactionConfig:
    """Configuration for PII redaction"""

    blur_faces: bool = True
    blur_sigma: float = 50.0
    redact_text: bool = True
    redaction_char: str = "X"
    anonymize: bool = False  # Replace with synthetic data
    preserve_format: bool = True  # Keep data format (e.g., XXX-XX-1234 for SSN)


class ConsentType(Enum):
    """Types of user consent"""

    DATA_COLLECTION = "data_collection"
    FACE_RECOGNITION = "face_recognition"
    AUDIO_RECORDING = "audio_recording"
    CLOUD_SYNC = "cloud_sync"
    ANALYTICS = "analytics"
    THIRD_PARTY_SHARING = "third_party_sharing"


class IPIIDetector(ABC):
    """Interface for PII detection"""

    @abstractmethod
    async def detect_visual_pii(self, frame: Frame) -> list[PIIDetection]:
        """
        Detect PII in visual data (faces, ID cards, etc.)

        Args:
            frame: Input frame

        Returns:
            List of detected PII
        """
        pass

    @abstractmethod
    async def detect_text_pii(self, text: str) -> list[PIIDetection]:
        """
        Detect PII in text data

        Args:
            text: Input text

        Returns:
            List of detected PII
        """
        pass


class IPrivacyFilter(ABC):
    """Interface for privacy filtering"""

    @abstractmethod
    async def filter_frame(
        self, frame: Frame, pii_detections: list[PIIDetection], config: RedactionConfig
    ) -> Frame:
        """
        Apply privacy filters to frame

        Args:
            frame: Input frame
            pii_detections: Detected PII to filter
            config: Filtering configuration

        Returns:
            Filtered frame
        """
        pass

    @abstractmethod
    async def filter_text(
        self, text: str, pii_detections: list[PIIDetection], config: RedactionConfig
    ) -> str:
        """
        Apply privacy filters to text

        Args:
            text: Input text
            pii_detections: Detected PII to filter
            config: Filtering configuration

        Returns:
            Filtered text
        """
        pass


class IConsentManager(ABC):
    """Interface for consent management"""

    @abstractmethod
    async def check_consent(self, user_id: str, consent_type: ConsentType) -> bool:
        """
        Check if user has given consent

        Args:
            user_id: User identifier
            consent_type: Type of consent to check

        Returns:
            True if consent granted
        """
        pass

    @abstractmethod
    async def request_consent(
        self, user_id: str, consent_type: ConsentType, description: str
    ) -> bool:
        """
        Request user consent

        Args:
            user_id: User identifier
            consent_type: Type of consent
            description: Human-readable description

        Returns:
            True if consent granted
        """
        pass

    @abstractmethod
    async def revoke_consent(self, user_id: str, consent_type: ConsentType) -> None:
        """
        Revoke previously granted consent

        Args:
            user_id: User identifier
            consent_type: Type of consent to revoke
        """
        pass


# ============================================================================
# AI Engine Interfaces
# ============================================================================


@dataclass
class Context:
    """Current contextual information for AI processing"""

    user_id: str
    session_id: str
    current_scene: Optional[SceneAnalysis] = None
    recent_interactions: list[dict[str, Any]] = field(default_factory=list)
    user_preferences: dict[str, Any] = field(default_factory=dict)
    temporal_history: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMRequest:
    """Request for LLM generation"""

    prompt: str
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    context: Optional[Context] = None
    stop_sequences: list[str] = field(default_factory=list)


@dataclass
class LLMResponse:
    """Response from LLM generation"""

    text: str
    model: str
    tokens_used: int
    finish_reason: str
    confidence: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    """Document in knowledge base"""

    id: str
    content: str
    metadata: dict[str, Any]
    embedding: npt.NDArray[np.float32]
    created_at: Timestamp
    updated_at: Timestamp


@dataclass
class SearchResult:
    """Search result from knowledge base"""

    document: Document
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RAGRequest:
    """Request for RAG pipeline"""

    query: str
    context: Optional[Context] = None
    top_k_documents: int = 5
    llm_config: Optional[LLMRequest] = None
    filters: Optional[dict[str, Any]] = None


@dataclass
class RAGResponse:
    """Response from RAG pipeline"""

    answer: str
    sources: list[Document]
    llm_response: LLMResponse
    metadata: dict[str, Any] = field(default_factory=dict)


class IContextEngine(ABC):
    """Interface for context management"""

    @abstractmethod
    async def update_context(
        self,
        session_id: str,
        scene: Optional[SceneAnalysis] = None,
        transcription: Optional[TranscriptionSegment] = None,
    ) -> Context:
        """
        Update context with new information

        Args:
            session_id: Current session ID
            scene: Latest scene analysis
            transcription: Latest transcription

        Returns:
            Updated context
        """
        pass

    @abstractmethod
    async def get_context(self, session_id: str) -> Context:
        """
        Retrieve current context for session

        Args:
            session_id: Session identifier

        Returns:
            Current context

        Raises:
            ContextNotFoundError: If session not found
        """
        pass

    @abstractmethod
    async def get_context_summary(self, session_id: str, max_length: int = 500) -> str:
        """
        Get text summary of current context

        Args:
            session_id: Session ID
            max_length: Maximum summary length in characters

        Returns:
            Context summary
        """
        pass


class ILLMProvider(ABC):
    """Interface for LLM integration"""

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate text using LLM

        Args:
            request: LLM request configuration

        Returns:
            Generated response
        """
        pass

    @abstractmethod
    async def generate_stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """
        Generate text with streaming response

        Args:
            request: LLM request configuration

        Yields:
            Text chunks as generated
        """
        pass

    @abstractmethod
    async def embed(self, text: str) -> npt.NDArray[np.float32]:
        """
        Generate embeddings for text

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        pass


class IKnowledgeBase(ABC):
    """Interface for knowledge base operations"""

    @abstractmethod
    async def search(
        self, query: str, top_k: int = 5, filters: Optional[dict[str, Any]] = None
    ) -> list[SearchResult]:
        """
        Semantic search in knowledge base

        Args:
            query: Search query
            top_k: Number of results to return
            filters: Metadata filters

        Returns:
            Top matching documents
        """
        pass

    @abstractmethod
    async def add_document(self, document: Document) -> str:
        """
        Add document to knowledge base

        Args:
            document: Document to add

        Returns:
            Document ID
        """
        pass

    @abstractmethod
    async def get_document(self, document_id: str) -> Optional[Document]:
        """
        Retrieve document by ID

        Args:
            document_id: Document identifier

        Returns:
            Document or None if not found
        """
        pass

    @abstractmethod
    async def delete_document(self, document_id: str) -> None:
        """
        Delete document from knowledge base

        Args:
            document_id: Document identifier
        """
        pass


class IRAGPipeline(ABC):
    """Interface for RAG pipeline"""

    @abstractmethod
    async def query(self, request: RAGRequest) -> RAGResponse:
        """
        Execute RAG query

        Args:
            request: RAG request configuration

        Returns:
            Generated answer with sources
        """
        pass


# ============================================================================
# Communication Interfaces
# ============================================================================

EventHandler = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass
class Message:
    """Message for queue system"""

    id: str
    topic: str
    payload: dict[str, Any]
    timestamp: Timestamp
    priority: int = 0
    retry_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class IEventBus(ABC):
    """Interface for event bus"""

    @abstractmethod
    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """
        Publish event

        Args:
            event_type: Event type identifier
            payload: Event data
        """
        pass

    @abstractmethod
    async def subscribe(self, event_type: str, handler: EventHandler) -> str:
        """
        Subscribe to event type

        Args:
            event_type: Event type to subscribe to
            handler: Async callback function

        Returns:
            Subscription ID for unsubscribing
        """
        pass

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> None:
        """
        Unsubscribe from events

        Args:
            subscription_id: Subscription identifier
        """
        pass


class IMessageQueue(ABC):
    """Interface for message queue"""

    @abstractmethod
    async def enqueue(self, message: Message) -> None:
        """
        Add message to queue

        Args:
            message: Message to enqueue
        """
        pass

    @abstractmethod
    async def dequeue(self, topic: str, timeout: float = 1.0) -> Optional[Message]:
        """
        Retrieve message from queue

        Args:
            topic: Queue topic
            timeout: Maximum wait time in seconds

        Returns:
            Message or None if timeout
        """
        pass

    @abstractmethod
    async def acknowledge(self, message_id: str) -> None:
        """
        Acknowledge message processing

        Args:
            message_id: Message identifier
        """
        pass

    @abstractmethod
    async def reject(self, message_id: str, requeue: bool = True) -> None:
        """
        Reject message

        Args:
            message_id: Message identifier
            requeue: Whether to requeue message
        """
        pass


# ============================================================================
# Storage Interfaces
# ============================================================================


@dataclass
class Session:
    """User session data"""

    session_id: str
    user_id: str
    start_time: Timestamp
    end_time: Optional[Timestamp] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        """Check if session is active"""
        return self.end_time is None

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get session duration in seconds"""
        if self.end_time is None:
            return None
        return self.end_time.value - self.start_time.value


class ISessionStore(ABC):
    """Interface for session storage"""

    @abstractmethod
    async def create_session(self, user_id: str) -> Session:
        """
        Create new session

        Args:
            user_id: User identifier

        Returns:
            Created session
        """
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        Retrieve session by ID

        Args:
            session_id: Session identifier

        Returns:
            Session or None if not found
        """
        pass

    @abstractmethod
    async def update_session(self, session: Session) -> None:
        """
        Update session data

        Args:
            session: Session to update
        """
        pass

    @abstractmethod
    async def end_session(self, session_id: str) -> None:
        """
        End active session

        Args:
            session_id: Session identifier
        """
        pass


class ICacheStore(ABC):
    """Interface for cache storage"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store value in cache

        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live in seconds
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        Delete value from cache

        Args:
            key: Cache key
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        pass


# ============================================================================
# Lifecycle Management
# ============================================================================


class ILifecycle(ABC):
    """Interface for component lifecycle management"""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize component and allocate resources"""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start component operations"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop component operations"""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup and release resources"""
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """
        Check component health

        Returns:
            True if component is healthy
        """
        pass


# ============================================================================
# Error Hierarchy
# ============================================================================


class EduLensError(Exception):
    """Base exception for all EduLens errors"""

    pass


class CameraError(EduLensError):
    """Camera-related errors"""

    pass


class AudioError(EduLensError):
    """Audio-related errors"""

    pass


class VisionError(EduLensError):
    """Vision processing errors"""

    pass


class AIError(EduLensError):
    """AI engine errors"""

    pass


class PrivacyError(EduLensError):
    """Privacy-related errors"""

    pass


class StorageError(EduLensError):
    """Storage-related errors"""

    pass


class ConfigurationError(EduLensError):
    """Configuration errors"""

    pass


class ContextNotFoundError(EduLensError):
    """Context not found error"""

    pass


# ============================================================================
# Protocol Definitions (Runtime Checkable)
# ============================================================================


@runtime_checkable
class Serializable(Protocol):
    """Protocol for serializable objects"""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Serializable":
        """Create from dictionary"""
        ...


@runtime_checkable
class Configurable(Protocol):
    """Protocol for configurable components"""

    def configure(self, config: dict[str, Any]) -> None:
        """Configure component"""
        ...

    def get_config(self) -> dict[str, Any]:
        """Get current configuration"""
        ...


# ============================================================================
# Type Variables
# ============================================================================

T = TypeVar("T")
ComponentType = TypeVar("ComponentType", bound=ILifecycle)
