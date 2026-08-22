"""
Audio Buffer for EduLens Voice Pipeline

Provides efficient ring buffer for continuous audio streaming with:
- Circular buffer implementation
- Automatic silence detection
- Speech segment extraction
- Audio level monitoring
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BufferConfig:
    """Audio buffer configuration."""

    max_duration: float = 30.0  # Maximum buffer duration (seconds)
    sample_rate: int = 16000  # Sample rate (Hz)
    silence_threshold: float = 0.02  # RMS threshold for silence
    silence_duration: float = 0.5  # Duration of silence to detect end (seconds)
    pre_speech_padding: float = 0.3  # Pre-speech padding (seconds)
    post_speech_padding: float = 0.3  # Post-speech padding (seconds)


@dataclass
class SpeechSegment:
    """Extracted speech segment with metadata."""

    audio_data: np.ndarray
    start_time: float
    end_time: float
    duration: float
    rms_level: float
    is_speech: bool

    @property
    def num_samples(self) -> int:
        """Get number of audio samples."""
        return len(self.audio_data)


class AudioBuffer:
    """
    Ring buffer for continuous audio streaming.

    Provides efficient buffering with automatic speech detection,
    silence detection, and segment extraction.
    """

    def __init__(self, config: Optional[BufferConfig] = None):
        """
        Initialize audio buffer.

        Args:
            config: Buffer configuration
        """
        self.config = config or BufferConfig()

        # Calculate buffer size
        self.max_samples = int(self.config.max_duration * self.config.sample_rate)
        self.silence_samples = int(self.config.silence_duration * self.config.sample_rate)
        self.pre_pad_samples = int(self.config.pre_speech_padding * self.config.sample_rate)
        self.post_pad_samples = int(self.config.post_speech_padding * self.config.sample_rate)

        # Ring buffer using deque
        self.buffer: deque = deque(maxlen=self.max_samples)
        self.timestamps: deque = deque(maxlen=self.max_samples)

        # State tracking
        self.speech_started = False
        self.speech_start_idx = 0
        self.silence_counter = 0
        self.total_samples_received = 0

        # Statistics
        self._current_level = 0.0
        self._peak_level = 0.0
        self._start_time = time.time()

        logger.info(
            f"Initialized AudioBuffer: "
            f"max_duration={self.config.max_duration}s, "
            f"buffer_size={self.max_samples} samples"
        )

    def add_samples(self, samples: np.ndarray) -> None:
        """
        Add audio samples to buffer.

        Args:
            samples: Audio samples (float32, mono, -1.0 to 1.0)
        """
        if samples.size == 0:
            return

        # Ensure correct format
        if samples.dtype != np.float32:
            samples = samples.astype(np.float32)

        # Normalize if needed
        if np.abs(samples).max() > 1.0:
            samples = samples / 32768.0  # Assume int16 range

        # Add to buffer
        current_time = time.time()
        for sample in samples:
            self.buffer.append(sample)
            self.timestamps.append(current_time)

        self.total_samples_received += len(samples)

        # Update statistics
        self._update_statistics(samples)

    def get_speech_segment(self, timeout: float = 0.0) -> Optional[SpeechSegment]:
        """
        Extract speech segment from buffer.

        Automatically detects speech boundaries using silence detection.

        Args:
            timeout: Maximum time to wait for speech end (seconds)
                    0.0 = return immediately

        Returns:
            SpeechSegment if speech detected and ended, None otherwise
        """
        if len(self.buffer) < self.silence_samples:
            return None

        # Convert buffer to numpy array for analysis
        audio_data = np.array(self.buffer, dtype=np.float32)

        # Detect speech boundaries
        speech_start, speech_end, is_speech = self._detect_speech_boundaries(audio_data)

        if not is_speech:
            return None

        # Check if speech has ended (sufficient silence after)
        if speech_end is None or speech_end >= len(audio_data) - self.silence_samples:
            # Speech still ongoing
            if timeout <= 0.0:
                return None

            # Wait for speech to end
            # In real implementation, would use event-based waiting
            return None

        # Extract speech segment with padding
        padded_start = max(0, speech_start - self.pre_pad_samples)
        padded_end = min(len(audio_data), speech_end + self.post_pad_samples)

        segment_audio = audio_data[padded_start:padded_end]

        # Calculate timestamps
        if self.timestamps:
            start_time = (
                self.timestamps[padded_start]
                if padded_start < len(self.timestamps)
                else time.time()
            )
            end_time = (
                self.timestamps[padded_end - 1]
                if padded_end <= len(self.timestamps)
                else time.time()
            )
        else:
            start_time = time.time()
            end_time = start_time

        # Calculate RMS level
        rms_level = self._calculate_rms(segment_audio)

        return SpeechSegment(
            audio_data=segment_audio,
            start_time=start_time,
            end_time=end_time,
            duration=(padded_end - padded_start) / self.config.sample_rate,
            rms_level=rms_level,
            is_speech=True,
        )

    def get_latest(self, duration: float) -> np.ndarray:
        """
        Get latest audio from buffer.

        Args:
            duration: Duration to retrieve (seconds)

        Returns:
            Audio samples (most recent)
        """
        num_samples = int(duration * self.config.sample_rate)
        num_samples = min(num_samples, len(self.buffer))

        if num_samples == 0:
            return np.array([], dtype=np.float32)

        # Get last N samples
        audio_data = np.array(list(self.buffer)[-num_samples:], dtype=np.float32)
        return audio_data

    def get_all(self) -> np.ndarray:
        """
        Get all audio from buffer.

        Returns:
            All buffered audio samples
        """
        return np.array(self.buffer, dtype=np.float32)

    def clear(self) -> None:
        """Clear buffer and reset state."""
        self.buffer.clear()
        self.timestamps.clear()
        self.speech_started = False
        self.speech_start_idx = 0
        self.silence_counter = 0
        self._current_level = 0.0
        self._peak_level = 0.0
        self._start_time = time.time()

        logger.debug("Buffer cleared")

    def get_level(self) -> float:
        """
        Get current audio level (RMS).

        Returns:
            Current RMS level (0.0 to 1.0)
        """
        return self._current_level

    def get_peak_level(self) -> float:
        """
        Get peak audio level since last reset.

        Returns:
            Peak RMS level (0.0 to 1.0)
        """
        return self._peak_level

    def is_silent(self) -> bool:
        """
        Check if current audio is silent.

        Returns:
            True if silent, False otherwise
        """
        return self._current_level < self.config.silence_threshold

    def has_speech(self) -> bool:
        """
        Check if buffer contains speech.

        Returns:
            True if speech detected, False otherwise
        """
        if len(self.buffer) < self.silence_samples:
            return False

        audio_data = np.array(list(self.buffer)[-self.silence_samples :], dtype=np.float32)
        rms = self._calculate_rms(audio_data)
        return rms >= self.config.silence_threshold

    def get_buffer_duration(self) -> float:
        """
        Get current buffer duration.

        Returns:
            Duration in seconds
        """
        return len(self.buffer) / self.config.sample_rate

    def get_fill_percentage(self) -> float:
        """
        Get buffer fill percentage.

        Returns:
            Fill percentage (0.0 to 1.0)
        """
        return len(self.buffer) / self.max_samples

    def _detect_speech_boundaries(self, audio_data: np.ndarray) -> Tuple[int, Optional[int], bool]:
        """
        Detect speech start and end boundaries.

        Args:
            audio_data: Audio samples

        Returns:
            Tuple of (start_idx, end_idx, is_speech)
            end_idx is None if speech is still ongoing
        """
        # Calculate RMS for each frame
        frame_length = int(0.02 * self.config.sample_rate)  # 20ms frames
        hop_length = int(0.01 * self.config.sample_rate)  # 10ms hop

        if len(audio_data) < frame_length:
            return 0, None, False

        # Calculate frame energies
        energies = []
        for i in range(0, len(audio_data) - frame_length, hop_length):
            frame = audio_data[i : i + frame_length]
            rms = self._calculate_rms(frame)
            energies.append(rms)

        energies = np.array(energies)

        # Detect speech frames
        speech_frames = energies >= self.config.silence_threshold

        if not speech_frames.any():
            return 0, None, False

        # Find speech boundaries
        speech_indices = np.where(speech_frames)[0]
        start_frame = speech_indices[0]
        end_frame = speech_indices[-1]

        # Convert frame indices to sample indices
        start_idx = start_frame * hop_length
        end_idx = end_frame * hop_length + frame_length

        # Check if speech has ended (silence after last speech frame)
        frames_after = len(energies) - end_frame - 1
        silence_frames_needed = int(self.config.silence_duration / 0.01)  # 10ms per frame

        if frames_after >= silence_frames_needed:
            # Check if trailing frames are silent
            trailing_energies = energies[end_frame + 1 : end_frame + 1 + silence_frames_needed]
            if np.all(trailing_energies < self.config.silence_threshold):
                # Speech has ended
                return start_idx, end_idx, True

        # Speech still ongoing
        return start_idx, None, True

    def _calculate_rms(self, samples: np.ndarray) -> float:
        """
        Calculate RMS (Root Mean Square) of audio samples.

        Args:
            samples: Audio samples

        Returns:
            RMS value
        """
        if len(samples) == 0:
            return 0.0

        return float(np.sqrt(np.mean(samples**2)))

    def _update_statistics(self, samples: np.ndarray) -> None:
        """
        Update buffer statistics.

        Args:
            samples: Latest audio samples
        """
        # Calculate current level
        self._current_level = self._calculate_rms(samples)

        # Update peak level
        if self._current_level > self._peak_level:
            self._peak_level = self._current_level

    def get_statistics(self) -> dict:
        """
        Get buffer statistics.

        Returns:
            Dictionary of statistics
        """
        return {
            "buffer_duration": self.get_buffer_duration(),
            "fill_percentage": self.get_fill_percentage(),
            "current_level": self._current_level,
            "peak_level": self._peak_level,
            "is_silent": self.is_silent(),
            "has_speech": self.has_speech(),
            "total_samples": self.total_samples_received,
            "uptime": time.time() - self._start_time,
        }

    def reset_peak_level(self) -> None:
        """Reset peak level counter."""
        self._peak_level = self._current_level

    def __len__(self) -> int:
        """Get number of samples in buffer."""
        return len(self.buffer)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"AudioBuffer(duration={self.get_buffer_duration():.2f}s, "
            f"fill={self.get_fill_percentage() * 100:.1f}%, "
            f"level={self._current_level:.3f})"
        )


class AsyncAudioBuffer:
    """
    Async wrapper for AudioBuffer.

    Provides event-based notifications for speech detection.
    """

    def __init__(self, config: Optional[BufferConfig] = None):
        """
        Initialize async audio buffer.

        Args:
            config: Buffer configuration
        """
        self.buffer = AudioBuffer(config)
        self._speech_event = asyncio.Event()
        self._segment_queue: asyncio.Queue = asyncio.Queue()
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

    async def add_samples(self, samples: np.ndarray) -> None:
        """
        Add audio samples (async).

        Args:
            samples: Audio samples
        """
        await asyncio.to_thread(self.buffer.add_samples, samples)

    async def get_speech_segment(self, timeout: float = 5.0) -> Optional[SpeechSegment]:
        """
        Wait for and extract speech segment.

        Args:
            timeout: Maximum time to wait (seconds)

        Returns:
            SpeechSegment if available, None on timeout
        """
        try:
            segment = await asyncio.wait_for(self._segment_queue.get(), timeout=timeout)
            return segment
        except asyncio.TimeoutError:
            return None

    async def start_monitoring(self, check_interval: float = 0.1) -> None:
        """
        Start automatic speech detection.

        Args:
            check_interval: How often to check for speech (seconds)
        """
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_speech(check_interval))
        logger.info("Started audio buffer monitoring")

    async def stop_monitoring(self) -> None:
        """Stop automatic speech detection."""
        if not self._monitoring:
            return

        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

        logger.info("Stopped audio buffer monitoring")

    async def _monitor_speech(self, check_interval: float) -> None:
        """
        Monitor buffer for speech segments.

        Args:
            check_interval: Check interval in seconds
        """
        while self._monitoring:
            try:
                # Check for speech segment
                segment = await asyncio.to_thread(self.buffer.get_speech_segment, timeout=0.0)

                if segment:
                    await self._segment_queue.put(segment)
                    self._speech_event.set()

                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.error(f"Error monitoring speech: {e}")
                await asyncio.sleep(check_interval)

    async def wait_for_speech(self, timeout: float = 30.0) -> bool:
        """
        Wait for speech to be detected.

        Args:
            timeout: Maximum time to wait (seconds)

        Returns:
            True if speech detected, False on timeout
        """
        try:
            await asyncio.wait_for(self._speech_event.wait(), timeout=timeout)
            self._speech_event.clear()
            return True
        except asyncio.TimeoutError:
            return False

    def clear(self) -> None:
        """Clear buffer."""
        self.buffer.clear()
        self._speech_event.clear()
        # Clear queue
        while not self._segment_queue.empty():
            try:
                self._segment_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    def get_level(self) -> float:
        """Get current audio level."""
        return self.buffer.get_level()

    def is_silent(self) -> bool:
        """Check if silent."""
        return self.buffer.is_silent()

    def has_speech(self) -> bool:
        """Check if has speech."""
        return self.buffer.has_speech()

    def get_statistics(self) -> dict:
        """Get buffer statistics."""
        return self.buffer.get_statistics()
