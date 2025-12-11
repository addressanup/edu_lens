"""
Claude Agents Orchestration System - Core Package.

This package contains core systems for agent communication, validation,
error recovery, and context management.
"""

from core.message_broker import MessageBroker, MessagePriority
from core.communication_protocol import (
    Message,
    MessageType,
    CommunicationProtocol,
)
from core.validation_gates import (
    ValidationGate,
    ValidationResult,
    Gate1ConceptDesign,
    Gate2MCPData,
    Gate3Infrastructure,
    Gate4CodeGenerated,
    Gate5IntegrationTest,
)
from core.error_recovery import (
    ErrorRecovery,
    RecoveryLevel,
    RecoveryResult,
)
from core.context_budget import (
    ContextBudgetManager,
    BudgetAllocation,
    BudgetAlert,
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
