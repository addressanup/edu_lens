"""
Claude Agents Orchestration System - Agents Package.

This package contains the agent framework including the base agent class
and all specialized agents for different development tasks.
"""

from typing import Dict, List, Optional, Type

from agents.base_agent import BaseAgent, AgentCapability, AgentStatus


# Agent registry for dynamic loading
_AGENT_REGISTRY: Dict[str, Type[BaseAgent]] = {}


def register_agent(agent_class: Type[BaseAgent]) -> Type[BaseAgent]:
    """
    Decorator to register an agent class.

    Example:
        @register_agent
        class MyAgent(BaseAgent):
            ...
    """
    _AGENT_REGISTRY[agent_class.agent_name] = agent_class
    return agent_class


def get_agent(name: str) -> Optional[Type[BaseAgent]]:
    """Get an agent class by name."""
    return _AGENT_REGISTRY.get(name)


def list_agents() -> List[str]:
    """List all registered agent names."""
    return list(_AGENT_REGISTRY.keys())


def get_all_agents() -> Dict[str, Type[BaseAgent]]:
    """Get all registered agents."""
    return _AGENT_REGISTRY.copy()


# Import agents to trigger registration
# Note: These imports happen after the registry is defined to avoid circular imports
def _load_agents():
    """Load all agent modules to register them."""
    from agents.concept_designer import ConceptDesignerAgent
    from agents.mcp_engineer import MCPEngineerAgent
    from agents.integration_engineer import IntegrationEngineerAgent
    from agents.backend_engineer import BackendEngineerAgent
    from agents.frontend_engineer import FrontendEngineerAgent
    from agents.security_engineer import SecurityEngineerAgent
    from agents.qa_engineer import QAEngineerAgent
    from agents.devops_engineer import DevOpsEngineerAgent

    # Register all agents
    for agent_class in [
        ConceptDesignerAgent,
        MCPEngineerAgent,
        IntegrationEngineerAgent,
        BackendEngineerAgent,
        FrontendEngineerAgent,
        SecurityEngineerAgent,
        QAEngineerAgent,
        DevOpsEngineerAgent,
    ]:
        _AGENT_REGISTRY[agent_class.agent_name] = agent_class


# Load agents on module import
_load_agents()


__all__ = [
    # Base classes
    "BaseAgent",
    "AgentCapability",
    "AgentStatus",
    # Registry functions
    "register_agent",
    "get_agent",
    "list_agents",
    "get_all_agents",
]
