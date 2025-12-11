"""
SceneAnalyzer - Homework and Scene Detection

Analyzes video frames to:
- Detect if homework is visible
- Identify subject (math, reading, science)
- Extract problems using OCR
- Track scene stability and changes
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class SceneType(Enum):
    """Types of scenes detectable."""
    HOMEWORK = "homework"
    NON_HOMEWORK = "non_homework"
    UNKNOWN = "unknown"


class SubjectType(Enum):
    """Subject types for homework."""
    MATH = "math"
    READING = "reading"
    SCIENCE = "science"
    SOCIAL_STUDIES = "social_studies"
    UNKNOWN = "unknown"


@dataclass
class SceneAnalysisResult:
    """Result of scene analysis."""
    scene_type: str  # SceneType value
    confidence: float
    subject: Optional[str] = None  # SubjectType value
    problems_detected: List[Dict[str, Any]] = field(default_factory=list)
    focus_region: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h
    text_content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_type": self.scene_type,
            "confidence": self.confidence,
            "subject": self.subject,
            "problems_detected": self.problems_detected,
            "focus_region": self.focus_region,
            "text_content": self.text_content,
            "metadata": self.metadata,
        }


class SceneAnalyzer:
    """
    Analyzes frames to detect homework scenes and extract problems.

    Uses:
    - Color/texture analysis for paper detection
    - OCR for text extraction
    - Pattern matching for math symbols, worksheets
    - Motion/stability tracking
    """

    # Keywords that indicate different subjects
    MATH_KEYWORDS = [
        "+", "-", "×", "÷", "=", "%",
        "sum", "add", "subtract", "multiply", "divide",
        "fraction", "decimal", "equation", "solve",
        "total", "difference", "product", "quotient",
    ]

    READING_KEYWORDS = [
        "read", "story", "paragraph", "sentence",
        "word", "vocabulary", "comprehension",
        "character", "author", "title", "chapter",
    ]

    SCIENCE_KEYWORDS = [
        "experiment", "hypothesis", "observe",
        "plant", "animal", "water", "earth", "sun",
        "energy", "matter", "force", "motion",
    ]

    def __init__(
        self,
        ocr_engine: Optional[Any] = None,
        enable_ocr: bool = True,
        min_text_confidence: float = 0.6,
    ):
        """
        Initialize scene analyzer.

        Args:
            ocr_engine: Optional OCR engine instance
            enable_ocr: Whether to run OCR on frames
            min_text_confidence: Minimum OCR confidence threshold
        """
        self.ocr_engine = ocr_engine
        self.enable_ocr = enable_ocr
        self.min_text_confidence = min_text_confidence

        # State for tracking
        self._last_scene = None
        self._scene_history: List[str] = []
        self._last_ocr_result = None
        self._last_ocr_time = 0

        # OCR rate limiting (don't OCR every frame)
        self._ocr_interval = 1.0  # seconds

        # Lazy load OCR engine
        if self.ocr_engine is None and self.enable_ocr:
            self._lazy_load_ocr()

    def _lazy_load_ocr(self) -> None:
        """Lazy load OCR engine."""
        try:
            from src.vision.ocr_engine import OCREngine
            self.ocr_engine = OCREngine()
            logger.info("OCR engine loaded for scene analysis")
        except ImportError:
            logger.warning("OCR engine not available, using text detection heuristics")
            self.ocr_engine = None

    async def analyze(self, frame: Any) -> Dict[str, Any]:
        """
        Analyze a frame for homework scene detection.

        Args:
            frame: Frame object with .data (JPEG bytes)

        Returns:
            Dict with scene_type, confidence, subject, etc.
        """
        try:
            # Decode JPEG to numpy array
            img = self._decode_frame(frame.data)
            if img is None:
                return SceneAnalysisResult(
                    scene_type=SceneType.UNKNOWN.value,
                    confidence=0.0
                ).to_dict()

            # Analyze image characteristics
            paper_score = self._detect_paper(img)
            text_score, text_regions = self._detect_text_regions(img)
            math_score = self._detect_math_patterns(img)

            # Run OCR if enabled and enough time has passed
            ocr_text = ""
            ocr_problems = []
            now = time.time()

            if self.enable_ocr and (now - self._last_ocr_time) >= self._ocr_interval:
                ocr_text, ocr_problems = await self._run_ocr(img)
                self._last_ocr_time = now
                self._last_ocr_result = (ocr_text, ocr_problems)
            elif self._last_ocr_result:
                ocr_text, ocr_problems = self._last_ocr_result

            # Determine subject from OCR text
            subject = self._detect_subject(ocr_text)

            # Calculate overall homework confidence
            homework_confidence = self._calculate_homework_confidence(
                paper_score, text_score, math_score, len(ocr_problems)
            )

            # Determine scene type
            if homework_confidence >= 0.7:
                scene_type = SceneType.HOMEWORK.value
            elif homework_confidence >= 0.4:
                scene_type = SceneType.UNKNOWN.value
            else:
                scene_type = SceneType.NON_HOMEWORK.value

            # Find focus region (largest text area)
            focus_region = self._find_focus_region(text_regions)

            result = SceneAnalysisResult(
                scene_type=scene_type,
                confidence=homework_confidence,
                subject=subject,
                problems_detected=ocr_problems,
                focus_region=focus_region,
                text_content=ocr_text[:500] if ocr_text else None,
                metadata={
                    "paper_score": paper_score,
                    "text_score": text_score,
                    "math_score": math_score,
                }
            )

            # Update history
            self._scene_history.append(scene_type)
            if len(self._scene_history) > 10:
                self._scene_history.pop(0)
            self._last_scene = scene_type

            return result.to_dict()

        except Exception as e:
            logger.error(f"Scene analysis error: {e}")
            return SceneAnalysisResult(
                scene_type=SceneType.UNKNOWN.value,
                confidence=0.0,
                metadata={"error": str(e)}
            ).to_dict()

    def _decode_frame(self, jpeg_data: bytes) -> Optional[np.ndarray]:
        """Decode JPEG bytes to numpy array."""
        try:
            nparr = np.frombuffer(jpeg_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            logger.error(f"Frame decode error: {e}")
            return None

    def _detect_paper(self, img: np.ndarray) -> float:
        """
        Detect if image contains paper/worksheet.

        Returns score 0-1 indicating likelihood of paper.
        """
        try:
            # Convert to HSV
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # Paper is typically bright (high V) and low saturation
            # Define range for white/off-white paper
            lower_white = np.array([0, 0, 180])
            upper_white = np.array([180, 50, 255])

            # Create mask
            mask = cv2.inRange(hsv, lower_white, upper_white)

            # Calculate percentage of paper-like pixels
            paper_ratio = np.sum(mask > 0) / mask.size

            # Paper typically covers significant portion (30-90%)
            if 0.3 <= paper_ratio <= 0.9:
                return min(paper_ratio * 1.2, 1.0)
            elif paper_ratio > 0.9:
                return 0.8  # Too much white might be overexposed
            else:
                return paper_ratio * 0.5

        except Exception as e:
            logger.debug(f"Paper detection error: {e}")
            return 0.0

    def _detect_text_regions(self, img: np.ndarray) -> Tuple[float, List[Tuple[int, int, int, int]]]:
        """
        Detect regions likely containing text.

        Returns (score, list of bounding boxes).
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Apply adaptive threshold to get binary image
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV, 11, 2
            )

            # Find contours
            contours, _ = cv2.findContours(
                thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            # Filter contours that look like text (small, horizontal)
            text_regions = []
            total_text_area = 0
            img_area = img.shape[0] * img.shape[1]

            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                aspect_ratio = w / max(h, 1)

                # Text characters typically have aspect ratio 0.2-3
                # and reasonable size
                if 0.2 <= aspect_ratio <= 3 and 10 <= w <= 200 and 10 <= h <= 100:
                    text_regions.append((x, y, w, h))
                    total_text_area += w * h

            # Score based on text coverage
            text_ratio = total_text_area / max(img_area, 1)
            score = min(text_ratio * 10, 1.0)  # Scale up, cap at 1

            return score, text_regions

        except Exception as e:
            logger.debug(f"Text detection error: {e}")
            return 0.0, []

    def _detect_math_patterns(self, img: np.ndarray) -> float:
        """
        Detect math-specific patterns (equations, numbers, symbols).

        Returns score 0-1 indicating likelihood of math content.
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Look for horizontal lines (equations, underlines)
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
            horizontal = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)

            # Look for patterns typical of math worksheets
            # (This is a simplified heuristic)
            lines = cv2.HoughLinesP(
                horizontal, 1, np.pi/180, 50,
                minLineLength=30, maxLineGap=10
            )

            line_count = len(lines) if lines is not None else 0

            # More horizontal lines suggest structured content (math worksheets)
            if line_count > 10:
                return 0.8
            elif line_count > 5:
                return 0.5
            elif line_count > 2:
                return 0.3
            else:
                return 0.1

        except Exception as e:
            logger.debug(f"Math pattern detection error: {e}")
            return 0.0

    async def _run_ocr(self, img: np.ndarray) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Run OCR on image to extract text and problems.

        Returns (full_text, list of detected problems).
        """
        if self.ocr_engine is None:
            return "", []

        try:
            # Run OCR in thread pool to not block
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self.ocr_engine.extract_text, img
            )

            full_text = result.get("text", "")
            regions = result.get("regions", [])

            # Parse text into problems
            problems = self._parse_problems(full_text, regions)

            return full_text, problems

        except Exception as e:
            logger.error(f"OCR error: {e}")
            return "", []

    def _parse_problems(
        self, text: str, regions: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Parse OCR text into individual problems."""
        problems = []

        # Simple parsing: split by newlines and look for problem patterns
        lines = text.split('\n')

        current_problem = None
        problem_id = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this looks like a new problem (starts with number/letter)
            is_new_problem = False
            if line and (line[0].isdigit() or (line[0].isalpha() and len(line) > 1 and line[1] in '.)')):
                is_new_problem = True

            # Check for equation patterns
            has_equation = any(op in line for op in ['=', '+', '-', '×', '÷', '*', '/'])

            if is_new_problem or (has_equation and current_problem is None):
                if current_problem:
                    problems.append(current_problem)

                problem_id += 1
                current_problem = {
                    "id": f"prob_{problem_id}",
                    "text": line,
                    "type": "equation" if has_equation else "text",
                    "status": "active",
                }
            elif current_problem:
                # Append to current problem
                current_problem["text"] += " " + line

        # Don't forget last problem
        if current_problem:
            problems.append(current_problem)

        return problems

    def _detect_subject(self, text: str) -> Optional[str]:
        """Detect subject from OCR text content."""
        if not text:
            return SubjectType.UNKNOWN.value

        text_lower = text.lower()

        # Count keyword matches
        math_count = sum(1 for kw in self.MATH_KEYWORDS if kw in text_lower)
        reading_count = sum(1 for kw in self.READING_KEYWORDS if kw in text_lower)
        science_count = sum(1 for kw in self.SCIENCE_KEYWORDS if kw in text_lower)

        # Check for math symbols (high weight)
        math_symbols = sum(1 for c in text if c in '+-×÷=')
        math_count += math_symbols * 2

        # Determine subject
        if math_count > max(reading_count, science_count):
            return SubjectType.MATH.value
        elif reading_count > max(math_count, science_count):
            return SubjectType.READING.value
        elif science_count > max(math_count, reading_count):
            return SubjectType.SCIENCE.value
        else:
            return SubjectType.UNKNOWN.value

    def _calculate_homework_confidence(
        self,
        paper_score: float,
        text_score: float,
        math_score: float,
        problem_count: int
    ) -> float:
        """Calculate overall confidence that this is homework."""
        # Weighted combination
        weights = {
            "paper": 0.25,
            "text": 0.3,
            "math": 0.2,
            "problems": 0.25,
        }

        # Problem count contributes to confidence
        problem_score = min(problem_count / 5, 1.0)  # 5+ problems = full score

        confidence = (
            weights["paper"] * paper_score +
            weights["text"] * text_score +
            weights["math"] * math_score +
            weights["problems"] * problem_score
        )

        return min(confidence, 1.0)

    def _find_focus_region(
        self, text_regions: List[Tuple[int, int, int, int]]
    ) -> Optional[Tuple[int, int, int, int]]:
        """Find the main focus region (largest text cluster)."""
        if not text_regions:
            return None

        # Find bounding box of all text regions
        if len(text_regions) == 1:
            return text_regions[0]

        # Compute overall bounding box
        min_x = min(r[0] for r in text_regions)
        min_y = min(r[1] for r in text_regions)
        max_x = max(r[0] + r[2] for r in text_regions)
        max_y = max(r[1] + r[3] for r in text_regions)

        return (min_x, min_y, max_x - min_x, max_y - min_y)

    def get_scene_stability(self) -> float:
        """Get scene stability score based on recent history."""
        if len(self._scene_history) < 3:
            return 0.0

        # Count how many recent scenes match the current
        recent = self._scene_history[-5:]
        if not recent:
            return 0.0

        most_common = max(set(recent), key=recent.count)
        stability = recent.count(most_common) / len(recent)

        return stability
