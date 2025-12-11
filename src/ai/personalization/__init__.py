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

from .student_model import (
    StudentModel,
    MasteryLevel,
    LearningStyle,
    LearningPace,
    ConceptKnowledgeState,
    InteractionRecord,
    create_student_model
)

from .adaptive_tutor import (
    AdaptiveTutor,
    HintDirectness,
    EmotionalState,
    ExplanationType,
    AdaptationContext,
    HintResponse,
    ExplanationResponse,
    create_adaptive_tutor
)

from .progress_tracker import (
    ProgressTracker,
    AttemptOutcome,
    ProblemAttempt,
    ConceptProgress,
    ProgressReport,
    create_progress_tracker
)

from .learning_analytics import (
    LearningAnalytics,
    LearningPattern,
    TimeOfDay,
    AggregateStatistics,
    TrendAnalysis,
    create_learning_analytics
)


__all__ = [
    # Student Model
    'StudentModel',
    'MasteryLevel',
    'LearningStyle',
    'LearningPace',
    'ConceptKnowledgeState',
    'InteractionRecord',
    'create_student_model',

    # Adaptive Tutor
    'AdaptiveTutor',
    'HintDirectness',
    'EmotionalState',
    'ExplanationType',
    'AdaptationContext',
    'HintResponse',
    'ExplanationResponse',
    'create_adaptive_tutor',

    # Progress Tracker
    'ProgressTracker',
    'AttemptOutcome',
    'ProblemAttempt',
    'ConceptProgress',
    'ProgressReport',
    'create_progress_tracker',

    # Learning Analytics
    'LearningAnalytics',
    'LearningPattern',
    'TimeOfDay',
    'AggregateStatistics',
    'TrendAnalysis',
    'create_learning_analytics',
]

__version__ = '1.0.0'
