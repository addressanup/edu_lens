# EduLens Component Interfaces

## Overview

This document defines the interfaces and contracts for all major components in the EduLens system. These interfaces enable loose coupling, testability, and modularity across the architecture.

## 1. Vision Pipeline Interfaces

### 1.1 IFrameCapture

Handles camera frame acquisition and buffering.

```python
from abc import ABC, abstractmethod
from typing import Optional, AsyncIterator
from dataclasses import dataclass
import numpy as np

@dataclass
class Frame:
    """Represents a single camera frame"""
    data: np.ndarray          # Raw frame data (H, W, C)
    timestamp: float          # Capture timestamp (Unix epoch)
    frame_id: int            # Monotonic frame counter
    metadata: dict           # Camera settings, exposure, etc.

class IFrameCapture(ABC):
    """Interface for camera frame capture"""

    @abstractmethod
    async def start_capture(self, fps: int = 30, resolution: tuple = (1920, 1080)) -> None:
        """
        Start capturing frames from the camera

        Args:
            fps: Target frames per second
            resolution: Capture resolution (width, height)
        """
        pass

    @abstractmethod
    async def stop_capture(self) -> None:
        """Stop frame capture and release resources"""
        pass

    @abstractmethod
    async def get_frame_stream(self) -> AsyncIterator[Frame]:
        """
        Get an async iterator of captured frames

        Yields:
            Frame: Next captured frame
        """
        pass

    @abstractmethod
    async def get_latest_frame(self) -> Optional[Frame]:
        """
        Get the most recent frame without blocking

        Returns:
            The latest frame or None if unavailable
        """
        pass

    @abstractmethod
    def is_capturing(self) -> bool:
        """Check if camera is currently capturing"""
        pass
```

### 1.2 IImagePreprocessor

Handles image preprocessing and normalization.

```python
from enum import Enum

class ColorSpace(Enum):
    RGB = "rgb"
    BGR = "bgr"
    GRAYSCALE = "grayscale"
    HSV = "hsv"

@dataclass
class PreprocessingConfig:
    target_size: Optional[tuple] = None  # (width, height)
    color_space: ColorSpace = ColorSpace.RGB
    normalize: bool = True
    mean: tuple = (0.485, 0.456, 0.406)
    std: tuple = (0.229, 0.224, 0.225)

class IImagePreprocessor(ABC):
    """Interface for image preprocessing operations"""

    @abstractmethod
    async def preprocess(
        self,
        frame: Frame,
        config: PreprocessingConfig
    ) -> np.ndarray:
        """
        Preprocess a frame for model inference

        Args:
            frame: Input frame
            config: Preprocessing configuration

        Returns:
            Preprocessed image tensor
        """
        pass

    @abstractmethod
    async def batch_preprocess(
        self,
        frames: list[Frame],
        config: PreprocessingConfig
    ) -> np.ndarray:
        """
        Preprocess multiple frames in batch

        Args:
            frames: List of input frames
            config: Preprocessing configuration

        Returns:
            Batched preprocessed tensors
        """
        pass
```

### 1.3 IObjectDetector

Detects and classifies objects in images.

```python
@dataclass
class BoundingBox:
    x1: float  # Top-left x (normalized 0-1)
    y1: float  # Top-left y (normalized 0-1)
    x2: float  # Bottom-right x (normalized 0-1)
    y2: float  # Bottom-right y (normalized 0-1)

@dataclass
class Detection:
    class_name: str
    confidence: float
    bbox: BoundingBox
    class_id: int
    features: Optional[np.ndarray] = None  # Embedding vector

class IObjectDetector(ABC):
    """Interface for object detection"""

    @abstractmethod
    async def detect(
        self,
        image: np.ndarray,
        confidence_threshold: float = 0.5,
        nms_threshold: float = 0.4
    ) -> list[Detection]:
        """
        Detect objects in an image

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
```

### 1.4 IOCREngine

Extracts text from images.

```python
@dataclass
class TextRegion:
    text: str
    bbox: BoundingBox
    confidence: float
    language: str

class IOCREngine(ABC):
    """Interface for optical character recognition"""

    @abstractmethod
    async def extract_text(
        self,
        image: np.ndarray,
        languages: Optional[list[str]] = None
    ) -> list[TextRegion]:
        """
        Extract text from an image

        Args:
            image: Input image
            languages: List of expected languages (e.g., ['en', 'es'])

        Returns:
            List of detected text regions
        """
        pass

    @abstractmethod
    async def extract_text_structured(
        self,
        image: np.ndarray
    ) -> dict:
        """
        Extract structured text (tables, forms, etc.)

        Args:
            image: Input image

        Returns:
            Structured text data with layout information
        """
        pass
```

### 1.5 ISceneAnalyzer

Analyzes overall scene context.

```python
from enum import Enum

class SceneType(Enum):
    CLASSROOM = "classroom"
    LABORATORY = "laboratory"
    OUTDOOR = "outdoor"
    LIBRARY = "library"
    LECTURE_HALL = "lecture_hall"
    OFFICE = "office"
    UNKNOWN = "unknown"

@dataclass
class SceneAnalysis:
    scene_type: SceneType
    confidence: float
    objects: list[Detection]
    text_regions: list[TextRegion]
    features: np.ndarray  # Scene embedding
    description: str

class ISceneAnalyzer(ABC):
    """Interface for scene understanding"""

    @abstractmethod
    async def analyze_scene(
        self,
        frame: Frame,
        include_objects: bool = True,
        include_text: bool = True
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
```

## 2. Audio Pipeline Interfaces

### 2.1 IAudioCapture

Handles microphone audio acquisition.

```python
@dataclass
class AudioChunk:
    data: np.ndarray      # Audio samples (channels, samples)
    timestamp: float      # Capture timestamp
    sample_rate: int      # Sampling rate (Hz)
    channels: int         # Number of audio channels

class IAudioCapture(ABC):
    """Interface for audio capture"""

    @abstractmethod
    async def start_capture(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_duration_ms: int = 100
    ) -> None:
        """
        Start capturing audio

        Args:
            sample_rate: Audio sample rate
            channels: Number of audio channels
            chunk_duration_ms: Duration of each audio chunk
        """
        pass

    @abstractmethod
    async def stop_capture(self) -> None:
        """Stop audio capture"""
        pass

    @abstractmethod
    async def get_audio_stream(self) -> AsyncIterator[AudioChunk]:
        """Get stream of audio chunks"""
        pass
```

### 2.2 IAudioPreprocessor

Handles audio preprocessing and enhancement.

```python
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
```

### 2.3 ISpeechRecognizer

Converts speech to text.

```python
@dataclass
class TranscriptionSegment:
    text: str
    start_time: float
    end_time: float
    confidence: float
    language: str
    speaker_id: Optional[str] = None

class ISpeechRecognizer(ABC):
    """Interface for speech recognition"""

    @abstractmethod
    async def transcribe(
        self,
        audio: AudioChunk,
        language: Optional[str] = None
    ) -> TranscriptionSegment:
        """
        Transcribe audio to text

        Args:
            audio: Audio chunk to transcribe
            language: Expected language code

        Returns:
            Transcription result
        """
        pass

    @abstractmethod
    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[AudioChunk]
    ) -> AsyncIterator[TranscriptionSegment]:
        """
        Transcribe streaming audio in real-time

        Args:
            audio_stream: Stream of audio chunks

        Yields:
            Transcription segments as they become available
        """
        pass
```

### 2.4 ISpeakerIdentifier

Identifies and separates speakers.

```python
@dataclass
class Speaker:
    speaker_id: str
    name: Optional[str] = None
    confidence: float = 0.0

class ISpeakerIdentifier(ABC):
    """Interface for speaker identification"""

    @abstractmethod
    async def identify_speaker(
        self,
        audio: AudioChunk
    ) -> Speaker:
        """Identify speaker from audio"""
        pass

    @abstractmethod
    async def enroll_speaker(
        self,
        speaker_name: str,
        audio_samples: list[AudioChunk]
    ) -> str:
        """
        Enroll a new speaker

        Returns:
            Speaker ID
        """
        pass
```

## 3. Privacy Layer Interfaces

### 3.1 IPIIDetector

Detects personally identifiable information.

```python
from enum import Enum

class PIIType(Enum):
    FACE = "face"
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    ADDRESS = "address"
    NAME = "name"
    DATE_OF_BIRTH = "date_of_birth"

@dataclass
class PIIDetection:
    pii_type: PIIType
    value: str
    confidence: float
    location: Optional[BoundingBox] = None  # For visual PII
    start_offset: Optional[int] = None      # For text PII
    end_offset: Optional[int] = None

class IPIIDetector(ABC):
    """Interface for PII detection"""

    @abstractmethod
    async def detect_visual_pii(
        self,
        frame: Frame
    ) -> list[PIIDetection]:
        """
        Detect PII in visual data (faces, ID cards, etc.)

        Args:
            frame: Input frame

        Returns:
            List of detected PII
        """
        pass

    @abstractmethod
    async def detect_text_pii(
        self,
        text: str
    ) -> list[PIIDetection]:
        """
        Detect PII in text data

        Args:
            text: Input text

        Returns:
            List of detected PII
        """
        pass
```

### 3.2 IPrivacyFilter

Redacts or anonymizes PII.

```python
@dataclass
class RedactionConfig:
    blur_faces: bool = True
    redact_text: bool = True
    anonymize: bool = False  # Replace with synthetic data

class IPrivacyFilter(ABC):
    """Interface for privacy filtering"""

    @abstractmethod
    async def filter_frame(
        self,
        frame: Frame,
        pii_detections: list[PIIDetection],
        config: RedactionConfig
    ) -> Frame:
        """
        Apply privacy filters to a frame

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
        self,
        text: str,
        pii_detections: list[PIIDetection],
        config: RedactionConfig
    ) -> str:
        """Apply privacy filters to text"""
        pass
```

### 3.3 IConsentManager

Manages user consent and preferences.

```python
from enum import Enum

class ConsentType(Enum):
    DATA_COLLECTION = "data_collection"
    FACE_RECOGNITION = "face_recognition"
    AUDIO_RECORDING = "audio_recording"
    CLOUD_SYNC = "cloud_sync"
    ANALYTICS = "analytics"

class IConsentManager(ABC):
    """Interface for consent management"""

    @abstractmethod
    async def check_consent(
        self,
        user_id: str,
        consent_type: ConsentType
    ) -> bool:
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
        self,
        user_id: str,
        consent_type: ConsentType,
        description: str
    ) -> bool:
        """
        Request user consent

        Returns:
            True if consent granted
        """
        pass

    @abstractmethod
    async def revoke_consent(
        self,
        user_id: str,
        consent_type: ConsentType
    ) -> None:
        """Revoke previously granted consent"""
        pass
```

## 4. AI Engine Interfaces

### 4.1 IContextEngine

Maintains and updates contextual information.

```python
@dataclass
class Context:
    user_id: str
    session_id: str
    current_scene: Optional[SceneAnalysis] = None
    recent_interactions: list[dict] = None
    user_preferences: dict = None
    temporal_history: list[dict] = None
    metadata: dict = None

class IContextEngine(ABC):
    """Interface for context management"""

    @abstractmethod
    async def update_context(
        self,
        session_id: str,
        scene: Optional[SceneAnalysis] = None,
        transcription: Optional[TranscriptionSegment] = None
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
        """Retrieve current context for a session"""
        pass

    @abstractmethod
    async def get_context_summary(
        self,
        session_id: str,
        max_length: int = 500
    ) -> str:
        """
        Get a text summary of current context

        Args:
            session_id: Session ID
            max_length: Maximum summary length in characters

        Returns:
            Context summary
        """
        pass
```

### 4.2 ILLMProvider

Interfaces with large language models.

```python
@dataclass
class LLMRequest:
    prompt: str
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000
    context: Optional[Context] = None

@dataclass
class LLMResponse:
    text: str
    model: str
    tokens_used: int
    finish_reason: str
    confidence: Optional[float] = None

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
    async def generate_stream(
        self,
        request: LLMRequest
    ) -> AsyncIterator[str]:
        """
        Generate text with streaming response

        Args:
            request: LLM request configuration

        Yields:
            Text chunks as they are generated
        """
        pass

    @abstractmethod
    async def embed(self, text: str) -> np.ndarray:
        """
        Generate embeddings for text

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        pass
```

### 4.3 IKnowledgeBase

Manages educational content and retrieval.

```python
@dataclass
class Document:
    id: str
    content: str
    metadata: dict
    embedding: np.ndarray

@dataclass
class SearchResult:
    document: Document
    score: float

class IKnowledgeBase(ABC):
    """Interface for knowledge base operations"""

    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[dict] = None
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
        """Add a document to the knowledge base"""
        pass

    @abstractmethod
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Retrieve a document by ID"""
        pass
```

### 4.4 IRAGPipeline

Retrieval-augmented generation pipeline.

```python
@dataclass
class RAGRequest:
    query: str
    context: Optional[Context] = None
    top_k_documents: int = 5
    llm_config: Optional[LLMRequest] = None

@dataclass
class RAGResponse:
    answer: str
    sources: list[Document]
    llm_response: LLMResponse

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
```

## 5. Communication Interfaces

### 5.1 IEventBus

Publish-subscribe event system.

```python
from typing import Callable, Awaitable

EventHandler = Callable[[dict], Awaitable[None]]

class IEventBus(ABC):
    """Interface for event bus"""

    @abstractmethod
    async def publish(self, event_type: str, payload: dict) -> None:
        """
        Publish an event

        Args:
            event_type: Event type identifier
            payload: Event data
        """
        pass

    @abstractmethod
    async def subscribe(
        self,
        event_type: str,
        handler: EventHandler
    ) -> str:
        """
        Subscribe to an event type

        Args:
            event_type: Event type to subscribe to
            handler: Async callback function

        Returns:
            Subscription ID
        """
        pass

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from events"""
        pass
```

### 5.2 IMessageQueue

Asynchronous message queue for task distribution.

```python
@dataclass
class Message:
    id: str
    topic: str
    payload: dict
    timestamp: float
    priority: int = 0
    retry_count: int = 0

class IMessageQueue(ABC):
    """Interface for message queue"""

    @abstractmethod
    async def enqueue(self, message: Message) -> None:
        """Add message to queue"""
        pass

    @abstractmethod
    async def dequeue(self, topic: str, timeout: float = 1.0) -> Optional[Message]:
        """
        Retrieve message from queue

        Args:
            topic: Queue topic
            timeout: Maximum wait time

        Returns:
            Message or None if timeout
        """
        pass

    @abstractmethod
    async def acknowledge(self, message_id: str) -> None:
        """Acknowledge message processing"""
        pass
```

## 6. Storage Interfaces

### 6.1 ISessionStore

Stores user session data.

```python
@dataclass
class Session:
    session_id: str
    user_id: str
    start_time: float
    end_time: Optional[float] = None
    metadata: dict = None

class ISessionStore(ABC):
    """Interface for session storage"""

    @abstractmethod
    async def create_session(self, user_id: str) -> Session:
        """Create a new session"""
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve session by ID"""
        pass

    @abstractmethod
    async def update_session(self, session: Session) -> None:
        """Update session data"""
        pass

    @abstractmethod
    async def end_session(self, session_id: str) -> None:
        """End a session"""
        pass
```

### 6.2 ICacheStore

Caching layer for frequently accessed data.

```python
class ICacheStore(ABC):
    """Interface for cache storage"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache"""
        pass

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
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
        """Delete value from cache"""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries"""
        pass
```

## 7. Interface Usage Examples

### Example 1: Vision Pipeline

```python
# Initialize components
frame_capture: IFrameCapture = get_frame_capture()
preprocessor: IImagePreprocessor = get_preprocessor()
scene_analyzer: ISceneAnalyzer = get_scene_analyzer()

# Start capture
await frame_capture.start_capture(fps=30)

# Process frames
async for frame in frame_capture.get_frame_stream():
    # Analyze scene
    analysis = await scene_analyzer.analyze_scene(frame)

    # Process results
    print(f"Scene type: {analysis.scene_type}")
    print(f"Objects detected: {len(analysis.objects)}")
```

### Example 2: Audio Pipeline with Privacy

```python
# Initialize components
audio_capture: IAudioCapture = get_audio_capture()
speech_recognizer: ISpeechRecognizer = get_speech_recognizer()
pii_detector: IPIIDetector = get_pii_detector()
privacy_filter: IPrivacyFilter = get_privacy_filter()

# Start capture
await audio_capture.start_capture()

# Process audio
async for audio in audio_capture.get_audio_stream():
    # Transcribe
    segment = await speech_recognizer.transcribe(audio)

    # Check for PII
    pii_list = await pii_detector.detect_text_pii(segment.text)

    # Filter if needed
    if pii_list:
        filtered_text = await privacy_filter.filter_text(
            segment.text,
            pii_list,
            RedactionConfig()
        )
        print(f"Filtered: {filtered_text}")
```

### Example 3: RAG Query

```python
# Initialize components
context_engine: IContextEngine = get_context_engine()
rag_pipeline: IRAGPipeline = get_rag_pipeline()

# Get current context
context = await context_engine.get_context(session_id)

# Execute RAG query
request = RAGRequest(
    query="Explain photosynthesis",
    context=context,
    top_k_documents=5
)

response = await rag_pipeline.query(request)
print(f"Answer: {response.answer}")
print(f"Sources: {len(response.sources)}")
```

---

**Document Version**: 1.0.0
**Last Updated**: 2025-12-10
**Authors**: Integration Agent (INT-001)
**Status**: Draft
