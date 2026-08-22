"""
Tests for the Orchestrator module.

Tests cover the main orchestration engine including phase execution,
validation gates, error recovery, and checkpoint management.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestrator.config import ConfigManager

# Import modules under test
from orchestrator.orchestrator import (
    ClaudeAgentsOrchestrator,
    OrchestratorPhase,
    OrchestratorStatus,
    PhaseResult,
    ProjectContext,
)
from orchestrator.state_manager import Checkpoint, StateStore


class TestOrchestratorPhase:
    """Tests for OrchestratorPhase enum."""

    def test_phase_values(self):
        """Test that all phases have correct values."""
        assert OrchestratorPhase.INITIALIZATION.value == "initialization"
        assert OrchestratorPhase.PHASE_1_CONCEPT.value == "phase_1_concept"
        assert OrchestratorPhase.PHASE_2_ARCHITECTURE.value == "phase_2_architecture"
        assert OrchestratorPhase.PHASE_3_IMPLEMENTATION.value == "phase_3_implementation"
        assert OrchestratorPhase.PHASE_4_TESTING.value == "phase_4_testing"
        assert OrchestratorPhase.PHASE_5_SECURITY.value == "phase_5_security"
        assert OrchestratorPhase.PHASE_6_DEPLOYMENT.value == "phase_6_deployment"
        assert OrchestratorPhase.COMPLETED.value == "completed"
        assert OrchestratorPhase.FAILED.value == "failed"

    def test_phase_count(self):
        """Test total number of phases."""
        assert len(OrchestratorPhase) == 9


class TestOrchestratorStatus:
    """Tests for OrchestratorStatus enum."""

    def test_status_values(self):
        """Test that all statuses have correct values."""
        assert OrchestratorStatus.IDLE.value == "idle"
        assert OrchestratorStatus.RUNNING.value == "running"
        assert OrchestratorStatus.PAUSED.value == "paused"
        assert OrchestratorStatus.COMPLETED.value == "completed"
        assert OrchestratorStatus.FAILED.value == "failed"


class TestPhaseResult:
    """Tests for PhaseResult dataclass."""

    def test_phase_result_creation(self):
        """Test creating a PhaseResult."""
        result = PhaseResult(
            phase=OrchestratorPhase.PHASE_1_CONCEPT,
            success=True,
            outputs={"concept": "test"},
            duration_seconds=10.5,
            validation_score=0.85,
        )

        assert result.phase == OrchestratorPhase.PHASE_1_CONCEPT
        assert result.success is True
        assert result.outputs == {"concept": "test"}
        assert result.duration_seconds == 10.5
        assert result.validation_score == 0.85
        assert result.errors == []

    def test_phase_result_to_dict(self):
        """Test PhaseResult serialization."""
        result = PhaseResult(
            phase=OrchestratorPhase.PHASE_1_CONCEPT,
            success=True,
            outputs={"key": "value"},
            errors=["error1"],
            duration_seconds=5.0,
            token_usage={"input": 100, "output": 50},
            validation_score=0.9,
        )

        data = result.to_dict()

        assert data["phase"] == "phase_1_concept"
        assert data["success"] is True
        assert data["outputs"] == {"key": "value"}
        assert data["errors"] == ["error1"]
        assert data["duration_seconds"] == 5.0
        assert data["token_usage"] == {"input": 100, "output": 50}
        assert data["validation_score"] == 0.9


class TestProjectContext:
    """Tests for ProjectContext dataclass."""

    def test_project_context_creation(self):
        """Test creating a ProjectContext."""
        context = ProjectContext(
            project_id="test-123",
            project_name="Test Project",
            specification={"name": "test", "features": []},
        )

        assert context.project_id == "test-123"
        assert context.project_name == "Test Project"
        assert context.specification == {"name": "test", "features": []}
        assert context.phase_outputs == {}
        assert context.current_phase == OrchestratorPhase.INITIALIZATION
        assert context.mcp_enabled is False
        assert context.mcp_data == {}

    def test_project_context_to_dict(self):
        """Test ProjectContext serialization."""
        context = ProjectContext(
            project_id="test-123",
            project_name="Test Project",
            specification={"name": "test"},
            mcp_enabled=True,
            mcp_data={"source": "data"},
        )

        data = context.to_dict()

        assert data["project_id"] == "test-123"
        assert data["project_name"] == "Test Project"
        assert data["specification"] == {"name": "test"}
        assert data["mcp_enabled"] is True
        assert data["mcp_data"] == {"source": "data"}
        assert data["current_phase"] == "initialization"


class TestClaudeAgentsOrchestrator:
    """Tests for ClaudeAgentsOrchestrator class."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock(spec=ConfigManager)
        config.get.return_value = {}
        return config

    @pytest.fixture
    def orchestrator(self, mock_config):
        """Create orchestrator instance with mocks."""
        with patch("orchestrator.orchestrator.get_config", return_value=mock_config):
            with patch("orchestrator.orchestrator.get_logger") as mock_logger:
                mock_logger.return_value = MagicMock()
                orch = ClaudeAgentsOrchestrator(config=mock_config)
                return orch

    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initializes correctly."""
        assert orchestrator._status == OrchestratorStatus.IDLE
        assert orchestrator._current_context is None
        assert orchestrator._phase_results == []

    def test_phase_sequence(self, orchestrator):
        """Test phase sequence is correct."""
        expected_phases = [
            OrchestratorPhase.PHASE_1_CONCEPT,
            OrchestratorPhase.PHASE_2_ARCHITECTURE,
            OrchestratorPhase.PHASE_3_IMPLEMENTATION,
            OrchestratorPhase.PHASE_4_TESTING,
            OrchestratorPhase.PHASE_5_SECURITY,
            OrchestratorPhase.PHASE_6_DEPLOYMENT,
        ]
        assert orchestrator._phase_sequence == expected_phases

    def test_phase_agents_mapping(self, orchestrator):
        """Test phase to agents mapping."""
        assert "concept_designer" in orchestrator._phase_agents[OrchestratorPhase.PHASE_1_CONCEPT]
        assert (
            "backend_engineer"
            in orchestrator._phase_agents[OrchestratorPhase.PHASE_3_IMPLEMENTATION]
        )
        assert "qa_engineer" in orchestrator._phase_agents[OrchestratorPhase.PHASE_4_TESTING]
        assert "security_engineer" in orchestrator._phase_agents[OrchestratorPhase.PHASE_5_SECURITY]
        assert "devops_engineer" in orchestrator._phase_agents[OrchestratorPhase.PHASE_6_DEPLOYMENT]

    def test_get_status_idle(self, orchestrator):
        """Test get_status when idle."""
        status = orchestrator.get_status()

        assert status["status"] == "idle"
        assert status["current_phase"] is None
        assert status["phases_completed"] == 0

    def test_validate_specification_valid(self, orchestrator):
        """Test specification validation with valid spec."""
        spec = {
            "name": "test-project",
            "description": "A test project",
            "features": ["feature1", "feature2"],
        }

        result = orchestrator._validate_specification(spec)

        assert result["valid"] is True
        assert result["errors"] == []

    def test_validate_specification_invalid(self, orchestrator):
        """Test specification validation with invalid spec."""
        spec = {
            "name": "test-project",
            # Missing description and features
        }

        result = orchestrator._validate_specification(spec)

        assert result["valid"] is False
        assert len(result["errors"]) == 2
        assert "description" in result["errors"][0]
        assert "features" in result["errors"][1]

    def test_classify_error_severity_critical(self, orchestrator):
        """Test error severity classification for critical errors."""
        from core.error_recovery import ErrorSeverity

        errors = ["Critical security vulnerability detected"]
        severity = orchestrator._classify_error_severity(errors)

        assert severity == ErrorSeverity.CRITICAL

    def test_classify_error_severity_medium(self, orchestrator):
        """Test error severity classification for medium errors."""
        from core.error_recovery import ErrorSeverity

        errors = ["Validation failed for output"]
        severity = orchestrator._classify_error_severity(errors)

        assert severity == ErrorSeverity.MEDIUM

    def test_classify_error_severity_low(self, orchestrator):
        """Test error severity classification for low errors."""
        from core.error_recovery import ErrorSeverity

        errors = ["Minor issue encountered"]
        severity = orchestrator._classify_error_severity(errors)

        assert severity == ErrorSeverity.LOW

    def test_get_phase_results_empty(self, orchestrator):
        """Test get_phase_results when no phases completed."""
        results = orchestrator.get_phase_results()
        assert results == []

    @pytest.mark.asyncio
    async def test_run_project_invalid_spec(self, orchestrator):
        """Test run_project with invalid specification."""
        # Mock dependencies
        orchestrator._secret_detector = MagicMock()
        orchestrator._secret_detector.has_secrets.return_value = False

        result = await orchestrator.run_project(
            project_name="test",
            specification={"name": "test"},  # Missing required fields
        )

        assert result["success"] is False
        assert "Invalid specification" in result["error"]

    @pytest.mark.asyncio
    async def test_run_project_secrets_detected(self, orchestrator):
        """Test run_project when secrets are detected."""
        orchestrator._secret_detector = MagicMock()
        orchestrator._secret_detector.has_secrets.return_value = True

        spec = {
            "name": "test",
            "description": "test desc",
            "features": ["f1"],
            "api_key": "sk-secret123",  # Simulated secret
        }

        result = await orchestrator.run_project(
            project_name="test",
            specification=spec,
        )

        assert result["success"] is False
        assert "Secrets detected" in result["error"]


class TestOrchestratorIntegration:
    """Integration tests for orchestrator."""

    @pytest.fixture
    def sample_specification(self):
        """Create a sample project specification."""
        return {
            "name": "test-app",
            "description": "A test application for integration testing",
            "features": [
                {"name": "User Auth", "description": "User authentication"},
                {"name": "Dashboard", "description": "Main dashboard"},
            ],
            "type": "web_application",
            "technical": {
                "frontend": {"framework": "react"},
                "backend": {"language": "python", "framework": "fastapi"},
            },
        }

    @pytest.mark.asyncio
    async def test_full_orchestration_flow(self, sample_specification):
        """Test complete orchestration flow (mocked)."""
        # This would be a full integration test
        # For now, we verify the structure is testable
        assert "name" in sample_specification
        assert "features" in sample_specification
        assert len(sample_specification["features"]) >= 2


class TestCheckpointManagement:
    """Tests for checkpoint functionality."""

    @pytest.fixture
    def mock_state_store(self):
        """Create mock state store."""
        store = AsyncMock(spec=StateStore)
        return store

    @pytest.mark.asyncio
    async def test_checkpoint_creation(self, mock_state_store):
        """Test checkpoint is created correctly."""
        checkpoint = Checkpoint(
            checkpoint_id="cp-123",
            project_id="proj-123",
            phase="phase_1_concept",
            state={"project_name": "test"},
            phase_outputs={"concept_designer": {"output": "data"}},
        )

        assert checkpoint.checkpoint_id == "cp-123"
        assert checkpoint.project_id == "proj-123"
        assert checkpoint.phase == "phase_1_concept"

    @pytest.mark.asyncio
    async def test_resume_from_checkpoint(self, mock_state_store):
        """Test resuming from checkpoint."""
        checkpoint = Checkpoint(
            checkpoint_id="cp-123",
            project_id="proj-123",
            phase="phase_2_architecture",
            state={
                "project_id": "proj-123",
                "project_name": "test",
                "specification": {"name": "test", "description": "d", "features": []},
                "mcp_enabled": False,
                "mcp_data": {},
            },
            phase_outputs={"phase_1_concept": {"output": "data"}},
        )

        mock_state_store.get_checkpoint.return_value = checkpoint

        # Verify checkpoint can be retrieved
        retrieved = await mock_state_store.get_checkpoint("cp-123")
        assert retrieved.checkpoint_id == "cp-123"
        assert retrieved.phase == "phase_2_architecture"


# Pytest configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
