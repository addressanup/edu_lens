"""
Content Safety Tests for EduLens

Tests content safety validation, inappropriate content detection,
violence/harmful content filtering, age-appropriate language,
and educational content validation.

Test Coverage:
- Inappropriate content detection
- Violence/harmful content filtering
- Age-appropriate language validation
- Educational content safety
- Content moderation edge cases
"""

from typing import Any, Dict, List

import pytest

from src.ai.safety.content_safety import (
    AgeAppropriatenessValidator,
    ContentSafetyValidator,
    EducationalContentValidator,
)


class TestInappropriateContentDetection:
    """Test detection of inappropriate content for children."""

    @pytest.mark.safety
    def test_explicit_language_detection(self):
        """Test detection of explicit language."""
        inappropriate_texts = [
            "This contains stupid words",
            "You're such an idiot at math",
            "This is dumb homework",
            "I hate this terrible subject",
        ]

        for text in inappropriate_texts:
            # In a real implementation, this would call content safety API
            result = self._check_content_safety(text)
            assert result["is_safe"] is False, f"Failed to detect inappropriate content: {text}"
            assert "inappropriate_language" in result["violation_types"]

    @pytest.mark.safety
    def test_bullying_language_detection(self):
        """Test detection of bullying or mean language."""
        bullying_texts = [
            "Nobody likes you",
            "You're the worst student",
            "Everyone thinks you're terrible",
            "You'll never be good at this",
        ]

        for text in bullying_texts:
            result = self._check_content_safety(text)
            assert result["is_safe"] is False
            assert "bullying" in result["violation_types"]

    @pytest.mark.safety
    def test_safe_educational_content_passes(self):
        """Test that safe educational content passes validation."""
        safe_texts = [
            "Great job on solving that problem!",
            "Let's explore how plants grow",
            "Can you think of another way to solve this?",
            "That's an interesting observation about the experiment",
        ]

        for text in safe_texts:
            result = self._check_content_safety(text)
            assert result["is_safe"] is True
            assert len(result["violation_types"]) == 0

    @pytest.mark.safety
    def test_profanity_filter(self):
        """Test profanity filtering."""
        # Test with masked profanity patterns
        profane_variants = ["What the h*ll is this", "This is cr@p", "D@mn this homework"]

        for text in profane_variants:
            result = self._check_content_safety(text)
            assert result["is_safe"] is False
            assert result["confidence"] > 0.7

    @pytest.mark.safety
    def test_context_aware_detection(self):
        """Test context-aware inappropriate content detection."""
        # Words that might be inappropriate in some contexts but not others
        contextual_texts = [
            ("Let's kill this test!", False),  # Violent language
            ("The plant died from lack of water", True),  # Scientific context
            ("He's a killer math student", False),  # Slang usage
            ("The battery is dead", True),  # Technical usage
        ]

        for text, should_be_safe in contextual_texts:
            result = self._check_content_safety(text)
            assert result["is_safe"] == should_be_safe, f"Context detection failed for: {text}"

    def _check_content_safety(self, text: str) -> Dict[str, Any]:
        """Delegate to the product content-safety validator."""
        return ContentSafetyValidator().check_content(text)


class TestViolenceHarmfulContentFiltering:
    """Test filtering of violent and harmful content."""

    @pytest.mark.safety
    def test_violence_detection(self):
        """Test detection of violent content."""
        violent_content = [
            "Let's destroy this problem",
            "Attack the question from another angle",
            "Fighting with this math problem",
        ]

        for text in violent_content:
            result = self._check_for_violence(text)
            # These should trigger warnings but context makes them acceptable
            assert result["contains_violent_language"] is True
            assert result["severity"] == "low"  # Educational context

    @pytest.mark.safety
    def test_harm_detection(self):
        """Test detection of harmful content."""
        harmful_content = [
            "You should hurt yourself for getting this wrong",
            "Students who fail should be punished",
            "This will cause you pain",
        ]

        for text in harmful_content:
            result = self._check_for_violence(text)
            assert result["contains_violent_language"] is True
            assert result["severity"] in ["high", "critical"]
            assert result["is_acceptable"] is False

    @pytest.mark.safety
    def test_self_harm_prevention(self):
        """Test detection of self-harm content."""
        self_harm_indicators = ["hurt yourself", "harm yourself", "you should give up"]

        for indicator in self_harm_indicators:
            text = f"Maybe {indicator} if you can't solve it"
            result = self._check_for_violence(text)
            assert result["requires_intervention"] is True
            assert result["is_acceptable"] is False

    @pytest.mark.safety
    def test_acceptable_competitive_language(self):
        """Test that acceptable competitive language passes."""
        acceptable_texts = [
            "Let's tackle this problem together!",
            "You can conquer this challenge!",
            "Beat your personal best score!",
            "Master this skill through practice",
        ]

        for text in acceptable_texts:
            result = self._check_for_violence(text)
            assert result["is_acceptable"] is True
            assert result["severity"] in ["none", "low"]

    @pytest.mark.safety
    def test_weapon_reference_detection(self):
        """Test detection of weapon references."""
        weapon_content = [
            "Use the gun to measure angles",  # Tool context
            "Shoot for the stars",  # Metaphor
            "Fire up your calculator",  # Metaphor
            "Bring a knife to cut the paper",  # Literal but educational
        ]

        for text in weapon_content:
            result = self._check_for_violence(text)
            # These should be flagged but allowed in educational context
            if "metaphor" in result["context_type"]:
                assert result["is_acceptable"] is True

    def _check_for_violence(self, text: str) -> Dict[str, Any]:
        """Delegate to the product content-safety validator."""
        return ContentSafetyValidator().check_violence(text)


class TestAgeAppropriateLanguage:
    """Test age-appropriate language validation."""

    @pytest.mark.safety
    @pytest.mark.parametrize(
        "age,text,should_pass",
        [
            (6, "Let's add these numbers!", True),
            (6, "Calculate the logarithmic derivative", False),
            (8, "Plants need water to grow", True),
            (8, "Photosynthesis requires chloroplasts", False),
            (10, "Solve for x in the equation", True),
            (10, "Apply the quadratic formula", True),
            (12, "Analyze the protagonist's motivation", True),
            (12, "Deconstruct the postmodern narrative", False),
        ],
    )
    def test_vocabulary_complexity_by_age(self, age: int, text: str, should_pass: bool):
        """Test that vocabulary complexity is appropriate for age."""
        result = self._check_age_appropriateness(text, age)
        assert (
            result["is_appropriate"] == should_pass
        ), f"Age {age} text '{text}' inappropriately marked as {result['is_appropriate']}"

    @pytest.mark.safety
    def test_sentence_length_by_age(self):
        """Test sentence length appropriateness by age."""
        test_cases = [
            (6, "Add two plus three.", True),
            (
                6,
                "Now we need to carefully consider the implications of adding two and three together.",
                False,
            ),
            (10, "To solve this problem, think about what the question is asking.", True),
            (
                10,
                "The methodology requires a comprehensive analytical approach incorporating multiple theoretical frameworks.",
                False,
            ),
        ]

        for age, text, should_pass in test_cases:
            result = self._check_age_appropriateness(text, age)
            assert result["is_appropriate"] == should_pass

    @pytest.mark.safety
    def test_concept_complexity_by_age(self):
        """Test concept complexity appropriateness."""
        age_concept_map = {
            6: ("Count the apples", True, "Advanced calculus", False),
            8: ("Multiplication tables", True, "Differential equations", False),
            10: ("Fractions and decimals", True, "Complex number theory", False),
            12: ("Basic algebra", True, "Quantum mechanics", False),
        }

        for age, (
            simple_concept,
            simple_expected,
            complex_concept,
            complex_expected,
        ) in age_concept_map.items():
            simple_result = self._check_age_appropriateness(simple_concept, age)
            complex_result = self._check_age_appropriateness(complex_concept, age)

            assert simple_result["is_appropriate"] == simple_expected
            assert complex_result["is_appropriate"] == complex_expected

    @pytest.mark.safety
    def test_reading_level_detection(self):
        """Test reading level appropriateness."""
        texts_by_level = {
            "grade_1": "The cat sat on the mat.",
            "grade_3": "Plants need sunlight and water to grow.",
            "grade_5": "Photosynthesis converts light energy into chemical energy.",
            "grade_8": "The mitochondria serves as the powerhouse of the cell.",
        }

        for level, text in texts_by_level.items():
            grade = int(level.split("_")[1])
            result = self._check_age_appropriateness(text, grade + 5)  # Age = grade + 5

            # Should be appropriate for target grade and above
            assert result["reading_level"] <= grade + 2  # Allow 2 grade buffer

    @pytest.mark.safety
    def test_cultural_sensitivity(self):
        """Test cultural sensitivity in age-appropriate content."""
        sensitive_topics = [
            ("Discuss different family structures", 6, True),
            ("Religious holidays around the world", 8, True),
            ("Cultural traditions in mathematics", 10, True),
            ("Only smart kids from good families succeed", 10, False),
        ]

        for text, age, should_pass in sensitive_topics:
            result = self._check_age_appropriateness(text, age)
            # Cultural sensitivity should be maintained
            assert result["culturally_appropriate"] == should_pass

    def _check_age_appropriateness(self, text: str, age: int) -> Dict[str, Any]:
        """Delegate to the product age-appropriateness validator."""
        return AgeAppropriatenessValidator().check_language(text, age)


class TestEducationalContentValidation:
    """Test validation of educational content safety."""

    @pytest.mark.safety
    def test_educational_value_validation(self):
        """Test that content has genuine educational value."""
        test_cases = [
            ("Let's learn about photosynthesis!", True, 0.9),
            ("Click here for free prizes!", False, 0.1),
            ("Watch random videos for fun", False, 0.2),
            ("Practice multiplication with this game", True, 0.85),
        ]

        for text, should_be_educational, min_score in test_cases:
            result = self._validate_educational_content(text)
            assert result["is_educational"] == should_be_educational
            if should_be_educational:
                assert result["educational_score"] >= min_score

    @pytest.mark.safety
    def test_misleading_information_detection(self):
        """Test detection of misleading or false information."""
        misleading_content = [
            "Plants don't need water to survive",
            "The Earth is flat according to science",
            "Math is just made up and not real",
            "Reading is a waste of time for students",
        ]

        for text in misleading_content:
            result = self._validate_educational_content(text)
            assert result["is_educational"] is False
            assert result["contains_misinformation"] is True

    @pytest.mark.safety
    def test_curriculum_alignment(self):
        """Test that content aligns with educational standards."""
        curriculum_content = {
            "math": "Learn to add and subtract numbers",
            "science": "Observe how plants grow",
            "reading": "Practice reading comprehension",
            "social_studies": "Explore different cultures",
        }

        for subject, text in curriculum_content.items():
            result = self._validate_educational_content(text, subject)
            assert result["is_educational"] is True
            assert result["curriculum_aligned"] is True

    @pytest.mark.safety
    def test_advertising_detection(self):
        """Test detection of advertising or promotional content."""
        advertising_texts = [
            "Buy our premium learning package now!",
            "Subscribe to unlock all features",
            "Click here to win prizes",
            "Limited time offer for students",
        ]

        for text in advertising_texts:
            result = self._validate_educational_content(text)
            assert result["contains_advertising"] is True
            assert result["is_educational"] is False

    @pytest.mark.safety
    def test_socratic_method_validation(self):
        """Test that content follows Socratic teaching method."""
        socratic_content = [
            "What do you think happens when plants don't get water?",
            "Can you explain why 2 + 2 equals 4?",
            "How might you solve this problem differently?",
            "What patterns do you notice in these numbers?",
        ]

        for text in socratic_content:
            result = self._validate_educational_content(text)
            assert result["uses_socratic_method"] is True
            assert result["educational_score"] >= 0.8

    @pytest.mark.safety
    def test_direct_answer_avoidance(self):
        """Test that content doesn't give direct answers."""
        direct_answer_texts = [
            "The answer is 42.",
            "Just write down 5 + 3 = 8",
            "The solution is x = 7",
            "Here's the answer: photosynthesis",
        ]

        for text in direct_answer_texts:
            result = self._validate_educational_content(text)
            assert result["gives_direct_answer"] is True
            assert result["educational_score"] < 0.7

    def _validate_educational_content(self, text: str, subject: str = None) -> Dict[str, Any]:
        """Delegate to the product educational-content validator."""
        return EducationalContentValidator().validate(text, subject)
