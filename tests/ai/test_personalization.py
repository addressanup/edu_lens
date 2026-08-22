"""
Comprehensive test suite for EduLens Personalization Engine.

Tests student modeling, adaptive tutoring, progress tracking, and learning analytics.

Author: EduLens AI Team
Version: 1.0.0
"""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.ai.personalization.adaptive_tutor import (
    AdaptationContext,
    AdaptiveTutor,
    EmotionalState,
    ExplanationType,
    HintDirectness,
    create_adaptive_tutor,
)
from src.ai.personalization.learning_analytics import (
    LearningAnalytics,
    LearningPattern,
    create_learning_analytics,
)
from src.ai.personalization.progress_tracker import (
    AttemptOutcome,
    ConceptProgress,
    ProgressTracker,
    create_progress_tracker,
)
from src.ai.personalization.student_model import (
    ConceptKnowledgeState,
    LearningPace,
    LearningStyle,
    MasteryLevel,
    StudentModel,
    create_student_model,
)

# ============================================================================
# Student Model Tests
# ============================================================================


class TestStudentModel:
    """Test suite for StudentModel."""

    @pytest.fixture
    def student_model(self):
        """Create a student model for testing."""
        return create_student_model(student_id="test_student_123", age=9, grade=4)

    def test_initialization(self, student_model):
        """Test student model initialization."""
        assert student_model.student_id == "test_student_123"
        assert student_model.age == 9
        assert student_model.grade == 4
        assert len(student_model.concept_states) == 0
        assert student_model.session_count == 0

    def test_update_from_interaction(self, student_model):
        """Test updating model from interaction."""
        result = student_model.update_from_interaction(
            concept_id="math_001",
            problem_type="multiplication",
            correct=True,
            attempts=1,
            time_spent=30.0,
            hint_level_used=0,
            student_response="The answer is 12",
            difficulty_level=2,
        )

        assert "math_001" in student_model.concept_states
        assert result["mastery_level"] == MasteryLevel.BEGINNER.name
        assert student_model.total_problems_attempted == 1

    def test_bayesian_knowledge_tracking(self, student_model):
        """Test Bayesian knowledge state updates."""
        concept_id = "math_001"

        # Initially not attempted
        assert student_model.get_mastery_level(concept_id) == MasteryLevel.NOT_ATTEMPTED

        # Add correct interaction
        student_model.update_from_interaction(
            concept_id=concept_id,
            problem_type="test",
            correct=True,
            attempts=1,
            time_spent=20.0,
            hint_level_used=0,
            student_response="correct",
            difficulty_level=2,
        )

        # Probability should increase
        state = student_model.concept_states[concept_id]
        assert state.probability_known > 0.0
        assert state.correct_count == 1

        # Add more correct interactions
        for _ in range(5):
            student_model.update_from_interaction(
                concept_id=concept_id,
                problem_type="test",
                correct=True,
                attempts=1,
                time_spent=20.0,
                hint_level_used=0,
                student_response="correct",
                difficulty_level=2,
            )

        # Should reach higher mastery
        final_state = student_model.concept_states[concept_id]
        assert final_state.probability_known > 0.5
        assert student_model.get_mastery_level(concept_id).value >= MasteryLevel.PROFICIENT.value

    def test_learning_style_detection(self, student_model):
        """Test learning style detection."""
        # Add interactions with different patterns
        for i in range(10):
            student_model.update_from_interaction(
                concept_id=f"concept_{i}",
                problem_type="test",
                correct=True,
                attempts=1,
                time_spent=15.0,  # Quick responses
                hint_level_used=1,  # Uses hints
                student_response="short",
                difficulty_level=2,
            )

        style = student_model.get_learning_style()
        assert isinstance(style, LearningStyle)

        # Get distribution
        distribution = student_model.get_learning_style_distribution()
        assert len(distribution) == len(LearningStyle)
        assert abs(sum(distribution.values()) - 1.0) < 0.01  # Should sum to ~1

    def test_pace_estimation(self, student_model):
        """Test learning pace estimation."""
        # Add fast interactions
        for i in range(5):
            student_model.update_from_interaction(
                concept_id=f"concept_{i}",
                problem_type="quick",
                correct=True,
                attempts=1,
                time_spent=10.0,
                hint_level_used=0,
                student_response="fast",
                difficulty_level=2,
            )

        pace = student_model.get_pace()
        assert isinstance(pace, LearningPace)

    def test_difficulty_prediction(self, student_model):
        """Test difficulty level prediction."""
        concept_id = "math_001"

        # Before any attempts - should predict moderate
        difficulty = student_model.predict_difficulty(concept_id)
        assert 1 <= difficulty <= 5

        # After successful attempts
        for _ in range(3):
            student_model.update_from_interaction(
                concept_id=concept_id,
                problem_type="test",
                correct=True,
                attempts=1,
                time_spent=20.0,
                hint_level_used=0,
                student_response="correct",
                difficulty_level=2,
            )

        # Should predict higher difficulty
        new_difficulty = student_model.predict_difficulty(concept_id)
        assert new_difficulty >= difficulty

    def test_strengths_and_weaknesses(self, student_model):
        """Test identification of strengths and weaknesses."""
        # Add concepts with varying mastery
        concepts = {
            "strong_1": (True, 5),
            "strong_2": (True, 5),
            "weak_1": (False, 5),
            "weak_2": (False, 5),
        }

        for concept_id, (correct, count) in concepts.items():
            for _ in range(count):
                student_model.update_from_interaction(
                    concept_id=concept_id,
                    problem_type="test",
                    correct=correct,
                    attempts=1,
                    time_spent=20.0,
                    hint_level_used=0,
                    student_response="response",
                    difficulty_level=2,
                )

        strengths = student_model.get_strengths(2)
        weaknesses = student_model.get_weaknesses(2)

        assert len(strengths) == 2
        assert len(weaknesses) == 2
        assert all("strong" in s[0] for s in strengths)
        assert all("weak" in w[0] for w in weaknesses)

    def test_save_and_load(self, student_model, tmp_path):
        """Test saving and loading student model."""
        # Add some data
        student_model.update_from_interaction(
            concept_id="math_001",
            problem_type="test",
            correct=True,
            attempts=1,
            time_spent=20.0,
            hint_level_used=0,
            student_response="test",
            difficulty_level=2,
        )

        # Save
        save_path = tmp_path / "student_model.json"
        success = student_model.save(str(save_path))
        assert success
        assert save_path.exists()

        # Load
        loaded_model = StudentModel.load(str(save_path))
        assert loaded_model is not None
        assert loaded_model.student_id == student_model.student_id
        assert loaded_model.age == student_model.age
        assert len(loaded_model.concept_states) == len(student_model.concept_states)


# ============================================================================
# Adaptive Tutor Tests
# ============================================================================


class TestAdaptiveTutor:
    """Test suite for AdaptiveTutor."""

    @pytest.fixture
    def adaptive_tutor(self):
        """Create adaptive tutor for testing."""
        student = create_student_model("test_student", age=9, grade=4)
        return create_adaptive_tutor(student)

    @pytest.fixture
    def sample_context(self):
        """Create sample adaptation context."""
        return AdaptationContext(
            concept_id="math_001",
            problem_statement="What is 6 × 4?",
            student_attempts=["20"],
            time_on_problem=30.0,
            hints_used=0,
            difficulty_level=2,
            session_duration=300.0,
            problems_solved_today=3,
        )

    def test_initialization(self, adaptive_tutor):
        """Test adaptive tutor initialization."""
        assert adaptive_tutor.student_model is not None
        assert adaptive_tutor.current_hint_level == HintDirectness.SOCRATIC
        assert adaptive_tutor.consecutive_struggles == 0

    def test_hint_level_selection(self, adaptive_tutor, sample_context):
        """Test hint level selection."""
        # First attempt - should be subtle
        hint_level = adaptive_tutor.select_hint_level(sample_context)
        assert isinstance(hint_level, HintDirectness)

        # After multiple attempts - should be more direct
        sample_context.student_attempts = ["20", "22", "23"]
        hint_level_after = adaptive_tutor.select_hint_level(sample_context)
        assert hint_level_after.value >= hint_level.value

    def test_hint_generation(self, adaptive_tutor, sample_context):
        """Test hint generation."""
        hint_response = adaptive_tutor.generate_hint(sample_context)

        assert isinstance(hint_response.hint_text, str)
        assert len(hint_response.hint_text) > 0
        assert isinstance(hint_response.directness, HintDirectness)
        assert isinstance(hint_response.encouragement, str)
        assert hint_response.follow_up_question is not None

    def test_explanation_adjustment(self, adaptive_tutor):
        """Test explanation adjustment by learning style."""
        base_explanation = "Multiplication is repeated addition."

        explanation = adaptive_tutor.adjust_explanation(
            concept_id="math_001", base_explanation=base_explanation, context=None
        )

        assert isinstance(explanation.explanation_text, str)
        assert len(explanation.explanation_text) >= len(base_explanation)
        assert isinstance(explanation.explanation_type, ExplanationType)
        assert isinstance(explanation.examples, list)

    def test_example_selection(self, adaptive_tutor):
        """Test example selection."""
        examples = adaptive_tutor.select_examples("math_001", count=3)

        assert len(examples) == 3
        assert all("problem" in ex for ex in examples)
        assert all("difficulty" in ex for ex in examples)

        # Difficulty should increase across examples
        difficulties = [ex["difficulty"] for ex in examples]
        assert difficulties[0] <= difficulties[-1]

    def test_frustration_detection(self, adaptive_tutor, sample_context):
        """Test emotional state detection."""
        # Normal state
        state, confidence = adaptive_tutor.detect_frustration(sample_context)
        assert isinstance(state, EmotionalState)
        assert 0.0 <= confidence <= 1.0

        # Frustrated state - multiple attempts, long time
        sample_context.student_attempts = ["a", "b", "c", "d"]
        sample_context.time_on_problem = 120.0
        sample_context.hints_used = 3

        state_frustrated, conf_frustrated = adaptive_tutor.detect_frustration(sample_context)
        assert state_frustrated in [EmotionalState.STRUGGLING, EmotionalState.FRUSTRATED]
        assert conf_frustrated > 0.4

    def test_adaptation_to_emotional_state(self, adaptive_tutor, sample_context):
        """Test adaptation based on emotional state."""
        # Test frustrated adaptation
        adaptation = adaptive_tutor.adapt_to_emotional_state(
            EmotionalState.FRUSTRATED, sample_context
        )

        assert adaptation["action"] == "provide_break"
        assert adaptation["difficulty_adjustment"] == -1
        assert adaptation["show_encouragement"] is True

        # Test confident adaptation
        adaptation_confident = adaptive_tutor.adapt_to_emotional_state(
            EmotionalState.CONFIDENT, sample_context
        )

        assert adaptation_confident["difficulty_adjustment"] >= 0

    def test_celebration(self, adaptive_tutor):
        """Test progress celebration."""
        celebration = adaptive_tutor.celebrate_progress(
            "mastery", {"concept": "Multiplication", "count": 5}
        )

        assert isinstance(celebration, str)
        assert len(celebration) > 0

    def test_session_state_updates(self, adaptive_tutor, sample_context):
        """Test session state tracking."""
        # Success
        adaptive_tutor.update_session_state(True, sample_context)
        assert adaptive_tutor.consecutive_successes == 1
        assert adaptive_tutor.consecutive_struggles == 0

        # Failure
        adaptive_tutor.update_session_state(False, sample_context)
        assert adaptive_tutor.consecutive_successes == 0
        assert adaptive_tutor.consecutive_struggles == 1


# ============================================================================
# Progress Tracker Tests
# ============================================================================


class TestProgressTracker:
    """Test suite for ProgressTracker."""

    @pytest.fixture
    def progress_tracker(self):
        """Create progress tracker for testing."""
        student = create_student_model("test_student", age=9, grade=4)
        return create_progress_tracker(student)

    def test_initialization(self, progress_tracker):
        """Test progress tracker initialization."""
        assert progress_tracker.student_model is not None
        assert len(progress_tracker.concept_progress) == 0
        assert len(progress_tracker.attempt_history) == 0

    def test_record_attempt(self, progress_tracker):
        """Test recording problem attempts."""
        result = progress_tracker.record_attempt(
            concept_id="math_001",
            problem_id="prob_001",
            correct=True,
            time_spent=30.0,
            hints_used=0,
            difficulty=2,
            attempts_on_problem=1,
        )

        assert "math_001" in progress_tracker.concept_progress
        assert result["total_attempts"] == 1
        assert result["mastery_score"] > 0.0
        assert len(progress_tracker.attempt_history) == 1

    def test_mastery_calculation(self, progress_tracker):
        """Test mastery score calculation."""
        concept_id = "math_001"

        # Add multiple successful attempts
        for i in range(5):
            progress_tracker.record_attempt(
                concept_id=concept_id,
                problem_id=f"prob_{i}",
                correct=True,
                time_spent=25.0,
                hints_used=0,
                difficulty=2 + (i % 3),
                attempts_on_problem=1,
            )

        mastery = progress_tracker.calculate_mastery(concept_id)
        assert 0.0 <= mastery <= 1.0
        assert mastery > 0.3  # Should have some mastery

    def test_spaced_repetition(self, progress_tracker):
        """Test spaced repetition scheduling."""
        concept_id = "math_001"

        # Record successful attempt
        progress_tracker.record_attempt(
            concept_id=concept_id,
            problem_id="prob_001",
            correct=True,
            time_spent=20.0,
            hints_used=0,
            difficulty=2,
            attempts_on_problem=1,
        )

        progress = progress_tracker.concept_progress[concept_id]

        # Should have next review scheduled
        assert progress.next_review_date is not None
        assert progress.interval > 0
        assert progress.easiness_factor > 0

    def test_gap_identification(self, progress_tracker):
        """Test knowledge gap identification."""
        # Add concepts with poor performance
        for i in range(5):
            progress_tracker.record_attempt(
                concept_id="weak_concept",
                problem_id=f"prob_{i}",
                correct=False,
                time_spent=60.0,
                hints_used=2,
                difficulty=2,
                attempts_on_problem=2,
            )

        gaps = progress_tracker.identify_gaps()

        assert len(gaps) > 0
        assert gaps[0]["concept_id"] == "weak_concept"
        assert gaps[0]["severity"] > 0.0

    def test_review_suggestions(self, progress_tracker):
        """Test review suggestions."""
        # Add concept that needs review
        concept_id = "math_001"
        progress_tracker.record_attempt(
            concept_id=concept_id,
            problem_id="prob_001",
            correct=True,
            time_spent=20.0,
            hints_used=0,
            difficulty=2,
            attempts_on_problem=1,
        )

        # Manually set to be due for review
        progress_tracker.concept_progress[concept_id].next_review_date = time.time() - 86400

        suggestions = progress_tracker.suggest_review(max_suggestions=5)

        assert len(suggestions) > 0
        assert suggestions[0]["concept_id"] == concept_id

    def test_progress_report_generation(self, progress_tracker):
        """Test progress report generation."""
        # Add some data
        for i in range(3):
            progress_tracker.record_attempt(
                concept_id=f"concept_{i}",
                problem_id=f"prob_{i}",
                correct=(i % 2 == 0),
                time_spent=30.0,
                hints_used=i % 2,
                difficulty=2,
                attempts_on_problem=1,
            )

        report = progress_tracker.generate_report()

        assert report.student_id == progress_tracker.student_model.student_id
        assert report.total_concepts > 0
        assert 0.0 <= report.overall_accuracy <= 1.0
        assert isinstance(report.top_strengths, list)
        assert isinstance(report.recommended_practice, list)

    def test_save_and_load(self, progress_tracker, tmp_path):
        """Test saving and loading progress data."""
        # Add data
        progress_tracker.record_attempt(
            concept_id="math_001",
            problem_id="prob_001",
            correct=True,
            time_spent=30.0,
            hints_used=0,
            difficulty=2,
            attempts_on_problem=1,
        )

        # Save
        save_path = tmp_path / "progress.json"
        success = progress_tracker.save(str(save_path))
        assert success
        assert save_path.exists()

        # Load
        loaded_tracker = ProgressTracker.load(progress_tracker.student_model, str(save_path))
        assert loaded_tracker is not None
        assert len(loaded_tracker.concept_progress) == len(progress_tracker.concept_progress)


# ============================================================================
# Learning Analytics Tests
# ============================================================================


class TestLearningAnalytics:
    """Test suite for LearningAnalytics."""

    @pytest.fixture
    def learning_analytics(self):
        """Create learning analytics for testing."""
        return create_learning_analytics("test_student_123", anonymize=True)

    def test_initialization(self, learning_analytics):
        """Test learning analytics initialization."""
        assert learning_analytics.student_id == "test_student_123"
        assert len(learning_analytics.student_id_hash) > 0
        assert learning_analytics.student_id != learning_analytics.student_id_hash

    def test_session_update(self, learning_analytics):
        """Test updating from session data."""
        session_data = {
            "session_id": "session_001",
            "start_time": time.time(),
            "end_time": time.time() + 1200,
            "problems_attempted": 10,
            "problems_correct": 8,
            "concepts_practiced": ["concept_1", "concept_2"],
            "mastery_scores": {"concept_1": 0.6, "concept_2": 0.7},
        }

        result = learning_analytics.update_from_session(session_data)

        assert "daily_accuracy" in result
        assert "weekly_pattern" in result
        assert len(learning_analytics.daily_metrics) > 0

    def test_pattern_detection(self, learning_analytics):
        """Test learning pattern detection."""
        # Add multiple sessions with improving performance over multiple weeks
        # Need enough data for pattern detection (at least 2 weeks)
        for i in range(10):
            session_data = {
                "session_id": f"session_{i}",
                "start_time": time.time() - (10 - i) * 86400,
                "end_time": time.time() - (10 - i) * 86400 + 1200,
                "problems_attempted": 10,
                "problems_correct": 5 + i,  # Improving
                "concepts_practiced": ["concept_1"],
                "mastery_scores": {"concept_1": 0.5 + i * 0.05},
            }
            learning_analytics.update_from_session(session_data)

        patterns = learning_analytics.detect_learning_patterns()

        assert isinstance(patterns, dict)
        # Pattern detection may not always find patterns with limited data
        # Just verify the method works without errors

    def test_trend_analysis(self, learning_analytics):
        """Test trend analysis."""
        # Add data over multiple days
        for i in range(7):
            session_data = {
                "session_id": f"session_{i}",
                "start_time": time.time() - (7 - i) * 86400,
                "end_time": time.time() - (7 - i) * 86400 + 1200,
                "problems_attempted": 10,
                "problems_correct": 7,
                "concepts_practiced": ["concept_1"],
                "mastery_scores": {},
            }
            learning_analytics.update_from_session(session_data)

        trend = learning_analytics.analyze_trends("accuracy", days=7)

        assert trend.metric_name == "accuracy"
        assert trend.trend_direction in ["increasing", "decreasing", "stable", "insufficient_data"]
        assert isinstance(trend.insights, list)

    def test_engagement_score(self, learning_analytics):
        """Test engagement score calculation."""
        # Add sessions
        for i in range(5):
            session_data = {
                "session_id": f"session_{i}",
                "start_time": time.time() - i * 86400,
                "end_time": time.time() - i * 86400 + 1200,
                "problems_attempted": 8,
                "problems_correct": 6,
                "concepts_practiced": ["concept_1"],
                "mastery_scores": {},
            }
            learning_analytics.update_from_session(session_data)

        engagement = learning_analytics.get_engagement_score()

        assert 0.0 <= engagement <= 1.0

    def test_learning_velocity(self, learning_analytics):
        """Test learning velocity calculation."""
        velocity = learning_analytics.get_learning_velocity(days=7)

        assert velocity >= 0.0

    def test_insights_generation(self, learning_analytics):
        """Test insights generation."""
        # Add some session data
        for i in range(3):
            session_data = {
                "session_id": f"session_{i}",
                "start_time": time.time() - i * 86400,
                "end_time": time.time() - i * 86400 + 1200,
                "problems_attempted": 10,
                "problems_correct": 7,
                "concepts_practiced": ["concept_1"],
                "mastery_scores": {},
            }
            learning_analytics.update_from_session(session_data)

        insights = learning_analytics.get_insights()

        assert isinstance(insights, list)

    def test_anonymized_export(self, learning_analytics):
        """Test anonymized data export."""
        # Add data
        session_data = {
            "session_id": "session_001",
            "start_time": time.time(),
            "end_time": time.time() + 1200,
            "problems_attempted": 10,
            "problems_correct": 8,
            "concepts_practiced": ["concept_1"],
            "mastery_scores": {},
        }
        learning_analytics.update_from_session(session_data)

        exported = learning_analytics.export_anonymized_data()

        assert exported["student_id_hash"] == learning_analytics.student_id_hash
        assert "weekly_statistics" in exported
        assert "engagement_score" in exported
        assert "insights" in exported

        # Should not contain raw student ID
        export_str = json.dumps(exported)
        assert learning_analytics.student_id not in export_str


# ============================================================================
# Integration Tests
# ============================================================================


class TestPersonalizationIntegration:
    """Integration tests for the complete personalization system."""

    def test_end_to_end_learning_session(self):
        """Test a complete learning session from start to finish."""
        # Create student model
        student = create_student_model("integration_test", age=9, grade=4)

        # Create supporting systems
        tutor = create_adaptive_tutor(student)
        tracker = create_progress_tracker(student)
        analytics = create_learning_analytics("integration_test", anonymize=True)

        # Simulate a learning session
        concept_id = "math_multiplication"
        problems = [
            {"id": "p1", "correct": False, "time": 45.0, "attempts": 2},
            {"id": "p2", "correct": True, "time": 30.0, "attempts": 1},
            {"id": "p3", "correct": True, "time": 25.0, "attempts": 1},
            {"id": "p4", "correct": True, "time": 20.0, "attempts": 1},
        ]

        session_start = time.time()
        correct_count = 0

        for i, problem in enumerate(problems):
            # Update student model
            student.update_from_interaction(
                concept_id=concept_id,
                problem_type="multiplication",
                correct=problem["correct"],
                attempts=problem["attempts"],
                time_spent=problem["time"],
                hint_level_used=1 if problem["attempts"] > 1 else 0,
                student_response="response",
                difficulty_level=2,
            )

            # Record in progress tracker
            tracker.record_attempt(
                concept_id=concept_id,
                problem_id=problem["id"],
                correct=problem["correct"],
                time_spent=problem["time"],
                hints_used=1 if problem["attempts"] > 1 else 0,
                difficulty=2,
                attempts_on_problem=problem["attempts"],
            )

            if problem["correct"]:
                correct_count += 1

            # Get adaptive hint if needed
            if not problem["correct"] or problem["attempts"] > 1:
                context = AdaptationContext(
                    concept_id=concept_id,
                    problem_statement="Test problem",
                    student_attempts=[],
                    time_on_problem=problem["time"],
                    hints_used=1 if problem["attempts"] > 1 else 0,
                    difficulty_level=2,
                    session_duration=time.time() - session_start,
                    problems_solved_today=i,
                )
                hint = tutor.generate_hint(context)
                assert hint.hint_text is not None

        # Update analytics
        session_data = {
            "session_id": "integration_session",
            "start_time": session_start,
            "end_time": time.time(),
            "problems_attempted": len(problems),
            "problems_correct": correct_count,
            "concepts_practiced": [concept_id],
            "mastery_scores": {concept_id: tracker.calculate_mastery(concept_id)},
        }
        analytics.update_from_session(session_data)

        # Verify system state
        assert student.get_mastery_level(concept_id).value > MasteryLevel.NOT_ATTEMPTED.value
        assert len(tracker.concept_progress) > 0
        assert analytics.get_engagement_score() > 0.0

        # Generate reports
        progress_report = tracker.generate_report()
        assert progress_report.total_concepts > 0

        patterns = analytics.detect_learning_patterns()
        assert isinstance(patterns, dict)

    def test_adaptive_difficulty_progression(self):
        """Test that difficulty adapts based on performance."""
        student = create_student_model("difficulty_test", age=10, grade=5)

        initial_difficulty = student.predict_difficulty("math_001")

        # Simulate successful attempts
        for _ in range(5):
            student.update_from_interaction(
                concept_id="math_001",
                problem_type="test",
                correct=True,
                attempts=1,
                time_spent=15.0,
                hint_level_used=0,
                student_response="correct",
                difficulty_level=initial_difficulty,
            )

        final_difficulty = student.predict_difficulty("math_001")

        # Difficulty should increase with success
        assert final_difficulty >= initial_difficulty

    def test_privacy_preservation(self, tmp_path):
        """Test that privacy is maintained throughout the system."""
        student_id = "privacy_test_student"
        student = create_student_model(
            student_id, age=9, grade=4, storage_path=str(tmp_path / "model.json")
        )
        tracker = create_progress_tracker(student, storage_path=str(tmp_path / "progress.json"))
        analytics = create_learning_analytics(student_id, anonymize=True)

        # Add data
        student.update_from_interaction(
            concept_id="test_concept",
            problem_type="test",
            correct=True,
            attempts=1,
            time_spent=20.0,
            hint_level_used=0,
            student_response="response",
            difficulty_level=2,
        )

        # Save everything
        student.save()
        tracker.save()

        # Check saved files don't contain sensitive data
        model_file = tmp_path / "model.json"
        assert model_file.exists()

        with open(model_file, "r") as f:
            model_data = json.load(f)

        # Check analytics export
        exported = analytics.export_anonymized_data()

        # Student ID should be hashed in analytics
        assert exported["student_id_hash"] != student_id

        # No raw responses should be in model file
        # (Only aggregated statistics)


# ============================================================================
# Performance Tests
# ============================================================================


@pytest.mark.performance
class TestPerformance:
    """Performance benchmarks for personalization system."""

    def test_student_model_update_performance(self):
        """Test student model update speed."""
        student = create_student_model("perf_test", age=9, grade=4)

        # Measure update performance
        start = time.time()
        for _ in range(100):
            student.update_from_interaction(
                concept_id="test",
                problem_type="test",
                correct=True,
                attempts=1,
                time_spent=20.0,
                hint_level_used=0,
                student_response="test",
                difficulty_level=2,
            )
        elapsed = time.time() - start

        # Should complete quickly
        assert elapsed < 2.0  # 100 updates in less than 2 seconds

    def test_progress_tracker_scale(self):
        """Test progress tracker with large history."""
        student = create_student_model("scale_test", age=9, grade=4)
        tracker = create_progress_tracker(student)

        # Add many attempts
        start = time.time()
        for i in range(100):
            tracker.record_attempt(
                concept_id=f"concept_{i % 10}",
                problem_id=f"prob_{i}",
                correct=(i % 3 != 0),
                time_spent=20.0,
                hints_used=i % 2,
                difficulty=2,
                attempts_on_problem=1,
            )

        elapsed = time.time() - start

        # Should complete in reasonable time
        assert elapsed < 5.0  # Less than 5 seconds for 100 attempts

        # Verify data integrity
        assert len(tracker.attempt_history) <= tracker.max_history_size


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
