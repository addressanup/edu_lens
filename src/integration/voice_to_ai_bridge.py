"""
Voice to AI Bridge for EduLens

Connects the voice processing pipeline to the educational AI system,
transforming speech input into AI-ready queries and AI responses into speech.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """Detected intent from student's voice query."""

    HELP_REQUEST = auto()  # "I need help" / "Help me"
    EXPLAIN_CONCEPT = auto()  # "What is..." / "Explain..."
    CHECK_ANSWER = auto()  # "Is this right?" / "Did I get it?"
    HINT_REQUEST = auto()  # "Give me a hint" / "Can I have a clue?"
    REPEAT_REQUEST = auto()  # "Say that again" / "Repeat"
    SLOWER_REQUEST = auto()  # "Slower please" / "Too fast"
    SKIP_REQUEST = auto()  # "Skip this" / "Next problem"
    READ_PROBLEM = auto()  # "Read the problem" / "What does it say?"
    CLARIFICATION = auto()  # "What do you mean?" / "I don't understand"
    AFFIRMATIVE = auto()  # "Yes" / "Okay" / "Got it"
    NEGATIVE = auto()  # "No" / "Not yet"
    UNKNOWN = auto()


@dataclass
class VoiceQuery:
    """Processed voice query from student."""

    # Raw transcription
    transcription: str
    confidence: float

    # Parsed intent
    intent: QueryIntent
    intent_confidence: float

    # Extracted entities
    subject_mentioned: str | None = None
    concept_mentioned: str | None = None
    number_mentioned: str | None = None

    # Timing
    timestamp: datetime = field(default_factory=datetime.utcnow)
    speech_duration_ms: int = 0

    # Context
    is_followup: bool = False
    previous_context: str | None = None


@dataclass
class SpeechResponse:
    """Response prepared for text-to-speech output."""

    text: str
    ssml: str | None = None

    # Speech parameters
    speed: float = 1.0  # 0.5 = slow, 1.0 = normal, 1.5 = fast
    emphasis_words: list[str] = field(default_factory=list)
    pause_after_sentences: bool = True

    # Emotional tone
    tone: str = "encouraging"  # encouraging, explaining, celebrating, gentle

    # Educational markers
    is_hint: bool = False
    hint_level: int = 0  # 0 = none, 1 = subtle, 2 = moderate, 3 = direct
    contains_question: bool = False


class VoiceToAIBridge:
    """
    Bridge connecting voice input to AI and AI output to voice.

    Responsibilities:
    - Parse student voice queries and detect intent
    - Prepare AI responses for natural speech output
    - Handle conversation flow and context
    """

    def __init__(self) -> None:
        self._intent_patterns = self._build_intent_patterns()
        self._conversation_history: list[tuple[VoiceQuery, SpeechResponse]] = []

    def _build_intent_patterns(self) -> dict[QueryIntent, list[str]]:
        """Build regex patterns for intent detection."""
        return {
            QueryIntent.HELP_REQUEST: [
                r"\bhelp\b",
                r"\bhelp me\b",
                r"\bi('m| am) stuck\b",
                r"\bdon'?t know\b",
                r"\bcan'?t figure\b",
            ],
            QueryIntent.EXPLAIN_CONCEPT: [
                r"\bwhat is\b",
                r"\bwhat are\b",
                r"\bexplain\b",
                r"\btell me about\b",
                r"\bwhat does .+ mean\b",
            ],
            QueryIntent.CHECK_ANSWER: [
                r"\bis (this|that|it) (right|correct)\b",
                r"\bdid i get it\b",
                r"\bam i right\b",
                r"\bcheck (my|this)\b",
            ],
            QueryIntent.HINT_REQUEST: [
                r"\bhint\b",
                r"\bclue\b",
                r"\bhelp me start\b",
                r"\bwhere do i begin\b",
                r"\bfirst step\b",
            ],
            QueryIntent.REPEAT_REQUEST: [
                r"\brepeat\b",
                r"\bsay (that |it )?again\b",
                r"\bwhat did you say\b",
                r"\bone more time\b",
            ],
            QueryIntent.SLOWER_REQUEST: [
                r"\bslower\b",
                r"\btoo fast\b",
                r"\bslow down\b",
            ],
            QueryIntent.SKIP_REQUEST: [
                r"\bskip\b",
                r"\bnext (one|problem)\b",
                r"\bmove on\b",
            ],
            QueryIntent.READ_PROBLEM: [
                r"\bread (the |this )?(problem|question)\b",
                r"\bwhat does it say\b",
                r"\bread it to me\b",
            ],
            QueryIntent.CLARIFICATION: [
                r"\bwhat do you mean\b",
                r"\bi don'?t understand\b",
                r"\bconfused\b",
                r"\bcan you explain\b",
            ],
            QueryIntent.AFFIRMATIVE: [
                r"^yes\b",
                r"^yeah\b",
                r"^okay\b",
                r"^ok\b",
                r"\bgot it\b",
                r"\bi understand\b",
                r"^sure\b",
            ],
            QueryIntent.NEGATIVE: [
                r"^no\b",
                r"^nope\b",
                r"\bnot yet\b",
                r"\bi don'?t get it\b",
                r"\bstill confused\b",
            ],
        }

    def process_voice_input(
        self,
        transcription: str,
        confidence: float,
        speech_duration_ms: int = 0,
    ) -> VoiceQuery:
        """
        Process transcribed voice input into structured query.

        Args:
            transcription: Transcribed text from ASR
            confidence: ASR confidence score
            speech_duration_ms: Duration of speech in milliseconds

        Returns:
            Structured VoiceQuery with parsed intent
        """
        # Detect intent
        intent, intent_confidence = self._detect_intent(transcription)

        # Extract entities
        subject = self._extract_subject_mention(transcription)
        concept = self._extract_concept_mention(transcription)
        number = self._extract_number_mention(transcription)

        # Check if follow-up
        is_followup = len(self._conversation_history) > 0
        previous_context = None
        if is_followup and self._conversation_history:
            last_response = self._conversation_history[-1][1]
            previous_context = last_response.text[:100]  # First 100 chars

        return VoiceQuery(
            transcription=transcription,
            confidence=confidence,
            intent=intent,
            intent_confidence=intent_confidence,
            subject_mentioned=subject,
            concept_mentioned=concept,
            number_mentioned=number,
            speech_duration_ms=speech_duration_ms,
            is_followup=is_followup,
            previous_context=previous_context,
        )

    def _detect_intent(self, text: str) -> tuple[QueryIntent, float]:
        """Detect the intent behind the student's query."""
        text_lower = text.lower().strip()

        for intent, patterns in self._intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    return intent, 0.9  # High confidence for pattern match

        # Default to help request if question-like
        if text_lower.endswith("?") or text_lower.startswith(
            ("how", "why", "what", "when", "where")
        ):
            return QueryIntent.HELP_REQUEST, 0.6

        return QueryIntent.UNKNOWN, 0.3

    def _extract_subject_mention(self, text: str) -> str | None:
        """Extract mentioned subject from text."""
        text_lower = text.lower()
        subjects = {
            "math": [
                "math",
                "mathematics",
                "addition",
                "subtraction",
                "multiplication",
                "division",
                "fraction",
            ],
            "reading": ["reading", "story", "book", "word", "sentence", "paragraph"],
            "science": ["science", "experiment", "plant", "animal", "weather"],
            "social_studies": ["social studies", "history", "map", "community", "government"],
        }

        for subject, keywords in subjects.items():
            if any(kw in text_lower for kw in keywords):
                return subject

        return None

    def _extract_concept_mention(self, text: str) -> str | None:
        """Extract specific concept mentions."""
        # Common math concepts
        math_concepts = [
            "addition",
            "subtraction",
            "multiplication",
            "division",
            "fraction",
            "decimal",
            "percent",
            "equation",
            "variable",
        ]

        text_lower = text.lower()
        for concept in math_concepts:
            if concept in text_lower:
                return concept

        return None

    def _extract_number_mention(self, text: str) -> str | None:
        """Extract number mentions from text."""
        # Find problem numbers like "number 5" or "question 3"
        match = re.search(r"(number|question|problem)\s*(\d+)", text, re.IGNORECASE)
        if match:
            return match.group(2)

        # Find standalone numbers
        match = re.search(r"\b(\d+)\b", text)
        if match:
            return match.group(1)

        return None

    def prepare_speech_response(
        self,
        ai_response: str,
        response_type: str = "explanation",
        hint_level: int = 0,
    ) -> SpeechResponse:
        """
        Prepare AI response for text-to-speech output.

        Args:
            ai_response: Raw text response from AI
            response_type: Type of response (explanation, hint, feedback, etc.)
            hint_level: 0-3 indicating hint directness

        Returns:
            SpeechResponse ready for TTS
        """
        # Clean up text for speech
        text = self._clean_for_speech(ai_response)

        # Determine tone based on response type
        tone = self._determine_tone(response_type, text)

        # Calculate appropriate speed
        speed = self._calculate_speech_speed(text, response_type)

        # Find words to emphasize
        emphasis_words = self._find_emphasis_words(text)

        # Generate SSML if supported
        ssml = self._generate_ssml(text, emphasis_words, speed, tone)

        # Check if response contains a question
        contains_question = "?" in text

        response = SpeechResponse(
            text=text,
            ssml=ssml,
            speed=speed,
            emphasis_words=emphasis_words,
            tone=tone,
            is_hint=hint_level > 0,
            hint_level=hint_level,
            contains_question=contains_question,
        )

        return response

    def _clean_for_speech(self, text: str) -> str:
        """Clean text for natural speech output."""
        # Remove markdown formatting
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)  # Bold
        text = re.sub(r"\*(.+?)\*", r"\1", text)  # Italic
        text = re.sub(r"`(.+?)`", r"\1", text)  # Code

        # Convert math symbols to words
        replacements = {
            "+": " plus ",
            "-": " minus ",
            "×": " times ",
            "÷": " divided by ",
            "=": " equals ",
            "<": " is less than ",
            ">": " is greater than ",
            "≤": " is less than or equal to ",
            "≥": " is greater than or equal to ",
        }
        for symbol, word in replacements.items():
            text = text.replace(symbol, word)

        # Clean up extra whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _determine_tone(self, response_type: str, text: str) -> str:
        """Determine appropriate emotional tone for response."""
        if response_type == "celebration" or "great job" in text.lower():
            return "celebrating"
        elif response_type == "hint":
            return "encouraging"
        elif response_type == "correction":
            return "gentle"
        elif response_type == "explanation":
            return "explaining"
        else:
            return "encouraging"

    def _calculate_speech_speed(self, text: str, response_type: str) -> float:
        """Calculate appropriate speech speed."""
        # Slower for explanations, normal for feedback
        if response_type == "explanation":
            return 0.9
        elif response_type == "hint":
            return 0.85  # Even slower for hints
        elif response_type == "celebration":
            return 1.1  # Slightly faster for positive feedback
        else:
            return 1.0

    def _find_emphasis_words(self, text: str) -> list[str]:
        """Find key words to emphasize in speech."""
        # Emphasize important educational keywords
        keywords = [
            "first",
            "next",
            "then",
            "finally",
            "remember",
            "important",
            "key",
            "notice",
            "think about",
        ]

        emphasis = []
        text_lower = text.lower()
        for kw in keywords:
            if kw in text_lower:
                emphasis.append(kw)

        return emphasis[:3]  # Limit to 3 emphasis points

    def _generate_ssml(
        self,
        text: str,
        emphasis_words: list[str],
        speed: float,
        tone: str,
    ) -> str:
        """Generate SSML markup for advanced TTS control."""
        ssml = f'<speak><prosody rate="{int(speed * 100)}%">'

        # Add emphasis to key words
        processed_text = text
        for word in emphasis_words:
            processed_text = re.sub(
                rf"\b({word})\b",
                r'<emphasis level="moderate">\1</emphasis>',
                processed_text,
                flags=re.IGNORECASE,
            )

        # Add pauses after sentences
        processed_text = re.sub(
            r"([.!?])\s+",
            r'\1<break time="500ms"/> ',
            processed_text,
        )

        ssml += processed_text
        ssml += "</prosody></speak>"

        return ssml

    def add_to_history(self, query: VoiceQuery, response: SpeechResponse) -> None:
        """Add interaction to conversation history."""
        self._conversation_history.append((query, response))
        # Keep only last 10 interactions
        if len(self._conversation_history) > 10:
            self._conversation_history = self._conversation_history[-10:]

    def get_conversation_context(self) -> str:
        """Get formatted conversation history for context."""
        if not self._conversation_history:
            return ""

        lines = []
        for query, response in self._conversation_history[-3:]:  # Last 3 exchanges
            lines.append(f"Student: {query.transcription}")
            lines.append(f"Tutor: {response.text[:100]}...")

        return "\n".join(lines)

    def reset_conversation(self) -> None:
        """Reset conversation history for new session."""
        self._conversation_history = []


def create_voice_bridge() -> VoiceToAIBridge:
    """Factory function to create a configured voice bridge."""
    return VoiceToAIBridge()
