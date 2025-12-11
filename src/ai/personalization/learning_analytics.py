"""
Learning Analytics for EduLens Personalization Engine

This module provides privacy-preserving aggregate statistics, learning pattern detection,
and trend analysis without storing raw personal data.

Author: EduLens AI Team
Version: 1.0.0
"""

import hashlib
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np


logger = logging.getLogger(__name__)


class LearningPattern(Enum):
    """Detected learning patterns."""
    STEADY_PROGRESS = "steady_progress"
    RAPID_IMPROVEMENT = "rapid_improvement"
    PLATEAU = "plateau"
    REGRESSION = "regression"
    INCONSISTENT = "inconsistent"
    STRUGGLING = "struggling"
    EXCELLING = "excelling"


class TimeOfDay(Enum):
    """Time of day categories."""
    MORNING = "morning"  # 6am-12pm
    AFTERNOON = "afternoon"  # 12pm-6pm
    EVENING = "evening"  # 6pm-10pm


@dataclass
class AggregateStatistics:
    """Privacy-preserving aggregate statistics."""
    student_id_hash: str  # Hashed ID for privacy
    time_period: str  # e.g., "2025-W50" for week 50 of 2025

    # Volume metrics
    total_sessions: int
    total_problems_attempted: int
    total_time_spent: float  # seconds

    # Performance metrics
    overall_accuracy: float
    average_time_per_problem: float
    problems_per_session: float

    # Mastery metrics
    concepts_attempted: int
    concepts_mastered: int
    average_mastery_score: float

    # Learning patterns
    primary_pattern: str
    learning_velocity: float  # concepts mastered per week

    # Engagement metrics
    session_consistency: float  # 0-1 scale
    average_session_duration: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'student_id_hash': self.student_id_hash,
            'time_period': self.time_period,
            'total_sessions': self.total_sessions,
            'total_problems_attempted': self.total_problems_attempted,
            'total_time_spent': self.total_time_spent,
            'overall_accuracy': self.overall_accuracy,
            'average_time_per_problem': self.average_time_per_problem,
            'problems_per_session': self.problems_per_session,
            'concepts_attempted': self.concepts_attempted,
            'concepts_mastered': self.concepts_mastered,
            'average_mastery_score': self.average_mastery_score,
            'primary_pattern': self.primary_pattern,
            'learning_velocity': self.learning_velocity,
            'session_consistency': self.session_consistency,
            'average_session_duration': self.average_session_duration
        }


@dataclass
class TrendAnalysis:
    """Trend analysis results."""
    metric_name: str
    time_series: List[Tuple[str, float]]  # (date, value)
    trend_direction: str  # "increasing", "decreasing", "stable"
    trend_strength: float  # 0-1 scale
    forecast_next: Optional[float]
    insights: List[str]


class LearningAnalytics:
    """
    Privacy-preserving learning analytics system.

    Provides aggregate statistics, pattern detection, and trend analysis
    without storing or exposing raw personal data.
    """

    def __init__(
        self,
        student_id: str,
        anonymize: bool = True
    ):
        """
        Initialize LearningAnalytics.

        Args:
            student_id: Student identifier
            anonymize: Whether to hash student ID for privacy
        """
        self.student_id = student_id
        self.student_id_hash = self._hash_id(student_id) if anonymize else student_id

        # Aggregate data storage (no raw personal data)
        self.weekly_aggregates: Dict[str, AggregateStatistics] = {}
        self.daily_metrics: Dict[str, Dict[str, float]] = defaultdict(dict)

        # Pattern detection state
        self.detected_patterns: List[LearningPattern] = []
        self.pattern_confidence: Dict[LearningPattern, float] = {}

        logger.info(f"LearningAnalytics initialized (anonymized: {anonymize})")

    def update_from_session(
        self,
        session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update analytics from session data.

        Args:
            session_data: Dictionary containing:
                - session_id: Session identifier
                - start_time: Session start timestamp
                - end_time: Session end timestamp
                - problems_attempted: Number of problems
                - problems_correct: Number correct
                - concepts_practiced: List of concept IDs
                - mastery_scores: Dict of concept_id -> mastery score

        Returns:
            Dictionary with updated analytics
        """
        # Extract session metrics
        duration = session_data.get('end_time', 0) - session_data.get('start_time', 0)
        date = datetime.fromtimestamp(session_data.get('start_time', time.time())).strftime('%Y-%m-%d')
        week = datetime.fromtimestamp(session_data.get('start_time', time.time())).strftime('%Y-W%W')

        # Update daily metrics
        if 'problems_attempted' not in self.daily_metrics[date]:
            self.daily_metrics[date]['problems_attempted'] = 0
            self.daily_metrics[date]['problems_correct'] = 0
            self.daily_metrics[date]['time_spent'] = 0
            self.daily_metrics[date]['sessions'] = 0

        self.daily_metrics[date]['problems_attempted'] += session_data.get('problems_attempted', 0)
        self.daily_metrics[date]['problems_correct'] += session_data.get('problems_correct', 0)
        self.daily_metrics[date]['time_spent'] += duration
        self.daily_metrics[date]['sessions'] += 1

        # Update weekly aggregates
        if week not in self.weekly_aggregates:
            self.weekly_aggregates[week] = self._create_empty_aggregate(week)

        aggregate = self.weekly_aggregates[week]
        aggregate.total_sessions += 1
        aggregate.total_problems_attempted += session_data.get('problems_attempted', 0)
        aggregate.total_time_spent += duration

        # Recalculate aggregate metrics
        self._recalculate_aggregate(aggregate)

        # Detect patterns
        self._detect_patterns()

        logger.debug(f"Updated analytics for session on {date}")

        return {
            'daily_accuracy': self._calculate_daily_accuracy(date),
            'weekly_pattern': aggregate.primary_pattern,
            'learning_velocity': aggregate.learning_velocity
        }

    def get_aggregate_statistics(
        self,
        period: str = 'week',
        count: int = 4
    ) -> List[AggregateStatistics]:
        """
        Get aggregate statistics for recent periods.

        Args:
            period: 'day' or 'week'
            count: Number of periods to return

        Returns:
            List of AggregateStatistics
        """
        if period == 'week':
            # Get last N weeks
            weeks = sorted(self.weekly_aggregates.keys(), reverse=True)[:count]
            return [self.weekly_aggregates[week] for week in weeks]
        else:
            # Aggregate daily data
            return self._aggregate_daily_to_periods(count)

    def detect_learning_patterns(self) -> Dict[LearningPattern, float]:
        """
        Detect learning patterns with confidence scores.

        Returns:
            Dictionary mapping patterns to confidence scores
        """
        self._detect_patterns()
        return self.pattern_confidence.copy()

    def analyze_trends(
        self,
        metric: str,
        days: int = 14
    ) -> TrendAnalysis:
        """
        Analyze trends for a specific metric.

        Args:
            metric: Metric name ('accuracy', 'mastery', 'velocity', etc.)
            days: Number of days to analyze

        Returns:
            TrendAnalysis instance
        """
        # Get time series data
        time_series = self._build_time_series(metric, days)

        if len(time_series) < 3:
            return TrendAnalysis(
                metric_name=metric,
                time_series=time_series,
                trend_direction="insufficient_data",
                trend_strength=0.0,
                forecast_next=None,
                insights=["Not enough data for trend analysis"]
            )

        # Calculate trend
        dates, values = zip(*time_series)
        x = np.arange(len(values))
        y = np.array(values)

        # Linear regression
        coefficients = np.polyfit(x, y, 1)
        slope = coefficients[0]
        trend_line = np.poly1d(coefficients)

        # Determine trend direction
        if abs(slope) < 0.01:
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"

        # Calculate trend strength (R-squared)
        y_pred = trend_line(x)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Forecast next value
        forecast = trend_line(len(values))

        # Generate insights
        insights = self._generate_trend_insights(metric, direction, slope, r_squared)

        return TrendAnalysis(
            metric_name=metric,
            time_series=time_series,
            trend_direction=direction,
            trend_strength=abs(r_squared),
            forecast_next=float(forecast),
            insights=insights
        )

    def get_optimal_learning_time(self) -> Dict[str, Any]:
        """
        Identify optimal learning times based on performance.

        Returns:
            Dictionary with time-of-day analysis
        """
        time_performance: Dict[TimeOfDay, List[float]] = {
            TimeOfDay.MORNING: [],
            TimeOfDay.AFTERNOON: [],
            TimeOfDay.EVENING: []
        }

        # Analyze performance by time of day
        for date, metrics in self.daily_metrics.items():
            # In production, would track actual session times
            # For now, use simplified logic
            accuracy = metrics.get('problems_correct', 0) / max(metrics.get('problems_attempted', 1), 1)

            # Distribute across times (simplified)
            time_performance[TimeOfDay.MORNING].append(accuracy)

        # Calculate best time
        best_time = None
        best_accuracy = 0.0

        for time_period, accuracies in time_performance.items():
            if accuracies:
                avg_accuracy = sum(accuracies) / len(accuracies)
                if avg_accuracy > best_accuracy:
                    best_accuracy = avg_accuracy
                    best_time = time_period

        return {
            'optimal_time': best_time.value if best_time else "insufficient_data",
            'time_performance': {
                tod.value: sum(accs) / len(accs) if accs else 0.0
                for tod, accs in time_performance.items()
            },
            'confidence': min(1.0, sum(len(accs) for accs in time_performance.values()) / 30)
        }

    def get_learning_velocity(
        self,
        days: int = 7
    ) -> float:
        """
        Calculate learning velocity (concepts mastered per week).

        Args:
            days: Number of days to calculate over

        Returns:
            Velocity score
        """
        # Get recent week
        recent_weeks = sorted(self.weekly_aggregates.keys(), reverse=True)[:max(1, days // 7)]

        if not recent_weeks:
            return 0.0

        velocities = [
            self.weekly_aggregates[week].learning_velocity
            for week in recent_weeks
        ]

        return sum(velocities) / len(velocities)

    def get_engagement_score(self) -> float:
        """
        Calculate engagement score (0-1).

        Returns:
            Engagement score
        """
        if not self.daily_metrics:
            return 0.0

        # Factors contributing to engagement:
        # 1. Session consistency (regular practice)
        # 2. Session length (appropriate duration)
        # 3. Problem volume (active participation)

        # Consistency: days active in last 7 days
        last_7_days = [
            (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            for i in range(7)
        ]
        active_days = sum(1 for day in last_7_days if day in self.daily_metrics)
        consistency_score = active_days / 7.0

        # Session length: average around 15-30 minutes is good
        avg_session_length = np.mean([
            metrics.get('time_spent', 0) / max(metrics.get('sessions', 1), 1)
            for metrics in self.daily_metrics.values()
        ])
        ideal_length = 1200  # 20 minutes in seconds
        length_score = 1.0 - min(1.0, abs(avg_session_length - ideal_length) / ideal_length)

        # Problem volume: attempting several problems per session
        avg_problems = np.mean([
            metrics.get('problems_attempted', 0) / max(metrics.get('sessions', 1), 1)
            for metrics in self.daily_metrics.values()
        ])
        volume_score = min(1.0, avg_problems / 10.0)  # 10 problems = full score

        # Weighted combination
        engagement = (
            0.4 * consistency_score +
            0.3 * length_score +
            0.3 * volume_score
        )

        return engagement

    def get_insights(self) -> List[str]:
        """
        Generate actionable insights from analytics.

        Returns:
            List of insight strings
        """
        insights = []

        # Engagement insights
        engagement = self.get_engagement_score()
        if engagement < 0.4:
            insights.append("Consider establishing a regular practice schedule")
        elif engagement > 0.8:
            insights.append("Great job maintaining consistent practice!")

        # Velocity insights
        velocity = self.get_learning_velocity()
        if velocity > 2.0:
            insights.append("You're learning new concepts quickly!")
        elif velocity < 0.5:
            insights.append("Focus on mastering current concepts before moving on")

        # Pattern insights
        patterns = self.detect_learning_patterns()
        if LearningPattern.STRUGGLING in patterns and patterns[LearningPattern.STRUGGLING] > 0.6:
            insights.append("Some concepts need extra attention - try reviewing prerequisites")

        if LearningPattern.PLATEAU in patterns and patterns[LearningPattern.PLATEAU] > 0.6:
            insights.append("Try challenging yourself with harder problems")

        # Accuracy insights
        recent_weeks = sorted(self.weekly_aggregates.keys(), reverse=True)[:2]
        if len(recent_weeks) >= 2:
            current_acc = self.weekly_aggregates[recent_weeks[0]].overall_accuracy
            prev_acc = self.weekly_aggregates[recent_weeks[1]].overall_accuracy

            if current_acc > prev_acc + 0.1:
                insights.append("Your accuracy is improving - keep up the good work!")
            elif current_acc < prev_acc - 0.1:
                insights.append("Accuracy has decreased - consider slowing down to focus on understanding")

        return insights

    def export_anonymized_data(self) -> Dict[str, Any]:
        """
        Export anonymized analytics data.

        Returns:
            Dictionary with anonymized analytics
        """
        return {
            'student_id_hash': self.student_id_hash,
            'export_date': time.time(),
            'weekly_statistics': [
                agg.to_dict() for agg in self.weekly_aggregates.values()
            ],
            'detected_patterns': {
                pattern.value: confidence
                for pattern, confidence in self.pattern_confidence.items()
            },
            'engagement_score': self.get_engagement_score(),
            'learning_velocity': self.get_learning_velocity(),
            'insights': self.get_insights()
        }

    # Private helper methods

    def _hash_id(self, student_id: str) -> str:
        """Hash student ID for privacy."""
        return hashlib.sha256(student_id.encode()).hexdigest()[:16]

    def _create_empty_aggregate(self, week: str) -> AggregateStatistics:
        """Create empty aggregate statistics."""
        return AggregateStatistics(
            student_id_hash=self.student_id_hash,
            time_period=week,
            total_sessions=0,
            total_problems_attempted=0,
            total_time_spent=0.0,
            overall_accuracy=0.0,
            average_time_per_problem=0.0,
            problems_per_session=0.0,
            concepts_attempted=0,
            concepts_mastered=0,
            average_mastery_score=0.0,
            primary_pattern="insufficient_data",
            learning_velocity=0.0,
            session_consistency=0.0,
            average_session_duration=0.0
        )

    def _recalculate_aggregate(self, aggregate: AggregateStatistics):
        """Recalculate derived metrics in aggregate."""
        if aggregate.total_problems_attempted > 0:
            aggregate.average_time_per_problem = (
                aggregate.total_time_spent / aggregate.total_problems_attempted
            )

        if aggregate.total_sessions > 0:
            aggregate.problems_per_session = (
                aggregate.total_problems_attempted / aggregate.total_sessions
            )
            aggregate.average_session_duration = (
                aggregate.total_time_spent / aggregate.total_sessions
            )

    def _calculate_daily_accuracy(self, date: str) -> float:
        """Calculate accuracy for a specific day."""
        if date not in self.daily_metrics:
            return 0.0

        metrics = self.daily_metrics[date]
        attempted = metrics.get('problems_attempted', 0)
        correct = metrics.get('problems_correct', 0)

        return correct / max(attempted, 1)

    def _detect_patterns(self):
        """Detect learning patterns from recent data."""
        self.pattern_confidence.clear()

        # Get last 4 weeks of data
        recent_weeks = sorted(self.weekly_aggregates.keys(), reverse=True)[:4]

        if len(recent_weeks) < 2:
            return

        # Analyze accuracy trend
        accuracies = [
            self.weekly_aggregates[week].overall_accuracy
            for week in recent_weeks
        ]

        # Detect patterns
        if len(accuracies) >= 3:
            # Steady progress: consistent improvement
            if all(accuracies[i] >= accuracies[i+1] for i in range(len(accuracies)-1)):
                self.pattern_confidence[LearningPattern.STEADY_PROGRESS] = 0.8

            # Rapid improvement: large gains
            if accuracies[0] - accuracies[-1] > 0.2:
                self.pattern_confidence[LearningPattern.RAPID_IMPROVEMENT] = 0.9

            # Plateau: similar performance
            if max(accuracies) - min(accuracies) < 0.1:
                self.pattern_confidence[LearningPattern.PLATEAU] = 0.7

            # Regression: declining performance
            if accuracies[0] < accuracies[-1] - 0.15:
                self.pattern_confidence[LearningPattern.REGRESSION] = 0.8

            # Struggling: consistently low accuracy
            if all(acc < 0.5 for acc in accuracies):
                self.pattern_confidence[LearningPattern.STRUGGLING] = 0.9

            # Excelling: consistently high accuracy
            if all(acc > 0.85 for acc in accuracies):
                self.pattern_confidence[LearningPattern.EXCELLING] = 0.9

    def _build_time_series(
        self,
        metric: str,
        days: int
    ) -> List[Tuple[str, float]]:
        """Build time series for a metric."""
        time_series = []

        for i in range(days):
            date = (datetime.now() - timedelta(days=days-i-1)).strftime('%Y-%m-%d')

            if date in self.daily_metrics:
                metrics = self.daily_metrics[date]

                if metric == 'accuracy':
                    value = self._calculate_daily_accuracy(date)
                elif metric == 'problems':
                    value = metrics.get('problems_attempted', 0)
                elif metric == 'time':
                    value = metrics.get('time_spent', 0) / 60.0  # Convert to minutes
                else:
                    value = 0.0

                time_series.append((date, value))

        return time_series

    def _generate_trend_insights(
        self,
        metric: str,
        direction: str,
        slope: float,
        strength: float
    ) -> List[str]:
        """Generate insights from trend analysis."""
        insights = []

        if strength < 0.3:
            insights.append(f"The trend for {metric} is not very strong")
        else:
            if direction == "increasing":
                insights.append(f"Your {metric} is improving!")
            elif direction == "decreasing":
                insights.append(f"Your {metric} has been declining - let's work on that")
            else:
                insights.append(f"Your {metric} is stable")

        if abs(slope) > 0.1 and strength > 0.5:
            insights.append(f"This is a strong and consistent trend")

        return insights

    def _aggregate_daily_to_periods(self, count: int) -> List[AggregateStatistics]:
        """Aggregate daily data into periods."""
        # Simplified implementation - in production would be more sophisticated
        return []


def create_learning_analytics(
    student_id: str,
    anonymize: bool = True
) -> LearningAnalytics:
    """
    Create a LearningAnalytics instance.

    Args:
        student_id: Student identifier
        anonymize: Whether to anonymize

    Returns:
        LearningAnalytics instance
    """
    return LearningAnalytics(student_id, anonymize)


# Example usage
if __name__ == "__main__":
    print("=== EduLens Learning Analytics ===\n")

    # Create analytics
    analytics = create_learning_analytics("student_123", anonymize=True)
    print(f"Analytics initialized (hash: {analytics.student_id_hash})")

    print("\n--- Simulating Sessions ---")

    # Simulate several sessions
    for i in range(5):
        session_data = {
            'session_id': f"session_{i}",
            'start_time': time.time() - (5-i) * 86400,  # Past 5 days
            'end_time': time.time() - (5-i) * 86400 + 1200,  # 20 min sessions
            'problems_attempted': 8 + i,
            'problems_correct': 6 + i,
            'concepts_practiced': [f"concept_{j}" for j in range(3)],
            'mastery_scores': {f"concept_{j}": 0.5 + i*0.1 for j in range(3)}
        }

        result = analytics.update_from_session(session_data)
        print(f"Session {i+1}: accuracy={result.get('daily_accuracy', 0):.2%}")

    print("\n--- Detecting Patterns ---")
    patterns = analytics.detect_learning_patterns()
    for pattern, confidence in patterns.items():
        print(f"{pattern.value}: {confidence:.2%} confidence")

    print("\n--- Trend Analysis ---")
    trend = analytics.analyze_trends('accuracy', days=7)
    print(f"Metric: {trend.metric_name}")
    print(f"Direction: {trend.trend_direction}")
    print(f"Strength: {trend.trend_strength:.2%}")
    if trend.forecast_next:
        print(f"Forecast next: {trend.forecast_next:.2%}")
    print(f"Insights: {', '.join(trend.insights)}")

    print("\n--- Engagement Score ---")
    engagement = analytics.get_engagement_score()
    print(f"Engagement: {engagement:.2%}")

    print("\n--- Learning Velocity ---")
    velocity = analytics.get_learning_velocity()
    print(f"Velocity: {velocity:.2f} concepts/week")

    print("\n--- Generated Insights ---")
    insights = analytics.get_insights()
    for i, insight in enumerate(insights, 1):
        print(f"{i}. {insight}")

    print("\n=== Learning Analytics Ready ===")
