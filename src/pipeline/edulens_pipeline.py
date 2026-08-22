"""
EduLens Main Integrated Pipeline

Orchestrates the complete Vision → AI → Voice flow for the EduLens tutoring system.
Provides the main entry point for running the full educational assistant pipeline
with vision capture, audio interaction, AI tutoring, and TTS output.

Author: Integration Agent (INT-001)
Version: 1.0.0
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Optional
from uuid import uuid4

from ..ai.tutor_inference import ResponseType, TutorEngine
from ..audio.audio_pipeline import (
    AudioPipeline,
)
from ..audio.audio_pipeline import PipelineConfig as AudioConfig
from ..audio.audio_pipeline import PipelineState as AudioState
from ..core.component_manager import Component, ComponentHealth, ComponentState
from ..core.event_bus import Event, EventBus, EventType, get_event_bus
from ..integration.context_builder import ContextBuilder
from ..integration.vision_to_ai_bridge import VisionToAIBridge, VisualContext
from ..integration.voice_to_ai_bridge import SpeechResponse, VoiceQuery, VoiceToAIBridge

logger = logging.getLogger(__name__)


class PipelineMode(Enum):
    """Operating modes for the pipeline."""

    FULL = auto()  # Complete vision + audio + AI
    AUDIO_ONLY = auto()  # Audio interaction without vision
    VISION_ONLY = auto()  # Vision processing without audio
    MANUAL = auto()  # Manual control for testing


@dataclass
class PipelineStats:
    """Statistics for pipeline operations."""

    sessions_started: int = 0
    frames_processed: int = 0
    queries_handled: int = 0
    responses_generated: int = 0
    errors_encountered: int = 0
    average_latency_ms: float = 0.0
    uptime_seconds: float = 0.0


@dataclass
class PipelineConfig:
    """Configuration for the EduLens pipeline."""

    # Operating mode
    mode: PipelineMode = PipelineMode.FULL

    # Student profile
    student_age: int = 8
    student_grade: str = "3"
    student_id: str = "default_student"

    # Vision settings
    enable_vision: bool = True
    vision_fps: int = 5  # Process frames at 5 FPS for homework
    enable_handwriting: bool = True

    # Audio settings
    enable_audio: bool = True
    audio_config: Optional[AudioConfig] = None

    # AI settings
    ai_model: str = "llama-3.2-3B"
    enable_socratic_mode: bool = True
    hint_progression: bool = True

    # Performance
    max_concurrent_operations: int = 3
    operation_timeout_seconds: float = 30.0

    # Error handling
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    enable_graceful_degradation: bool = True


class EduLensPipeline(Component):
    """
    Main integrated pipeline for EduLens tutoring system.

    Orchestrates:
    - Vision capture and OCR processing
    - Audio input (wake word detection, speech recognition)
    - AI tutoring response generation (Socratic method)
    - Audio output (TTS with educational persona)

    Features:
    - Event-driven architecture
    - Concurrent processing where possible
    - Graceful error handling and recovery
    - Component lifecycle management
    - Performance monitoring
    """

    def __init__(
        self, config: Optional[PipelineConfig] = None, event_bus: Optional[EventBus] = None
    ) -> None:
        """
        Initialize the EduLens pipeline.

        Args:
            config: Pipeline configuration
            event_bus: Event bus for inter-component communication
        """
        super().__init__(name="edulens_pipeline", event_bus=event_bus)

        self.config = config or PipelineConfig()
        self._stats = PipelineStats()
        self._start_time: Optional[datetime] = None

        # Core components
        self._audio_pipeline: Optional[AudioPipeline] = None
        self._tutor_engine: Optional[TutorEngine] = None
        self._vision_bridge: Optional[VisionToAIBridge] = None
        self._voice_bridge: Optional[VoiceToAIBridge] = None
        self._context_builder: Optional[ContextBuilder] = None

        # Current session state
        self._current_session_id: Optional[str] = None
        self._current_visual_context: Optional[VisualContext] = None
        self._current_voice_query: Optional[VoiceQuery] = None

        # Processing state
        self._is_processing: bool = False
        self._processing_lock = asyncio.Lock()
        self._pending_operations: set[asyncio.Task] = set()

        logger.info(f"EduLensPipeline initialized in {self.config.mode.name} mode")

    async def initialize(self) -> None:
        """Initialize all pipeline components."""
        logger.info("Initializing EduLens pipeline components...")

        try:
            # Initialize vision bridge
            if self.config.enable_vision:
                self._vision_bridge = VisionToAIBridge()
                logger.info("Vision bridge initialized")

            # Initialize voice bridge
            if self.config.enable_audio:
                self._voice_bridge = VoiceToAIBridge()
                logger.info("Voice bridge initialized")

            # Initialize audio pipeline
            if self.config.enable_audio:
                audio_config = self.config.audio_config or AudioConfig()
                self._audio_pipeline = AudioPipeline(audio_config)
                await self._audio_pipeline.initialize()

                # Register audio event handlers
                self._audio_pipeline.on_event(self._handle_audio_event)
                logger.info("Audio pipeline initialized")

            # Initialize AI tutor engine
            self._tutor_engine = TutorEngine(model_name=self.config.ai_model, config_path=None)
            logger.info(f"Tutor engine initialized with {self.config.ai_model}")

            # Initialize context builder
            self._context_builder = ContextBuilder()
            logger.info("Context builder initialized")

            # Subscribe to relevant events
            self.event_bus.subscribe(EventType.VISION_TEXT_DETECTED, self._on_vision_text_detected)
            self.event_bus.subscribe(
                EventType.AUDIO_TRANSCRIPTION_READY, self._on_audio_transcription
            )
            self.event_bus.subscribe(EventType.AI_ERROR, self._on_ai_error)

            self._state = ComponentState.READY
            logger.info("EduLens pipeline initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize pipeline: {e}", exc_info=True)
            self._state = ComponentState.ERROR
            raise

    async def start(self) -> None:
        """Start the pipeline."""
        logger.info("Starting EduLens pipeline...")

        if self._state != ComponentState.READY:
            raise RuntimeError(f"Cannot start pipeline in state: {self._state}")

        try:
            self._start_time = datetime.utcnow()

            # Start audio pipeline if enabled
            if self._audio_pipeline:
                await self._audio_pipeline.start()
                logger.info("Audio pipeline started")

            self._state = ComponentState.RUNNING

            # Publish system ready event
            await self.event_bus.publish(
                Event(
                    event_type=EventType.SYSTEM_READY,
                    source=self.name,
                    payload={"mode": self.config.mode.name, "student_id": self.config.student_id},
                )
            )

            logger.info("EduLens pipeline started successfully")

        except Exception as e:
            logger.error(f"Failed to start pipeline: {e}", exc_info=True)
            self._state = ComponentState.ERROR
            raise

    async def stop(self) -> None:
        """Stop the pipeline gracefully."""
        logger.info("Stopping EduLens pipeline...")

        try:
            # Cancel pending operations
            for task in self._pending_operations:
                if not task.done():
                    task.cancel()

            if self._pending_operations:
                await asyncio.gather(*self._pending_operations, return_exceptions=True)

            # Stop audio pipeline
            if self._audio_pipeline:
                await self._audio_pipeline.stop()
                logger.info("Audio pipeline stopped")

            # Reset conversation state
            if self._tutor_engine:
                self._tutor_engine.reset_conversation()

            if self._voice_bridge:
                self._voice_bridge.reset_conversation()

            self._state = ComponentState.STOPPED
            logger.info("EduLens pipeline stopped")

        except Exception as e:
            logger.error(f"Error stopping pipeline: {e}", exc_info=True)
            self._state = ComponentState.ERROR

    async def health_check(self) -> ComponentHealth:
        """Check health of the pipeline."""
        is_healthy = True
        error_messages = []
        metrics = {}

        try:
            # Check component states
            if self._audio_pipeline and not self._audio_pipeline.is_healthy():
                is_healthy = False
                error_messages.append("Audio pipeline unhealthy")

            # Check processing state
            if self._is_processing and len(self._pending_operations) > 10:
                error_messages.append(
                    f"Too many pending operations: {len(self._pending_operations)}"
                )

            # Collect metrics
            if self._start_time:
                uptime = (datetime.utcnow() - self._start_time).total_seconds()
                self._stats.uptime_seconds = uptime

            metrics = {
                "sessions_started": self._stats.sessions_started,
                "frames_processed": self._stats.frames_processed,
                "queries_handled": self._stats.queries_handled,
                "responses_generated": self._stats.responses_generated,
                "errors_encountered": self._stats.errors_encountered,
                "uptime_seconds": self._stats.uptime_seconds,
                "pending_operations": len(self._pending_operations),
            }

        except Exception as e:
            is_healthy = False
            error_messages.append(f"Health check error: {str(e)}")

        return ComponentHealth(
            is_healthy=is_healthy,
            state=self._state,
            error_message="; ".join(error_messages) if error_messages else None,
            metrics=metrics,
        )

    async def start_session(self, student_id: Optional[str] = None) -> str:
        """
        Start a new tutoring session.

        Args:
            student_id: Optional student identifier

        Returns:
            Session ID
        """
        session_id = str(uuid4())
        self._current_session_id = session_id
        self._stats.sessions_started += 1

        if student_id:
            self.config.student_id = student_id

        logger.info(f"Started tutoring session: {session_id}")

        # Publish session started event
        await self.event_bus.publish(
            Event(
                event_type=EventType.SESSION_STARTED,
                source=self.name,
                payload={
                    "session_id": session_id,
                    "student_id": self.config.student_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        )

        return session_id

    async def process_frame(
        self,
        frame_data: Any,
        ocr_result: Optional[dict] = None,
        layout_result: Optional[dict] = None,
        handwriting_result: Optional[dict] = None,
    ) -> Optional[VisualContext]:
        """
        Process a camera frame through the vision pipeline.

        Args:
            frame_data: Camera frame data
            ocr_result: OCR processing result
            layout_result: Layout analysis result
            handwriting_result: Handwriting recognition result

        Returns:
            Visual context extracted from frame
        """
        if not self.config.enable_vision or not self._vision_bridge:
            return None

        try:
            self._stats.frames_processed += 1

            # Process vision output into AI context
            visual_context = self._vision_bridge.process_vision_output(
                ocr_result=ocr_result or {},
                layout_result=layout_result,
                handwriting_result=handwriting_result,
            )

            # Store current visual context
            self._current_visual_context = visual_context

            logger.info(
                f"Processed frame: subject={visual_context.subject_area.value}, "
                f"type={visual_context.content_type.name}, "
                f"confidence={visual_context.confidence:.2f}"
            )

            # Publish vision event
            await self.event_bus.publish(
                Event(
                    event_type=EventType.VISION_TEXT_DETECTED,
                    source=self.name,
                    payload={
                        "session_id": self._current_session_id,
                        "visual_context": visual_context.to_ai_prompt_context(),
                        "subject": visual_context.subject_area.value,
                        "content_type": visual_context.content_type.name,
                    },
                )
            )

            return visual_context

        except Exception as e:
            logger.error(f"Error processing frame: {e}", exc_info=True)
            self._stats.errors_encountered += 1
            return None

    async def generate_response(
        self,
        student_query: Optional[str] = None,
        visual_context: Optional[VisualContext] = None,
        response_type: Optional[ResponseType] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Generate AI tutoring response.

        Args:
            student_query: Student's spoken question
            visual_context: Visual context from camera
            response_type: Type of response to generate

        Returns:
            AI response dictionary
        """
        if not self._tutor_engine:
            logger.error("Tutor engine not initialized")
            return None

        async with self._processing_lock:
            try:
                self._is_processing = True

                # Build context for AI
                context = {
                    "age": self.config.student_age,
                    "grade": self.config.student_grade,
                    "subject": "general",
                    "session_id": self._current_session_id,
                }

                # Add visual context if available
                if visual_context:
                    context["subject"] = visual_context.subject_area.value
                    context["problem_statement"] = visual_context.problem_text
                    context["student_answer"] = visual_context.student_answer

                # Use current visual context if not provided
                if not visual_context and self._current_visual_context:
                    visual_context = self._current_visual_context
                    context["subject"] = visual_context.subject_area.value

                # Generate response
                query_text = student_query or "Help me understand this problem"

                logger.info(f"Generating response for query: {query_text[:50]}...")

                response = self._tutor_engine.generate_response(
                    student_query=query_text, context=context, response_type=response_type
                )

                self._stats.responses_generated += 1

                logger.info(
                    f"Generated response: type={response['response_type']}, "
                    f"length={len(response['response'])}"
                )

                # Publish AI response event
                await self.event_bus.publish(
                    Event(
                        event_type=EventType.AI_RESPONSE_GENERATED,
                        source=self.name,
                        payload={
                            "session_id": self._current_session_id,
                            "response": response["response"],
                            "response_type": response["response_type"],
                        },
                    )
                )

                return response

            except Exception as e:
                logger.error(f"Error generating AI response: {e}", exc_info=True)
                self._stats.errors_encountered += 1

                # Publish error event
                await self.event_bus.publish(
                    Event(
                        event_type=EventType.AI_ERROR,
                        source=self.name,
                        payload={"session_id": self._current_session_id, "error": str(e)},
                    )
                )

                return None

            finally:
                self._is_processing = False

    async def deliver_response(
        self, response_text: str, response_type: str = "explanation"
    ) -> bool:
        """
        Deliver AI response via text-to-speech.

        Args:
            response_text: Text to speak
            response_type: Type of response for appropriate tone

        Returns:
            True if successful
        """
        if not self._audio_pipeline or not self._voice_bridge:
            logger.warning("Audio not enabled, cannot deliver response")
            return False

        try:
            # Prepare speech response
            speech_response = self._voice_bridge.prepare_speech_response(
                ai_response=response_text, response_type=response_type
            )

            # Play through audio pipeline
            await self._audio_pipeline.play_response(speech_response.text)

            logger.info(f"Delivered response via TTS: {response_text[:50]}...")

            # Publish TTS event
            await self.event_bus.publish(
                Event(
                    event_type=EventType.AUDIO_TTS_STARTED,
                    source=self.name,
                    payload={
                        "session_id": self._current_session_id,
                        "text": response_text,
                        "tone": speech_response.tone,
                    },
                )
            )

            return True

        except Exception as e:
            logger.error(f"Error delivering response: {e}", exc_info=True)
            self._stats.errors_encountered += 1
            return False

    async def process_interaction(
        self, student_query: str, visual_context: Optional[VisualContext] = None
    ) -> Optional[str]:
        """
        Process a complete interaction: query → AI → TTS.

        Args:
            student_query: Student's question
            visual_context: Optional visual context

        Returns:
            AI response text
        """
        try:
            # Generate AI response
            response = await self.generate_response(
                student_query=student_query, visual_context=visual_context
            )

            if not response:
                return None

            response_text = response["response"]
            response_type = response["response_type"]

            # Deliver via TTS
            await self.deliver_response(response_text, response_type)

            return response_text

        except Exception as e:
            logger.error(f"Error processing interaction: {e}", exc_info=True)
            return None

    def get_stats(self) -> PipelineStats:
        """Get pipeline statistics."""
        return self._stats

    async def _handle_audio_event(self, event: Any) -> None:
        """Handle events from audio pipeline."""
        try:
            if hasattr(event, "state"):
                logger.debug(f"Audio pipeline state: {event.state.value}")

        except Exception as e:
            logger.error(f"Error handling audio event: {e}", exc_info=True)

    async def _on_vision_text_detected(self, event: Event) -> None:
        """Handle vision text detection event."""
        try:
            logger.debug(f"Vision text detected: {event.payload.get('subject')}")

        except Exception as e:
            logger.error(f"Error handling vision event: {e}", exc_info=True)

    async def _on_audio_transcription(self, event: Event) -> None:
        """Handle audio transcription event."""
        try:
            transcription = event.payload.get("transcription")
            if transcription and self._voice_bridge:
                # Process voice input
                voice_query = self._voice_bridge.process_voice_input(
                    transcription=transcription, confidence=event.payload.get("confidence", 0.0)
                )

                self._current_voice_query = voice_query
                self._stats.queries_handled += 1

                logger.info(f"Processed voice query: intent={voice_query.intent.name}")

                # Trigger AI response generation
                task = asyncio.create_task(
                    self.process_interaction(
                        student_query=voice_query.transcription,
                        visual_context=self._current_visual_context,
                    )
                )
                self._pending_operations.add(task)
                task.add_done_callback(self._pending_operations.discard)

        except Exception as e:
            logger.error(f"Error handling transcription: {e}", exc_info=True)

    async def _on_ai_error(self, event: Event) -> None:
        """Handle AI error event."""
        try:
            error_msg = event.payload.get("error", "Unknown error")
            logger.error(f"AI error: {error_msg}")
            self._stats.errors_encountered += 1

        except Exception as e:
            logger.error(f"Error handling AI error event: {e}", exc_info=True)


async def create_pipeline(config: Optional[PipelineConfig] = None) -> EduLensPipeline:
    """
    Create and initialize an EduLens pipeline.

    Args:
        config: Optional pipeline configuration

    Returns:
        Initialized pipeline
    """
    pipeline = EduLensPipeline(config=config)
    await pipeline.initialize()
    return pipeline
