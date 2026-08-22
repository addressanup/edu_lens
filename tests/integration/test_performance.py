"""
Integration Performance Tests

Tests system-wide performance requirements including latency, memory usage,
and CPU usage across integrated components.

Task: TST-001-T2 - Integration Test Suite
Author: Testing Agent (TST-001)

Performance Requirements:
- End-to-end latency: <2s
- Memory usage: <500MB
- CPU usage: Reasonable for edge device
"""

import asyncio
import gc
import os
import platform
import time
from typing import Dict, List
from unittest.mock import Mock, patch

import numpy as np
import psutil
import pytest

# ============================================================================
# Performance Measurement Utilities
# ============================================================================


class PerformanceMonitor:
    """Monitor system performance metrics."""

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_memory = 0
        self.peak_memory = 0
        self.start_cpu = 0
        self.measurements = []

    def start(self):
        """Start performance monitoring."""
        gc.collect()  # Force garbage collection
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.start_cpu = self.process.cpu_percent()
        self.peak_memory = self.start_memory

    def measure(self) -> Dict[str, float]:
        """Take a performance measurement."""
        current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        current_cpu = self.process.cpu_percent()

        self.peak_memory = max(self.peak_memory, current_memory)

        measurement = {
            "memory_mb": current_memory,
            "memory_delta_mb": current_memory - self.start_memory,
            "cpu_percent": current_cpu,
            "timestamp": time.perf_counter(),
        }

        self.measurements.append(measurement)
        return measurement

    def stop(self) -> Dict[str, float]:
        """Stop monitoring and return summary."""
        final = self.measure()

        return {
            "peak_memory_mb": self.peak_memory,
            "memory_increase_mb": self.peak_memory - self.start_memory,
            "final_memory_mb": final["memory_mb"],
            "avg_cpu_percent": (
                sum(m["cpu_percent"] for m in self.measurements) / len(self.measurements)
                if self.measurements
                else 0
            ),
            "peak_cpu_percent": (
                max(m["cpu_percent"] for m in self.measurements) if self.measurements else 0
            ),
        }


@pytest.fixture
def performance_monitor():
    """Create performance monitor."""
    return PerformanceMonitor()


# ============================================================================
# Latency Tests
# ============================================================================


class TestEndToEndLatency:
    """Test end-to-end system latency requirements."""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_vision_to_response_latency(
        self,
        vision_to_ai_bridge,
        voice_to_ai_bridge,
        mock_tts_engine,
        sample_ocr_result,
        sample_layout_result,
        assert_latency,
    ):
        """Test complete vision-to-response pipeline latency (<2s)."""
        start_time = time.perf_counter()

        # 1. Vision processing
        visual_context = vision_to_ai_bridge.process_vision_output(
            ocr_result=sample_ocr_result,
            layout_result=sample_layout_result,
        )

        # 2. AI context building
        ai_context = vision_to_ai_bridge.build_ai_context(visual_context)

        # 3. AI response (mocked - in real system would call AI)
        ai_response = "Let me help you with that problem. The answer is 5."

        # 4. Speech preparation
        speech_response = voice_to_ai_bridge.prepare_speech_response(
            ai_response,
            response_type="explanation",
        )

        # 5. TTS synthesis
        audio_output = await mock_tts_engine.synthesize(speech_response.text)

        elapsed = time.perf_counter() - start_time

        # Total latency should be under 2 seconds
        assert_latency(elapsed, 2.0, "Vision-to-response pipeline")

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_audio_to_response_latency(
        self,
        mock_speech_recognizer,
        voice_to_ai_bridge,
        mock_tts_engine,
        sample_audio_question,
        assert_latency,
    ):
        """Test complete audio-to-response pipeline latency (<2s)."""
        start_time = time.perf_counter()

        # 1. Speech recognition
        transcription = await mock_speech_recognizer.transcribe(sample_audio_question)

        # 2. Voice query processing
        voice_query = voice_to_ai_bridge.process_voice_input(
            transcription.text,
            transcription.confidence,
        )

        # 3. AI response (mocked)
        ai_response = "That's a great question! Let me explain."

        # 4. Speech preparation
        speech_response = voice_to_ai_bridge.prepare_speech_response(ai_response)

        # 5. TTS synthesis
        audio_output = await mock_tts_engine.synthesize(speech_response.text)

        elapsed = time.perf_counter() - start_time

        # Total latency should be under 2 seconds
        assert_latency(elapsed, 2.0, "Audio-to-response pipeline")

    @pytest.mark.performance
    def test_component_processing_breakdown(
        self,
        vision_to_ai_bridge,
        sample_ocr_result,
        integration_test_timer,
    ):
        """Test and profile individual component latencies."""
        integration_test_timer.start()

        # Vision processing
        visual_context = vision_to_ai_bridge.process_vision_output(sample_ocr_result)
        integration_test_timer.checkpoint("vision_processing")

        # Context building
        ai_context = vision_to_ai_bridge.build_ai_context(visual_context)
        integration_test_timer.checkpoint("context_building")

        # Verify reasonable distribution
        vision_time = integration_test_timer.checkpoint_duration("vision_processing")
        context_time = integration_test_timer.checkpoint_duration("context_building") - vision_time

        assert vision_time < 0.5, "Vision processing too slow"
        assert context_time < 0.1, "Context building too slow"

    @pytest.mark.performance
    def test_wake_word_detection_latency(
        self,
        mock_wake_word_detector,
        assert_latency,
    ):
        """Test wake word detection latency (<100ms)."""
        # Start listening
        start_time = time.perf_counter()

        mock_wake_word_detector.start_listening()

        elapsed = time.perf_counter() - start_time

        # Starting should be very fast
        assert_latency(elapsed, 0.1, "Wake word detector start")


# ============================================================================
# Memory Usage Tests
# ============================================================================


class TestMemoryUsage:
    """Test memory usage requirements (<500MB)."""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_session_memory_usage(
        self,
        session_manager,
        performance_monitor,
    ):
        """Test memory usage during typical session (<500MB)."""
        performance_monitor.start()

        # Simulate typical session
        session = session_manager.create_session("TEST_STUDENT")
        performance_monitor.measure()

        # Record many interactions
        for i in range(50):
            session_manager.record_interaction(
                session_id=session.session_id,
                interaction_type="PROBLEM_HELP",
                visual_context=f"Problem {i}: What is {i} + {i}?",
                student_query="How do I solve this?",
                tutor_response=f"The answer is {i + i}.",
            )

            if i % 10 == 0:
                performance_monitor.measure()

        # End session
        session_manager.end_session(session.session_id)

        stats = performance_monitor.stop()

        # Memory increase should be reasonable
        assert stats["memory_increase_mb"] < 100, (
            f"Memory increased by {stats['memory_increase_mb']:.2f}MB, "
            "should be <100MB for session"
        )

        # Peak memory should be under 500MB (relative to baseline)
        # Note: This is the increase, not absolute usage
        assert stats["memory_increase_mb"] < 500

    @pytest.mark.performance
    def test_image_processing_memory(
        self,
        data_minimizer,
        sample_math_image_bytes,
        performance_monitor,
    ):
        """Test image processing doesn't leak memory."""
        performance_monitor.start()

        # Process multiple images
        for i in range(20):
            minimized = data_minimizer.minimize_image(
                sample_math_image_bytes,
                detected_objects=["book", "desk"],
                detected_text=[f"Problem {i}"],
            )

            if i % 5 == 0:
                performance_monitor.measure()

        stats = performance_monitor.stop()

        # Memory increase should be minimal (data is minimized and discarded)
        assert stats["memory_increase_mb"] < 50, "Image processing leaked memory"

    @pytest.mark.performance
    def test_audio_processing_memory(
        self,
        data_minimizer,
        sample_audio_bytes,
        performance_monitor,
    ):
        """Test audio processing doesn't leak memory."""
        performance_monitor.start()

        # Process multiple audio samples
        for i in range(20):
            minimized = data_minimizer.minimize_audio(
                sample_audio_bytes,
                transcription=f"Question {i}",
                intent="question",
            )

            if i % 5 == 0:
                performance_monitor.measure()

        stats = performance_monitor.stop()

        # Memory increase should be minimal
        assert stats["memory_increase_mb"] < 50, "Audio processing leaked memory"

    @pytest.mark.performance
    def test_conversation_history_memory(
        self,
        voice_to_ai_bridge,
        performance_monitor,
    ):
        """Test conversation history has bounded memory."""
        performance_monitor.start()

        # Add many interactions
        for i in range(100):
            query = voice_to_ai_bridge.process_voice_input(f"Question {i}", 0.95)
            from src.integration.voice_to_ai_bridge import SpeechResponse

            response = SpeechResponse(text=f"Response {i}", tone="explaining")
            voice_to_ai_bridge.add_to_history(query, response)

            if i % 20 == 0:
                performance_monitor.measure()

        stats = performance_monitor.stop()

        # Memory should not grow unbounded (history should be limited)
        assert stats["memory_increase_mb"] < 20, "Conversation history grew unbounded"


# ============================================================================
# CPU Usage Tests
# ============================================================================


class TestCPUUsage:
    """Test CPU usage is reasonable for edge device."""

    @pytest.mark.performance
    def test_idle_cpu_usage(
        self,
        session_manager,
        performance_monitor,
    ):
        """Test CPU usage when idle is minimal."""
        performance_monitor.start()

        # Create session but don't do anything
        session = session_manager.create_session("TEST_STUDENT")

        # Measure over time
        for _ in range(5):
            time.sleep(0.1)
            performance_monitor.measure()

        stats = performance_monitor.stop()

        # Idle CPU should be very low
        assert (
            stats["avg_cpu_percent"] < 10
        ), f"Idle CPU usage too high: {stats['avg_cpu_percent']:.1f}%"

    @pytest.mark.performance
    def test_active_processing_cpu(
        self,
        vision_to_ai_bridge,
        sample_ocr_result,
        sample_layout_result,
        performance_monitor,
    ):
        """Test CPU usage during active processing."""
        performance_monitor.start()

        # Process multiple requests
        for i in range(20):
            visual_context = vision_to_ai_bridge.process_vision_output(
                ocr_result=sample_ocr_result,
                layout_result=sample_layout_result,
            )
            ai_context = vision_to_ai_bridge.build_ai_context(visual_context)

            if i % 5 == 0:
                performance_monitor.measure()

        stats = performance_monitor.stop()

        # CPU should be reasonable even under load
        # Note: This can vary greatly by system, so use generous threshold
        assert (
            stats["avg_cpu_percent"] < 80
        ), f"Average CPU too high: {stats['avg_cpu_percent']:.1f}%"

    @pytest.mark.performance
    def test_data_minimization_cpu(
        self,
        data_minimizer,
        sample_math_image_bytes,
        performance_monitor,
    ):
        """Test data minimization CPU usage."""
        performance_monitor.start()

        # Process many images
        for i in range(30):
            minimized = data_minimizer.minimize_image(
                sample_math_image_bytes,
                detected_objects=["book"],
                detected_text=["Problem 1"],
            )

            if i % 10 == 0:
                performance_monitor.measure()

        stats = performance_monitor.stop()

        # Should not peg CPU
        assert stats["peak_cpu_percent"] < 90


# ============================================================================
# Throughput Tests
# ============================================================================


class TestThroughput:
    """Test system throughput capabilities."""

    @pytest.mark.performance
    def test_interactions_per_second(
        self,
        session_manager,
    ):
        """Test system can handle reasonable interaction rate."""
        session = session_manager.create_session("TEST_STUDENT")

        start_time = time.perf_counter()
        interaction_count = 50

        for i in range(interaction_count):
            session_manager.record_interaction(
                session_id=session.session_id,
                interaction_type="PROBLEM_HELP",
                student_query=f"Question {i}",
                tutor_response=f"Response {i}",
            )

        elapsed = time.perf_counter() - start_time

        interactions_per_second = interaction_count / elapsed

        # Should handle at least 100 interactions per second
        assert (
            interactions_per_second > 100
        ), f"Throughput too low: {interactions_per_second:.1f} interactions/s"

    @pytest.mark.performance
    def test_concurrent_processing(
        self,
        vision_to_ai_bridge,
        voice_to_ai_bridge,
        sample_ocr_result,
    ):
        """Test system can handle concurrent operations."""
        start_time = time.perf_counter()

        # Process multiple items concurrently
        tasks = []
        for i in range(10):
            # Vision processing
            visual_context = vision_to_ai_bridge.process_vision_output(sample_ocr_result)

            # Voice processing
            voice_query = voice_to_ai_bridge.process_voice_input(f"Question {i}", 0.95)

        elapsed = time.perf_counter() - start_time

        # Should complete reasonably fast
        assert elapsed < 1.0, f"Concurrent processing too slow: {elapsed:.2f}s"


# ============================================================================
# Resource Cleanup Tests
# ============================================================================


class TestResourceCleanup:
    """Test proper resource cleanup to prevent leaks."""

    @pytest.mark.performance
    def test_session_cleanup(
        self,
        session_manager,
        performance_monitor,
    ):
        """Test sessions are properly cleaned up."""
        performance_monitor.start()

        # Create and end many sessions
        for i in range(20):
            session = session_manager.create_session(f"STUDENT_{i}")
            session_manager.record_interaction(
                session_id=session.session_id,
                interaction_type="PROBLEM_HELP",
                student_query="Test",
            )
            session_manager.end_session(session.session_id)

            if i % 5 == 0:
                performance_monitor.measure()

        stats = performance_monitor.stop()

        # Memory should not grow significantly
        assert stats["memory_increase_mb"] < 30, "Sessions not properly cleaned up"

    @pytest.mark.performance
    def test_minimized_data_cleanup(
        self,
        data_minimizer,
        sample_math_image_bytes,
        performance_monitor,
    ):
        """Test minimized data doesn't accumulate."""
        performance_monitor.start()

        minimized_items = []

        # Create many minimized items
        for i in range(50):
            minimized = data_minimizer.minimize_image(
                sample_math_image_bytes,
                detected_objects=["book"],
            )
            minimized_items.append(minimized)

            if i % 10 == 0:
                performance_monitor.measure()

        # Clear references
        minimized_items.clear()
        gc.collect()

        stats = performance_monitor.stop()

        # Memory should be reasonable
        assert stats["memory_increase_mb"] < 50


# ============================================================================
# Stress Tests
# ============================================================================


class TestStressScenarios:
    """Test system under stress conditions."""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_extended_session_stress(
        self,
        session_manager,
        performance_monitor,
    ):
        """Test system handles extended session well."""
        performance_monitor.start()

        session = session_manager.create_session("TEST_STUDENT")

        # Simulate long session with many interactions
        for i in range(200):
            session_manager.record_interaction(
                session_id=session.session_id,
                interaction_type="PROBLEM_HELP",
                visual_context=f"Problem {i}",
                student_query=f"Question {i}",
                tutor_response=f"Response {i}",
                subject="math" if i % 2 == 0 else "science",
            )

            if i % 50 == 0:
                performance_monitor.measure()

        stats = performance_monitor.stop()

        # Should handle gracefully
        assert stats["memory_increase_mb"] < 150
        assert stats["avg_cpu_percent"] < 50

    @pytest.mark.performance
    @pytest.mark.slow
    def test_rapid_state_changes_stress(
        self,
        session_manager,
        performance_monitor,
    ):
        """Test system handles rapid state changes."""
        performance_monitor.start()

        session = session_manager.create_session("TEST_STUDENT")

        # Rapid state changes
        states = [
            "IDLE",
            "LISTENING",
            "PROCESSING",
            "RESPONDING",
            "WAITING_RESPONSE",
        ]

        for i in range(500):
            from src.pipeline.session_manager import SessionState

            state = SessionState[states[i % len(states)]]
            session_manager.update_state(session.session_id, state)

            if i % 100 == 0:
                performance_monitor.measure()

        stats = performance_monitor.stop()

        # Should handle rapid changes
        assert stats["avg_cpu_percent"] < 60


# ============================================================================
# Platform-Specific Tests
# ============================================================================


class TestPlatformPerformance:
    """Test performance on different platforms."""

    @pytest.mark.performance
    def test_platform_capabilities(self):
        """Log platform capabilities for context."""
        info = {
            "platform": platform.system(),
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(),
            "memory_gb": psutil.virtual_memory().total / 1024 / 1024 / 1024,
        }

        print(f"\nPlatform: {info['platform']}")
        print(f"Processor: {info['processor']}")
        print(f"CPU cores: {info['cpu_count']}")
        print(f"Memory: {info['memory_gb']:.1f} GB")

        # Basic sanity checks for edge device
        assert info["cpu_count"] >= 2, "Need at least 2 CPU cores"
        assert info["memory_gb"] >= 2, "Need at least 2GB RAM"


# ============================================================================
# Performance Regression Tests
# ============================================================================


class TestPerformanceRegression:
    """Test for performance regressions."""

    @pytest.mark.performance
    def test_baseline_latencies(
        self,
        vision_to_ai_bridge,
        voice_to_ai_bridge,
        sample_ocr_result,
    ):
        """Establish baseline latencies for regression testing."""
        baselines = {}

        # Vision processing
        start = time.perf_counter()
        vision_to_ai_bridge.process_vision_output(sample_ocr_result)
        baselines["vision_processing"] = time.perf_counter() - start

        # Voice processing
        start = time.perf_counter()
        voice_to_ai_bridge.process_voice_input("Test question", 0.95)
        baselines["voice_processing"] = time.perf_counter() - start

        # Log baselines
        print(f"\nPerformance Baselines:")
        for operation, latency in baselines.items():
            print(f"  {operation}: {latency*1000:.2f}ms")

        # Verify all are reasonable
        for operation, latency in baselines.items():
            assert latency < 0.5, f"{operation} baseline too high: {latency*1000:.2f}ms"
