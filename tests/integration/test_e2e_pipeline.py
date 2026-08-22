"""
End-to-End Pipeline Integration Tests for EduLens

Tests the complete Vision → AI → Voice flow with all components integrated.
Validates the full tutoring pipeline from frame capture to TTS output.

Author: Integration Agent (INT-001)
Version: 1.0.0
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.event_bus import Event, EventType, get_event_bus
from src.integration.vision_to_ai_bridge import ContentType, SubjectArea, VisualContext
from src.pipeline.edulens_pipeline import (
    EduLensPipeline,
    PipelineConfig,
    PipelineMode,
    create_pipeline,
)
from src.pipeline.error_handler import (
    ErrorCategory,
    ErrorHandler,
    RecoveryConfig,
    create_error_handler,
)
from src.pipeline.health_checker import (
    HealthCheckConfig,
    HealthChecker,
    HealthStatus,
    create_health_checker,
)
from src.pipeline.pipeline_coordinator import PipelineCoordinator, TaskPriority, create_coordinator


class TestEduLensPipeline:
    """Test suite for the main EduLens pipeline."""

    @pytest.fixture
    async def pipeline(self):
        """Create a pipeline instance for testing."""
        config = PipelineConfig(
            mode=PipelineMode.FULL,
            student_age=8,
            student_grade="3",
            enable_vision=True,
            enable_audio=False,  # Disable audio for unit tests
        )

        pipeline = EduLensPipeline(config=config)
        await pipeline.initialize()

        yield pipeline

        await pipeline.stop()

    @pytest.mark.asyncio
    async def test_pipeline_initialization(self, pipeline):
        """Test pipeline initializes correctly."""
        assert pipeline is not None
        assert pipeline._vision_bridge is not None
        assert pipeline._tutor_engine is not None
        assert pipeline._context_builder is not None

    @pytest.mark.asyncio
    async def test_start_stop_pipeline(self, pipeline):
        """Test pipeline can start and stop."""
        await pipeline.start()
        assert pipeline._state.name == "RUNNING"

        await pipeline.stop()
        assert pipeline._state.name == "STOPPED"

    @pytest.mark.asyncio
    async def test_start_session(self, pipeline):
        """Test starting a tutoring session."""
        await pipeline.start()

        session_id = await pipeline.start_session(student_id="test_student_123")

        assert session_id is not None
        assert pipeline._current_session_id == session_id
        assert pipeline._stats.sessions_started == 1

    @pytest.mark.asyncio
    async def test_process_frame(self, pipeline):
        """Test processing a camera frame."""
        await pipeline.start()
        await pipeline.start_session()

        # Mock OCR result
        ocr_result = {"full_text": "What is 5 + 3?", "average_confidence": 0.95}

        visual_context = await pipeline.process_frame(frame_data=None, ocr_result=ocr_result)

        assert visual_context is not None
        assert visual_context.full_text == "What is 5 + 3?"
        assert pipeline._stats.frames_processed == 1

    @pytest.mark.asyncio
    async def test_generate_response(self, pipeline):
        """Test generating AI response."""
        await pipeline.start()
        await pipeline.start_session()

        response = await pipeline.generate_response(student_query="What is 5 + 3?")

        assert response is not None
        assert "response" in response
        assert "response_type" in response
        assert pipeline._stats.responses_generated == 1

    @pytest.mark.asyncio
    async def test_process_interaction(self, pipeline):
        """Test complete interaction flow."""
        await pipeline.start()
        await pipeline.start_session()

        response_text = await pipeline.process_interaction(
            student_query="Help me with this math problem"
        )

        assert response_text is not None
        assert len(response_text) > 0

    @pytest.mark.asyncio
    async def test_health_check(self, pipeline):
        """Test pipeline health check."""
        await pipeline.start()

        health = await pipeline.health_check()

        assert health is not None
        assert health.is_healthy
        assert "sessions_started" in health.metrics

    @pytest.mark.asyncio
    async def test_get_stats(self, pipeline):
        """Test retrieving pipeline statistics."""
        await pipeline.start()
        await pipeline.start_session()
        await pipeline.process_interaction("test query")

        stats = pipeline.get_stats()

        assert stats.sessions_started >= 1
        assert stats.responses_generated >= 1


class TestPipelineCoordinator:
    """Test suite for the pipeline coordinator."""

    @pytest.fixture
    async def coordinator(self):
        """Create coordinator for testing."""
        coord = await create_coordinator(max_concurrent_tasks=3, max_queue_size=10)

        yield coord

        await coord.stop()

    @pytest.mark.asyncio
    async def test_coordinator_start_stop(self, coordinator):
        """Test coordinator starts and stops."""
        assert coordinator._is_running

        await coordinator.stop()
        assert not coordinator._is_running

    @pytest.mark.asyncio
    async def test_schedule_task(self, coordinator):
        """Test scheduling a task."""

        async def test_task():
            await asyncio.sleep(0.1)
            return "task_result"

        task_id = await coordinator.schedule_task(
            task_type="test_task", coroutine=test_task(), priority=TaskPriority.NORMAL
        )

        assert task_id is not None
        assert coordinator._stats.tasks_scheduled == 1

        # Wait for task completion
        result = await coordinator.wait_for_task(task_id, timeout=1.0)
        assert result == "task_result"

    @pytest.mark.asyncio
    async def test_concurrent_tasks(self, coordinator):
        """Test multiple concurrent tasks."""

        async def test_task(delay: float):
            await asyncio.sleep(delay)
            return f"result_{delay}"

        task_ids = []
        for i in range(5):
            task_id = await coordinator.schedule_task(
                task_type=f"test_task_{i}",
                coroutine=test_task(0.1 * i),
                priority=TaskPriority.NORMAL,
            )
            task_ids.append(task_id)

        # Wait for all tasks
        for task_id in task_ids:
            result = await coordinator.wait_for_task(task_id, timeout=2.0)
            assert result is not None

        stats = coordinator.get_stats()
        assert stats.tasks_completed == 5

    @pytest.mark.asyncio
    async def test_priority_scheduling(self, coordinator):
        """Test priority-based task scheduling."""
        results = []

        async def priority_task(name: str):
            await asyncio.sleep(0.1)
            results.append(name)
            return name

        # Schedule tasks with different priorities
        await coordinator.schedule_task(
            task_type="low", coroutine=priority_task("low"), priority=TaskPriority.LOW
        )

        await coordinator.schedule_task(
            task_type="critical",
            coroutine=priority_task("critical"),
            priority=TaskPriority.CRITICAL,
        )

        await coordinator.schedule_task(
            task_type="high", coroutine=priority_task("high"), priority=TaskPriority.HIGH
        )

        # Wait for completion
        await asyncio.sleep(1.0)

        # Higher priority should execute first
        assert results[0] == "critical"


class TestErrorHandler:
    """Test suite for error handling."""

    @pytest.fixture
    def error_handler(self):
        """Create error handler for testing."""
        config = RecoveryConfig(max_retries=2, retry_delay_seconds=0.1)
        return create_error_handler(config=config)

    @pytest.mark.asyncio
    async def test_handle_vision_error(self, error_handler):
        """Test handling vision errors."""
        error = Exception("Camera connection failed")

        success, result = await error_handler.handle_vision_error(
            error=error, component="camera_module", context={"frame_id": 123}
        )

        assert error_handler._stats.total_errors == 1
        assert ErrorCategory.VISION in error_handler._stats.errors_by_category

    @pytest.mark.asyncio
    async def test_handle_audio_error(self, error_handler):
        """Test handling audio errors."""
        error = Exception("Microphone unavailable")

        success, result = await error_handler.handle_audio_error(
            error=error, component="microphone", context={}
        )

        assert error_handler._stats.total_errors == 1
        assert ErrorCategory.AUDIO in error_handler._stats.errors_by_category

    @pytest.mark.asyncio
    async def test_handle_ai_error(self, error_handler):
        """Test handling AI errors."""
        error = Exception("Model inference timeout")

        success, result = await error_handler.handle_ai_error(
            error=error, component="tutor_engine", context={}
        )

        assert error_handler._stats.total_errors == 1
        assert ErrorCategory.AI in error_handler._stats.errors_by_category

    @pytest.mark.asyncio
    async def test_error_recovery(self, error_handler):
        """Test error recovery mechanism."""

        async def recovery_function():
            return "recovered"

        error = Exception("Test error")
        error_record = error_handler._create_error_record(
            category=ErrorCategory.VISION, error=error, component="test_component", context={}
        )

        success, result = await error_handler.recover(
            error_record=error_record, recovery_fn=recovery_function
        )

        assert success
        assert result == "recovered"
        assert error_handler._stats.successful_recoveries == 1

    @pytest.mark.asyncio
    async def test_error_escalation(self, error_handler):
        """Test error escalation."""
        error = Exception("Critical failure")
        error_record = error_handler._create_error_record(
            category=ErrorCategory.HARDWARE, error=error, component="hardware", context={}
        )

        await error_handler.escalate(error_record=error_record, reason="Critical hardware failure")

        assert error_handler._stats.escalations == 1

    def test_component_degradation(self, error_handler):
        """Test component degradation marking."""
        component_name = "test_component"

        error_handler.mark_component_degraded(component_name)
        assert error_handler.is_component_degraded(component_name)

    def test_should_escalate(self, error_handler):
        """Test escalation threshold."""
        component = "failing_component"

        # Simulate multiple errors
        for i in range(error_handler.config.escalation_threshold):
            error_handler._error_counts[component] += 1

        assert error_handler.should_escalate(component)


class TestHealthChecker:
    """Test suite for health checking."""

    @pytest.fixture
    async def health_checker(self):
        """Create health checker for testing."""
        config = HealthCheckConfig(check_interval_seconds=1.0)
        return create_health_checker(config=config)

    @pytest.mark.asyncio
    async def test_register_component(self, health_checker):
        """Test component registration."""
        from src.pipeline.health_checker import ComponentType

        mock_component = MagicMock()
        mock_component.health_check = AsyncMock(return_value=True)

        health_checker.register_component(
            component_name="test_component",
            component_type=ComponentType.VISION,
            component=mock_component,
        )

        assert "test_component" in health_checker._components

    @pytest.mark.asyncio
    async def test_check_component_health(self, health_checker):
        """Test checking component health."""
        from src.pipeline.health_checker import ComponentType

        mock_component = MagicMock()
        mock_component.health_check = AsyncMock(return_value=True)

        health_checker.register_component(
            component_name="test_component",
            component_type=ComponentType.VISION,
            component=mock_component,
        )

        health = await health_checker.get_component_status("test_component")

        assert health is not None
        assert health.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_all_components(self, health_checker):
        """Test checking all components."""
        from src.pipeline.health_checker import ComponentType

        # Register multiple components
        for i in range(3):
            mock_component = MagicMock()
            mock_component.health_check = AsyncMock(return_value=True)

            health_checker.register_component(
                component_name=f"component_{i}",
                component_type=ComponentType.PIPELINE,
                component=mock_component,
            )

        system_health = await health_checker.check_all_components()

        assert system_health is not None
        assert len(system_health.components) == 3
        assert system_health.overall_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

    @pytest.mark.asyncio
    async def test_run_diagnostics(self, health_checker):
        """Test running diagnostics."""
        from src.pipeline.health_checker import ComponentType

        mock_component = MagicMock()
        mock_component.health_check = AsyncMock(return_value=True)

        health_checker.register_component(
            component_name="test_component",
            component_type=ComponentType.AI,
            component=mock_component,
        )

        results = await health_checker.run_diagnostics()

        assert len(results) > 0
        assert all(hasattr(r, "passed") for r in results)

    @pytest.mark.asyncio
    async def test_health_monitoring(self, health_checker):
        """Test automatic health monitoring."""
        from src.pipeline.health_checker import ComponentType

        mock_component = MagicMock()
        mock_component.health_check = AsyncMock(return_value=True)

        health_checker.register_component(
            component_name="monitored_component",
            component_type=ComponentType.AUDIO,
            component=mock_component,
        )

        # Start monitoring
        await health_checker.start_monitoring()
        assert health_checker._is_monitoring

        # Wait for a few checks
        await asyncio.sleep(2.5)

        # Stop monitoring
        await health_checker.stop_monitoring()
        assert not health_checker._is_monitoring

        # Should have collected some health history
        assert len(health_checker._health_history) > 0


class TestE2EIntegration:
    """End-to-end integration tests."""

    @pytest.mark.asyncio
    async def test_complete_tutoring_flow(self):
        """Test complete tutoring flow: vision → AI → response."""
        # Create pipeline
        config = PipelineConfig(mode=PipelineMode.FULL, enable_vision=True, enable_audio=False)

        pipeline = EduLensPipeline(config=config)
        await pipeline.initialize()
        await pipeline.start()

        # Start session
        session_id = await pipeline.start_session(student_id="test_student")

        # Process frame
        ocr_result = {"full_text": "Solve: 12 + 8 = ?", "average_confidence": 0.92}

        visual_context = await pipeline.process_frame(frame_data=None, ocr_result=ocr_result)

        assert visual_context is not None

        # Generate response
        response = await pipeline.generate_response(
            student_query="How do I solve this?", visual_context=visual_context
        )

        assert response is not None
        assert len(response["response"]) > 0

        # Clean up
        await pipeline.stop()

    @pytest.mark.asyncio
    async def test_error_recovery_integration(self):
        """Test error recovery in integrated pipeline."""
        config = PipelineConfig(enable_audio=False)
        pipeline = EduLensPipeline(config=config)
        await pipeline.initialize()

        # Create error handler
        error_handler = create_error_handler()

        # Simulate an error
        try:
            raise Exception("Simulated vision error")
        except Exception as e:
            success, _ = await error_handler.handle_vision_error(
                error=e, component="vision_pipeline", context={}
            )

        # Pipeline should still be operational
        health = await pipeline.health_check()
        assert health is not None

        await pipeline.stop()

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent pipeline operations."""
        coordinator = await create_coordinator(max_concurrent_tasks=5)

        # Schedule multiple operations
        async def mock_operation(op_id: int):
            await asyncio.sleep(0.1)
            return f"operation_{op_id}_complete"

        task_ids = []
        for i in range(10):
            task_id = await coordinator.schedule_task(
                task_type=f"operation_{i}",
                coroutine=mock_operation(i),
                priority=TaskPriority.NORMAL,
            )
            task_ids.append(task_id)

        # Wait for all
        results = []
        for task_id in task_ids:
            result = await coordinator.wait_for_task(task_id, timeout=5.0)
            results.append(result)

        assert len(results) == 10
        assert all(r is not None for r in results)

        await coordinator.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
