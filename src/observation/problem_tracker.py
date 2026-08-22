"""
ProblemTracker - Track Child's Engagement with Problems

Tracks:
- Which problem child is currently working on
- Time spent on each problem
- Activity state (writing, erasing, idle)
- Problem completion/skipping
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class ActivityState(Enum):
    """Child's activity state."""

    ACTIVE = "active"  # Writing/working
    IDLE = "idle"  # No activity detected
    ERASING = "erasing"  # Erasing motion detected
    UNKNOWN = "unknown"


class ProblemStatus(Enum):
    """Status of a problem."""

    ACTIVE = "active"  # Currently being worked on
    COMPLETED = "completed"  # Finished correctly
    SKIPPED = "skipped"  # Moved on without completing
    ABANDONED = "abandoned"  # No longer working on it


@dataclass
class Problem:
    """A tracked homework problem."""

    id: str
    text: str
    problem_type: str  # "equation", "text", "multiple_choice"
    status: str = ProblemStatus.ACTIVE.value
    region: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h
    started_at: float = field(default_factory=time.time)
    last_activity_at: float = field(default_factory=time.time)
    total_time_seconds: float = 0.0
    activity_events: List[Dict[str, Any]] = field(default_factory=list)
    interventions: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "type": self.problem_type,
            "status": self.status,
            "region": self.region,
            "started_at": self.started_at,
            "total_time_seconds": self.total_time_seconds,
            "interventions": self.interventions,
        }


@dataclass
class TrackingResult:
    """Result of problem tracking."""

    new_problem: bool = False
    problem: Optional[Dict[str, Any]] = None
    activity: str = ActivityState.UNKNOWN.value
    motion_score: float = 0.0
    focus_changed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "new_problem": self.new_problem,
            "problem": self.problem,
            "activity": self.activity,
            "motion_score": self.motion_score,
            "focus_changed": self.focus_changed,
            "metadata": self.metadata,
        }


class ProblemTracker:
    """
    Tracks child's engagement with homework problems.

    Uses:
    - Frame differencing for activity detection
    - Motion pattern analysis for writing/erasing
    - Focus region tracking
    """

    def __init__(
        self,
        motion_threshold: float = 0.05,
        idle_threshold_seconds: float = 15.0,
        erasing_pattern_detection: bool = True,
    ):
        """
        Initialize problem tracker.

        Args:
            motion_threshold: Minimum motion to be considered activity
            idle_threshold_seconds: Time without activity = idle
            erasing_pattern_detection: Enable erasing motion detection
        """
        self.motion_threshold = motion_threshold
        self.idle_threshold_seconds = idle_threshold_seconds
        self.erasing_pattern_detection = erasing_pattern_detection

        # State
        self._current_problem: Optional[Problem] = None
        self._problem_history: List[Problem] = []
        self._last_frame: Optional[np.ndarray] = None
        self._last_activity_time: float = time.time()
        self._activity_state = ActivityState.UNKNOWN

        # Motion tracking
        self._motion_history: List[float] = []
        self._motion_window = 10  # frames

        # Focus region tracking
        self._last_focus_region: Optional[Tuple[int, int, int, int]] = None

    async def track(self, frame: Any, current_problem: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Track problem engagement from a frame.

        Args:
            frame: Frame object with .data (JPEG bytes)
            current_problem: Current problem dict (from scene analyzer)

        Returns:
            TrackingResult as dict
        """
        try:
            # Decode frame
            img = self._decode_frame(frame.data)
            if img is None:
                return TrackingResult().to_dict()

            # Detect activity via frame differencing
            motion_score = self._calculate_motion(img)
            activity = self._classify_activity(motion_score, img)

            # Update last activity time if active
            if activity in [ActivityState.ACTIVE, ActivityState.ERASING]:
                self._last_activity_time = time.time()

            # Check for new problem
            new_problem = False
            if current_problem:
                problem_id = current_problem.get("id")

                if self._current_problem is None or self._current_problem.id != problem_id:
                    # New problem detected
                    if self._current_problem:
                        # Mark old problem as skipped/completed
                        self._finalize_problem(self._current_problem)

                    # Create new problem
                    self._current_problem = Problem(
                        id=problem_id,
                        text=current_problem.get("text", ""),
                        problem_type=current_problem.get("type", "unknown"),
                        region=current_problem.get("region"),
                    )
                    new_problem = True
                    logger.info(f"Tracking new problem: {problem_id}")

            # Update current problem tracking
            if self._current_problem:
                self._current_problem.last_activity_at = time.time()
                self._current_problem.total_time_seconds = (
                    time.time() - self._current_problem.started_at
                )

                # Record activity event
                self._current_problem.activity_events.append(
                    {
                        "timestamp": time.time(),
                        "activity": activity.value,
                        "motion_score": motion_score,
                    }
                )

                # Limit event history
                if len(self._current_problem.activity_events) > 100:
                    self._current_problem.activity_events = self._current_problem.activity_events[
                        -50:
                    ]

            # Store frame for next comparison
            self._last_frame = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            self._activity_state = activity

            # Build result
            result = TrackingResult(
                new_problem=new_problem,
                problem=self._current_problem.to_dict() if self._current_problem else None,
                activity=activity.value,
                motion_score=motion_score,
                focus_changed=new_problem,
                metadata={
                    "idle_time": time.time() - self._last_activity_time,
                    "problem_count": len(self._problem_history)
                    + (1 if self._current_problem else 0),
                },
            )

            return result.to_dict()

        except Exception as e:
            logger.error(f"Problem tracking error: {e}")
            return TrackingResult(metadata={"error": str(e)}).to_dict()

    def _decode_frame(self, jpeg_data: bytes) -> Optional[np.ndarray]:
        """Decode JPEG bytes to numpy array."""
        try:
            nparr = np.frombuffer(jpeg_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            logger.error(f"Frame decode error: {e}")
            return None

    def _calculate_motion(self, img: np.ndarray) -> float:
        """
        Calculate motion score between current and previous frame.

        Returns value 0-1 indicating amount of motion.
        """
        if self._last_frame is None:
            return 0.0

        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Resize for faster processing if needed
            if gray.shape[0] > 480:
                scale = 480 / gray.shape[0]
                gray = cv2.resize(gray, None, fx=scale, fy=scale)
                last_frame = cv2.resize(self._last_frame, None, fx=scale, fy=scale)
            else:
                last_frame = self._last_frame

            # Ensure same size
            if gray.shape != last_frame.shape:
                return 0.0

            # Calculate absolute difference
            diff = cv2.absdiff(gray, last_frame)

            # Apply threshold to filter noise
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

            # Calculate motion ratio
            motion_pixels = np.sum(thresh > 0)
            total_pixels = thresh.size
            motion_score = motion_pixels / total_pixels

            # Update motion history
            self._motion_history.append(motion_score)
            if len(self._motion_history) > self._motion_window:
                self._motion_history.pop(0)

            return motion_score

        except Exception as e:
            logger.debug(f"Motion calculation error: {e}")
            return 0.0

    def _classify_activity(self, motion_score: float, img: np.ndarray) -> ActivityState:
        """
        Classify activity state based on motion and patterns.

        Args:
            motion_score: Current frame motion score
            img: Current frame image

        Returns:
            ActivityState enum value
        """
        # Check for idle (low motion over time)
        if motion_score < self.motion_threshold:
            idle_time = time.time() - self._last_activity_time
            if idle_time >= self.idle_threshold_seconds:
                return ActivityState.IDLE
            # Still might be reading/thinking
            return ActivityState.UNKNOWN

        # Detect erasing pattern if enabled
        if self.erasing_pattern_detection and motion_score > self.motion_threshold:
            is_erasing = self._detect_erasing_pattern(img)
            if is_erasing:
                return ActivityState.ERASING

        # High motion = active writing
        if motion_score > self.motion_threshold:
            return ActivityState.ACTIVE

        return ActivityState.UNKNOWN

    def _detect_erasing_pattern(self, img: np.ndarray) -> bool:
        """
        Detect if motion pattern indicates erasing.

        Erasing typically has:
        - Back-and-forth horizontal motion
        - More localized area than writing
        - Specific motion patterns
        """
        if len(self._motion_history) < 3:
            return False

        try:
            # Check for oscillating motion pattern
            # Erasing tends to have consistent back-and-forth motion
            recent_motion = self._motion_history[-5:]

            if len(recent_motion) < 3:
                return False

            # Look for repeating high-motion pattern
            high_motion_count = sum(1 for m in recent_motion if m > self.motion_threshold * 2)

            # Erasing typically has sustained high motion
            if high_motion_count >= 3:
                # Additional check: analyze motion direction if possible
                # For now, use simple heuristic
                avg_motion = sum(recent_motion) / len(recent_motion)
                variance = sum((m - avg_motion) ** 2 for m in recent_motion) / len(recent_motion)

                # Erasing has more consistent motion than writing
                if variance < 0.001 and avg_motion > self.motion_threshold * 1.5:
                    return True

            return False

        except Exception as e:
            logger.debug(f"Erasing detection error: {e}")
            return False

    def _finalize_problem(self, problem: Problem) -> None:
        """Finalize a problem when moving to next one."""
        # Determine final status
        if problem.total_time_seconds < 5:
            problem.status = ProblemStatus.SKIPPED.value
        else:
            # Could be completed or abandoned - hard to tell without answer checking
            problem.status = ProblemStatus.COMPLETED.value

        # Add to history
        self._problem_history.append(problem)

        # Limit history size
        if len(self._problem_history) > 20:
            self._problem_history.pop(0)

        logger.info(f"Problem {problem.id} finalized: {problem.status}")

    def get_current_problem(self) -> Optional[Dict[str, Any]]:
        """Get current problem being tracked."""
        if self._current_problem:
            return self._current_problem.to_dict()
        return None

    def get_problem_history(self) -> List[Dict[str, Any]]:
        """Get history of tracked problems."""
        return [p.to_dict() for p in self._problem_history]

    def get_activity_summary(self) -> Dict[str, Any]:
        """Get summary of activity tracking."""
        return {
            "current_state": self._activity_state.value,
            "idle_time": time.time() - self._last_activity_time,
            "avg_motion": sum(self._motion_history) / max(len(self._motion_history), 1),
            "problems_tracked": len(self._problem_history) + (1 if self._current_problem else 0),
        }

    def record_intervention(self) -> None:
        """Record that an intervention was triggered for current problem."""
        if self._current_problem:
            self._current_problem.interventions += 1

    def mark_problem_completed(self) -> None:
        """Mark current problem as completed."""
        if self._current_problem:
            self._current_problem.status = ProblemStatus.COMPLETED.value
            self._finalize_problem(self._current_problem)
            self._current_problem = None

    def reset(self) -> None:
        """Reset tracker state."""
        if self._current_problem:
            self._finalize_problem(self._current_problem)

        self._current_problem = None
        self._last_frame = None
        self._motion_history.clear()
        self._last_activity_time = time.time()
        self._activity_state = ActivityState.UNKNOWN
