"""
Claude Agents Orchestration System - Orchestrator Package.

This package contains the core orchestration engine and supporting modules
for coordinating multi-agent software development workflows.
"""

from orchestrator.config import ConfigManager
from orchestrator.logger import LoggerManager
from orchestrator.state_manager import StateStore

__all__ = [
    "ConfigManager",
    "LoggerManager",
    "StateStore",
    # ClaudeAgentsOrchestrator is imported separately to avoid circular imports
]

__version__ = "1.0.0-alpha"
__author__ = "Your Organization"
