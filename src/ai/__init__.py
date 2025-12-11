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

from .curriculum_manager import CurriculumManager, create_curriculum_manager
from .tutor_inference import (
    TutorEngine,
    create_tutor_engine,
    ResponseType,
    DifficultyLevel
)
from .prompt_templates import (
    PromptTemplateManager,
    HintLevel
)
from .response_validator import (
    ResponseValidator,
    validate_educational_response
)
from .llm_service import (
    LLMService,
    LLMConfig,
    LLMProvider,
    LLMMessage,
    LLMResponse,
    generate_response
)

# Import personalization module
from . import personalization

__all__ = [
    # Curriculum
    'CurriculumManager',
    'create_curriculum_manager',
    # Tutoring
    'TutorEngine',
    'create_tutor_engine',
    'ResponseType',
    'DifficultyLevel',
    # Templates
    'PromptTemplateManager',
    'HintLevel',
    # Validation
    'ResponseValidator',
    'validate_educational_response',
    # LLM Service
    'LLMService',
    'LLMConfig',
    'LLMProvider',
    'LLMMessage',
    'LLMResponse',
    'generate_response',
    # Personalization
    'personalization',
]
