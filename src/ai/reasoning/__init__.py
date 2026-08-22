"""
Subject-Specific Reasoning Modules for EduLens

This package provides specialized reasoning engines for each subject area,
enabling subject-specific problem solving, comprehension strategies, and
educational guidance for K-6 students.

Available Modules:
- MathReasoner: Mathematics reasoning and problem solving
- ReadingReasoner: Reading comprehension and literacy support
- ScienceReasoner: Scientific method and concept explanation
- SocialStudiesReasoner: History, geography, civics, and cultural understanding

Author: EduLens AI Team
Version: 1.0.0
"""

from .math_reasoning import (
    ErrorAnalysis,
    MathOperation,
    MathProblemType,
    MathReasoner,
    MathStep,
    create_math_reasoner,
)
from .reading_reasoning import (
    ComprehensionCheck,
    ComprehensionLevel,
    ReadingReasoner,
    ReadingStrategy,
    TextType,
    VocabularyExplanation,
    create_reading_reasoner,
)
from .science_reasoning import (
    ConceptExplanation,
    ExperimentGuidance,
    ExperimentPhase,
    ScienceDomain,
    ScienceReasoner,
    ScientificProcessSkill,
    create_science_reasoner,
)
from .social_studies_reasoning import (
    CivicConcept,
    GeographicExplanation,
    GeographicFeature,
    HistoricalContext,
    SocialStudiesDomain,
    SocialStudiesReasoner,
    TimelinePeriod,
    create_social_studies_reasoner,
)

__all__ = [
    # Math reasoning
    "MathReasoner",
    "create_math_reasoner",
    "MathProblemType",
    "MathOperation",
    "MathStep",
    "ErrorAnalysis",
    # Reading reasoning
    "ReadingReasoner",
    "create_reading_reasoner",
    "TextType",
    "ComprehensionLevel",
    "ReadingStrategy",
    "VocabularyExplanation",
    "ComprehensionCheck",
    # Science reasoning
    "ScienceReasoner",
    "create_science_reasoner",
    "ScienceDomain",
    "ScientificProcessSkill",
    "ExperimentPhase",
    "ConceptExplanation",
    "ExperimentGuidance",
    # Social studies reasoning
    "SocialStudiesReasoner",
    "create_social_studies_reasoner",
    "SocialStudiesDomain",
    "TimelinePeriod",
    "GeographicFeature",
    "HistoricalContext",
    "GeographicExplanation",
    "CivicConcept",
]


# Convenience function to create all reasoners at once
def create_all_reasoners(curriculum_manager=None):
    """
    Create instances of all reasoning modules.

    Args:
        curriculum_manager: Optional shared CurriculumManager instance

    Returns:
        Dictionary containing all reasoner instances
    """
    return {
        "math": create_math_reasoner(curriculum_manager),
        "reading": create_reading_reasoner(curriculum_manager),
        "science": create_science_reasoner(curriculum_manager),
        "social_studies": create_social_studies_reasoner(curriculum_manager),
    }


# Module version and metadata
__version__ = "1.0.0"
__author__ = "EduLens AI Team"
__description__ = "Subject-specific reasoning modules for educational AI"
