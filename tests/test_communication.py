"""
Tests for the Communication and Core modules.

Tests cover message broker, communication protocol, validation gates,
error recovery, and context budget management.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.communication_protocol import (
    MessageType,
    create_message,
    sign_message,
    validate_message,
)
from core.context_budget import (
    BudgetAllocation,
    BudgetCategory,
    ContextBudgetManager,
)
from core.error_recovery import (
    ErrorRecoveryManager,
    ErrorSeverity,
    RecoveryLevel,
    RecoveryResult,
)

# Import modules under test
from core.message_broker import Message, MessageBroker, MessagePriority
from core.validation_gates import (
    GateType,
    ValidationGateManager,
    ValidationResult,
)


class TestMessagePriority:
    """Tests for MessagePriority enum."""

    def test_priority_values(self):
        """Test priority enum values."""
        assert MessagePriority.CRITICAL.value == 0
        assert MessagePriority.HIGH.value == 1
        assert MessagePriority.NORMAL.value == 2
        assert MessagePriority.LOW.value == 3

    def test_priority_ordering(self):
        """Test priority ordering (lower value = higher priority)."""
        assert MessagePriority.CRITICAL.value < MessagePriority.HIGH.value
        assert MessagePriority.HIGH.value < MessagePriority.NORMAL.value
        assert MessagePriority.NORMAL.value < MessagePriority.LOW.value


class TestMessageType:
    """Tests for MessageType enum."""

    def test_message_type_values(self):
        """Test message type values."""
        assert MessageType.TASK_ASSIGNMENT.value == "task_assignment"
        assert MessageType.TASK_RESULT.value == "task_result"
        assert MessageType.STATUS_UPDATE.value == "status_update"
        assert MessageType.ERROR_REPORT.value == "error_report"
        assert MessageType.VALIDATION_REQUEST.value == "validation_request"
        assert MessageType.VALIDATION_RESULT.value == "validation_result"


class TestMessage:
    """Tests for Message dataclass."""

    def test_message_creation(self):
        """Test creating a message."""
        msg = Message(
            message_id="msg-001",
            message_type=MessageType.TASK_ASSIGNMENT,
            sender="orchestrator",
            recipient="backend_engineer",
            payload={"task": "implement_api"},
            priority=MessagePriority.HIGH,
        )

        assert msg.message_id == "msg-001"
        assert msg.message_type == MessageType.TASK_ASSIGNMENT
        assert msg.sender == "orchestrator"
        assert msg.recipient == "backend_engineer"
        assert msg.priority == MessagePriority.HIGH

    def test_create_message_function(self):
        """Test create_message helper function."""
        msg = create_message(
            msg_type=MessageType.STATUS_UPDATE,
            sender="agent_1",
            recipient="orchestrator",
            payload={"status": "completed"},
        )

        assert msg.message_type == MessageType.STATUS_UPDATE
        assert msg.sender == "agent_1"
        assert msg.recipient == "orchestrator"
        assert msg.message_id is not None
        assert msg.timestamp is not None


class TestMessageBroker:
    """Tests for MessageBroker class."""

    @pytest.fixture
    def broker(self):
        """Create message broker instance."""
        return MessageBroker()

    @pytest.mark.asyncio
    async def test_broker_publish(self, broker):
        """Test message publishing."""
        with patch.object(broker, "_redis", create=True) as mock_redis:
            mock_redis.lpush = AsyncMock(return_value=1)

            msg = create_message(
                msg_type=MessageType.TASK_ASSIGNMENT,
                sender="test",
                recipient="agent",
                payload={},
            )

            # Should not raise
            await broker.publish("test_queue", msg)

    @pytest.mark.asyncio
    async def test_broker_subscribe(self, broker):
        """Test message subscription."""
        messages_received = []

        async def handler(msg):
            messages_received.append(msg)

        # Subscription should register handler
        broker.subscribe("test_queue", handler)

        assert "test_queue" in broker._handlers

    def test_broker_get_queue_stats(self, broker):
        """Test queue statistics retrieval."""
        stats = broker.get_queue_stats()

        assert "queues" in stats
        assert isinstance(stats["queues"], dict)


class TestValidationGates:
    """Tests for validation gate system."""

    @pytest.fixture
    def gate_manager(self):
        """Create validation gate manager."""
        return ValidationGateManager()

    def test_gate_types(self):
        """Test all gate types exist."""
        assert GateType.CONCEPT_VALIDATION
        assert GateType.ARCHITECTURE_VALIDATION
        assert GateType.IMPLEMENTATION_VALIDATION
        assert GateType.TESTING_VALIDATION
        assert GateType.SECURITY_VALIDATION

    @pytest.mark.asyncio
    async def test_concept_validation(self, gate_manager):
        """Test concept validation gate."""
        data = {
            "concept_designer": {
                "concept": "A web application",
                "features": ["user auth", "dashboard"],
                "architecture": "microservices",
            }
        }

        result = await gate_manager.validate(
            gate_type=GateType.CONCEPT_VALIDATION,
            data=data,
            context={"specification": {"name": "test"}},
        )

        assert isinstance(result, ValidationResult)
        assert hasattr(result, "passed")
        assert hasattr(result, "confidence_score")
        assert 0 <= result.confidence_score <= 1

    @pytest.mark.asyncio
    async def test_validation_with_low_confidence(self, gate_manager):
        """Test validation with low confidence data."""
        data = {
            "concept_designer": {
                # Minimal/incomplete data
                "concept": "x",
            }
        }

        result = await gate_manager.validate(
            gate_type=GateType.CONCEPT_VALIDATION,
            data=data,
            context={},
        )

        # Should have lower confidence for incomplete data
        assert result.confidence_score < 1.0


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test creating validation result."""
        result = ValidationResult(
            passed=True,
            confidence_score=0.85,
            message="Validation passed",
            details={"checks": ["completeness", "consistency"]},
        )

        assert result.passed is True
        assert result.confidence_score == 0.85
        assert result.message == "Validation passed"

    def test_validation_result_to_dict(self):
        """Test validation result serialization."""
        result = ValidationResult(
            passed=False,
            confidence_score=0.45,
            message="Below threshold",
            issues=["Missing feature definitions"],
        )

        data = result.to_dict()

        assert data["passed"] is False
        assert data["confidence_score"] == 0.45
        assert "issues" in data


class TestErrorRecovery:
    """Tests for error recovery system."""

    @pytest.fixture
    def recovery_manager(self):
        """Create error recovery manager."""
        return ErrorRecoveryManager()

    def test_recovery_levels(self):
        """Test recovery level enum."""
        assert RecoveryLevel.RETRY.value == "retry"
        assert RecoveryLevel.PHASE_ROLLBACK.value == "phase_rollback"
        assert RecoveryLevel.FULL_ROLLBACK.value == "full_rollback"

    def test_error_severity(self):
        """Test error severity enum."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"

    @pytest.mark.asyncio
    async def test_retry_recovery(self, recovery_manager):
        """Test retry-level recovery."""
        attempt_count = 0

        async def retry_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception("Transient error")
            return {"success": True}

        result = await recovery_manager.recover(
            level=RecoveryLevel.RETRY,
            error_data={"error": "test"},
            retry_func=retry_func,
        )

        assert attempt_count >= 1

    @pytest.mark.asyncio
    async def test_phase_rollback_recovery(self, recovery_manager):
        """Test phase rollback recovery."""
        rollback_called = False

        async def rollback_func():
            nonlocal rollback_called
            rollback_called = True
            return True

        result = await recovery_manager.recover(
            level=RecoveryLevel.PHASE_ROLLBACK,
            error_data={"error": "phase failed"},
            rollback_func=rollback_func,
        )

        assert isinstance(result, RecoveryResult)


class TestRecoveryResult:
    """Tests for RecoveryResult dataclass."""

    def test_recovery_result_creation(self):
        """Test creating recovery result."""
        result = RecoveryResult(
            success=True,
            level=RecoveryLevel.RETRY,
            attempts=3,
            message="Recovery successful after retry",
        )

        assert result.success is True
        assert result.level == RecoveryLevel.RETRY
        assert result.attempts == 3


class TestContextBudget:
    """Tests for context budget management."""

    @pytest.fixture
    def budget_manager(self):
        """Create context budget manager."""
        return ContextBudgetManager(total_budget=200000)

    def test_budget_initialization(self, budget_manager):
        """Test budget manager initialization."""
        assert budget_manager._total_budget == 200000

    def test_budget_categories(self):
        """Test budget category enum."""
        assert BudgetCategory.SYSTEM.value == "system"
        assert BudgetCategory.HISTORICAL.value == "historical"
        assert BudgetCategory.TASK.value == "task"
        assert BudgetCategory.PROCESSING.value == "processing"
        assert BudgetCategory.RESERVED.value == "reserved"

    def test_get_allocation(self, budget_manager):
        """Test getting budget allocation."""
        allocation = budget_manager.get_allocation(BudgetCategory.SYSTEM)

        assert isinstance(allocation, BudgetAllocation)
        assert allocation.tokens > 0
        assert allocation.percentage > 0

    def test_check_budget_within_limit(self, budget_manager):
        """Test budget check within limit."""
        result = budget_manager.check_budget("test_agent", 1000)

        assert result["allowed"] is True
        assert result["available"] >= 1000

    def test_check_budget_exceeds_limit(self, budget_manager):
        """Test budget check exceeding limit."""
        result = budget_manager.check_budget("test_agent", 300000)

        assert result["allowed"] is False

    def test_record_usage(self, budget_manager):
        """Test recording token usage."""
        initial_remaining = budget_manager.get_remaining()

        budget_manager.record_usage("test_agent", 1000)

        new_remaining = budget_manager.get_remaining()
        assert new_remaining < initial_remaining

    def test_get_summary(self, budget_manager):
        """Test getting budget summary."""
        budget_manager.record_usage("agent_1", 5000)
        budget_manager.record_usage("agent_2", 3000)

        summary = budget_manager.get_summary()

        assert "total_budget" in summary
        assert "used" in summary
        assert "remaining" in summary
        assert "by_category" in summary


class TestBudgetAllocation:
    """Tests for BudgetAllocation dataclass."""

    def test_allocation_creation(self):
        """Test creating budget allocation."""
        allocation = BudgetAllocation(
            category=BudgetCategory.PROCESSING,
            tokens=80000,
            percentage=40.0,
        )

        assert allocation.category == BudgetCategory.PROCESSING
        assert allocation.tokens == 80000
        assert allocation.percentage == 40.0


class TestCommunicationIntegration:
    """Integration tests for communication system."""

    @pytest.mark.asyncio
    async def test_message_flow(self):
        """Test complete message flow."""
        # Create message
        msg = create_message(
            msg_type=MessageType.TASK_ASSIGNMENT,
            sender="orchestrator",
            recipient="backend_engineer",
            payload={
                "task": "implement_api",
                "specification": {"endpoints": ["/users", "/items"]},
            },
        )

        # Validate message
        is_valid = validate_message(msg)
        assert is_valid is True

        # Sign message
        signed = sign_message(msg)
        assert signed.signature is not None

    @pytest.mark.asyncio
    async def test_validation_gate_flow(self):
        """Test validation gate flow."""
        manager = ValidationGateManager()

        # Phase 1 validation
        result = await manager.validate(
            gate_type=GateType.CONCEPT_VALIDATION,
            data={"concept_designer": {"concept": "test app", "features": ["f1"]}},
            context={},
        )

        if result.passed:
            # Proceed to next phase
            assert result.confidence_score >= 0.5
        else:
            # Would trigger review or halt
            assert result.confidence_score < 0.7


# Pytest configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
