"""
Context Builder for EduLens AI Tutoring

Builds comprehensive context for the AI tutor by combining:
- Visual context (what the student is looking at)
- Audio context (what the student asked)
- Student profile (learning history, preferences)
- Curriculum context (relevant concepts, prerequisites)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class StudentProfile:
    """Student profile for personalized tutoring."""

    student_id: str
    age: int
    grade_level: str

    # Learning preferences
    preferred_explanation_style: str = "step_by_step"  # step_by_step, analogy, visual
    reading_level: str = "grade_level"

    # Subject strengths/weaknesses
    subject_confidence: dict[str, float] = field(default_factory=dict)

    # Recent activity
    mastered_concepts: list[str] = field(default_factory=list)
    struggling_concepts: list[str] = field(default_factory=list)

    # Session state
    current_session_problems: int = 0
    current_session_correct: int = 0


@dataclass
class TutoringContext:
    """Complete context for AI tutoring interaction."""

    # What the student is working on
    visual_context: str
    subject: str
    content_type: str
    problem_text: str | None = None

    # What the student asked
    student_question: str | None = None

    # Student information
    student_age: int = 8
    student_grade: str = "3"
    explanation_style: str = "step_by_step"

    # Curriculum context
    relevant_concepts: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    common_misconceptions: list[str] = field(default_factory=list)

    # Interaction context
    is_followup: bool = False
    previous_hints_given: int = 0
    student_answer: str | None = None

    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    confidence: float = 0.0

    def to_prompt_context(self) -> str:
        """Convert to formatted context for AI prompt."""
        lines = [
            "=== TUTORING CONTEXT ===",
            "",
            f"Student: {self.student_age} years old, Grade {self.student_grade}",
            f"Preferred Style: {self.explanation_style}",
            "",
            "--- What Student Is Working On ---",
            self.visual_context,
            "",
        ]

        if self.student_question:
            lines.extend(
                [
                    "--- Student's Question ---",
                    self.student_question,
                    "",
                ]
            )

        if self.student_answer:
            lines.extend(
                [
                    "--- Student's Answer ---",
                    self.student_answer,
                    "",
                ]
            )

        if self.relevant_concepts:
            lines.extend(
                [
                    "--- Relevant Concepts ---",
                    ", ".join(self.relevant_concepts),
                    "",
                ]
            )

        if self.common_misconceptions:
            lines.extend(
                [
                    "--- Common Misconceptions to Watch For ---",
                    "\n".join(f"- {m}" for m in self.common_misconceptions),
                    "",
                ]
            )

        if self.is_followup:
            lines.append(f"(This is a follow-up. {self.previous_hints_given} hints already given.)")

        return "\n".join(lines)


class ContextBuilder:
    """
    Builds tutoring context by combining multiple information sources.

    This is the central point where vision, audio, student profile,
    and curriculum information come together to create the context
    that drives AI tutoring responses.
    """

    def __init__(
        self,
        curriculum_manager: Any | None = None,
    ) -> None:
        """
        Initialize the context builder.

        Args:
            curriculum_manager: CurriculumManager instance for concept lookup
        """
        self.curriculum_manager = curriculum_manager
        self._session_history: list[TutoringContext] = []

    def build_context(
        self,
        visual_context: dict[str, Any],
        audio_context: dict[str, Any] | None = None,
        student_profile: StudentProfile | None = None,
    ) -> TutoringContext:
        """
        Build complete tutoring context from available inputs.

        Args:
            visual_context: Output from VisionToAIBridge
            audio_context: Transcribed student question and metadata
            student_profile: Student's learning profile

        Returns:
            Complete TutoringContext for AI prompt generation
        """
        # Extract visual information
        visual_text = visual_context.get("visual", "")
        subject = visual_context.get("subject", "unknown")
        content_type = visual_context.get("content_type", "UNKNOWN")
        student_answer = visual_context.get("student_answer")
        confidence = visual_context.get("confidence", 0.0)

        # Extract audio information
        student_question = None
        if audio_context:
            student_question = audio_context.get("transcription")

        # Get student profile defaults
        student_age = 8
        student_grade = "3"
        explanation_style = "step_by_step"
        if student_profile:
            student_age = student_profile.age
            student_grade = student_profile.grade_level
            explanation_style = student_profile.preferred_explanation_style

        # Get curriculum context
        relevant_concepts = []
        prerequisites = []
        common_misconceptions = []

        if self.curriculum_manager and subject != "unknown":
            curriculum_context = self._get_curriculum_context(subject, content_type, student_grade)
            relevant_concepts = curriculum_context.get("concepts", [])
            prerequisites = curriculum_context.get("prerequisites", [])
            common_misconceptions = curriculum_context.get("misconceptions", [])

        # Determine if this is a follow-up
        is_followup = len(self._session_history) > 0
        previous_hints = 0
        if is_followup and self._session_history:
            previous_hints = self._session_history[-1].previous_hints_given + 1

        context = TutoringContext(
            visual_context=visual_text,
            subject=subject,
            content_type=content_type,
            student_question=student_question,
            student_age=student_age,
            student_grade=student_grade,
            explanation_style=explanation_style,
            relevant_concepts=relevant_concepts,
            prerequisites=prerequisites,
            common_misconceptions=common_misconceptions,
            is_followup=is_followup,
            previous_hints_given=previous_hints,
            student_answer=student_answer,
            confidence=confidence,
        )

        # Track history
        self._session_history.append(context)

        return context

    def _get_curriculum_context(
        self,
        subject: str,
        content_type: str,
        grade: str,
    ) -> dict[str, Any]:
        """
        Look up relevant curriculum information.

        Args:
            subject: Subject area
            content_type: Type of content
            grade: Student's grade level

        Returns:
            Dictionary with concepts, prerequisites, and misconceptions
        """
        if not self.curriculum_manager:
            return {}

        try:
            # Get grade-level topics
            topics = self.curriculum_manager.get_grade_level_topics(grade, subject)

            # Find most relevant concept based on content type
            relevant = []
            for topic in topics[:5]:  # Limit to avoid overwhelming
                concept_id = topic.get("id")
                if concept_id:
                    relevant.append(topic.get("name", concept_id))

            # Get prerequisites and misconceptions for top concept
            prerequisites = []
            misconceptions = []
            if topics:
                top_concept_id = topics[0].get("id")
                if top_concept_id:
                    prereqs = self.curriculum_manager.get_prerequisites(top_concept_id)
                    prerequisites = [p.get("name", p.get("id", "")) for p in prereqs]

                    misc = self.curriculum_manager.get_common_misconceptions(top_concept_id)
                    misconceptions = misc if isinstance(misc, list) else []

            return {
                "concepts": relevant,
                "prerequisites": prerequisites,
                "misconceptions": misconceptions,
            }
        except Exception as e:
            logger.warning(f"Error getting curriculum context: {e}")
            return {}

    def get_session_summary(self) -> dict[str, Any]:
        """Get summary of current tutoring session."""
        if not self._session_history:
            return {"interactions": 0}

        subjects = [c.subject for c in self._session_history]
        questions = [c.student_question for c in self._session_history if c.student_question]

        return {
            "interactions": len(self._session_history),
            "subjects_covered": list(set(subjects)),
            "questions_asked": len(questions),
            "total_hints_given": sum(c.previous_hints_given for c in self._session_history),
        }

    def reset_session(self) -> None:
        """Reset session history for new tutoring session."""
        self._session_history = []

    def get_escalation_needed(self) -> bool:
        """
        Determine if student needs more help (e.g., call parent/teacher).

        Returns True if student seems stuck after multiple hints.
        """
        if not self._session_history:
            return False

        recent = self._session_history[-1]
        return recent.previous_hints_given >= 5  # Escalate after 5 hints


def create_context_builder(curriculum_manager: Any | None = None) -> ContextBuilder:
    """Factory function to create a configured context builder."""
    return ContextBuilder(curriculum_manager=curriculum_manager)
