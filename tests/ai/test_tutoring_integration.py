"""
Integration Tests for Tutoring LLM Infrastructure

Tests the full pipeline: TutorEngine -> PromptTemplateManager -> ResponseValidator

Run: pytest tests/ai/test_tutoring_integration.py -v
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ai.tutor_inference import (
    create_tutor_engine,
    TutorEngine,
    ResponseType,
    DifficultyLevel
)
from src.ai.prompt_templates import PromptTemplateManager, HintLevel
from src.ai.response_validator import ResponseValidator


class TestTutorEngineIntegration:
    """Integration tests for TutorEngine."""

    @pytest.fixture
    def engine(self):
        """Create a TutorEngine instance for testing."""
        return create_tutor_engine()

    @pytest.fixture
    def math_context(self):
        """Standard math context for testing."""
        return {
            'age': 8,
            'grade': '3',
            'subject': 'math',
            'concept_id': 'math_3_oa_001'
        }

    def test_engine_initialization(self, engine):
        """Test that engine initializes properly."""
        assert isinstance(engine, TutorEngine)
        assert engine.model_name == "llama-3.2-3B"
        assert engine.curriculum_manager is not None
        assert engine.template_manager is not None
        assert engine.validator is not None

    def test_generate_response_basic(self, engine, math_context):
        """Test basic response generation."""
        result = engine.generate_response(
            student_query="What is 5 times 3?",
            context=math_context
        )

        assert 'response' in result
        assert 'response_type' in result
        assert 'metadata' in result
        assert isinstance(result['response'], str)
        assert len(result['response']) > 0

    def test_generate_response_validation(self, engine, math_context):
        """Test that generated responses are validated."""
        result = engine.generate_response(
            student_query="What is multiplication?",
            context=math_context
        )

        # Check that validation metadata is present
        assert 'validation' in result['metadata']
        validation = result['metadata']['validation']
        assert 'is_valid' in validation
        assert 'overall_score' in validation

    def test_multi_turn_conversation(self, engine, math_context):
        """Test multi-turn conversation tracking."""
        queries = [
            "What is 5 times 3?",
            "How do I solve it?",
            "Is it 15?"
        ]

        for i, query in enumerate(queries, 1):
            result = engine.generate_response(
                student_query=query,
                context=math_context
            )

            # Check turn count increases
            assert result['metadata']['turn_count'] == i

        # Check conversation history
        assert len(engine.conversation_history) == 6  # 3 turns * 2 messages

    def test_guide_to_answer(self, engine, math_context):
        """Test multi-turn guidance functionality."""
        guidance = engine.guide_to_answer(
            problem_statement="What is 234 + 567?",
            student_attempts=["700", "790"],
            context=math_context
        )

        assert 'response' in guidance
        assert 'metadata' in guidance
        assert guidance['metadata']['hint_level'] is not None

    def test_hint_level_progression(self, engine, math_context):
        """Test that hint level progresses with attempts."""
        # First attempt
        result1 = engine.guide_to_answer(
            problem_statement="What is 42 - 17?",
            student_attempts=["35"],
            context=math_context
        )

        # Second attempt
        result2 = engine.guide_to_answer(
            problem_statement="What is 42 - 17?",
            student_attempts=["35", "29"],
            context=math_context
        )

        # Third+ attempt
        result3 = engine.guide_to_answer(
            problem_statement="What is 42 - 17?",
            student_attempts=["35", "29", "28", "26"],
            context=math_context
        )

        # Hint levels should progress
        assert result1['metadata']['hint_level'] <= result2['metadata']['hint_level']
        assert result2['metadata']['hint_level'] <= result3['metadata']['hint_level']

    def test_explain_concept(self, engine):
        """Test concept explanation generation."""
        explanation = engine.explain_concept(
            concept_id='math_3_oa_001',
            student_age=8,
            current_understanding="I know that multiplication is like adding"
        )

        assert 'response' in explanation
        assert len(explanation['response']) > 20  # Substantial explanation

    def test_check_understanding(self, engine, math_context):
        """Test comprehension checking."""
        check = engine.check_understanding(
            concept_id='math_3_oa_001',
            student_response="Multiplication is repeated addition",
            context=math_context
        )

        assert 'response' in check
        assert check['response_type'] == 'comprehension_check'

    def test_difficulty_adjustment(self, engine):
        """Test adaptive difficulty adjustment."""
        # High performance
        high_perf = {
            'correct_attempts': 8,
            'total_attempts': 10
        }
        difficulty_high = engine.adjust_difficulty(high_perf)
        assert difficulty_high.value >= DifficultyLevel.MODERATE.value

        # Low performance
        engine.current_difficulty = DifficultyLevel.MODERATE
        low_perf = {
            'correct_attempts': 2,
            'total_attempts': 10
        }
        difficulty_low = engine.adjust_difficulty(low_perf)
        assert difficulty_low.value <= DifficultyLevel.MODERATE.value

    def test_conversation_reset(self, engine, math_context):
        """Test conversation reset functionality."""
        # Generate some responses
        for _ in range(3):
            engine.generate_response(
                student_query="Test query",
                context=math_context
            )

        assert len(engine.conversation_history) > 0

        # Reset
        engine.reset_conversation()

        assert len(engine.conversation_history) == 0
        assert engine.hint_level == HintLevel.SUBTLE
        assert engine.current_difficulty == DifficultyLevel.MODERATE


class TestPromptTemplateIntegration:
    """Integration tests for PromptTemplateManager."""

    @pytest.fixture
    def manager(self):
        """Create a PromptTemplateManager instance."""
        return PromptTemplateManager()

    def test_subject_templates(self, manager):
        """Test that all subjects have templates."""
        subjects = ['math', 'reading', 'science', 'social_studies', 'general']
        template_types = ['socratic_question', 'hint', 'explanation', 'comprehension_check']

        for subject in subjects:
            for template_type in template_types:
                template = manager.get_template(subject, template_type)
                assert isinstance(template, str)
                assert len(template) > 0

    def test_age_appropriate_guidelines(self, manager):
        """Test age-appropriate language guidelines."""
        ages = [6, 7, 8, 9, 10, 11, 12, 13]

        for age in ages:
            guidelines = manager.get_age_appropriate_guidelines(age)
            assert isinstance(guidelines, str)
            assert len(guidelines) > 0
            assert 'LANGUAGE GUIDELINES' in guidelines

    def test_socratic_patterns(self, manager):
        """Test Socratic questioning patterns."""
        patterns = [
            'general', 'prior_knowledge', 'break_down',
            'visualization', 'reasoning'
        ]

        for pattern in patterns:
            question = manager.get_socratic_pattern(pattern)
            assert isinstance(question, str)
            assert len(question) > 0

    def test_hint_templates(self, manager):
        """Test hint progression templates."""
        for level in HintLevel:
            template = manager.get_hint_template(level)
            assert isinstance(template, str)
            assert '{' in template  # Has placeholders

    def test_encouragement_templates(self, manager):
        """Test encouragement phrases."""
        encouragements = manager.get_encouragement()
        assert isinstance(encouragements, list)
        assert len(encouragements) > 10
        assert all(isinstance(e, str) for e in encouragements)


class TestResponseValidatorIntegration:
    """Integration tests for ResponseValidator."""

    @pytest.fixture
    def validator(self):
        """Create a ResponseValidator instance."""
        return ResponseValidator()

    def test_good_response_validation(self, validator):
        """Test validation of a good Socratic response."""
        good_response = (
            "Great question! What do you already know about multiplication? "
            "Can you think of it as groups of things? "
            "Try drawing 5 groups with 3 items in each!"
        )

        result = validator.validate_response(
            response=good_response,
            age=8,
            subject='math'
        )

        assert result['is_valid'] is True
        assert result['overall_score'] > 0.7
        assert len(result['issues']) == 0

    def test_direct_answer_detection(self, validator):
        """Test detection of direct answers."""
        direct_answer = "The answer is 15. You multiply 5 times 3."

        result = validator.validate_response(
            response=direct_answer,
            age=8,
            subject='math'
        )

        assert result['is_valid'] is False
        assert any('direct answer' in issue.lower() for issue in result['issues'])
        assert result['scores']['socratic'] < 0.7

    def test_age_inappropriateness_detection(self, validator):
        """Test detection of age-inappropriate language."""
        complex_response = (
            "Multiplication represents the mathematical operation "
            "of iterative summation utilizing multiplicative factors "
            "to achieve computational efficiency."
        )

        result = validator.validate_response(
            response=complex_response,
            age=7,
            subject='math'
        )

        assert result['overall_score'] < 0.7
        assert len(result['warnings']) > 0

    def test_content_safety(self, validator):
        """Test content safety checking."""
        # Note: Using mild test case as we don't want actual inappropriate content
        unsafe_response = "You're stupid if you don't know this."

        result = validator.validate_response(
            response=unsafe_response,
            age=8,
            subject='math'
        )

        assert result['is_valid'] is False
        assert result['scores']['encouraging'] < 0.5

    def test_length_validation(self, validator):
        """Test response length validation."""
        # Too short
        too_short = "Good job."

        result_short = validator.validate_response(
            response=too_short,
            age=8,
            subject='math'
        )

        assert result_short['scores']['length'] < 1.0

        # Appropriate length
        appropriate = (
            "That's a great start! You're thinking in the right direction. "
            "What happens if you break this into smaller parts?"
        )

        result_good = validator.validate_response(
            response=appropriate,
            age=8,
            subject='math'
        )

        assert result_good['scores']['length'] >= 0.7


class TestFullPipeline:
    """End-to-end integration tests."""

    @pytest.fixture
    def engine(self):
        """Create a TutorEngine instance."""
        return create_tutor_engine()

    def test_full_tutoring_session(self, engine):
        """Test a complete tutoring session."""
        context = {
            'age': 8,
            'grade': '3',
            'subject': 'math',
            'concept_id': 'math_3_oa_001'
        }

        # Student asks question
        result1 = engine.generate_response(
            student_query="What is 5 times 3?",
            context=context
        )

        assert result1['metadata']['validation']['is_valid']

        # Student asks follow-up
        result2 = engine.generate_response(
            student_query="How do I figure it out?",
            context=context
        )

        assert result2['metadata']['turn_count'] == 2

        # Student makes attempt
        result3 = engine.generate_response(
            student_query="Is it 15?",
            context=context
        )

        assert len(engine.conversation_history) == 6  # 3 turns

    def test_different_subjects(self, engine):
        """Test that engine works with different subjects."""
        subjects = ['math', 'reading', 'science', 'social_studies']

        for subject in subjects:
            context = {
                'age': 9,
                'grade': '4',
                'subject': subject
            }

            result = engine.generate_response(
                student_query="I need help understanding this.",
                context=context
            )

            assert result['response']
            assert result['metadata']['validation']['is_valid']

    def test_age_range_coverage(self, engine):
        """Test that engine works for all age ranges."""
        ages = [6, 7, 8, 9, 10, 11, 12]

        for age in ages:
            context = {
                'age': age,
                'grade': str(age - 5),  # Approximate grade
                'subject': 'math'
            }

            result = engine.generate_response(
                student_query="I have a question.",
                context=context
            )

            assert result['response']
            # Note: In production, would validate age-appropriateness more thoroughly


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, '-v'])
