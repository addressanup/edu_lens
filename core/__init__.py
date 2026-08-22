"""
Claude Agents Orchestration System - Core Package.

This package contains core systems for agent communication, validation,
error recovery, and context management.
"""

from core.communication_protocol import (
    CommunicationProtocol,
    Message,
    MessageType,
)
from core.context_budget import (
    BudgetAlert,
    BudgetAllocation,
    ContextBudgetManager,
)
from core.error_recovery import (
    ErrorRecovery,
    RecoveryLevel,
    RecoveryResult,
)
from core.message_broker import MessageBroker, MessagePriority
from core.validation_gates import (
    Gate1ConceptDesign,
    Gate2MCPData,
    Gate3Infrastructure,
    Gate4CodeGenerated,
    Gate5IntegrationTest,
    ValidationGate,
    ValidationResult,
)

__all__ = [
    # Message Broker
    "MessageBroker",
    "MessagePriority",
    # Communication Protocol
    "Message",
    "MessageType",
    "CommunicationProtocol",
    # Validation Gates
    "ValidationGate",
    "ValidationResult",
    "Gate1ConceptDesign",
    "Gate2MCPData",
    "Gate3Infrastructure",
    "Gate4CodeGenerated",
    "Gate5IntegrationTest",
    # Error Recovery
    "ErrorRecovery",
    "RecoveryLevel",
    "RecoveryResult",
    # Context Budget
    "ContextBudgetManager",
    "BudgetAllocation",
    "BudgetAlert",
]
