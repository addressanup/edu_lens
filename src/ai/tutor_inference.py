"""
Tutoring Inference Engine for EduLens AI Agent

This module provides the TutorEngine class for generating age-appropriate, Socratic-method
educational responses. It integrates with the curriculum manager and uses fine-tuned LLMs
to guide students to answers rather than giving direct solutions.

Author: EduLens AI Team
Version: 1.0.0
"""

import json
import logging
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .curriculum_manager import CurriculumManager, create_curriculum_manager
from .llm_service import LLMConfig, LLMMessage, LLMProvider, LLMService
from .prompt_templates import HintLevel, PromptTemplateManager
from .response_validator import ResponseValidator

logger = logging.getLogger(__name__)


class DifficultyLevel(Enum):
    """Difficulty levels for adaptive explanation complexity."""

    VERY_EASY = 1
    EASY = 2
    MODERATE = 3
    CHALLENGING = 4
    ADVANCED = 5


class ResponseType(Enum):
    """Types of tutoring responses."""

    SOCRATIC_QUESTION = "socratic_question"
    HINT = "hint"
    EXPLANATION = "explanation"
    ENCOURAGEMENT = "encouragement"
    COMPREHENSION_CHECK = "comprehension_check"
    GUIDED_DISCOVERY = "guided_discovery"


# Fallback when neither config nor caller specifies a model.
DEFAULT_MODEL_FALLBACK = "claude-sonnet-4-20250514"

# Sensible default model per explicit provider choice.
DEFAULT_PROVIDER_MODELS = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o",
    "google": "gemini-1.5-flash",
    "deepseek": "deepseek-chat",
    "ollama": "llama3.2:3b",
}


class TutorEngine:
    """
    Main tutoring inference engine for generating educational responses.

    Uses Socratic method to guide students to understanding without directly
    providing answers. Adapts to student age, comprehension level, and subject matter.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        config_path: Optional[str] = None,
        curriculum_manager: Optional[CurriculumManager] = None,
        llm_provider: Optional[str] = None,
        llm_api_key: Optional[str] = None,
    ):
        """
        Initialize the TutorEngine.

        Model and provider resolution order:
        1. Explicit arguments
        2. ``configs/llm/generation_config.yaml`` (``model.name``) — the
           edge-first default (e.g. ``llama-3.2-3B``)
        3. Provider defaults / ``DEFAULT_MODEL_FALLBACK``

        Args:
            model_name: Name of the LLM model to use
            config_path: Path to generation config YAML file
            curriculum_manager: Optional pre-initialized CurriculumManager
            llm_provider: LLM provider (anthropic, openai, google, deepseek, ollama)
            llm_api_key: API key (or set via environment variable)
        """
        self.config_path = config_path or self._get_default_config_path()

        # Initialize components
        self.curriculum_manager = curriculum_manager or create_curriculum_manager()
        self.template_manager = PromptTemplateManager()
        self.validator = ResponseValidator()

        # Load configuration BEFORE LLM init so model/provider are config-driven.
        self.config = self._load_config()
        config_model = (self.config or {}).get("model", {}) or {}

        if llm_provider is None:
            llm_provider = config_model.get("provider") or "anthropic"
        if model_name is None:
            model_name = (
                config_model.get("name")
                or DEFAULT_PROVIDER_MODELS.get(llm_provider, DEFAULT_MODEL_FALLBACK)
            )

        self.model_name = model_name

        # Initialize LLM service
        self.llm_service = LLMService(
            provider=llm_provider,
            model=model_name,
            api_key=llm_api_key,
            temperature=0.7,
            max_tokens=1024,
            safety_filter=True,  # Always enable for child content
        )

        # Conversation state tracking
        self.conversation_history: List[Dict[str, str]] = []
        self.hint_level = HintLevel.SUBTLE
        self.current_difficulty = DifficultyLevel.MODERATE

        logger.info(f"TutorEngine initialized with {llm_provider}/{model_name}")

    def _get_default_config_path(self) -> str:
        """Get default path to generation config."""
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent
        return str(project_root / "configs" / "llm" / "generation_config.yaml")

    def _load_config(self) -> Dict:
        """Load generation configuration from YAML file."""
        import yaml

        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded config from {self.config_path}")
            return config
        except FileNotFoundError:
            logger.warning(f"Config file not found at {self.config_path}, using defaults")
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Get default configuration if file not found."""
        return {
            "model": {
                "name": DEFAULT_MODEL_FALLBACK,
                "max_tokens": 200,
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 50,
            },
            "safety": {
                "max_response_length": 500,
                "min_response_length": 20,
                "enable_content_filter": True,
            },
            "educational": {
                "enable_socratic_method": True,
                "max_hint_progression": 3,
                "encouragement_frequency": 0.3,
            },
        }

    def generate_response(
        self,
        student_query: str,
        context: Dict[str, Any],
        response_type: Optional[ResponseType] = None,
    ) -> Dict[str, Any]:
        """
        Generate an educational response to student query.

        Args:
            student_query: The student's question or statement
            context: Context dictionary containing:
                - age: Student age (6-12)
                - grade: Grade level (K-6)
                - subject: Subject area
                - concept_id: Current concept being taught (optional)
                - problem_statement: The problem being solved (optional)
                - previous_attempts: List of previous student attempts (optional)
            response_type: Type of response to generate (auto-detected if None)

        Returns:
            Dictionary containing:
                - response: Generated text response
                - response_type: Type of response generated
                - metadata: Additional information (hints used, difficulty, etc.)
        """
        # Validate context
        if not self._validate_context(context):
            raise ValueError("Invalid context provided")

        # Auto-detect response type if not specified
        if response_type is None:
            response_type = self._detect_response_type(student_query, context)

        # Get concept information if available
        concept_data = None
        if "concept_id" in context:
            concept_data = self.curriculum_manager.get_concept_by_id(context["concept_id"])

        # Build the prompt
        prompt = self.create_socratic_prompt(
            student_query=student_query,
            context=context,
            response_type=response_type,
            concept_data=concept_data,
        )

        # Generate response using LLM (placeholder for actual model inference)
        generated_text = self._generate_with_llm(prompt)

        # Validate response
        validation_result = self.validator.validate_response(
            response=generated_text,
            age=context.get("age", 8),
            subject=context.get("subject", "general"),
        )

        if not validation_result["is_valid"]:
            # Regenerate with stricter constraints and re-validate the retry.
            logger.warning(f"Invalid response: {validation_result['issues']}")
            generated_text = self._regenerate_safe_response(prompt, context)
            validation_result = self.validator.validate_response(
                response=generated_text,
                age=context.get("age", 8),
                subject=context.get("subject", "general"),
            )
            if not validation_result["is_valid"]:
                logger.warning("Regenerated response still invalid; returning best effort")

        # Update conversation history
        self.conversation_history.append({"role": "student", "content": student_query})
        self.conversation_history.append(
            {"role": "tutor", "content": generated_text, "type": response_type.value}
        )

        return {
            "response": generated_text,
            "response_type": response_type.value,
            "metadata": {
                "hint_level": self.hint_level.value if response_type == ResponseType.HINT else None,
                "difficulty": self.current_difficulty.value,
                "concept_id": context.get("concept_id"),
                "validation": validation_result,
                "turn_count": len(self.conversation_history) // 2,
            },
        }

    def create_socratic_prompt(
        self,
        student_query: str,
        context: Dict[str, Any],
        response_type: ResponseType,
        concept_data: Optional[Dict] = None,
    ) -> str:
        """
        Build a Socratic-style prompt for the LLM.

        Args:
            student_query: Student's question or statement
            context: Context information
            response_type: Type of response to generate
            concept_data: Concept information from curriculum

        Returns:
            Formatted prompt string for LLM
        """
        age = context.get("age", 8)
        grade = context.get("grade", "3")
        subject = context.get("subject", "general")

        # Get base template
        template = self.template_manager.get_template(
            subject=subject, template_type=response_type.value
        )

        # Build context section
        context_section = self._build_context_section(context, concept_data)

        # Build conversation history
        history_section = self._build_history_section()

        # Get age-appropriate language guidelines
        language_guidelines = self.template_manager.get_age_appropriate_guidelines(age)

        # Format the complete prompt
        prompt = template.format(
            age=age,
            grade=grade,
            subject=subject,
            context=context_section,
            conversation_history=history_section,
            student_query=student_query,
            language_guidelines=language_guidelines,
            hint_level=self.hint_level.value,
        )

        return prompt

    def guide_to_answer(
        self, problem_statement: str, student_attempts: List[str], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Provide multi-turn guidance without directly giving the answer.

        Args:
            problem_statement: The problem the student is solving
            student_attempts: List of student's previous attempts
            context: Context dictionary (age, grade, subject, etc.)

        Returns:
            Dictionary with guidance response and metadata
        """
        # Analyze student attempts to identify misconceptions
        misconceptions = self._identify_misconceptions(student_attempts, context.get("concept_id"))

        # Determine if hint level should progress
        if len(student_attempts) > 0:
            self._adjust_hint_level(len(student_attempts))

        # Build context with problem and attempts
        guidance_context = {
            **context,
            "problem_statement": problem_statement,
            "previous_attempts": student_attempts,
            "misconceptions": misconceptions,
        }

        # Generate guidance using hint template
        return self.generate_response(
            student_query=f"Student is working on: {problem_statement}",
            context=guidance_context,
            response_type=ResponseType.HINT,
        )

    def explain_concept(
        self, concept_id: str, student_age: int, current_understanding: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain a concept at an age-appropriate level.

        Args:
            concept_id: ID of concept to explain
            student_age: Student's age (6-12)
            current_understanding: Student's current understanding (optional)

        Returns:
            Dictionary with explanation and metadata
        """
        # Get concept data
        concept = self.curriculum_manager.get_concept_by_id(concept_id)
        if not concept:
            raise ValueError(f"Concept {concept_id} not found")

        # Get prerequisites
        prerequisites = self.curriculum_manager.get_prerequisites(concept_id)

        # Build context
        context = {
            "age": student_age,
            "grade": concept["grade"],
            "subject": concept["subject"],
            "concept_id": concept_id,
            "current_understanding": current_understanding,
            "prerequisites": [p["name"] for p in prerequisites],
        }

        # Generate explanation
        return self.generate_response(
            student_query=f"Explain {concept['name']}",
            context=context,
            response_type=ResponseType.EXPLANATION,
        )

    def check_understanding(
        self, concept_id: str, student_response: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify student comprehension through Socratic questioning.

        Args:
            concept_id: Concept being checked
            student_response: Student's response to check
            context: Context dictionary

        Returns:
            Dictionary with comprehension check result and follow-up
        """
        # Analyze student response for understanding indicators
        understanding_level = self._assess_understanding(student_response, concept_id)

        # Update context with understanding assessment
        check_context = {
            **context,
            "concept_id": concept_id,
            "student_response": student_response,
            "understanding_level": understanding_level,
        }

        # Generate comprehension check question or feedback
        return self.generate_response(
            student_query=student_response,
            context=check_context,
            response_type=ResponseType.COMPREHENSION_CHECK,
        )

    def adjust_difficulty(self, student_performance: Dict[str, Any]) -> DifficultyLevel:
        """
        Adapt explanation complexity based on student performance.

        Args:
            student_performance: Dictionary containing:
                - correct_attempts: Number of correct attempts
                - total_attempts: Total number of attempts
                - time_spent: Time spent on current concept (seconds)
                - struggle_indicators: List of struggle indicators

        Returns:
            New difficulty level
        """
        # Calculate success rate
        success_rate = student_performance.get("correct_attempts", 0) / max(
            student_performance.get("total_attempts", 1), 1
        )

        # Adjust based on success rate
        if success_rate >= 0.8:
            # Student is doing well, can increase difficulty
            new_difficulty = min(DifficultyLevel.ADVANCED.value, self.current_difficulty.value + 1)
        elif success_rate < 0.4:
            # Student is struggling, decrease difficulty
            new_difficulty = max(DifficultyLevel.VERY_EASY.value, self.current_difficulty.value - 1)
        else:
            # Maintain current difficulty
            new_difficulty = self.current_difficulty.value

        self.current_difficulty = DifficultyLevel(new_difficulty)
        logger.info(f"Adjusted difficulty to {self.current_difficulty.name}")

        return self.current_difficulty

    def reset_conversation(self):
        """Reset conversation history and state."""
        self.conversation_history = []
        self.hint_level = HintLevel.SUBTLE
        self.current_difficulty = DifficultyLevel.MODERATE
        logger.info("Conversation reset")

    # Private helper methods

    def _validate_context(self, context: Dict[str, Any]) -> bool:
        """Validate that context contains required fields."""
        required_fields = ["age", "grade", "subject"]
        return all(field in context for field in required_fields)

    def _detect_response_type(self, student_query: str, context: Dict[str, Any]) -> ResponseType:
        """Auto-detect the appropriate response type."""
        query_lower = student_query.lower()

        # Check for help requests
        if any(word in query_lower for word in ["help", "stuck", "don't understand"]):
            return ResponseType.HINT

        # Check for explanation requests
        if any(word in query_lower for word in ["what is", "explain", "how does", "why"]):
            return ResponseType.EXPLANATION

        # Check if the child is submitting an answer for verification
        answer_check_patterns = [
            "is this answer correct",
            "is this right",
            "did i get",
            "check my answer",
            "is my answer",
            "am i right",
        ]
        if any(pattern in query_lower for pattern in answer_check_patterns):
            return ResponseType.COMPREHENSION_CHECK

        # Check if this is likely an answer to check
        if "problem_statement" in context and len(student_query.split()) < 20:
            return ResponseType.COMPREHENSION_CHECK

        # Default to Socratic questioning
        return ResponseType.SOCRATIC_QUESTION

    def _build_context_section(self, context: Dict[str, Any], concept_data: Optional[Dict]) -> str:
        """Build the context section of the prompt."""
        sections = []

        # Add concept information if available
        if concept_data:
            sections.append(f"Current Concept: {concept_data['name']}")
            sections.append(f"Definition: {concept_data['definition']}")

            if concept_data.get("common_misconceptions"):
                misconceptions = "\n".join(
                    f"- {m}" for m in concept_data["common_misconceptions"][:3]
                )
                sections.append(f"Common Misconceptions:\n{misconceptions}")

        # Add problem statement if available
        if "problem_statement" in context:
            sections.append(f"Problem: {context['problem_statement']}")

        # Add previous attempts if available
        if "previous_attempts" in context and context["previous_attempts"]:
            attempts = "\n".join(
                f"Attempt {i+1}: {attempt}"
                for i, attempt in enumerate(context["previous_attempts"][-3:])
            )
            sections.append(f"Previous Attempts:\n{attempts}")

        return "\n\n".join(sections) if sections else "No additional context."

    def _build_history_section(self, max_turns: int = 5) -> str:
        """Build conversation history section."""
        if not self.conversation_history:
            return "No previous conversation."

        # Get last N turns
        recent_history = self.conversation_history[-max_turns * 2 :]

        formatted = []
        for entry in recent_history:
            role = "Student" if entry["role"] == "student" else "Tutor"
            formatted.append(f"{role}: {entry['content']}")

        return "\n".join(formatted)

    def _adjust_hint_level(self, attempt_count: int):
        """Adjust hint level based on number of attempts."""
        if attempt_count <= 1:
            self.hint_level = HintLevel.SUBTLE
        elif attempt_count <= 3:
            self.hint_level = HintLevel.MODERATE
        else:
            self.hint_level = HintLevel.DIRECT

        logger.info(f"Adjusted hint level to {self.hint_level.name}")

    def _identify_misconceptions(
        self, student_attempts: List[str], concept_id: Optional[str]
    ) -> List[str]:
        """Identify potential misconceptions from student attempts."""
        misconceptions = []

        if not concept_id:
            return misconceptions

        # Get known misconceptions for this concept
        known_misconceptions = self.curriculum_manager.get_common_misconceptions(concept_id)

        # Simple pattern matching (in production, use more sophisticated NLP)
        for misconception in known_misconceptions:
            # Check if misconception patterns appear in attempts
            if any(
                self._check_misconception_pattern(attempt, misconception)
                for attempt in student_attempts
            ):
                misconceptions.append(misconception)

        return misconceptions

    def _check_misconception_pattern(self, attempt: str, misconception: str) -> bool:
        """Check if attempt shows signs of a specific misconception."""
        # Simple keyword matching (placeholder for more sophisticated analysis)
        misconception_keywords = misconception.lower().split()[:3]
        attempt_lower = attempt.lower()

        return any(keyword in attempt_lower for keyword in misconception_keywords)

    def _assess_understanding(self, student_response: str, concept_id: str) -> str:
        """Assess level of student understanding from response."""
        # Length-based initial assessment. Bands are tuned for elementary
        # children: short but substantive explanations (5+ words with subject
        # vocabulary) already indicate basic understanding; ~8+ words that
        # engage the concept indicate good understanding.
        response_length = len(student_response.split())

        if response_length < 4:
            return "minimal"
        elif response_length < 8:
            return "basic"
        elif response_length < 25:
            return "good"
        else:
            return "thorough"

    def _generate_with_llm(self, prompt: str) -> str:
        """
        Generate response using configured LLM provider.

        Args:
            prompt: The full prompt to send to the LLM

        Returns:
            Generated text response
        """
        logger.info(f"Generating response with {self.model_name}")

        try:
            # Build messages for LLM
            messages = [
                LLMMessage(role="system", content=self._get_system_prompt()),
                LLMMessage(role="user", content=prompt),
            ]

            # Add conversation history for context
            for turn in self.conversation_history[-6:]:  # Last 3 turns
                # Map internal roles to LLM API roles
                role = turn["role"]
                if role == "tutor":
                    role = "assistant"
                elif role == "student":
                    role = "user"
                messages.insert(-1, LLMMessage(role=role, content=turn["content"]))

            # Generate response synchronously
            response = self.llm_service.generate_sync(messages)
            return response.content

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            # Fallback response - keep it short for voice
            return "Hmm, let me think. What part are you stuck on?"

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the tutor."""
        return """You are EduLens, a friendly AI tutor for children ages 6-12.

CRITICAL: Keep responses VERY SHORT (1-2 sentences max). This is for voice output.

TEACHING APPROACH:
- Ask ONE guiding question OR give ONE small hint
- Be warm and encouraging
- Use simple words

RESPONSE LENGTH:
- Maximum 15 words per response
- Never list multiple questions
- Never use bullet points
- One sentence is ideal

EXAMPLES OF GOOD RESPONSES:
- "That's great! What comes after 5?"
- "Nice try! Think about what half of 10 is."
- "You got it! Let's try another one."

SAFETY: Keep all content child-appropriate."""

    def _regenerate_safe_response(self, prompt: str, context: Dict[str, Any]) -> str:
        """Regenerate response with stricter safety constraints."""
        # Add safety instructions to prompt
        safe_prompt = (
            f"{prompt}\n\n"
            "IMPORTANT: Response must be age-appropriate, encouraging, "
            "and follow the Socratic method without giving direct answers."
        )

        # Attempt regeneration with higher safety settings
        return self._generate_with_llm(safe_prompt)


def create_tutor_engine(
    model_name: Optional[str] = None,
    config_path: Optional[str] = None,
    llm_provider: Optional[str] = None,
    llm_api_key: Optional[str] = None,
) -> TutorEngine:
    """
    Convenience function to create a TutorEngine instance.

    Args:
        model_name: Name of the LLM model (config-driven default if None)
        config_path: Path to generation config file
        llm_provider: LLM provider (anthropic, openai, google, deepseek, ollama);
            provider defaults apply only when explicitly given
        llm_api_key: API key (or set via environment variable)

    Returns:
        Initialized TutorEngine instance

    Example:
        # Config-driven default (configs/llm/generation_config.yaml)
        engine = create_tutor_engine()

        # Using OpenAI
        engine = create_tutor_engine(llm_provider="openai", model_name="gpt-4o")

        # Using Google Gemini
        engine = create_tutor_engine(llm_provider="google", model_name="gemini-1.5-flash")

        # Using local Ollama
        engine = create_tutor_engine(llm_provider="ollama", model_name="llama3.2:3b")
    """
    return TutorEngine(
        model_name=model_name,
        config_path=config_path,
        llm_provider=llm_provider,
        llm_api_key=llm_api_key,
    )


# Example usage
if __name__ == "__main__":
    # Initialize engine
    engine = create_tutor_engine()

    print("=== EduLens Tutor Engine ===\n")

    # Example 1: Generate response to student question
    print("--- Example 1: Socratic Response ---")
    context = {"age": 8, "grade": "3", "subject": "math", "concept_id": "math_3_oa_001"}

    result = engine.generate_response(student_query="What is 5 times 3?", context=context)

    print(f"Response: {result['response']}")
    print(f"Type: {result['response_type']}")
    print()

    # Example 2: Multi-turn guidance
    print("--- Example 2: Multi-turn Guidance ---")
    guidance_context = {"age": 9, "grade": "4", "subject": "math", "concept_id": "math_4_nbt_001"}

    guidance = engine.guide_to_answer(
        problem_statement="What is 234 + 567?",
        student_attempts=["700", "790"],
        context=guidance_context,
    )

    print(f"Guidance: {guidance['response']}")
    print(f"Hint Level: {guidance['metadata']['hint_level']}")
    print()

    # Example 3: Explain concept
    print("--- Example 3: Concept Explanation ---")
    explanation = engine.explain_concept(
        concept_id="math_3_oa_001",
        student_age=8,
        current_understanding="I know that multiplication is like adding",
    )

    print(f"Explanation: {explanation['response']}")
    print()

    # Example 4: Check understanding
    print("--- Example 4: Comprehension Check ---")
    check = engine.check_understanding(
        concept_id="math_3_oa_001",
        student_response="Multiplication is repeated addition",
        context=context,
    )

    print(f"Check: {check['response']}")
    print()

    print("=== Tutor Engine Ready ===")
