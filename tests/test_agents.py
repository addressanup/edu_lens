"""
Tests for the Agent modules.

Tests cover the base agent class and all specialized agent implementations.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

# Import modules under test
from agents.base_agent import BaseAgent, AgentCapability, AgentState


class TestAgentCapability:
    """Tests for AgentCapability enum."""

    def test_capability_values(self):
        """Test that capabilities have correct values."""
        assert AgentCapability.GENERATE_CODE.value == "generate_code"
        assert AgentCapability.REVIEW_CODE.value == "review_code"
        assert AgentCapability.GENERATE_TESTS.value == "generate_tests"
        assert AgentCapability.SECURITY_AUDIT.value == "security_audit"
        assert AgentCapability.GENERATE_DOCS.value == "generate_docs"


class TestAgentState:
    """Tests for AgentState enum."""

    def test_state_values(self):
        """Test that states have correct values."""
        assert AgentState.IDLE.value == "idle"
        assert AgentState.PROCESSING.value == "processing"
        assert AgentState.WAITING.value == "waiting"
        assert AgentState.COMPLETED.value == "completed"
        assert AgentState.FAILED.value == "failed"


class ConcreteAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""

    @property
    def name(self) -> str:
        return "test_agent"

    @property
    def capabilities(self) -> list:
        return [AgentCapability.GENERATE_CODE, AgentCapability.REVIEW_CODE]

    async def _process(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": True,
            "output": f"Processed: {prompt[:50]}",
            "context_used": list(context.keys()),
        }


class TestBaseAgent:
    """Tests for BaseAgent class."""

    @pytest.fixture
    def agent(self):
        """Create a concrete agent instance."""
        return ConcreteAgent(
            agent_id="test-001",
            config={"max_tokens": 4000},
        )

    def test_agent_initialization(self, agent):
        """Test agent initializes correctly."""
        assert agent.agent_id == "test-001"
        assert agent.name == "test_agent"
        assert agent.state == AgentState.IDLE
        assert AgentCapability.GENERATE_CODE in agent.capabilities

    def test_agent_has_capability(self, agent):
        """Test capability checking."""
        assert agent.has_capability(AgentCapability.GENERATE_CODE) is True
        assert agent.has_capability(AgentCapability.SECURITY_AUDIT) is False

    @pytest.mark.asyncio
    async def test_agent_execute(self, agent):
        """Test agent execution."""
        with patch.object(agent, "invoke_claude", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = {
                "success": True,
                "response": "Generated output",
                "input_tokens": 100,
                "output_tokens": 50,
            }

            result = await agent.execute(
                prompt="Generate a function",
                context={"project": "test"},
            )

            assert result["success"] is True
            assert agent.state == AgentState.COMPLETED

    @pytest.mark.asyncio
    async def test_agent_execute_failure(self, agent):
        """Test agent execution failure handling."""
        with patch.object(agent, "invoke_claude", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.side_effect = Exception("Claude invocation failed")

            result = await agent.execute(
                prompt="Generate a function",
                context={},
            )

            assert result["success"] is False
            assert "error" in result
            assert agent.state == AgentState.FAILED

    def test_agent_get_status(self, agent):
        """Test agent status retrieval."""
        status = agent.get_status()

        assert status["agent_id"] == "test-001"
        assert status["name"] == "test_agent"
        assert status["state"] == "idle"
        assert "capabilities" in status


class TestConceptDesignerAgent:
    """Tests for ConceptDesigner agent."""

    @pytest.fixture
    def concept_designer(self):
        """Create ConceptDesigner instance."""
        from agents.concept_designer import ConceptDesignerAgent

        return ConceptDesignerAgent(
            agent_id="concept-001",
            config={},
        )

    def test_concept_designer_properties(self, concept_designer):
        """Test ConceptDesigner properties."""
        assert concept_designer.name == "concept_designer"
        assert AgentCapability.GENERATE_DOCS in concept_designer.capabilities

    @pytest.mark.asyncio
    async def test_concept_designer_process(self, concept_designer):
        """Test ConceptDesigner processing."""
        with patch.object(concept_designer, "invoke_claude", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "success": True,
                "response": '{"concept": "design", "features": []}',
                "input_tokens": 200,
                "output_tokens": 100,
            }

            result = await concept_designer.execute(
                prompt="Design a web app",
                context={"specification": {"name": "test"}},
            )

            assert result["success"] is True


class TestBackendEngineerAgent:
    """Tests for BackendEngineer agent."""

    @pytest.fixture
    def backend_engineer(self):
        """Create BackendEngineer instance."""
        from agents.backend_engineer import BackendEngineerAgent

        return BackendEngineerAgent(
            agent_id="backend-001",
            config={},
        )

    def test_backend_engineer_properties(self, backend_engineer):
        """Test BackendEngineer properties."""
        assert backend_engineer.name == "backend_engineer"
        assert AgentCapability.GENERATE_CODE in backend_engineer.capabilities
        assert AgentCapability.GENERATE_TESTS in backend_engineer.capabilities


class TestFrontendEngineerAgent:
    """Tests for FrontendEngineer agent."""

    @pytest.fixture
    def frontend_engineer(self):
        """Create FrontendEngineer instance."""
        from agents.frontend_engineer import FrontendEngineerAgent

        return FrontendEngineerAgent(
            agent_id="frontend-001",
            config={},
        )

    def test_frontend_engineer_properties(self, frontend_engineer):
        """Test FrontendEngineer properties."""
        assert frontend_engineer.name == "frontend_engineer"
        assert AgentCapability.GENERATE_CODE in frontend_engineer.capabilities


class TestSecurityEngineerAgent:
    """Tests for SecurityEngineer agent."""

    @pytest.fixture
    def security_engineer(self):
        """Create SecurityEngineer instance."""
        from agents.security_engineer import SecurityEngineerAgent

        return SecurityEngineerAgent(
            agent_id="security-001",
            config={},
        )

    def test_security_engineer_properties(self, security_engineer):
        """Test SecurityEngineer properties."""
        assert security_engineer.name == "security_engineer"
        assert AgentCapability.SECURITY_AUDIT in security_engineer.capabilities
        assert AgentCapability.REVIEW_CODE in security_engineer.capabilities


class TestQAEngineerAgent:
    """Tests for QAEngineer agent."""

    @pytest.fixture
    def qa_engineer(self):
        """Create QAEngineer instance."""
        from agents.qa_engineer import QAEngineerAgent

        return QAEngineerAgent(
            agent_id="qa-001",
            config={},
        )

    def test_qa_engineer_properties(self, qa_engineer):
        """Test QAEngineer properties."""
        assert qa_engineer.name == "qa_engineer"
        assert AgentCapability.GENERATE_TESTS in qa_engineer.capabilities
        assert AgentCapability.REVIEW_CODE in qa_engineer.capabilities


class TestDevOpsEngineerAgent:
    """Tests for DevOpsEngineer agent."""

    @pytest.fixture
    def devops_engineer(self):
        """Create DevOpsEngineer instance."""
        from agents.devops_engineer import DevOpsEngineerAgent

        return DevOpsEngineerAgent(
            agent_id="devops-001",
            config={},
        )

    def test_devops_engineer_properties(self, devops_engineer):
        """Test DevOpsEngineer properties."""
        assert devops_engineer.name == "devops_engineer"
        assert AgentCapability.GENERATE_CODE in devops_engineer.capabilities
        assert AgentCapability.GENERATE_DOCS in devops_engineer.capabilities


class TestMCPEngineerAgent:
    """Tests for MCPEngineer agent."""

    @pytest.fixture
    def mcp_engineer(self):
        """Create MCPEngineer instance."""
        from agents.mcp_engineer import MCPEngineerAgent

        return MCPEngineerAgent(
            agent_id="mcp-001",
            config={},
        )

    def test_mcp_engineer_properties(self, mcp_engineer):
        """Test MCPEngineer properties."""
        assert mcp_engineer.name == "mcp_engineer"


class TestIntegrationEngineerAgent:
    """Tests for IntegrationEngineer agent."""

    @pytest.fixture
    def integration_engineer(self):
        """Create IntegrationEngineer instance."""
        from agents.integration_engineer import IntegrationEngineerAgent

        return IntegrationEngineerAgent(
            agent_id="integration-001",
            config={},
        )

    def test_integration_engineer_properties(self, integration_engineer):
        """Test IntegrationEngineer properties."""
        assert integration_engineer.name == "integration_engineer"
        assert AgentCapability.REVIEW_CODE in integration_engineer.capabilities


class TestAgentRegistry:
    """Tests for agent registry functionality."""

    def test_get_agent_registry(self):
        """Test agent registry retrieval."""
        from agents import get_agent_registry

        registry = get_agent_registry()

        assert "concept_designer" in registry
        assert "backend_engineer" in registry
        assert "frontend_engineer" in registry
        assert "security_engineer" in registry
        assert "qa_engineer" in registry
        assert "devops_engineer" in registry
        assert "mcp_engineer" in registry
        assert "integration_engineer" in registry

    def test_registry_agent_count(self):
        """Test correct number of agents in registry."""
        from agents import get_agent_registry

        registry = get_agent_registry()
        assert len(registry) == 8


class TestAgentCommunication:
    """Tests for agent communication patterns."""

    @pytest.mark.asyncio
    async def test_agent_to_agent_message(self):
        """Test agent communication via messages."""
        from core.communication_protocol import create_message, MessageType

        message = create_message(
            msg_type=MessageType.TASK_ASSIGNMENT,
            sender="orchestrator",
            recipient="backend_engineer",
            payload={"task": "implement_api", "spec": {}},
        )

        assert message.sender == "orchestrator"
        assert message.recipient == "backend_engineer"
        assert message.payload["task"] == "implement_api"


# Pytest configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
