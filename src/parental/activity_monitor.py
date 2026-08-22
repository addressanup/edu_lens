"""
Activity Monitor for EduLens Parental Controls

Privacy-respecting activity monitoring with aggregated statistics.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SessionData:
    """Represents a single learning session."""

    def __init__(
        self,
        session_id: str,
        start_time: datetime,
        end_time: datetime,
        subject: str,
        duration_minutes: int,
        problems_attempted: int,
        problems_correct: int,
        difficulty_level: str,
        topics_covered: List[str],
    ):
        self.session_id = session_id
        self.start_time = start_time
        self.end_time = end_time
        self.subject = subject
        self.duration_minutes = duration_minutes
        self.problems_attempted = problems_attempted
        self.problems_correct = problems_correct
        self.difficulty_level = difficulty_level
        self.topics_covered = topics_covered

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "subject": self.subject,
            "duration_minutes": self.duration_minutes,
            "problems_attempted": self.problems_attempted,
            "problems_correct": self.problems_correct,
            "difficulty_level": self.difficulty_level,
            "topics_covered": self.topics_covered,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SessionData":
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            subject=data["subject"],
            duration_minutes=data["duration_minutes"],
            problems_attempted=data["problems_attempted"],
            problems_correct=data["problems_correct"],
            difficulty_level=data["difficulty_level"],
            topics_covered=data["topics_covered"],
        )


class ActivityMonitor:
    """
    Privacy-respecting activity monitor for parental controls.

    Features:
    - Session logging (summary only, no raw content)
    - Daily and weekly reports
    - Subject breakdown
    - Progress metrics
    - Aggregated statistics only
    - No storage of actual problem content or answers
    """

    def __init__(self, user_id: str, storage_path: Optional[Path] = None):
        """
        Initialize ActivityMonitor.

        Args:
            user_id: Unique identifier for the user
            storage_path: Path to store activity data
        """
        self.user_id = user_id
        self.storage_path = storage_path or Path(f"/tmp/edulens/activity/{user_id}")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.sessions: List[SessionData] = []
        self._load_sessions()

    def log_session(
        self,
        session_id: str,
        start_time: datetime,
        end_time: datetime,
        subject: str,
        problems_attempted: int,
        problems_correct: int,
        difficulty_level: str,
        topics_covered: List[str],
        additional_metadata: Optional[Dict] = None,
    ) -> None:
        """
        Log a completed learning session.

        Args:
            session_id: Unique session identifier
            start_time: Session start time
            end_time: Session end time
            subject: Subject studied
            problems_attempted: Number of problems attempted
            problems_correct: Number of problems answered correctly
            difficulty_level: Difficulty level of content
            topics_covered: List of topics covered
            additional_metadata: Optional metadata (not stored, privacy)

        Note: This method stores only aggregated statistics, not actual content.
        """
        duration_minutes = int((end_time - start_time).total_seconds() / 60)

        session = SessionData(
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            subject=subject,
            duration_minutes=duration_minutes,
            problems_attempted=problems_attempted,
            problems_correct=problems_correct,
            difficulty_level=difficulty_level,
            topics_covered=topics_covered,
        )

        self.sessions.append(session)
        logger.info(
            f"Logged session {session_id} for user {self.user_id}: "
            f"{duration_minutes} min, {subject}, "
            f"{problems_correct}/{problems_attempted} correct"
        )

        self._save_sessions()

    def get_daily_report(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get aggregated daily activity report.

        Args:
            date: Date to report on (defaults to today)

        Returns:
            Dictionary with daily statistics
        """
        if date is None:
            date = datetime.now()

        # Filter sessions for the specified date
        date_str = date.strftime("%Y-%m-%d")
        daily_sessions = [s for s in self.sessions if s.start_time.strftime("%Y-%m-%d") == date_str]

        if not daily_sessions:
            return {
                "date": date_str,
                "total_sessions": 0,
                "total_duration_minutes": 0,
                "subjects": {},
                "overall_accuracy": 0.0,
                "problems_attempted": 0,
                "problems_correct": 0,
            }

        # Calculate statistics
        total_duration = sum(s.duration_minutes for s in daily_sessions)
        total_attempted = sum(s.problems_attempted for s in daily_sessions)
        total_correct = sum(s.problems_correct for s in daily_sessions)

        # Subject breakdown
        subject_stats = defaultdict(
            lambda: {"duration": 0, "attempted": 0, "correct": 0, "sessions": 0}
        )

        for session in daily_sessions:
            stats = subject_stats[session.subject]
            stats["duration"] += session.duration_minutes
            stats["attempted"] += session.problems_attempted
            stats["correct"] += session.problems_correct
            stats["sessions"] += 1

        # Calculate accuracy per subject
        for subject, stats in subject_stats.items():
            if stats["attempted"] > 0:
                stats["accuracy"] = round(stats["correct"] / stats["attempted"] * 100, 2)
            else:
                stats["accuracy"] = 0.0

        overall_accuracy = (
            round(total_correct / total_attempted * 100, 2) if total_attempted > 0 else 0.0
        )

        return {
            "date": date_str,
            "total_sessions": len(daily_sessions),
            "total_duration_minutes": total_duration,
            "subjects": dict(subject_stats),
            "overall_accuracy": overall_accuracy,
            "problems_attempted": total_attempted,
            "problems_correct": total_correct,
            "average_session_duration": round(total_duration / len(daily_sessions), 2),
        }

    def get_weekly_report(self, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get aggregated weekly activity report (last 7 days).

        Args:
            end_date: End date of the week (defaults to today)

        Returns:
            Dictionary with weekly statistics
        """
        if end_date is None:
            end_date = datetime.now()

        start_date = end_date - timedelta(days=6)

        # Filter sessions for the week
        weekly_sessions = [s for s in self.sessions if start_date <= s.start_time <= end_date]

        if not weekly_sessions:
            return {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "total_sessions": 0,
                "total_duration_minutes": 0,
                "daily_breakdown": {},
                "subjects": {},
                "overall_accuracy": 0.0,
            }

        # Daily breakdown
        daily_breakdown = {}
        current_date = start_date
        while current_date <= end_date:
            daily_report = self.get_daily_report(current_date)
            daily_breakdown[current_date.strftime("%Y-%m-%d")] = {
                "duration": daily_report["total_duration_minutes"],
                "sessions": daily_report["total_sessions"],
                "accuracy": daily_report["overall_accuracy"],
            }
            current_date += timedelta(days=1)

        # Overall statistics
        total_duration = sum(s.duration_minutes for s in weekly_sessions)
        total_attempted = sum(s.problems_attempted for s in weekly_sessions)
        total_correct = sum(s.problems_correct for s in weekly_sessions)

        # Subject breakdown
        subject_stats = defaultdict(
            lambda: {"duration": 0, "attempted": 0, "correct": 0, "sessions": 0}
        )

        for session in weekly_sessions:
            stats = subject_stats[session.subject]
            stats["duration"] += session.duration_minutes
            stats["attempted"] += session.problems_attempted
            stats["correct"] += session.problems_correct
            stats["sessions"] += 1

        for subject, stats in subject_stats.items():
            if stats["attempted"] > 0:
                stats["accuracy"] = round(stats["correct"] / stats["attempted"] * 100, 2)
            else:
                stats["accuracy"] = 0.0

        overall_accuracy = (
            round(total_correct / total_attempted * 100, 2) if total_attempted > 0 else 0.0
        )

        return {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "total_sessions": len(weekly_sessions),
            "total_duration_minutes": total_duration,
            "average_daily_duration": round(total_duration / 7, 2),
            "daily_breakdown": daily_breakdown,
            "subjects": dict(subject_stats),
            "overall_accuracy": overall_accuracy,
            "problems_attempted": total_attempted,
            "problems_correct": total_correct,
        }

    def get_subject_breakdown(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed breakdown by subject for a date range.

        Args:
            start_date: Start date (defaults to 30 days ago)
            end_date: End date (defaults to today)

        Returns:
            Dictionary mapping subjects to their statistics
        """
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        # Filter sessions
        period_sessions = [s for s in self.sessions if start_date <= s.start_time <= end_date]

        subject_breakdown = defaultdict(
            lambda: {
                "total_duration": 0,
                "session_count": 0,
                "problems_attempted": 0,
                "problems_correct": 0,
                "accuracy": 0.0,
                "topics": defaultdict(int),
                "difficulty_distribution": defaultdict(int),
                "average_session_duration": 0.0,
            }
        )

        for session in period_sessions:
            stats = subject_breakdown[session.subject]
            stats["total_duration"] += session.duration_minutes
            stats["session_count"] += 1
            stats["problems_attempted"] += session.problems_attempted
            stats["problems_correct"] += session.problems_correct
            stats["difficulty_distribution"][session.difficulty_level] += 1

            for topic in session.topics_covered:
                stats["topics"][topic] += 1

        # Calculate derived metrics
        for subject, stats in subject_breakdown.items():
            if stats["problems_attempted"] > 0:
                stats["accuracy"] = round(
                    stats["problems_correct"] / stats["problems_attempted"] * 100, 2
                )
            if stats["session_count"] > 0:
                stats["average_session_duration"] = round(
                    stats["total_duration"] / stats["session_count"], 2
                )

            # Convert defaultdicts to regular dicts
            stats["topics"] = dict(stats["topics"])
            stats["difficulty_distribution"] = dict(stats["difficulty_distribution"])

        return dict(subject_breakdown)

    def get_progress_metrics(self, subject: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """
        Get progress and learning metrics.

        Args:
            subject: Specific subject to analyze (None for all subjects)
            days: Number of days to analyze

        Returns:
            Dictionary with progress metrics
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Filter sessions
        period_sessions = [s for s in self.sessions if start_date <= s.start_time <= end_date]

        if subject:
            period_sessions = [s for s in period_sessions if s.subject == subject]

        if not period_sessions:
            return {"subject": subject or "all", "period_days": days, "no_data": True}

        # Sort by date
        period_sessions.sort(key=lambda s: s.start_time)

        # Calculate metrics
        total_duration = sum(s.duration_minutes for s in period_sessions)
        total_attempted = sum(s.problems_attempted for s in period_sessions)
        total_correct = sum(s.problems_correct for s in period_sessions)

        # Trend analysis (compare first half vs second half)
        midpoint = len(period_sessions) // 2
        first_half = period_sessions[:midpoint] if midpoint > 0 else []
        second_half = period_sessions[midpoint:] if midpoint > 0 else period_sessions

        first_half_accuracy = self._calculate_accuracy(first_half)
        second_half_accuracy = self._calculate_accuracy(second_half)

        accuracy_trend = second_half_accuracy - first_half_accuracy

        # Consistency (days with activity)
        active_days = len(set(s.start_time.strftime("%Y-%m-%d") for s in period_sessions))

        # Difficulty progression
        difficulty_order = {
            "elementary": 1,
            "middle_school": 2,
            "high_school": 3,
            "college": 4,
            "advanced": 5,
        }
        avg_difficulty_first = (
            sum(difficulty_order.get(s.difficulty_level.lower(), 0) for s in first_half)
            / len(first_half)
            if first_half
            else 0
        )
        avg_difficulty_second = (
            sum(difficulty_order.get(s.difficulty_level.lower(), 0) for s in second_half)
            / len(second_half)
            if second_half
            else 0
        )

        return {
            "subject": subject or "all",
            "period_days": days,
            "total_sessions": len(period_sessions),
            "total_duration_minutes": total_duration,
            "total_problems_attempted": total_attempted,
            "total_problems_correct": total_correct,
            "overall_accuracy": (
                round(total_correct / total_attempted * 100, 2) if total_attempted > 0 else 0.0
            ),
            "active_days": active_days,
            "consistency_percentage": round(active_days / days * 100, 2),
            "average_daily_duration": (
                round(total_duration / active_days, 2) if active_days > 0 else 0.0
            ),
            "trends": {
                "accuracy_improvement": round(accuracy_trend, 2),
                "improving": accuracy_trend > 0,
                "first_half_accuracy": round(first_half_accuracy, 2),
                "second_half_accuracy": round(second_half_accuracy, 2),
                "difficulty_progression": avg_difficulty_second - avg_difficulty_first,
            },
            "streaks": self._calculate_streaks(period_sessions),
        }

    def get_learning_insights(self, days: int = 30) -> Dict[str, Any]:
        """
        Generate learning insights and recommendations.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with insights and recommendations
        """
        progress = self.get_progress_metrics(days=days)
        subject_breakdown = self.get_subject_breakdown(
            start_date=datetime.now() - timedelta(days=days)
        )

        insights = {
            "strengths": [],
            "areas_for_improvement": [],
            "recommendations": [],
            "highlights": [],
        }

        if progress.get("no_data"):
            insights["recommendations"].append(
                "Start practicing regularly to build a learning habit"
            )
            return insights

        # Identify strengths (high accuracy subjects)
        for subject, stats in subject_breakdown.items():
            if stats["accuracy"] >= 80:
                insights["strengths"].append(
                    f"Strong performance in {subject} ({stats['accuracy']}% accuracy)"
                )

        # Identify areas for improvement (low accuracy subjects)
        for subject, stats in subject_breakdown.items():
            if stats["accuracy"] < 60 and stats["problems_attempted"] >= 10:
                insights["areas_for_improvement"].append(
                    f"{subject} needs more practice ({stats['accuracy']}% accuracy)"
                )

        # Consistency recommendations
        if progress["consistency_percentage"] < 50:
            insights["recommendations"].append(
                f"Try to practice more consistently. Active on {progress['active_days']}/{days} days"
            )
        elif progress["consistency_percentage"] >= 80:
            insights["highlights"].append(
                f"Excellent consistency! Active on {progress['active_days']}/{days} days"
            )

        # Accuracy trend
        if progress["trends"]["improving"]:
            insights["highlights"].append(
                f"Accuracy improving! Up {progress['trends']['accuracy_improvement']}% over the period"
            )
        elif progress["trends"]["accuracy_improvement"] < -5:
            insights["recommendations"].append(
                "Consider reviewing fundamentals or reducing difficulty level temporarily"
            )

        # Duration recommendations
        avg_daily = progress["average_daily_duration"]
        if avg_daily < 15:
            insights["recommendations"].append(
                "Try to increase daily practice time for better retention"
            )
        elif avg_daily > 120:
            insights["recommendations"].append(
                "Great dedication! Remember to take breaks to avoid burnout"
            )

        return insights

    def _calculate_accuracy(self, sessions: List[SessionData]) -> float:
        """Calculate average accuracy for a list of sessions."""
        if not sessions:
            return 0.0

        total_attempted = sum(s.problems_attempted for s in sessions)
        total_correct = sum(s.problems_correct for s in sessions)

        return (total_correct / total_attempted * 100) if total_attempted > 0 else 0.0

    def _calculate_streaks(self, sessions: List[SessionData]) -> Dict[str, int]:
        """Calculate activity streaks."""
        if not sessions:
            return {"current_streak": 0, "longest_streak": 0}

        # Get unique dates
        dates = sorted(set(s.start_time.date() for s in sessions))

        current_streak = 0
        longest_streak = 0
        temp_streak = 1

        for i in range(len(dates)):
            if i > 0:
                if (dates[i] - dates[i - 1]).days == 1:
                    temp_streak += 1
                else:
                    longest_streak = max(longest_streak, temp_streak)
                    temp_streak = 1

        longest_streak = max(longest_streak, temp_streak)

        # Calculate current streak (from today backwards)
        today = datetime.now().date()
        if dates and dates[-1] == today:
            current_streak = 1
            for i in range(len(dates) - 2, -1, -1):
                if (dates[i + 1] - dates[i]).days == 1:
                    current_streak += 1
                else:
                    break
        elif dates and (today - dates[-1]).days == 1:
            # If last activity was yesterday, count it
            current_streak = 1
            for i in range(len(dates) - 2, -1, -1):
                if (dates[i + 1] - dates[i]).days == 1:
                    current_streak += 1
                else:
                    break

        return {"current_streak": current_streak, "longest_streak": longest_streak}

    def _save_sessions(self) -> None:
        """Save sessions to disk."""
        sessions_file = self.storage_path / "sessions.json"

        data = {"user_id": self.user_id, "sessions": [s.to_dict() for s in self.sessions]}

        with open(sessions_file, "w") as f:
            json.dump(data, f, indent=2)

    def _load_sessions(self) -> None:
        """Load sessions from disk."""
        sessions_file = self.storage_path / "sessions.json"

        if not sessions_file.exists():
            return

        try:
            with open(sessions_file, "r") as f:
                data = json.load(f)

            self.sessions = [SessionData.from_dict(s) for s in data.get("sessions", [])]
            logger.info(f"Loaded {len(self.sessions)} sessions for user {self.user_id}")
        except Exception as e:
            logger.error(f"Error loading sessions for user {self.user_id}: {e}")

    def clear_old_sessions(self, days_to_keep: int = 90) -> int:
        """
        Clear sessions older than specified days.

        Args:
            days_to_keep: Number of days of history to retain

        Returns:
            Number of sessions removed
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        original_count = len(self.sessions)

        self.sessions = [s for s in self.sessions if s.start_time >= cutoff_date]

        removed = original_count - len(self.sessions)
        if removed > 0:
            logger.info(f"Removed {removed} old sessions for user {self.user_id}")
            self._save_sessions()

        return removed
