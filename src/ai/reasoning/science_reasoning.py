"""
Science Reasoning Module for EduLens AI Agent

This module provides specialized reasoning capabilities for science education,
including scientific method guidance, concept explanation, experiment support,
and data analysis for K-6 science students.

Author: EduLens AI Team
Version: 1.0.0
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ScienceDomain(Enum):
    """Science subject domains."""

    LIFE_SCIENCE = "life_science"
    PHYSICAL_SCIENCE = "physical_science"
    EARTH_SCIENCE = "earth_science"
    ENGINEERING = "engineering"


class ScientificProcessSkill(Enum):
    """Scientific process skills."""

    OBSERVING = "observing"
    CLASSIFYING = "classifying"
    MEASURING = "measuring"
    PREDICTING = "predicting"
    INFERRING = "inferring"
    COMMUNICATING = "communicating"
    EXPERIMENTING = "experimenting"


class ExperimentPhase(Enum):
    """Phases of scientific experimentation."""

    QUESTION = "question"
    HYPOTHESIS = "hypothesis"
    MATERIALS = "materials"
    PROCEDURE = "procedure"
    OBSERVATIONS = "observations"
    DATA_COLLECTION = "data_collection"
    ANALYSIS = "analysis"
    CONCLUSION = "conclusion"


@dataclass
class ConceptExplanation:
    """Science concept explanation."""

    concept_name: str
    simple_definition: str
    visual_description: str
    real_world_examples: List[str]
    key_vocabulary: List[str]
    common_misconceptions: List[str]


@dataclass
class ExperimentGuidance:
    """Guidance for conducting experiments."""

    phase: ExperimentPhase
    instructions: str
    guiding_questions: List[str]
    safety_notes: List[str]
    expected_observations: Optional[str]


class ScienceReasoner:
    """
    Specialized reasoning engine for science education.

    Provides concept explanations, experiment guidance, scientific method
    support, and data analysis help for K-6 science students.
    """

    def __init__(self, curriculum_manager=None):
        """
        Initialize the ScienceReasoner.

        Args:
            curriculum_manager: Optional CurriculumManager instance
        """
        self.curriculum_manager = curriculum_manager
        self.science_vocabulary = self._initialize_science_vocabulary()
        self.process_skills = self._initialize_process_skills()
        self.safety_guidelines = self._initialize_safety_guidelines()

    def explain_concept(
        self,
        concept_name: str,
        grade_level: str,
        student_age: int,
        prior_knowledge: Optional[List[str]] = None,
    ) -> ConceptExplanation:
        """
        Provide age-appropriate explanation of a science concept.

        Args:
            concept_name: Name of the science concept
            grade_level: Student's grade level (K-6)
            student_age: Student's age for language level
            prior_knowledge: What the student already knows

        Returns:
            ConceptExplanation object with detailed concept information
        """
        logger.info(f"Explaining science concept: {concept_name}")

        # Determine science domain
        domain = self._identify_domain(concept_name)

        # Generate age-appropriate definition
        simple_def = self._create_simple_definition(concept_name, student_age, domain)

        # Create visual description
        visual = self._create_visual_description(concept_name, student_age)

        # Get real-world examples
        examples = self._get_real_world_examples(concept_name, student_age, domain)

        # Extract key vocabulary
        vocabulary = self._get_key_vocabulary(concept_name, domain)

        # Identify common misconceptions
        misconceptions = self._get_common_misconceptions(concept_name)

        return ConceptExplanation(
            concept_name=concept_name,
            simple_definition=simple_def,
            visual_description=visual,
            real_world_examples=examples,
            key_vocabulary=vocabulary,
            common_misconceptions=misconceptions,
        )

    def guide_experiment(
        self,
        experiment_question: str,
        current_phase: ExperimentPhase,
        student_age: int,
        grade_level: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExperimentGuidance:
        """
        Provide scientific method guidance for experiments.

        Args:
            experiment_question: The scientific question being investigated
            current_phase: Current phase of the experiment
            student_age: Student's age
            grade_level: Student's grade level
            context: Additional context (materials, observations, etc.)

        Returns:
            ExperimentGuidance object with phase-specific guidance
        """
        logger.info(f"Guiding experiment phase: {current_phase.value}")

        # Generate phase-specific instructions
        instructions = self._generate_phase_instructions(
            experiment_question, current_phase, student_age
        )

        # Create guiding questions
        questions = self._generate_phase_questions(current_phase, experiment_question, student_age)

        # Identify safety considerations
        safety = self._identify_safety_notes(experiment_question, current_phase, context)

        # Describe expected observations (if applicable)
        expected_obs = None
        if current_phase in [ExperimentPhase.OBSERVATIONS, ExperimentPhase.DATA_COLLECTION]:
            expected_obs = self._describe_expected_observations(experiment_question, context)

        return ExperimentGuidance(
            phase=current_phase,
            instructions=instructions,
            guiding_questions=questions,
            safety_notes=safety,
            expected_observations=expected_obs,
        )

    def analyze_data(
        self,
        data: Dict[str, Any],
        experiment_question: str,
        student_age: int,
        data_type: str = "observations",
    ) -> Dict[str, Any]:
        """
        Help interpret experimental data and results.

        Args:
            data: The data collected (observations, measurements, etc.)
            experiment_question: The original question
            student_age: Student's age
            data_type: Type of data (observations, measurements, etc.)

        Returns:
            Dictionary with data analysis guidance:
                - patterns: Patterns noticed in data
                - guiding_questions: Questions to prompt thinking
                - interpretation_hints: Hints for understanding data
                - connection_to_question: How data relates to question
                - next_steps: What to do with this information
        """
        logger.info("Analyzing experimental data")

        # Identify patterns in the data
        patterns = self._identify_patterns(data, data_type)

        # Generate analysis questions
        questions = self._generate_analysis_questions(data, experiment_question, student_age)

        # Provide interpretation hints
        hints = self._create_interpretation_hints(data, patterns, student_age)

        # Connect data to original question
        connection = self._connect_data_to_question(data, patterns, experiment_question)

        # Suggest next steps
        next_steps = self._suggest_next_steps(data, patterns, experiment_question)

        return {
            "patterns": patterns,
            "guiding_questions": questions,
            "interpretation_hints": hints,
            "connection_to_question": connection,
            "next_steps": next_steps,
            "visualize_suggestion": self._suggest_visualization(data_type),
        }

    def connect_concepts(
        self,
        current_concept: str,
        student_age: int,
        grade_level: str,
        prior_concepts: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Connect current concept to prior knowledge and related concepts.

        Args:
            current_concept: The concept being learned
            student_age: Student's age
            grade_level: Student's grade level
            prior_concepts: Previously learned concepts

        Returns:
            Dictionary with concept connections:
                - builds_on: Prior concepts this builds on
                - related_concepts: Related science concepts
                - real_world_connections: How concept appears in daily life
                - cross_curricular: Connections to other subjects
                - analogies: Simple analogies to aid understanding
        """
        logger.info(f"Connecting concepts for: {current_concept}")

        # Identify foundational concepts
        builds_on = self._identify_prerequisite_concepts(current_concept)

        # Find related concepts
        related = self._find_related_concepts(current_concept, grade_level)

        # Create real-world connections
        real_world = self._create_real_world_connections(current_concept, student_age)

        # Find cross-curricular connections
        cross_curricular = self._find_cross_curricular_connections(current_concept)

        # Generate helpful analogies
        analogies = self._generate_analogies(current_concept, student_age)

        return {
            "builds_on": builds_on,
            "related_concepts": related,
            "real_world_connections": real_world,
            "cross_curricular": cross_curricular,
            "analogies": analogies,
            "big_idea": self._identify_big_idea(current_concept),
        }

    def guide_observation(
        self, observation_target: str, student_age: int, observation_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Guide students in making scientific observations.

        Args:
            observation_target: What is being observed
            student_age: Student's age
            observation_type: Type of observation (visual, sensory, etc.)

        Returns:
            Dictionary with observation guidance:
                - what_to_look_for: Specific things to observe
                - senses_to_use: Which senses to use
                - questions_to_ask: Questions while observing
                - recording_method: How to record observations
                - avoid_inferences: Reminder to observe vs. infer
        """
        logger.info(f"Guiding observation of: {observation_target}")

        # Identify what to look for
        look_for = self._generate_observation_targets(observation_target, observation_type)

        # Determine appropriate senses
        senses = self._identify_appropriate_senses(observation_target, observation_type)

        # Create observation questions
        questions = self._create_observation_questions(observation_target, student_age)

        # Suggest recording methods
        recording = self._suggest_recording_methods(observation_type, student_age)

        # Provide observation vs. inference guidance
        inference_guidance = self._create_inference_guidance(student_age)

        return {
            "what_to_look_for": look_for,
            "senses_to_use": senses,
            "questions_to_ask": questions,
            "recording_method": recording,
            "avoid_inferences": inference_guidance,
            "observation_tips": self._get_observation_tips(student_age),
        }

    def explain_scientific_method(
        self, student_age: int, with_example: bool = True
    ) -> Dict[str, Any]:
        """
        Explain the scientific method at an age-appropriate level.

        Args:
            student_age: Student's age
            with_example: Include example investigation

        Returns:
            Dictionary with scientific method explanation
        """
        logger.info("Explaining scientific method")

        # Get steps appropriate for age
        steps = self._get_scientific_method_steps(student_age)

        # Create simple explanations
        explanations = self._explain_method_steps(steps, student_age)

        result = {
            "steps": steps,
            "explanations": explanations,
            "why_important": self._explain_method_importance(student_age),
            "memory_aid": self._create_memory_aid(student_age),
        }

        if with_example:
            result["example"] = self._create_method_example(student_age)

        return result

    def check_hypothesis(self, hypothesis: str, question: str, student_age: int) -> Dict[str, Any]:
        """
        Check if a hypothesis is well-formed and provide guidance.

        Args:
            hypothesis: Student's hypothesis statement
            question: The scientific question
            student_age: Student's age

        Returns:
            Dictionary with hypothesis evaluation and guidance
        """
        logger.info("Checking hypothesis quality")

        # Check if hypothesis is testable
        is_testable = self._is_hypothesis_testable(hypothesis)

        # Check if it answers the question
        answers_question = self._hypothesis_matches_question(hypothesis, question)

        # Check for proper structure
        has_structure = self._check_hypothesis_structure(hypothesis)

        # Generate feedback
        feedback = self._generate_hypothesis_feedback(
            is_testable, answers_question, has_structure, student_age
        )

        # Provide improvement suggestions
        suggestions = self._suggest_hypothesis_improvements(hypothesis, question, student_age)

        return {
            "is_testable": is_testable,
            "answers_question": answers_question,
            "has_proper_structure": has_structure,
            "overall_quality": (
                "good" if all([is_testable, answers_question, has_structure]) else "needs_work"
            ),
            "feedback": feedback,
            "suggestions": suggestions,
            "example_format": self._get_hypothesis_format_example(student_age),
        }

    # Private helper methods

    def _identify_domain(self, concept_name: str) -> ScienceDomain:
        """Identify which science domain a concept belongs to."""
        concept_lower = concept_name.lower()

        # Life science indicators
        life_keywords = ["plant", "animal", "living", "organism", "habitat", "food chain"]
        if any(keyword in concept_lower for keyword in life_keywords):
            return ScienceDomain.LIFE_SCIENCE

        # Physical science indicators
        physical_keywords = ["matter", "energy", "force", "motion", "heat", "light", "sound"]
        if any(keyword in concept_lower for keyword in physical_keywords):
            return ScienceDomain.PHYSICAL_SCIENCE

        # Earth science indicators
        earth_keywords = ["weather", "rock", "earth", "water cycle", "planet", "solar system"]
        if any(keyword in concept_lower for keyword in earth_keywords):
            return ScienceDomain.EARTH_SCIENCE

        # Default to life science
        return ScienceDomain.LIFE_SCIENCE

    def _create_simple_definition(self, concept: str, age: int, domain: ScienceDomain) -> str:
        """Create age-appropriate definition."""
        # Placeholder - production would have comprehensive definitions
        if age <= 7:
            return f"{concept} is something we can learn about in science!"
        elif age <= 9:
            return f"{concept} is an important science idea about {domain.value.replace('_', ' ')}."
        else:
            return f"{concept} is a scientific concept that helps us understand {domain.value.replace('_', ' ')}."

    def _create_visual_description(self, concept: str, age: int) -> str:
        """Create visual description of concept."""
        return f"Imagine seeing {concept} - picture what it looks like, how it moves, and what happens!"

    def _get_real_world_examples(self, concept: str, age: int, domain: ScienceDomain) -> List[str]:
        """Get real-world examples of concept."""
        examples = {
            ScienceDomain.LIFE_SCIENCE: [
                "Watching plants grow in a garden",
                "Seeing animals in their habitats",
                "Observing how caterpillars become butterflies",
            ],
            ScienceDomain.PHYSICAL_SCIENCE: [
                "Pushing a swing at the playground",
                "Watching ice melt into water",
                "Seeing a ball roll down a hill",
            ],
            ScienceDomain.EARTH_SCIENCE: [
                "Watching clouds change shapes",
                "Seeing rain fall from the sky",
                "Looking at rocks and minerals",
            ],
        }

        return examples.get(domain, ["Examples from everyday life"])[:3]

    def _get_key_vocabulary(self, concept: str, domain: ScienceDomain) -> List[str]:
        """Get key vocabulary words for concept."""
        vocab_by_domain = {
            ScienceDomain.LIFE_SCIENCE: ["organism", "habitat", "adaptation", "life cycle"],
            ScienceDomain.PHYSICAL_SCIENCE: ["matter", "energy", "force", "motion"],
            ScienceDomain.EARTH_SCIENCE: ["atmosphere", "erosion", "weather", "climate"],
        }

        return vocab_by_domain.get(domain, ["science", "observation", "experiment"])[:4]

    def _get_common_misconceptions(self, concept: str) -> List[str]:
        """Identify common misconceptions about concept."""
        # Placeholder - production would have comprehensive misconceptions database
        return ["A common mistake students make", "Something that seems true but isn't quite right"]

    def _generate_phase_instructions(self, question: str, phase: ExperimentPhase, age: int) -> str:
        """Generate instructions for experiment phase."""
        instructions = {
            ExperimentPhase.QUESTION: "Think about what you want to learn. Ask a question that you can test!",
            ExperimentPhase.HYPOTHESIS: "Make a guess about what you think will happen. Use 'If...then...' to help!",
            ExperimentPhase.MATERIALS: "List everything you need for your experiment. Don't forget any tools!",
            ExperimentPhase.PROCEDURE: "Write down each step of what you'll do. Number them in order!",
            ExperimentPhase.OBSERVATIONS: "Use your senses! Write or draw what you see, hear, smell, or feel.",
            ExperimentPhase.DATA_COLLECTION: "Record your measurements and observations carefully.",
            ExperimentPhase.ANALYSIS: "Look at your data. What patterns do you see? What does it tell you?",
            ExperimentPhase.CONCLUSION: "Did your results match your hypothesis? What did you learn?",
        }

        return instructions.get(phase, "Follow the scientific method!")

    def _generate_phase_questions(
        self, phase: ExperimentPhase, question: str, age: int
    ) -> List[str]:
        """Generate guiding questions for phase."""
        questions_map = {
            ExperimentPhase.QUESTION: [
                "What do you want to find out?",
                "Can you test this question?",
                "Is your question clear?",
            ],
            ExperimentPhase.HYPOTHESIS: [
                "What do you think will happen?",
                "Why do you think that?",
                "How can you test your idea?",
            ],
            ExperimentPhase.OBSERVATIONS: [
                "What do you see?",
                "What changed?",
                "What stayed the same?",
            ],
            ExperimentPhase.CONCLUSION: [
                "What did you discover?",
                "Was your hypothesis correct?",
                "What would you do differently next time?",
            ],
        }

        return questions_map.get(phase, ["What do you notice?"])

    def _identify_safety_notes(
        self, question: str, phase: ExperimentPhase, context: Optional[Dict]
    ) -> List[str]:
        """Identify safety considerations."""
        safety_notes = ["Always have an adult help with experiments."]

        # Check for common safety concerns
        question_lower = question.lower()

        if any(word in question_lower for word in ["heat", "hot", "fire", "burn"]):
            safety_notes.append("Be careful with heat. Never touch hot objects!")

        if any(word in question_lower for word in ["water", "liquid", "wet"]):
            safety_notes.append("Be careful not to spill. Wipe up any spills right away!")

        if any(word in question_lower for word in ["sharp", "cut", "scissors"]):
            safety_notes.append("Handle sharp objects carefully with adult supervision!")

        return safety_notes

    def _describe_expected_observations(self, question: str, context: Optional[Dict]) -> str:
        """Describe what might be observed."""
        return "Look carefully at what happens. You might see changes in color, size, shape, or movement!"

    def _identify_patterns(self, data: Dict[str, Any], data_type: str) -> List[str]:
        """Identify patterns in data."""
        patterns = []

        # Simple pattern detection
        if isinstance(data, dict):
            if "measurements" in data:
                patterns.append("Notice how the measurements change")

            if "observations" in data:
                patterns.append("Look for things that happen more than once")

        patterns.append("Think about what stays the same and what changes")

        return patterns

    def _generate_analysis_questions(self, data: Dict, question: str, age: int) -> List[str]:
        """Generate questions for data analysis."""
        return [
            "What patterns do you see in your data?",
            "What surprised you?",
            "How does this answer your question?",
            "What do you think caused these results?",
        ]

    def _create_interpretation_hints(self, data: Dict, patterns: List[str], age: int) -> List[str]:
        """Create hints for interpreting data."""
        return [
            "Look at all your observations together",
            "Think about what changed and what stayed the same",
            "Connect what you see to your original question",
        ]

    def _connect_data_to_question(self, data: Dict, patterns: List[str], question: str) -> str:
        """Connect data back to original question."""
        return "Your data helps answer your question by showing you what really happened in your experiment!"

    def _suggest_next_steps(self, data: Dict, patterns: List[str], question: str) -> List[str]:
        """Suggest next steps after analysis."""
        return [
            "Make a conclusion about what you learned",
            "Think about what you would do differently next time",
            "Consider what new questions you have now",
        ]

    def _suggest_visualization(self, data_type: str) -> str:
        """Suggest how to visualize data."""
        return "Try making a chart, graph, or drawing to show your data!"

    def _identify_prerequisite_concepts(self, concept: str) -> List[str]:
        """Identify concepts this builds on."""
        # Placeholder - production would use curriculum data
        return ["basic science observation", "using senses"]

    def _find_related_concepts(self, concept: str, grade_level: str) -> List[str]:
        """Find related concepts."""
        # Placeholder
        return ["related concept 1", "related concept 2"]

    def _create_real_world_connections(self, concept: str, age: int) -> List[str]:
        """Create real-world connections."""
        return ["You see this in nature", "This happens at home", "This is used in everyday life"]

    def _find_cross_curricular_connections(self, concept: str) -> Dict[str, str]:
        """Find connections to other subjects."""
        return {
            "math": "We can measure and count things in science",
            "reading": "We read to learn about science",
            "art": "We can draw what we observe",
        }

    def _generate_analogies(self, concept: str, age: int) -> List[str]:
        """Generate helpful analogies."""
        return [f"{concept} is like something you already know"]

    def _identify_big_idea(self, concept: str) -> str:
        """Identify the big idea behind concept."""
        return "Science helps us understand the world around us!"

    def _generate_observation_targets(self, target: str, obs_type: str) -> List[str]:
        """Generate what to look for."""
        return [
            "Color and appearance",
            "Size and shape",
            "How it moves or changes",
            "Any patterns you notice",
        ]

    def _identify_appropriate_senses(self, target: str, obs_type: str) -> List[str]:
        """Identify which senses to use."""
        senses = ["sight (eyes)"]

        target_lower = target.lower()

        if "sound" in target_lower or "noise" in target_lower:
            senses.append("hearing (ears)")

        if "smell" in target_lower or "odor" in target_lower:
            senses.append("smell (nose)")

        senses.append("Do NOT taste unless an adult says it's safe!")

        return senses

    def _create_observation_questions(self, target: str, age: int) -> List[str]:
        """Create observation questions."""
        return [
            "What do you see?",
            "What do you notice?",
            "How would you describe it?",
            "What details can you find?",
        ]

    def _suggest_recording_methods(self, obs_type: str, age: int) -> List[str]:
        """Suggest how to record observations."""
        return [
            "Draw pictures of what you see",
            "Write descriptions with words",
            "Make a list of what you notice",
            "Use a chart or table",
        ]

    def _create_inference_guidance(self, age: int) -> str:
        """Guide on observation vs. inference."""
        return "Remember: Observations are what you see, hear, smell, or touch. Inferences are your guesses about why!"

    def _get_observation_tips(self, age: int) -> List[str]:
        """Get tips for good observation."""
        return [
            "Take your time and look carefully",
            "Use more than one sense if you can",
            "Notice small details",
            "Write down everything you observe",
        ]

    def _get_scientific_method_steps(self, age: int) -> List[str]:
        """Get age-appropriate scientific method steps."""
        if age <= 7:
            return [
                "Ask a Question",
                "Make a Guess",
                "Try It Out",
                "See What Happens",
                "Tell What You Learned",
            ]
        else:
            return [
                "Ask a Question",
                "Form a Hypothesis",
                "Plan Your Experiment",
                "Do the Experiment",
                "Collect Data",
                "Analyze Results",
                "Make a Conclusion",
            ]

    def _explain_method_steps(self, steps: List[str], age: int) -> Dict[str, str]:
        """Explain each step."""
        explanations = {}
        for step in steps:
            explanations[step] = f"This is when you {step.lower()}!"

        return explanations

    def _explain_method_importance(self, age: int) -> str:
        """Explain why scientific method matters."""
        return "The scientific method helps us be careful scientists and make good discoveries!"

    def _create_memory_aid(self, age: int) -> str:
        """Create memory aid for scientific method."""
        return "Remember: Question, Guess, Test, Observe, Conclude!"

    def _create_method_example(self, age: int) -> Dict[str, str]:
        """Create example of scientific method."""
        return {
            "question": "Do plants need water to grow?",
            "hypothesis": "I think plants need water to grow.",
            "test": "Give water to one plant but not another",
            "observe": "Watch both plants for two weeks",
            "conclusion": "The plant with water grew, so plants need water!",
        }

    def _is_hypothesis_testable(self, hypothesis: str) -> bool:
        """Check if hypothesis is testable."""
        # Simple check for testable statements
        testable_indicators = ["if", "then", "will", "would"]
        return any(word in hypothesis.lower() for word in testable_indicators)

    def _hypothesis_matches_question(self, hypothesis: str, question: str) -> bool:
        """Check if hypothesis relates to question."""
        # Simple word overlap check
        hyp_words = set(hypothesis.lower().split())
        q_words = set(question.lower().split())
        overlap = len(hyp_words & q_words)

        return overlap >= 2

    def _check_hypothesis_structure(self, hypothesis: str) -> bool:
        """Check if hypothesis has proper structure."""
        # Check for "if...then" structure
        hypothesis_lower = hypothesis.lower()
        return "if" in hypothesis_lower and "then" in hypothesis_lower

    def _generate_hypothesis_feedback(
        self, testable: bool, matches: bool, structure: bool, age: int
    ) -> str:
        """Generate feedback on hypothesis."""
        if testable and matches and structure:
            return "Great hypothesis! It's clear and testable!"
        elif not testable:
            return "Can you make your hypothesis something we can test with an experiment?"
        elif not structure:
            return "Try using 'If...then...' to make your hypothesis clearer!"
        else:
            return "Make sure your hypothesis answers your question!"

    def _suggest_hypothesis_improvements(
        self, hypothesis: str, question: str, age: int
    ) -> List[str]:
        """Suggest improvements to hypothesis."""
        suggestions = []

        if "if" not in hypothesis.lower():
            suggestions.append("Start with 'If...'")

        if "then" not in hypothesis.lower():
            suggestions.append("Include 'then' to show what you predict will happen")

        suggestions.append("Make sure you can test your hypothesis with an experiment")

        return suggestions

    def _get_hypothesis_format_example(self, age: int) -> str:
        """Get example hypothesis format."""
        return "If [I do this], then [this will happen] because [reason]."

    def _initialize_science_vocabulary(self) -> Dict[str, List[str]]:
        """Initialize science vocabulary by domain."""
        return {
            "life_science": ["organism", "habitat", "adaptation", "life cycle", "food chain"],
            "physical_science": ["matter", "energy", "force", "motion", "property"],
            "earth_science": ["weather", "climate", "erosion", "rock", "mineral"],
            "general": ["observe", "experiment", "hypothesis", "conclusion", "data"],
        }

    def _initialize_process_skills(self) -> Dict[str, str]:
        """Initialize scientific process skills."""
        return {
            skill.value: f"Using {skill.value} to learn about science"
            for skill in ScientificProcessSkill
        }

    def _initialize_safety_guidelines(self) -> List[str]:
        """Initialize general safety guidelines."""
        return [
            "Always work with an adult",
            "Wear safety gear if needed",
            "Keep workspace clean and organized",
            "Never taste anything unless told it's safe",
            "Wash hands before and after experiments",
        ]


def create_science_reasoner(curriculum_manager=None) -> ScienceReasoner:
    """
    Convenience function to create a ScienceReasoner instance.

    Args:
        curriculum_manager: Optional CurriculumManager instance

    Returns:
        Initialized ScienceReasoner instance
    """
    return ScienceReasoner(curriculum_manager)


# Example usage
if __name__ == "__main__":
    reasoner = create_science_reasoner()

    print("=== Science Reasoning Module ===\n")

    # Example 1: Explain a concept
    print("--- Example 1: Concept Explanation ---")
    concept = reasoner.explain_concept(concept_name="plant growth", grade_level="2", student_age=7)
    print(f"Concept: {concept.concept_name}")
    print(f"Definition: {concept.simple_definition}")
    print(f"Examples: {', '.join(concept.real_world_examples[:2])}")
    print()

    # Example 2: Guide experiment
    print("--- Example 2: Experiment Guidance ---")
    guidance = reasoner.guide_experiment(
        experiment_question="Do plants need water to grow?",
        current_phase=ExperimentPhase.HYPOTHESIS,
        student_age=8,
        grade_level="3",
    )
    print(f"Phase: {guidance.phase.value}")
    print(f"Instructions: {guidance.instructions}")
    print("Guiding Questions:")
    for q in guidance.guiding_questions:
        print(f"  - {q}")
    print()

    # Example 3: Check hypothesis
    print("--- Example 3: Hypothesis Check ---")
    hyp_check = reasoner.check_hypothesis(
        hypothesis="If I give water to plants, then they will grow.",
        question="Do plants need water to grow?",
        student_age=8,
    )
    print(f"Hypothesis Quality: {hyp_check['overall_quality']}")
    print(f"Is Testable: {hyp_check['is_testable']}")
    print(f"Feedback: {hyp_check['feedback']}")
    print()

    # Example 4: Guide observation
    print("--- Example 4: Observation Guidance ---")
    obs_guide = reasoner.guide_observation(observation_target="plants in the garden", student_age=7)
    print("What to look for:")
    for item in obs_guide["what_to_look_for"][:3]:
        print(f"  - {item}")
    print(f"Recording: {obs_guide['recording_method'][0]}")
    print()

    print("=== Science Reasoner Ready ===")
