"""
Wake Word Detection Engine for EduLens

High-performance wake word detector optimized for "Hey EduLens" trigger phrase.
Designed for edge device deployment with special optimizations for children's
voices (ages 6-12).

Target Performance:
- 95%+ true positive rate
- <2% false positive rate
- <100ms detection latency
"""

import asyncio
import logging
import os
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import yaml

from .audio_capture import AudioConfig, MicrophoneStream
from .feature_extraction import (
    FeatureNormalizer,
    MFCCExtractor,
    NoiseEstimator,
    VoiceActivityDetector,
    combine_features,
)

logger = logging.getLogger(__name__)


class DetectionMode(Enum):
    """Detection mode options."""

    STREAMING = "streaming"  # Real-time continuous detection
    BATCH = "batch"  # Process complete audio files


@dataclass
class DetectionResult:
    """Wake word detection result."""

    detected: bool
    confidence: float
    timestamp: float
    latency_ms: float
    audio_segment: Optional[np.ndarray] = None


@dataclass
class DetectionStats:
    """Detection statistics for monitoring."""

    total_detections: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    avg_confidence: float = 0.0
    avg_latency_ms: float = 0.0

    @property
    def true_positive_rate(self) -> float:
        """Calculate TPR."""
        if self.true_positives + self.false_negatives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_negatives)

    @property
    def false_positive_rate(self) -> float:
        """Calculate FPR."""
        if self.false_positives + self.true_positives == 0:
            return 0.0
        return self.false_positives / (self.false_positives + self.true_positives)


class AudioStreamProcessor:
    """
    Real-time audio stream processor for wake word detection.

    Handles audio buffering, feature extraction, and detection pipeline
    with minimal latency.
    """

    def __init__(self, detector: "WakeWordDetector", audio_config: AudioConfig):
        """
        Initialize stream processor.

        Args:
            detector: Wake word detector instance
            audio_config: Audio configuration
        """
        self.detector = detector
        self.audio_config = audio_config

        # Feature extractors
        self.mfcc_extractor = MFCCExtractor(
            sample_rate=audio_config.sample_rate,
            n_mfcc=13,
            n_fft=512,
            hop_length=160,
            n_mels=40,
            fmin=100.0,  # Optimized for children
            fmax=8000.0,
        )

        self.vad = VoiceActivityDetector(
            sample_rate=audio_config.sample_rate,
            energy_threshold=0.05,  # Lower threshold for children
            speech_pad_ms=300.0,
        )

        self.noise_estimator = NoiseEstimator(
            sample_rate=audio_config.sample_rate, adaptation_rate=0.1
        )

        self.normalizer = FeatureNormalizer(feature_dim=39)  # 13 MFCC + delta + delta-delta

        # Processing state
        self._processing = False
        self._lock = threading.Lock()

        logger.info("Initialized AudioStreamProcessor")

    def process_chunk(self, audio_data: np.ndarray) -> Optional[DetectionResult]:
        """
        Process single audio chunk.

        Args:
            audio_data: Audio samples

        Returns:
            Detection result if wake word detected, None otherwise
        """
        start_time = time.time()

        try:
            # Voice activity detection
            is_speech, vad_confidence = self.vad.detect(audio_data)

            # Update noise estimator
            self.noise_estimator.update(audio_data, is_speech=is_speech)

            # Skip processing if no speech detected
            if not is_speech or vad_confidence < 0.3:
                return None

            # Extract features
            features = self._extract_features(audio_data)

            if features is None or features.shape[1] < 5:  # Need minimum frames
                return None

            # Run detection
            confidence = self.detector._run_inference(features)

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Check detection threshold
            if confidence >= self.detector.threshold:
                logger.info(
                    f"Wake word detected! Confidence: {confidence:.3f}, Latency: {latency_ms:.1f}ms"
                )

                return DetectionResult(
                    detected=True,
                    confidence=confidence,
                    timestamp=time.time(),
                    latency_ms=latency_ms,
                    audio_segment=audio_data,
                )

            return None

        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}", exc_info=True)
            return None

    def _extract_features(self, audio_data: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract features from audio.

        Args:
            audio_data: Audio samples

        Returns:
            Feature array or None
        """
        try:
            # Apply noise reduction if SNR is low
            snr = self.noise_estimator.get_snr(audio_data)
            if snr < 10.0:  # Low SNR
                audio_data = self.noise_estimator.apply_noise_reduction(audio_data, strength=0.5)

            # Extract MFCC
            mfcc = self.mfcc_extractor.extract(audio_data)

            if mfcc.shape[1] == 0:
                return None

            # Combine with delta features
            features = combine_features(mfcc, include_delta=True, include_delta_delta=True)

            # Normalize features
            self.normalizer.update(features)
            features = self.normalizer.normalize(features)

            return features

        except Exception as e:
            logger.error(f"Feature extraction error: {e}")
            return None


class WakeWordDetector:
    """
    Wake word detection engine for "Hey EduLens".

    Supports both streaming and batch detection modes with configurable
    sensitivity and performance monitoring.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        sensitivity: float = 0.5,
        config_path: Optional[str] = None,
    ):
        """
        Initialize wake word detector.

        Args:
            model_path: Path to detection model (optional for now)
            sensitivity: Detection sensitivity (0.0-1.0)
            config_path: Path to configuration file
        """
        self.model_path = model_path
        self.sensitivity = sensitivity
        self.config_path = config_path

        # Load configuration
        self.config = self._load_config()

        # Audio configuration
        self.audio_config = AudioConfig(
            sample_rate=self.config.get("sample_rate", 16000),
            channels=1,
            chunk_size=self.config.get("chunk_size", 1024),
            buffer_duration=self.config.get("buffer_duration", 1.5),
        )

        # Detection parameters
        self.threshold = self._sensitivity_to_threshold(sensitivity)
        self.min_detection_interval = self.config.get("min_detection_interval", 2.0)  # seconds

        # Components
        self._stream = None
        self._processor = None
        self._callbacks = []

        # State
        self._is_listening = False
        self._last_detection_time = 0.0
        self._detection_confidence = 0.0
        self._lock = threading.Lock()
        self._detection_thread = None

        # Statistics
        self.stats = DetectionStats()

        # Load model
        self._model = self._load_model()

        logger.info(
            f"Initialized WakeWordDetector: "
            f"sensitivity={sensitivity}, threshold={self.threshold:.3f}"
        )

    def start_listening(self) -> None:
        """Start wake word detection in streaming mode."""
        with self._lock:
            if self._is_listening:
                logger.warning("Already listening")
                return

            try:
                # Initialize stream processor
                self._processor = AudioStreamProcessor(
                    detector=self, audio_config=self.audio_config
                )

                # Initialize microphone stream
                self._stream = MicrophoneStream(
                    config=self.audio_config, callback=self._audio_callback
                )

                # Start audio stream
                self._stream.start()

                self._is_listening = True

                logger.info("Started wake word detection")

            except Exception as e:
                logger.error(f"Failed to start listening: {e}", exc_info=True)
                self._cleanup()
                raise

    def stop_listening(self) -> None:
        """Stop wake word detection."""
        with self._lock:
            if not self._is_listening:
                return

            self._is_listening = False
            self._cleanup()

            logger.info("Stopped wake word detection")

    def on_wake_word(self, callback: Callable[[DetectionResult], None]) -> None:
        """
        Register callback for wake word detection.

        Args:
            callback: Function to call when wake word is detected
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)
            logger.info(f"Registered wake word callback: {callback.__name__}")

    def get_detection_confidence(self) -> float:
        """
        Get confidence of last detection.

        Returns:
            Confidence score (0.0-1.0)
        """
        return self._detection_confidence

    def adjust_sensitivity(self, level: float) -> None:
        """
        Adjust detection sensitivity.

        Args:
            level: Sensitivity level (0.0-1.0)
                  0.0 = fewer false positives, more false negatives
                  1.0 = fewer false negatives, more false positives
        """
        if not 0.0 <= level <= 1.0:
            raise ValueError("Sensitivity must be between 0.0 and 1.0")

        self.sensitivity = level
        self.threshold = self._sensitivity_to_threshold(level)

        logger.info(f"Adjusted sensitivity to {level:.2f} (threshold: {self.threshold:.3f})")

    def detect_batch(self, audio_data: np.ndarray) -> DetectionResult:
        """
        Detect wake word in audio file (batch mode).

        Args:
            audio_data: Audio samples

        Returns:
            Detection result
        """
        start_time = time.time()

        # Initialize processor if needed
        if self._processor is None:
            self._processor = AudioStreamProcessor(detector=self, audio_config=self.audio_config)

        # Process audio
        result = self._processor.process_chunk(audio_data)

        if result is None:
            latency_ms = (time.time() - start_time) * 1000
            result = DetectionResult(
                detected=False, confidence=0.0, timestamp=time.time(), latency_ms=latency_ms
            )

        return result

    def _audio_callback(self, audio_data: np.ndarray) -> None:
        """
        Callback for audio stream processing.

        Args:
            audio_data: Audio chunk from microphone
        """
        if not self._is_listening:
            return

        try:
            # Check minimum detection interval
            time_since_last = time.time() - self._last_detection_time
            if time_since_last < self.min_detection_interval:
                return

            # Process audio chunk
            result = self._processor.process_chunk(audio_data)

            if result and result.detected:
                self._detection_confidence = result.confidence
                self._last_detection_time = time.time()

                # Update statistics
                self.stats.total_detections += 1
                self.stats.avg_confidence = (
                    self.stats.avg_confidence * (self.stats.total_detections - 1)
                    + result.confidence
                ) / self.stats.total_detections
                self.stats.avg_latency_ms = (
                    self.stats.avg_latency_ms * (self.stats.total_detections - 1)
                    + result.latency_ms
                ) / self.stats.total_detections

                # Trigger callbacks
                self._trigger_callbacks(result)

        except Exception as e:
            logger.error(f"Error in audio callback: {e}", exc_info=True)

    def _trigger_callbacks(self, result: DetectionResult) -> None:
        """
        Trigger registered callbacks.

        Args:
            result: Detection result
        """
        for callback in self._callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Error in callback {callback.__name__}: {e}", exc_info=True)

    def _run_inference(self, features: np.ndarray) -> float:
        """
        Run wake word detection inference.

        Args:
            features: Extracted audio features

        Returns:
            Detection confidence score
        """
        # Placeholder for actual model inference
        # In production, this would run a trained neural network model
        # For now, implement a simple pattern matching approach

        if self._model is None:
            # Simple heuristic-based detection (replace with real model)
            return self._heuristic_detection(features)

        try:
            # Run model inference
            # confidence = self._model.predict(features)
            # return float(confidence)
            return self._heuristic_detection(features)

        except Exception as e:
            logger.error(f"Model inference error: {e}")
            return 0.0

    def _heuristic_detection(self, features: np.ndarray) -> float:
        """
        Heuristic-based detection (placeholder for model).

        Args:
            features: Audio features

        Returns:
            Confidence score
        """
        # Simple energy and pattern-based heuristic
        # In production, replace with trained model

        if features.shape[1] < 10:  # Need minimum frames for "Hey EduLens"
            return 0.0

        # Check feature statistics
        feature_energy = np.mean(np.abs(features))
        feature_variance = np.var(features)

        # Simple scoring (this is a placeholder)
        base_score = min(feature_energy / 0.5, 1.0) * 0.6
        variance_score = min(feature_variance / 0.3, 1.0) * 0.4

        confidence = base_score + variance_score

        # Add some randomness to simulate real detection
        confidence = np.clip(confidence, 0.0, 1.0)

        return float(confidence)

    def _load_model(self) -> Optional[object]:
        """
        Load wake word detection model.

        Returns:
            Model object or None
        """
        if self.model_path is None:
            logger.info("No model path specified, using heuristic detection")
            return None

        model_path = Path(self.model_path)
        if not model_path.exists():
            logger.warning(f"Model not found at {model_path}, using heuristic detection")
            return None

        try:
            # Placeholder for model loading
            # In production, load TensorFlow Lite, ONNX, or other edge model
            # model = tf.lite.Interpreter(model_path=str(model_path))
            # model.allocate_tensors()
            logger.info(f"Model loading not yet implemented: {model_path}")
            return None

        except Exception as e:
            logger.error(f"Failed to load model: {e}", exc_info=True)
            return None

    def _load_config(self) -> dict:
        """
        Load configuration from file.

        Returns:
            Configuration dictionary
        """
        if self.config_path is None:
            logger.info("No config path specified, using defaults")
            return {}

        config_path = Path(self.config_path)
        if not config_path.exists():
            logger.warning(f"Config not found at {config_path}, using defaults")
            return {}

        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {config_path}")
            return config

        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}

    @staticmethod
    def _sensitivity_to_threshold(sensitivity: float) -> float:
        """
        Convert sensitivity level to detection threshold.

        Args:
            sensitivity: Sensitivity (0.0-1.0)

        Returns:
            Detection threshold
        """
        # Map sensitivity to threshold
        # Higher sensitivity = lower threshold
        # 0.0 sensitivity -> 0.9 threshold (very conservative)
        # 0.5 sensitivity -> 0.6 threshold (balanced)
        # 1.0 sensitivity -> 0.3 threshold (very aggressive)

        threshold = 0.9 - (sensitivity * 0.6)
        return threshold

    def _cleanup(self) -> None:
        """Clean up resources."""
        if self._stream:
            try:
                self._stream.stop()
            except Exception as e:
                logger.error(f"Error stopping stream: {e}")
            finally:
                self._stream = None

        self._processor = None

    @property
    def is_listening(self) -> bool:
        """Check if detector is listening."""
        return self._is_listening

    def get_stats(self) -> DetectionStats:
        """Get detection statistics."""
        return self.stats

    def reset_stats(self) -> None:
        """Reset detection statistics."""
        self.stats = DetectionStats()

    def __enter__(self):
        """Context manager entry."""
        self.start_listening()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_listening()
        return False


class AsyncWakeWordDetector:
    """
    Async wrapper for wake word detector.

    Enables async/await patterns for wake word detection.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        sensitivity: float = 0.5,
        config_path: Optional[str] = None,
    ):
        """
        Initialize async wake word detector.

        Args:
            model_path: Path to detection model
            sensitivity: Detection sensitivity
            config_path: Path to configuration file
        """
        self._detector = WakeWordDetector(
            model_path=model_path, sensitivity=sensitivity, config_path=config_path
        )
        self._detection_queue = asyncio.Queue()
        self._loop = None

    async def start_listening(self) -> None:
        """Start wake word detection."""
        self._loop = asyncio.get_event_loop()

        # Register callback to enqueue detections
        self._detector.on_wake_word(self._enqueue_detection)

        # Start detector in thread
        await asyncio.get_event_loop().run_in_executor(None, self._detector.start_listening)

    async def stop_listening(self) -> None:
        """Stop wake word detection."""
        await asyncio.get_event_loop().run_in_executor(None, self._detector.stop_listening)

    def _enqueue_detection(self, result: DetectionResult) -> None:
        """Enqueue detection result."""
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._detection_queue.put(result), self._loop)

    async def wait_for_wake_word(self) -> DetectionResult:
        """
        Wait for next wake word detection.

        Returns:
            Detection result
        """
        return await self._detection_queue.get()

    def __aiter__(self):
        """Async iterator support."""
        return self

    async def __anext__(self) -> DetectionResult:
        """Get next detection."""
        if not self._detector.is_listening:
            raise StopAsyncIteration
        return await self.wait_for_wake_word()
