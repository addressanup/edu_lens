"""
EduLens Observation Module

Autonomous observation and proactive intervention for homework help.
"""

from .continuous_observer import (
    ContinuousObserver,
    Frame,
    ObservationConfig,
    ObservationEvent,
    ObservationState,
)
from .intervention_manager import InterventionManager, InterventionType
from .problem_tracker import ActivityState, ProblemStatus, ProblemTracker
from .scene_analyzer import SceneAnalyzer, SceneType, SubjectType
from .struggle_detector import StruggleDetector, StruggleIndicator, StruggleSeverity

__all__ = [
    # Core
    "ContinuousObserver",
    "ObservationState",
    "ObservationEvent",
    "ObservationConfig",
    "Frame",
    # Scene Analysis
    "SceneAnalyzer",
    "SceneType",
    "SubjectType",
    # Problem Tracking
    "ProblemTracker",
    "ActivityState",
    "ProblemStatus",
    # Struggle Detection
    "StruggleDetector",
    "StruggleIndicator",
    "StruggleSeverity",
    # Intervention
    "InterventionManager",
    "InterventionType",
]
