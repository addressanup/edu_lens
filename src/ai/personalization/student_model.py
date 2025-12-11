"""
Student Model for EduLens Personalization Engine

This module implements privacy-preserving student modeling using Bayesian knowledge tracing
to track learning progress, estimate mastery levels, and adapt to individual learning patterns.

Author: EduLens AI Team
Version: 1.0.0
"""

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


logger = logging.getLogger(__name__)


class MasteryLevel(Enum):
    """Mastery levels for concept understanding."""
    NOT_ATTEMPTED = 0
    BEGINNER = 1
    DEVELOPING = 2
    PROFICIENT = 3
    MASTERED = 4
    EXPERT = 5


class LearningStyle(Enum):
    """Learning style preferences."""
    VISUAL = "visual"
    VERBAL = "verbal"
    ANALYTICAL = "analytical"
    PRACTICAL = "practical"
    EXPLORATORY = "exploratory"


class LearningPace(Enum):
    """Optimal learning pace indicators."""
    VERY_SLOW = 1
    SLOW = 2
    MODERATE = 3
    FAST = 4
    VERY_FAST = 5


@dataclass
class InteractionRecord:
    """Record of a single tutoring interaction."""
    timestamp: float
    concept_id: str
    problem_type: str
    correct: bool
    attempts: int
    time_spent: float  # seconds
    hint_level_used: int
    student_response: str
    difficulty_level: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp,
            'concept_id': self.concept_id,
            'problem_type': self.problem_type,
            'correct': self.correct,
            'attempts': self.attempts,
            'time_spent': self.time_spent,
            'hint_level_used': self.hint_level_used,
            'student_response': self.student_response,
            'difficulty_level': self.difficulty_level
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InteractionRecord':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ConceptKnowledgeState:
    """Bayesian knowledge state for a single concept."""
    concept_id: str
    probability_known: float = 0.0  # P(L) - probability student has learned
    probability_slip: float = 0.15  # P(S) - probability of making a mistake when known
    probability_guess: float = 0.25  # P(G) - probability of guessing correctly
    probability_transit: float = 0.10  # P(T) - probability of learning from one opportunity

    attempts: int = 0
    correct_count: int = 0
    incorrect_count: int = 0

    last_interaction: Optional[float] = None
    total_time_spent: float = 0.0

    def update_from_observation(self, correct: bool):
        """
        Update knowledge state using Bayesian Knowledge Tracing.

        Args:
            correct: Whether the student answered correctly
        """
        # Bayesian update based on observation
        if correct:
            # P(L|correct) using Bayes' rule
            p_correct_given_known = 1 - self.probability_slip
            p_correct_given_unknown = self.probability_guess

            numerator = p_correct_given_known * self.probability_known
            denominator = (
                p_correct_given_known * self.probability_known +
                p_correct_given_unknown * (1 - self.probability_known)
            )

            self.probability_known = numerator / denominator if denominator > 0 else self.probability_known
            self.correct_count += 1
        else:
            # P(L|incorrect) using Bayes' rule
            p_incorrect_given_known = self.probability_slip
            p_incorrect_given_unknown = 1 - self.probability_guess

            numerator = p_incorrect_given_known * self.probability_known
            denominator = (
                p_incorrect_given_known * self.probability_known +
                p_incorrect_given_unknown * (1 - self.probability_known)
            )

            self.probability_known = numerator / denominator if denominator > 0 else self.probability_known
            self.incorrect_count += 1

        # Apply learning (transition)
        # P(L_t+1) = P(L_t) + (1 - P(L_t)) * P(T)
        self.probability_known = self.probability_known + (1 - self.probability_known) * self.probability_transit

        # Ensure probability stays in [0, 1]
        self.probability_known = max(0.0, min(1.0, self.probability_known))

        self.attempts += 1
        self.last_interaction = time.time()

    def get_mastery_level(self) -> MasteryLevel:
        """
        Get discrete mastery level based on probability.

        Returns:
            MasteryLevel enum value
        """
        if self.attempts == 0:
            return MasteryLevel.NOT_ATTEMPTED
        elif self.probability_known < 0.2:
            return MasteryLevel.BEGINNER
        elif self.probability_known < 0.4:
            return MasteryLevel.DEVELOPING
        elif self.probability_known < 0.6:
            return MasteryLevel.PROFICIENT
        elif self.probability_known < 0.8:
            return MasteryLevel.MASTERED
        else:
            return MasteryLevel.EXPERT

    def days_since_last_interaction(self) -> Optional[float]:
        """Get days since last interaction."""
        if self.last_interaction is None:
            return None
        return (time.time() - self.last_interaction) / 86400  # seconds to days

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'concept_id': self.concept_id,
            'probability_known': self.probability_known,
            'probability_slip': self.probability_slip,
            'probability_guess': self.probability_guess,
            'probability_transit': self.probability_transit,
            'attempts': self.attempts,
            'correct_count': self.correct_count,
            'incorrect_count': self.incorrect_count,
            'last_interaction': self.last_interaction,
            'total_time_spent': self.total_time_spent
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConceptKnowledgeState':
        """Create from dictionary."""
        return cls(**data)


class StudentModel:
    """
    Privacy-preserving student model for personalized learning.

    Tracks learning progress, estimates mastery levels, identifies learning styles,
    and predicts optimal difficulty without storing raw personal data.
    """

    def __init__(
        self,
        student_id: str,
        age: int,
        grade: int,
        storage_path: Optional[str] = None
    ):
        """
        Initialize StudentModel.

        Args:
            student_id: Anonymous student identifier (hashed)
            age: Student age (6-12)
            grade: Grade level (K-6)
            storage_path: Optional path to persist model (privacy-preserving)
        """
        self.student_id = student_id
        self.age = age
        self.grade = grade
        self.storage_path = storage_path

        # Knowledge states per concept (Bayesian tracking)
        self.concept_states: Dict[str, ConceptKnowledgeState] = {}

        # Interaction history (limited retention for privacy)
        self.recent_interactions: List[InteractionRecord] = []
        self.max_history_size = 100  # Only keep recent interactions

        # Learning style indicators (aggregated statistics)
        self.learning_style_scores: Dict[LearningStyle, float] = {
            style: 0.5 for style in LearningStyle
        }

        # Performance metrics (aggregated)
        self.session_count = 0
        self.total_problems_attempted = 0
        self.total_time_spent = 0.0

        # Pace tracking
        self.average_time_per_problem: Dict[str, float] = {}  # By problem type
        self.pace_score = 3.0  # 1-5 scale, default moderate

        # Difficulty adaptation
        self.optimal_difficulty_by_concept: Dict[str, int] = {}  # 1-5 scale

        logger.info(f"StudentModel initialized for student {student_id}, age {age}, grade {grade}")

    def update_from_interaction(
        self,
        concept_id: str,
        problem_type: str,
        correct: bool,
        attempts: int,
        time_spent: float,
        hint_level_used: int,
        student_response: str,
        difficulty_level: int
    ) -> Dict[str, Any]:
        """
        Learn from a tutoring interaction.

        Args:
            concept_id: Concept being practiced
            problem_type: Type of problem
            correct: Whether answer was correct
            attempts: Number of attempts
            time_spent: Time spent in seconds
            hint_level_used: Level of hints used (0-3)
            student_response: Student's response (for style analysis)
            difficulty_level: Difficulty of problem (1-5)

        Returns:
            Dictionary with updated state information
        """
        # Create interaction record
        interaction = InteractionRecord(
            timestamp=time.time(),
            concept_id=concept_id,
            problem_type=problem_type,
            correct=correct,
            attempts=attempts,
            time_spent=time_spent,
            hint_level_used=hint_level_used,
            student_response=student_response,
            difficulty_level=difficulty_level
        )

        # Add to recent history (maintain size limit for privacy)
        self.recent_interactions.append(interaction)
        if len(self.recent_interactions) > self.max_history_size:
            self.recent_interactions.pop(0)

        # Update concept knowledge state
        if concept_id not in self.concept_states:
            self.concept_states[concept_id] = ConceptKnowledgeState(concept_id=concept_id)

        self.concept_states[concept_id].update_from_observation(correct)
        self.concept_states[concept_id].total_time_spent += time_spent

        # Update global statistics
        self.total_problems_attempted += 1
        self.total_time_spent += time_spent

        # Update learning style indicators
        self._update_learning_style(interaction)

        # Update pace estimation
        self._update_pace_estimation(problem_type, time_spent)

        # Update optimal difficulty
        self._update_optimal_difficulty(concept_id, difficulty_level, correct)

        logger.debug(f"Updated model for concept {concept_id}: mastery={self.get_mastery_level(concept_id)}")

        return {
            'mastery_level': self.get_mastery_level(concept_id).name,
            'probability_known': self.concept_states[concept_id].probability_known,
            'learning_style': self.get_learning_style().name,
            'optimal_difficulty': self.predict_difficulty(concept_id)
        }

    def get_mastery_level(self, concept_id: str) -> MasteryLevel:
        """
        Get current mastery level for a concept.

        Args:
            concept_id: Concept identifier

        Returns:
            MasteryLevel enum value
        """
        if concept_id not in self.concept_states:
            return MasteryLevel.NOT_ATTEMPTED

        return self.concept_states[concept_id].get_mastery_level()

    def get_learning_style(self) -> LearningStyle:
        """
        Get preferred learning style based on interaction patterns.

        Returns:
            LearningStyle enum value
        """
        # Return style with highest score
        return max(self.learning_style_scores.items(), key=lambda x: x[1])[0]

    def get_learning_style_distribution(self) -> Dict[str, float]:
        """
        Get distribution of learning style preferences.

        Returns:
            Dictionary mapping style names to scores
        """
        return {style.name: score for style, score in self.learning_style_scores.items()}

    def get_pace(self) -> LearningPace:
        """
        Get optimal learning pace.

        Returns:
            LearningPace enum value
        """
        pace_value = int(round(self.pace_score))
        pace_value = max(1, min(5, pace_value))
        return LearningPace(pace_value)

    def predict_difficulty(self, concept_id: str) -> int:
        """
        Predict appropriate difficulty level for a concept.

        Args:
            concept_id: Concept identifier

        Returns:
            Difficulty level (1-5)
        """
        # If we have history for this concept, use it
        if concept_id in self.optimal_difficulty_by_concept:
            return self.optimal_difficulty_by_concept[concept_id]

        # Otherwise, use mastery level to predict
        mastery = self.get_mastery_level(concept_id)

        if mastery == MasteryLevel.NOT_ATTEMPTED:
            return 2  # Start slightly easy
        elif mastery == MasteryLevel.BEGINNER:
            return 1
        elif mastery == MasteryLevel.DEVELOPING:
            return 2
        elif mastery == MasteryLevel.PROFICIENT:
            return 3
        elif mastery == MasteryLevel.MASTERED:
            return 4
        else:  # EXPERT
            return 5

    def get_strengths(self, top_n: int = 5) -> List[Tuple[str, float]]:
        """
        Identify student's strongest concepts.

        Args:
            top_n: Number of top concepts to return

        Returns:
            List of (concept_id, mastery_probability) tuples
        """
        concept_scores = [
            (cid, state.probability_known)
            for cid, state in self.concept_states.items()
            if state.attempts > 0
        ]

        # Sort by probability (descending)
        concept_scores.sort(key=lambda x: x[1], reverse=True)

        return concept_scores[:top_n]

    def get_weaknesses(self, top_n: int = 5) -> List[Tuple[str, float]]:
        """
        Identify student's weakest concepts that need work.

        Args:
            top_n: Number of concepts to return

        Returns:
            List of (concept_id, mastery_probability) tuples
        """
        concept_scores = [
            (cid, state.probability_known)
            for cid, state in self.concept_states.items()
            if state.attempts > 0
        ]

        # Sort by probability (ascending)
        concept_scores.sort(key=lambda x: x[1])

        return concept_scores[:top_n]

    def get_concepts_for_review(self, days_threshold: int = 3) -> List[str]:
        """
        Get concepts that should be reviewed based on spaced repetition.

        Args:
            days_threshold: Days since last practice to trigger review

        Returns:
            List of concept IDs needing review
        """
        concepts_to_review = []

        for concept_id, state in self.concept_states.items():
            days_since = state.days_since_last_interaction()

            # Skip if never attempted
            if days_since is None:
                continue

            # Review if:
            # 1. Enough time has passed AND
            # 2. Not yet mastered (< 80% probability)
            if days_since >= days_threshold and state.probability_known < 0.8:
                concepts_to_review.append(concept_id)

        return concepts_to_review

    def get_summary(self) -> Dict[str, Any]:
        """
        Get privacy-preserving summary of student model.

        Returns:
            Dictionary with aggregated statistics (no raw data)
        """
        mastery_counts = defaultdict(int)
        for state in self.concept_states.values():
            if state.attempts > 0:
                mastery_counts[state.get_mastery_level().name] += 1

        return {
            'student_id': self.student_id,
            'age': self.age,
            'grade': self.grade,
            'session_count': self.session_count,
            'total_problems_attempted': self.total_problems_attempted,
            'concepts_attempted': len([s for s in self.concept_states.values() if s.attempts > 0]),
            'mastery_distribution': dict(mastery_counts),
            'learning_style': self.get_learning_style().name,
            'pace': self.get_pace().name,
            'average_time_per_problem': sum(self.average_time_per_problem.values()) / max(len(self.average_time_per_problem), 1)
        }

    def save(self, path: Optional[str] = None) -> bool:
        """
        Save student model to disk (privacy-preserving format).

        Args:
            path: Optional path to save to (uses self.storage_path if None)

        Returns:
            True if successful
        """
        save_path = path or self.storage_path
        if not save_path:
            logger.warning("No storage path provided, cannot save model")
            return False

        try:
            save_data = {
                'student_id': self.student_id,
                'age': self.age,
                'grade': self.grade,
                'concept_states': {
                    cid: state.to_dict() for cid, state in self.concept_states.items()
                },
                'learning_style_scores': {
                    style.name: score for style, score in self.learning_style_scores.items()
                },
                'session_count': self.session_count,
                'total_problems_attempted': self.total_problems_attempted,
                'total_time_spent': self.total_time_spent,
                'pace_score': self.pace_score,
                'optimal_difficulty_by_concept': self.optimal_difficulty_by_concept,
                'average_time_per_problem': self.average_time_per_problem,
                'last_updated': time.time()
            }

            path_obj = Path(save_path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)

            with open(path_obj, 'w') as f:
                json.dump(save_data, f, indent=2)

            logger.info(f"Saved student model to {save_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save student model: {e}")
            return False

    @classmethod
    def load(cls, path: str) -> Optional['StudentModel']:
        """
        Load student model from disk.

        Args:
            path: Path to load from

        Returns:
            StudentModel instance or None if failed
        """
        try:
            with open(path, 'r') as f:
                data = json.load(f)

            model = cls(
                student_id=data['student_id'],
                age=data['age'],
                grade=data['grade'],
                storage_path=path
            )

            # Restore concept states
            for cid, state_data in data.get('concept_states', {}).items():
                model.concept_states[cid] = ConceptKnowledgeState.from_dict(state_data)

            # Restore learning style scores
            for style_name, score in data.get('learning_style_scores', {}).items():
                try:
                    style = LearningStyle[style_name]
                    model.learning_style_scores[style] = score
                except KeyError:
                    pass

            # Restore other fields
            model.session_count = data.get('session_count', 0)
            model.total_problems_attempted = data.get('total_problems_attempted', 0)
            model.total_time_spent = data.get('total_time_spent', 0.0)
            model.pace_score = data.get('pace_score', 3.0)
            model.optimal_difficulty_by_concept = data.get('optimal_difficulty_by_concept', {})
            model.average_time_per_problem = data.get('average_time_per_problem', {})

            logger.info(f"Loaded student model from {path}")
            return model

        except Exception as e:
            logger.error(f"Failed to load student model: {e}")
            return None

    # Private helper methods

    def _update_learning_style(self, interaction: InteractionRecord):
        """Update learning style indicators based on interaction."""
        response_length = len(interaction.student_response.split())

        # Visual learners: quick responses, prefer hints
        if interaction.time_spent < 30 and interaction.hint_level_used > 0:
            self.learning_style_scores[LearningStyle.VISUAL] += 0.01

        # Verbal learners: longer explanations
        if response_length > 10:
            self.learning_style_scores[LearningStyle.VERBAL] += 0.01

        # Analytical learners: multiple attempts, less hints
        if interaction.attempts > 1 and interaction.hint_level_used == 0:
            self.learning_style_scores[LearningStyle.ANALYTICAL] += 0.01

        # Practical learners: quick correct answers
        if interaction.correct and interaction.time_spent < 20:
            self.learning_style_scores[LearningStyle.PRACTICAL] += 0.01

        # Exploratory learners: willing to use hints and try different approaches
        if interaction.hint_level_used > 1 and interaction.attempts > 1:
            self.learning_style_scores[LearningStyle.EXPLORATORY] += 0.01

        # Normalize scores to sum to 1.0
        total = sum(self.learning_style_scores.values())
        if total > 0:
            for style in self.learning_style_scores:
                self.learning_style_scores[style] /= total

    def _update_pace_estimation(self, problem_type: str, time_spent: float):
        """Update pace estimation based on problem-solving speed."""
        # Update running average for this problem type
        if problem_type not in self.average_time_per_problem:
            self.average_time_per_problem[problem_type] = time_spent
        else:
            # Exponential moving average
            alpha = 0.2
            self.average_time_per_problem[problem_type] = (
                alpha * time_spent +
                (1 - alpha) * self.average_time_per_problem[problem_type]
            )

        # Calculate overall pace score (1-5 scale)
        avg_time = sum(self.average_time_per_problem.values()) / max(len(self.average_time_per_problem), 1)

        # Adjust pace score based on average time
        # Faster = higher pace score
        if avg_time < 20:
            self.pace_score = min(5.0, self.pace_score + 0.05)
        elif avg_time > 60:
            self.pace_score = max(1.0, self.pace_score - 0.05)

    def _update_optimal_difficulty(self, concept_id: str, difficulty: int, correct: bool):
        """Update optimal difficulty level for concept."""
        if concept_id not in self.optimal_difficulty_by_concept:
            self.optimal_difficulty_by_concept[concept_id] = difficulty
            return

        current_optimal = self.optimal_difficulty_by_concept[concept_id]

        # Adjust based on performance
        if correct:
            # Student succeeded - can try slightly harder
            new_difficulty = min(5, current_optimal + 0.1)
        else:
            # Student struggled - try slightly easier
            new_difficulty = max(1, current_optimal - 0.2)

        # Exponential moving average
        alpha = 0.3
        self.optimal_difficulty_by_concept[concept_id] = (
            alpha * new_difficulty +
            (1 - alpha) * current_optimal
        )


def create_student_model(
    student_id: str,
    age: int,
    grade: int,
    storage_path: Optional[str] = None
) -> StudentModel:
    """
    Create a new StudentModel instance.

    Args:
        student_id: Anonymous student identifier
        age: Student age (6-12)
        grade: Grade level (K-6)
        storage_path: Optional path to persist model

    Returns:
        StudentModel instance
    """
    return StudentModel(student_id, age, grade, storage_path)


# Example usage
if __name__ == "__main__":
    print("=== EduLens Student Model ===\n")

    # Create a student model
    model = create_student_model(
        student_id="anon_student_123",
        age=9,
        grade=4
    )

    print(f"Created model for {model.student_id}")
    print(f"Age: {model.age}, Grade: {model.grade}\n")

    # Simulate some interactions
    print("--- Simulating Interactions ---")

    # Interaction 1: Multiplication problem
    result1 = model.update_from_interaction(
        concept_id="math_3_oa_001",
        problem_type="multiplication_basic",
        correct=False,
        attempts=2,
        time_spent=45.0,
        hint_level_used=1,
        student_response="I tried 5x3=15",
        difficulty_level=2
    )
    print(f"After interaction 1: {result1}")

    # Interaction 2: Same concept, better
    result2 = model.update_from_interaction(
        concept_id="math_3_oa_001",
        problem_type="multiplication_basic",
        correct=True,
        attempts=1,
        time_spent=20.0,
        hint_level_used=0,
        student_response="6x4=24",
        difficulty_level=2
    )
    print(f"After interaction 2: {result2}")

    # Interaction 3: More practice
    result3 = model.update_from_interaction(
        concept_id="math_3_oa_001",
        problem_type="multiplication_basic",
        correct=True,
        attempts=1,
        time_spent=15.0,
        hint_level_used=0,
        student_response="7x3=21",
        difficulty_level=3
    )
    print(f"After interaction 3: {result3}\n")

    # Get mastery level
    print("--- Mastery Assessment ---")
    mastery = model.get_mastery_level("math_3_oa_001")
    print(f"Mastery level: {mastery.name}")
    print(f"Probability known: {model.concept_states['math_3_oa_001'].probability_known:.2%}\n")

    # Get learning style
    print("--- Learning Style ---")
    style = model.get_learning_style()
    print(f"Primary learning style: {style.name}")
    print(f"Style distribution: {model.get_learning_style_distribution()}\n")

    # Get pace
    print("--- Learning Pace ---")
    pace = model.get_pace()
    print(f"Optimal pace: {pace.name}\n")

    # Get difficulty prediction
    print("--- Difficulty Prediction ---")
    difficulty = model.predict_difficulty("math_3_oa_001")
    print(f"Predicted difficulty: {difficulty}/5\n")

    # Get summary
    print("--- Student Model Summary ---")
    summary = model.get_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")

    print("\n=== Student Model Ready ===")
