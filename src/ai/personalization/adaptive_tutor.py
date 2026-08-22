"""
Adaptive Tutor for EduLens Personalization Engine

This module provides real-time adaptation during tutoring sessions, adjusting hints,
explanations, and examples based on student performance and emotional state.

Author: EduLens AI Team
Version: 1.0.0
"""

import logging
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .student_model import LearningStyle, MasteryLevel, StudentModel

logger = logging.getLogger(__name__)


class HintDirectness(Enum):
    """Levels of hint directness."""

    SOCRATIC = 1  # Ask guiding questions
    SUBTLE = 2  # Point to relevant concepts
    MODERATE = 3  # Show partial solution
    DIRECT = 4  # Show full solution step


class EmotionalState(Enum):
    """Detected emotional states during learning."""

    ENGAGED = "engaged"
    STRUGGLING = "struggling"
    FRUSTRATED = "frustrated"
    CONFIDENT = "confident"
    BORED = "bored"


class ExplanationType(Enum):
    """Types of explanations."""

    CONCEPTUAL = "conceptual"  # High-level understanding
    PROCEDURAL = "procedural"  # Step-by-step process
    VISUAL = "visual"  # Diagrams and analogies
    EXAMPLE_BASED = "example-based"  # Concrete examples
    ANALOGICAL = "analogical"  # Real-world analogies


@dataclass
class AdaptationContext:
    """Context for making adaptation decisions."""

    concept_id: str
    problem_statement: str
    student_attempts: List[str]
    time_on_problem: float
    hints_used: int
    difficulty_level: int
    session_duration: float
    problems_solved_today: int


@dataclass
class HintResponse:
    """Response containing a hint."""

    hint_text: str
    directness: HintDirectness
    follow_up_question: Optional[str]
    encouragement: str
    metadata: Dict[str, Any]


@dataclass
class ExplanationResponse:
    """Response containing an explanation."""

    explanation_text: str
    explanation_type: ExplanationType
    examples: List[str]
    visual_suggestions: List[str]
    check_understanding_question: str
    metadata: Dict[str, Any]


class AdaptiveTutor:
    """
    Adaptive tutoring system that personalizes in real-time.

    Adjusts hint levels, explanation styles, examples, and pacing based on
    student model and current performance.
    """

    def __init__(self, student_model: StudentModel, config: Optional[Dict[str, Any]] = None):
        """
        Initialize AdaptiveTutor.

        Args:
            student_model: StudentModel instance for the current student
            config: Optional configuration dictionary
        """
        self.student_model = student_model
        self.config = config or self._get_default_config()

        # Session state
        self.current_hint_level = HintDirectness.SOCRATIC
        self.consecutive_struggles = 0
        self.consecutive_successes = 0
        self.last_encouragement_time = 0.0
        self.session_start_time = time.time()

        # Adaptation parameters
        self.hint_progression_threshold = self.config.get("hint_progression_threshold", 2)
        self.frustration_threshold = self.config.get("frustration_threshold", 3)
        self.encouragement_frequency = self.config.get("encouragement_frequency", 120)  # seconds

        logger.info(f"AdaptiveTutor initialized for student {student_model.student_id}")

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "hint_progression_threshold": 2,
            "frustration_threshold": 3,
            "encouragement_frequency": 120,
            "max_hint_directness": 4,
            "celebration_triggers": {
                "mastery_achieved": True,
                "consecutive_correct": 3,
                "difficult_problem_solved": True,
            },
        }

    def select_hint_level(self, context: AdaptationContext) -> HintDirectness:
        """
        Select appropriate hint directness level.

        Args:
            context: Current adaptation context

        Returns:
            HintDirectness enum value
        """
        # Get mastery level
        mastery = self.student_model.get_mastery_level(context.concept_id)

        # Base hint level on mastery
        if mastery == MasteryLevel.NOT_ATTEMPTED or mastery == MasteryLevel.BEGINNER:
            base_level = HintDirectness.MODERATE
        elif mastery == MasteryLevel.DEVELOPING:
            base_level = HintDirectness.SUBTLE
        else:  # PROFICIENT, MASTERED, EXPERT
            base_level = HintDirectness.SOCRATIC

        # Adjust based on current struggle
        if len(context.student_attempts) >= self.hint_progression_threshold:
            # Student is struggling - be more direct
            adjusted_level = min(
                HintDirectness.DIRECT.value, base_level.value + len(context.student_attempts) - 1
            )
            return HintDirectness(adjusted_level)

        # Adjust based on time spent
        expected_time = self._estimate_expected_time(context.concept_id, context.difficulty_level)
        if context.time_on_problem > expected_time * 2:
            # Taking much longer than expected - be more helpful
            adjusted_level = min(HintDirectness.DIRECT.value, base_level.value + 1)
            return HintDirectness(adjusted_level)

        return base_level

    def generate_hint(self, context: AdaptationContext) -> HintResponse:
        """
        Generate adaptive hint based on student state.

        Args:
            context: Current adaptation context

        Returns:
            HintResponse with personalized hint
        """
        hint_level = self.select_hint_level(context)
        learning_style = self.student_model.get_learning_style()

        # Generate hint text based on directness
        if hint_level == HintDirectness.SOCRATIC:
            hint_text = self._generate_socratic_hint(context, learning_style)
            follow_up = "What do you think the next step should be?"
        elif hint_level == HintDirectness.SUBTLE:
            hint_text = self._generate_subtle_hint(context, learning_style)
            follow_up = "Does that help you see what to do next?"
        elif hint_level == HintDirectness.MODERATE:
            hint_text = self._generate_moderate_hint(context, learning_style)
            follow_up = "Can you complete the rest on your own?"
        else:  # DIRECT
            hint_text = self._generate_direct_hint(context, learning_style)
            follow_up = "Now try a similar problem to practice!"

        # Generate encouragement
        encouragement = self._generate_encouragement(context)

        return HintResponse(
            hint_text=hint_text,
            directness=hint_level,
            follow_up_question=follow_up,
            encouragement=encouragement,
            metadata={
                "hint_number": context.hints_used + 1,
                "learning_style": learning_style.name,
                "mastery_level": self.student_model.get_mastery_level(context.concept_id).name,
            },
        )

    def adjust_explanation(
        self, concept_id: str, base_explanation: str, context: Optional[AdaptationContext] = None
    ) -> ExplanationResponse:
        """
        Modify explanation based on student learning style and level.

        Args:
            concept_id: Concept being explained
            base_explanation: Base explanation text
            context: Optional adaptation context

        Returns:
            ExplanationResponse with adapted explanation
        """
        learning_style = self.student_model.get_learning_style()
        mastery = self.student_model.get_mastery_level(concept_id)

        # Choose explanation type based on learning style
        if learning_style == LearningStyle.VISUAL:
            explanation_type = ExplanationType.VISUAL
            adapted_text = self._add_visual_elements(base_explanation)
            visual_suggestions = ["Draw a diagram", "Use colored markers", "Create a chart"]
        elif learning_style == LearningStyle.VERBAL:
            explanation_type = ExplanationType.CONCEPTUAL
            adapted_text = self._add_verbal_elaboration(base_explanation)
            visual_suggestions = []
        elif learning_style == LearningStyle.ANALYTICAL:
            explanation_type = ExplanationType.PROCEDURAL
            adapted_text = self._add_procedural_steps(base_explanation)
            visual_suggestions = ["Follow step-by-step", "Make a checklist"]
        elif learning_style == LearningStyle.PRACTICAL:
            explanation_type = ExplanationType.EXAMPLE_BASED
            adapted_text = self._add_concrete_examples(base_explanation)
            visual_suggestions = ["Try it yourself", "Use real objects"]
        else:  # EXPLORATORY
            explanation_type = ExplanationType.ANALOGICAL
            adapted_text = self._add_analogies(base_explanation)
            visual_suggestions = ["Explore different ways", "Make connections"]

        # Adjust complexity based on mastery
        if mastery in [MasteryLevel.NOT_ATTEMPTED, MasteryLevel.BEGINNER]:
            adapted_text = self._simplify_language(adapted_text)

        # Generate examples
        examples = self._generate_examples(concept_id, learning_style, 2)

        # Generate comprehension check
        check_question = self._generate_comprehension_check(concept_id, mastery)

        return ExplanationResponse(
            explanation_text=adapted_text,
            explanation_type=explanation_type,
            examples=examples,
            visual_suggestions=visual_suggestions,
            check_understanding_question=check_question,
            metadata={
                "learning_style": learning_style.name,
                "mastery_level": mastery.name,
                "age": self.student_model.age,
            },
        )

    def select_examples(self, concept_id: str, count: int = 3) -> List[Dict[str, Any]]:
        """
        Select relevant examples for the student.

        Args:
            concept_id: Concept identifier
            count: Number of examples to select

        Returns:
            List of example dictionaries
        """
        mastery = self.student_model.get_mastery_level(concept_id)
        learning_style = self.student_model.get_learning_style()
        difficulty = self.student_model.predict_difficulty(concept_id)

        examples = []

        # Generate examples with appropriate difficulty
        for i in range(count):
            # Gradually increase difficulty across examples
            example_difficulty = min(5, difficulty + i)

            example = {
                "problem": self._generate_example_problem(concept_id, example_difficulty),
                "difficulty": example_difficulty,
                "style": learning_style.name,
                "hints_available": mastery.value < 3,  # Provide hints for lower mastery
                "solution_shown": False,
            }

            examples.append(example)

        logger.debug(f"Selected {count} examples for {concept_id} at difficulty {difficulty}")

        return examples

    def detect_frustration(self, context: AdaptationContext) -> Tuple[EmotionalState, float]:
        """
        Detect student emotional state and frustration level.

        Args:
            context: Current adaptation context

        Returns:
            Tuple of (EmotionalState, confidence_score)
        """
        frustration_score = 0.0

        # Indicators of frustration
        # 1. Multiple failed attempts
        if len(context.student_attempts) >= self.frustration_threshold:
            frustration_score += 0.3

        # 2. Long time on problem
        expected_time = self._estimate_expected_time(context.concept_id, context.difficulty_level)
        if context.time_on_problem > expected_time * 2.5:
            frustration_score += 0.25

        # 3. Multiple hints used
        if context.hints_used >= 3:
            frustration_score += 0.2

        # 4. Long session without success
        if context.session_duration > 1800 and context.problems_solved_today < 3:  # 30 min
            frustration_score += 0.15

        # 5. Consecutive struggles
        if self.consecutive_struggles >= 3:
            frustration_score += 0.1

        # Determine emotional state
        confidence = min(1.0, frustration_score)

        if frustration_score < 0.2:
            state = EmotionalState.ENGAGED
        elif frustration_score < 0.4:
            state = EmotionalState.STRUGGLING
        elif frustration_score < 0.6:
            state = EmotionalState.FRUSTRATED
        else:
            # Very frustrated - need intervention
            state = EmotionalState.FRUSTRATED

        # Check for boredom (opposite pattern)
        if (
            context.time_on_problem < expected_time * 0.5
            and context.hints_used == 0
            and self.consecutive_successes >= 5
        ):
            state = EmotionalState.BORED
            confidence = 0.7

        # Check for confidence
        if (
            self.consecutive_successes >= 3
            and context.hints_used == 0
            and len(context.student_attempts) == 1
        ):
            state = EmotionalState.CONFIDENT
            confidence = 0.8

        logger.debug(f"Detected emotional state: {state.name} (confidence: {confidence:.2f})")

        return state, confidence

    def celebrate_progress(self, achievement_type: str, context: Dict[str, Any]) -> str:
        """
        Generate celebratory message for achievements.

        Args:
            achievement_type: Type of achievement (mastery, streak, difficulty, etc.)
            context: Context about the achievement

        Returns:
            Celebration message string
        """
        celebrations = {
            "mastery": [
                "Amazing! You've mastered {concept}! 🌟",
                "Fantastic work! You really understand {concept} now!",
                "You did it! {concept} is one of your strengths now!",
            ],
            "streak": [
                "Wow! {count} correct in a row! You're on fire!",
                "Incredible streak! Keep up the great work!",
                "You're really getting good at this!",
            ],
            "difficult": [
                "That was a tough problem, and you solved it! Excellent!",
                "Great job tackling a challenging problem!",
                "You showed real perseverance on that hard problem!",
            ],
            "improvement": [
                "Look at your progress! You're improving so much!",
                "You're getting better and better at this!",
                "What great improvement! Your hard work is paying off!",
            ],
            "first_try": [
                "Perfect! You got it on the first try!",
                "Excellent! You knew exactly what to do!",
                "Wow! First try! You really understand this!",
            ],
        }

        messages = celebrations.get(achievement_type, ["Great job!"])
        message = random.choice(messages)

        # Fill in context variables
        return message.format(**context)

    def adapt_to_emotional_state(
        self, state: EmotionalState, context: AdaptationContext
    ) -> Dict[str, Any]:
        """
        Provide adaptation recommendations based on emotional state.

        Args:
            state: Detected emotional state
            context: Current context

        Returns:
            Dictionary with adaptation recommendations
        """
        if state == EmotionalState.FRUSTRATED:
            return {
                "action": "provide_break",
                "message": "Let's take a short break. You're working really hard!",
                "hint_level": "direct",
                "difficulty_adjustment": -1,
                "show_encouragement": True,
                "suggest_different_concept": True,
            }

        elif state == EmotionalState.STRUGGLING:
            return {
                "action": "increase_support",
                "message": "This is challenging! Let me help you a bit more.",
                "hint_level": "moderate",
                "difficulty_adjustment": 0,
                "show_encouragement": True,
                "suggest_different_concept": False,
            }

        elif state == EmotionalState.BORED:
            return {
                "action": "increase_challenge",
                "message": "You're doing great! Ready for something more challenging?",
                "hint_level": "socratic",
                "difficulty_adjustment": +1,
                "show_encouragement": True,
                "suggest_different_concept": False,
            }

        elif state == EmotionalState.CONFIDENT:
            return {
                "action": "maintain_challenge",
                "message": "You're really getting this! Keep going!",
                "hint_level": "subtle",
                "difficulty_adjustment": +1,
                "show_encouragement": False,
                "suggest_different_concept": False,
            }

        else:  # ENGAGED
            return {
                "action": "continue",
                "message": "You're doing well! Keep it up!",
                "hint_level": "subtle",
                "difficulty_adjustment": 0,
                "show_encouragement": False,
                "suggest_different_concept": False,
            }

    def should_encourage(self) -> bool:
        """
        Determine if it's time for encouragement.

        Returns:
            True if encouragement should be shown
        """
        time_since_last = time.time() - self.last_encouragement_time

        # Encourage periodically
        if time_since_last > self.encouragement_frequency:
            return True

        # Encourage after struggles
        if self.consecutive_struggles >= 2:
            return True

        return False

    def update_session_state(self, success: bool, context: AdaptationContext):
        """
        Update session state based on student performance.

        Args:
            success: Whether student succeeded
            context: Current context
        """
        if success:
            self.consecutive_successes += 1
            self.consecutive_struggles = 0
        else:
            self.consecutive_struggles += 1
            self.consecutive_successes = 0

        logger.debug(
            f"Session state: successes={self.consecutive_successes}, "
            f"struggles={self.consecutive_struggles}"
        )

    # Private helper methods

    def _estimate_expected_time(self, concept_id: str, difficulty: int) -> float:
        """Estimate expected time for a problem."""
        # Base time by age
        base_time = 30.0 + (12 - self.student_model.age) * 5.0

        # Adjust by difficulty
        difficulty_multiplier = 0.5 + (difficulty * 0.25)

        # Adjust by mastery
        mastery = self.student_model.get_mastery_level(concept_id)
        mastery_multiplier = 1.5 - (mastery.value * 0.15)

        return base_time * difficulty_multiplier * mastery_multiplier

    def _generate_socratic_hint(self, context: AdaptationContext, style: LearningStyle) -> str:
        """Generate Socratic-style hint."""
        hints = [
            "What do you already know about this problem?",
            "What's the first step you could try?",
            "What similar problems have you solved before?",
            "What information do you have, and what do you need to find?",
        ]
        return random.choice(hints)

    def _generate_subtle_hint(self, context: AdaptationContext, style: LearningStyle) -> str:
        """Generate subtle hint."""
        hints = [
            "Think about the concept we just learned.",
            "Remember the pattern we saw in the examples.",
            "Look closely at the numbers in the problem.",
            "Try breaking the problem into smaller parts.",
        ]
        return random.choice(hints)

    def _generate_moderate_hint(self, context: AdaptationContext, style: LearningStyle) -> str:
        """Generate moderate hint."""
        return "Here's how to start: First, identify what the problem is asking. Then, think about which operation to use."

    def _generate_direct_hint(self, context: AdaptationContext, style: LearningStyle) -> str:
        """Generate direct hint."""
        return "Let me show you how to solve this step by step. Follow along and try to understand each step."

    def _generate_encouragement(self, context: AdaptationContext) -> str:
        """Generate encouraging message."""
        encouragements = [
            "You're doing great! Keep thinking!",
            "I can see you're working hard on this!",
            "Don't give up - you're making progress!",
            "You're on the right track!",
            "Great effort! Keep going!",
        ]

        if self.consecutive_struggles >= 2:
            encouragements = [
                "This is challenging, but I know you can do it!",
                "You're learning even when it's hard - that's amazing!",
                "Every mistake helps you learn. Keep trying!",
                "You're showing great perseverance!",
            ]

        return random.choice(encouragements)

    def _add_visual_elements(self, text: str) -> str:
        """Add visual elements to explanation."""
        return f"{text}\n\nTry drawing this out or using objects to visualize it!"

    def _add_verbal_elaboration(self, text: str) -> str:
        """Add verbal elaboration."""
        return f"{text}\n\nIn other words, we're looking at how different parts connect and work together."

    def _add_procedural_steps(self, text: str) -> str:
        """Add step-by-step procedure."""
        return f"{text}\n\nHere are the steps: 1) Read carefully, 2) Identify what's needed, 3) Apply the method, 4) Check your answer."

    def _add_concrete_examples(self, text: str) -> str:
        """Add concrete examples."""
        return f"{text}\n\nFor example, imagine you have 5 apples and you get 3 more. How many do you have in total?"

    def _add_analogies(self, text: str) -> str:
        """Add real-world analogies."""
        return f"{text}\n\nThink of it like building with blocks - each piece builds on the one before!"

    def _simplify_language(self, text: str) -> str:
        """Simplify language for younger students."""
        # In production, use NLP to actually simplify
        return (
            text.replace("utilize", "use")
            .replace("demonstrate", "show")
            .replace("comprehend", "understand")
        )

    def _generate_examples(self, concept_id: str, style: LearningStyle, count: int) -> List[str]:
        """Generate examples appropriate for learning style."""
        # Placeholder - in production, retrieve from curriculum
        return [
            f"Example {i+1}: Try solving a similar problem with different numbers"
            for i in range(count)
        ]

    def _generate_comprehension_check(self, concept_id: str, mastery: MasteryLevel) -> str:
        """Generate question to check understanding."""
        if mastery in [MasteryLevel.NOT_ATTEMPTED, MasteryLevel.BEGINNER]:
            return "Can you explain what we just learned in your own words?"
        elif mastery == MasteryLevel.DEVELOPING:
            return "Why do you think this method works?"
        else:
            return "How would you explain this to a friend who's just learning it?"

    def _generate_example_problem(self, concept_id: str, difficulty: int) -> str:
        """Generate an example problem."""
        # Placeholder - in production, generate from concept templates
        return f"Example problem for {concept_id} at difficulty {difficulty}"


def create_adaptive_tutor(
    student_model: StudentModel, config: Optional[Dict[str, Any]] = None
) -> AdaptiveTutor:
    """
    Create an AdaptiveTutor instance.

    Args:
        student_model: StudentModel for the student
        config: Optional configuration

    Returns:
        AdaptiveTutor instance
    """
    return AdaptiveTutor(student_model, config)


# Example usage
if __name__ == "__main__":
    from .student_model import create_student_model

    print("=== EduLens Adaptive Tutor ===\n")

    # Create student model
    student = create_student_model("anon_123", age=9, grade=4)

    # Simulate some learning history
    student.update_from_interaction(
        concept_id="math_3_oa_001",
        problem_type="multiplication",
        correct=False,
        attempts=2,
        time_spent=45.0,
        hint_level_used=1,
        student_response="I'm not sure",
        difficulty_level=2,
    )

    # Create adaptive tutor
    tutor = create_adaptive_tutor(student)

    print("--- Hint Generation ---")
    context = AdaptationContext(
        concept_id="math_3_oa_001",
        problem_statement="What is 6 × 4?",
        student_attempts=["20", "26"],
        time_on_problem=60.0,
        hints_used=0,
        difficulty_level=2,
        session_duration=300.0,
        problems_solved_today=2,
    )

    hint = tutor.generate_hint(context)
    print(f"Hint ({hint.directness.name}): {hint.hint_text}")
    print(f"Encouragement: {hint.encouragement}")
    print(f"Follow-up: {hint.follow_up_question}\n")

    print("--- Emotional State Detection ---")
    state, confidence = tutor.detect_frustration(context)
    print(f"Detected state: {state.name} (confidence: {confidence:.2%})\n")

    print("--- Adaptation Recommendation ---")
    adaptation = tutor.adapt_to_emotional_state(state, context)
    print(f"Action: {adaptation['action']}")
    print(f"Message: {adaptation['message']}")
    print(f"Difficulty adjustment: {adaptation['difficulty_adjustment']}\n")

    print("--- Example Selection ---")
    examples = tutor.select_examples("math_3_oa_001", count=3)
    for i, example in enumerate(examples, 1):
        print(f"{i}. Difficulty {example['difficulty']}: {example['problem']}")

    print("\n=== Adaptive Tutor Ready ===")
