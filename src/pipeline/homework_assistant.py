"""
Homework Assistant Pipeline for EduLens

The main end-to-end pipeline that orchestrates all components to provide
real-time homework assistance through the smart glasses.

Pipeline Flow:
1. Wake word detection triggers session
2. Camera captures homework/textbook
3. Vision processing extracts content
4. Student asks question (voice)
5. AI generates educational response
6. Response delivered via TTS
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable

from ..core.event_bus import Event, EventBus, EventType, create_event, get_event_bus
from ..integration.context_builder import ContextBuilder, StudentProfile, TutoringContext
from ..integration.vision_to_ai_bridge import VisionToAIBridge, VisualContext
from ..integration.voice_to_ai_bridge import QueryIntent, SpeechResponse, VoiceToAIBridge
from .session_manager import InteractionType, SessionManager, SessionState

logger = logging.getLogger(__name__)


class PipelineState(Enum):
    """States of the homework assistant pipeline."""

    IDLE = auto()
    WAKE_WORD_DETECTED = auto()
    CAPTURING_VISUAL = auto()
    PROCESSING_VISUAL = auto()
    LISTENING_QUERY = auto()
    PROCESSING_QUERY = auto()
    GENERATING_RESPONSE = auto()
    SPEAKING_RESPONSE = auto()
    AWAITING_FOLLOWUP = auto()
    ERROR = auto()


@dataclass
class PipelineMetrics:
    """Performance metrics for the pipeline."""

    total_requests: int = 0
    successful_responses: int = 0
    average_latency_ms: float = 0.0
    vision_latency_ms: float = 0.0
    ai_latency_ms: float = 0.0
    tts_latency_ms: float = 0.0


class HomeworkAssistant:
    """
    Main homework assistance pipeline for EduLens.

    Coordinates:
    - Vision processing (OCR, layout analysis, handwriting)
    - Voice processing (wake word, ASR, TTS)
    - Educational AI (tutoring responses)
    - Session management
    - Privacy compliance
    """

    def __init__(
        self,
        event_bus: EventBus | None = None,
        session_manager: SessionManager | None = None,
        vision_bridge: VisionToAIBridge | None = None,
        voice_bridge: VoiceToAIBridge | None = None,
        context_builder: ContextBuilder | None = None,
    ) -> None:
        """
        Initialize the homework assistant.

        Components can be injected for testing or use defaults.
        """
        self.event_bus = event_bus or get_event_bus()
        self.session_manager = session_manager or SessionManager()
        self.vision_bridge = vision_bridge or VisionToAIBridge()
        self.voice_bridge = voice_bridge or VoiceToAIBridge()
        self.context_builder = context_builder or ContextBuilder()

        # Pipeline state
        self._state = PipelineState.IDLE
        self._current_session_id: str | None = None
        self._current_visual_context: VisualContext | None = None
        self._current_student_profile: StudentProfile | None = None

        # Callbacks
        self._on_response_ready: Callable[[SpeechResponse], None] | None = None
        self._on_state_change: Callable[[PipelineState], None] | None = None

        # Metrics
        self._metrics = PipelineMetrics()
        self._latency_history: list[float] = []

        # Configuration
        self._followup_timeout_seconds = 30.0
        self._max_hints_per_problem = 5

        # Subscribe to events
        self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
        """Set up event bus subscriptions."""
        self.event_bus.subscribe(
            EventType.AUDIO_WAKE_WORD_DETECTED,
            self._handle_wake_word,
        )
        self.event_bus.subscribe(
            EventType.AUDIO_TRANSCRIPTION_READY,
            self._handle_transcription,
        )
        self.event_bus.subscribe(
            EventType.VISION_DOCUMENT_RECOGNIZED,
            self._handle_document_recognized,
        )

    async def _handle_wake_word(self, event: Event) -> None:
        """Handle wake word detection event."""
        logger.info("Wake word detected - starting assistance")
        await self.start_assistance()

    async def _handle_transcription(self, event: Event) -> None:
        """Handle speech transcription event."""
        transcription = event.payload.get("text", "")
        confidence = event.payload.get("confidence", 0.0)

        if self._state in (PipelineState.LISTENING_QUERY, PipelineState.AWAITING_FOLLOWUP):
            await self.process_student_query(transcription, confidence)

    async def _handle_document_recognized(self, event: Event) -> None:
        """Handle document recognition event."""
        ocr_result = event.payload.get("ocr_result", {})
        layout_result = event.payload.get("layout_result")
        handwriting_result = event.payload.get("handwriting_result")

        if self._state == PipelineState.PROCESSING_VISUAL:
            await self.process_visual_input(ocr_result, layout_result, handwriting_result)

    async def start_assistance(
        self,
        student_id: str = "default_student",
    ) -> None:
        """
        Start a homework assistance interaction.

        Called when wake word is detected.
        """
        self._set_state(PipelineState.WAKE_WORD_DETECTED)

        # Create or get session
        session = self.session_manager.get_active_session_for_student(student_id)
        if not session:
            session = self.session_manager.create_session(student_id)

        self._current_session_id = session.session_id
        self.session_manager.update_state(session.session_id, SessionState.LISTENING)

        # Start visual capture
        self._set_state(PipelineState.CAPTURING_VISUAL)
        await self.event_bus.publish(
            create_event(
                EventType.VISION_FRAME_CAPTURED,
                source="homework_assistant",
                action="capture_for_analysis",
            )
        )

        # Start listening for student query
        self._set_state(PipelineState.LISTENING_QUERY)

        # Provide audio feedback
        greeting = SpeechResponse(
            text="I'm here to help! What would you like to work on?",
            tone="encouraging",
            speed=1.0,
        )
        await self._deliver_response(greeting)

    async def process_visual_input(
        self,
        ocr_result: dict[str, Any],
        layout_result: dict[str, Any] | None = None,
        handwriting_result: dict[str, Any] | None = None,
    ) -> VisualContext:
        """
        Process visual input from the camera.

        Returns the processed visual context.
        """
        start_time = time.time()
        self._set_state(PipelineState.PROCESSING_VISUAL)

        # Process through vision bridge
        visual_context = self.vision_bridge.process_vision_output(
            ocr_result=ocr_result,
            layout_result=layout_result,
            handwriting_result=handwriting_result,
        )

        self._current_visual_context = visual_context

        # Track latency
        latency = (time.time() - start_time) * 1000
        self._metrics.vision_latency_ms = latency

        logger.info(
            f"Visual processing complete: {visual_context.content_type.name}, "
            f"subject={visual_context.subject_area.value}, "
            f"confidence={visual_context.confidence:.2f}"
        )

        return visual_context

    async def process_student_query(
        self,
        transcription: str,
        confidence: float,
    ) -> SpeechResponse:
        """
        Process student's voice query and generate response.

        This is the main interaction handler.
        """
        start_time = time.time()
        self._set_state(PipelineState.PROCESSING_QUERY)

        # Parse the voice query
        voice_query = self.voice_bridge.process_voice_input(
            transcription=transcription,
            confidence=confidence,
        )

        logger.info(f"Student query: '{transcription}' -> intent={voice_query.intent.name}")

        # Handle special intents
        if voice_query.intent == QueryIntent.REPEAT_REQUEST:
            return await self._handle_repeat_request()

        if voice_query.intent == QueryIntent.SLOWER_REQUEST:
            return await self._handle_slower_request()

        if voice_query.intent == QueryIntent.SKIP_REQUEST:
            return await self._handle_skip_request()

        # Build full context
        visual_context_dict = {}
        if self._current_visual_context:
            visual_context_dict = {
                "visual": self._current_visual_context.to_ai_prompt_context(),
                "subject": self._current_visual_context.subject_area.value,
                "content_type": self._current_visual_context.content_type.name,
                "student_answer": self._current_visual_context.student_answer,
                "confidence": self._current_visual_context.confidence,
            }

        audio_context = {
            "transcription": transcription,
            "intent": voice_query.intent.name,
        }

        tutoring_context = self.context_builder.build_context(
            visual_context=visual_context_dict,
            audio_context=audio_context,
            student_profile=self._current_student_profile,
        )

        # Generate AI response
        self._set_state(PipelineState.GENERATING_RESPONSE)
        ai_response = await self._generate_ai_response(tutoring_context, voice_query)

        # Track AI latency
        ai_latency = (time.time() - start_time) * 1000
        self._metrics.ai_latency_ms = ai_latency

        # Prepare for speech
        response_type = self._determine_response_type(voice_query.intent)
        hint_level = self._get_current_hint_level()

        speech_response = self.voice_bridge.prepare_speech_response(
            ai_response=ai_response,
            response_type=response_type,
            hint_level=hint_level,
        )

        # Record interaction
        if self._current_session_id:
            interaction_type = self._map_intent_to_interaction(voice_query.intent)
            self.session_manager.record_interaction(
                session_id=self._current_session_id,
                interaction_type=interaction_type,
                visual_context=(
                    tutoring_context.visual_context[:200]
                    if tutoring_context.visual_context
                    else None
                ),
                student_query=transcription,
                tutor_response=ai_response[:200],
                subject=tutoring_context.subject,
                hint_level=hint_level,
                response_time_ms=int(ai_latency),
            )

        # Track conversation
        self.voice_bridge.add_to_history(voice_query, speech_response)

        # Deliver response
        await self._deliver_response(speech_response)

        # Update metrics
        total_latency = (time.time() - start_time) * 1000
        self._update_metrics(total_latency)

        # Move to awaiting follow-up
        self._set_state(PipelineState.AWAITING_FOLLOWUP)

        # Set timeout for follow-up
        asyncio.create_task(self._followup_timeout())

        return speech_response

    async def _generate_ai_response(
        self,
        context: TutoringContext,
        voice_query: Any,
    ) -> str:
        """
        Generate educational AI response.

        This is a placeholder - actual implementation would call
        the TutorEngine from EDU-001-T2.
        """
        # TODO: Replace with actual TutorEngine call
        # from ..ai.tutor_inference import TutorEngine
        # tutor = TutorEngine()
        # return await tutor.generate_response(context)

        # Placeholder responses based on intent
        intent = voice_query.intent

        if intent == QueryIntent.HELP_REQUEST:
            return self._generate_help_response(context)
        elif intent == QueryIntent.HINT_REQUEST:
            return self._generate_hint_response(context)
        elif intent == QueryIntent.CHECK_ANSWER:
            return self._generate_answer_check_response(context)
        elif intent == QueryIntent.EXPLAIN_CONCEPT:
            return self._generate_explanation_response(context)
        elif intent == QueryIntent.CLARIFICATION:
            return self._generate_clarification_response(context)
        else:
            return self._generate_default_response(context)

    def _generate_help_response(self, context: TutoringContext) -> str:
        """Generate a help response using Socratic method."""
        if context.subject == "math":
            return (
                "I see you're working on a math problem. "
                "Let's think about this together. "
                "What do you think the first step should be? "
                "Take your time - there's no rush!"
            )
        elif context.subject == "reading":
            return (
                "This looks like a reading question. "
                "Let's break it down. Can you tell me what the passage is about? "
                "Sometimes understanding the main idea helps us answer questions."
            )
        else:
            return (
                "I'm here to help! Let's work through this together. "
                "What part are you finding tricky? "
                "Don't worry - making mistakes is part of learning!"
            )

    def _generate_hint_response(self, context: TutoringContext) -> str:
        """Generate a hint response."""
        hint_level = context.previous_hints_given + 1

        if hint_level == 1:
            return (
                "Here's a little hint: Think about what you already know about this topic. "
                "What does the question remind you of?"
            )
        elif hint_level == 2:
            return (
                "Let me give you another hint. "
                "Try reading the problem again and look for the key words. "
                "What information does it give you?"
            )
        elif hint_level >= 3:
            return (
                "Okay, here's a bigger hint. "
                "Let's focus on the most important part of this problem. "
                "Would you like me to help you get started with the first step?"
            )
        else:
            return "Let me help you think about this differently..."

    def _generate_answer_check_response(self, context: TutoringContext) -> str:
        """Generate response for answer checking."""
        if context.student_answer:
            # TODO: Actual answer verification would go here
            return (
                f"I see you wrote '{context.student_answer}'. "
                "Let's check your work together. "
                "Can you walk me through how you got that answer?"
            )
        else:
            return "I'd be happy to check your answer! " "Can you tell me or show me what you got?"

    def _generate_explanation_response(self, context: TutoringContext) -> str:
        """Generate concept explanation."""
        return (
            "Great question! Let me explain this in a way that makes sense. "
            "Think of it like this... "
            "Does that help? Let me know if you'd like me to explain it differently!"
        )

    def _generate_clarification_response(self, context: TutoringContext) -> str:
        """Generate clarification of previous response."""
        return (
            "Let me try explaining that differently. "
            "Sometimes it helps to think about it another way. "
            "Is there a specific part that's confusing?"
        )

    def _generate_default_response(self, context: TutoringContext) -> str:
        """Generate default helpful response."""
        return (
            "I'm here to help! "
            "You can ask me to explain something, give you a hint, "
            "or check your answer. What would be most helpful?"
        )

    async def _handle_repeat_request(self) -> SpeechResponse:
        """Handle request to repeat last response."""
        history = self.voice_bridge._conversation_history
        if history:
            last_response = history[-1][1]
            return SpeechResponse(
                text=last_response.text,
                speed=0.85,  # Slightly slower on repeat
                tone="explaining",
            )
        else:
            return SpeechResponse(
                text="I haven't said anything yet! What would you like help with?",
                tone="encouraging",
            )

    async def _handle_slower_request(self) -> SpeechResponse:
        """Handle request for slower speech."""
        return SpeechResponse(
            text="Of course! I'll speak more slowly. Just let me know if you need me to go even slower.",
            speed=0.75,
            tone="gentle",
        )

    async def _handle_skip_request(self) -> SpeechResponse:
        """Handle request to skip current problem."""
        self._current_visual_context = None
        self.context_builder.reset_session()

        return SpeechResponse(
            text="No problem! Let's move on. Show me the next thing you'd like to work on.",
            tone="encouraging",
        )

    async def _deliver_response(self, response: SpeechResponse) -> None:
        """Deliver speech response via TTS."""
        self._set_state(PipelineState.SPEAKING_RESPONSE)

        # Publish event for TTS engine
        await self.event_bus.publish(
            create_event(
                EventType.AUDIO_TTS_STARTED,
                source="homework_assistant",
                text=response.text,
                ssml=response.ssml,
                speed=response.speed,
                tone=response.tone,
            )
        )

        # Call callback if registered
        if self._on_response_ready:
            self._on_response_ready(response)

    async def _followup_timeout(self) -> None:
        """Handle timeout waiting for follow-up."""
        await asyncio.sleep(self._followup_timeout_seconds)

        if self._state == PipelineState.AWAITING_FOLLOWUP:
            # Prompt for continuation
            prompt = SpeechResponse(
                text="Are you still there? Let me know if you need more help!",
                tone="gentle",
            )
            await self._deliver_response(prompt)

            # Wait a bit more then go idle
            await asyncio.sleep(self._followup_timeout_seconds)
            if self._state == PipelineState.AWAITING_FOLLOWUP:
                self._set_state(PipelineState.IDLE)

    def _set_state(self, new_state: PipelineState) -> None:
        """Update pipeline state."""
        old_state = self._state
        self._state = new_state

        logger.debug(f"Pipeline: {old_state.name} -> {new_state.name}")

        if self._on_state_change:
            self._on_state_change(new_state)

    def _determine_response_type(self, intent: QueryIntent) -> str:
        """Map intent to response type."""
        mapping = {
            QueryIntent.HELP_REQUEST: "explanation",
            QueryIntent.HINT_REQUEST: "hint",
            QueryIntent.CHECK_ANSWER: "feedback",
            QueryIntent.EXPLAIN_CONCEPT: "explanation",
            QueryIntent.CLARIFICATION: "explanation",
        }
        return mapping.get(intent, "explanation")

    def _get_current_hint_level(self) -> int:
        """Get current hint level for the problem."""
        if self._current_session_id:
            session = self.session_manager.get_session(self._current_session_id)
            if session:
                return session.current_hint_level
        return 0

    def _map_intent_to_interaction(self, intent: QueryIntent) -> InteractionType:
        """Map query intent to interaction type."""
        mapping = {
            QueryIntent.HELP_REQUEST: InteractionType.PROBLEM_HELP,
            QueryIntent.HINT_REQUEST: InteractionType.HINT_GIVEN,
            QueryIntent.CHECK_ANSWER: InteractionType.ANSWER_CHECK,
            QueryIntent.EXPLAIN_CONCEPT: InteractionType.CONCEPT_EXPLANATION,
            QueryIntent.CLARIFICATION: InteractionType.CLARIFICATION,
        }
        return mapping.get(intent, InteractionType.PROBLEM_HELP)

    def _update_metrics(self, latency_ms: float) -> None:
        """Update pipeline metrics."""
        self._metrics.total_requests += 1
        self._metrics.successful_responses += 1

        self._latency_history.append(latency_ms)
        if len(self._latency_history) > 100:
            self._latency_history = self._latency_history[-100:]

        self._metrics.average_latency_ms = sum(self._latency_history) / len(self._latency_history)

    def get_metrics(self) -> PipelineMetrics:
        """Get current pipeline metrics."""
        return self._metrics

    def end_session(self) -> dict[str, Any] | None:
        """End current tutoring session."""
        if self._current_session_id:
            stats = self.session_manager.end_session(self._current_session_id)
            self._current_session_id = None
            self._current_visual_context = None
            self._set_state(PipelineState.IDLE)

            # Reset conversation history
            self.voice_bridge.reset_conversation()
            self.context_builder.reset_session()

            if stats:
                return {
                    "total_interactions": stats.total_interactions,
                    "problems_attempted": stats.problems_attempted,
                    "problems_correct": stats.problems_correct,
                    "hints_given": stats.hints_given,
                    "total_time_minutes": stats.total_time_minutes,
                }

        return None

    def set_student_profile(self, profile: StudentProfile) -> None:
        """Set the current student profile for personalization."""
        self._current_student_profile = profile

    def on_response_ready(self, callback: Callable[[SpeechResponse], None]) -> None:
        """Register callback for when responses are ready."""
        self._on_response_ready = callback

    def on_state_change(self, callback: Callable[[PipelineState], None]) -> None:
        """Register callback for state changes."""
        self._on_state_change = callback


def create_homework_assistant() -> HomeworkAssistant:
    """Factory function to create a configured homework assistant."""
    return HomeworkAssistant()
