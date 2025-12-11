"""
Integration Tests for Session Flow

Tests complete tutoring session lifecycle including multi-turn conversations,
session timeout handling, and progress tracking.

Task: TST-001-T2 - Integration Test Suite
Author: Testing Agent (TST-001)
"""

import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from src.pipeline.session_manager import (
    SessionManager,
    SessionState,
    InteractionType,
    TutoringSession,
)


class TestCompleteTutoringSessionFlow:
    """Test complete tutoring session from start to finish."""

    def test_session_creation(
        self,
        session_manager,
    ):
        """Test session is created successfully."""
        student_id = "TEST_STUDENT_001"

        session = session_manager.create_session(student_id)

        assert session is not None
        assert session.student_id == student_id
        assert session.state == SessionState.IDLE
        assert session.start_time is not None
        assert session.end_time is None

    def test_session_state_transitions(
        self,
        session_manager,
        active_session,
    ):
        """Test session transitions through states correctly."""
        session_id = active_session.session_id

        # IDLE -> LISTENING
        session_manager.update_state(session_id, SessionState.LISTENING)
        session = session_manager.get_session(session_id)
        assert session.state == SessionState.LISTENING

        # LISTENING -> PROCESSING
        session_manager.update_state(session_id, SessionState.PROCESSING)
        session = session_manager.get_session(session_id)
        assert session.state == SessionState.PROCESSING

        # PROCESSING -> RESPONDING
        session_manager.update_state(session_id, SessionState.RESPONDING)
        session = session_manager.get_session(session_id)
        assert session.state == SessionState.RESPONDING

        # RESPONDING -> WAITING_RESPONSE
        session_manager.update_state(session_id, SessionState.WAITING_RESPONSE)
        session = session_manager.get_session(session_id)
        assert session.state == SessionState.WAITING_RESPONSE

    def test_interaction_recording(
        self,
        session_manager,
        active_session,
    ):
        """Test interactions are recorded in session."""
        session_id = active_session.session_id

        # Record interaction
        interaction = session_manager.record_interaction(
            session_id=session_id,
            interaction_type=InteractionType.PROBLEM_HELP,
            visual_context="Problem: What is 2+3?",
            student_query="How do I solve this?",
            tutor_response="Let's think about counting. If you have 2 apples...",
            problem_id="PROB_001",
            subject="math",
            was_correct=None,
            hint_level=1,
            response_time_ms=1500,
        )

        assert interaction is not None
        assert interaction.interaction_type == InteractionType.PROBLEM_HELP

        # Verify session has interaction
        session = session_manager.get_session(session_id)
        assert len(session.interactions) == 1
        assert session.interactions[0] == interaction

    def test_complete_problem_solving_flow(
        self,
        session_manager,
        active_session,
    ):
        """Test complete flow of solving a problem."""
        session_id = active_session.session_id

        # 1. Student looks at problem (PROCESSING)
        session_manager.update_state(session_id, SessionState.PROCESSING)

        # 2. Student asks question (LISTENING)
        session_manager.update_state(session_id, SessionState.LISTENING)
        session_manager.record_interaction(
            session_id=session_id,
            interaction_type=InteractionType.PROBLEM_HELP,
            visual_context="What is 5 + 7?",
            student_query="I don't understand",
            tutor_response="Let's break it down...",
        )

        # 3. AI provides hint (RESPONDING)
        session_manager.update_state(session_id, SessionState.RESPONDING)
        session_manager.record_interaction(
            session_id=session_id,
            interaction_type=InteractionType.HINT_GIVEN,
            tutor_response="Think about counting from 5: 6, 7, 8...",
            hint_level=1,
        )

        # 4. Student tries again (WAITING_RESPONSE)
        session_manager.update_state(session_id, SessionState.WAITING_RESPONSE)

        # 5. Student gets it right (PROCESSING)
        session_manager.update_state(session_id, SessionState.PROCESSING)
        session_manager.record_interaction(
            session_id=session_id,
            interaction_type=InteractionType.ANSWER_CHECK,
            student_query="Is 12 correct?",
            tutor_response="Yes! Excellent work!",
            was_correct=True,
        )

        # Verify flow
        session = session_manager.get_session(session_id)
        assert len(session.interactions) >= 3

    def test_session_completion(
        self,
        session_manager,
        active_session,
    ):
        """Test session ends correctly and generates stats."""
        session_id = active_session.session_id

        # Record some interactions
        session_manager.record_interaction(
            session_id=session_id,
            interaction_type=InteractionType.PROBLEM_HELP,
            subject="math",
            was_correct=True,
        )
        session_manager.record_interaction(
            session_id=session_id,
            interaction_type=InteractionType.PROBLEM_HELP,
            subject="math",
            was_correct=False,
        )

        # End session
        stats = session_manager.end_session(session_id)

        assert stats is not None
        assert stats.total_interactions == 2
        assert stats.problems_attempted >= 1
        assert stats.total_time_minutes >= 0

        # Session should be ended
        session = session_manager.get_session(session_id)
        assert session is None  # No longer in active sessions


class TestMultiTurnConversations:
    """Test multi-turn conversation flows."""

    def test_sequential_questions(
        self,
        session_manager,
        active_session,
    ):
        """Test multiple sequential questions in one session."""
        session_id = active_session.session_id

        # Question 1
        session_manager.record_interaction(
            session_id=session_id,
            interaction_type=InteractionType.EXPLAIN_CONCEPT,
            student_query="What is addition?",
            tutor_response="Addition is combining numbers...",
            subject="math",
        )

        # Question 2 (follow-up)
        session_manager.record_interaction(
            session_id=session_id,
            interaction_type=InteractionType.PROBLEM_HELP,
            student_query="Can you show me an example?",
            tutor_response="Sure! Let's try 2 + 3...",
            subject="math",
        )

        # Question 3
        session_manager.record_interaction(
            session_id=session_id,
            interaction_type=InteractionType.ANSWER_CHECK,
            student_query="Is 5 correct?",
            tutor_response="Yes! Great job!",
            subject="math",
            was_correct=True,
        )

        # Verify all interactions recorded
        session = session_manager.get_session(session_id)
        assert len(session.interactions) == 3

    def test_conversation_context_maintained(
        self,
        session_manager,
        active_session,
    ):
        """Test conversation context is maintained across turns."""
        session_id = active_session.session_id

        # Set context with first problem
        session_manager.record_interaction(
            session_id=session_id,
            interaction_type=InteractionType.PROBLEM_HELP,
            problem_id="PROB_001",
            subject="math",
            visual_context="Problem 1: What is 5 + 3?",
        )

        session = session_manager.get_session(session_id)
        assert session.current_problem_id == "PROB_001"
        assert session.current_subject == "math"

    def test_hint_escalation(
        self,
        session_manager,
        active_session,
    ):
        """Test hint level escalates when student struggles."""
        session_id = active_session.session_id

        # Hint level 1
        session_manager.record_interaction(
            session_id=session_id,
            interaction_type=InteractionType.HINT_GIVEN,
            tutor_response="Try counting...",
            hint_level=1,
        )

        # Hint level 2
        session_manager.record_interaction(
            session_id=session_id,
            interaction_type=InteractionType.HINT_GIVEN,
            tutor_response="Start at 5 and count 3 more...",
            hint_level=2,
        )

        # Hint level 3
        session_manager.record_interaction(
            session_id=session_id,
            interaction_type=InteractionType.HINT_GIVEN,
            tutor_response="5... 6... 7... 8. The answer is 8!",
            hint_level=3,
        )

        session = session_manager.get_session(session_id)
        assert session.current_hint_level == 3

    def test_subject_switching(
        self,
        session_manager,
        active_session,
    ):
        """Test switching between different subjects in one session."""
        session_id = active_session.session_id

        # Math problem
        session_manager.record_interaction(
            session_id=session_id,
            interaction_type=InteractionType.PROBLEM_HELP,
            subject="math",
            student_query="What is 5 + 3?",
        )

        # Science question
        session_manager.record_interaction(
            session_id=session_id,
            interaction_type=InteractionType.EXPLAIN_CONCEPT,
            subject="science",
            student_query="What is photosynthesis?",
        )

        session = session_manager.get_session(session_id)
        assert len(session.interactions) == 2

        # Current subject should be science
        assert session.current_subject == "science"


class TestSessionTimeoutHandling:
    """Test session timeout and idle detection."""

    def test_idle_timeout_detection(
        self,
        session_manager,
    ):
        """Test idle sessions are detected."""
        # Create session with short timeout
        session_manager.default_idle_timeout = 0.01 / 60  # 0.6 seconds in minutes

        session = session_manager.create_session("TEST_STUDENT")
        session_id = session.session_id

        # Wait for timeout
        time.sleep(1)

        # Check timeouts
        timed_out = session_manager.check_timeouts()

        # Session should have timed out
        assert session_id in timed_out

    def test_activity_resets_idle_timer(
        self,
        session_manager,
        active_session,
    ):
        """Test activity resets the idle timer."""
        session_id = active_session.session_id

        # Record activity
        session_manager.record_interaction(
            session_id=session_id,
            interaction_type=InteractionType.PROBLEM_HELP,
            student_query="Test question",
        )

        # Update state (also activity)
        session_manager.update_state(session_id, SessionState.PROCESSING)

        # Should not timeout immediately after activity
        timed_out = session_manager.check_timeouts()
        assert session_id not in timed_out

    def test_max_duration_timeout(
        self,
        session_manager,
    ):
        """Test maximum session duration is enforced."""
        # Create session with very short max duration
        session = session_manager.create_session("TEST_STUDENT")
        session.max_duration_minutes = 0.01 / 60  # Very short for testing

        session_id = session.session_id

        # Wait
        time.sleep(1)

        # Check timeouts
        timed_out = session_manager.check_timeouts()

        # Should timeout due to max duration
        assert session_id in timed_out

    def test_pause_and_resume(
        self,
        session_manager,
        active_session,
    ):
        """Test session can be paused and resumed."""
        session_id = active_session.session_id

        # Pause
        session_manager.pause_session(session_id)
        session = session_manager.get_session(session_id)
        assert session.state == SessionState.PAUSED

        # Resume
        session_manager.resume_session(session_id)
        session = session_manager.get_session(session_id)
        assert session.state == SessionState.IDLE


class TestProgressTracking:
    """Test progress tracking throughout session."""

    def test_session_statistics(
        self,
        session_manager,
        active_session,
    ):
        """Test session statistics are calculated correctly."""
        session_id = active_session.session_id

        # Record various interactions
        session_manager.record_interaction(
            session_id=session_id,
            interaction_type=InteractionType.PROBLEM_HELP,
            subject="math",
            was_correct=True,
        )
        session_manager.record_interaction(
            session_id=session_id,
            interaction_type=InteractionType.PROBLEM_HELP,
            subject="math",
            was_correct=False,
        )
        session_manager.record_interaction(
            session_id=session_id,
            interaction_type=InteractionType.HINT_GIVEN,
            hint_level=1,
        )
        session_manager.record_interaction(
            session_id=session_id,
            interaction_type=InteractionType.EXPLAIN_CONCEPT,
            subject="science",
        )

        # Get stats
        session = session_manager.get_session(session_id)
        stats = session.get_stats()

        assert stats.total_interactions == 4
        assert stats.problems_attempted == 2
        assert stats.problems_correct == 1
        assert stats.hints_given == 1
        assert stats.concepts_explained == 1

    def test_subject_breakdown(
        self,
        session_manager,
        active_session,
    ):
        """Test subject breakdown in statistics."""
        session_id = active_session.session_id

        # Math interactions
        for _ in range(3):
            session_manager.record_interaction(
                session_id=session_id,
                interaction_type=InteractionType.PROBLEM_HELP,
                subject="math",
            )

        # Science interactions
        for _ in range(2):
            session_manager.record_interaction(
                session_id=session_id,
                interaction_type=InteractionType.PROBLEM_HELP,
                subject="science",
            )

        # Get stats
        session = session_manager.get_session(session_id)
        stats = session.get_stats()

        assert stats.subject_breakdown["math"] == 3
        assert stats.subject_breakdown["science"] == 2

    def test_accuracy_tracking(
        self,
        session_manager,
        active_session,
    ):
        """Test answer accuracy is tracked."""
        session_id = active_session.session_id

        # Correct answers
        for _ in range(7):
            session_manager.record_interaction(
                session_id=session_id,
                interaction_type=InteractionType.PROBLEM_HELP,
                was_correct=True,
            )

        # Incorrect answers
        for _ in range(3):
            session_manager.record_interaction(
                session_id=session_id,
                interaction_type=InteractionType.PROBLEM_HELP,
                was_correct=False,
            )

        session = session_manager.get_session(session_id)
        stats = session.get_stats()

        # 7 correct out of 10 = 70%
        assert stats.problems_attempted == 10
        assert stats.problems_correct == 7

    def test_daily_statistics(
        self,
        session_manager,
    ):
        """Test daily statistics aggregation."""
        student_id = "TEST_STUDENT"

        # Create and complete multiple sessions
        for i in range(3):
            session = session_manager.create_session(student_id)
            session_manager.record_interaction(
                session_id=session.session_id,
                interaction_type=InteractionType.PROBLEM_HELP,
                subject="math",
                was_correct=(i % 2 == 0),  # Alternate correct/incorrect
            )
            session_manager.end_session(session.session_id)

        # Get daily stats
        daily_stats = session_manager.get_daily_stats(student_id)

        assert daily_stats["problems_attempted"] >= 3
        assert "total_time_minutes" in daily_stats
        assert "accuracy" in daily_stats


class TestConcurrentSessions:
    """Test handling of concurrent sessions."""

    def test_max_concurrent_sessions_limit(
        self,
        session_manager,
    ):
        """Test maximum concurrent sessions is enforced."""
        student_id = "TEST_STUDENT"

        # Create first session
        session1 = session_manager.create_session(student_id)
        assert session1 is not None

        # Try to create second session (should end first one)
        session2 = session_manager.create_session(student_id)
        assert session2 is not None

        # First session should be ended
        old_session = session_manager.get_session(session1.session_id)
        assert old_session is None

    def test_get_active_session_for_student(
        self,
        session_manager,
    ):
        """Test retrieving active session for a student."""
        student_id = "TEST_STUDENT"

        # Create session
        session = session_manager.create_session(student_id)

        # Retrieve
        active = session_manager.get_active_session_for_student(student_id)

        assert active is not None
        assert active.session_id == session.session_id


@pytest.mark.performance
class TestSessionPerformance:
    """Test session management performance."""

    def test_state_transition_latency(
        self,
        session_manager,
        active_session,
        assert_latency,
    ):
        """Test state transitions are fast (<100ms)."""
        session_id = active_session.session_id

        start_time = time.perf_counter()

        session_manager.update_state(session_id, SessionState.PROCESSING)

        elapsed = time.perf_counter() - start_time

        assert_latency(elapsed, 0.1, "State transition")

    def test_interaction_recording_latency(
        self,
        session_manager,
        active_session,
        assert_latency,
    ):
        """Test interaction recording is fast."""
        session_id = active_session.session_id

        start_time = time.perf_counter()

        session_manager.record_interaction(
            session_id=session_id,
            interaction_type=InteractionType.PROBLEM_HELP,
            student_query="Test question",
        )

        elapsed = time.perf_counter() - start_time

        assert_latency(elapsed, 0.05, "Interaction recording")

    def test_statistics_calculation_latency(
        self,
        session_manager,
        active_session,
        assert_latency,
    ):
        """Test statistics calculation is fast even with many interactions."""
        session_id = active_session.session_id

        # Add many interactions
        for i in range(100):
            session_manager.record_interaction(
                session_id=session_id,
                interaction_type=InteractionType.PROBLEM_HELP,
                subject="math",
            )

        session = session_manager.get_session(session_id)

        start_time = time.perf_counter()

        stats = session.get_stats()

        elapsed = time.perf_counter() - start_time

        assert_latency(elapsed, 0.1, "Statistics calculation")
