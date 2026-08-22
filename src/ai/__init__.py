"""
Educational AI modules for EduLens.

This package provides AI-powered educational components including:
- Curriculum management and concept graphs
- Socratic tutoring inference engine
- Response validation and safety
- Age-appropriate prompt templates
- Personalization and adaptive learning
- Multi-provider LLM integration
"""

# Import personalization module
from . import personalization
from .curriculum_manager import CurriculumManager, create_curriculum_manager
from .llm_service import (
    LLMConfig,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    LLMService,
    generate_response,
)
from .prompt_templates import HintLevel, PromptTemplateManager
from .response_validator import ResponseValidator, validate_educational_response
from .tutor_inference import DifficultyLevel, ResponseType, TutorEngine, create_tutor_engine

__all__ = [
    # Curriculum
    "CurriculumManager",
    "create_curriculum_manager",
    # Tutoring
    "TutorEngine",
    "create_tutor_engine",
    "ResponseType",
    "DifficultyLevel",
    # Templates
    "PromptTemplateManager",
    "HintLevel",
    # Validation
    "ResponseValidator",
    "validate_educational_response",
    # LLM Service
    "LLMService",
    "LLMConfig",
    "LLMProvider",
    "LLMMessage",
    "LLMResponse",
    "generate_response",
    # Personalization
    "personalization",
]
