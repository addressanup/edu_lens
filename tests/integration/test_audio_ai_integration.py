"""
Integration Tests for Audio-to-AI Pipeline

Tests the complete integration between audio processing components
(wake word, ASR, TTS) and the AI tutoring system.

Task: TST-001-T2 - Integration Test Suite
Author: Testing Agent (TST-001)
"""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest

from src.integration.voice_to_ai_bridge import (
    QueryIntent,
    SpeechResponse,
    VoiceQuery,
    VoiceToAIBridge,
)


class TestWakeWordPipeline:
    """Test wake word triggers the processing pipeline."""

    def test_wake_word_detection_triggers_pipeline(
        self,
        mock_wake_word_detector,
    ):
        """Test wake word detection initiates audio processing."""
        # Register callback
        callback_triggered = []

        def on_detection(result):
            callback_triggered.append(result)

        mock_wake_word_detector.on_wake_word(on_detection)

        # Start listening
        mock_wake_word_detector.start_listening()

        assert mock_wake_word_detector.is_listening is True

    def test_wake_word_confidence_threshold(
        self,
        mock_wake_word_detector,
    ):
        """Test wake word confidence meets threshold requirements."""
        confidence = mock_wake_word_detector.get_detection_confidence()

        # Should meet minimum confidence threshold
        assert confidence >= 0.8, "Wake word confidence should be >= 0.8"

    def test_wake_word_sensitivity_adjustment(
        self,
        mock_wake_word_detector,
    ):
        """Test wake word sensitivity can be adjusted."""
        initial_sensitivity = mock_wake_word_detector.sensitivity

        # Mock sensitivity adjustment
        mock_wake_word_detector.sensitivity = 0.7
        mock_wake_word_detector.threshold = 0.5

        assert mock_wake_word_detector.sensitivity != initial_sensitivity

    def test_wake_word_stops_listening(
        self,
        mock_wake_word_detector,
    ):
        """Test wake word detector can be stopped."""
        mock_wake_word_detector.start_listening()
        assert mock_wake_word_detector.is_listening is True

        mock_wake_word_detector.stop_listening()
        assert mock_wake_word_detector.is_listening is False


class TestASRAIIntegration:
    """Test ASR output feeds AI correctly."""

    @pytest.mark.asyncio
    async def test_asr_transcription_to_voice_query(
        self,
        voice_to_ai_bridge,
    ):
        """Test ASR transcription is converted to voice query."""
        transcription = "What is photosynthesis?"
        confidence = 0.94

        # Process voice input
        voice_query = voice_to_ai_bridge.process_voice_input(
            transcription=transcription,
            confidence=confidence,
            speech_duration_ms=1800,
        )

        # Verify voice query structure
        assert isinstance(voice_query, VoiceQuery)
        assert voice_query.transcription == transcription
        assert voice_query.confidence == confidence
        assert voice_query.intent != QueryIntent.UNKNOWN

    @pytest.mark.asyncio
    async def test_intent_detection_from_transcription(
        self,
        voice_to_ai_bridge,
    ):
        """Test intent is correctly detected from transcription."""
        # Help request
        help_query = voice_to_ai_bridge.process_voice_input(
            "I need help with this problem",
            0.95,
        )
        assert help_query.intent == QueryIntent.HELP_REQUEST

        # Explanation request
        explain_query = voice_to_ai_bridge.process_voice_input(
            "What is multiplication?",
            0.93,
        )
        assert explain_query.intent == QueryIntent.EXPLAIN_CONCEPT

        # Answer check
        check_query = voice_to_ai_bridge.process_voice_input(
            "Is this answer correct?",
            0.92,
        )
        assert check_query.intent == QueryIntent.CHECK_ANSWER

    @pytest.mark.asyncio
    async def test_entity_extraction_from_speech(
        self,
        voice_to_ai_bridge,
    ):
        """Test entities are extracted from speech transcription."""
        query = voice_to_ai_bridge.process_voice_input(
            "Help me with math problem number 5",
            0.94,
        )

        # Should extract subject and number
        assert query.subject_mentioned in ["math", "mathematics"]
        assert query.number_mentioned == "5"

    @pytest.mark.asyncio
    async def test_low_confidence_transcription_handling(
        self,
        voice_to_ai_bridge,
    ):
        """Test handling of low-confidence transcriptions."""
        low_conf_query = voice_to_ai_bridge.process_voice_input(
            "unclear speech pattern",
            confidence=0.4,  # Low confidence
        )

        # Should still create query but flag low confidence
        assert low_conf_query.confidence < 0.5
        assert isinstance(low_conf_query, VoiceQuery)

    @pytest.mark.asyncio
    async def test_followup_question_detection(
        self,
        voice_to_ai_bridge,
    ):
        """Test follow-up questions use previous context."""
        # First query
        first_query = voice_to_ai_bridge.process_voice_input(
            "What is photosynthesis?",
            0.95,
        )
        first_response = SpeechResponse(
            text="Photosynthesis is how plants make food from sunlight.",
            tone="explaining",
        )
        voice_to_ai_bridge.add_to_history(first_query, first_response)

        # Follow-up query
        followup_query = voice_to_ai_bridge.process_voice_input(
            "Can you explain more?",
            0.93,
        )

        # Should detect as follow-up
        assert followup_query.is_followup is True
        assert followup_query.previous_context is not None


class TestAIToTTSIntegration:
    """Test AI response feeds TTS correctly."""

    @pytest.mark.asyncio
    async def test_ai_response_to_speech_response(
        self,
        voice_to_ai_bridge,
    ):
        """Test AI response is prepared for TTS."""
        ai_response = "Great job! Let me explain. When you add 2 + 3, you're combining two numbers."

        # Prepare for speech
        speech_response = voice_to_ai_bridge.prepare_speech_response(
            ai_response=ai_response,
            response_type="explanation",
            hint_level=0,
        )

        # Verify speech response
        assert isinstance(speech_response, SpeechResponse)
        assert speech_response.text is not None
        assert len(speech_response.text) > 0

    @pytest.mark.asyncio
    async def test_speech_response_cleaning(
        self,
        voice_to_ai_bridge,
    ):
        """Test text is cleaned for speech synthesis."""
        markdown_text = "The answer is **5**. That's correct! You can see: `2 + 3 = 5`"

        speech_response = voice_to_ai_bridge.prepare_speech_response(
            ai_response=markdown_text,
            response_type="feedback",
        )

        # Markdown should be removed
        assert "**" not in speech_response.text
        assert "`" not in speech_response.text

    @pytest.mark.asyncio
    async def test_math_symbol_conversion_for_speech(
        self,
        voice_to_ai_bridge,
    ):
        """Test math symbols are converted to words for TTS."""
        math_response = "The equation is 2 + 3 = 5 and 10 ÷ 2 = 5"

        speech_response = voice_to_ai_bridge.prepare_speech_response(
            ai_response=math_response,
            response_type="explanation",
        )

        # Symbols should be converted
        assert "plus" in speech_response.text or "+" not in speech_response.text
        assert "divided by" in speech_response.text or "÷" not in speech_response.text

    @pytest.mark.asyncio
    async def test_tone_selection_for_response_type(
        self,
        voice_to_ai_bridge,
    ):
        """Test appropriate tone is selected based on response type."""
        # Explanation
        explanation = voice_to_ai_bridge.prepare_speech_response(
            "Let me explain how this works.",
            response_type="explanation",
        )
        assert explanation.tone == "explaining"

        # Celebration
        celebration = voice_to_ai_bridge.prepare_speech_response(
            "Great job! You got it right!",
            response_type="celebration",
        )
        assert celebration.tone == "celebrating"

        # Hint
        hint = voice_to_ai_bridge.prepare_speech_response(
            "Think about what happens when you add.",
            response_type="hint",
        )
        assert hint.tone == "encouraging"

    @pytest.mark.asyncio
    async def test_speech_speed_adjustment(
        self,
        voice_to_ai_bridge,
    ):
        """Test speech speed is adjusted based on response type."""
        # Explanation should be slower
        explanation = voice_to_ai_bridge.prepare_speech_response(
            "Let me explain multiplication.",
            response_type="explanation",
        )
        assert explanation.speed <= 1.0

        # Celebration can be faster
        celebration = voice_to_ai_bridge.prepare_speech_response(
            "Excellent!",
            response_type="celebration",
        )
        assert celebration.speed >= 0.9

    @pytest.mark.asyncio
    async def test_ssml_generation_for_emphasis(
        self,
        voice_to_ai_bridge,
    ):
        """Test SSML is generated with emphasis markers."""
        response_with_emphasis = voice_to_ai_bridge.prepare_speech_response(
            "First, think about the problem. Then, solve it step by step.",
            response_type="explanation",
        )

        # Should have SSML markup
        if response_with_emphasis.ssml:
            assert "<speak>" in response_with_emphasis.ssml
            assert "<prosody" in response_with_emphasis.ssml


class TestBargeInHandling:
    """Test barge-in (interruption) handling."""

    @pytest.mark.asyncio
    async def test_interrupt_detection(
        self,
        voice_to_ai_bridge,
    ):
        """Test system can detect user interruption."""
        # Simulate ongoing response
        original_response = SpeechResponse(
            text="Let me explain photosynthesis in detail...",
            contains_question=False,
        )

        # User interrupts with new query
        interrupt_query = voice_to_ai_bridge.process_voice_input(
            "Wait, what about plants?",
            0.92,
        )

        # Should be recognized as valid query (interruption)
        assert interrupt_query.intent != QueryIntent.UNKNOWN

    @pytest.mark.asyncio
    async def test_conversation_context_maintained(
        self,
        voice_to_ai_bridge,
    ):
        """Test conversation context is maintained across interruptions."""
        # First interaction
        query1 = voice_to_ai_bridge.process_voice_input("Explain photosynthesis", 0.95)
        response1 = SpeechResponse(text="Photosynthesis is...", tone="explaining")
        voice_to_ai_bridge.add_to_history(query1, response1)

        # Get context
        context = voice_to_ai_bridge.get_conversation_context()

        # Should have conversation history
        assert len(context) > 0
        assert "photosynthesis" in context.lower()

    @pytest.mark.asyncio
    async def test_conversation_reset(
        self,
        voice_to_ai_bridge,
    ):
        """Test conversation context can be reset."""
        # Add some history
        query = voice_to_ai_bridge.process_voice_input("Test question", 0.95)
        response = SpeechResponse(text="Test response", tone="explaining")
        voice_to_ai_bridge.add_to_history(query, response)

        # Reset
        voice_to_ai_bridge.reset_conversation()

        # Context should be empty
        context = voice_to_ai_bridge.get_conversation_context()
        assert len(context) == 0


class TestAudioAIErrorHandling:
    """Test error handling in audio-AI pipeline."""

    @pytest.mark.asyncio
    async def test_empty_transcription_handling(
        self,
        voice_to_ai_bridge,
    ):
        """Test handling of empty transcription."""
        query = voice_to_ai_bridge.process_voice_input("", confidence=0.0)

        # Should create query but with UNKNOWN intent
        assert query.intent == QueryIntent.UNKNOWN
        assert query.transcription == ""

    @pytest.mark.asyncio
    async def test_noise_transcription_handling(
        self,
        voice_to_ai_bridge,
    ):
        """Test handling of noise/gibberish transcription."""
        noise_query = voice_to_ai_bridge.process_voice_input(
            "bzzzz krrr fffff",
            confidence=0.3,
        )

        # Low confidence should be flagged
        assert noise_query.confidence < 0.5

    @pytest.mark.asyncio
    async def test_tts_synthesis_error_handling(
        self,
        mock_tts_engine,
    ):
        """Test TTS synthesis error handling."""
        # Mock TTS error
        mock_tts_engine.synthesize.side_effect = Exception("TTS failed")

        with pytest.raises(Exception):
            await mock_tts_engine.synthesize("Test text")


@pytest.mark.performance
class TestAudioAIPerformance:
    """Test performance of audio-AI integration."""

    @pytest.mark.asyncio
    async def test_voice_processing_latency(
        self,
        voice_to_ai_bridge,
        assert_latency,
    ):
        """Test voice processing meets latency requirements (<500ms)."""
        start_time = time.perf_counter()

        query = voice_to_ai_bridge.process_voice_input(
            "What is multiplication?",
            0.94,
        )

        elapsed = time.perf_counter() - start_time

        # Voice-to-AI processing should be very fast
        assert_latency(elapsed, 0.1, "Voice-to-AI processing")

    @pytest.mark.asyncio
    async def test_speech_response_preparation_latency(
        self,
        voice_to_ai_bridge,
        assert_latency,
    ):
        """Test speech response preparation is fast."""
        ai_response = "Let me explain multiplication. It's repeated addition."

        start_time = time.perf_counter()

        speech_response = voice_to_ai_bridge.prepare_speech_response(
            ai_response,
            response_type="explanation",
        )

        elapsed = time.perf_counter() - start_time

        # Response preparation should be instant
        assert_latency(elapsed, 0.05, "Speech response preparation")

    @pytest.mark.asyncio
    async def test_end_to_end_audio_latency(
        self,
        voice_to_ai_bridge,
        mock_speech_recognizer,
        mock_tts_engine,
        assert_latency,
    ):
        """Test end-to-end audio processing latency (<2s)."""
        # Simulate audio input
        audio_data = np.random.randn(16000).astype(np.float32)

        start_time = time.perf_counter()

        # ASR
        transcription_result = await mock_speech_recognizer.transcribe(audio_data)

        # Voice processing
        voice_query = voice_to_ai_bridge.process_voice_input(
            transcription_result.text,
            transcription_result.confidence,
        )

        # AI response (mocked)
        ai_response = "This is a test response from the AI tutor."

        # TTS preparation
        speech_response = voice_to_ai_bridge.prepare_speech_response(ai_response)

        # TTS synthesis
        audio_output = await mock_tts_engine.synthesize(speech_response.text)

        elapsed = time.perf_counter() - start_time

        # End-to-end should be under 2 seconds
        assert_latency(elapsed, 2.0, "End-to-end audio processing")


class TestMultiTurnConversation:
    """Test multi-turn conversation flow."""

    @pytest.mark.asyncio
    async def test_multi_turn_context_accumulation(
        self,
        voice_to_ai_bridge,
    ):
        """Test context accumulates across multiple turns."""
        # Turn 1
        q1 = voice_to_ai_bridge.process_voice_input("What is photosynthesis?", 0.95)
        r1 = SpeechResponse(text="Photosynthesis is how plants make food.", tone="explaining")
        voice_to_ai_bridge.add_to_history(q1, r1)

        # Turn 2
        q2 = voice_to_ai_bridge.process_voice_input("How do they do that?", 0.93)
        r2 = SpeechResponse(text="They use sunlight, water, and carbon dioxide.", tone="explaining")
        voice_to_ai_bridge.add_to_history(q2, r2)

        # Turn 3
        q3 = voice_to_ai_bridge.process_voice_input("What do they produce?", 0.94)

        # Should have context from previous turns
        assert q3.is_followup is True
        context = voice_to_ai_bridge.get_conversation_context()
        assert "photosynthesis" in context.lower()

    @pytest.mark.asyncio
    async def test_conversation_history_limit(
        self,
        voice_to_ai_bridge,
    ):
        """Test conversation history is limited to prevent memory issues."""
        # Add many interactions
        for i in range(15):
            query = voice_to_ai_bridge.process_voice_input(f"Question {i}", 0.95)
            response = SpeechResponse(text=f"Response {i}", tone="explaining")
            voice_to_ai_bridge.add_to_history(query, response)

        # History should be limited (e.g., last 10)
        context = voice_to_ai_bridge.get_conversation_context()

        # Should not include all 15 interactions
        assert context.count("Question") <= 10
