"""
Vision to AI Bridge for EduLens

Connects the vision processing pipeline to the educational AI system,
transforming visual input (OCR, layout analysis) into AI-ready context.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Types of educational content detected by vision system."""

    MATH_PROBLEM = auto()
    MATH_EQUATION = auto()
    READING_PASSAGE = auto()
    MULTIPLE_CHOICE = auto()
    FILL_IN_BLANK = auto()
    SHORT_ANSWER = auto()
    DIAGRAM = auto()
    WORD_PROBLEM = auto()
    VOCABULARY = auto()
    SCIENCE_DIAGRAM = auto()
    MAP = auto()
    UNKNOWN = auto()


class SubjectArea(Enum):
    """Subject areas for educational content."""

    MATH = "math"
    READING = "reading"
    SCIENCE = "science"
    SOCIAL_STUDIES = "social_studies"
    UNKNOWN = "unknown"


@dataclass
class VisualContext:
    """
    Context extracted from visual input for AI processing.

    Contains all information the AI needs to understand what
    the student is working on.
    """

    # Raw extracted text
    full_text: str

    # Structured content
    content_type: ContentType
    subject_area: SubjectArea

    # Problem-specific fields
    problem_text: str | None = None
    problem_number: str | None = None
    answer_choices: list[str] = field(default_factory=list)
    student_answer: str | None = None

    # Layout information
    has_diagram: bool = False
    diagram_description: str | None = None

    # Metadata
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source_region: dict[str, Any] = field(default_factory=dict)

    # Handwriting detected
    is_handwritten: bool = False
    handwriting_confidence: float = 0.0

    def to_ai_prompt_context(self) -> str:
        """Convert to string context for AI prompt."""
        parts = []

        parts.append(f"Subject: {self.subject_area.value}")
        parts.append(f"Content Type: {self.content_type.name.replace('_', ' ').title()}")

        if self.problem_number:
            parts.append(f"Problem Number: {self.problem_number}")

        if self.problem_text:
            parts.append(f"Problem: {self.problem_text}")

        if self.answer_choices:
            choices_str = "\n".join(
                f"  {chr(65+i)}. {c}" for i, c in enumerate(self.answer_choices)
            )
            parts.append(f"Answer Choices:\n{choices_str}")

        if self.student_answer:
            parts.append(f"Student's Answer: {self.student_answer}")

        if self.has_diagram and self.diagram_description:
            parts.append(f"Diagram: {self.diagram_description}")

        return "\n".join(parts)


class VisionToAIBridge:
    """
    Bridge connecting vision processing output to AI tutoring system.

    Responsibilities:
    - Transform OCR output into structured educational context
    - Classify content type and subject area
    - Extract problem structure (question, choices, answer space)
    - Prepare context for AI prompt generation
    """

    def __init__(self) -> None:
        self._subject_keywords = self._build_subject_keywords()
        self._content_patterns = self._build_content_patterns()

    def _build_subject_keywords(self) -> dict[SubjectArea, set[str]]:
        """Build keyword sets for subject classification."""
        return {
            SubjectArea.MATH: {
                "add",
                "subtract",
                "multiply",
                "divide",
                "sum",
                "difference",
                "product",
                "quotient",
                "equation",
                "solve",
                "calculate",
                "fraction",
                "decimal",
                "percent",
                "area",
                "perimeter",
                "volume",
                "angle",
                "triangle",
                "rectangle",
                "circle",
                "+",
                "-",
                "×",
                "÷",
                "=",
                "<",
                ">",
                "≤",
                "≥",
            },
            SubjectArea.READING: {
                "read",
                "passage",
                "paragraph",
                "story",
                "character",
                "setting",
                "plot",
                "author",
                "main idea",
                "detail",
                "vocabulary",
                "word",
                "sentence",
                "comprehension",
                "summarize",
                "infer",
                "conclude",
                "context",
            },
            SubjectArea.SCIENCE: {
                "observe",
                "hypothesis",
                "experiment",
                "data",
                "result",
                "plant",
                "animal",
                "cell",
                "energy",
                "force",
                "motion",
                "matter",
                "solid",
                "liquid",
                "gas",
                "weather",
                "earth",
                "sun",
                "moon",
                "planet",
                "ecosystem",
                "habitat",
            },
            SubjectArea.SOCIAL_STUDIES: {
                "map",
                "community",
                "city",
                "state",
                "country",
                "government",
                "president",
                "history",
                "culture",
                "geography",
                "citizen",
                "law",
                "rights",
                "economy",
                "trade",
                "timeline",
            },
        }

    def _build_content_patterns(self) -> dict[ContentType, list[str]]:
        """Build patterns for content type detection."""
        return {
            ContentType.MULTIPLE_CHOICE: ["a)", "b)", "c)", "d)", "A.", "B.", "C.", "D."],
            ContentType.FILL_IN_BLANK: ["___", "____", "_____", "fill in"],
            ContentType.MATH_EQUATION: ["=", "solve for", "find x", "find the value"],
            ContentType.WORD_PROBLEM: ["how many", "how much", "what is the total"],
        }

    def process_vision_output(
        self,
        ocr_result: dict[str, Any],
        layout_result: dict[str, Any] | None = None,
        handwriting_result: dict[str, Any] | None = None,
    ) -> VisualContext:
        """
        Process vision pipeline output into AI-ready context.

        Args:
            ocr_result: Output from OCR engine
            layout_result: Output from layout analyzer (optional)
            handwriting_result: Output from handwriting recognizer (optional)

        Returns:
            VisualContext ready for AI processing
        """
        # Extract base text
        full_text = ocr_result.get("full_text", "")
        confidence = ocr_result.get("average_confidence", 0.0)

        # Check for handwriting
        is_handwritten = False
        handwriting_confidence = 0.0
        if handwriting_result:
            is_handwritten = True
            handwriting_confidence = handwriting_result.get("confidence", 0.0)
            # Prefer handwriting text if available and confident
            if handwriting_confidence > 0.7:
                full_text = handwriting_result.get("text", full_text)

        # Classify subject and content type
        subject_area = self._classify_subject(full_text)
        content_type = self._classify_content_type(full_text, layout_result)

        # Extract problem structure
        problem_text, problem_number = self._extract_problem(full_text, layout_result)
        answer_choices = self._extract_choices(full_text, content_type)
        student_answer = self._extract_student_answer(handwriting_result)

        # Check for diagrams
        has_diagram = False
        diagram_description = None
        if layout_result:
            diagrams = layout_result.get("diagrams", [])
            if diagrams:
                has_diagram = True
                diagram_description = self._describe_diagram(diagrams[0])

        return VisualContext(
            full_text=full_text,
            content_type=content_type,
            subject_area=subject_area,
            problem_text=problem_text,
            problem_number=problem_number,
            answer_choices=answer_choices,
            student_answer=student_answer,
            has_diagram=has_diagram,
            diagram_description=diagram_description,
            confidence=confidence,
            is_handwritten=is_handwritten,
            handwriting_confidence=handwriting_confidence,
        )

    def _classify_subject(self, text: str) -> SubjectArea:
        """Classify the subject area based on text content."""
        text_lower = text.lower()

        scores = {}
        for subject, keywords in self._subject_keywords.items():
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            scores[subject] = score

        if not scores or max(scores.values()) == 0:
            return SubjectArea.UNKNOWN

        return max(scores, key=scores.get)

    def _classify_content_type(
        self,
        text: str,
        layout_result: dict[str, Any] | None,
    ) -> ContentType:
        """Classify the type of educational content."""
        text_lower = text.lower()

        # Check for multiple choice
        for pattern in self._content_patterns[ContentType.MULTIPLE_CHOICE]:
            if pattern.lower() in text_lower:
                return ContentType.MULTIPLE_CHOICE

        # Check for fill in blank
        for pattern in self._content_patterns[ContentType.FILL_IN_BLANK]:
            if pattern in text:
                return ContentType.FILL_IN_BLANK

        # Check for math equation
        if any(p in text for p in self._content_patterns[ContentType.MATH_EQUATION]):
            return ContentType.MATH_EQUATION

        # Check for word problem
        for pattern in self._content_patterns[ContentType.WORD_PROBLEM]:
            if pattern in text_lower:
                return ContentType.WORD_PROBLEM

        # Check layout for reading passage
        if layout_result:
            region_types = layout_result.get("region_types", [])
            if "PASSAGE" in region_types or "PARAGRAPH" in region_types:
                return ContentType.READING_PASSAGE

        # Default based on detected subject
        subject = self._classify_subject(text)
        if subject == SubjectArea.MATH:
            return ContentType.MATH_PROBLEM
        elif subject == SubjectArea.READING:
            return ContentType.READING_PASSAGE

        return ContentType.UNKNOWN

    def _extract_problem(
        self,
        text: str,
        layout_result: dict[str, Any] | None,
    ) -> tuple[str | None, str | None]:
        """Extract problem text and number from content."""
        problem_text = None
        problem_number = None

        # Try to get from layout result first
        if layout_result:
            problems = layout_result.get("problems", [])
            if problems:
                problem = problems[0]  # Focus on first/current problem
                problem_text = problem.get("text")
                problem_number = problem.get("number")

        # Fall back to simple extraction
        if not problem_text:
            lines = text.strip().split("\n")
            if lines:
                # Look for numbered problems
                import re

                for line in lines:
                    match = re.match(r"^(\d+)[.)\s]+(.+)", line)
                    if match:
                        problem_number = match.group(1)
                        problem_text = match.group(2)
                        break

                # If no number found, use first substantive line
                if not problem_text:
                    problem_text = lines[0] if lines else None

        return problem_text, problem_number

    def _extract_choices(self, text: str, content_type: ContentType) -> list[str]:
        """Extract answer choices for multiple choice questions."""
        if content_type != ContentType.MULTIPLE_CHOICE:
            return []

        import re

        choices = []

        # Pattern for A) B) C) D) or A. B. C. D.
        pattern = r"[A-Da-d][.)]\s*([^\n]+)"
        matches = re.findall(pattern, text)
        choices = [m.strip() for m in matches]

        return choices[:4]  # Max 4 choices

    def _extract_student_answer(
        self,
        handwriting_result: dict[str, Any] | None,
    ) -> str | None:
        """Extract student's handwritten answer if present."""
        if not handwriting_result:
            return None

        # Look for answer region in handwriting
        answer_regions = handwriting_result.get("answer_regions", [])
        if answer_regions:
            return answer_regions[0].get("text")

        return None

    def _describe_diagram(self, diagram: dict[str, Any]) -> str:
        """Generate a text description of a diagram for AI context."""
        diagram_type = diagram.get("type", "unknown")
        labels = diagram.get("labels", [])

        description = f"A {diagram_type} diagram"
        if labels:
            description += f" with labels: {', '.join(labels)}"

        return description

    def build_ai_context(
        self,
        visual_context: VisualContext,
        student_question: str | None = None,
    ) -> dict[str, Any]:
        """
        Build complete context for AI tutoring system.

        Args:
            visual_context: Processed visual context
            student_question: Student's spoken question (if any)

        Returns:
            Dictionary with all context for AI prompt generation
        """
        context = {
            "visual": visual_context.to_ai_prompt_context(),
            "subject": visual_context.subject_area.value,
            "content_type": visual_context.content_type.name,
            "confidence": visual_context.confidence,
            "has_student_answer": visual_context.student_answer is not None,
            "student_answer": visual_context.student_answer,
        }

        if student_question:
            context["student_question"] = student_question

        return context


def create_bridge() -> VisionToAIBridge:
    """Factory function to create a configured bridge instance."""
    return VisionToAIBridge()
