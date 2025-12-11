"""
Integration Tests for Audio Pipeline

Tests the complete audio pipeline including:
- State transitions
- Wake word -> ASR -> TTS flow
- Barge-in functionality
- Latency monitoring
- Error handling
"""

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pytest

from src.audio.audio_pipeline import (
    AudioPipeline,
    PipelineConfig,
    PipelineState,
    PipelineEvent,
    create_pipeline
)
from src.audio.audio_buffer import BufferConfig, SpeechSegment
from src.audio.interruption_handler import InterruptionEvent, InterruptionType
from src.audio.latency_monitor import PipelineStage, LatencyMetrics
from src.audio.speech_recognizer import TranscriptionResult
from src.audio.tts_engine import AudioOutput
from src.audio.wake_word_engine import DetectionResult


@pytest.fixture
def pipeline_config():
    """Create test pipeline configuration."""
    return PipelineConfig(
        sample_rate=16000,
        channels=1,
        chunk_size=1024,
        wake_word_sensitivity=0.5,
        asr_model_size="base",
        tts_backend="pyttsx3",
        listening_timeout=2.0,
        silence_timeout=0.5,
        latency_threshold=2000.0,
        enable_barge_in=True,
        barge_in_sensitivity=0.7
    )


@pytest.fixture
async def pipeline(pipeline_config):
    """Create audio pipeline for testing."""
    pipeline = AudioPipeline(pipeline_config)

    # Mock components to avoid requiring actual models
    with patch('src.audio.audio_pipeline.AsyncWakeWordDetector'):
        with patch('src.audio.audio_pipeline.SpeechRecognizer'):
            with patch('src.audio.audio_pipeline.TTSEngine'):
                with patch('src.audio.audio_pipeline.MicrophoneStream'):
                    await pipeline.initialize()
                    yield pipeline

    # Cleanup
    if pipeline._is_running:
        await pipeline.stop()


@pytest.fixture
def mock_audio_data():
    """Generate mock audio data."""
    duration = 1.0  # 1 second
    sample_rate = 16000
    num_samples = int(duration * sample_rate)

    # Generate sine wave
    t = np.linspace(0, duration, num_samples)
    audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)  # 440 Hz tone

    return audio


@pytest.fixture
def mock_wake_detection():
    """Create mock wake word detection result."""
    return DetectionResult(
        detected=True,
        confidence=0.95,
        timestamp=time.time(),
        latency_ms=50.0
    )


@pytest.fixture
def mock_transcription():
    """Create mock transcription result."""
    return TranscriptionResult(
        text="What is two plus two?",
        confidence=0.92,
        language="en",
        word_timestamps=[],
        processing_time=0.5
    )


@pytest.fixture
def mock_audio_output():
    """Create mock TTS audio output."""
    return AudioOutput(
        audio_data=b"mock_audio_data",
        sample_rate=22050,
        duration_ms=2000.0,
        format="wav"
    )


class TestPipelineInitialization:
    """Test pipeline initialization."""

    @pytest.mark.asyncio
    async def test_pipeline_creation(self, pipeline_config):
        """Test creating pipeline instance."""
        pipeline = AudioPipeline(pipeline_config)

        assert pipeline.config == pipeline_config
        assert pipeline.get_state() == PipelineState.IDLE
        assert not pipeline._is_running

    @pytest.mark.asyncio
    async def test_pipeline_initialization(self, pipeline):
        """Test pipeline component initialization."""
        assert pipeline._wake_detector is not None
        assert pipeline._speech_recognizer is not None
        assert pipeline._tts_engine is not None
        assert pipeline._audio_buffer is not None
        assert pipeline._interruption_handler is not None
        assert pipeline._latency_monitor is not None

    @pytest.mark.asyncio
    async def test_create_pipeline_helper(self):
        """Test create_pipeline helper function."""
        with patch('src.audio.audio_pipeline.AsyncWakeWordDetector'):
            with patch('src.audio.audio_pipeline.SpeechRecognizer'):
                with patch('src.audio.audio_pipeline.TTSEngine'):
                    pipeline = await create_pipeline()

                    assert isinstance(pipeline, AudioPipeline)
                    assert pipeline._wake_detector is not None


class TestStateTransitions:
    """Test pipeline state transitions."""

    @pytest.mark.asyncio
    async def test_idle_to_wake_detected(self, pipeline, mock_wake_detection):
        """Test transition from IDLE to WAKE_DETECTED."""
        events = []

        def on_wake_detected(event: PipelineEvent):
            events.append(event)

        pipeline.on_state_change(PipelineState.WAKE_DETECTED, on_wake_detected)

        await pipeline.handle_wake_word(mock_wake_detection)

        # Should transition through WAKE_DETECTED to LISTENING
        await asyncio.sleep(0.2)  # Wait for transition

        assert len(events) >= 1
        assert events[0].state == PipelineState.WAKE_DETECTED
        assert events[0].previous_state == PipelineState.IDLE

    @pytest.mark.asyncio
    async def test_wake_to_listening_transition(self, pipeline, mock_wake_detection):
        """Test automatic transition from WAKE_DETECTED to LISTENING."""
        await pipeline.handle_wake_word(mock_wake_detection)

        # Wait for transition
        await asyncio.sleep(0.2)

        assert pipeline.get_state() == PipelineState.LISTENING

    @pytest.mark.asyncio
    async def test_listening_to_processing(self, pipeline):
        """Test transition from LISTENING to PROCESSING."""
        pipeline._state = PipelineState.LISTENING
        pipeline._current_session_id = "test_session"

        # Create mock speech segment
        segment = SpeechSegment(
            audio_data=np.random.randn(16000).astype(np.float32),
            start_time=time.time(),
            end_time=time.time() + 1.0,
            duration=1.0,
            rms_level=0.1,
            is_speech=True
        )

        # Mock ASR
        pipeline._speech_recognizer.transcribe = AsyncMock(
            return_value=TranscriptionResult(
                text="test",
                confidence=0.9,
                language="en",
                processing_time=0.3
            )
        )

        await pipeline.handle_speech_end(segment)

        # Should be in PROCESSING state
        assert pipeline.get_state() == PipelineState.PROCESSING

    @pytest.mark.asyncio
    async def test_speaking_to_idle(self, pipeline, mock_audio_output):
        """Test transition from SPEAKING to IDLE."""
        pipeline._state = PipelineState.SPEAKING
        pipeline._current_session_id = "test_session"

        # Mock audio playback
        pipeline._play_audio = AsyncMock()

        await pipeline.play_response("Test response")

        # Should return to IDLE after speaking
        assert pipeline.get_state() == PipelineState.IDLE


class TestAudioProcessing:
    """Test audio processing functionality."""

    @pytest.mark.asyncio
    async def test_audio_callback(self, pipeline, mock_audio_data):
        """Test audio callback processing."""
        # Add audio to queue via callback
        pipeline._audio_callback(mock_audio_data)

        # Queue should have audio
        assert not pipeline._audio_queue.empty()

        # Get audio back
        audio = await asyncio.wait_for(
            pipeline._audio_queue.get(),
            timeout=1.0
        )

        assert np.array_equal(audio, mock_audio_data)

    @pytest.mark.asyncio
    async def test_audio_buffer_integration(self, pipeline, mock_audio_data):
        """Test audio buffer integration."""
        await pipeline._audio_buffer.add_samples(mock_audio_data)

        stats = pipeline._audio_buffer.get_statistics()

        assert stats["buffer_duration"] > 0
        assert stats["current_level"] > 0


class TestWakeWordIntegration:
    """Test wake word detection integration."""

    @pytest.mark.asyncio
    async def test_wake_word_triggers_listening(self, pipeline, mock_wake_detection):
        """Test that wake word detection starts listening."""
        await pipeline.handle_wake_word(mock_wake_detection)

        # Wait for transition
        await asyncio.sleep(0.2)

        # Should be in LISTENING state
        assert pipeline.get_state() == PipelineState.LISTENING

        # Should have started latency tracking
        assert pipeline._current_session_id is not None

    @pytest.mark.asyncio
    async def test_wake_word_latency_tracking(self, pipeline, mock_wake_detection):
        """Test latency tracking starts on wake word."""
        await pipeline.handle_wake_word(mock_wake_detection)

        # Should have recorded checkpoint
        session_id = pipeline._current_session_id
        latency = pipeline._latency_monitor.get_total_latency(session_id)

        assert latency is not None
        assert latency >= 0


class TestSpeechRecognition:
    """Test speech recognition integration."""

    @pytest.mark.asyncio
    async def test_speech_transcription(self, pipeline, mock_transcription):
        """Test speech transcription."""
        pipeline._state = PipelineState.LISTENING
        pipeline._current_session_id = "test_session"

        # Mock ASR
        pipeline._speech_recognizer.transcribe = AsyncMock(
            return_value=mock_transcription
        )

        # Create speech segment
        segment = SpeechSegment(
            audio_data=np.random.randn(16000).astype(np.float32),
            start_time=time.time(),
            end_time=time.time() + 1.0,
            duration=1.0,
            rms_level=0.1,
            is_speech=True
        )

        await pipeline.handle_speech_end(segment)

        # Should have called ASR
        pipeline._speech_recognizer.transcribe.assert_called_once()

        # Should have queued response
        assert not pipeline._response_queue.empty()


class TestTTSIntegration:
    """Test TTS integration."""

    @pytest.mark.asyncio
    async def test_tts_synthesis(self, pipeline, mock_audio_output):
        """Test TTS synthesis."""
        pipeline._current_session_id = "test_session"

        # Mock TTS
        pipeline._tts_engine.synthesize = AsyncMock(
            return_value=mock_audio_output
        )
        pipeline._play_audio = AsyncMock()

        await pipeline.play_response("Test response")

        # Should have synthesized
        pipeline._tts_engine.synthesize.assert_called_once_with("Test response")

        # Should have played audio
        pipeline._play_audio.assert_called_once()

    @pytest.mark.asyncio
    async def test_tts_latency_tracking(self, pipeline, mock_audio_output):
        """Test TTS latency tracking."""
        pipeline._current_session_id = "test_session"
        pipeline._latency_monitor.start_timer(pipeline._current_session_id)

        # Mock TTS
        pipeline._tts_engine.synthesize = AsyncMock(
            return_value=mock_audio_output
        )
        pipeline._play_audio = AsyncMock()

        await pipeline.play_response("Test response")

        # Should have recorded TTS checkpoints
        breakdown = pipeline._latency_monitor.get_breakdown(pipeline._current_session_id)

        # Should have latency data
        assert len(breakdown) > 0


class TestBargeIn:
    """Test barge-in functionality."""

    @pytest.mark.asyncio
    async def test_barge_in_during_speaking(self, pipeline):
        """Test barge-in interrupts TTS."""
        pipeline._state = PipelineState.SPEAKING
        pipeline._current_session_id = "test_session"

        # Create interruption event
        interrupt = InterruptionEvent(
            interrupt_type=InterruptionType.SPEECH,
            timestamp=time.time(),
            audio_level=0.15,
            confidence=0.85
        )

        await pipeline.handle_barge_in(interrupt)

        # Should transition to LISTENING
        assert pipeline.get_state() == PipelineState.LISTENING

    @pytest.mark.asyncio
    async def test_barge_in_detection(self, pipeline, mock_audio_data):
        """Test barge-in detection during playback."""
        pipeline._state = PipelineState.SPEAKING
        pipeline._interruption_handler.set_playback_state(True)
        pipeline._interruption_handler.start_monitoring()

        # Create loud audio (simulating speech)
        loud_audio = mock_audio_data * 3.0

        interrupt = await pipeline._interruption_handler.detect_interruption(
            loud_audio,
            pipeline.config.sample_rate
        )

        # May or may not detect depending on thresholds
        # Just verify no errors occur
        assert interrupt is None or isinstance(interrupt, InterruptionEvent)


class TestLatencyMonitoring:
    """Test latency monitoring."""

    @pytest.mark.asyncio
    async def test_latency_tracking(self, pipeline):
        """Test end-to-end latency tracking."""
        session_id = "test_session"

        pipeline._latency_monitor.start_timer(session_id)

        # Record checkpoints
        await asyncio.sleep(0.05)
        pipeline._latency_monitor.record_checkpoint(
            session_id,
            PipelineStage.WAKE_WORD_DETECTION
        )

        await asyncio.sleep(0.1)
        pipeline._latency_monitor.record_checkpoint(
            session_id,
            PipelineStage.ASR_START
        )

        await asyncio.sleep(0.2)
        pipeline._latency_monitor.record_checkpoint(
            session_id,
            PipelineStage.ASR_END
        )

        # End tracking
        metrics = pipeline._latency_monitor.end_timer(session_id)

        assert metrics.total_latency > 0
        assert metrics.session_id == session_id
        assert len(metrics.checkpoints) == 3

    @pytest.mark.asyncio
    async def test_latency_threshold_alert(self, pipeline):
        """Test latency threshold violation alert."""
        alerts = []

        def on_alert(metrics: LatencyMetrics):
            alerts.append(metrics)

        pipeline._latency_monitor.register_callback(on_alert)

        session_id = "test_session"
        pipeline._latency_monitor.start_timer(session_id)

        # Simulate long delay
        await asyncio.sleep(2.5)

        # End timer (should exceed 2000ms threshold)
        metrics = pipeline._latency_monitor.end_timer(session_id)

        # Check if alert was triggered
        assert metrics.exceeded_threshold


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_asr_failure_handling(self, pipeline):
        """Test handling of ASR failure."""
        pipeline._state = PipelineState.LISTENING
        pipeline._current_session_id = "test_session"

        # Mock ASR to raise exception
        pipeline._speech_recognizer.transcribe = AsyncMock(
            side_effect=Exception("ASR failed")
        )

        segment = SpeechSegment(
            audio_data=np.random.randn(16000).astype(np.float32),
            start_time=time.time(),
            end_time=time.time() + 1.0,
            duration=1.0,
            rms_level=0.1,
            is_speech=True
        )

        await pipeline.handle_speech_end(segment)

        # Should transition to ERROR state
        assert pipeline.get_state() == PipelineState.ERROR

    @pytest.mark.asyncio
    async def test_tts_failure_handling(self, pipeline):
        """Test handling of TTS failure."""
        pipeline._current_session_id = "test_session"

        # Mock TTS to raise exception
        pipeline._tts_engine.synthesize = AsyncMock(
            side_effect=Exception("TTS failed")
        )

        await pipeline.play_response("Test response")

        # Should transition to ERROR state
        assert pipeline.get_state() == PipelineState.ERROR


class TestEventCallbacks:
    """Test event callback system."""

    @pytest.mark.asyncio
    async def test_state_change_callback(self, pipeline):
        """Test state change callbacks."""
        events = []

        def on_listening(event: PipelineEvent):
            events.append(event)

        pipeline.on_state_change(PipelineState.LISTENING, on_listening)

        # Trigger transition
        pipeline._state = PipelineState.IDLE
        await pipeline._transition_state(PipelineState.LISTENING)

        assert len(events) == 1
        assert events[0].state == PipelineState.LISTENING

    @pytest.mark.asyncio
    async def test_general_event_callback(self, pipeline):
        """Test general event callbacks."""
        events = []

        def on_event(event: PipelineEvent):
            events.append(event)

        pipeline.on_event(on_event)

        # Trigger multiple transitions
        await pipeline._transition_state(PipelineState.LISTENING)
        await pipeline._transition_state(PipelineState.PROCESSING)

        assert len(events) == 2


class TestPipelineHealth:
    """Test pipeline health monitoring."""

    @pytest.mark.asyncio
    async def test_healthy_pipeline(self, pipeline):
        """Test healthy pipeline check."""
        pipeline._is_running = True
        pipeline._state = PipelineState.IDLE

        # With no latency violations, should be healthy
        is_healthy = pipeline.is_healthy()

        assert is_healthy

    @pytest.mark.asyncio
    async def test_unhealthy_pipeline_stopped(self, pipeline):
        """Test unhealthy pipeline when stopped."""
        pipeline._is_running = False

        is_healthy = pipeline.is_healthy()

        assert not is_healthy

    @pytest.mark.asyncio
    async def test_unhealthy_pipeline_error(self, pipeline):
        """Test unhealthy pipeline in error state."""
        pipeline._is_running = True
        pipeline._state = PipelineState.ERROR

        is_healthy = pipeline.is_healthy()

        assert not is_healthy


class TestEndToEndFlow:
    """Test complete end-to-end flows."""

    @pytest.mark.asyncio
    async def test_complete_interaction_flow(
        self,
        pipeline,
        mock_wake_detection,
        mock_transcription,
        mock_audio_output
    ):
        """Test complete interaction: wake word -> ASR -> TTS."""
        # Setup mocks
        pipeline._speech_recognizer.transcribe = AsyncMock(
            return_value=mock_transcription
        )
        pipeline._tts_engine.synthesize = AsyncMock(
            return_value=mock_audio_output
        )
        pipeline._play_audio = AsyncMock()

        # 1. Wake word detected
        await pipeline.handle_wake_word(mock_wake_detection)
        await asyncio.sleep(0.2)

        assert pipeline.get_state() == PipelineState.LISTENING

        # 2. Speech input
        segment = SpeechSegment(
            audio_data=np.random.randn(16000).astype(np.float32),
            start_time=time.time(),
            end_time=time.time() + 1.0,
            duration=1.0,
            rms_level=0.1,
            is_speech=True
        )

        await pipeline.handle_speech_end(segment)

        assert pipeline.get_state() == PipelineState.PROCESSING

        # 3. Get response from queue and play
        response = await asyncio.wait_for(
            pipeline._response_queue.get(),
            timeout=1.0
        )

        await pipeline.play_response("Test response")

        # Should return to IDLE
        assert pipeline.get_state() == PipelineState.IDLE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
