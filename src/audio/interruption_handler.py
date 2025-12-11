"""
Interruption Handler for EduLens Audio Pipeline

Handles barge-in functionality allowing students to interrupt
ongoing TTS playback when they want to speak.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

import numpy as np

logger = logging.getLogger(__name__)


class InterruptionType(Enum):
    """Types of interruptions."""
    SPEECH = "speech"  # Student started speaking
    WAKE_WORD = "wake_word"  # Wake word detected
    MANUAL = "manual"  # Manual interrupt (e.g., button press)
    TIMEOUT = "timeout"  # Response timeout


@dataclass
class InterruptionEvent:
    """Interruption event data."""
    interrupt_type: InterruptionType
    timestamp: float
    audio_level: float
    confidence: float
    metadata: dict = None

    @property
    def age_ms(self) -> float:
        """Get age of interruption in milliseconds."""
        return (time.time() - self.timestamp) * 1000


@dataclass
class InterruptionConfig:
    """Configuration for interruption detection."""
    # Detection thresholds
    speech_threshold: float = 0.05  # RMS threshold for speech detection
    confidence_threshold: float = 0.7  # Confidence threshold for valid interrupt

    # Timing parameters
    detection_window_ms: float = 200.0  # Window for detecting speech start (ms)
    debounce_time_ms: float = 100.0  # Debounce time to avoid false positives (ms)
    cooldown_time_ms: float = 500.0  # Cooldown after interruption (ms)

    # Sensitivity
    sensitivity: float = 0.7  # Overall sensitivity (0.0-1.0)

    # False positive prevention
    min_speech_duration_ms: float = 150.0  # Minimum speech duration to trigger (ms)
    require_sustained_speech: bool = True  # Require sustained speech vs single spike


class InterruptionHandler:
    """
    Handles barge-in interruptions during TTS playback.

    Detects when student starts speaking and immediately pauses
    current TTS playback to allow interaction.
    """

    def __init__(self, config: Optional[InterruptionConfig] = None):
        """
        Initialize interruption handler.

        Args:
            config: Interruption configuration
        """
        self.config = config or InterruptionConfig()

        # State
        self._is_monitoring = False
        self._is_playing = False
        self._last_interrupt_time = 0.0
        self._in_cooldown = False

        # Audio monitoring
        self._audio_buffer = []
        self._detection_samples = int(
            self.config.detection_window_ms * 16  # Assume 16kHz
        )

        # Callbacks
        self._interrupt_callbacks = []

        # Statistics
        self._total_interrupts = 0
        self._false_positive_count = 0
        self._true_positive_count = 0

        logger.info(
            f"Initialized InterruptionHandler: "
            f"sensitivity={self.config.sensitivity:.2f}, "
            f"threshold={self.config.speech_threshold:.3f}"
        )

    def start_monitoring(self) -> None:
        """Start monitoring for interruptions."""
        if self._is_monitoring:
            logger.warning("Already monitoring")
            return

        self._is_monitoring = True
        self._audio_buffer.clear()
        logger.info("Started interruption monitoring")

    def stop_monitoring(self) -> None:
        """Stop monitoring for interruptions."""
        if not self._is_monitoring:
            return

        self._is_monitoring = False
        self._audio_buffer.clear()
        logger.info("Stopped interruption monitoring")

    def set_playback_state(self, is_playing: bool) -> None:
        """
        Set current playback state.

        Args:
            is_playing: True if TTS is playing, False otherwise
        """
        self._is_playing = is_playing

        if is_playing:
            logger.debug("TTS playback started - monitoring for interruptions")
        else:
            logger.debug("TTS playback stopped")

    def detect_interruption(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000
    ) -> Optional[InterruptionEvent]:
        """
        Detect if current audio contains an interruption.

        Args:
            audio_data: Audio samples to analyze
            sample_rate: Audio sample rate (Hz)

        Returns:
            InterruptionEvent if interruption detected, None otherwise
        """
        if not self._is_monitoring or not self._is_playing:
            return None

        # Check cooldown
        if self._in_cooldown:
            time_since_interrupt = time.time() - self._last_interrupt_time
            if time_since_interrupt < (self.config.cooldown_time_ms / 1000.0):
                return None
            else:
                self._in_cooldown = False

        # Ensure audio is float32 and normalized
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        if np.abs(audio_data).max() > 1.0:
            audio_data = audio_data / 32768.0

        # Add to buffer
        self._audio_buffer.extend(audio_data.tolist())

        # Keep only detection window
        if len(self._audio_buffer) > self._detection_samples:
            self._audio_buffer = self._audio_buffer[-self._detection_samples:]

        # Need minimum samples
        min_samples = int(self.config.min_speech_duration_ms * sample_rate / 1000)
        if len(self._audio_buffer) < min_samples:
            return None

        # Analyze audio for speech
        analysis_window = np.array(self._audio_buffer[-min_samples:], dtype=np.float32)

        # Calculate audio level
        audio_level = self._calculate_rms(analysis_window)

        # Check if exceeds threshold
        adjusted_threshold = self._adjust_threshold()

        if audio_level < adjusted_threshold:
            return None

        # Check for sustained speech if required
        if self.config.require_sustained_speech:
            is_sustained = self._check_sustained_speech(analysis_window, sample_rate)
            if not is_sustained:
                return None

        # Calculate confidence
        confidence = self._calculate_confidence(audio_level, adjusted_threshold)

        # Check confidence threshold
        if confidence < self.config.confidence_threshold:
            return None

        # Valid interruption detected!
        event = InterruptionEvent(
            interrupt_type=InterruptionType.SPEECH,
            timestamp=time.time(),
            audio_level=audio_level,
            confidence=confidence
        )

        # Update state
        self._last_interrupt_time = time.time()
        self._in_cooldown = True
        self._total_interrupts += 1

        logger.info(
            f"Interruption detected: level={audio_level:.3f}, "
            f"confidence={confidence:.2f}"
        )

        return event

    def pause_playback(self) -> bool:
        """
        Pause current TTS playback.

        Returns:
            True if playback was paused, False if not playing
        """
        if not self._is_playing:
            logger.debug("No playback to pause")
            return False

        self._is_playing = False
        logger.info("Paused TTS playback due to interruption")

        # Trigger callbacks
        self._trigger_callbacks(InterruptionEvent(
            interrupt_type=InterruptionType.SPEECH,
            timestamp=time.time(),
            audio_level=0.0,
            confidence=1.0
        ))

        return True

    def resume_playback(self) -> bool:
        """
        Resume paused playback.

        Returns:
            True if playback was resumed, False if already playing
        """
        if self._is_playing:
            logger.debug("Already playing")
            return False

        self._is_playing = True
        logger.info("Resumed TTS playback")
        return True

    def cancel_response(self) -> None:
        """
        Cancel current response completely.

        Called when interruption should abort the response
        rather than just pause it.
        """
        self._is_playing = False
        self._audio_buffer.clear()
        logger.info("Cancelled current response")

    def on_interrupt(self, callback: Callable[[InterruptionEvent], None]) -> None:
        """
        Register callback for interruptions.

        Args:
            callback: Function to call when interruption detected
        """
        if callback not in self._interrupt_callbacks:
            self._interrupt_callbacks.append(callback)
            logger.debug(f"Registered interrupt callback: {callback.__name__}")

    def set_sensitivity(self, sensitivity: float) -> None:
        """
        Adjust interruption sensitivity.

        Args:
            sensitivity: Sensitivity level (0.0-1.0)
                        0.0 = less sensitive (fewer false positives)
                        1.0 = more sensitive (catches all interruptions)
        """
        if not 0.0 <= sensitivity <= 1.0:
            raise ValueError("Sensitivity must be between 0.0 and 1.0")

        self.config.sensitivity = sensitivity
        logger.info(f"Set interruption sensitivity to {sensitivity:.2f}")

    def get_statistics(self) -> dict:
        """
        Get interruption statistics.

        Returns:
            Dictionary of statistics
        """
        total = self._true_positive_count + self._false_positive_count
        accuracy = (
            self._true_positive_count / total if total > 0 else 0.0
        )

        return {
            "total_interrupts": self._total_interrupts,
            "true_positives": self._true_positive_count,
            "false_positives": self._false_positive_count,
            "accuracy": accuracy,
            "is_monitoring": self._is_monitoring,
            "is_playing": self._is_playing,
            "in_cooldown": self._in_cooldown
        }

    def mark_true_positive(self) -> None:
        """Mark last interruption as true positive (valid)."""
        self._true_positive_count += 1
        logger.debug("Marked interruption as true positive")

    def mark_false_positive(self) -> None:
        """Mark last interruption as false positive (invalid)."""
        self._false_positive_count += 1
        logger.debug("Marked interruption as false positive")

    def reset_statistics(self) -> None:
        """Reset interruption statistics."""
        self._total_interrupts = 0
        self._false_positive_count = 0
        self._true_positive_count = 0
        logger.info("Reset interruption statistics")

    def _adjust_threshold(self) -> float:
        """
        Adjust detection threshold based on sensitivity.

        Returns:
            Adjusted threshold
        """
        # Higher sensitivity = lower threshold
        # 0.0 sensitivity -> 2x base threshold (conservative)
        # 0.5 sensitivity -> 1x base threshold (balanced)
        # 1.0 sensitivity -> 0.5x base threshold (aggressive)

        multiplier = 2.0 - (self.config.sensitivity * 1.5)
        return self.config.speech_threshold * multiplier

    def _calculate_confidence(self, audio_level: float, threshold: float) -> float:
        """
        Calculate confidence score for interruption.

        Args:
            audio_level: Measured audio level
            threshold: Detection threshold

        Returns:
            Confidence score (0.0-1.0)
        """
        # Simple ratio-based confidence
        # Could be enhanced with more sophisticated features

        if threshold == 0:
            return 1.0

        ratio = audio_level / threshold

        # Map ratio to confidence
        # ratio=1.0 -> confidence=0.5
        # ratio=2.0 -> confidence=0.8
        # ratio=3.0+ -> confidence=1.0

        confidence = min(0.5 + (ratio - 1.0) * 0.3, 1.0)
        return float(confidence)

    def _check_sustained_speech(
        self,
        audio_data: np.ndarray,
        sample_rate: int
    ) -> bool:
        """
        Check if audio contains sustained speech (not just spike).

        Args:
            audio_data: Audio samples
            sample_rate: Sample rate (Hz)

        Returns:
            True if sustained speech detected
        """
        # Split into small frames and check consistency
        frame_size = int(0.03 * sample_rate)  # 30ms frames

        if len(audio_data) < frame_size * 2:
            return False

        # Calculate RMS for each frame
        frame_rms = []
        for i in range(0, len(audio_data) - frame_size, frame_size):
            frame = audio_data[i:i + frame_size]
            rms = self._calculate_rms(frame)
            frame_rms.append(rms)

        if not frame_rms:
            return False

        # Check how many frames exceed threshold
        threshold = self._adjust_threshold()
        above_threshold = sum(1 for rms in frame_rms if rms >= threshold)

        # Require at least 60% of frames to be above threshold
        ratio = above_threshold / len(frame_rms)
        return ratio >= 0.6

    def _calculate_rms(self, samples: np.ndarray) -> float:
        """
        Calculate RMS (Root Mean Square) of audio.

        Args:
            samples: Audio samples

        Returns:
            RMS value
        """
        if len(samples) == 0:
            return 0.0

        return float(np.sqrt(np.mean(samples ** 2)))

    def _trigger_callbacks(self, event: InterruptionEvent) -> None:
        """
        Trigger registered callbacks.

        Args:
            event: Interruption event
        """
        for callback in self._interrupt_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in interrupt callback {callback.__name__}: {e}")

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"InterruptionHandler("
            f"monitoring={self._is_monitoring}, "
            f"playing={self._is_playing}, "
            f"sensitivity={self.config.sensitivity:.2f}"
            f")"
        )


class AsyncInterruptionHandler:
    """
    Async wrapper for InterruptionHandler.

    Provides async event notifications for interruptions.
    """

    def __init__(self, config: Optional[InterruptionConfig] = None):
        """
        Initialize async interruption handler.

        Args:
            config: Interruption configuration
        """
        self._handler = InterruptionHandler(config)
        self._interrupt_queue: asyncio.Queue = asyncio.Queue()
        self._monitoring_task: Optional[asyncio.Task] = None
        self._is_monitoring = False

    def start_monitoring(self) -> None:
        """Start monitoring for interruptions."""
        self._handler.start_monitoring()
        self._is_monitoring = True

    def stop_monitoring(self) -> None:
        """Stop monitoring for interruptions."""
        self._handler.stop_monitoring()
        self._is_monitoring = False

    def set_playback_state(self, is_playing: bool) -> None:
        """Set playback state."""
        self._handler.set_playback_state(is_playing)

    async def detect_interruption(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000
    ) -> Optional[InterruptionEvent]:
        """
        Detect interruption (async).

        Args:
            audio_data: Audio samples
            sample_rate: Sample rate (Hz)

        Returns:
            InterruptionEvent if detected
        """
        event = await asyncio.to_thread(
            self._handler.detect_interruption,
            audio_data,
            sample_rate
        )

        if event:
            await self._interrupt_queue.put(event)

        return event

    async def wait_for_interrupt(
        self,
        timeout: Optional[float] = None
    ) -> Optional[InterruptionEvent]:
        """
        Wait for next interruption.

        Args:
            timeout: Maximum time to wait (seconds)

        Returns:
            InterruptionEvent or None on timeout
        """
        try:
            if timeout:
                event = await asyncio.wait_for(
                    self._interrupt_queue.get(),
                    timeout=timeout
                )
            else:
                event = await self._interrupt_queue.get()

            return event

        except asyncio.TimeoutError:
            return None

    async def pause_playback(self) -> bool:
        """Pause playback (async)."""
        return await asyncio.to_thread(self._handler.pause_playback)

    async def resume_playback(self) -> bool:
        """Resume playback (async)."""
        return await asyncio.to_thread(self._handler.resume_playback)

    async def cancel_response(self) -> None:
        """Cancel response (async)."""
        await asyncio.to_thread(self._handler.cancel_response)

    def on_interrupt(self, callback: Callable[[InterruptionEvent], None]) -> None:
        """Register interrupt callback."""
        self._handler.on_interrupt(callback)

    def set_sensitivity(self, sensitivity: float) -> None:
        """Set sensitivity."""
        self._handler.set_sensitivity(sensitivity)

    def get_statistics(self) -> dict:
        """Get statistics."""
        return self._handler.get_statistics()

    def mark_true_positive(self) -> None:
        """Mark as true positive."""
        self._handler.mark_true_positive()

    def mark_false_positive(self) -> None:
        """Mark as false positive."""
        self._handler.mark_false_positive()

    def reset_statistics(self) -> None:
        """Reset statistics."""
        self._handler.reset_statistics()

    def __repr__(self) -> str:
        """String representation."""
        return repr(self._handler)
