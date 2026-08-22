"""
Comprehensive Test Suite for Subject-Specific Reasoning Modules

Tests all four reasoning modules (Math, Reading, Science, Social Studies)
to ensure they provide appropriate educational guidance for K-6 students.

Author: EduLens AI Team
Version: 1.0.0
"""

import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.ai.reasoning import (
    ComprehensionLevel,
    ExperimentPhase,
    MathOperation,
    MathProblemType,
    MathReasoner,
    ReadingReasoner,
    ReadingStrategy,
    ScienceDomain,
    ScienceReasoner,
    SocialStudiesDomain,
    SocialStudiesReasoner,
    TextType,
    create_all_reasoners,
)

# ============================================================================
# MATH REASONING TESTS
# ============================================================================


class TestMathReasoner:
    """Test suite for MathReasoner module."""

    @pytest.fixture
    def math_reasoner(self):
        """Create MathReasoner instance for testing."""
        return MathReasoner()

    def test_initialization(self, math_reasoner):
        """Test MathReasoner initializes correctly."""
        assert math_reasoner is not None
        assert hasattr(math_reasoner, "common_errors")
        assert hasattr(math_reasoner, "strategies")

    def test_analyze_arithmetic_problem(self, math_reasoner):
        """Test analyzing a simple arithmetic problem."""
        problem = "What is 5 + 3?"
        result = math_reasoner.analyze_problem(problem, grade_level="1")

        assert "problem_type" in result
        assert "operations" in result
        assert "difficulty" in result
        assert MathOperation.ADDITION.value in result["operations"]

    def test_analyze_word_problem(self, math_reasoner):
        """Test analyzing a word problem."""
        problem = "Sarah has 5 apples. She buys 3 more. How many does she have now?"
        result = math_reasoner.analyze_problem(problem, grade_level="2")

        assert result["problem_type"] == MathProblemType.WORD_PROBLEM.value
        assert result["is_word_problem"] is True
        assert len(result["numbers"]) == 2
        assert 5 in result["numbers"]
        assert 3 in result["numbers"]

    def test_analyze_fraction_problem(self, math_reasoner):
        """Test analyzing a fraction problem."""
        problem = "What is 1/2 + 1/4?"
        result = math_reasoner.analyze_problem(problem, grade_level="4")

        assert result["problem_type"] == MathProblemType.FRACTIONS.value

    def test_generate_solution_steps(self, math_reasoner):
        """Test generating solution steps."""
        problem = "What is 15 + 7?"
        steps = math_reasoner.generate_steps(problem, grade_level="2", student_age=7)

        assert len(steps) > 0
        assert all(hasattr(step, "step_number") for step in steps)
        assert all(hasattr(step, "student_friendly") for step in steps)

    def test_check_correct_work(self, math_reasoner):
        """Test checking correct student work."""
        problem = "What is 5 + 3?"
        solution = "8"
        result = math_reasoner.check_work(problem, solution, expected_answer="8", grade_level="1")

        assert "is_correct" in result
        assert "confidence" in result
        assert "feedback" in result
        assert result["is_correct"] is True

    def test_check_incorrect_work(self, math_reasoner):
        """Test checking incorrect student work."""
        problem = "What is 5 + 3?"
        solution = "7"
        result = math_reasoner.check_work(problem, solution, expected_answer="8", grade_level="1")

        assert result["is_correct"] is False

    def test_identify_errors(self, math_reasoner):
        """Test identifying mathematical errors."""
        problem = "What is 15 + 7?"
        student_work = "15 + 7 = 13"
        errors = math_reasoner.identify_errors(
            problem, student_work, correct_answer="22", grade_level="2"
        )

        assert isinstance(errors, list)

    def test_suggest_strategy(self, math_reasoner):
        """Test suggesting problem-solving strategy."""
        problem = "What is 25 + 17?"
        result = math_reasoner.suggest_strategy(problem, grade_level="2", student_age=7)

        assert "strategy_name" in result
        assert "description" in result
        assert "steps" in result
        assert "visual_aids" in result

    def test_explain_concept(self, math_reasoner):
        """Test explaining a math concept."""
        result = math_reasoner.explain_concept(
            concept_name="addition", student_age=6, include_examples=True
        )

        assert "concept" in result
        assert "definition" in result
        assert "visual_representation" in result
        assert "real_world_examples" in result
        assert "practice_examples" in result


# ============================================================================
# READING REASONING TESTS
# ============================================================================


class TestReadingReasoner:
    """Test suite for ReadingReasoner module."""

    @pytest.fixture
    def reading_reasoner(self):
        """Create ReadingReasoner instance for testing."""
        return ReadingReasoner()

    @pytest.fixture
    def sample_passage(self):
        """Sample reading passage for testing."""
        return """
        Sarah loved to read books. Every day after school, she would sit
        under the big oak tree in her backyard and read for hours. Her
        favorite books were adventure stories about brave heroes.
        """

    def test_initialization(self, reading_reasoner):
        """Test ReadingReasoner initializes correctly."""
        assert reading_reasoner is not None
        assert hasattr(reading_reasoner, "reading_strategies")

    def test_analyze_fiction_passage(self, reading_reasoner, sample_passage):
        """Test analyzing a fiction passage."""
        result = reading_reasoner.analyze_passage(sample_passage, grade_level="3")

        assert "text_type" in result
        assert "reading_level" in result
        assert "themes" in result
        assert "word_count" in result
        assert result["word_count"] > 0

    def test_identify_main_idea(self, reading_reasoner, sample_passage):
        """Test identifying main idea."""
        result = reading_reasoner.identify_main_idea(
            sample_passage, student_age=8, provide_guidance=True
        )

        assert "guiding_questions" in result
        assert "key_details" in result
        assert "thinking_strategy" in result
        assert len(result["guiding_questions"]) > 0

    def test_explain_vocabulary(self, reading_reasoner):
        """Test vocabulary explanation."""
        vocab = reading_reasoner.explain_vocabulary(
            word="adventure",
            context_sentence="Her favorite books were adventure stories.",
            student_age=8,
        )

        assert vocab.word == "adventure"
        assert vocab.definition is not None
        assert vocab.student_friendly_definition is not None
        assert isinstance(vocab.context_clues, list)
        assert isinstance(vocab.synonyms, list)

    def test_guide_comprehension(self, reading_reasoner, sample_passage):
        """Test comprehension guidance."""
        result = reading_reasoner.guide_comprehension(
            passage=sample_passage,
            student_response="Sarah likes to read",
            question="What does Sarah like to do?",
            grade_level="3",
            student_age=8,
        )

        assert "feedback" in result
        assert "guiding_questions" in result
        assert "strategy_suggestion" in result
        assert "hints" in result

    def test_check_understanding(self, reading_reasoner, sample_passage):
        """Test checking reading understanding."""
        result = reading_reasoner.check_understanding(
            passage=sample_passage,
            student_summary="Sarah loves reading adventure books every day.",
            grade_level="3",
        )

        assert "comprehension_level" in result
        assert "accuracy_score" in result
        assert "feedback" in result
        assert 0 <= result["accuracy_score"] <= 1

    def test_suggest_reading_strategy(self, reading_reasoner, sample_passage):
        """Test suggesting reading strategy."""
        result = reading_reasoner.suggest_reading_strategy(
            passage=sample_passage, difficulty_area="main_idea", student_age=8
        )

        assert "strategy_name" in result
        assert "description" in result
        assert "steps" in result
        assert "when_to_use" in result

    def test_analyze_character(self, reading_reasoner, sample_passage):
        """Test character analysis."""
        result = reading_reasoner.analyze_character(
            passage=sample_passage, character_name="Sarah", student_age=8
        )

        assert "character_name" in result
        assert "traits" in result
        assert "actions" in result
        assert "guiding_questions" in result
        assert result["character_name"] == "Sarah"


# ============================================================================
# SCIENCE REASONING TESTS
# ============================================================================


class TestScienceReasoner:
    """Test suite for ScienceReasoner module."""

    @pytest.fixture
    def science_reasoner(self):
        """Create ScienceReasoner instance for testing."""
        return ScienceReasoner()

    def test_initialization(self, science_reasoner):
        """Test ScienceReasoner initializes correctly."""
        assert science_reasoner is not None
        assert hasattr(science_reasoner, "science_vocabulary")
        assert hasattr(science_reasoner, "process_skills")

    def test_explain_concept(self, science_reasoner):
        """Test explaining a science concept."""
        concept = science_reasoner.explain_concept(
            concept_name="plant growth", grade_level="2", student_age=7
        )

        assert concept.concept_name == "plant growth"
        assert concept.simple_definition is not None
        assert concept.visual_description is not None
        assert len(concept.real_world_examples) > 0
        assert len(concept.key_vocabulary) > 0

    def test_guide_experiment_hypothesis_phase(self, science_reasoner):
        """Test guiding hypothesis phase of experiment."""
        guidance = science_reasoner.guide_experiment(
            experiment_question="Do plants need water to grow?",
            current_phase=ExperimentPhase.HYPOTHESIS,
            student_age=8,
            grade_level="3",
        )

        assert guidance.phase == ExperimentPhase.HYPOTHESIS
        assert guidance.instructions is not None
        assert len(guidance.guiding_questions) > 0
        assert len(guidance.safety_notes) > 0

    def test_guide_experiment_observation_phase(self, science_reasoner):
        """Test guiding observation phase."""
        guidance = science_reasoner.guide_experiment(
            experiment_question="What happens when ice melts?",
            current_phase=ExperimentPhase.OBSERVATIONS,
            student_age=7,
            grade_level="2",
        )

        assert guidance.phase == ExperimentPhase.OBSERVATIONS
        assert guidance.expected_observations is not None

    def test_analyze_data(self, science_reasoner):
        """Test analyzing experimental data."""
        data = {
            "observations": ["Plant A grew 2 inches", "Plant B grew 0 inches"],
            "measurements": [2, 0],
        }

        result = science_reasoner.analyze_data(
            data=data, experiment_question="Do plants need water?", student_age=8
        )

        assert "patterns" in result
        assert "guiding_questions" in result
        assert "interpretation_hints" in result
        assert "connection_to_question" in result

    def test_connect_concepts(self, science_reasoner):
        """Test connecting science concepts."""
        result = science_reasoner.connect_concepts(
            current_concept="photosynthesis", student_age=10, grade_level="5"
        )

        assert "builds_on" in result
        assert "related_concepts" in result
        assert "real_world_connections" in result
        assert "cross_curricular" in result

    def test_guide_observation(self, science_reasoner):
        """Test guiding scientific observation."""
        result = science_reasoner.guide_observation(
            observation_target="plants in the garden", student_age=7
        )

        assert "what_to_look_for" in result
        assert "senses_to_use" in result
        assert "questions_to_ask" in result
        assert "recording_method" in result

    def test_explain_scientific_method(self, science_reasoner):
        """Test explaining scientific method."""
        result = science_reasoner.explain_scientific_method(student_age=8, with_example=True)

        assert "steps" in result
        assert "explanations" in result
        assert "why_important" in result
        assert "example" in result

    def test_check_hypothesis_quality(self, science_reasoner):
        """Test checking hypothesis quality."""
        result = science_reasoner.check_hypothesis(
            hypothesis="If I give water to plants, then they will grow.",
            question="Do plants need water to grow?",
            student_age=8,
        )

        assert "is_testable" in result
        assert "answers_question" in result
        assert "overall_quality" in result
        assert "feedback" in result


# ============================================================================
# SOCIAL STUDIES REASONING TESTS
# ============================================================================


class TestSocialStudiesReasoner:
    """Test suite for SocialStudiesReasoner module."""

    @pytest.fixture
    def social_studies_reasoner(self):
        """Create SocialStudiesReasoner instance for testing."""
        return SocialStudiesReasoner()

    def test_initialization(self, social_studies_reasoner):
        """Test SocialStudiesReasoner initializes correctly."""
        assert social_studies_reasoner is not None
        assert hasattr(social_studies_reasoner, "historical_periods")
        assert hasattr(social_studies_reasoner, "geographic_terms")

    def test_provide_historical_context(self, social_studies_reasoner):
        """Test providing historical context."""
        result = social_studies_reasoner.provide_context(
            topic="American Revolution",
            domain=SocialStudiesDomain.HISTORY,
            grade_level="5",
            student_age=10,
        )

        assert "background" in result
        assert "key_points" in result
        assert "connections_to_today" in result
        assert "vocabulary" in result

    def test_provide_geographic_context(self, social_studies_reasoner):
        """Test providing geographic context."""
        result = social_studies_reasoner.provide_context(
            topic="mountains", domain=SocialStudiesDomain.GEOGRAPHY, grade_level="3", student_age=8
        )

        assert result["domain"] == SocialStudiesDomain.GEOGRAPHY.value

    def test_explain_civic_concept(self, social_studies_reasoner):
        """Test explaining a civic concept."""
        result = social_studies_reasoner.explain_concepts(
            concept="citizenship", domain=SocialStudiesDomain.CIVICS, student_age=8
        )

        assert "concept" in result
        assert "definition" in result
        assert "why_it_matters" in result

    def test_analyze_maps(self, social_studies_reasoner):
        """Test map analysis guidance."""
        result = social_studies_reasoner.analyze_maps(
            map_description="Political map of United States", map_type="political", student_age=8
        )

        assert "what_to_look_for" in result
        assert "map_elements" in result
        assert "questions_to_ask" in result
        assert "map_reading_tips" in result

    def test_timeline_support(self, social_studies_reasoner):
        """Test timeline support."""
        events = [
            {"name": "Event 1", "date": "1776"},
            {"name": "Event 2", "date": "1787"},
            {"name": "Event 3", "date": "1800"},
        ]

        result = social_studies_reasoner.timeline_support(events=events, student_age=10)

        assert "organized_events" in result
        assert "time_relationships" in result
        assert "memory_aids" in result

    def test_explain_perspectives(self, social_studies_reasoner):
        """Test explaining different perspectives."""
        result = social_studies_reasoner.explain_perspectives(
            topic="school rules", student_age=8, grade_level="3"
        )

        assert "what_are_perspectives" in result
        assert "why_perspectives_matter" in result
        assert "questions_to_consider" in result
        assert "empathy_guidance" in result

    def test_community_connections(self, social_studies_reasoner):
        """Test creating community connections."""
        result = social_studies_reasoner.community_connections(
            concept="citizenship", student_age=8, grade_level="3"
        )

        assert "in_my_community" in result
        assert "in_my_life" in result
        assert "people_who_help" in result
        assert "ways_to_participate" in result

    def test_explain_historical_significance(self, social_studies_reasoner):
        """Test explaining historical significance."""
        context = social_studies_reasoner.explain_historical_significance(
            event="Declaration of Independence", student_age=10, grade_level="5"
        )

        assert context.event_name == "Declaration of Independence"
        assert context.time_period is not None
        assert context.why_significant is not None
        assert context.connection_to_today is not None

    def test_cultural_awareness(self, social_studies_reasoner):
        """Test cultural awareness guidance."""
        result = social_studies_reasoner.cultural_awareness(
            culture_topic="holiday traditions", student_age=8
        )

        assert "overview" in result
        assert "similarities_and_differences" in result
        assert "how_to_appreciate" in result
        assert "questions_for_understanding" in result


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestReasoningIntegration:
    """Integration tests for all reasoning modules."""

    def test_create_all_reasoners(self):
        """Test creating all reasoners at once."""
        reasoners = create_all_reasoners()

        assert "math" in reasoners
        assert "reading" in reasoners
        assert "science" in reasoners
        assert "social_studies" in reasoners

        assert isinstance(reasoners["math"], MathReasoner)
        assert isinstance(reasoners["reading"], ReadingReasoner)
        assert isinstance(reasoners["science"], ScienceReasoner)
        assert isinstance(reasoners["social_studies"], SocialStudiesReasoner)

    def test_math_reading_collaboration(self):
        """Test math word problems requiring reading comprehension."""
        math_reasoner = MathReasoner()
        reading_reasoner = ReadingReasoner()

        problem = "Sarah has 5 apples. She buys 3 more. How many does she have now?"

        # Analyze as math problem
        math_analysis = math_reasoner.analyze_problem(problem, grade_level="2")
        assert math_analysis["is_word_problem"] is True

        # Analyze reading comprehension
        reading_analysis = reading_reasoner.analyze_passage(problem, grade_level="2")
        assert reading_analysis["word_count"] > 0

    def test_science_math_collaboration(self):
        """Test science experiments requiring math calculations."""
        science_reasoner = ScienceReasoner()
        math_reasoner = MathReasoner()

        # Science experiment with measurements
        data = {"measurements": [2.5, 3.0, 3.5], "observations": ["Plant grew"]}

        science_analysis = science_reasoner.analyze_data(
            data=data, experiment_question="How much did the plant grow?", student_age=9
        )

        assert "patterns" in science_analysis

    def test_cross_subject_vocabulary(self):
        """Test vocabulary support across subjects."""
        reasoners = create_all_reasoners()

        # Each reasoner should handle vocabulary
        math_concept = reasoners["math"].explain_concept(concept_name="addition", student_age=7)
        assert "key_vocabulary" in math_concept

        reading_vocab = reasoners["reading"].explain_vocabulary(
            word="character",
            context_sentence="The character in the story was brave.",
            student_age=8,
        )
        assert reading_vocab.word == "character"


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_math_empty_problem(self):
        """Test handling empty problem."""
        reasoner = MathReasoner()
        result = reasoner.analyze_problem("", grade_level="3")
        assert "problem_type" in result

    def test_reading_very_short_passage(self):
        """Test handling very short passage."""
        reasoner = ReadingReasoner()
        result = reasoner.analyze_passage("Hi.", grade_level="1")
        assert "text_type" in result

    def test_science_complex_question(self):
        """Test handling complex science question."""
        reasoner = ScienceReasoner()
        guidance = reasoner.guide_experiment(
            experiment_question="What is the relationship between temperature and plant growth rate?",
            current_phase=ExperimentPhase.HYPOTHESIS,
            student_age=11,
            grade_level="6",
        )
        assert guidance.instructions is not None

    def test_social_studies_modern_topic(self):
        """Test handling modern social studies topic."""
        reasoner = SocialStudiesReasoner()
        result = reasoner.provide_context(
            topic="internet safety",
            domain=SocialStudiesDomain.CIVICS,
            grade_level="5",
            student_age=10,
        )
        assert "background" in result


# ============================================================================
# AGE-APPROPRIATENESS TESTS
# ============================================================================


class TestAgeAppropriateness:
    """Test age-appropriate responses for different grade levels."""

    def test_math_k_2_language(self):
        """Test math language for K-2 students."""
        reasoner = MathReasoner()
        steps = reasoner.generate_steps("What is 2 + 3?", grade_level="1", student_age=6)

        # Check that language is simple
        for step in steps:
            assert step.student_friendly is not None
            # Should be simple, encouraging language

    def test_reading_age_progression(self):
        """Test reading explanations scale with age."""
        reasoner = ReadingReasoner()

        # Younger student
        vocab_young = reasoner.explain_vocabulary(
            word="big", context_sentence="The big dog ran.", student_age=6
        )

        # Older student
        vocab_old = reasoner.explain_vocabulary(
            word="enormous", context_sentence="The enormous building towered above.", student_age=11
        )

        assert vocab_young.word is not None
        assert vocab_old.word is not None

    def test_science_experiment_guidance_by_age(self):
        """Test science guidance adapts to age."""
        reasoner = ScienceReasoner()

        # Younger student
        method_young = reasoner.explain_scientific_method(student_age=6)
        assert len(method_young["steps"]) >= 4

        # Older student
        method_old = reasoner.explain_scientific_method(student_age=11)
        assert len(method_old["steps"]) >= 4


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "math: tests for math reasoning module")
    config.addinivalue_line("markers", "reading: tests for reading reasoning module")
    config.addinivalue_line("markers", "science: tests for science reasoning module")
    config.addinivalue_line("markers", "social_studies: tests for social studies reasoning module")
    config.addinivalue_line("markers", "integration: integration tests across modules")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
