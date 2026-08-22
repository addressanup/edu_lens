"""
EduLens Personalization Engine

This package provides comprehensive personalization capabilities including:
- Student modeling with Bayesian knowledge tracking
- Adaptive tutoring with real-time adjustments
- Progress tracking with spaced repetition
- Privacy-preserving learning analytics

Author: EduLens AI Team
Version: 1.0.0
"""

from .adaptive_tutor import (
    AdaptationContext,
    AdaptiveTutor,
    EmotionalState,
    ExplanationResponse,
    ExplanationType,
    HintDirectness,
    HintResponse,
    create_adaptive_tutor,
)
from .learning_analytics import (
    AggregateStatistics,
    LearningAnalytics,
    LearningPattern,
    TimeOfDay,
    TrendAnalysis,
    create_learning_analytics,
)
from .progress_tracker import (
    AttemptOutcome,
    ConceptProgress,
    ProblemAttempt,
    ProgressReport,
    ProgressTracker,
    create_progress_tracker,
)
from .student_model import (
    ConceptKnowledgeState,
    InteractionRecord,
    LearningPace,
    LearningStyle,
    MasteryLevel,
    StudentModel,
    create_student_model,
)

__all__ = [
    # Student Model
    "StudentModel",
    "MasteryLevel",
    "LearningStyle",
    "LearningPace",
    "ConceptKnowledgeState",
    "InteractionRecord",
    "create_student_model",
    # Adaptive Tutor
    "AdaptiveTutor",
    "HintDirectness",
    "EmotionalState",
    "ExplanationType",
    "AdaptationContext",
    "HintResponse",
    "ExplanationResponse",
    "create_adaptive_tutor",
    # Progress Tracker
    "ProgressTracker",
    "AttemptOutcome",
    "ProblemAttempt",
    "ConceptProgress",
    "ProgressReport",
    "create_progress_tracker",
    # Learning Analytics
    "LearningAnalytics",
    "LearningPattern",
    "TimeOfDay",
    "AggregateStatistics",
    "TrendAnalysis",
    "create_learning_analytics",
]

__version__ = "1.0.0"
