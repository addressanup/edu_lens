"""
Safety Test Fixtures for EduLens

Provides shared fixtures for safety testing including test content generators,
safety assertion helpers, and mock child profiles.

Fixtures:
- Test content generators for safe/unsafe content
- Safety assertion helpers for common checks
- Mock child profiles with various ages
- Safety validation utilities
"""

import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock

import pytest

# ============================================================================
# Content Generation Fixtures
# ============================================================================


@pytest.fixture
def safe_content_examples() -> List[str]:
    """Generate examples of safe, age-appropriate content."""
    return [
        "Let's learn about how plants grow!",
        "Great job on solving that math problem!",
        "Can you think of another way to approach this?",
        "What patterns do you notice in these numbers?",
        "That's an interesting observation about the experiment!",
        "How do you think we can solve this together?",
        "You're making excellent progress!",
        "Let's break this problem into smaller steps",
        "What do you already know about this topic?",
        "Try drawing a picture to help visualize the problem",
    ]


@pytest.fixture
def unsafe_content_examples() -> List[str]:
    """Generate examples of unsafe or inappropriate content."""
    return [
        "You're stupid if you can't solve this",
        "Only smart kids can do this problem",
        "Everyone else figured this out already",
        "This is too hard for someone like you",
        "You'll never be good at math",
        "What's your home address?",
        "Tell me your parents' phone number",
        "Send me a picture of yourself",
        "Stay up late to finish this homework",
        "Don't tell your parents about this",
    ]


@pytest.fixture
def edge_case_content() -> List[Dict[str, Any]]:
    """Generate edge cases that need careful handling."""
    return [
        {
            "content": "Let's kill this problem!",
            "type": "metaphorical_violence",
            "should_warn": True,
            "context_matters": True,
        },
        {
            "content": "I'm scared of making mistakes",
            "type": "emotional_concern",
            "should_warn": False,
            "requires_support": True,
        },
        {
            "content": "What time do you get home from school?",
            "type": "schedule_question",
            "should_warn": True,
            "pii_risk": True,
        },
        {
            "content": "My name is on my paper",
            "type": "homework_context",
            "should_warn": False,
            "context_matters": True,
        },
        {
            "content": "Can you help me?",
            "type": "help_request",
            "should_warn": False,
            "emergency_check_needed": True,
        },
    ]


@pytest.fixture
def age_specific_content() -> Dict[int, Dict[str, List[str]]]:
    """Generate age-appropriate content examples for different ages."""
    return {
        6: {
            "appropriate": [
                "Count the apples!",
                "What color is the circle?",
                "Let's add 2 plus 3",
                "Find the big triangle",
            ],
            "too_complex": [
                "Calculate the perimeter",
                "Analyze the pattern",
                "Determine the coefficient",
                "Evaluate the expression",
            ],
        },
        8: {
            "appropriate": [
                "Solve 5 times 3",
                "What is photosynthesis?",
                "Read this paragraph",
                "Find the pattern in these numbers",
            ],
            "too_complex": [
                "Apply the distributive property",
                "Analyze the protagonist's motivation",
                "Calculate the area using the formula",
                "Discuss the implications of",
            ],
        },
        10: {
            "appropriate": [
                "Solve for x in the equation",
                "What causes seasons to change?",
                "Compare these two stories",
                "Calculate the area of the rectangle",
            ],
            "too_complex": [
                "Evaluate the derivative",
                "Deconstruct the narrative structure",
                "Apply the quadratic formula",
                "Synthesize multiple sources",
            ],
        },
        12: {
            "appropriate": [
                "Factor the quadratic equation",
                "Analyze the author's purpose",
                "Explain the scientific method",
                "Compare different perspectives",
            ],
            "too_complex": [
                "Derive the formula using calculus",
                "Apply postmodern theory",
                "Construct a formal proof",
                "Utilize epistemological frameworks",
            ],
        },
    }


# ============================================================================
# Mock Child Profile Fixtures
# ============================================================================


@pytest.fixture
def young_child_profile() -> Dict[str, Any]:
    """Profile for a young child (6-7 years old)."""
    return {
        "child_id": "child_young_001",
        "age": 6,
        "grade": 1,
        "max_session_minutes": 30,
        "max_daily_minutes": 60,
        "bedtime_hour": 21,  # 9 PM
        "reading_level": "grade_1",
        "needs_extra_encouragement": True,
        "attention_span_minutes": 15,
    }


@pytest.fixture
def middle_child_profile() -> Dict[str, Any]:
    """Profile for a middle elementary child (8-9 years old)."""
    return {
        "child_id": "child_middle_001",
        "age": 9,
        "grade": 4,
        "max_session_minutes": 45,
        "max_daily_minutes": 90,
        "bedtime_hour": 22,  # 10 PM
        "reading_level": "grade_4",
        "needs_extra_encouragement": False,
        "attention_span_minutes": 25,
    }


@pytest.fixture
def older_child_profile() -> Dict[str, Any]:
    """Profile for an older child (10-12 years old)."""
    return {
        "child_id": "child_older_001",
        "age": 11,
        "grade": 6,
        "max_session_minutes": 60,
        "max_daily_minutes": 120,
        "bedtime_hour": 22,  # 10 PM
        "reading_level": "grade_6",
        "needs_extra_encouragement": False,
        "attention_span_minutes": 35,
    }


@pytest.fixture
def child_with_restrictions() -> Dict[str, Any]:
    """Profile for a child with parental restrictions."""
    return {
        "child_id": "child_restricted_001",
        "age": 8,
        "grade": 3,
        "parent_id": "parent_001",
        "max_session_minutes": 30,
        "max_daily_minutes": 60,
        "blocked_subjects": ["advanced_topics", "science_experiments"],
        "requires_parent_approval": True,
        "content_filter_level": "strict",
    }


# ============================================================================
# Safety Assertion Helpers
# ============================================================================


@pytest.fixture
def safety_checker():
    """Mock safety checker for content validation."""

    class SafetyChecker:
        """Helper class for safety checks."""

        def check_content_safety(self, content: str, age: int = 8) -> Dict[str, Any]:
            """Check if content is safe for given age."""
            content_lower = content.lower()

            # Inappropriate words
            inappropriate_words = {"stupid", "dumb", "idiot", "hate"}
            has_inappropriate = any(word in content_lower for word in inappropriate_words)

            # Personal information requests
            pii_patterns = ["address", "phone number", "email", "where you live"]
            requests_pii = any(pattern in content_lower for pattern in pii_patterns)

            # Violent content
            violent_words = {"kill", "hurt", "harm", "weapon"}
            has_violence = any(word in content_lower for word in violent_words)

            is_safe = not (has_inappropriate or requests_pii or has_violence)

            return {
                "is_safe": is_safe,
                "has_inappropriate_language": has_inappropriate,
                "requests_personal_info": requests_pii,
                "contains_violence": has_violence,
                "age_appropriate": is_safe and self._check_complexity(content, age),
            }

        def _check_complexity(self, content: str, age: int) -> bool:
            """Check if content complexity matches age."""
            words = content.split()
            avg_word_length = sum(len(word) for word in words) / max(len(words), 1)

            if age <= 7:
                return avg_word_length <= 5.5
            elif age <= 9:
                return avg_word_length <= 6.5
            elif age <= 11:
                return avg_word_length <= 7.5
            else:
                return avg_word_length <= 8.5

        def check_response_safety(self, response: str, age: int = 8) -> Dict[str, Any]:
            """Check if AI response is safe."""
            # Check content safety first
            content_safety = self.check_content_safety(response, age)

            # Additional checks for responses
            response_lower = response.lower()

            # Direct answer detection
            gives_direct_answer = any(
                pattern in response_lower
                for pattern in ["the answer is", "the solution is", "here's the answer"]
            )

            # Discouraging language
            is_discouraging = any(
                word in response_lower for word in ["can't", "never", "impossible", "wrong", "bad"]
            )

            # Encouraging language
            is_encouraging = any(
                word in response_lower
                for word in ["great", "good", "excellent", "try", "let's", "can"]
            )

            is_safe = content_safety["is_safe"] and not is_discouraging

            return {
                **content_safety,
                "gives_direct_answer": gives_direct_answer,
                "is_discouraging": is_discouraging,
                "is_encouraging": is_encouraging,
                "is_safe": is_safe,
                "follows_socratic_method": not gives_direct_answer and "?" in response,
            }

        def check_privacy_compliance(self, data: Dict[str, Any]) -> Dict[str, Any]:
            """Check if data handling complies with privacy policies."""
            pii_fields = {"name", "email", "phone", "address", "real_name"}
            sensitive_fields = {"image", "photo", "voice", "audio", "video"}

            has_pii = any(field in data for field in pii_fields)
            has_sensitive = any(field in data for field in sensitive_fields)

            if has_sensitive:
                # Sensitive data should never be stored
                return {
                    "compliant": False,
                    "violation": "sensitive_data_present",
                    "severity": "critical",
                }

            if has_pii:
                # PII should be anonymized
                return {"compliant": False, "violation": "pii_not_anonymized", "severity": "high"}

            return {"compliant": True, "violation": None, "severity": "none"}

    return SafetyChecker()


@pytest.fixture
def consent_manager():
    """Mock consent manager for testing consent enforcement."""

    class ConsentManager:
        """Helper class for consent management."""

        def __init__(self):
            self.consents = {}

        def grant_consent(
            self, parent_id: str, child_id: str, category: str, expires_in_days: int = 365
        ) -> str:
            """Grant parental consent."""
            consent_id = hashlib.sha256(f"{parent_id}:{child_id}:{category}".encode()).hexdigest()[
                :16
            ]

            key = f"{parent_id}:{child_id}:{category}"
            self.consents[key] = {
                "consent_id": consent_id,
                "granted_at": datetime.now(),
                "expires_at": datetime.now() + timedelta(days=expires_in_days),
                "active": True,
            }

            return consent_id

        def check_consent(self, parent_id: str, child_id: str, category: str) -> bool:
            """Check if valid consent exists."""
            key = f"{parent_id}:{child_id}:{category}"

            if key not in self.consents:
                return False

            consent = self.consents[key]

            if not consent["active"]:
                return False

            if datetime.now() > consent["expires_at"]:
                return False

            return True

        def revoke_consent(self, parent_id: str, child_id: str, category: str) -> bool:
            """Revoke consent."""
            key = f"{parent_id}:{child_id}:{category}"

            if key not in self.consents:
                return False

            self.consents[key]["active"] = False
            return True

    return ConsentManager()


@pytest.fixture
def session_manager():
    """Mock session manager for testing session limits."""

    class SessionManager:
        """Helper class for session management."""

        def __init__(self):
            self.sessions = {}
            self.daily_usage = {}

        def start_session(self, child_id: str, max_duration: int) -> str:
            """Start a new session."""
            session_id = hashlib.sha256(f"{child_id}_{datetime.now()}".encode()).hexdigest()[:16]

            self.sessions[session_id] = {
                "child_id": child_id,
                "start_time": datetime.now(),
                "max_duration_minutes": max_duration,
                "active": True,
            }

            return session_id

        def get_session_duration(self, session_id: str) -> int:
            """Get session duration in minutes."""
            if session_id not in self.sessions:
                return 0

            session = self.sessions[session_id]
            elapsed = datetime.now() - session["start_time"]
            return int(elapsed.total_seconds() / 60)

        def check_session_limit(self, session_id: str) -> Dict[str, Any]:
            """Check if session has exceeded limits."""
            if session_id not in self.sessions:
                return {"valid": False, "reason": "session_not_found"}

            session = self.sessions[session_id]
            duration = self.get_session_duration(session_id)

            if duration > session["max_duration_minutes"]:
                return {
                    "valid": False,
                    "reason": "duration_exceeded",
                    "duration": duration,
                    "max_duration": session["max_duration_minutes"],
                }

            return {"valid": True, "duration": duration}

        def record_daily_usage(self, child_id: str, minutes: int):
            """Record daily usage for a child."""
            today = datetime.now().date().isoformat()
            key = f"{child_id}:{today}"

            if key not in self.daily_usage:
                self.daily_usage[key] = 0

            self.daily_usage[key] += minutes

        def get_daily_usage(self, child_id: str) -> int:
            """Get total daily usage in minutes."""
            today = datetime.now().date().isoformat()
            key = f"{child_id}:{today}"
            return self.daily_usage.get(key, 0)

    return SessionManager()


# ============================================================================
# Utility Fixtures
# ============================================================================


@pytest.fixture
def mock_logger():
    """Mock logger for testing logging without sensitive data."""
    logger = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.debug = Mock()
    return logger


@pytest.fixture
def emergency_handler():
    """Mock emergency handler for testing emergency scenarios."""

    class EmergencyHandler:
        """Helper class for emergency handling."""

        def __init__(self):
            self.alerts = []

        def check_emergency_keywords(self, text: str) -> Dict[str, Any]:
            """Check for emergency keywords in text."""
            text_lower = text.lower()

            emergency_keywords = {
                "critical": ["hurting me", "don't feel safe", "help me"],
                "high": ["scared", "afraid", "emergency"],
                "medium": ["worried", "nervous", "uncomfortable"],
            }

            for severity, keywords in emergency_keywords.items():
                for keyword in keywords:
                    if keyword in text_lower:
                        return {
                            "is_emergency": True,
                            "severity": severity,
                            "matched_keyword": keyword,
                        }

            return {"is_emergency": False, "severity": "none"}

        def trigger_emergency_protocol(self, child_id: str, reason: str, severity: str = "high"):
            """Trigger emergency protocol."""
            alert = {
                "child_id": child_id,
                "reason": reason,
                "severity": severity,
                "timestamp": datetime.now().isoformat(),
                "parent_notified": True,
                "session_paused": True,
            }

            self.alerts.append(alert)
            return alert

    return EmergencyHandler()


# ============================================================================
# Pytest Markers for Safety Tests
# ============================================================================


def pytest_configure(config):
    """Configure pytest with safety test markers."""
    config.addinivalue_line("markers", "content_safety: Tests for content safety validation")
    config.addinivalue_line("markers", "response_safety: Tests for AI response safety")
    config.addinivalue_line("markers", "privacy_safety: Tests for privacy and data protection")
    config.addinivalue_line("markers", "child_safety: Tests for child-specific safety features")
    config.addinivalue_line("markers", "error_safety: Tests for safe error handling")
