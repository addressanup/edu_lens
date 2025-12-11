"""
StruggleDetector - Detect When Child Needs Help

Detects struggle using multiple indicators:
- Time-based: Too long on same problem
- Activity-based: Extended idle, repeated erasing
- Visual-based: Crossed out work, repeated attempts
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class StruggleIndicator(Enum):
    """Types of struggle indicators."""
    TIME_THRESHOLD = "time_threshold"           # >45 seconds on same problem
    NO_ACTIVITY = "no_activity"                 # >15 seconds idle
    ERASING = "erasing"                         # Detected erasing motion
    CROSSING_OUT = "crossing_out"               # Crossed out work
    REPEATED_ATTEMPTS = "repeated_attempts"     # Multiple attempts visible
    CONFUSION_DETECTED = "confusion_detected"   # Visual signs of confusion


class StruggleSeverity(Enum):
    """Severity levels of detected struggle."""
    LOW = "low"           # Might need help soon
    MEDIUM = "medium"     # Likely struggling
    HIGH = "high"         # Definitely needs help
    CRITICAL = "critical" # Frustration likely


@dataclass
class StruggleDetectionResult:
    """Result of struggle detection."""
    is_struggling: bool = False
    severity: str = StruggleSeverity.LOW.value
    reason: Optional[str] = None
    indicators: List[str] = field(default_factory=list)
    confidence: float = 0.0
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_struggling": self.is_struggling,
            "severity": self.severity,
            "reason": self.reason,
            "indicators": self.indicators,
            "confidence": self.confidence,
            "recommendations": self.recommendations,
            "metadata": self.metadata,
        }


class StruggleDetector:
    """
    Detects when a child is struggling with homework.

    Uses multiple detection methods:
    1. Time-based: Track duration on problem
    2. Activity-based: Detect idle, erasing patterns
    3. Visual-based: Detect crossed out work
    """

    def __init__(self, config: Any = None):
        """
        Initialize struggle detector.

        Args:
            config: ObservationConfig with detection thresholds
        """
        # Load config or use defaults
        if config:
            self.time_threshold = config.time_on_problem_threshold_seconds
            self.warning_threshold = config.warning_threshold_seconds
            self.idle_threshold = config.idle_threshold_seconds
            self.motion_threshold = config.motion_threshold
        else:
            self.time_threshold = 45.0
            self.warning_threshold = 30.0
            self.idle_threshold = 15.0
            self.motion_threshold = 0.05

        # Detection state
        self._last_struggle_time: Optional[float] = None
        self._indicator_history: List[Dict[str, Any]] = []
        self._erasing_count = 0
        self._crossing_detected = False

        # Visual detection cache
        self._last_analysis_time = 0
        self._visual_analysis_interval = 2.0  # seconds

    async def detect(
        self,
        frame: Any,
        indicators: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if child is struggling.

        Args:
            frame: Frame object with .data (JPEG bytes)
            indicators: Dict with time_on_problem, idle_time, activity_state, etc.

        Returns:
            StruggleDetectionResult dict if struggling, None otherwise
        """
        try:
            detected_indicators = []
            severity_scores = []

            # 1. Time-based detection
            time_result = self._check_time_threshold(indicators)
            if time_result:
                detected_indicators.append(time_result["indicator"])
                severity_scores.append(time_result["severity_score"])

            # 2. Idle detection
            idle_result = self._check_idle_threshold(indicators)
            if idle_result:
                detected_indicators.append(idle_result["indicator"])
                severity_scores.append(idle_result["severity_score"])

            # 3. Erasing detection
            erasing_result = self._check_erasing(indicators)
            if erasing_result:
                detected_indicators.append(erasing_result["indicator"])
                severity_scores.append(erasing_result["severity_score"])

            # 4. Visual detection (less frequent)
            now = time.time()
            if (now - self._last_analysis_time) >= self._visual_analysis_interval:
                visual_result = await self._check_visual_indicators(frame)
                self._last_analysis_time = now
                if visual_result:
                    detected_indicators.append(visual_result["indicator"])
                    severity_scores.append(visual_result["severity_score"])

            # Determine if struggling
            if not detected_indicators:
                return None

            # Calculate overall severity
            avg_severity = sum(severity_scores) / len(severity_scores)
            max_severity = max(severity_scores)

            # Use max severity but boost if multiple indicators
            final_severity = max_severity
            if len(detected_indicators) >= 2:
                final_severity = min(final_severity + 0.2, 1.0)
            if len(detected_indicators) >= 3:
                final_severity = min(final_severity + 0.2, 1.0)

            # Map to severity level
            if final_severity >= 0.8:
                severity = StruggleSeverity.CRITICAL.value
            elif final_severity >= 0.6:
                severity = StruggleSeverity.HIGH.value
            elif final_severity >= 0.4:
                severity = StruggleSeverity.MEDIUM.value
            else:
                severity = StruggleSeverity.LOW.value

            # Only trigger intervention for MEDIUM or higher
            is_struggling = severity in [
                StruggleSeverity.MEDIUM.value,
                StruggleSeverity.HIGH.value,
                StruggleSeverity.CRITICAL.value,
            ]

            # Primary reason is highest severity indicator
            primary_reason = detected_indicators[severity_scores.index(max_severity)]

            # Generate recommendations
            recommendations = self._generate_recommendations(detected_indicators)

            result = StruggleDetectionResult(
                is_struggling=is_struggling,
                severity=severity,
                reason=primary_reason,
                indicators=detected_indicators,
                confidence=final_severity,
                recommendations=recommendations,
                metadata={
                    "time_on_problem": indicators.get("time_on_problem", 0),
                    "idle_time": indicators.get("idle_time", 0),
                    "intervention_count": indicators.get("intervention_count", 0),
                }
            )

            # Record in history
            self._indicator_history.append({
                "timestamp": time.time(),
                "result": result.to_dict(),
            })
            if len(self._indicator_history) > 50:
                self._indicator_history.pop(0)

            if is_struggling:
                self._last_struggle_time = time.time()
                logger.info(f"Struggle detected: {primary_reason} (severity: {severity})")

            return result.to_dict()

        except Exception as e:
            logger.error(f"Struggle detection error: {e}")
            return None

    def _check_time_threshold(self, indicators: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if time on problem exceeds threshold."""
        time_on_problem = indicators.get("time_on_problem", 0)

        if time_on_problem >= self.time_threshold:
            # Calculate severity based on how much over threshold
            over_time = time_on_problem - self.time_threshold
            severity = min(0.5 + (over_time / 60) * 0.5, 1.0)  # Max at 60s over

            return {
                "indicator": StruggleIndicator.TIME_THRESHOLD.value,
                "severity_score": severity,
                "details": {
                    "time_on_problem": time_on_problem,
                    "threshold": self.time_threshold,
                }
            }

        # Warning level (approaching threshold)
        if time_on_problem >= self.warning_threshold:
            return {
                "indicator": StruggleIndicator.TIME_THRESHOLD.value,
                "severity_score": 0.3,  # Low severity, just warning
                "details": {
                    "time_on_problem": time_on_problem,
                    "threshold": self.warning_threshold,
                    "is_warning": True,
                }
            }

        return None

    def _check_idle_threshold(self, indicators: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if child has been idle too long."""
        idle_time = indicators.get("idle_time", 0)

        if idle_time >= self.idle_threshold:
            # Severity increases with idle time
            severity = min(0.4 + (idle_time - self.idle_threshold) / 30, 0.9)

            return {
                "indicator": StruggleIndicator.NO_ACTIVITY.value,
                "severity_score": severity,
                "details": {
                    "idle_time": idle_time,
                    "threshold": self.idle_threshold,
                }
            }

        return None

    def _check_erasing(self, indicators: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check for erasing activity pattern."""
        activity_state = indicators.get("activity_state", "unknown")

        if activity_state == "erasing":
            self._erasing_count += 1

            # Multiple erasing events indicate struggle
            if self._erasing_count >= 3:
                severity = min(0.4 + (self._erasing_count - 3) * 0.1, 0.8)

                return {
                    "indicator": StruggleIndicator.ERASING.value,
                    "severity_score": severity,
                    "details": {
                        "erasing_count": self._erasing_count,
                    }
                }
        else:
            # Decay erasing count slowly
            if self._erasing_count > 0:
                self._erasing_count = max(0, self._erasing_count - 0.1)

        return None

    async def _check_visual_indicators(self, frame: Any) -> Optional[Dict[str, Any]]:
        """
        Check for visual indicators of struggle.

        Looks for:
        - Crossed out work
        - Multiple attempts/corrections
        - Messy handwriting patterns
        """
        try:
            # Decode frame
            img = self._decode_frame(frame.data)
            if img is None:
                return None

            # Check for crossing out patterns
            crossing_score = self._detect_crossing_out(img)

            if crossing_score > 0.5:
                self._crossing_detected = True

                return {
                    "indicator": StruggleIndicator.CROSSING_OUT.value,
                    "severity_score": crossing_score,
                    "details": {
                        "crossing_score": crossing_score,
                    }
                }

            return None

        except Exception as e:
            logger.debug(f"Visual detection error: {e}")
            return None

    def _decode_frame(self, jpeg_data: bytes) -> Optional[np.ndarray]:
        """Decode JPEG bytes to numpy array."""
        try:
            nparr = np.frombuffer(jpeg_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception:
            return None

    def _detect_crossing_out(self, img: np.ndarray) -> float:
        """
        Detect crossed-out work in the image.

        Looks for X patterns and horizontal strike-through lines.
        Returns score 0-1 indicating likelihood of crossing out.
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Apply edge detection
            edges = cv2.Canny(gray, 50, 150)

            # Detect lines
            lines = cv2.HoughLinesP(
                edges, 1, np.pi/180, 30,
                minLineLength=20, maxLineGap=10
            )

            if lines is None:
                return 0.0

            # Count diagonal lines (crossing out pattern)
            diagonal_count = 0
            horizontal_strike_count = 0

            for line in lines:
                x1, y1, x2, y2 = line[0]
                length = np.sqrt((x2-x1)**2 + (y2-y1)**2)

                if length < 15:
                    continue

                # Calculate angle
                angle = np.abs(np.arctan2(y2-y1, x2-x1) * 180 / np.pi)

                # Diagonal lines (30-60 degrees or 120-150 degrees)
                if (30 <= angle <= 60) or (120 <= angle <= 150):
                    diagonal_count += 1

                # Horizontal strike-through (near 0 or 180 degrees)
                if angle <= 15 or angle >= 165:
                    horizontal_strike_count += 1

            # Calculate score based on line patterns
            total_suspect_lines = diagonal_count + horizontal_strike_count

            if total_suspect_lines >= 4:
                return min(0.3 + total_suspect_lines * 0.1, 0.9)
            elif diagonal_count >= 2:
                return 0.4  # X pattern likely

            return 0.0

        except Exception as e:
            logger.debug(f"Crossing detection error: {e}")
            return 0.0

    def _generate_recommendations(
        self, indicators: List[str]
    ) -> List[str]:
        """Generate intervention recommendations based on indicators."""
        recommendations = []

        if StruggleIndicator.TIME_THRESHOLD.value in indicators:
            recommendations.append("Offer a hint or break down the problem")

        if StruggleIndicator.NO_ACTIVITY.value in indicators:
            recommendations.append("Check if child needs clarification")
            recommendations.append("Ask if they understand the question")

        if StruggleIndicator.ERASING.value in indicators:
            recommendations.append("Validate their approach before they continue")
            recommendations.append("Review the steps they've taken")

        if StruggleIndicator.CROSSING_OUT.value in indicators:
            recommendations.append("Acknowledge their effort and persistence")
            recommendations.append("Suggest starting fresh with guidance")

        if not recommendations:
            recommendations.append("Offer encouragement and check in")

        return recommendations

    def reset_problem_tracking(self) -> None:
        """Reset tracking for a new problem."""
        self._erasing_count = 0
        self._crossing_detected = False

    def get_struggle_history(self) -> List[Dict[str, Any]]:
        """Get recent struggle detection history."""
        return self._indicator_history[-10:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get detection statistics."""
        if not self._indicator_history:
            return {
                "total_detections": 0,
                "avg_severity": 0,
                "common_indicators": [],
            }

        struggles = [h for h in self._indicator_history if h["result"]["is_struggling"]]

        indicator_counts: Dict[str, int] = {}
        for h in self._indicator_history:
            for ind in h["result"]["indicators"]:
                indicator_counts[ind] = indicator_counts.get(ind, 0) + 1

        common = sorted(indicator_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            "total_detections": len(struggles),
            "total_checks": len(self._indicator_history),
            "avg_severity": (
                sum(h["result"]["confidence"] for h in struggles) / max(len(struggles), 1)
            ),
            "common_indicators": [c[0] for c in common[:3]],
        }
