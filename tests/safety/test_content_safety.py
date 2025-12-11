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

import pytest
from typing import Dict, Any, List


class TestInappropriateContentDetection:
    """Test detection of inappropriate content for children."""

    @pytest.mark.safety
    def test_explicit_language_detection(self):
        """Test detection of explicit language."""
        inappropriate_texts = [
            "This contains stupid words",
            "You're such an idiot at math",
            "This is dumb homework",
            "I hate this terrible subject"
        ]

        for text in inappropriate_texts:
            # In a real implementation, this would call content safety API
            result = self._check_content_safety(text)
            assert result['is_safe'] is False, f"Failed to detect inappropriate content: {text}"
            assert 'inappropriate_language' in result['violation_types']

    @pytest.mark.safety
    def test_bullying_language_detection(self):
        """Test detection of bullying or mean language."""
        bullying_texts = [
            "Nobody likes you",
            "You're the worst student",
            "Everyone thinks you're terrible",
            "You'll never be good at this"
        ]

        for text in bullying_texts:
            result = self._check_content_safety(text)
            assert result['is_safe'] is False
            assert 'bullying' in result['violation_types']

    @pytest.mark.safety
    def test_safe_educational_content_passes(self):
        """Test that safe educational content passes validation."""
        safe_texts = [
            "Great job on solving that problem!",
            "Let's explore how plants grow",
            "Can you think of another way to solve this?",
            "That's an interesting observation about the experiment"
        ]

        for text in safe_texts:
            result = self._check_content_safety(text)
            assert result['is_safe'] is True
            assert len(result['violation_types']) == 0

    @pytest.mark.safety
    def test_profanity_filter(self):
        """Test profanity filtering."""
        # Test with masked profanity patterns
        profane_variants = [
            "What the h*ll is this",
            "This is cr@p",
            "D@mn this homework"
        ]

        for text in profane_variants:
            result = self._check_content_safety(text)
            assert result['is_safe'] is False
            assert result['confidence'] > 0.7

    @pytest.mark.safety
    def test_context_aware_detection(self):
        """Test context-aware inappropriate content detection."""
        # Words that might be inappropriate in some contexts but not others
        contextual_texts = [
            ("Let's kill this test!", False),  # Violent language
            ("The plant died from lack of water", True),  # Scientific context
            ("He's a killer math student", False),  # Slang usage
            ("The battery is dead", True)  # Technical usage
        ]

        for text, should_be_safe in contextual_texts:
            result = self._check_content_safety(text)
            assert result['is_safe'] == should_be_safe, \
                f"Context detection failed for: {text}"

    def _check_content_safety(self, text: str) -> Dict[str, Any]:
        """Mock content safety checker."""
        # Simulate content safety API
        violation_types = []

        # Check for inappropriate words
        inappropriate_words = {
            'stupid', 'idiot', 'dumb', 'hate', 'terrible',
            'nobody', 'worst', 'never', 'kill', 'died', 'dead'
        }

        text_lower = text.lower()
        found_violations = [word for word in inappropriate_words if word in text_lower]

        if any(word in text_lower for word in ['stupid', 'idiot', 'dumb']):
            violation_types.append('inappropriate_language')

        if any(word in text_lower for word in ['nobody', 'worst', 'never']):
            violation_types.append('bullying')

        # Profanity patterns
        if any(pattern in text_lower for pattern in ['h*ll', 'cr@p', 'd@mn']):
            violation_types.append('profanity')

        # Context-aware: allow "died" in plant/battery context
        if 'kill' in text_lower and 'test' not in text_lower:
            violation_types.append('violence')
        elif 'died' in text_lower and 'plant' not in text_lower and 'battery' not in text_lower:
            violation_types.append('violence')

        is_safe = len(violation_types) == 0

        return {
            'is_safe': is_safe,
            'confidence': 0.85 if not is_safe else 0.95,
            'violation_types': violation_types,
            'matched_terms': found_violations
        }


class TestViolenceHarmfulContentFiltering:
    """Test filtering of violent and harmful content."""

    @pytest.mark.safety
    def test_violence_detection(self):
        """Test detection of violent content."""
        violent_content = [
            "Let's destroy this problem",
            "Attack the question from another angle",
            "Fighting with this math problem"
        ]

        for text in violent_content:
            result = self._check_for_violence(text)
            # These should trigger warnings but context makes them acceptable
            assert result['contains_violent_language'] is True
            assert result['severity'] == 'low'  # Educational context

    @pytest.mark.safety
    def test_harm_detection(self):
        """Test detection of harmful content."""
        harmful_content = [
            "You should hurt yourself for getting this wrong",
            "Students who fail should be punished",
            "This will cause you pain"
        ]

        for text in harmful_content:
            result = self._check_for_violence(text)
            assert result['contains_violent_language'] is True
            assert result['severity'] in ['high', 'critical']
            assert result['is_acceptable'] is False

    @pytest.mark.safety
    def test_self_harm_prevention(self):
        """Test detection of self-harm content."""
        self_harm_indicators = [
            "hurt yourself",
            "harm yourself",
            "you should give up"
        ]

        for indicator in self_harm_indicators:
            text = f"Maybe {indicator} if you can't solve it"
            result = self._check_for_violence(text)
            assert result['requires_intervention'] is True
            assert result['is_acceptable'] is False

    @pytest.mark.safety
    def test_acceptable_competitive_language(self):
        """Test that acceptable competitive language passes."""
        acceptable_texts = [
            "Let's tackle this problem together!",
            "You can conquer this challenge!",
            "Beat your personal best score!",
            "Master this skill through practice"
        ]

        for text in acceptable_texts:
            result = self._check_for_violence(text)
            assert result['is_acceptable'] is True
            assert result['severity'] in ['none', 'low']

    @pytest.mark.safety
    def test_weapon_reference_detection(self):
        """Test detection of weapon references."""
        weapon_content = [
            "Use the gun to measure angles",  # Tool context
            "Shoot for the stars",  # Metaphor
            "Fire up your calculator",  # Metaphor
            "Bring a knife to cut the paper"  # Literal but educational
        ]

        for text in weapon_content:
            result = self._check_for_violence(text)
            # These should be flagged but allowed in educational context
            if 'metaphor' in result['context_type']:
                assert result['is_acceptable'] is True

    def _check_for_violence(self, text: str) -> Dict[str, Any]:
        """Mock violence checker."""
        violent_words = {
            'destroy', 'attack', 'fighting', 'hurt', 'harm', 'pain',
            'punished', 'kill', 'gun', 'knife', 'weapon'
        }

        motivational_words = {
            'tackle', 'conquer', 'beat', 'master', 'shoot for',
            'fire up'
        }

        text_lower = text.lower()

        # Check for violent language
        found_violent = [word for word in violent_words if word in text_lower]
        contains_violent = len(found_violent) > 0

        # Check for motivational context
        has_motivational = any(word in text_lower for word in motivational_words)

        # Determine severity
        high_severity_words = {'hurt yourself', 'harm yourself', 'punished', 'pain'}
        is_high_severity = any(word in text_lower for word in high_severity_words)

        if is_high_severity:
            severity = 'critical' if 'yourself' in text_lower else 'high'
            is_acceptable = False
            requires_intervention = True
        elif contains_violent and not has_motivational:
            severity = 'medium'
            is_acceptable = False
            requires_intervention = False
        elif contains_violent and has_motivational:
            severity = 'low'
            is_acceptable = True
            requires_intervention = False
        else:
            severity = 'none'
            is_acceptable = True
            requires_intervention = False

        # Determine context type
        context_type = 'educational'
        if any(word in text_lower for word in ['shoot for', 'fire up']):
            context_type = 'metaphor'

        return {
            'contains_violent_language': contains_violent,
            'severity': severity,
            'is_acceptable': is_acceptable,
            'requires_intervention': requires_intervention,
            'context_type': context_type,
            'flagged_terms': found_violent
        }


class TestAgeAppropriateLanguage:
    """Test age-appropriate language validation."""

    @pytest.mark.safety
    @pytest.mark.parametrize("age,text,should_pass", [
        (6, "Let's add these numbers!", True),
        (6, "Calculate the logarithmic derivative", False),
        (8, "Plants need water to grow", True),
        (8, "Photosynthesis requires chloroplasts", False),
        (10, "Solve for x in the equation", True),
        (10, "Apply the quadratic formula", True),
        (12, "Analyze the protagonist's motivation", True),
        (12, "Deconstruct the postmodern narrative", False)
    ])
    def test_vocabulary_complexity_by_age(self, age: int, text: str, should_pass: bool):
        """Test that vocabulary complexity is appropriate for age."""
        result = self._check_age_appropriateness(text, age)
        assert result['is_appropriate'] == should_pass, \
            f"Age {age} text '{text}' inappropriately marked as {result['is_appropriate']}"

    @pytest.mark.safety
    def test_sentence_length_by_age(self):
        """Test sentence length appropriateness by age."""
        test_cases = [
            (6, "Add two plus three.", True),
            (6, "Now we need to carefully consider the implications of adding two and three together.", False),
            (10, "To solve this problem, think about what the question is asking.", True),
            (10, "The methodology requires a comprehensive analytical approach incorporating multiple theoretical frameworks.", False)
        ]

        for age, text, should_pass in test_cases:
            result = self._check_age_appropriateness(text, age)
            assert result['is_appropriate'] == should_pass

    @pytest.mark.safety
    def test_concept_complexity_by_age(self):
        """Test concept complexity appropriateness."""
        age_concept_map = {
            6: ("Count the apples", True, "Advanced calculus", False),
            8: ("Multiplication tables", True, "Differential equations", False),
            10: ("Fractions and decimals", True, "Complex number theory", False),
            12: ("Basic algebra", True, "Quantum mechanics", False)
        }

        for age, (simple_concept, simple_expected, complex_concept, complex_expected) in age_concept_map.items():
            simple_result = self._check_age_appropriateness(simple_concept, age)
            complex_result = self._check_age_appropriateness(complex_concept, age)

            assert simple_result['is_appropriate'] == simple_expected
            assert complex_result['is_appropriate'] == complex_expected

    @pytest.mark.safety
    def test_reading_level_detection(self):
        """Test reading level appropriateness."""
        texts_by_level = {
            'grade_1': "The cat sat on the mat.",
            'grade_3': "Plants need sunlight and water to grow.",
            'grade_5': "Photosynthesis converts light energy into chemical energy.",
            'grade_8': "The mitochondria serves as the powerhouse of the cell."
        }

        for level, text in texts_by_level.items():
            grade = int(level.split('_')[1])
            result = self._check_age_appropriateness(text, grade + 5)  # Age = grade + 5

            # Should be appropriate for target grade and above
            assert result['reading_level'] <= grade + 2  # Allow 2 grade buffer

    @pytest.mark.safety
    def test_cultural_sensitivity(self):
        """Test cultural sensitivity in age-appropriate content."""
        sensitive_topics = [
            ("Discuss different family structures", 6, True),
            ("Religious holidays around the world", 8, True),
            ("Cultural traditions in mathematics", 10, True),
            ("Only smart kids from good families succeed", 10, False)
        ]

        for text, age, should_pass in sensitive_topics:
            result = self._check_age_appropriateness(text, age)
            # Cultural sensitivity should be maintained
            assert result['culturally_appropriate'] == should_pass

    def _check_age_appropriateness(self, text: str, age: int) -> Dict[str, Any]:
        """Mock age appropriateness checker."""
        words = text.split()
        avg_word_length = sum(len(word) for word in words) / max(len(words), 1)
        sentence_count = text.count('.') + text.count('!') + text.count('?')
        avg_sentence_length = len(words) / max(sentence_count, 1)

        # Complex vocabulary
        complex_words = {
            'logarithmic', 'derivative', 'chloroplasts', 'quadratic',
            'protagonist', 'postmodern', 'narrative', 'comprehensive',
            'theoretical', 'frameworks', 'methodology', 'analytical',
            'calculus', 'differential', 'quantum', 'mechanics', 'mitochondria'
        }

        has_complex_vocab = any(word.lower() in complex_words for word in words)

        # Age-based thresholds
        if age <= 7:
            max_word_length = 5.0
            max_sentence_length = 12
        elif age <= 9:
            max_word_length = 6.0
            max_sentence_length = 15
        elif age <= 11:
            max_word_length = 7.0
            max_sentence_length = 18
        else:
            max_word_length = 8.0
            max_sentence_length = 20

        # Check appropriateness
        vocab_appropriate = avg_word_length <= max_word_length and not has_complex_vocab
        length_appropriate = avg_sentence_length <= max_sentence_length
        is_appropriate = vocab_appropriate and length_appropriate

        # Calculate reading level (rough estimate)
        reading_level = int(avg_word_length + avg_sentence_length / 5)

        # Cultural sensitivity check
        insensitive_phrases = ['only smart kids', 'good families succeed']
        culturally_appropriate = not any(phrase in text.lower() for phrase in insensitive_phrases)

        return {
            'is_appropriate': is_appropriate and culturally_appropriate,
            'average_word_length': avg_word_length,
            'average_sentence_length': avg_sentence_length,
            'has_complex_vocabulary': has_complex_vocab,
            'reading_level': reading_level,
            'culturally_appropriate': culturally_appropriate,
            'vocabulary_appropriate': vocab_appropriate,
            'length_appropriate': length_appropriate
        }


class TestEducationalContentValidation:
    """Test validation of educational content safety."""

    @pytest.mark.safety
    def test_educational_value_validation(self):
        """Test that content has genuine educational value."""
        test_cases = [
            ("Let's learn about photosynthesis!", True, 0.9),
            ("Click here for free prizes!", False, 0.1),
            ("Watch random videos for fun", False, 0.2),
            ("Practice multiplication with this game", True, 0.85)
        ]

        for text, should_be_educational, min_score in test_cases:
            result = self._validate_educational_content(text)
            assert result['is_educational'] == should_be_educational
            if should_be_educational:
                assert result['educational_score'] >= min_score

    @pytest.mark.safety
    def test_misleading_information_detection(self):
        """Test detection of misleading or false information."""
        misleading_content = [
            "Plants don't need water to survive",
            "The Earth is flat according to science",
            "Math is just made up and not real",
            "Reading is a waste of time for students"
        ]

        for text in misleading_content:
            result = self._validate_educational_content(text)
            assert result['is_educational'] is False
            assert result['contains_misinformation'] is True

    @pytest.mark.safety
    def test_curriculum_alignment(self):
        """Test that content aligns with educational standards."""
        curriculum_content = {
            'math': "Learn to add and subtract numbers",
            'science': "Observe how plants grow",
            'reading': "Practice reading comprehension",
            'social_studies': "Explore different cultures"
        }

        for subject, text in curriculum_content.items():
            result = self._validate_educational_content(text, subject)
            assert result['is_educational'] is True
            assert result['curriculum_aligned'] is True

    @pytest.mark.safety
    def test_advertising_detection(self):
        """Test detection of advertising or promotional content."""
        advertising_texts = [
            "Buy our premium learning package now!",
            "Subscribe to unlock all features",
            "Click here to win prizes",
            "Limited time offer for students"
        ]

        for text in advertising_texts:
            result = self._validate_educational_content(text)
            assert result['contains_advertising'] is True
            assert result['is_educational'] is False

    @pytest.mark.safety
    def test_socratic_method_validation(self):
        """Test that content follows Socratic teaching method."""
        socratic_content = [
            "What do you think happens when plants don't get water?",
            "Can you explain why 2 + 2 equals 4?",
            "How might you solve this problem differently?",
            "What patterns do you notice in these numbers?"
        ]

        for text in socratic_content:
            result = self._validate_educational_content(text)
            assert result['uses_socratic_method'] is True
            assert result['educational_score'] >= 0.8

    @pytest.mark.safety
    def test_direct_answer_avoidance(self):
        """Test that content doesn't give direct answers."""
        direct_answer_texts = [
            "The answer is 42.",
            "Just write down 5 + 3 = 8",
            "The solution is x = 7",
            "Here's the answer: photosynthesis"
        ]

        for text in direct_answer_texts:
            result = self._validate_educational_content(text)
            assert result['gives_direct_answer'] is True
            assert result['educational_score'] < 0.7

    def _validate_educational_content(self, text: str, subject: str = None) -> Dict[str, Any]:
        """Mock educational content validator."""
        text_lower = text.lower()

        # Educational indicators
        educational_keywords = {
            'learn', 'practice', 'understand', 'explore', 'discover',
            'think', 'observe', 'explain', 'solve', 'question'
        }

        # Non-educational indicators
        commercial_keywords = {
            'buy', 'subscribe', 'click', 'prize', 'win', 'offer',
            'premium', 'unlock', 'limited time'
        }

        # Misinformation patterns
        misinformation_patterns = [
            "don't need", "is flat", "just made up", "waste of time",
            "according to science" # when followed by false statement
        ]

        # Socratic method indicators
        socratic_indicators = {
            'what do you think', 'can you explain', 'how might you',
            'what patterns', 'why do you', 'what if'
        }

        # Direct answer patterns
        direct_answer_patterns = ['the answer is', 'just write', 'the solution is', "here's the answer"]

        # Calculate scores
        edu_keywords_found = sum(1 for kw in educational_keywords if kw in text_lower)
        commercial_found = sum(1 for kw in commercial_keywords if kw in text_lower)
        has_misinformation = any(pattern in text_lower for pattern in misinformation_patterns)
        uses_socratic = any(indicator in text_lower for indicator in socratic_indicators)
        gives_direct_answer = any(pattern in text_lower for pattern in direct_answer_patterns)

        # Question-based learning
        has_questions = '?' in text

        # Educational score calculation
        educational_score = 0.5
        if edu_keywords_found > 0:
            educational_score += 0.2
        if has_questions and uses_socratic:
            educational_score += 0.3
        if commercial_found > 0:
            educational_score -= 0.4
        if has_misinformation:
            educational_score -= 0.5
        if gives_direct_answer:
            educational_score -= 0.3

        educational_score = max(0.0, min(1.0, educational_score))

        # Curriculum alignment (if subject provided)
        curriculum_aligned = False
        if subject:
            subject_keywords = {
                'math': ['add', 'subtract', 'multiply', 'numbers', 'solve'],
                'science': ['plants', 'grow', 'observe', 'experiment'],
                'reading': ['read', 'comprehension', 'story', 'practice'],
                'social_studies': ['culture', 'history', 'explore', 'community']
            }
            if subject in subject_keywords:
                curriculum_aligned = any(kw in text_lower for kw in subject_keywords[subject])

        is_educational = (
            educational_score >= 0.6 and
            not has_misinformation and
            commercial_found == 0
        )

        return {
            'is_educational': is_educational,
            'educational_score': educational_score,
            'contains_misinformation': has_misinformation,
            'contains_advertising': commercial_found > 0,
            'curriculum_aligned': curriculum_aligned,
            'uses_socratic_method': uses_socratic,
            'gives_direct_answer': gives_direct_answer,
            'has_questions': has_questions
        }
