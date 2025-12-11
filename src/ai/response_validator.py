"""
Response Validator for EduLens AI Agent

This module provides validation for AI-generated educational responses to ensure they are:
- Age-appropriate for the target audience (6-12 years)
- Following Socratic method (not giving direct answers)
- Educational and encouraging
- Safe and appropriate content

Author: EduLens AI Team
Version: 1.0.0
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of response validation."""
    is_valid: bool
    score: float  # 0.0 to 1.0
    issues: List[str]
    warnings: List[str]
    suggestions: List[str]


class ResponseValidator:
    """
    Validates AI-generated educational responses for quality and appropriateness.

    Checks for:
    - Age-appropriate language and content
    - Socratic method adherence (no direct answers)
    - Educational value
    - Encouraging and supportive tone
    - Content safety
    """

    def __init__(self):
        """Initialize the ResponseValidator with validation rules."""
        self.inappropriate_words = self._load_inappropriate_words()
        self.direct_answer_patterns = self._load_direct_answer_patterns()
        self.educational_indicators = self._load_educational_indicators()
        self.encouragement_words = self._load_encouragement_words()

    def validate_response(
        self,
        response: str,
        age: int,
        subject: str,
        expected_type: Optional[str] = None
    ) -> Dict:
        """
        Validate an educational response comprehensively.

        Args:
            response: The generated response text
            age: Student's age (6-12)
            subject: Subject area
            expected_type: Expected response type (optional)

        Returns:
            Dictionary with validation results
        """
        issues = []
        warnings = []
        suggestions = []
        scores = {}

        # Run all validation checks
        scores['age_appropriate'] = self._check_age_appropriateness(
            response, age, issues, warnings
        )

        scores['socratic'] = self._check_socratic_method(
            response, issues, warnings
        )

        scores['educational'] = self._check_educational_value(
            response, issues, suggestions
        )

        scores['encouraging'] = self._check_encouraging_tone(
            response, warnings, suggestions
        )

        scores['safe'] = self._check_content_safety(
            response, issues
        )

        scores['length'] = self._check_length_appropriateness(
            response, age, warnings
        )

        # Calculate overall score
        overall_score = sum(scores.values()) / len(scores)

        # Determine if valid (threshold: 0.7)
        is_valid = overall_score >= 0.7 and len(issues) == 0

        return {
            'is_valid': is_valid,
            'overall_score': overall_score,
            'scores': scores,
            'issues': issues,  # Critical problems
            'warnings': warnings,  # Minor concerns
            'suggestions': suggestions  # Improvement recommendations
        }

    def _check_age_appropriateness(
        self,
        response: str,
        age: int,
        issues: List[str],
        warnings: List[str]
    ) -> float:
        """Check if language is age-appropriate."""
        score = 1.0

        # Check vocabulary complexity
        words = response.split()
        avg_word_length = sum(len(word) for word in words) / max(len(words), 1)

        # Age-based thresholds
        if age <= 7:
            max_avg_length = 5.0
            max_sentence_words = 12
        elif age <= 9:
            max_avg_length = 6.0
            max_sentence_words = 15
        elif age <= 11:
            max_avg_length = 7.0
            max_sentence_words = 18
        else:
            max_avg_length = 8.0
            max_sentence_words = 20

        # Check average word length
        if avg_word_length > max_avg_length + 1.5:
            score -= 0.3
            warnings.append(
                f"Words may be too complex for age {age} "
                f"(avg length: {avg_word_length:.1f}, expected: {max_avg_length})"
            )

        # Check sentence length
        sentences = re.split(r'[.!?]+', response)
        for sentence in sentences:
            sentence_words = len(sentence.split())
            if sentence_words > max_sentence_words * 1.5:
                score -= 0.2
                warnings.append(
                    f"Sentence too long for age {age} ({sentence_words} words)"
                )
                break

        # Check for overly complex words
        complex_words = self._find_complex_words(response, age)
        if complex_words:
            score -= min(0.3, len(complex_words) * 0.1)
            warnings.append(
                f"Complex words for age {age}: {', '.join(list(complex_words)[:3])}"
            )

        # Check for inappropriate content
        if self._contains_inappropriate_content(response):
            score = 0.0
            issues.append("Response contains inappropriate content")

        return max(0.0, score)

    def _check_socratic_method(
        self,
        response: str,
        issues: List[str],
        warnings: List[str]
    ) -> float:
        """Check if response follows Socratic method (asking vs. telling)."""
        score = 1.0

        # Count questions vs. statements
        question_marks = response.count('?')
        sentences = len(re.findall(r'[.!?]+', response))

        if sentences == 0:
            return 0.5

        question_ratio = question_marks / sentences

        # Check for direct answer patterns
        direct_answer_count = self._count_direct_answers(response)

        if direct_answer_count > 0:
            score -= direct_answer_count * 0.3
            issues.append(
                f"Response appears to give {direct_answer_count} direct answer(s)"
            )

        # Socratic responses should have questions
        if question_ratio < 0.2:
            score -= 0.3
            warnings.append(
                "Response could include more guiding questions (Socratic method)"
            )

        # Check for guidance phrases
        if not self._has_guidance_phrases(response):
            score -= 0.2
            warnings.append("Response could include more guidance phrases")

        return max(0.0, score)

    def _check_educational_value(
        self,
        response: str,
        issues: List[str],
        suggestions: List[str]
    ) -> float:
        """Check if response has educational value."""
        score = 1.0

        # Check for educational indicators
        edu_indicators = self._count_educational_indicators(response)

        if edu_indicators == 0:
            score -= 0.4
            suggestions.append("Include educational concepts or strategies")

        # Check if response is too vague
        if self._is_too_vague(response):
            score -= 0.3
            suggestions.append("Be more specific with guidance or examples")

        # Check for concept building
        if not self._builds_on_prior_knowledge(response):
            score -= 0.2
            suggestions.append("Connect to prior knowledge or simpler concepts")

        # Very short responses may lack depth
        if len(response.split()) < 15:
            score -= 0.2
            suggestions.append("Provide more educational depth")

        return max(0.0, score)

    def _check_encouraging_tone(
        self,
        response: str,
        warnings: List[str],
        suggestions: List[str]
    ) -> float:
        """Check if response is encouraging and supportive."""
        score = 1.0

        # Check for encouragement words/phrases
        encouragement_count = self._count_encouragement_phrases(response)

        if encouragement_count == 0:
            score -= 0.3
            suggestions.append("Add encouraging language to support the student")

        # Check for negative words
        negative_words = self._find_negative_words(response)
        if negative_words:
            score -= len(negative_words) * 0.2
            warnings.append(
                f"Response contains potentially discouraging words: "
                f"{', '.join(list(negative_words)[:3])}"
            )

        # Check for growth mindset language
        if not self._has_growth_mindset_language(response):
            score -= 0.1
            suggestions.append("Consider adding growth mindset encouragement")

        return max(0.0, score)

    def _check_content_safety(
        self,
        response: str,
        issues: List[str]
    ) -> float:
        """Check for content safety issues."""
        score = 1.0

        # Check for inappropriate words
        inappropriate = self._find_inappropriate_words(response)
        if inappropriate:
            score = 0.0
            issues.append(
                f"Response contains inappropriate words: {', '.join(inappropriate)}"
            )

        # Check for personal information requests
        if self._requests_personal_info(response):
            score = 0.0
            issues.append("Response requests personal information")

        # Check for external links or contact info
        if self._contains_links_or_contact(response):
            score = 0.0
            issues.append("Response contains links or contact information")

        return score

    def _check_length_appropriateness(
        self,
        response: str,
        age: int,
        warnings: List[str]
    ) -> float:
        """Check if response length is appropriate."""
        score = 1.0
        word_count = len(response.split())

        # Age-based length guidelines
        if age <= 7:
            min_words, max_words = 15, 60
        elif age <= 9:
            min_words, max_words = 20, 100
        elif age <= 11:
            min_words, max_words = 25, 150
        else:
            min_words, max_words = 30, 200

        if word_count < min_words:
            score -= 0.3
            warnings.append(f"Response may be too short ({word_count} words)")

        if word_count > max_words:
            score -= 0.3
            warnings.append(f"Response may be too long ({word_count} words)")

        return max(0.0, score)

    # Helper methods for validation checks

    def _find_complex_words(self, text: str, age: int) -> Set[str]:
        """Find words that may be too complex for the age."""
        # Words that are too long or complex for young students
        age_thresholds = {
            7: 8,   # 6-7 year olds
            9: 10,  # 8-9 year olds
            11: 12, # 10-11 year olds
            12: 14  # 12+ year olds
        }

        threshold = age_thresholds.get(
            min(age, 12) if age >= 7 else 7,
            8
        )

        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        complex_words = {word for word in words if len(word) > threshold}

        # Remove common long words that are still simple
        simple_long_words = {
            'because', 'something', 'everyone', 'everything',
            'anything', 'together', 'another', 'important',
            'different', 'understand', 'remember'
        }

        return complex_words - simple_long_words

    def _count_direct_answers(self, text: str) -> int:
        """Count instances of direct answer patterns."""
        count = 0

        for pattern in self.direct_answer_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                count += 1

        return count

    def _has_guidance_phrases(self, text: str) -> bool:
        """Check if text contains guidance phrases."""
        guidance_phrases = [
            'think about', 'what if', 'can you', 'try',
            'notice', 'look at', 'consider', 'imagine',
            'let\'s', 'how about', 'what do you'
        ]

        text_lower = text.lower()
        return any(phrase in text_lower for phrase in guidance_phrases)

    def _count_educational_indicators(self, text: str) -> int:
        """Count educational concept indicators."""
        count = 0
        text_lower = text.lower()

        for indicator in self.educational_indicators:
            if indicator in text_lower:
                count += 1

        return count

    def _is_too_vague(self, text: str) -> bool:
        """Check if response is too vague."""
        vague_only_patterns = [
            r'^(good|great|nice)\s+(job|work|question)[.!]?$',
            r'^(that\'s|thats)\s+(right|correct|good)[.!]?$',
            r'^(keep|keep up|continue)\s+.{0,20}[.!]?$'
        ]

        text_stripped = text.strip()
        for pattern in vague_only_patterns:
            if re.match(pattern, text_stripped, re.IGNORECASE):
                return True

        # Check for very generic responses
        if len(text.split()) < 10 and not any(
            word in text.lower() for word in
            ['why', 'how', 'what', 'where', 'when', 'because', 'try']
        ):
            return True

        return False

    def _builds_on_prior_knowledge(self, text: str) -> bool:
        """Check if response builds on prior knowledge."""
        prior_knowledge_phrases = [
            'remember', 'you know', 'learned', 'before',
            'like when', 'similar to', 'just like',
            'you\'ve seen', 'already know'
        ]

        text_lower = text.lower()
        return any(phrase in text_lower for phrase in prior_knowledge_phrases)

    def _count_encouragement_phrases(self, text: str) -> int:
        """Count encouraging phrases in text."""
        count = 0
        text_lower = text.lower()

        for word in self.encouragement_words:
            if word in text_lower:
                count += 1

        return count

    def _find_negative_words(self, text: str) -> Set[str]:
        """Find potentially discouraging words."""
        negative_words = {
            'wrong', 'incorrect', 'bad', 'fail', 'failure',
            'can\'t', 'cannot', 'unable', 'impossible',
            'never', 'always', 'stupid', 'dumb'
        }

        words = set(re.findall(r'\b[a-z\']+\b', text.lower()))
        return words & negative_words

    def _has_growth_mindset_language(self, text: str) -> bool:
        """Check for growth mindset language."""
        growth_phrases = [
            'yet', 'learn', 'grow', 'practice', 'improve',
            'try again', 'keep going', 'you\'re getting',
            'progress', 'discover', 'figure out'
        ]

        text_lower = text.lower()
        return any(phrase in text_lower for phrase in growth_phrases)

    def _contains_inappropriate_content(self, text: str) -> bool:
        """Check for inappropriate content."""
        return len(self._find_inappropriate_words(text)) > 0

    def _find_inappropriate_words(self, text: str) -> List[str]:
        """Find inappropriate words in text."""
        words = set(re.findall(r'\b[a-z]+\b', text.lower()))
        return list(words & self.inappropriate_words)

    def _requests_personal_info(self, text: str) -> bool:
        """Check if response requests personal information."""
        personal_info_patterns = [
            r'what\'?s? your (name|address|phone|email)',
            r'where do you live',
            r'tell me your (full name|address)',
            r'what school do you go to'
        ]

        text_lower = text.lower()
        return any(
            re.search(pattern, text_lower)
            for pattern in personal_info_patterns
        )

    def _contains_links_or_contact(self, text: str) -> bool:
        """Check for URLs, emails, or phone numbers."""
        patterns = [
            r'http[s]?://',
            r'www\.',
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        ]

        return any(re.search(pattern, text) for pattern in patterns)

    def _load_inappropriate_words(self) -> Set[str]:
        """Load set of inappropriate words."""
        # Basic set - in production, this would be more comprehensive
        return {
            'stupid', 'dumb', 'idiot', 'hate', 'kill',
            'die', 'death', 'violence', 'weapon'
            # Note: Real implementation would have comprehensive list
        }

    def _load_direct_answer_patterns(self) -> List[str]:
        """Load patterns that indicate direct answers."""
        return [
            r'the answer is \d+',
            r'it equals \d+',
            r'the solution is',
            r'^\d+\s*[+\-*/]\s*\d+\s*=\s*\d+',  # "5 + 3 = 8"
            r'you (should|need to|must) do',
            r'the correct answer',
            r'here\'?s? the answer'
        ]

    def _load_educational_indicators(self) -> List[str]:
        """Load educational concept indicators."""
        return [
            'because', 'strategy', 'method', 'pattern', 'concept',
            'example', 'step', 'process', 'understand', 'learn',
            'discover', 'notice', 'observe', 'compare', 'connect',
            'break down', 'think about', 'reason', 'explain'
        ]

    def _load_encouragement_words(self) -> List[str]:
        """Load encouraging words and phrases."""
        return [
            'great', 'good', 'excellent', 'wonderful', 'awesome',
            'nice', 'super', 'fantastic', 'amazing', 'brilliant',
            'love', 'like', 'proud', 'impressive', 'terrific',
            'you\'re', 'you can', 'well done', 'keep going',
            'keep it up', 'way to go', 'that\'s right'
        ]


def validate_educational_response(
    response: str,
    age: int,
    subject: str
) -> Dict:
    """
    Convenience function to validate a response.

    Args:
        response: Generated response text
        age: Student age
        subject: Subject area

    Returns:
        Validation result dictionary
    """
    validator = ResponseValidator()
    return validator.validate_response(response, age, subject)


# Example usage and testing
if __name__ == "__main__":
    validator = ResponseValidator()

    print("=== EduLens Response Validator ===\n")

    # Example 1: Good Socratic response
    print("--- Example 1: Good Response ---")
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

    print(f"Response: {good_response}")
    print(f"Valid: {result['is_valid']}")
    print(f"Score: {result['overall_score']:.2f}")
    print(f"Issues: {result['issues'] or 'None'}")
    print(f"Warnings: {result['warnings'] or 'None'}")
    print()

    # Example 2: Direct answer (bad)
    print("--- Example 2: Direct Answer (Invalid) ---")
    bad_response = "The answer is 15. You multiply 5 times 3."

    result = validator.validate_response(
        response=bad_response,
        age=8,
        subject='math'
    )

    print(f"Response: {bad_response}")
    print(f"Valid: {result['is_valid']}")
    print(f"Score: {result['overall_score']:.2f}")
    print(f"Issues: {result['issues']}")
    print()

    # Example 3: Too complex language
    print("--- Example 3: Too Complex for Age ---")
    complex_response = (
        "Multiplication represents the mathematical operation "
        "of iterative summation utilizing multiplicative factors."
    )

    result = validator.validate_response(
        response=complex_response,
        age=7,
        subject='math'
    )

    print(f"Response: {complex_response}")
    print(f"Valid: {result['is_valid']}")
    print(f"Score: {result['overall_score']:.2f}")
    print(f"Warnings: {result['warnings']}")
    print()

    # Example 4: Good encouraging response
    print("--- Example 4: Encouraging Response ---")
    encouraging_response = (
        "I can see you're really thinking hard about this! "
        "You're on the right track. What if you tried breaking "
        "the problem into smaller parts? You've got this!"
    )

    result = validator.validate_response(
        response=encouraging_response,
        age=9,
        subject='math'
    )

    print(f"Response: {encouraging_response}")
    print(f"Valid: {result['is_valid']}")
    print(f"Score: {result['overall_score']:.2f}")
    print(f"Encouragement Score: {result['scores']['encouraging']:.2f}")
    print()

    print("=== Validator Ready ===")
