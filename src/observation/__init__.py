"""
EduLens Observation Module

Autonomous observation and proactive intervention for homework help.
"""

from .continuous_observer import (
    ContinuousObserver,
    ObservationState,
    ObservationEvent,
    ObservationConfig,
    Frame,
)
from .scene_analyzer import SceneAnalyzer, SceneType, SubjectType
from .problem_tracker import ProblemTracker, ActivityState, ProblemStatus
from .struggle_detector import StruggleDetector, StruggleIndicator, StruggleSeverity
from .intervention_manager import InterventionManager, InterventionType

__all__ = [
    # Core
    'ContinuousObserver',
    'ObservationState',
    'ObservationEvent',
    'ObservationConfig',
    'Frame',
    # Scene Analysis
    'SceneAnalyzer',
    'SceneType',
    'SubjectType',
    # Problem Tracking
    'ProblemTracker',
    'ActivityState',
    'ProblemStatus',
    # Struggle Detection
    'StruggleDetector',
    'StruggleIndicator',
    'StruggleSeverity',
    # Intervention
    'InterventionManager',
    'InterventionType',
]
