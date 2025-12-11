"""
Problem Segmenter for EduLens - Exercise and Question Detection

This module provides specialized functionality for segmenting educational worksheets
into individual problems/exercises, extracting question parts, and identifying
problem structure (questions, choices, answer spaces).

Author: Vision Processing Agent (VIS-001)
Task: VIS-001-T3
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional, Any, Set
import numpy as np
from pathlib import Path
import logging
import re

try:
    import cv2
except ImportError:
    cv2 = None

from src.vision.ocr_engine import BoundingBox, TextRegion, OCRResult
from src.vision.layout_analyzer import (
    LayoutAnalyzer,
    LayoutRegion,
    RegionType,
    DocumentStructure
)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProblemFormat(Enum):
    """Types of problem formats supported."""
    MULTIPLE_CHOICE = "multiple_choice"
    FILL_IN_BLANK = "fill_in_blank"
    SHORT_ANSWER = "short_answer"
    TRUE_FALSE = "true_false"
    MATCHING = "matching"
    ESSAY = "essay"
    CALCULATION = "calculation"
    DIAGRAM_LABELING = "diagram_labeling"
    UNKNOWN = "unknown"


class ProblemDifficulty(Enum):
    """Estimated problem difficulty levels."""
    ELEMENTARY = "elementary"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    UNKNOWN = "unknown"


@dataclass
class ProblemPart:
    """
    Represents a component of a problem (question text, choice, answer space, etc.).

    Attributes:
        part_type: Type of part (question, choice, answer, etc.)
        content: Text content of the part
        bounding_box: Spatial location
        metadata: Additional part-specific information
    """
    part_type: str
    content: str
    bounding_box: BoundingBox
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "part_type": self.part_type,
            "content": self.content,
            "bounding_box": self.bounding_box.to_dict(),
            "metadata": self.metadata
        }


@dataclass
class Problem:
    """
    Represents a complete problem/exercise from a worksheet.

    Attributes:
        problem_id: Unique identifier
        problem_number: Problem number as appears in document (e.g., "1", "2a")
        problem_format: Type of problem (multiple choice, short answer, etc.)
        question_text: Main question text
        choices: List of multiple choice options (if applicable)
        answer_space: Region for answer (if applicable)
        diagram: Associated diagram/image (if applicable)
        parts: All component parts of the problem
        bounding_box: Overall bounding box containing entire problem
        difficulty: Estimated difficulty level
        metadata: Additional problem metadata
    """
    problem_id: str
    problem_number: str
    problem_format: ProblemFormat
    question_text: str
    choices: List[ProblemPart] = field(default_factory=list)
    answer_space: Optional[ProblemPart] = None
    diagram: Optional[LayoutRegion] = None
    parts: List[ProblemPart] = field(default_factory=list)
    bounding_box: Optional[BoundingBox] = None
    difficulty: ProblemDifficulty = ProblemDifficulty.UNKNOWN
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "problem_id": self.problem_id,
            "problem_number": self.problem_number,
            "problem_format": self.problem_format.value,
            "question_text": self.question_text,
            "choices": [c.to_dict() for c in self.choices],
            "answer_space": self.answer_space.to_dict() if self.answer_space else None,
            "diagram": self.diagram.to_dict() if self.diagram else None,
            "parts": [p.to_dict() for p in self.parts],
            "bounding_box": self.bounding_box.to_dict() if self.bounding_box else None,
            "difficulty": self.difficulty.value,
            "metadata": self.metadata
        }


@dataclass
class WorksheetProblems:
    """
    Container for all problems detected in a worksheet.

    Attributes:
        problems: List of detected problems
        total_count: Total number of problems
        format_distribution: Count of each problem format
        metadata: Worksheet-level metadata
    """
    problems: List[Problem] = field(default_factory=list)
    total_count: int = 0
    format_distribution: Dict[ProblemFormat, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "problems": [p.to_dict() for p in self.problems],
            "total_count": self.total_count,
            "format_distribution": {k.value: v for k, v in self.format_distribution.items()},
            "metadata": self.metadata
        }


class ProblemSegmenter:
    """
    Segments educational worksheets into individual problems and extracts structure.

    This class specializes in identifying problem boundaries, extracting question
    parts (text, choices, answer spaces), and classifying problem types.
    """

    def __init__(
        self,
        layout_analyzer: Optional[LayoutAnalyzer] = None,
        min_problem_size: int = 200
    ):
        """
        Initialize the ProblemSegmenter.

        Args:
            layout_analyzer: LayoutAnalyzer instance (creates new if not provided)
            min_problem_size: Minimum area for a valid problem (pixels)
        """
        self.layout_analyzer = layout_analyzer or LayoutAnalyzer()
        self.min_problem_size = min_problem_size
        self._problem_counter = 0

        # Problem number patterns
        self.number_patterns = [
            r'^\s*(\d+)[\.\)]\s*',  # 1. or 1)
            r'^\s*(\d+[a-z])[\.\)]\s*',  # 1a. or 1a)
            r'^\s*([A-Z])[\.\)]\s*',  # A. or A)
            r'^\s*Question\s+(\d+)',  # Question 1
            r'^\s*Problem\s+(\d+)',  # Problem 1
            r'^\s*Exercise\s+(\d+)',  # Exercise 1
        ]

        # Multiple choice patterns
        self.choice_patterns = [
            r'^\s*([A-D])[\.\)]\s+(.+)',  # A. text or A) text
            r'^\s*\(([A-D])\)\s+(.+)',  # (A) text
        ]

    def segment_problems(
        self,
        image: np.ndarray,
        ocr_result: Optional[OCRResult] = None,
        document_structure: Optional[DocumentStructure] = None
    ) -> WorksheetProblems:
        """
        Segment a worksheet image into individual problems.

        Args:
            image: Worksheet image as numpy array
            ocr_result: Optional pre-computed OCR results
            document_structure: Optional pre-computed document structure

        Returns:
            WorksheetProblems containing all detected problems
        """
        logger.info("Starting problem segmentation")

        # Get document structure if not provided
        if document_structure is None:
            document_structure = self.layout_analyzer.analyze_layout(image, ocr_result)

        # Extract question regions
        question_regions = document_structure.get_regions_by_type(RegionType.QUESTION)
        mc_regions = document_structure.get_regions_by_type(RegionType.MULTIPLE_CHOICE)

        # Combine question regions
        all_question_regions = question_regions + mc_regions

        logger.info(f"Found {len(all_question_regions)} potential problem regions")

        # Process each question region into a Problem
        problems = []
        for region in all_question_regions:
            problem = self._region_to_problem(region, document_structure, image)
            if problem:
                problems.append(problem)

        # Sort problems by position (reading order)
        problems.sort(key=lambda p: (
            p.bounding_box.y if p.bounding_box else 0,
            p.bounding_box.x if p.bounding_box else 0
        ))

        # Build format distribution
        format_dist = {}
        for problem in problems:
            format_dist[problem.problem_format] = format_dist.get(problem.problem_format, 0) + 1

        result = WorksheetProblems(
            problems=problems,
            total_count=len(problems),
            format_distribution=format_dist,
            metadata={
                "image_shape": image.shape,
                "num_regions_analyzed": len(all_question_regions)
            }
        )

        logger.info(f"Segmentation complete: {len(problems)} problems detected")
        return result

    def extract_problem_parts(
        self,
        region: LayoutRegion,
        document_structure: DocumentStructure
    ) -> List[ProblemPart]:
        """
        Extract individual parts of a problem (question, choices, answer space).

        Args:
            region: LayoutRegion containing the problem
            document_structure: Full document structure for context

        Returns:
            List of ProblemPart objects
        """
        parts = []
        text = region.text_content

        # Extract problem number
        problem_number = self.detect_problem_numbers(text)
        if problem_number:
            parts.append(ProblemPart(
                part_type="number",
                content=problem_number,
                bounding_box=region.bounding_box,
                metadata={"position": "prefix"}
            ))

        # Check for multiple choice
        choices = self._extract_multiple_choice(text, region.bounding_box)
        if choices:
            parts.extend(choices)

            # Extract question text (before choices)
            question_text = self._extract_question_before_choices(text)
            if question_text:
                parts.append(ProblemPart(
                    part_type="question",
                    content=question_text,
                    bounding_box=region.bounding_box,
                    metadata={"has_choices": True}
                ))
        else:
            # No choices, entire text is question
            parts.append(ProblemPart(
                part_type="question",
                content=text,
                bounding_box=region.bounding_box,
                metadata={"has_choices": False}
            ))

        # Look for answer space in children
        for child in region.children:
            if child.region_type == RegionType.ANSWER_SPACE:
                parts.append(ProblemPart(
                    part_type="answer_space",
                    content="",
                    bounding_box=child.bounding_box,
                    metadata={"area": child.area()}
                ))

        return parts

    def detect_problem_numbers(self, text: str) -> Optional[str]:
        """
        Detect problem number from text.

        Args:
            text: Text to search for problem number

        Returns:
            Problem number string if found, None otherwise
        """
        for pattern in self.number_patterns:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def group_related_content(
        self,
        problem: Problem,
        document_structure: DocumentStructure
    ) -> Problem:
        """
        Associate diagrams and other related content with a problem.

        Args:
            problem: Problem to enhance with related content
            document_structure: Full document structure

        Returns:
            Enhanced Problem with related content
        """
        if not problem.bounding_box:
            return problem

        # Find nearby diagrams
        diagrams = document_structure.get_regions_by_type(RegionType.DIAGRAM)
        images = document_structure.get_regions_by_type(RegionType.IMAGE)
        visual_regions = diagrams + images

        # Find closest visual region
        closest_diagram = None
        min_distance = float('inf')

        p_center_x = problem.bounding_box.x + problem.bounding_box.width // 2
        p_center_y = problem.bounding_box.y + problem.bounding_box.height // 2

        for visual in visual_regions:
            v_center_x = visual.bounding_box.x + visual.bounding_box.width // 2
            v_center_y = visual.bounding_box.y + visual.bounding_box.height // 2

            distance = np.sqrt((p_center_x - v_center_x)**2 + (p_center_y - v_center_y)**2)

            # Only consider if within reasonable distance
            if distance < 400 and distance < min_distance:
                min_distance = distance
                closest_diagram = visual

        if closest_diagram:
            problem.diagram = closest_diagram
            problem.metadata['has_diagram'] = True
            problem.metadata['diagram_distance'] = min_distance

        return problem

    def _region_to_problem(
        self,
        region: LayoutRegion,
        document_structure: DocumentStructure,
        image: np.ndarray
    ) -> Optional[Problem]:
        """Convert a LayoutRegion to a Problem object."""
        # Extract problem parts
        parts = self.extract_problem_parts(region, document_structure)

        # Detect problem number
        problem_number = self.detect_problem_numbers(region.text_content)
        if not problem_number:
            # Try to generate a number based on position
            problem_number = f"p{self._problem_counter + 1}"

        # Classify problem format
        problem_format = self._classify_problem_format(region, parts)

        # Extract question text
        question_parts = [p for p in parts if p.part_type == "question"]
        question_text = " ".join([p.content for p in question_parts])

        # Extract choices
        choice_parts = [p for p in parts if p.part_type == "choice"]

        # Extract answer space
        answer_parts = [p for p in parts if p.part_type == "answer_space"]
        answer_space = answer_parts[0] if answer_parts else None

        # Create problem
        problem = Problem(
            problem_id=self._get_next_problem_id(),
            problem_number=problem_number,
            problem_format=problem_format,
            question_text=question_text,
            choices=choice_parts,
            answer_space=answer_space,
            parts=parts,
            bounding_box=region.bounding_box
        )

        # Associate related content (diagrams, etc.)
        problem = self.group_related_content(problem, document_structure)

        # Estimate difficulty
        problem.difficulty = self._estimate_difficulty(problem)

        self._problem_counter += 1
        return problem

    def _classify_problem_format(
        self,
        region: LayoutRegion,
        parts: List[ProblemPart]
    ) -> ProblemFormat:
        """Classify the format of a problem."""
        text = region.text_content.lower()

        # Check for multiple choice
        choice_parts = [p for p in parts if p.part_type == "choice"]
        if len(choice_parts) >= 2:
            return ProblemFormat.MULTIPLE_CHOICE

        # Check for true/false
        if 'true or false' in text or 'true/false' in text or 't/f' in text:
            return ProblemFormat.TRUE_FALSE

        # Check for fill in blank
        if '____' in region.text_content or '_____' in region.text_content:
            return ProblemFormat.FILL_IN_BLANK

        # Check for matching
        if 'match' in text and ('column' in text or 'following' in text):
            return ProblemFormat.MATCHING

        # Check for calculation (math keywords)
        math_keywords = ['solve', 'calculate', 'compute', 'add', 'subtract', 'multiply', 'divide', '=', '+', '-']
        if any(keyword in text for keyword in math_keywords):
            return ProblemFormat.CALCULATION

        # Check for diagram labeling
        if region.children and any(c.region_type == RegionType.DIAGRAM for c in region.children):
            if 'label' in text or 'name the' in text or 'identify' in text:
                return ProblemFormat.DIAGRAM_LABELING

        # Check for essay (long answer)
        has_answer_space = any(p.part_type == "answer_space" for p in parts)
        if has_answer_space:
            answer_spaces = [p for p in parts if p.part_type == "answer_space"]
            if answer_spaces and answer_spaces[0].metadata.get('area', 0) > 5000:
                return ProblemFormat.ESSAY

        # Default to short answer
        return ProblemFormat.SHORT_ANSWER

    def _extract_multiple_choice(
        self,
        text: str,
        bbox: BoundingBox
    ) -> List[ProblemPart]:
        """Extract multiple choice options from text."""
        choices = []
        lines = text.split('\n')

        for line in lines:
            for pattern in self.choice_patterns:
                match = re.match(pattern, line.strip())
                if match:
                    choice_label = match.group(1)
                    choice_text = match.group(2).strip()

                    choices.append(ProblemPart(
                        part_type="choice",
                        content=f"{choice_label}. {choice_text}",
                        bounding_box=bbox,
                        metadata={
                            "label": choice_label,
                            "text": choice_text
                        }
                    ))
                    break

        # Validate we have at least 2 choices
        if len(choices) >= 2:
            return choices
        return []

    def _extract_question_before_choices(self, text: str) -> str:
        """Extract question text that appears before multiple choice options."""
        lines = text.split('\n')
        question_lines = []

        for line in lines:
            # Stop when we hit a choice
            is_choice = False
            for pattern in self.choice_patterns:
                if re.match(pattern, line.strip()):
                    is_choice = True
                    break

            if is_choice:
                break

            question_lines.append(line)

        return '\n'.join(question_lines).strip()

    def _estimate_difficulty(self, problem: Problem) -> ProblemDifficulty:
        """
        Estimate problem difficulty based on various factors.

        Heuristics:
        - Question length
        - Vocabulary complexity
        - Number of steps
        - Presence of diagrams
        """
        text = problem.question_text.lower()

        # Simple heuristics
        word_count = len(text.split())

        # Elementary: short, simple questions
        if word_count < 15 and problem.problem_format in [
            ProblemFormat.MULTIPLE_CHOICE,
            ProblemFormat.TRUE_FALSE,
            ProblemFormat.FILL_IN_BLANK
        ]:
            return ProblemDifficulty.ELEMENTARY

        # Advanced: long questions, complex formats
        if word_count > 40 or problem.problem_format in [
            ProblemFormat.ESSAY,
            ProblemFormat.MATCHING
        ]:
            return ProblemDifficulty.ADVANCED

        # Intermediate: everything else
        return ProblemDifficulty.INTERMEDIATE

    def _get_next_problem_id(self) -> str:
        """Generate unique problem ID."""
        self._problem_counter += 1
        return f"problem_{self._problem_counter:04d}"


# Convenience functions

def segment_worksheet(
    image: np.ndarray,
    ocr_result: Optional[OCRResult] = None
) -> WorksheetProblems:
    """
    Convenience function to segment a worksheet in one call.

    Args:
        image: Worksheet image as numpy array
        ocr_result: Optional pre-computed OCR results

    Returns:
        WorksheetProblems with all detected problems
    """
    segmenter = ProblemSegmenter()
    return segmenter.segment_problems(image, ocr_result)


def extract_problem_by_number(
    problems: WorksheetProblems,
    problem_number: str
) -> Optional[Problem]:
    """
    Extract a specific problem by its number.

    Args:
        problems: WorksheetProblems to search
        problem_number: Problem number to find

    Returns:
        Problem if found, None otherwise
    """
    for problem in problems.problems:
        if problem.problem_number == problem_number:
            return problem
    return None


def get_problems_by_format(
    problems: WorksheetProblems,
    problem_format: ProblemFormat
) -> List[Problem]:
    """
    Get all problems of a specific format.

    Args:
        problems: WorksheetProblems to filter
        problem_format: Format to filter by

    Returns:
        List of matching problems
    """
    return [p for p in problems.problems if p.problem_format == problem_format]
