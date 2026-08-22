"""
Audio Capture Utilities for EduLens Wake Word Detection

This module provides real-time audio capture functionality optimized for
wake word detection on edge devices. Includes microphone streaming,
buffering, and audio format conversion utilities.
"""

import asyncio
import logging
import threading
from collections import deque
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import pyaudio

logger = logging.getLogger(__name__)


@dataclass
class AudioConfig:
    """Audio configuration parameters."""

    sample_rate: int = 16000  # Hz - standard for speech recognition
    channels: int = 1  # Mono
    chunk_size: int = 1024  # Samples per frame
    format: int = pyaudio.paInt16  # 16-bit PCM
    buffer_duration: float = 1.5  # Seconds to buffer for detection

    @property
    def bytes_per_sample(self) -> int:
        """Get bytes per sample based on format."""
        return pyaudio.get_sample_size(self.format)

    @property
    def buffer_size(self) -> int:
        """Calculate buffer size in samples."""
        return int(self.sample_rate * self.buffer_duration)

    @property
    def chunk_duration_ms(self) -> float:
        """Get chunk duration in milliseconds."""
        return (self.chunk_size / self.sample_rate) * 1000


class AudioBuffer:
    """
    Thread-safe circular buffer for windowed audio processing.

    Optimized for real-time audio streaming with efficient memory usage.
    """

    def __init__(self, max_size: int, sample_rate: int = 16000):
        """
        Initialize audio buffer.

        Args:
            max_size: Maximum number of samples to store
            sample_rate: Audio sample rate in Hz
        """
        self.max_size = max_size
        self.sample_rate = sample_rate
        self._buffer = deque(maxlen=max_size)
        self._lock = threading.Lock()
        self._total_samples = 0

    def append(self, data: np.ndarray) -> None:
        """
        Append audio data to buffer.

        Args:
            data: Audio samples as numpy array
        """
        with self._lock:
            if len(data.shape) > 1:
                data = data.flatten()

            for sample in data:
                self._buffer.append(sample)

            self._total_samples += len(data)

    def get_window(self, duration_seconds: float) -> np.ndarray:
        """
        Get most recent audio window.

        Args:
            duration_seconds: Duration of window to retrieve

        Returns:
            Numpy array of audio samples
        """
        with self._lock:
            num_samples = min(int(duration_seconds * self.sample_rate), len(self._buffer))

            if num_samples == 0:
                return np.array([], dtype=np.float32)

            # Get last num_samples from buffer
            window = np.array(list(self._buffer)[-num_samples:], dtype=np.float32)
            return window

    def get_all(self) -> np.ndarray:
        """
        Get all buffered audio data.

        Returns:
            Numpy array of all samples in buffer
        """
        with self._lock:
            return np.array(list(self._buffer), dtype=np.float32)

    def clear(self) -> None:
        """Clear the buffer."""
        with self._lock:
            self._buffer.clear()
            self._total_samples = 0

    @property
    def size(self) -> int:
        """Get current number of samples in buffer."""
        return len(self._buffer)

    @property
    def duration_seconds(self) -> float:
        """Get current buffer duration in seconds."""
        return self.size / self.sample_rate

    @property
    def total_samples(self) -> int:
        """Get total number of samples processed."""
        return self._total_samples


class MicrophoneStream:
    """
    Real-time microphone audio stream with callback support.

    Optimized for low-latency wake word detection with automatic
    gain control and noise handling.
    """

    def __init__(
        self,
        config: Optional[AudioConfig] = None,
        callback: Optional[Callable[[np.ndarray], None]] = None,
    ):
        """
        Initialize microphone stream.

        Args:
            config: Audio configuration parameters
            callback: Optional callback function for audio chunks
        """
        self.config = config or AudioConfig()
        self.callback = callback

        self._pyaudio = None
        self._stream = None
        self._is_streaming = False
        self._lock = threading.Lock()

        self.buffer = AudioBuffer(
            max_size=self.config.buffer_size, sample_rate=self.config.sample_rate
        )

        logger.info(
            f"Initialized MicrophoneStream: "
            f"{self.config.sample_rate}Hz, "
            f"chunk={self.config.chunk_size}, "
            f"buffer={self.config.buffer_duration}s"
        )

    def start(self) -> None:
        """Start the audio stream."""
        with self._lock:
            if self._is_streaming:
                logger.warning("Stream already started")
                return

            try:
                self._pyaudio = pyaudio.PyAudio()

                # Find best input device
                device_index = self._find_best_input_device()

                self._stream = self._pyaudio.open(
                    format=self.config.format,
                    channels=self.config.channels,
                    rate=self.config.sample_rate,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=self.config.chunk_size,
                    stream_callback=self._audio_callback,
                )

                self._is_streaming = True
                self._stream.start_stream()

                logger.info(f"Started audio stream (device: {device_index})")

            except Exception as e:
                logger.error(f"Failed to start audio stream: {e}")
                self._cleanup()
                raise

    def stop(self) -> None:
        """Stop the audio stream."""
        with self._lock:
            if not self._is_streaming:
                return

            self._is_streaming = False
            self._cleanup()
            logger.info("Stopped audio stream")

    def _audio_callback(
        self, in_data: bytes, frame_count: int, time_info: dict, status_flags: int
    ) -> tuple:
        """
        PyAudio callback for audio data.

        Args:
            in_data: Raw audio bytes
            frame_count: Number of frames
            time_info: Timing information
            status_flags: Stream status flags

        Returns:
            Tuple of (None, pyaudio.paContinue)
        """
        if status_flags:
            logger.warning(f"Audio stream status: {status_flags}")

        try:
            # Convert bytes to numpy array
            audio_data = np.frombuffer(in_data, dtype=np.int16)

            # Normalize to float32 range [-1.0, 1.0]
            audio_data = audio_data.astype(np.float32) / 32768.0

            # Add to buffer
            self.buffer.append(audio_data)

            # Call user callback if provided
            if self.callback:
                self.callback(audio_data)

        except Exception as e:
            logger.error(f"Error in audio callback: {e}")

        return (None, pyaudio.paContinue)

    def _find_best_input_device(self) -> Optional[int]:
        """
        Find the best input device for recording.

        Returns:
            Device index or None for default
        """
        try:
            default_device = self._pyaudio.get_default_input_device_info()
            logger.info(f"Using default input device: {default_device['name']}")
            return default_device["index"]
        except Exception as e:
            logger.warning(f"Could not get default input device: {e}")
            return None

    def _cleanup(self) -> None:
        """Clean up audio resources."""
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception as e:
                logger.error(f"Error closing stream: {e}")
            finally:
                self._stream = None

        if self._pyaudio:
            try:
                self._pyaudio.terminate()
            except Exception as e:
                logger.error(f"Error terminating PyAudio: {e}")
            finally:
                self._pyaudio = None

    @property
    def is_streaming(self) -> bool:
        """Check if stream is active."""
        return self._is_streaming

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False


class AsyncMicrophoneStream:
    """
    Async wrapper for MicrophoneStream with queue-based processing.

    Enables async/await patterns for audio processing pipelines.
    """

    def __init__(self, config: Optional[AudioConfig] = None, queue_size: int = 100):
        """
        Initialize async microphone stream.

        Args:
            config: Audio configuration parameters
            queue_size: Maximum number of chunks to queue
        """
        self.config = config or AudioConfig()
        self._queue = asyncio.Queue(maxsize=queue_size)
        self._stream = MicrophoneStream(config=self.config, callback=self._enqueue_audio)
        self._loop = None

    def _enqueue_audio(self, audio_data: np.ndarray) -> None:
        """
        Enqueue audio data for async processing.

        Args:
            audio_data: Audio samples
        """
        if self._loop and not self._queue.full():
            asyncio.run_coroutine_threadsafe(self._queue.put(audio_data), self._loop)

    async def start(self) -> None:
        """Start the audio stream."""
        self._loop = asyncio.get_event_loop()
        self._stream.start()

    async def stop(self) -> None:
        """Stop the audio stream."""
        self._stream.stop()

    async def read_chunk(self) -> np.ndarray:
        """
        Read next audio chunk.

        Returns:
            Audio data as numpy array
        """
        return await self._queue.get()

    def __aiter__(self):
        """Async iterator support."""
        return self

    async def __anext__(self) -> np.ndarray:
        """Get next audio chunk."""
        if not self._stream.is_streaming:
            raise StopAsyncIteration
        return await self.read_chunk()


def convert_audio_format(audio_data: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    """
    Convert audio sample rate using linear interpolation.

    Args:
        audio_data: Source audio data
        source_rate: Source sample rate
        target_rate: Target sample rate

    Returns:
        Resampled audio data
    """
    if source_rate == target_rate:
        return audio_data

    duration = len(audio_data) / source_rate
    target_samples = int(duration * target_rate)

    # Linear interpolation for resampling
    source_indices = np.linspace(0, len(audio_data) - 1, target_samples)
    resampled = np.interp(source_indices, np.arange(len(audio_data)), audio_data)

    return resampled.astype(np.float32)


def normalize_audio(audio_data: np.ndarray, target_db: float = -20.0) -> np.ndarray:
    """
    Normalize audio to target dB level.

    Args:
        audio_data: Audio data to normalize
        target_db: Target level in dB

    Returns:
        Normalized audio data
    """
    if len(audio_data) == 0:
        return audio_data

    # Calculate current RMS
    rms = np.sqrt(np.mean(audio_data**2))

    if rms > 0:
        # Calculate scaling factor
        current_db = 20 * np.log10(rms)
        scale = 10 ** ((target_db - current_db) / 20)

        # Apply scaling with clipping
        normalized = np.clip(audio_data * scale, -1.0, 1.0)
        return normalized

    return audio_data


def apply_pre_emphasis(audio_data: np.ndarray, coef: float = 0.97) -> np.ndarray:
    """
    Apply pre-emphasis filter to enhance high frequencies.

    Common preprocessing step for speech recognition.

    Args:
        audio_data: Audio data
        coef: Pre-emphasis coefficient

    Returns:
        Filtered audio data
    """
    if len(audio_data) == 0:
        return audio_data

    emphasized = np.append(audio_data[0], audio_data[1:] - coef * audio_data[:-1])
    return emphasized.astype(np.float32)
