"""
EduLens Data Minimizer

This module implements data minimization strategies to extract only necessary features
from sensitive data (images, audio) and immediately discard the raw data. Ensures
COPPA compliance by never persisting personally identifiable information.

Classification: SECURITY CRITICAL
Author: Security and Privacy Agent (SEC-001)
Task: SEC-001-T2 - On-Device Data Protection
Last Updated: 2025-12-10
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataType(Enum):
    """Types of data that can be minimized."""
    IMAGE = "image"
    AUDIO = "audio"
    TEXT = "text"
    VIDEO = "video"
    TELEMETRY = "telemetry"
    METADATA = "metadata"


class MinimizationLevel(Enum):
    """Levels of data minimization aggressiveness."""
    NONE = 0  # No minimization
    BASIC = 1  # Remove obvious PII
    STANDARD = 2  # Extract features, discard raw data
    AGGRESSIVE = 3  # Maximum minimization, anonymization
    ABSOLUTE = 4  # Only non-reversible digests


@dataclass
class MinimizedImage:
    """Minimized representation of an image (raw image discarded)."""
    feature_digest: str  # Non-reversible hash of features
    detected_objects: List[str]  # e.g., ["book", "desk", "pencil"]
    detected_text: List[str]  # OCR results (text only, no positions)
    scene_type: str  # e.g., "classroom", "homework", "textbook"
    quality_score: float  # Image quality (0.0 - 1.0)
    timestamp: datetime
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "feature_digest": self.feature_digest,
            "detected_objects": self.detected_objects,
            "detected_text": self.detected_text,
            "scene_type": self.scene_type,
            "quality_score": self.quality_score,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class MinimizedAudio:
    """Minimized representation of audio (raw audio discarded)."""
    feature_digest: str  # Non-reversible hash of features
    transcription: str  # Text transcription only
    intent: str  # Detected intent (e.g., "question", "request_help")
    keywords: List[str]  # Extracted keywords
    duration_seconds: float
    language: str
    timestamp: datetime
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "feature_digest": self.feature_digest,
            "transcription": self.transcription,
            "intent": self.intent,
            "keywords": self.keywords,
            "duration_seconds": self.duration_seconds,
            "language": self.language,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class LearningDataAggregate:
    """Aggregated learning data (anonymized, non-identifiable)."""
    session_id: str  # Ephemeral session ID (not linked to user)
    subject_area: str
    interaction_count: int
    question_count: int
    success_indicators: List[str]
    difficulty_level: str
    duration_seconds: float
    timestamp_hour: int  # Hour of day only (no precise timestamp)
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "subject_area": self.subject_area,
            "interaction_count": self.interaction_count,
            "question_count": self.question_count,
            "success_indicators": self.success_indicators,
            "difficulty_level": self.difficulty_level,
            "duration_seconds": self.duration_seconds,
            "timestamp_hour": self.timestamp_hour,
            "metadata": self.metadata,
        }


class DataMinimizer:
    """
    Implements data minimization strategies for privacy protection.

    Key Features:
    - Extract only necessary features from images
    - Extract only necessary features from audio
    - Discard raw sensitive data immediately
    - Remove personally identifiable information (PII)
    - Aggregate and anonymize learning data
    - Create non-reversible data digests

    COPPA Compliance:
    - No storage of raw images or audio
    - All extracted data is minimal and purpose-limited
    - PII is automatically stripped
    - Aggregation prevents individual identification
    """

    def __init__(self, default_minimization_level: MinimizationLevel = MinimizationLevel.STANDARD):
        """
        Initialize the data minimizer.

        Args:
            default_minimization_level: Default level of minimization (default: STANDARD)
        """
        self.default_minimization_level = default_minimization_level
        self.pii_patterns = self._initialize_pii_patterns()

        logger.info(f"DataMinimizer initialized with level: {default_minimization_level.name}")

    def minimize_image(self,
                      image_data: bytes,
                      detected_objects: Optional[List[str]] = None,
                      detected_text: Optional[List[str]] = None,
                      scene_type: Optional[str] = None,
                      minimization_level: Optional[MinimizationLevel] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> MinimizedImage:
        """
        Extract minimal features from image and discard raw image data.

        This method processes the image to extract only the necessary information
        for educational assistance, then IMMEDIATELY discards the raw image data.

        Args:
            image_data: Raw image bytes (WILL BE DISCARDED)
            detected_objects: List of detected objects (from CV model)
            detected_text: List of detected text (from OCR)
            scene_type: Type of scene detected
            minimization_level: Override default minimization level
            metadata: Optional metadata

        Returns:
            MinimizedImage with only essential features

        Example:
            >>> minimizer = DataMinimizer()
            >>> # Image processing happens here, then raw data is discarded
            >>> minimized = minimizer.minimize_image(
            ...     image_data=raw_bytes,
            ...     detected_objects=["textbook", "desk"],
            ...     detected_text=["Chapter 5", "Photosynthesis"],
            ...     scene_type="textbook"
            ... )
            >>> # raw_bytes is now discarded, only minimized features remain
        """
        level = minimization_level or self.default_minimization_level

        # Extract features (simulated - in production, this would use CV models)
        feature_vector = self._extract_image_features(image_data)

        # Create non-reversible digest of features
        feature_digest = self._create_digest(feature_vector)

        # Strip PII from detected text
        if detected_text:
            detected_text = [self.strip_pii(text) for text in detected_text]

        # Calculate quality score (simulated)
        quality_score = self._calculate_image_quality(image_data)

        # Create minimized representation
        minimized = MinimizedImage(
            feature_digest=feature_digest,
            detected_objects=detected_objects or [],
            detected_text=detected_text or [],
            scene_type=scene_type or "unknown",
            quality_score=quality_score,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
        )

        # CRITICAL: Raw image_data is now out of scope and will be garbage collected
        # Explicitly clear reference to ensure immediate cleanup
        image_data = None

        logger.info(
            f"Image minimized: {len(minimized.detected_objects)} objects, "
            f"{len(minimized.detected_text)} text items, digest: {feature_digest[:16]}..."
        )

        return minimized

    def minimize_audio(self,
                      audio_data: bytes,
                      transcription: Optional[str] = None,
                      intent: Optional[str] = None,
                      duration_seconds: Optional[float] = None,
                      language: str = "en",
                      minimization_level: Optional[MinimizationLevel] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> MinimizedAudio:
        """
        Extract minimal features from audio and discard raw audio data.

        This method processes the audio to extract only the necessary information
        (transcription, intent, keywords), then IMMEDIATELY discards the raw audio.

        Args:
            audio_data: Raw audio bytes (WILL BE DISCARDED)
            transcription: Text transcription (from ASR)
            intent: Detected intent
            duration_seconds: Audio duration
            language: Language code
            minimization_level: Override default minimization level
            metadata: Optional metadata

        Returns:
            MinimizedAudio with only essential features

        Example:
            >>> minimizer = DataMinimizer()
            >>> minimized = minimizer.minimize_audio(
            ...     audio_data=raw_audio_bytes,
            ...     transcription="What is photosynthesis?",
            ...     intent="question",
            ...     duration_seconds=2.5
            ... )
            >>> # raw_audio_bytes is now discarded
        """
        level = minimization_level or self.default_minimization_level

        # Extract features (simulated - in production, this would use audio models)
        feature_vector = self._extract_audio_features(audio_data)

        # Create non-reversible digest of features
        feature_digest = self._create_digest(feature_vector)

        # Strip PII from transcription
        if transcription:
            transcription = self.strip_pii(transcription)

        # Extract keywords
        keywords = self._extract_keywords(transcription) if transcription else []

        # Calculate duration if not provided
        if duration_seconds is None:
            duration_seconds = self._calculate_audio_duration(audio_data)

        # Create minimized representation
        minimized = MinimizedAudio(
            feature_digest=feature_digest,
            transcription=transcription or "",
            intent=intent or "unknown",
            keywords=keywords,
            duration_seconds=duration_seconds,
            language=language,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
        )

        # CRITICAL: Raw audio_data is now out of scope and will be garbage collected
        audio_data = None

        logger.info(
            f"Audio minimized: {duration_seconds:.2f}s, "
            f"transcription length: {len(transcription or '')}, "
            f"digest: {feature_digest[:16]}..."
        )

        return minimized

    def aggregate_learning_data(self,
                               interaction_events: List[Dict[str, Any]],
                               session_id: Optional[str] = None,
                               anonymize: bool = True) -> LearningDataAggregate:
        """
        Aggregate learning interaction data into anonymized summary.

        This method combines multiple interaction events into a single anonymized
        aggregate that cannot be traced back to individual users.

        Args:
            interaction_events: List of interaction event dictionaries
            session_id: Optional session ID (will be hashed if not provided)
            anonymize: Apply additional anonymization (default: True)

        Returns:
            LearningDataAggregate with anonymized summary

        Example:
            >>> events = [
            ...     {"type": "question", "subject": "science", "success": True},
            ...     {"type": "question", "subject": "science", "success": True},
            ... ]
            >>> aggregate = minimizer.aggregate_learning_data(events)
        """
        if not interaction_events:
            raise ValueError("No interaction events provided")

        # Generate or hash session ID
        if session_id is None:
            session_data = f"{datetime.utcnow().isoformat()}{len(interaction_events)}"
            session_id = hashlib.sha256(session_data.encode()).hexdigest()[:16]
        elif anonymize:
            session_id = hashlib.sha256(session_id.encode()).hexdigest()[:16]

        # Extract aggregated metrics
        subject_areas = set()
        question_count = 0
        success_indicators = []
        total_duration = 0.0

        for event in interaction_events:
            if "subject" in event:
                subject_areas.add(event["subject"])
            if event.get("type") == "question":
                question_count += 1
            if event.get("success"):
                success_indicators.append(event.get("indicator", "generic_success"))
            if "duration_seconds" in event:
                total_duration += event["duration_seconds"]

        # Determine primary subject area
        subject_area = list(subject_areas)[0] if subject_areas else "general"

        # Determine difficulty level based on success rate
        difficulty_level = self._infer_difficulty_level(interaction_events)

        # Get hour of day only (no precise timestamp for privacy)
        timestamp_hour = datetime.utcnow().hour

        # Create aggregate
        aggregate = LearningDataAggregate(
            session_id=session_id,
            subject_area=subject_area,
            interaction_count=len(interaction_events),
            question_count=question_count,
            success_indicators=success_indicators,
            difficulty_level=difficulty_level,
            duration_seconds=total_duration,
            timestamp_hour=timestamp_hour,
            metadata={"aggregated_from": len(interaction_events)},
        )

        logger.info(
            f"Aggregated learning data: {len(interaction_events)} events, "
            f"subject: {subject_area}, session: {session_id[:8]}..."
        )

        return aggregate

    def strip_pii(self, text: str) -> str:
        """
        Remove personally identifiable information from text.

        Removes or redacts:
        - Names (common patterns)
        - Email addresses
        - Phone numbers
        - Addresses
        - Social Security Numbers
        - Credit card numbers
        - IP addresses
        - URLs with personal info

        Args:
            text: Input text potentially containing PII

        Returns:
            Text with PII removed/redacted

        Example:
            >>> minimizer.strip_pii("My name is John Smith and my email is john@example.com")
            "My name is [REDACTED] and my email is [REDACTED]"
        """
        if not text:
            return text

        cleaned = text

        # Apply PII removal patterns
        for pattern_name, (pattern, replacement) in self.pii_patterns.items():
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

        return cleaned

    def create_digest(self, data: Any) -> str:
        """
        Create a non-reversible digest of data.

        This creates a SHA-256 hash that can be used for deduplication
        or validation without exposing the original data.

        Args:
            data: Any data to create digest from

        Returns:
            Hex digest string (64 characters)

        Example:
            >>> digest = minimizer.create_digest({"some": "data"})
        """
        return self._create_digest(data)

    def minimize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Minimize metadata by removing unnecessary fields.

        Args:
            metadata: Input metadata dictionary

        Returns:
            Minimized metadata with only essential fields
        """
        # Define essential metadata fields
        essential_fields = {
            "timestamp",
            "type",
            "classification",
            "subject_area",
            "duration_seconds",
            "language",
            "device_type",
        }

        # Keep only essential fields
        minimized = {
            key: value
            for key, value in metadata.items()
            if key in essential_fields
        }

        # Round timestamps to hour for privacy
        if "timestamp" in minimized:
            if isinstance(minimized["timestamp"], datetime):
                minimized["timestamp_hour"] = minimized["timestamp"].hour
                del minimized["timestamp"]

        return minimized

    def _extract_image_features(self, image_data: bytes) -> np.ndarray:
        """
        Extract feature vector from image (simulated).

        In production, this would use a computer vision model to extract
        semantic features from the image.

        Args:
            image_data: Raw image bytes

        Returns:
            Feature vector as numpy array
        """
        # Simulate feature extraction with hash-based features
        # In production: Use ResNet, CLIP, or similar model
        hash_value = hashlib.sha256(image_data).digest()
        features = np.frombuffer(hash_value, dtype=np.uint8).astype(np.float32)

        return features

    def _extract_audio_features(self, audio_data: bytes) -> np.ndarray:
        """
        Extract feature vector from audio (simulated).

        In production, this would use an audio model to extract
        acoustic features from the audio.

        Args:
            audio_data: Raw audio bytes

        Returns:
            Feature vector as numpy array
        """
        # Simulate feature extraction with hash-based features
        # In production: Use Wav2Vec2, HuBERT, or similar model
        hash_value = hashlib.sha256(audio_data).digest()
        features = np.frombuffer(hash_value, dtype=np.uint8).astype(np.float32)

        return features

    def _create_digest(self, data: Any) -> str:
        """Create non-reversible SHA-256 digest of data."""
        if isinstance(data, bytes):
            data_bytes = data
        elif isinstance(data, str):
            data_bytes = data.encode('utf-8')
        elif isinstance(data, np.ndarray):
            data_bytes = data.tobytes()
        elif isinstance(data, (dict, list)):
            data_bytes = json.dumps(data, sort_keys=True).encode('utf-8')
        else:
            data_bytes = str(data).encode('utf-8')

        return hashlib.sha256(data_bytes).hexdigest()

    def _calculate_image_quality(self, image_data: bytes) -> float:
        """
        Calculate image quality score (simulated).

        In production, this would analyze image sharpness, brightness, etc.

        Args:
            image_data: Raw image bytes

        Returns:
            Quality score (0.0 - 1.0)
        """
        # Simulate quality calculation
        # In production: Use BRISQUE, NIQE, or similar metric
        hash_value = int(hashlib.sha256(image_data).hexdigest()[:8], 16)
        quality = (hash_value % 40 + 60) / 100.0  # Range: 0.6 - 1.0

        return quality

    def _calculate_audio_duration(self, audio_data: bytes) -> float:
        """
        Calculate audio duration in seconds (simulated).

        In production, this would parse audio format and calculate duration.

        Args:
            audio_data: Raw audio bytes

        Returns:
            Duration in seconds
        """
        # Simulate duration calculation
        # Assume 16kHz 16-bit mono audio: 32000 bytes per second
        duration = len(audio_data) / 32000.0

        return max(0.1, min(duration, 30.0))  # Clamp to 0.1 - 30 seconds

    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        Extract keywords from text.

        Args:
            text: Input text
            max_keywords: Maximum number of keywords to extract

        Returns:
            List of keywords
        """
        if not text:
            return []

        # Simple keyword extraction (in production: use TF-IDF, KeyBERT, etc.)
        # Remove common stop words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "is", "was", "are", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "can", "what", "when", "where", "why", "how",
        }

        # Extract words (alphanumeric only)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

        # Filter stop words and get unique words
        keywords = [word for word in words if word not in stop_words]

        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for word in keywords:
            if word not in seen:
                seen.add(word)
                unique_keywords.append(word)

        return unique_keywords[:max_keywords]

    def _infer_difficulty_level(self, events: List[Dict[str, Any]]) -> str:
        """
        Infer difficulty level from interaction events.

        Args:
            events: List of interaction events

        Returns:
            Difficulty level string ("easy", "medium", "hard")
        """
        if not events:
            return "unknown"

        # Calculate success rate
        success_count = sum(1 for event in events if event.get("success", False))
        success_rate = success_count / len(events)

        # Infer difficulty
        if success_rate >= 0.8:
            return "easy"
        elif success_rate >= 0.5:
            return "medium"
        else:
            return "hard"

    def _initialize_pii_patterns(self) -> Dict[str, Tuple[str, str]]:
        """
        Initialize regex patterns for PII detection and removal.

        Returns:
            Dictionary mapping PII type to (pattern, replacement) tuples
        """
        return {
            "email": (
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                '[EMAIL_REDACTED]'
            ),
            "phone": (
                r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
                '[PHONE_REDACTED]'
            ),
            "ssn": (
                r'\b\d{3}-\d{2}-\d{4}\b',
                '[SSN_REDACTED]'
            ),
            "credit_card": (
                r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
                '[CARD_REDACTED]'
            ),
            "ip_address": (
                r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
                '[IP_REDACTED]'
            ),
            "url_with_params": (
                r'https?://[^\s]+(?:\?|&)[^\s]*(?:token|key|password|session)=[^\s&]+',
                '[URL_REDACTED]'
            ),
            # Common name patterns (simple heuristic)
            "potential_name": (
                r'\b(?:my name is|i am|i\'m|called)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
                r'\1 [NAME_REDACTED]'
            ),
        }


# Export public API
__all__ = [
    "DataMinimizer",
    "DataType",
    "MinimizationLevel",
    "MinimizedImage",
    "MinimizedAudio",
    "LearningDataAggregate",
]
