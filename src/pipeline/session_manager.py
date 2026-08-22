"""
Session Manager for EduLens Tutoring Sessions

Manages the lifecycle of tutoring sessions, tracking state,
progress, and coordinating between components.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Callable

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """States of a tutoring session."""

    IDLE = auto()  # Waiting for wake word
    LISTENING = auto()  # Listening for student input
    PROCESSING = auto()  # Processing visual/audio input
    RESPONDING = auto()  # AI generating/speaking response
    WAITING_RESPONSE = auto()  # Waiting for student response
    PAUSED = auto()  # Session paused
    ENDED = auto()  # Session ended


class InteractionType(Enum):
    """Types of tutoring interactions."""

    PROBLEM_HELP = auto()  # Help with a specific problem
    CONCEPT_EXPLANATION = auto()  # Explaining a concept
    ANSWER_CHECK = auto()  # Checking student's answer
    ENCOURAGEMENT = auto()  # Positive feedback
    HINT_GIVEN = auto()  # Provided a hint
    CLARIFICATION = auto()  # Clarifying previous response


@dataclass
class Interaction:
    """Record of a single tutoring interaction."""

    interaction_id: str
    interaction_type: InteractionType
    timestamp: datetime

    # Input
    visual_context: str | None = None
    student_query: str | None = None

    # Output
    tutor_response: str | None = None
    hint_level: int = 0

    # Problem tracking
    problem_id: str | None = None
    subject: str | None = None
    was_correct: bool | None = None

    # Timing
    response_time_ms: int = 0


@dataclass
class SessionStats:
    """Statistics for a tutoring session."""

    total_interactions: int = 0
    problems_attempted: int = 0
    problems_correct: int = 0
    hints_given: int = 0
    concepts_explained: int = 0

    # By subject
    subject_breakdown: dict[str, int] = field(default_factory=dict)

    # Time
    total_time_minutes: float = 0.0
    average_response_time_ms: float = 0.0


@dataclass
class TutoringSession:
    """Represents a complete tutoring session."""

    session_id: str
    student_id: str
    start_time: datetime
    end_time: datetime | None = None

    state: SessionState = SessionState.IDLE
    interactions: list[Interaction] = field(default_factory=list)

    # Current context
    current_problem_id: str | None = None
    current_subject: str | None = None
    current_hint_level: int = 0

    # Session limits
    max_duration_minutes: int = 120  # 2 hour max
    idle_timeout_minutes: int = 5

    # Callbacks
    _on_state_change: Callable[[SessionState], None] | None = None

    def add_interaction(self, interaction: Interaction) -> None:
        """Add an interaction to the session."""
        self.interactions.append(interaction)
        logger.info(f"Session {self.session_id}: Added {interaction.interaction_type.name}")

    def get_stats(self) -> SessionStats:
        """Calculate session statistics."""
        stats = SessionStats()
        stats.total_interactions = len(self.interactions)

        response_times = []
        for interaction in self.interactions:
            if interaction.interaction_type == InteractionType.PROBLEM_HELP:
                stats.problems_attempted += 1
                if interaction.was_correct:
                    stats.problems_correct += 1

            if interaction.interaction_type == InteractionType.HINT_GIVEN:
                stats.hints_given += 1

            if interaction.interaction_type == InteractionType.CONCEPT_EXPLANATION:
                stats.concepts_explained += 1

            if interaction.subject:
                stats.subject_breakdown[interaction.subject] = (
                    stats.subject_breakdown.get(interaction.subject, 0) + 1
                )

            if interaction.response_time_ms > 0:
                response_times.append(interaction.response_time_ms)

        # Calculate time
        end = self.end_time or datetime.utcnow()
        stats.total_time_minutes = (end - self.start_time).total_seconds() / 60

        if response_times:
            stats.average_response_time_ms = sum(response_times) / len(response_times)

        return stats


class SessionManager:
    """
    Manages tutoring sessions for EduLens.

    Responsibilities:
    - Create and track sessions
    - Manage session state transitions
    - Enforce session limits and timeouts
    - Provide session statistics
    """

    def __init__(
        self,
        max_concurrent_sessions: int = 1,  # Device typically has 1 user
        default_max_duration_minutes: int = 120,
        default_idle_timeout_minutes: int = 5,
    ) -> None:
        self.max_concurrent_sessions = max_concurrent_sessions
        self.default_max_duration = default_max_duration_minutes
        self.default_idle_timeout = default_idle_timeout_minutes

        self._active_sessions: dict[str, TutoringSession] = {}
        self._session_history: list[TutoringSession] = []
        self._last_activity: dict[str, datetime] = {}

    def create_session(
        self,
        student_id: str,
        on_state_change: Callable[[SessionState], None] | None = None,
    ) -> TutoringSession:
        """
        Create a new tutoring session.

        Args:
            student_id: ID of the student
            on_state_change: Callback for state changes

        Returns:
            New TutoringSession instance
        """
        # Check concurrent session limit
        if len(self._active_sessions) >= self.max_concurrent_sessions:
            # End oldest session
            oldest_id = min(
                self._active_sessions.keys(),
                key=lambda k: self._active_sessions[k].start_time,
            )
            self.end_session(oldest_id)

        session_id = str(uuid.uuid4())[:8]
        session = TutoringSession(
            session_id=session_id,
            student_id=student_id,
            start_time=datetime.utcnow(),
            max_duration_minutes=self.default_max_duration,
            idle_timeout_minutes=self.default_idle_timeout,
            _on_state_change=on_state_change,
        )

        self._active_sessions[session_id] = session
        self._last_activity[session_id] = datetime.utcnow()

        logger.info(f"Created session {session_id} for student {student_id}")
        return session

    def get_session(self, session_id: str) -> TutoringSession | None:
        """Get an active session by ID."""
        return self._active_sessions.get(session_id)

    def get_active_session_for_student(self, student_id: str) -> TutoringSession | None:
        """Get active session for a student."""
        for session in self._active_sessions.values():
            if session.student_id == student_id:
                return session
        return None

    def update_state(self, session_id: str, new_state: SessionState) -> None:
        """Update session state."""
        session = self._active_sessions.get(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return

        old_state = session.state
        session.state = new_state
        self._last_activity[session_id] = datetime.utcnow()

        logger.debug(f"Session {session_id}: {old_state.name} -> {new_state.name}")

        if session._on_state_change:
            session._on_state_change(new_state)

    def record_interaction(
        self,
        session_id: str,
        interaction_type: InteractionType,
        visual_context: str | None = None,
        student_query: str | None = None,
        tutor_response: str | None = None,
        problem_id: str | None = None,
        subject: str | None = None,
        was_correct: bool | None = None,
        hint_level: int = 0,
        response_time_ms: int = 0,
    ) -> Interaction | None:
        """
        Record an interaction in the session.

        Returns the created Interaction or None if session not found.
        """
        session = self._active_sessions.get(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return None

        interaction = Interaction(
            interaction_id=str(uuid.uuid4())[:8],
            interaction_type=interaction_type,
            timestamp=datetime.utcnow(),
            visual_context=visual_context,
            student_query=student_query,
            tutor_response=tutor_response,
            problem_id=problem_id,
            subject=subject,
            was_correct=was_correct,
            hint_level=hint_level,
            response_time_ms=response_time_ms,
        )

        session.add_interaction(interaction)
        self._last_activity[session_id] = datetime.utcnow()

        # Update session context
        if problem_id:
            session.current_problem_id = problem_id
        if subject:
            session.current_subject = subject
        if hint_level > session.current_hint_level:
            session.current_hint_level = hint_level

        return interaction

    def end_session(self, session_id: str) -> SessionStats | None:
        """
        End a tutoring session.

        Returns session statistics or None if not found.
        """
        session = self._active_sessions.pop(session_id, None)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return None

        session.end_time = datetime.utcnow()
        session.state = SessionState.ENDED

        # Calculate stats
        stats = session.get_stats()

        # Move to history
        self._session_history.append(session)
        self._last_activity.pop(session_id, None)

        logger.info(
            f"Ended session {session_id}: "
            f"{stats.total_interactions} interactions, "
            f"{stats.problems_correct}/{stats.problems_attempted} correct, "
            f"{stats.total_time_minutes:.1f} minutes"
        )

        return stats

    def check_timeouts(self) -> list[str]:
        """
        Check for sessions that have timed out.

        Returns list of session IDs that were ended due to timeout.
        """
        now = datetime.utcnow()
        timed_out = []

        for session_id, session in list(self._active_sessions.items()):
            last_activity = self._last_activity.get(session_id, session.start_time)

            # Check idle timeout
            idle_duration = (now - last_activity).total_seconds() / 60
            if idle_duration > session.idle_timeout_minutes:
                logger.info(f"Session {session_id} idle timeout")
                self.end_session(session_id)
                timed_out.append(session_id)
                continue

            # Check max duration
            session_duration = (now - session.start_time).total_seconds() / 60
            if session_duration > session.max_duration_minutes:
                logger.info(f"Session {session_id} max duration reached")
                self.end_session(session_id)
                timed_out.append(session_id)

        return timed_out

    def get_daily_stats(self, student_id: str) -> dict[str, Any]:
        """Get today's tutoring statistics for a student."""
        today = datetime.utcnow().date()

        total_time = 0.0
        total_problems = 0
        total_correct = 0
        subjects = {}

        for session in self._session_history:
            if session.student_id != student_id:
                continue
            if session.start_time.date() != today:
                continue

            stats = session.get_stats()
            total_time += stats.total_time_minutes
            total_problems += stats.problems_attempted
            total_correct += stats.problems_correct

            for subject, count in stats.subject_breakdown.items():
                subjects[subject] = subjects.get(subject, 0) + count

        return {
            "date": today.isoformat(),
            "total_time_minutes": total_time,
            "problems_attempted": total_problems,
            "problems_correct": total_correct,
            "accuracy": total_correct / total_problems if total_problems > 0 else 0,
            "subjects": subjects,
        }

    def pause_session(self, session_id: str) -> None:
        """Pause a session."""
        self.update_state(session_id, SessionState.PAUSED)

    def resume_session(self, session_id: str) -> None:
        """Resume a paused session."""
        session = self._active_sessions.get(session_id)
        if session and session.state == SessionState.PAUSED:
            self.update_state(session_id, SessionState.IDLE)


def create_session_manager() -> SessionManager:
    """Factory function to create a configured session manager."""
    return SessionManager()
