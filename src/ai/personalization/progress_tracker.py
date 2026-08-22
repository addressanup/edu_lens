"""
Progress Tracker for EduLens Personalization Engine

This module implements progress tracking with spaced repetition, mastery calculation,
gap identification, and progress reporting for personalized learning.

Author: EduLens AI Team
Version: 1.0.0
"""

import json
import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .student_model import MasteryLevel, StudentModel

logger = logging.getLogger(__name__)


class AttemptOutcome(Enum):
    """Outcome of a problem attempt."""

    CORRECT_FIRST_TRY = "correct_first_try"
    CORRECT_WITH_HINTS = "correct_with_hints"
    CORRECT_AFTER_RETRY = "correct_after_retry"
    INCORRECT = "incorrect"
    SKIPPED = "skipped"


@dataclass
class ProblemAttempt:
    """Record of a single problem attempt."""

    timestamp: float
    concept_id: str
    problem_id: str
    outcome: AttemptOutcome
    time_spent: float
    hints_used: int
    difficulty: int
    correct: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "concept_id": self.concept_id,
            "problem_id": self.problem_id,
            "outcome": self.outcome.value,
            "time_spent": self.time_spent,
            "hints_used": self.hints_used,
            "difficulty": self.difficulty,
            "correct": self.correct,
        }


@dataclass
class ConceptProgress:
    """Progress tracking for a single concept."""

    concept_id: str
    first_attempt: Optional[float] = None
    last_practice: Optional[float] = None
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0

    # Spaced repetition parameters
    easiness_factor: float = 2.5  # SM-2 algorithm
    interval: int = 0  # Days until next review
    repetitions: int = 0  # Number of successful reviews
    next_review_date: Optional[float] = None

    # Mastery tracking
    mastery_score: float = 0.0  # 0-1 scale
    mastery_level: str = "NOT_ATTEMPTED"

    # Performance metrics
    average_time: float = 0.0
    best_time: Optional[float] = None
    average_difficulty: float = 0.0

    def update_spaced_repetition(self, quality: int):
        """
        Update spaced repetition schedule using SM-2 algorithm.

        Args:
            quality: Quality of recall (0-5 scale)
                0 - complete blackout
                1 - incorrect response, but correct one seemed familiar
                2 - incorrect response, correct one remembered
                3 - correct response, but required significant effort
                4 - correct response, after some hesitation
                5 - perfect response
        """
        if quality < 3:
            # Reset repetitions but keep easiness
            self.repetitions = 0
            self.interval = 1
        else:
            if self.repetitions == 0:
                self.interval = 1
            elif self.repetitions == 1:
                self.interval = 6
            else:
                self.interval = int(self.interval * self.easiness_factor)

            self.repetitions += 1

        # Update easiness factor
        self.easiness_factor = max(
            1.3, self.easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        )

        # Set next review date
        self.next_review_date = time.time() + (self.interval * 86400)  # Convert days to seconds

    def days_until_review(self) -> Optional[float]:
        """Get days until next review."""
        if self.next_review_date is None:
            return None

        seconds_until = self.next_review_date - time.time()
        return seconds_until / 86400

    def is_due_for_review(self) -> bool:
        """Check if concept is due for review."""
        if self.next_review_date is None:
            return self.total_attempts > 0  # Review if practiced but no schedule set

        return time.time() >= self.next_review_date

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "concept_id": self.concept_id,
            "first_attempt": self.first_attempt,
            "last_practice": self.last_practice,
            "total_attempts": self.total_attempts,
            "successful_attempts": self.successful_attempts,
            "failed_attempts": self.failed_attempts,
            "easiness_factor": self.easiness_factor,
            "interval": self.interval,
            "repetitions": self.repetitions,
            "next_review_date": self.next_review_date,
            "mastery_score": self.mastery_score,
            "mastery_level": self.mastery_level,
            "average_time": self.average_time,
            "best_time": self.best_time,
            "average_difficulty": self.average_difficulty,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConceptProgress":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ProgressReport:
    """Comprehensive progress report."""

    student_id: str
    report_date: float
    total_concepts: int
    mastered_concepts: int
    in_progress_concepts: int
    concepts_needing_review: int

    # Performance metrics
    overall_accuracy: float
    average_time_per_problem: float
    problems_solved_today: int
    problems_solved_this_week: int

    # Mastery breakdown
    mastery_distribution: Dict[str, int]

    # Strengths and weaknesses
    top_strengths: List[Tuple[str, float]]
    areas_for_improvement: List[Tuple[str, float]]

    # Learning velocity
    concepts_mastered_this_week: int
    concepts_mastered_this_month: int

    # Recommendations
    recommended_practice: List[str]
    recommended_review: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "student_id": self.student_id,
            "report_date": self.report_date,
            "total_concepts": self.total_concepts,
            "mastered_concepts": self.mastered_concepts,
            "in_progress_concepts": self.in_progress_concepts,
            "concepts_needing_review": self.concepts_needing_review,
            "overall_accuracy": self.overall_accuracy,
            "average_time_per_problem": self.average_time_per_problem,
            "problems_solved_today": self.problems_solved_today,
            "problems_solved_this_week": self.problems_solved_this_week,
            "mastery_distribution": self.mastery_distribution,
            "top_strengths": self.top_strengths,
            "areas_for_improvement": self.areas_for_improvement,
            "concepts_mastered_this_week": self.concepts_mastered_this_week,
            "concepts_mastered_this_month": self.concepts_mastered_this_month,
            "recommended_practice": self.recommended_practice,
            "recommended_review": self.recommended_review,
        }


class ProgressTracker:
    """
    Progress tracking system with spaced repetition support.

    Tracks problem attempts, calculates mastery, identifies gaps,
    suggests reviews, and generates progress reports.
    """

    def __init__(self, student_model: StudentModel, storage_path: Optional[str] = None):
        """
        Initialize ProgressTracker.

        Args:
            student_model: StudentModel instance
            storage_path: Optional path to persist progress data
        """
        self.student_model = student_model
        self.storage_path = storage_path

        # Progress tracking
        self.concept_progress: Dict[str, ConceptProgress] = {}
        self.attempt_history: List[ProblemAttempt] = []
        self.max_history_size = 1000  # Privacy: limit history retention

        # Statistics
        self.daily_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"attempts": 0, "correct": 0, "time_spent": 0}
        )

        logger.info(f"ProgressTracker initialized for student {student_model.student_id}")

    def record_attempt(
        self,
        concept_id: str,
        problem_id: str,
        correct: bool,
        time_spent: float,
        hints_used: int,
        difficulty: int,
        attempts_on_problem: int = 1,
    ) -> Dict[str, Any]:
        """
        Record a problem attempt and update progress.

        Args:
            concept_id: Concept identifier
            problem_id: Problem identifier
            correct: Whether answer was correct
            time_spent: Time spent in seconds
            hints_used: Number of hints used
            difficulty: Problem difficulty (1-5)
            attempts_on_problem: Number of attempts on this problem

        Returns:
            Dictionary with updated progress information
        """
        # Determine outcome
        if correct:
            if attempts_on_problem == 1 and hints_used == 0:
                outcome = AttemptOutcome.CORRECT_FIRST_TRY
            elif hints_used > 0:
                outcome = AttemptOutcome.CORRECT_WITH_HINTS
            else:
                outcome = AttemptOutcome.CORRECT_AFTER_RETRY
        else:
            outcome = AttemptOutcome.INCORRECT

        # Create attempt record
        attempt = ProblemAttempt(
            timestamp=time.time(),
            concept_id=concept_id,
            problem_id=problem_id,
            outcome=outcome,
            time_spent=time_spent,
            hints_used=hints_used,
            difficulty=difficulty,
            correct=correct,
        )

        # Add to history (maintain size limit)
        self.attempt_history.append(attempt)
        if len(self.attempt_history) > self.max_history_size:
            self.attempt_history.pop(0)

        # Update concept progress
        if concept_id not in self.concept_progress:
            self.concept_progress[concept_id] = ConceptProgress(concept_id=concept_id)

        progress = self.concept_progress[concept_id]

        # Update timestamps
        if progress.first_attempt is None:
            progress.first_attempt = time.time()
        progress.last_practice = time.time()

        # Update attempt counts
        progress.total_attempts += 1
        if correct:
            progress.successful_attempts += 1
        else:
            progress.failed_attempts += 1

        # Update average time
        alpha = 0.2  # Exponential moving average factor
        if progress.average_time == 0:
            progress.average_time = time_spent
        else:
            progress.average_time = alpha * time_spent + (1 - alpha) * progress.average_time

        # Update best time
        if correct and (progress.best_time is None or time_spent < progress.best_time):
            progress.best_time = time_spent

        # Update average difficulty
        if progress.average_difficulty == 0:
            progress.average_difficulty = difficulty
        else:
            progress.average_difficulty = (
                alpha * difficulty + (1 - alpha) * progress.average_difficulty
            )

        # Update spaced repetition schedule
        quality = self._calculate_recall_quality(outcome, hints_used, attempts_on_problem)
        progress.update_spaced_repetition(quality)

        # Update mastery score
        progress.mastery_score = self.calculate_mastery(concept_id)
        progress.mastery_level = self.student_model.get_mastery_level(concept_id).name

        # Update daily stats
        today = datetime.now().strftime("%Y-%m-%d")
        self.daily_stats[today]["attempts"] += 1
        if correct:
            self.daily_stats[today]["correct"] += 1
        self.daily_stats[today]["time_spent"] += int(time_spent)

        logger.debug(
            f"Recorded attempt for {concept_id}: {outcome.value}, "
            f"mastery={progress.mastery_score:.2f}"
        )

        return {
            "mastery_score": progress.mastery_score,
            "mastery_level": progress.mastery_level,
            "next_review_days": progress.days_until_review(),
            "total_attempts": progress.total_attempts,
            "success_rate": progress.successful_attempts / max(progress.total_attempts, 1),
        }

    def calculate_mastery(self, concept_id: str) -> float:
        """
        Calculate mastery score for a concept.

        Args:
            concept_id: Concept identifier

        Returns:
            Mastery score (0-1 scale)
        """
        if concept_id not in self.concept_progress:
            return 0.0

        progress = self.concept_progress[concept_id]

        if progress.total_attempts == 0:
            return 0.0

        # Components of mastery score
        # 1. Success rate (40%)
        success_rate = progress.successful_attempts / progress.total_attempts
        success_component = success_rate * 0.4

        # 2. Recent performance (30%)
        recent_attempts = [a for a in self.attempt_history[-20:] if a.concept_id == concept_id]
        if recent_attempts:
            recent_success = sum(1 for a in recent_attempts if a.correct) / len(recent_attempts)
            recent_component = recent_success * 0.3
        else:
            recent_component = success_component  # Use overall rate

        # 3. Consistency (20%) - based on spaced repetition success
        consistency = min(1.0, progress.repetitions / 5.0)
        consistency_component = consistency * 0.2

        # 4. Difficulty level (10%) - higher difficulty means more mastery
        difficulty_normalized = min(1.0, progress.average_difficulty / 5.0)
        difficulty_component = difficulty_normalized * 0.1

        mastery_score = (
            success_component + recent_component + consistency_component + difficulty_component
        )

        return min(1.0, mastery_score)

    def identify_gaps(self, subject: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Identify knowledge gaps that need attention.

        Args:
            subject: Optional subject filter

        Returns:
            List of gap dictionaries with concept and severity
        """
        gaps = []

        for concept_id, progress in self.concept_progress.items():
            # Skip if not attempted enough
            if progress.total_attempts < 3:
                continue

            # Calculate gap severity
            success_rate = progress.successful_attempts / progress.total_attempts
            mastery_score = progress.mastery_score

            # Identify as gap if:
            # 1. Low success rate (< 60%)
            # 2. Low mastery score (< 0.5)
            # 3. Has been attempted but not improving

            if success_rate < 0.6 or mastery_score < 0.5:
                severity = 1.0 - min(success_rate, mastery_score)

                gaps.append(
                    {
                        "concept_id": concept_id,
                        "severity": severity,
                        "success_rate": success_rate,
                        "mastery_score": mastery_score,
                        "attempts": progress.total_attempts,
                        "last_practice": progress.last_practice,
                        "recommendation": self._generate_gap_recommendation(progress),
                    }
                )

        # Sort by severity (descending)
        gaps.sort(key=lambda x: x["severity"], reverse=True)

        logger.info(f"Identified {len(gaps)} knowledge gaps")

        return gaps

    def suggest_review(self, max_suggestions: int = 5) -> List[Dict[str, Any]]:
        """
        Suggest concepts for review based on spaced repetition.

        Args:
            max_suggestions: Maximum number of suggestions

        Returns:
            List of review suggestion dictionaries
        """
        suggestions = []

        for concept_id, progress in self.concept_progress.items():
            # Only suggest if practiced before
            if progress.total_attempts == 0:
                continue

            # Check if due for review
            if progress.is_due_for_review():
                days_overdue = -progress.days_until_review() if progress.days_until_review() else 0

                suggestions.append(
                    {
                        "concept_id": concept_id,
                        "priority": max(1, days_overdue),  # Higher priority if overdue
                        "last_practice": progress.last_practice,
                        "mastery_score": progress.mastery_score,
                        "interval": progress.interval,
                        "repetitions": progress.repetitions,
                    }
                )

        # Sort by priority (descending)
        suggestions.sort(key=lambda x: x["priority"], reverse=True)

        logger.info(f"Generated {len(suggestions)} review suggestions")

        return suggestions[:max_suggestions]

    def generate_report(self) -> ProgressReport:
        """
        Generate comprehensive progress report.

        Returns:
            ProgressReport instance
        """
        now = time.time()
        today = datetime.now().strftime("%Y-%m-%d")

        # Count concepts by mastery
        mastery_counts = defaultdict(int)
        for concept_id, progress in self.concept_progress.items():
            if progress.total_attempts > 0:
                mastery_level = self.student_model.get_mastery_level(concept_id)
                mastery_counts[mastery_level.name] += 1

        # Calculate mastered concepts
        mastered = sum(
            1
            for p in self.concept_progress.values()
            if p.mastery_score >= 0.8 and p.total_attempts > 0
        )

        # Calculate in-progress concepts
        in_progress = sum(
            1
            for p in self.concept_progress.values()
            if 0 < p.mastery_score < 0.8 and p.total_attempts > 0
        )

        # Calculate concepts needing review
        needing_review = sum(1 for p in self.concept_progress.values() if p.is_due_for_review())

        # Overall accuracy
        total_attempts = sum(p.total_attempts for p in self.concept_progress.values())
        total_correct = sum(p.successful_attempts for p in self.concept_progress.values())
        overall_accuracy = total_correct / max(total_attempts, 1)

        # Average time
        all_times = [a.time_spent for a in self.attempt_history]
        avg_time = sum(all_times) / max(len(all_times), 1)

        # Daily/weekly stats
        problems_today = self.daily_stats[today]["attempts"]
        problems_week = self._count_problems_last_n_days(7)

        # Strengths and weaknesses
        top_strengths = self.student_model.get_strengths(5)
        weaknesses = self.student_model.get_weaknesses(5)

        # Learning velocity
        mastered_week = self._count_newly_mastered(7)
        mastered_month = self._count_newly_mastered(30)

        # Recommendations
        recommended_practice = self._generate_practice_recommendations(3)
        recommended_review = [s["concept_id"] for s in self.suggest_review(3)]

        report = ProgressReport(
            student_id=self.student_model.student_id,
            report_date=now,
            total_concepts=len([p for p in self.concept_progress.values() if p.total_attempts > 0]),
            mastered_concepts=mastered,
            in_progress_concepts=in_progress,
            concepts_needing_review=needing_review,
            overall_accuracy=overall_accuracy,
            average_time_per_problem=avg_time,
            problems_solved_today=problems_today,
            problems_solved_this_week=problems_week,
            mastery_distribution=dict(mastery_counts),
            top_strengths=top_strengths,
            areas_for_improvement=weaknesses,
            concepts_mastered_this_week=mastered_week,
            concepts_mastered_this_month=mastered_month,
            recommended_practice=recommended_practice,
            recommended_review=recommended_review,
        )

        logger.info(f"Generated progress report: {mastered} mastered, {in_progress} in progress")

        return report

    def save(self, path: Optional[str] = None) -> bool:
        """
        Save progress data to disk.

        Args:
            path: Optional path (uses self.storage_path if None)

        Returns:
            True if successful
        """
        save_path = path or self.storage_path
        if not save_path:
            logger.warning("No storage path provided")
            return False

        try:
            save_data = {
                "student_id": self.student_model.student_id,
                "concept_progress": {
                    cid: progress.to_dict() for cid, progress in self.concept_progress.items()
                },
                "daily_stats": dict(self.daily_stats),
                "last_updated": time.time(),
            }

            path_obj = Path(save_path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)

            with open(path_obj, "w") as f:
                json.dump(save_data, f, indent=2)

            logger.info(f"Saved progress data to {save_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save progress data: {e}")
            return False

    @classmethod
    def load(cls, student_model: StudentModel, path: str) -> Optional["ProgressTracker"]:
        """
        Load progress data from disk.

        Args:
            student_model: StudentModel instance
            path: Path to load from

        Returns:
            ProgressTracker instance or None if failed
        """
        try:
            with open(path, "r") as f:
                data = json.load(f)

            tracker = cls(student_model, storage_path=path)

            # Restore concept progress
            for cid, progress_data in data.get("concept_progress", {}).items():
                tracker.concept_progress[cid] = ConceptProgress.from_dict(progress_data)

            # Restore daily stats
            tracker.daily_stats = defaultdict(
                lambda: {"attempts": 0, "correct": 0, "time_spent": 0}, data.get("daily_stats", {})
            )

            logger.info(f"Loaded progress data from {path}")
            return tracker

        except Exception as e:
            logger.error(f"Failed to load progress data: {e}")
            return None

    # Private helper methods

    def _calculate_recall_quality(
        self, outcome: AttemptOutcome, hints_used: int, attempts: int
    ) -> int:
        """Calculate recall quality (0-5) for spaced repetition."""
        if outcome == AttemptOutcome.CORRECT_FIRST_TRY and hints_used == 0:
            return 5  # Perfect
        elif outcome == AttemptOutcome.CORRECT_FIRST_TRY and hints_used == 1:
            return 4  # Good with minimal help
        elif outcome == AttemptOutcome.CORRECT_WITH_HINTS:
            return 3  # Required effort and hints
        elif outcome == AttemptOutcome.CORRECT_AFTER_RETRY:
            return 2  # Eventually got it
        elif outcome == AttemptOutcome.INCORRECT:
            return 1  # Failed but tried
        else:
            return 0  # Skipped or no attempt

    def _generate_gap_recommendation(self, progress: ConceptProgress) -> str:
        """Generate recommendation for addressing a gap."""
        if progress.total_attempts < 5:
            return "Practice more problems to build familiarity"
        elif progress.average_time > 60:
            return "Focus on understanding the underlying concept"
        else:
            return "Review prerequisites and try different problem types"

    def _count_problems_last_n_days(self, days: int) -> int:
        """Count problems solved in last N days."""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        count = 0

        for date, stats in self.daily_stats.items():
            if date >= cutoff:
                count += stats["attempts"]

        return count

    def _count_newly_mastered(self, days: int) -> int:
        """Count concepts newly mastered in last N days."""
        cutoff_time = time.time() - (days * 86400)
        count = 0

        for progress in self.concept_progress.values():
            if (
                progress.mastery_score >= 0.8
                and progress.last_practice
                and progress.last_practice >= cutoff_time
            ):
                count += 1

        return count

    def _generate_practice_recommendations(self, count: int) -> List[str]:
        """Generate practice recommendations."""
        recommendations = []

        # Get concepts that need practice
        for concept_id, progress in self.concept_progress.items():
            if 0.3 < progress.mastery_score < 0.7 and progress.total_attempts >= 2:
                recommendations.append(concept_id)

        return recommendations[:count]


def create_progress_tracker(
    student_model: StudentModel, storage_path: Optional[str] = None
) -> ProgressTracker:
    """
    Create a ProgressTracker instance.

    Args:
        student_model: StudentModel instance
        storage_path: Optional storage path

    Returns:
        ProgressTracker instance
    """
    return ProgressTracker(student_model, storage_path)


# Example usage
if __name__ == "__main__":
    from .student_model import create_student_model

    print("=== EduLens Progress Tracker ===\n")

    # Create student model and tracker
    student = create_student_model("anon_123", age=9, grade=4)
    tracker = create_progress_tracker(student)

    print("--- Recording Attempts ---")

    # Simulate several attempts
    concepts = ["math_3_oa_001", "math_4_nbt_001", "math_3_oa_001"]
    for i, concept in enumerate(concepts):
        result = tracker.record_attempt(
            concept_id=concept,
            problem_id=f"prob_{i}",
            correct=(i % 2 == 0),
            time_spent=30.0 + i * 10,
            hints_used=i % 2,
            difficulty=2 + (i % 3),
            attempts_on_problem=1,
        )
        print(f"Attempt {i+1}: {concept} - Mastery: {result['mastery_score']:.2f}")

    print("\n--- Mastery Calculation ---")
    mastery = tracker.calculate_mastery("math_3_oa_001")
    print(f"Mastery for math_3_oa_001: {mastery:.2%}")

    print("\n--- Gap Identification ---")
    gaps = tracker.identify_gaps()
    if gaps:
        print(f"Found {len(gaps)} knowledge gaps:")
        for gap in gaps[:3]:
            print(f"  - {gap['concept_id']}: severity {gap['severity']:.2f}")
    else:
        print("No significant gaps identified")

    print("\n--- Review Suggestions ---")
    reviews = tracker.suggest_review(3)
    if reviews:
        print(f"Concepts needing review:")
        for review in reviews:
            print(f"  - {review['concept_id']} (priority: {review['priority']:.1f})")
    else:
        print("No reviews needed yet")

    print("\n--- Progress Report ---")
    report = tracker.generate_report()
    print(f"Total concepts: {report.total_concepts}")
    print(f"Mastered: {report.mastered_concepts}")
    print(f"In progress: {report.in_progress_concepts}")
    print(f"Overall accuracy: {report.overall_accuracy:.1%}")
    print(f"Problems solved today: {report.problems_solved_today}")

    print("\n=== Progress Tracker Ready ===")
