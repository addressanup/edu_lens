"""
Unified Audio Pipeline for EduLens

Integrates wake word detection, ASR, and TTS into a seamless
voice interaction pipeline with state machine management.

State Flow:
IDLE → WAKE_DETECTED → LISTENING → PROCESSING → SPEAKING → IDLE

Features:
- Seamless state transitions
- Barge-in support during TTS
- Sub-2-second total latency
- Event-driven callbacks
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, Optional

import numpy as np

from .audio_buffer import AsyncAudioBuffer, BufferConfig, SpeechSegment
from .audio_capture import AudioConfig, MicrophoneStream
from .interruption_handler import (
    AsyncInterruptionHandler,
    InterruptionConfig,
    InterruptionEvent,
    InterruptionType,
)
from .latency_monitor import AsyncLatencyMonitor, LatencyMetrics, PipelineStage
from .speech_recognizer import SpeechConfig, SpeechRecognizer, TranscriptionResult
from .tts_engine import AudioOutput, TTSConfig, TTSEngine
from .wake_word_engine import AsyncWakeWordDetector, DetectionResult

logger = logging.getLogger(__name__)


class PipelineState(Enum):
    """Audio pipeline states."""

    IDLE = "idle"  # Waiting for wake word
    WAKE_DETECTED = "wake_detected"  # Wake word detected, preparing to listen
    LISTENING = "listening"  # Actively listening for user speech
    PROCESSING = "processing"  # Processing speech (ASR + NLU)
    SPEAKING = "speaking"  # Playing TTS response
    ERROR = "error"  # Error state
    STOPPED = "stopped"  # Pipeline stopped


@dataclass
class PipelineConfig:
    """Configuration for audio pipeline."""

    # Audio settings
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024

    # Wake word settings
    wake_word_sensitivity: float = 0.5
    wake_word_model_path: Optional[str] = None

    # ASR settings
    asr_model_size: str = "base"
    asr_language: str = "en"

    # TTS settings
    tts_backend: str = "pyttsx3"
    tts_voice_id: Optional[str] = None
    tts_speed: float = 1.0

    # Timing settings
    listening_timeout: float = 5.0  # Max time to wait for speech
    silence_timeout: float = 1.5  # Silence duration to end listening
    latency_threshold: float = 2000.0  # Latency threshold (ms)

    # Barge-in settings
    enable_barge_in: bool = True
    barge_in_sensitivity: float = 0.7

    # Buffer settings
    buffer_duration: float = 30.0

    @classmethod
    def from_yaml(cls, config_path: Path) -> "PipelineConfig":
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to config file

        Returns:
            PipelineConfig instance
        """
        import yaml

        with open(config_path, "r") as f:
            config_dict = yaml.safe_load(f)

        return cls(**config_dict)


@dataclass
class PipelineEvent:
    """Event from pipeline state change."""

    state: PipelineState
    previous_state: PipelineState
    timestamp: float
    session_id: str
    data: Optional[Dict[str, Any]] = None


class AudioPipeline:
    """
    Unified audio pipeline for voice interaction.

    Integrates wake word detection, ASR, and TTS with seamless
    state transitions and barge-in support.
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        Initialize audio pipeline.

        Args:
            config: Pipeline configuration
        """
        self.config = config or PipelineConfig()

        # State
        self._state = PipelineState.IDLE
        self._previous_state = PipelineState.IDLE
        self._is_running = False
        self._current_session_id: Optional[str] = None

        # Components
        self._wake_detector: Optional[AsyncWakeWordDetector] = None
        self._speech_recognizer: Optional[SpeechRecognizer] = None
        self._tts_engine: Optional[TTSEngine] = None
        self._audio_buffer: Optional[AsyncAudioBuffer] = None
        self._interruption_handler: Optional[AsyncInterruptionHandler] = None
        self._latency_monitor: Optional[AsyncLatencyMonitor] = None

        # Audio stream
        self._microphone: Optional[MicrophoneStream] = None
        self._audio_queue: asyncio.Queue = asyncio.Queue()

        # Event callbacks
        self._state_callbacks: Dict[PipelineState, list] = {state: [] for state in PipelineState}
        self._event_callbacks = []

        # Pipeline tasks
        self._pipeline_task: Optional[asyncio.Task] = None
        self._audio_task: Optional[asyncio.Task] = None

        # Response handling
        self._response_queue: asyncio.Queue = asyncio.Queue()
        self._playback_task: Optional[asyncio.Task] = None

        logger.info("Initialized AudioPipeline")

    async def initialize(self) -> None:
        """Initialize pipeline components."""
        logger.info("Initializing pipeline components...")

        # Initialize wake word detector
        self._wake_detector = AsyncWakeWordDetector(
            model_path=self.config.wake_word_model_path,
            sensitivity=self.config.wake_word_sensitivity,
        )

        # Initialize speech recognizer
        speech_config = SpeechConfig(
            model_size=self.config.asr_model_size,
            language=self.config.asr_language,
            sample_rate=self.config.sample_rate,
        )
        self._speech_recognizer = SpeechRecognizer(speech_config)
        await self._speech_recognizer.initialize()

        # Initialize TTS engine
        tts_config = TTSConfig(
            backend=TTSConfig.backend.__class__(self.config.tts_backend),
            voice_id=self.config.tts_voice_id,
            speaking_rate=self.config.tts_speed,
            sample_rate=self.config.sample_rate,
        )
        self._tts_engine = TTSEngine(tts_config)

        # Initialize audio buffer
        buffer_config = BufferConfig(
            max_duration=self.config.buffer_duration,
            sample_rate=self.config.sample_rate,
            silence_duration=self.config.silence_timeout,
        )
        self._audio_buffer = AsyncAudioBuffer(buffer_config)

        # Initialize interruption handler
        interrupt_config = InterruptionConfig(sensitivity=self.config.barge_in_sensitivity)
        self._interruption_handler = AsyncInterruptionHandler(interrupt_config)
        self._interruption_handler.on_interrupt(self._on_interrupt)

        # Initialize latency monitor
        self._latency_monitor = AsyncLatencyMonitor(threshold_ms=self.config.latency_threshold)
        self._latency_monitor.register_callback(self._on_latency_alert)

        logger.info("Pipeline components initialized successfully")

    async def start(self) -> None:
        """Start audio pipeline."""
        if self._is_running:
            logger.warning("Pipeline already running")
            return

        logger.info("Starting audio pipeline...")

        # Initialize components if not already done
        if self._wake_detector is None:
            await self.initialize()

        # Start audio capture
        audio_config = AudioConfig(
            sample_rate=self.config.sample_rate,
            channels=self.config.channels,
            chunk_size=self.config.chunk_size,
        )
        self._microphone = MicrophoneStream(config=audio_config, callback=self._audio_callback)
        self._microphone.start()

        # Start wake word detection
        await self._wake_detector.start_listening()

        # Start pipeline processing
        self._is_running = True
        self._pipeline_task = asyncio.create_task(self._run_pipeline())
        self._audio_task = asyncio.create_task(self._process_audio_stream())

        # Transition to IDLE state
        await self._transition_state(PipelineState.IDLE)

        logger.info("Audio pipeline started successfully")

    async def stop(self) -> None:
        """Stop audio pipeline."""
        if not self._is_running:
            return

        logger.info("Stopping audio pipeline...")

        self._is_running = False

        # Stop tasks
        if self._pipeline_task:
            self._pipeline_task.cancel()
            try:
                await self._pipeline_task
            except asyncio.CancelledError:
                pass

        if self._audio_task:
            self._audio_task.cancel()
            try:
                await self._audio_task
            except asyncio.CancelledError:
                pass

        if self._playback_task:
            self._playback_task.cancel()
            try:
                await self._playback_task
            except asyncio.CancelledError:
                pass

        # Stop components
        if self._wake_detector:
            await self._wake_detector.stop_listening()

        if self._microphone:
            self._microphone.stop()

        if self._speech_recognizer:
            await self._speech_recognizer.close()

        # Transition to STOPPED state
        await self._transition_state(PipelineState.STOPPED)

        logger.info("Audio pipeline stopped")

    async def process_audio_stream(self) -> None:
        """Process continuous audio stream (main pipeline loop)."""
        await self._process_audio_stream()

    async def handle_wake_word(self, detection: DetectionResult) -> None:
        """
        Handle wake word detection.

        Args:
            detection: Wake word detection result
        """
        logger.info(f"Wake word detected: confidence={detection.confidence:.2f}")

        # Create new session
        self._current_session_id = str(uuid.uuid4())

        # Start latency tracking
        self._latency_monitor.start_timer(self._current_session_id)
        self._latency_monitor.record_checkpoint(
            self._current_session_id, PipelineStage.WAKE_WORD_DETECTION
        )

        # Transition to WAKE_DETECTED
        await self._transition_state(PipelineState.WAKE_DETECTED, data={"detection": detection})

        # Immediately transition to LISTENING
        await asyncio.sleep(0.1)  # Small delay for audio feedback
        await self._transition_state(PipelineState.LISTENING)

        # Start listening for speech
        self._latency_monitor.record_checkpoint(
            self._current_session_id, PipelineStage.SPEECH_START
        )

    async def handle_speech_end(self, segment: SpeechSegment) -> None:
        """
        Handle end of speech input.

        Args:
            segment: Speech segment from buffer
        """
        logger.info(f"Speech ended: duration={segment.duration:.2f}s")

        # Record checkpoint
        self._latency_monitor.record_checkpoint(self._current_session_id, PipelineStage.SPEECH_END)

        # Transition to PROCESSING
        await self._transition_state(PipelineState.PROCESSING, data={"segment": segment})

        # Transcribe speech
        self._latency_monitor.record_checkpoint(self._current_session_id, PipelineStage.ASR_START)

        try:
            transcription = await self._speech_recognizer.transcribe(segment.audio_data)

            self._latency_monitor.record_checkpoint(
                self._current_session_id,
                PipelineStage.ASR_END,
                metadata={"text": transcription.text},
            )

            logger.info(f"Transcription: '{transcription.text}'")

            # Queue response for processing
            await self._response_queue.put(
                {
                    "type": "transcription",
                    "data": transcription,
                    "session_id": self._current_session_id,
                }
            )

        except Exception as e:
            logger.error(f"Speech recognition failed: {e}")
            await self._transition_state(PipelineState.ERROR)

    async def play_response(self, text: str, priority: bool = False) -> None:
        """
        Play TTS response.

        Args:
            text: Text to speak
            priority: If True, interrupt current speech
        """
        logger.info(f"Playing response: '{text[:50]}...'")

        # Record TTS start
        if self._current_session_id:
            self._latency_monitor.record_checkpoint(
                self._current_session_id, PipelineStage.TTS_START
            )

        # Synthesize speech
        try:
            audio_output = await self._tts_engine.synthesize(text)

            if self._current_session_id:
                self._latency_monitor.record_checkpoint(
                    self._current_session_id, PipelineStage.TTS_END
                )

            # Transition to SPEAKING
            await self._transition_state(
                PipelineState.SPEAKING, data={"text": text, "audio": audio_output}
            )

            # Play audio
            await self._play_audio(audio_output)

            # Return to IDLE after speaking
            await self._transition_state(PipelineState.IDLE)

            # End latency tracking
            if self._current_session_id:
                metrics = self._latency_monitor.end_timer(self._current_session_id)
                logger.info(f"Session completed: {metrics.total_latency:.1f}ms total latency")
                self._current_session_id = None

        except Exception as e:
            logger.error(f"TTS playback failed: {e}")
            await self._transition_state(PipelineState.ERROR)

    async def handle_barge_in(self, event: InterruptionEvent) -> None:
        """
        Handle barge-in interruption.

        Args:
            event: Interruption event
        """
        logger.info(f"Barge-in detected: type={event.interrupt_type.value}")

        if self._state != PipelineState.SPEAKING:
            return

        # Pause playback
        await self._interruption_handler.pause_playback()

        # Cancel current response
        await self._interruption_handler.cancel_response()

        # Clear buffer and prepare for new input
        self._audio_buffer.clear()

        # Transition to LISTENING
        await self._transition_state(PipelineState.LISTENING, data={"interruption": event})

        logger.info("Transitioned to listening after barge-in")

    def on_state_change(
        self, state: PipelineState, callback: Callable[[PipelineEvent], None]
    ) -> None:
        """
        Register callback for specific state.

        Args:
            state: State to listen for
            callback: Callback function
        """
        if callback not in self._state_callbacks[state]:
            self._state_callbacks[state].append(callback)
            logger.debug(f"Registered callback for state: {state.value}")

    def on_event(self, callback: Callable[[PipelineEvent], None]) -> None:
        """
        Register callback for all events.

        Args:
            callback: Callback function
        """
        if callback not in self._event_callbacks:
            self._event_callbacks.append(callback)
            logger.debug("Registered event callback")

    def get_state(self) -> PipelineState:
        """
        Get current pipeline state.

        Returns:
            Current PipelineState
        """
        return self._state

    def get_latency_stats(self) -> Dict:
        """
        Get latency statistics.

        Returns:
            Dictionary of latency stats
        """
        return self._latency_monitor.get_statistics().__dict__

    def is_healthy(self) -> bool:
        """
        Check if pipeline is healthy.

        Returns:
            True if healthy, False otherwise
        """
        return (
            self._is_running
            and self._state not in (PipelineState.ERROR, PipelineState.STOPPED)
            and self._latency_monitor.is_healthy()
        )

    async def _run_pipeline(self) -> None:
        """Main pipeline processing loop."""
        logger.info("Pipeline processing loop started")

        try:
            while self._is_running:
                # Wait for wake word
                if self._state == PipelineState.IDLE:
                    detection = await self._wake_detector.wait_for_wake_word()
                    if detection:
                        await self.handle_wake_word(detection)

                # Process responses
                try:
                    response = await asyncio.wait_for(self._response_queue.get(), timeout=0.1)

                    if response["type"] == "transcription":
                        # In real implementation, this would go to NLU/dialogue manager
                        # For now, echo back
                        transcription = response["data"]
                        response_text = f"You said: {transcription.text}"
                        await self.play_response(response_text)

                except asyncio.TimeoutError:
                    continue

        except asyncio.CancelledError:
            logger.info("Pipeline processing loop cancelled")
        except Exception as e:
            logger.error(f"Error in pipeline loop: {e}", exc_info=True)
            await self._transition_state(PipelineState.ERROR)

    async def _process_audio_stream(self) -> None:
        """Process incoming audio stream."""
        logger.info("Audio stream processing started")

        try:
            while self._is_running:
                # Get audio from queue
                try:
                    audio_data = await asyncio.wait_for(self._audio_queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue

                # Add to buffer
                await self._audio_buffer.add_samples(audio_data)

                # Check for interruptions during speaking
                if self._state == PipelineState.SPEAKING and self.config.enable_barge_in:
                    interrupt = await self._interruption_handler.detect_interruption(
                        audio_data, self.config.sample_rate
                    )
                    if interrupt:
                        await self.handle_barge_in(interrupt)

                # Extract speech segments when listening
                if self._state == PipelineState.LISTENING:
                    segment = await self._audio_buffer.get_speech_segment(
                        timeout=self.config.listening_timeout
                    )
                    if segment:
                        await self.handle_speech_end(segment)

        except asyncio.CancelledError:
            logger.info("Audio stream processing cancelled")
        except Exception as e:
            logger.error(f"Error processing audio stream: {e}", exc_info=True)

    def _audio_callback(self, audio_data: np.ndarray) -> None:
        """
        Callback for audio capture.

        Args:
            audio_data: Audio samples from microphone
        """
        try:
            # Put audio in queue for processing
            self._audio_queue.put_nowait(audio_data)
        except asyncio.QueueFull:
            logger.warning("Audio queue full, dropping samples")

    async def _play_audio(self, audio_output: AudioOutput) -> None:
        """
        Play audio output.

        Args:
            audio_output: Audio to play
        """
        # Record playback start
        if self._current_session_id:
            self._latency_monitor.record_checkpoint(
                self._current_session_id, PipelineStage.PLAYBACK_START
            )

        # Set interruption handler state
        self._interruption_handler.set_playback_state(True)

        # TODO: Implement actual audio playback
        # For now, simulate with sleep
        await asyncio.sleep(audio_output.duration_ms / 1000.0)

        # Record playback end
        if self._current_session_id:
            self._latency_monitor.record_checkpoint(
                self._current_session_id, PipelineStage.PLAYBACK_END
            )

        self._interruption_handler.set_playback_state(False)

    async def _transition_state(
        self, new_state: PipelineState, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Transition to new pipeline state.

        Args:
            new_state: State to transition to
            data: Optional event data
        """
        if new_state == self._state:
            return

        previous = self._state
        self._state = new_state
        self._previous_state = previous

        # Create event
        import time

        event = PipelineEvent(
            state=new_state,
            previous_state=previous,
            timestamp=time.time(),
            session_id=self._current_session_id or "",
            data=data,
        )

        logger.info(f"State transition: {previous.value} -> {new_state.value}")

        # Trigger callbacks
        await self._trigger_callbacks(event)

    async def _trigger_callbacks(self, event: PipelineEvent) -> None:
        """
        Trigger event callbacks.

        Args:
            event: Pipeline event
        """
        # State-specific callbacks
        for callback in self._state_callbacks[event.state]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in state callback: {e}")

        # General event callbacks
        for callback in self._event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")

    def _on_interrupt(self, event: InterruptionEvent) -> None:
        """
        Handle interruption event.

        Args:
            event: Interruption event
        """
        # Create async task to handle interruption
        asyncio.create_task(self.handle_barge_in(event))

    def _on_latency_alert(self, metrics: LatencyMetrics) -> None:
        """
        Handle latency alert.

        Args:
            metrics: Latency metrics
        """
        logger.warning(
            f"Latency alert: {metrics.total_latency:.1f}ms "
            f"(threshold: {self.config.latency_threshold}ms)"
        )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"AudioPipeline("
            f"state={self._state.value}, "
            f"running={self._is_running}, "
            f"healthy={self.is_healthy()}"
            f")"
        )


# Convenience function for creating pipeline
async def create_pipeline(config_path: Optional[Path] = None) -> AudioPipeline:
    """
    Create and initialize audio pipeline.

    Args:
        config_path: Optional path to configuration file

    Returns:
        Initialized AudioPipeline
    """
    if config_path:
        config = PipelineConfig.from_yaml(config_path)
    else:
        config = PipelineConfig()

    pipeline = AudioPipeline(config)
    await pipeline.initialize()

    return pipeline
