"""
Child-safety validators for EduLens.

Single source of truth for the safety semantics asserted by
``tests/safety/*``: content screening, violence/self-harm detection,
age-appropriateness, response safety, PII-request prevention, interaction
tone, and session/bedtime policy.

These are deterministic, dependency-free heuristics suitable for on-device
use. They are a safety *layer* (defense in depth), not a complete
moderation solution; the LLM system prompts and parental controls provide
additional layers.

Author: EduLens AI Team
Version: 1.1.0
"""

from __future__ import annotations

import hashlib
import re
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Content screening (inappropriate language, bullying, profanity, violence)
# ---------------------------------------------------------------------------

_INAPPROPRIATE_WORDS = {"stupid", "idiot", "dumb", "hate", "terrible"}

_BULLYING_WORDS = {"nobody", "worst", "never", "everyone thinks"}
_BULLYING_PHRASES = (
    "nobody likes you",
    "you'll never",
    "you will never",
    "everyone thinks you're",
    "worst student",
)

_PROFANITY_PATTERNS = ("h*ll", "cr@p", "d@mn", "sh*t", "f*ck")

_VIOLENT_WORDS = {
    "destroy",
    "attack",
    "fighting",
    "hurt",
    "harm",
    "pain",
    "punished",
    "kill",
    "killer",
    "gun",
    "knife",
    "weapon",
}

_MOTIVATIONAL_WORDS = {"tackle", "conquer", "beat", "master", "shoot for", "fire up"}

_SELF_HARM_PHRASES = ("hurt yourself", "harm yourself", "give up", "you should give up")

# Harm directed at the child without self-harm framing is still high severity.
_HARMFUL_TARGET_WORDS = ("punished", "pain")

_EDUCATIONAL_CONTEXT_MARKERS = (
    "problem",
    "question",
    "math",
    "test",
    "homework",
    "study",
    "learn",
    "practice",
    "lesson",
)

_SAFE_DEATH_CONTEXTS = ("plant", "battery", "phone", "laptop", "car")


class ContentSafetyValidator:
    """Screens text for content unsafe for children aged 6-12."""

    def check_content(self, text: str) -> Dict[str, Any]:
        """Screen arbitrary text. Returns is_safe, violation_types, confidence."""
        text_lower = (text or "").lower()
        violation_types: List[str] = []

        if any(w in text_lower for w in _INAPPROPRIATE_WORDS):
            violation_types.append("inappropriate_language")

        if any(w in text_lower for w in _BULLYING_WORDS) or any(
            p in text_lower for p in _BULLYING_PHRASES
        ):
            violation_types.append("bullying")

        if any(p in text_lower for p in _PROFANITY_PATTERNS):
            violation_types.append("profanity")

        # "kill"/"killer" is unsafe in child-facing text even in slang
        # ("let's kill this test", "killer math student").
        if "kill" in text_lower or "killer" in text_lower:
            violation_types.append("violence")
        elif any(w in text_lower for w in ("died", "dead")):
            # Death is acceptable only in clearly technical/scientific contexts.
            if not any(ctx in text_lower for ctx in _SAFE_DEATH_CONTEXTS):
                violation_types.append("violence")

        matched = sorted(
            w for w in (_INAPPROPRIATE_WORDS | _VIOLENT_WORDS) if w in text_lower
        )
        is_safe = len(violation_types) == 0
        return {
            "is_safe": is_safe,
            "confidence": 0.95 if is_safe else 0.85,
            "violation_types": violation_types,
            "matched_terms": matched,
        }

    def check_violence(self, text: str) -> Dict[str, Any]:
        """Detect violent language with severity, acceptability and context."""
        text_lower = (text or "").lower()

        found_violent = [w for w in _VIOLENT_WORDS if w in text_lower]
        contains_violent = len(found_violent) > 0
        has_motivational = any(w in text_lower for w in _MOTIVATIONAL_WORDS)
        has_educational_context = any(m in text_lower for m in _EDUCATIONAL_CONTEXT_MARKERS)
        is_self_harm = any(p in text_lower for p in _SELF_HARM_PHRASES)

        if is_self_harm:
            severity = "critical" if "yourself" in text_lower else "high"
            is_acceptable = False
            requires_intervention = True
        elif contains_violent and any(w in text_lower for w in _HARMFUL_TARGET_WORDS):
            # Harm directed at the student ("you should be punished",
            # "this will cause you pain").
            severity = "high"
            is_acceptable = False
            requires_intervention = False
        elif contains_violent and (has_motivational or has_educational_context):
            # Metaphorical/competitive usage in a learning context.
            severity = "low"
            is_acceptable = True
            requires_intervention = False
        elif contains_violent:
            severity = "medium"
            is_acceptable = False
            requires_intervention = False
        else:
            severity = "none"
            is_acceptable = True
            requires_intervention = False

        context_type = "educational"
        if any(w in text_lower for w in ("shoot for", "fire up")):
            context_type = "metaphor"

        return {
            "contains_violent_language": contains_violent,
            "severity": severity,
            "is_acceptable": is_acceptable,
            "requires_intervention": requires_intervention,
            "context_type": context_type,
            "flagged_terms": found_violent,
        }


# ---------------------------------------------------------------------------
# Age-appropriateness (vocabulary bands, reading level, tone by age)
# ---------------------------------------------------------------------------

# Vocabulary that is too advanced for elementary children even at 12.
_ADVANCED_WORDS = {
    "logarithmic",
    "derivative",
    "chloroplasts",
    "postmodern",
    "comprehensive",
    "theoretical",
    "frameworks",
    "methodology",
    "analytical",
    "calculus",
    "differential",
    "quantum",
    "mechanics",
    "mitochondria",
    "deconstruct",
    "epistemological",
    "paradigm",
    "metacognitive",
    "computational",
    "satisfactorily",
    "multiplicative",
    "proficiency",
    "parameters",
    "utilize",
}

# Vocabulary that becomes appropriate from age 10.
_MID_BAND_WORDS = {"quadratic", "protagonist", "narrative", "coefficient", "inverse"}

_ADVANCED_PHRASES = (
    "number theory",
    "quantum mechanics",
    "differential equations",
    "advanced calculus",
    "chain rule",
)

_CULTURALLY_INSENSITIVE_PHRASES = ("only smart kids", "good families succeed")

# Common curriculum words that are long but age-appropriate; excluded from the
# average word-length penalty so "multiplication tables" isn't flagged at age 8.
_COMMON_CURRICULUM_WORDS = {
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "photosynthesis",
    "temperature",
    "sunlight",
    "butterfly",
}

_CONDESCENDING_PHRASES = (
    "even a baby",
    "why don't you understand",
    "everyone else",
    "should be obvious",
)

_SUPPORTIVE_PHRASES = (
    "okay to make mistakes",
    "take your time",
    "you're doing",
    "keep trying",
    "break this into",
    "let's",
)

_ENCOURAGING_PHRASES = (
    "getting this",
    "nice work",
    "well done",
    "strong problem-solving",
    "proud of you",
    "keep it up",
    "you've got this",
)

_ENTHUSIASM_WORDS = {
    "wow",
    "amazing",
    "great",
    "awesome",
    "excellent",
    "fantastic",
    "wonderful",
    "nice",
    "good",
}


class AgeAppropriatenessValidator:
    """Validates language complexity and tone against a child's age."""

    def _max_word_length(self, age: int) -> float:
        if age <= 7:
            return 5.5
        if age <= 9:
            return 6.5
        if age <= 11:
            return 7.5
        return 8.5

    def _max_sentence_length(self, age: int) -> int:
        if age <= 7:
            return 12
        if age <= 9:
            return 15
        if age <= 11:
            return 18
        return 20

    @staticmethod
    def _average_word_length(text: str) -> float:
        """Average word length, ignoring punctuation and whitelisted
        curriculum words that are long but age-appropriate."""
        words = [w.strip(".,!?;:'\"-()").lower() for w in text.split()]
        words = [w for w in words if w]
        content = [w for w in words if w not in _COMMON_CURRICULUM_WORDS] or words
        return sum(len(w) for w in content) / max(len(content), 1)

    def _has_advanced_vocabulary(self, text_lower: str, age: int) -> bool:
        if any(p in text_lower for p in _ADVANCED_PHRASES):
            return True
        words = text_lower.split()
        for word in words:
            if word in _ADVANCED_WORDS:
                return True
            if age < 10 and word in _MID_BAND_WORDS:
                return True
        return False

    def check_language(self, text: str, age: int) -> Dict[str, Any]:
        """Check whether explanatory text is age-appropriate."""
        text_lower = (text or "").lower()
        words = text.split()
        avg_word_length = self._average_word_length(text)
        sentence_count = text.count(".") + text.count("!") + text.count("?")
        avg_sentence_length = len(words) / max(sentence_count, 1)

        vocab_appropriate = (
            avg_word_length <= self._max_word_length(age)
            and not self._has_advanced_vocabulary(text_lower, age)
        )
        length_appropriate = avg_sentence_length <= self._max_sentence_length(age)

        # Conservative reading-level estimate (grade equivalents).
        reading_level = int(avg_word_length * 0.5 + avg_sentence_length / 6)

        culturally_appropriate = not any(
            p in text_lower for p in _CULTURALLY_INSENSITIVE_PHRASES
        )

        is_appropriate = vocab_appropriate and length_appropriate and culturally_appropriate
        return {
            "is_appropriate": is_appropriate,
            "average_word_length": avg_word_length,
            "average_sentence_length": avg_sentence_length,
            "has_complex_vocabulary": not vocab_appropriate,
            "reading_level": reading_level,
            "culturally_appropriate": culturally_appropriate,
            "vocabulary_appropriate": vocab_appropriate,
            "length_appropriate": length_appropriate,
        }

    def check_response(self, response: str, age: int) -> Dict[str, Any]:
        """Check whether a tutor response's tone/complexity suits the age."""
        response_lower = (response or "").lower()
        words = response.split()
        avg_word_length = self._average_word_length(response)

        vocabulary_appropriate = (
            avg_word_length <= self._max_word_length(age)
            and not self._has_advanced_vocabulary(response_lower, age)
        )

        enthusiasm_count = sum(1 for w in _ENTHUSIASM_WORDS if w in response_lower)
        exclaims = response.count("!")
        has_encouraging_phrase = any(p in response_lower for p in _ENCOURAGING_PHRASES)
        enthusiasm_score = min(
            1.0, 0.35 * enthusiasm_count + 0.15 * exclaims + (0.35 if has_encouraging_phrase else 0.0)
        )

        is_supportive = any(p in response_lower for p in _SUPPORTIVE_PHRASES)
        is_condescending = any(p in response_lower for p in _CONDESCENDING_PHRASES)

        return {
            "is_appropriate": vocabulary_appropriate and not is_condescending,
            "average_word_length": avg_word_length,
            "has_complex_vocabulary": not vocabulary_appropriate,
            "enthusiasm_score": enthusiasm_score,
            "is_supportive": is_supportive,
            "is_condescending": is_condescending,
            "vocabulary_appropriate": vocabulary_appropriate,
        }


# ---------------------------------------------------------------------------
# Response safety (dangerous suggestions, PII requests)
# ---------------------------------------------------------------------------

_DANGEROUS_KEYWORDS = (
    "chemicals",
    "electrical outlet",
    "matches",
    "fire",
    "climb",
    "roof",
    "mixing",
)

_SUPERVISION_KEYWORDS = (
    "alone",
    "by yourself",
    "without help",
    "stove",
    "go outside",
    "take apart",
    "go to the store",
)

_SUPERVISION_MENTIONS = (
    "with adult supervision",
    "ask a parent",
    "ask an adult",
    "with help from",
    "have a grown-up",
)

_PSYCHOLOGICAL_HARM_KEYWORDS = (
    "worthless",
    "punish yourself",
    "not smart enough",
    "give up",
    "you'll never",
)

_RULE_BREAKING_KEYWORDS = (
    "stay up past",
    "skip",
    "don't tell",
    "cheat",
    "look up the answer",
)


class ResponseSafetyValidator:
    """Validates AI responses for physical/psychological safety and PII requests."""

    def check_response(self, response: str, age: int) -> Dict[str, Any]:
        response_lower = (response or "").lower()
        safety_violations: List[str] = []
        warnings: List[str] = []
        severity = "none"

        if any(kw in response_lower for kw in _DANGEROUS_KEYWORDS):
            safety_violations.append("dangerous_activity")
            severity = "critical"

        has_supervision_mention = any(p in response_lower for p in _SUPERVISION_MENTIONS)

        if any(kw in response_lower for kw in _SUPERVISION_KEYWORDS):
            if age < 10:
                warnings.append("requires_supervision")
                if not has_supervision_mention:
                    safety_violations.append("unsupervised_activity")
                    if severity == "none":
                        severity = "high"

        if any(kw in response_lower for kw in _PSYCHOLOGICAL_HARM_KEYWORDS):
            safety_violations.append("psychological_harm")
            severity = "critical"

        if any(kw in response_lower for kw in _RULE_BREAKING_KEYWORDS):
            safety_violations.append("encourages_rule_breaking")
            if severity == "none":
                severity = "high"

        return {
            "is_safe": len(safety_violations) == 0,
            "safety_violations": safety_violations,
            "warnings": warnings,
            "severity": severity,
            "requires_intervention": "psychological_harm" in safety_violations,
            "has_supervision_mention": has_supervision_mention,
        }

    def check_pii_request(self, response: str) -> Dict[str, Any]:
        """Detect attempts to extract personal information from a child."""
        response_lower = (response or "").lower()
        pii_violations: List[str] = []

        name_patterns = ("what's your", "your full name", "tell me your name", "call you")
        asks_name = any(p in response_lower for p in name_patterns) and (
            "name" in response_lower or "call you" in response_lower
        )
        homework_exception = "write" in response_lower and "top" in response_lower
        if asks_name and not homework_exception:
            pii_violations.append("requests_name")

        location_patterns = (
            "where do you live",
            "your address",
            "what school",
            "what city",
            "home address",
        )
        if any(p in response_lower for p in location_patterns):
            pii_violations.append("requests_location")

        contact_patterns = ("phone number", "email", "contact you", "parent's phone")
        if any(p in response_lower for p in contact_patterns):
            pii_violations.append("requests_contact_info")

        family_patterns = ("who do you live", "parents do", "siblings", "parents home")
        if any(p in response_lower for p in family_patterns):
            pii_violations.append("requests_family_info")

        schedule_patterns = ("what time", "when are your parents", "home alone", "daily routine")
        risk_words = ("home", "alone", "parents", "routine", "schedule")
        if any(p in response_lower for p in schedule_patterns) and any(
            r in response_lower for r in risk_words
        ):
            pii_violations.append("requests_schedule")

        media_patterns = (
            "picture of yourself",
            "show me your face",
            "photo of yourself",
            "what you look like",
        )
        if any(p in response_lower for p in media_patterns):
            pii_violations.append("requests_personal_media")

        return {
            "is_safe": len(pii_violations) == 0,
            "pii_violations": pii_violations,
            "severity": "high" if pii_violations else "none",
        }


# ---------------------------------------------------------------------------
# Educational content validation
# ---------------------------------------------------------------------------

_EDUCATIONAL_KEYWORDS = {
    "learn",
    "practice",
    "understand",
    "explore",
    "discover",
    "think",
    "observe",
    "explain",
    "solve",
    "question",
}

_SUBJECT_NOUNS = {
    "photosynthesis",
    "multiplication",
    "division",
    "fraction",
    "fractions",
    "equation",
    "experiment",
    "grammar",
    "energy",
    "numbers",
    "plants",
    "reading",
    "comprehension",
    "history",
    "culture",
    "patterns",
}

_COMMERCIAL_KEYWORDS = {
    "buy",
    "subscribe",
    "click",
    "prize",
    "prizes",
    "win",
    "offer",
    "premium",
    "unlock",
    "limited time",
}

_MISINFORMATION_PATTERNS = (
    "don't need",
    "is flat",
    "just made up",
    "waste of time",
)

_SOCRATIC_INDICATORS = (
    "what do you think",
    "can you explain",
    "how might you",
    "what patterns",
    "why do you",
    "what if",
)

_DIRECT_ANSWER_PATTERNS = (
    "the answer is",
    "just write",
    "the solution is",
    "here's the answer",
)

_CURRICULUM_KEYWORDS = {
    "math": ["add", "subtract", "multiply", "numbers", "solve"],
    "science": ["plants", "grow", "observe", "experiment"],
    "reading": ["read", "comprehension", "story", "practice"],
    "social_studies": ["culture", "history", "explore", "community"],
}


class EducationalContentValidator:
    """Scores text for genuine educational value vs. advertising/misinformation."""

    def validate(self, text: str, subject: Optional[str] = None) -> Dict[str, Any]:
        text_lower = (text or "").lower()

        edu_found = sum(1 for kw in _EDUCATIONAL_KEYWORDS if kw in text_lower)
        subject_noun_found = any(kw in text_lower for kw in _SUBJECT_NOUNS)
        commercial_found = sum(1 for kw in _COMMERCIAL_KEYWORDS if kw in text_lower)
        has_misinformation = any(p in text_lower for p in _MISINFORMATION_PATTERNS)
        uses_socratic = any(p in text_lower for p in _SOCRATIC_INDICATORS)
        gives_direct_answer = any(p in text_lower for p in _DIRECT_ANSWER_PATTERNS)
        has_questions = "?" in text

        score = 0.5
        if edu_found > 0:
            score += 0.25
        if subject_noun_found:
            score += 0.15
        if has_questions and uses_socratic:
            score += 0.3
        if commercial_found > 0:
            score -= 0.4
        if has_misinformation:
            score -= 0.5
        if gives_direct_answer:
            score -= 0.3
        educational_score = max(0.0, min(1.0, score))

        curriculum_aligned = False
        if subject and subject in _CURRICULUM_KEYWORDS:
            curriculum_aligned = any(
                kw in text_lower for kw in _CURRICULUM_KEYWORDS[subject]
            )

        is_educational = (
            educational_score >= 0.6 and not has_misinformation and commercial_found == 0
        )
        return {
            "is_educational": is_educational,
            "educational_score": educational_score,
            "contains_misinformation": has_misinformation,
            "contains_advertising": commercial_found > 0,
            "curriculum_aligned": curriculum_aligned,
            "uses_socratic_method": uses_socratic,
            "gives_direct_answer": gives_direct_answer,
            "has_questions": has_questions,
        }


# ---------------------------------------------------------------------------
# Interaction tone analysis
# ---------------------------------------------------------------------------

_FRIENDLY_WORDS = ("great", "good", "nice", "let's", "together", "can you", "working hard")
_SUPPORTIVE_MARKERS = ("good start", "working hard", "step by step", "great job")
_DEMANDING_WORDS = ("must", "immediately", "have to", "hurry up")
_TIME_PRESSURE_WORDS = (
    "quick",
    "faster",
    "time runs out",
    "seconds left",
    "almost up",
    "hurry",
)
_PATIENCE_PHRASES = ("take your time", "it's okay", "no rush", "at their own pace")
_ENCOURAGING_MARKERS = (
    "can",
    "together",
    "try again",
    "work through",
    "take your time",
    "own pace",
)
_GROWTH_PHRASES = ("learning", "growing", "mistakes help", "you haven't", "yet", "practice")


class InteractionToneAnalyzer:
    """Analyzes tutor-to-child messages for tone safety."""

    def analyze(self, text: str) -> Dict[str, Any]:
        text_lower = (text or "").lower()

        is_friendly = any(w in text_lower for w in _FRIENDLY_WORDS)
        is_supportive = any(p in text_lower for p in _SUPPORTIVE_MARKERS)
        is_demanding = any(w in text_lower for w in _DEMANDING_WORDS)
        creates_time_pressure = any(w in text_lower for w in _TIME_PRESSURE_WORDS)
        shows_patience = any(p in text_lower for p in _PATIENCE_PHRASES)
        is_encouraging = any(w in text_lower for w in _ENCOURAGING_MARKERS)
        promotes_growth_mindset = any(p in text_lower for p in _GROWTH_PHRASES)

        tone = "friendly" if (is_friendly or is_supportive) else "neutral"
        if is_demanding:
            tone = "demanding"

        is_safe_for_children = not is_demanding and not creates_time_pressure and (
            is_friendly or is_supportive
        )

        return {
            "tone": tone,
            "is_friendly": is_friendly,
            "is_supportive": is_supportive,
            "is_demanding": is_demanding,
            "creates_time_pressure": creates_time_pressure,
            "shows_patience": shows_patience,
            "is_encouraging": is_encouraging,
            "promotes_growth_mindset": promotes_growth_mindset,
            "is_safe_for_children": is_safe_for_children,
        }


# ---------------------------------------------------------------------------
# Session safety policy (bedtime, breaks)
# ---------------------------------------------------------------------------


class SessionSafetyPolicy:
    """Age-based session guardrails."""

    def bedtime_hour(self, age: int) -> int:
        if age <= 7:
            return 21
        if age <= 9:
            return 22
        return 23

    def check_bedtime_restriction(self, time_str: str, age: int) -> Dict[str, Any]:
        hour = int(time_str.split(":")[0])
        bedtime_hour = self.bedtime_hour(age)
        allow_session = hour < bedtime_hour
        return {
            "allow_session": allow_session,
            "current_hour": hour,
            "bedtime_hour": bedtime_hour,
            "reason": None if allow_session else "Past bedtime",
        }

    def break_suggestion(self, session_duration_minutes: int) -> Dict[str, Any]:
        should_suggest = session_duration_minutes >= 30
        return {
            "suggest_break": should_suggest,
            "message": (
                "You've been working hard! How about taking a short rest?"
                if should_suggest
                else None
            ),
            "duration_minutes": session_duration_minutes,
        }

    def check_break_requirement(self, session_duration: int) -> Dict[str, Any]:
        break_required = session_duration >= 45
        return {
            "break_required": break_required,
            "minimum_break_minutes": 10 if break_required else 0,
            "session_duration": session_duration,
        }

    def max_session_minutes(self, age: int) -> int:
        if age <= 7:
            return 30
        if age <= 9:
            return 45
        if age <= 11:
            return 60
        return 90


# ---------------------------------------------------------------------------
# Error sanitization and PII-safe logging
# ---------------------------------------------------------------------------

_SECRET_VALUE_PATTERN = re.compile(r"(sk-[\w-]+|secret|token|password|api[_-]?key)", re.IGNORECASE)


def sanitize_stack_trace(exception: BaseException) -> str:
    """
    Produce a stack trace safe to log or display.

    Redacts secret-shaped strings from the formatted trace AND from local
    variables in the exception's frames (raw locals are never emitted;
    redaction markers are emitted instead).
    """
    trace = traceback.format_exc() or ""

    trace = re.sub(r"sk-ant-[\w-]+", "sk-ant-****", trace)
    trace = re.sub(r"sk-[\w-]+", "sk-****", trace)
    trace = re.sub(r'password["\']?\s*[:=]\s*["\']?(\w+)', "password=****", trace)

    # Scrub local variables from the frames: never dump raw values.
    tb = exception.__traceback__
    seen_frames = set()
    while tb is not None:
        frame = tb.tb_frame
        frame_id = id(frame)
        if frame_id not in seen_frames:
            seen_frames.add(frame_id)
            for name, value in frame.f_locals.items():
                if isinstance(value, str) and _SECRET_VALUE_PATTERN.search(value):
                    trace += f"\n  [redacted local '{name}': ****]"
                elif _SECRET_VALUE_PATTERN.search(str(name)):
                    trace += f"\n  [redacted local '{name}': ****]"
        tb = tb.tb_next

    return trace


_PII_LOG_FIELDS = ("name", "email", "phone", "address", "ip_address", "real_name", "school")


def create_safe_log_entry(data: Dict[str, Any]) -> Dict[str, Any]:
    """Build a log entry that excludes PII and hashes identifiers."""
    student_id = str(data.get("student_id", "UNKNOWN"))
    safe_data = {
        "student_hash": hashlib.sha256(student_id.encode()).hexdigest()[:12],
        "age": data.get("age"),
        "timestamp": datetime.utcnow().isoformat(),
    }
    return {
        "level": "INFO",
        "message": "Student activity recorded",
        "student_hash": safe_data["student_hash"],
        "data": safe_data,
    }


def sanitize_error_message(error: Dict[str, Any]) -> Dict[str, Any]:
    """Strip PII fields from an error payload before display/storage."""
    sanitized = {
        k: v for k, v in error.items() if k not in _PII_LOG_FIELDS and "email" not in k
    }
    for key in ("user_name", "user_email"):
        if key in error:
            sanitized[key] = "***"
    if "ip_address" in error:
        sanitized["ip_address"] = "***.***.***.***"
    return sanitized
