"""
SQLAlchemy Models for Claude Agents Orchestration System.

This module defines the database models for persisting orchestration state,
agent executions, decisions, errors, and audit logs.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum


# Create declarative base
Base = declarative_base()


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


class ProjectStatus(str, enum.Enum):
    """Project status enumeration."""

    CREATED = "created"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionStatus(str, enum.Enum):
    """Agent execution status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class Project(Base):
    """
    Project model for tracking orchestration projects.

    Attributes:
        id: Unique project identifier
        user_id: Owner user ID
        name: Project name
        description: Project description
        spec: Project specification (JSON)
        status: Current status
        current_phase: Current execution phase
        config: Project configuration (JSON)
        metadata: Additional metadata (JSON)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    spec = Column(JSON, nullable=False, default=dict)
    status = Column(
        SQLEnum(ProjectStatus),
        nullable=False,
        default=ProjectStatus.CREATED
    )
    current_phase = Column(Integer, nullable=False, default=0)
    config = Column(JSON, nullable=False, default=dict)
    metadata_ = Column("metadata", JSON, nullable=False, default=dict)
    checkpoint_id = Column(String(36), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now
    )

    # Relationships
    executions = relationship("AgentExecution", back_populates="project", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="project", cascade="all, delete-orphan")
    errors = relationship("Error", back_populates="project", cascade="all, delete-orphan")
    token_usages = relationship("TokenUsage", back_populates="project", cascade="all, delete-orphan")
    validation_results = relationship("ValidationResult", back_populates="project", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_projects_user_status", "user_id", "status"),
        Index("idx_projects_created", "created_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "spec": self.spec,
            "status": self.status.value if self.status else None,
            "current_phase": self.current_phase,
            "config": self.config,
            "metadata": self.metadata_,
            "checkpoint_id": self.checkpoint_id,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AgentExecution(Base):
    """
    Agent execution record model.

    Tracks individual agent invocations within a project.

    Attributes:
        id: Unique execution identifier
        project_id: Parent project ID
        agent_name: Name of the agent
        phase: Execution phase
        status: Execution status
        input_data: Input to the agent (JSON)
        output_data: Output from the agent (JSON)
        tokens_input: Input tokens used
        tokens_output: Output tokens generated
        latency_ms: Execution latency in milliseconds
        error_message: Error message if failed
        started_at: Execution start time
        completed_at: Execution completion time
        created_at: Record creation time
    """

    __tablename__ = "agent_executions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    agent_name = Column(String(64), nullable=False, index=True)
    phase = Column(Integer, nullable=False, default=0)
    status = Column(
        SQLEnum(ExecutionStatus),
        nullable=False,
        default=ExecutionStatus.PENDING
    )
    input_data = Column(JSON, nullable=False, default=dict)
    output_data = Column(JSON, nullable=False, default=dict)
    tokens_input = Column(Integer, nullable=False, default=0)
    tokens_output = Column(Integer, nullable=False, default=0)
    latency_ms = Column(Float, nullable=False, default=0.0)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    project = relationship("Project", back_populates="executions")

    # Indexes
    __table_args__ = (
        Index("idx_executions_project_phase", "project_id", "phase"),
        Index("idx_executions_agent", "agent_name"),
        Index("idx_executions_status", "status"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "agent_name": self.agent_name,
            "phase": self.phase,
            "status": self.status.value if self.status else None,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "latency_ms": self.latency_ms,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Decision(Base):
    """
    Decision record model.

    Tracks decisions made by agents during execution.

    Attributes:
        id: Unique decision identifier
        project_id: Parent project ID
        agent_name: Agent that made the decision
        phase: Phase when decision was made
        decision: The decision made
        reasoning: Explanation for the decision
        alternatives: Alternative options considered (JSON list)
        confidence_score: Confidence in the decision (0-1)
        context: Decision context (JSON)
        timestamp: When the decision was made
    """

    __tablename__ = "decisions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    agent_name = Column(String(64), nullable=False, index=True)
    phase = Column(Integer, nullable=False, default=0)
    decision = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=True)
    alternatives = Column(JSON, nullable=False, default=list)
    confidence_score = Column(Float, nullable=False, default=0.0)
    context = Column(JSON, nullable=False, default=dict)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    project = relationship("Project", back_populates="decisions")

    # Indexes
    __table_args__ = (
        Index("idx_decisions_project_agent", "project_id", "agent_name"),
        Index("idx_decisions_timestamp", "timestamp"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "agent_name": self.agent_name,
            "phase": self.phase,
            "decision": self.decision,
            "reasoning": self.reasoning,
            "alternatives": self.alternatives,
            "confidence_score": self.confidence_score,
            "context": self.context,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class Error(Base):
    """
    Error record model.

    Tracks errors and recovery attempts during execution.

    Attributes:
        id: Unique error identifier
        project_id: Parent project ID
        agent_name: Agent that encountered the error
        phase: Phase when error occurred
        error_type: Type/class of error
        error_message: Error message
        stack_trace: Full stack trace
        context: Error context (JSON)
        recovery_level: Recovery level attempted
        recovery_attempted: Whether recovery was attempted
        recovery_successful: Whether recovery succeeded
        outcome: Final outcome description
        timestamp: When the error occurred
    """

    __tablename__ = "errors"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    agent_name = Column(String(64), nullable=False, index=True)
    phase = Column(Integer, nullable=False, default=0)
    error_type = Column(String(128), nullable=False)
    error_message = Column(Text, nullable=False)
    stack_trace = Column(Text, nullable=True)
    context = Column(JSON, nullable=False, default=dict)
    recovery_level = Column(String(32), nullable=True)
    recovery_attempted = Column(Boolean, nullable=False, default=False)
    recovery_successful = Column(Boolean, nullable=False, default=False)
    outcome = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    project = relationship("Project", back_populates="errors")

    # Indexes
    __table_args__ = (
        Index("idx_errors_project", "project_id"),
        Index("idx_errors_type", "error_type"),
        Index("idx_errors_timestamp", "timestamp"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "agent_name": self.agent_name,
            "phase": self.phase,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "context": self.context,
            "recovery_level": self.recovery_level,
            "recovery_attempted": self.recovery_attempted,
            "recovery_successful": self.recovery_successful,
            "outcome": self.outcome,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class TokenUsage(Base):
    """
    Token usage record model.

    Tracks token consumption per agent per phase.

    Attributes:
        id: Unique usage identifier
        project_id: Parent project ID
        agent_name: Agent that used tokens
        phase: Execution phase
        category: Budget category
        input_tokens: Input tokens consumed
        output_tokens: Output tokens generated
        cost_usd: Estimated cost in USD
        timestamp: When usage was recorded
    """

    __tablename__ = "token_usages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    agent_name = Column(String(64), nullable=False, index=True)
    phase = Column(Integer, nullable=False, default=0)
    category = Column(String(32), nullable=False, default="processing")
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float, nullable=False, default=0.0)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    project = relationship("Project", back_populates="token_usages")

    # Indexes
    __table_args__ = (
        Index("idx_tokens_project_phase", "project_id", "phase"),
        Index("idx_tokens_agent", "agent_name"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "agent_name": self.agent_name,
            "phase": self.phase,
            "category": self.category,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
            "cost_usd": self.cost_usd,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class ValidationResult(Base):
    """
    Validation result model.

    Records results from validation gates.

    Attributes:
        id: Unique result identifier
        project_id: Parent project ID
        gate_name: Name of the validation gate
        phase: Phase being validated
        passed: Whether validation passed
        confidence_score: Confidence score (0-1)
        status: Validation status
        issues: List of issues found (JSON)
        recommendations: Suggested improvements (JSON)
        metrics: Validation metrics (JSON)
        timestamp: When validation was performed
    """

    __tablename__ = "validation_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    gate_name = Column(String(64), nullable=False, index=True)
    phase = Column(Integer, nullable=False, default=0)
    passed = Column(Boolean, nullable=False, default=False)
    confidence_score = Column(Float, nullable=False, default=0.0)
    status = Column(String(32), nullable=False, default="pending")
    issues = Column(JSON, nullable=False, default=list)
    recommendations = Column(JSON, nullable=False, default=list)
    metrics = Column(JSON, nullable=False, default=dict)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    project = relationship("Project", back_populates="validation_results")

    # Indexes
    __table_args__ = (
        Index("idx_validations_project_phase", "project_id", "phase"),
        Index("idx_validations_gate", "gate_name"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "gate_name": self.gate_name,
            "phase": self.phase,
            "passed": self.passed,
            "confidence_score": self.confidence_score,
            "status": self.status,
            "issues": self.issues,
            "recommendations": self.recommendations,
            "metrics": self.metrics,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class AuditLog(Base):
    """
    Audit log model for compliance tracking.

    Records all significant actions with 7-year retention capability.

    Attributes:
        id: Unique log identifier
        user_id: User who performed the action
        action: Action performed
        resource_type: Type of resource affected
        resource_id: ID of affected resource
        result: Action result (success/failure/denied)
        ip_address: Client IP address
        user_agent: Client user agent
        request_id: Request correlation ID
        details: Additional details (JSON)
        timestamp: When the action occurred
    """

    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False, index=True)
    action = Column(String(64), nullable=False, index=True)
    resource_type = Column(String(64), nullable=False, index=True)
    resource_id = Column(String(36), nullable=True, index=True)
    result = Column(String(16), nullable=False, default="success")
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    request_id = Column(String(36), nullable=True, index=True)
    details = Column(JSON, nullable=False, default=dict)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Indexes for compliance queries
    __table_args__ = (
        Index("idx_audit_user_action", "user_id", "action"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_request", "request_id"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "result": self.result,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
