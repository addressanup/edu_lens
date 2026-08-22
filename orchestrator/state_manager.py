"""
State Management for Claude Agents Orchestration System.

This module provides persistent state storage using SQLAlchemy,
supporting both PostgreSQL (production) and SQLite (development/testing).
"""

import json
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type, TypeVar

from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

T = TypeVar("T")


@dataclass
class Checkpoint:
    """Data structure for orchestration checkpoints."""

    id: str
    project_name: str
    current_phase: int
    status: str  # in_progress, completed, failed, paused
    state_data: Dict[str, Any] = field(default_factory=dict)
    agent_outputs: Dict[str, Any] = field(default_factory=dict)
    validation_results: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "project_name": self.project_name,
            "current_phase": self.current_phase,
            "status": self.status,
            "state_data": self.state_data,
            "agent_outputs": self.agent_outputs,
            "validation_results": self.validation_results,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        """Create from dictionary."""
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")

        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)

        return cls(
            id=data["id"],
            project_name=data["project_name"],
            current_phase=data["current_phase"],
            status=data["status"],
            state_data=data.get("state_data", {}),
            agent_outputs=data.get("agent_outputs", {}),
            validation_results=data.get("validation_results", {}),
            error_message=data.get("error_message"),
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=updated_at or datetime.now(timezone.utc),
        )


@dataclass
class AgentExecutionRecord:
    """Data structure for agent execution records."""

    id: str
    checkpoint_id: str
    agent_name: str
    phase: int
    status: str  # pending, running, completed, failed
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: float = 0.0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class StateStore:
    """
    Persistent state storage for the orchestration system.

    Supports PostgreSQL for production and SQLite for development/testing.
    Provides CRUD operations for checkpoints, agent executions, and other
    orchestration state.

    Example:
        state_store = StateStore("postgresql://user:pass@localhost/db")

        # Create checkpoint
        checkpoint = Checkpoint(id="cp1", project_name="MyProject", ...)
        state_store.save_checkpoint(checkpoint)

        # Retrieve checkpoint
        checkpoint = state_store.get_checkpoint("cp1")

        # List checkpoints
        checkpoints = state_store.list_checkpoints(limit=10)
    """

    def __init__(self, database_url: str):
        """
        Initialize the state store.

        Args:
            database_url: SQLAlchemy database URL
        """
        self._database_url = database_url
        self._is_sqlite = database_url.startswith("sqlite")

        # Configure engine based on database type
        if self._is_sqlite:
            # SQLite-specific configuration
            self._engine = create_engine(
                database_url,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False},
            )
            # Enable foreign keys for SQLite
            event.listen(self._engine, "connect", self._set_sqlite_pragma)
        else:
            # PostgreSQL configuration with connection pooling
            self._engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,
            )

        # Create session factory
        session_factory = sessionmaker(bind=self._engine)
        self._Session = scoped_session(session_factory)

        # Initialize tables
        self._init_tables()

    def _set_sqlite_pragma(self, dbapi_conn, connection_record) -> None:
        """Enable foreign keys for SQLite connections."""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    def _init_tables(self) -> None:
        """Initialize database tables."""
        with self._engine.connect() as conn:
            # Create checkpoints table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id TEXT PRIMARY KEY,
                    project_name TEXT NOT NULL,
                    current_phase INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'in_progress',
                    state_data TEXT DEFAULT '{}',
                    agent_outputs TEXT DEFAULT '{}',
                    validation_results TEXT DEFAULT '{}',
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Create agent_executions table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS agent_executions (
                    id TEXT PRIMARY KEY,
                    checkpoint_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    phase INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    input_data TEXT DEFAULT '{}',
                    output_data TEXT DEFAULT '{}',
                    tokens_input INTEGER DEFAULT 0,
                    tokens_output INTEGER DEFAULT 0,
                    latency_ms REAL DEFAULT 0.0,
                    error_message TEXT,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (checkpoint_id) REFERENCES checkpoints(id)
                )
            """))

            # Create validation_results table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS validation_results (
                    id TEXT PRIMARY KEY,
                    checkpoint_id TEXT NOT NULL,
                    gate_name TEXT NOT NULL,
                    phase INTEGER NOT NULL,
                    passed INTEGER NOT NULL DEFAULT 0,
                    confidence_score REAL DEFAULT 0.0,
                    issues TEXT DEFAULT '[]',
                    recommendations TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (checkpoint_id) REFERENCES checkpoints(id)
                )
            """))

            # Create indexes
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_checkpoints_status
                ON checkpoints(status)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_checkpoints_created
                ON checkpoints(created_at DESC)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_agent_executions_checkpoint
                ON agent_executions(checkpoint_id)
            """))

            conn.commit()

    @contextmanager
    def session(self):
        """Provide a transactional scope around a series of operations."""
        session = self._Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # Checkpoint Operations

    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """
        Save or update a checkpoint.

        Args:
            checkpoint: Checkpoint to save
        """
        checkpoint.updated_at = datetime.now(timezone.utc)

        with self._engine.connect() as conn:
            # Check if exists
            result = conn.execute(
                text("SELECT id FROM checkpoints WHERE id = :id"), {"id": checkpoint.id}
            ).fetchone()

            if result:
                # Update
                conn.execute(
                    text("""
                    UPDATE checkpoints SET
                        project_name = :project_name,
                        current_phase = :current_phase,
                        status = :status,
                        state_data = :state_data,
                        agent_outputs = :agent_outputs,
                        validation_results = :validation_results,
                        error_message = :error_message,
                        updated_at = :updated_at
                    WHERE id = :id
                """),
                    {
                        "id": checkpoint.id,
                        "project_name": checkpoint.project_name,
                        "current_phase": checkpoint.current_phase,
                        "status": checkpoint.status,
                        "state_data": json.dumps(checkpoint.state_data),
                        "agent_outputs": json.dumps(checkpoint.agent_outputs),
                        "validation_results": json.dumps(checkpoint.validation_results),
                        "error_message": checkpoint.error_message,
                        "updated_at": checkpoint.updated_at,
                    },
                )
            else:
                # Insert
                conn.execute(
                    text("""
                    INSERT INTO checkpoints (
                        id, project_name, current_phase, status,
                        state_data, agent_outputs, validation_results,
                        error_message, created_at, updated_at
                    ) VALUES (
                        :id, :project_name, :current_phase, :status,
                        :state_data, :agent_outputs, :validation_results,
                        :error_message, :created_at, :updated_at
                    )
                """),
                    {
                        "id": checkpoint.id,
                        "project_name": checkpoint.project_name,
                        "current_phase": checkpoint.current_phase,
                        "status": checkpoint.status,
                        "state_data": json.dumps(checkpoint.state_data),
                        "agent_outputs": json.dumps(checkpoint.agent_outputs),
                        "validation_results": json.dumps(checkpoint.validation_results),
                        "error_message": checkpoint.error_message,
                        "created_at": checkpoint.created_at,
                        "updated_at": checkpoint.updated_at,
                    },
                )

            conn.commit()

    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """
        Retrieve a checkpoint by ID.

        Args:
            checkpoint_id: Checkpoint ID

        Returns:
            Checkpoint if found, None otherwise
        """
        with self._engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM checkpoints WHERE id = :id"), {"id": checkpoint_id}
            ).fetchone()

            if not result:
                return None

            return Checkpoint(
                id=result[0],
                project_name=result[1],
                current_phase=result[2],
                status=result[3],
                state_data=json.loads(result[4] or "{}"),
                agent_outputs=json.loads(result[5] or "{}"),
                validation_results=json.loads(result[6] or "{}"),
                error_message=result[7],
                created_at=(
                    result[8]
                    if isinstance(result[8], datetime)
                    else datetime.fromisoformat(result[8]) if result[8] else None
                ),
                updated_at=(
                    result[9]
                    if isinstance(result[9], datetime)
                    else datetime.fromisoformat(result[9]) if result[9] else None
                ),
            )

    def list_checkpoints(
        self, status: Optional[str] = None, limit: Optional[int] = 10
    ) -> List[Checkpoint]:
        """
        List checkpoints with optional filtering.

        Args:
            status: Filter by status
            limit: Maximum number to return (None for all)

        Returns:
            List of checkpoints
        """
        query = "SELECT * FROM checkpoints"
        params: Dict[str, Any] = {}

        if status:
            query += " WHERE status = :status"
            params["status"] = status

        query += " ORDER BY created_at DESC"

        if limit:
            query += " LIMIT :limit"
            params["limit"] = limit

        with self._engine.connect() as conn:
            results = conn.execute(text(query), params).fetchall()

            checkpoints = []
            for row in results:
                checkpoints.append(
                    Checkpoint(
                        id=row[0],
                        project_name=row[1],
                        current_phase=row[2],
                        status=row[3],
                        state_data=json.loads(row[4] or "{}"),
                        agent_outputs=json.loads(row[5] or "{}"),
                        validation_results=json.loads(row[6] or "{}"),
                        error_message=row[7],
                        created_at=(
                            row[8]
                            if isinstance(row[8], datetime)
                            else datetime.fromisoformat(row[8]) if row[8] else None
                        ),
                        updated_at=(
                            row[9]
                            if isinstance(row[9], datetime)
                            else datetime.fromisoformat(row[9]) if row[9] else None
                        ),
                    )
                )

            return checkpoints

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Delete a checkpoint and related records.

        Args:
            checkpoint_id: Checkpoint ID to delete

        Returns:
            True if deleted, False if not found
        """
        with self._engine.connect() as conn:
            # Delete related records first
            conn.execute(
                text("DELETE FROM agent_executions WHERE checkpoint_id = :id"),
                {"id": checkpoint_id},
            )
            conn.execute(
                text("DELETE FROM validation_results WHERE checkpoint_id = :id"),
                {"id": checkpoint_id},
            )

            # Delete checkpoint
            result = conn.execute(
                text("DELETE FROM checkpoints WHERE id = :id"), {"id": checkpoint_id}
            )
            conn.commit()

            return result.rowcount > 0

    # Agent Execution Operations

    def save_agent_execution(self, execution: AgentExecutionRecord) -> None:
        """Save an agent execution record."""
        with self._engine.connect() as conn:
            conn.execute(
                text("""
                INSERT INTO agent_executions (
                    id, checkpoint_id, agent_name, phase, status,
                    input_data, output_data, tokens_input, tokens_output,
                    latency_ms, error_message, started_at, completed_at, created_at
                ) VALUES (
                    :id, :checkpoint_id, :agent_name, :phase, :status,
                    :input_data, :output_data, :tokens_input, :tokens_output,
                    :latency_ms, :error_message, :started_at, :completed_at, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    status = :status,
                    output_data = :output_data,
                    tokens_input = :tokens_input,
                    tokens_output = :tokens_output,
                    latency_ms = :latency_ms,
                    error_message = :error_message,
                    completed_at = :completed_at
            """),
                {
                    "id": execution.id,
                    "checkpoint_id": execution.checkpoint_id,
                    "agent_name": execution.agent_name,
                    "phase": execution.phase,
                    "status": execution.status,
                    "input_data": json.dumps(execution.input_data),
                    "output_data": json.dumps(execution.output_data),
                    "tokens_input": execution.tokens_input,
                    "tokens_output": execution.tokens_output,
                    "latency_ms": execution.latency_ms,
                    "error_message": execution.error_message,
                    "started_at": execution.started_at,
                    "completed_at": execution.completed_at,
                    "created_at": execution.created_at,
                },
            )
            conn.commit()

    def get_agent_executions(
        self, checkpoint_id: str, agent_name: Optional[str] = None
    ) -> List[AgentExecutionRecord]:
        """Get agent execution records for a checkpoint."""
        query = "SELECT * FROM agent_executions WHERE checkpoint_id = :checkpoint_id"
        params: Dict[str, Any] = {"checkpoint_id": checkpoint_id}

        if agent_name:
            query += " AND agent_name = :agent_name"
            params["agent_name"] = agent_name

        query += " ORDER BY created_at"

        with self._engine.connect() as conn:
            results = conn.execute(text(query), params).fetchall()

            executions = []
            for row in results:
                executions.append(
                    AgentExecutionRecord(
                        id=row[0],
                        checkpoint_id=row[1],
                        agent_name=row[2],
                        phase=row[3],
                        status=row[4],
                        input_data=json.loads(row[5] or "{}"),
                        output_data=json.loads(row[6] or "{}"),
                        tokens_input=row[7],
                        tokens_output=row[8],
                        latency_ms=row[9],
                        error_message=row[10],
                        started_at=row[11],
                        completed_at=row[12],
                        created_at=row[13],
                    )
                )

            return executions

    # Utility Methods

    def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                return True
        except SQLAlchemyError:
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self._engine.connect() as conn:
            checkpoint_count = conn.execute(text("SELECT COUNT(*) FROM checkpoints")).scalar()

            execution_count = conn.execute(text("SELECT COUNT(*) FROM agent_executions")).scalar()

            status_counts = {}
            for row in conn.execute(
                text("SELECT status, COUNT(*) FROM checkpoints GROUP BY status")
            ).fetchall():
                status_counts[row[0]] = row[1]

            return {
                "checkpoints": checkpoint_count,
                "executions": execution_count,
                "checkpoints_by_status": status_counts,
            }

    def cleanup_old_checkpoints(self, days: int = 30) -> int:
        """
        Delete checkpoints older than specified days.

        Args:
            days: Age threshold in days

        Returns:
            Number of deleted checkpoints
        """
        with self._engine.connect() as conn:
            if self._is_sqlite:
                result = conn.execute(
                    text("""
                    DELETE FROM checkpoints
                    WHERE created_at < datetime('now', :days || ' days')
                    AND status IN ('completed', 'failed')
                """),
                    {"days": f"-{days}"},
                )
            else:
                result = conn.execute(
                    text("""
                    DELETE FROM checkpoints
                    WHERE created_at < NOW() - INTERVAL ':days days'
                    AND status IN ('completed', 'failed')
                """),
                    {"days": days},
                )

            conn.commit()
            return result.rowcount

    def close(self) -> None:
        """Close database connections."""
        self._Session.remove()
        self._engine.dispose()
