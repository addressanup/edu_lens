"""
InterventionManager - Generate Proactive Interventions

Manages proactive tutoring interventions:
- Message generation using AI tutor
- TTS audio generation
- Message personalization
- Cooldown and rate limiting
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class InterventionType(Enum):
    """Types of interventions."""

    GENTLE_PROMPT = "gentle_prompt"  # "Would you like a hint?"
    HINT_OFFER = "hint_offer"  # "I have an idea that might help!"
    CHECK_IN = "check_in"  # "How's it going?"
    ENCOURAGEMENT = "encouragement"  # "Don't give up!"
    DIRECT_HELP = "direct_help"  # Provide actual hint/guidance


@dataclass
class Intervention:
    """A generated intervention."""

    intervention_type: str
    message: str
    audio_data: Optional[bytes] = None
    audio_url: Optional[str] = None
    language: str = "en"
    personalized: bool = False
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intervention_type": self.intervention_type,
            "message": self.message,
            "audio_url": self.audio_url,
            "has_audio": self.audio_data is not None,
            "language": self.language,
            "personalized": self.personalized,
            "generated_at": self.generated_at,
        }


class InterventionManager:
    """
    Generates and manages proactive interventions.

    Features:
    - Multi-language message templates
    - AI-generated contextual messages
    - TTS audio generation
    - Personalization with child's name
    - Message variation
    - Cooldown management
    """

    # Message templates by language
    TEMPLATES: Dict[str, Dict[str, List[str]]] = {
        "en": {
            "gentle_prompt": [
                "I see you've been working on this for a while. Would you like a hint?",
                "This one looks tricky! Do you want me to help you think it through?",
                "I'm here if you need me! Want to talk about this problem?",
                "Having trouble? I'd love to help if you want!",
            ],
            "hint_offer": [
                "I have an idea that might help! Want to hear it?",
                "I noticed you might be stuck. Can I give you a little hint?",
                "What if I share a small tip? Would that be okay?",
            ],
            "check_in": [
                "How's it going? Let me know if you need anything!",
                "Just checking in - are you finding this okay?",
                "Everything alright? I'm happy to help whenever you need!",
            ],
            "encouragement": [
                "I see you working hard! That's great!",
                "Don't give up - you're getting closer!",
                "Making mistakes is part of learning. Keep trying!",
                "You're doing amazing! Keep going!",
                "I believe in you! You can do this!",
            ],
            "direct_help": [
                "Let me help you with this one.",
                "Here's something that might help...",
                "Let's work through this together.",
            ],
        },
        "es": {
            "gentle_prompt": [
                "Veo que has estado trabajando en esto por un rato. Te gustaria una pista?",
                "Este parece dificil! Quieres que te ayude a pensarlo?",
                "Estoy aqui si me necesitas! Quieres hablar sobre este problema?",
            ],
            "hint_offer": [
                "Tengo una idea que podria ayudar! Quieres escucharla?",
                "Note que podrias estar atascado. Puedo darte una pequena pista?",
            ],
            "check_in": [
                "Como va? Dime si necesitas algo!",
                "Solo queria ver como estas - todo bien?",
            ],
            "encouragement": [
                "Te veo trabajando duro! Muy bien!",
                "No te rindas - estas cada vez mas cerca!",
                "Los errores son parte del aprendizaje. Sigue intentando!",
            ],
            "direct_help": [
                "Dejame ayudarte con este.",
                "Aqui hay algo que podria ayudar...",
            ],
        },
        "fr": {
            "gentle_prompt": [
                "Je vois que tu travailles depuis un moment. Veux-tu un indice?",
                "Ca a l'air difficile! Tu veux que je t'aide a reflechir?",
            ],
            "hint_offer": [
                "J'ai une idee qui pourrait t'aider! Tu veux l'entendre?",
            ],
            "check_in": [
                "Comment ca va? Dis-moi si tu as besoin de quelque chose!",
            ],
            "encouragement": [
                "Je te vois travailler dur! C'est super!",
                "N'abandonne pas - tu y arrives!",
            ],
            "direct_help": [
                "Laisse-moi t'aider avec celui-ci.",
            ],
        },
        "de": {
            "gentle_prompt": [
                "Ich sehe, du arbeitest schon eine Weile daran. Mochtest du einen Hinweis?",
                "Das sieht schwierig aus! Soll ich dir beim Durchdenken helfen?",
            ],
            "hint_offer": [
                "Ich habe eine Idee, die helfen konnte! Willst du sie horen?",
            ],
            "check_in": [
                "Wie lauft es? Sag mir, wenn du etwas brauchst!",
            ],
            "encouragement": [
                "Ich sehe, du arbeitest hart! Das ist toll!",
                "Gib nicht auf - du kommst naher!",
            ],
            "direct_help": [
                "Lass mich dir dabei helfen.",
            ],
        },
        "zh": {
            "gentle_prompt": [
                "我看到你已经做这道题一段时间了。需要一点提示吗？",
                "这道题看起来有点难！要我帮你想一想吗？",
            ],
            "hint_offer": [
                "我有个主意可能会帮助你！想听听吗？",
            ],
            "check_in": [
                "进展如何？需要什么就告诉我！",
            ],
            "encouragement": [
                "我看到你很努力！太棒了！",
                "别放弃——你越来越接近了！",
            ],
            "direct_help": [
                "让我来帮你看看这道题。",
            ],
        },
        "hi": {
            "gentle_prompt": [
                "मैं देख रहा हूं कि तुम इस पर काफी समय से काम कर रहे हो। क्या तुम एक संकेत चाहोगे?",
                "यह मुश्किल लग रहा है! क्या तुम चाहते हो कि मैं तुम्हें सोचने में मदद करूं?",
            ],
            "hint_offer": [
                "मेरे पास एक विचार है जो मदद कर सकता है! सुनना चाहोगे?",
            ],
            "check_in": [
                "कैसे चल रहा है? अगर कुछ चाहिए तो बताओ!",
            ],
            "encouragement": [
                "मैं देख रहा हूं तुम कड़ी मेहनत कर रहे हो! बहुत अच्छा!",
                "हार मत मानो - तुम करीब आ रहे हो!",
            ],
            "direct_help": [
                "चलो मैं इसमें तुम्हारी मदद करता हूं।",
            ],
        },
        "ne": {
            "gentle_prompt": [
                "म देख्छु तिमी यसमा केही समयदेखि काम गर्दैछौ। के तिमी एउटा संकेत चाहन्छौ?",
                "यो गाह्रो देखिन्छ! के तिमी चाहन्छौ म तिमीलाई सोच्न मद्दत गरूँ?",
            ],
            "hint_offer": [
                "मसँग एउटा विचार छ जसले मद्दत गर्न सक्छ! सुन्न चाहन्छौ?",
            ],
            "check_in": [
                "कस्तो चलिरहेको छ? केही चाहियो भने भन!",
            ],
            "encouragement": [
                "म देख्छु तिमी कडा मेहनत गर्दैछौ! राम्रो छ!",
                "हार नमान - तिमी नजिकै आइरहेका छौ!",
            ],
            "direct_help": [
                "म यसमा तिमीलाई मद्दत गर्छु।",
            ],
        },
    }

    def __init__(
        self,
        language: str = "en",
        child_name: Optional[str] = None,
        config: Any = None,
        tts_callback: Optional[Callable[[str, str], Awaitable[bytes]]] = None,
        ai_generator: Optional[Callable[[str, Dict], Awaitable[str]]] = None,
    ):
        """
        Initialize intervention manager.

        Args:
            language: Language code for messages
            child_name: Child's name for personalization
            config: ObservationConfig with intervention settings
            tts_callback: Async function to generate TTS audio(text, language) -> bytes
            ai_generator: Async function to generate AI response(prompt, context) -> str
        """
        self.language = language
        self.child_name = child_name
        self.config = config
        self.tts_callback = tts_callback
        self.ai_generator = ai_generator

        # Load config or use defaults
        if config:
            self.use_child_name = config.use_child_name
            self.vary_messages = config.vary_messages
        else:
            self.use_child_name = True
            self.vary_messages = True

        # State
        self._message_indices: Dict[str, int] = {}
        self._intervention_history: List[Dict[str, Any]] = []

    async def generate(
        self,
        intervention_type: str,
        struggle_reason: Optional[str] = None,
        problem: Optional[Dict[str, Any]] = None,
        problem_time: float = 0.0,
        use_ai: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate an intervention.

        Args:
            intervention_type: Type of intervention (gentle_prompt, hint_offer, etc.)
            struggle_reason: Why struggle was detected
            problem: Current problem dict
            problem_time: Time spent on problem
            use_ai: Whether to use AI for message generation

        Returns:
            Intervention dict with message and optional audio
        """
        try:
            # Get message
            if use_ai and self.ai_generator:
                message = await self._generate_ai_message(
                    intervention_type, struggle_reason, problem, problem_time
                )
            else:
                message = self._get_template_message(intervention_type)

            if not message:
                return None

            # Personalize
            if self.use_child_name and self.child_name:
                message = self._personalize_message(message)

            # Generate audio if TTS callback available
            audio_data = None
            if self.tts_callback:
                try:
                    audio_data = await self.tts_callback(message, self.language)
                except Exception as e:
                    logger.warning(f"TTS generation failed: {e}")

            # Create intervention
            intervention = Intervention(
                intervention_type=intervention_type,
                message=message,
                audio_data=audio_data,
                language=self.language,
                personalized=self.child_name is not None,
            )

            # Record in history
            self._intervention_history.append(
                {
                    "timestamp": time.time(),
                    "intervention": intervention.to_dict(),
                    "struggle_reason": struggle_reason,
                    "problem_time": problem_time,
                }
            )

            # Limit history
            if len(self._intervention_history) > 50:
                self._intervention_history.pop(0)

            logger.info(f"Generated intervention: {intervention_type} in {self.language}")

            return intervention.to_dict()

        except Exception as e:
            logger.error(f"Intervention generation error: {e}")
            return None

    def _get_template_message(self, intervention_type: str) -> Optional[str]:
        """Get a template message for the intervention type."""
        # Get templates for language (fallback to English)
        lang_templates = self.TEMPLATES.get(self.language, self.TEMPLATES["en"])
        type_templates = lang_templates.get(intervention_type)

        if not type_templates:
            # Fallback to English
            type_templates = self.TEMPLATES["en"].get(intervention_type, [])

        if not type_templates:
            return None

        # Select message
        if self.vary_messages:
            # Cycle through messages
            idx = self._message_indices.get(intervention_type, 0)
            message = type_templates[idx % len(type_templates)]
            self._message_indices[intervention_type] = idx + 1
        else:
            message = type_templates[0]

        return message

    async def _generate_ai_message(
        self,
        intervention_type: str,
        struggle_reason: Optional[str],
        problem: Optional[Dict[str, Any]],
        problem_time: float,
    ) -> Optional[str]:
        """Generate contextual message using AI."""
        if not self.ai_generator:
            return self._get_template_message(intervention_type)

        try:
            # Build context
            context = {
                "intervention_type": intervention_type,
                "struggle_reason": struggle_reason,
                "problem_text": problem.get("text") if problem else None,
                "problem_time_seconds": problem_time,
                "language": self.language,
                "child_name": self.child_name,
            }

            # Build prompt
            prompt = self._build_ai_prompt(intervention_type, context)

            # Generate
            message = await self.ai_generator(prompt, context)

            return message

        except Exception as e:
            logger.warning(f"AI generation failed: {e}, using template")
            return self._get_template_message(intervention_type)

    def _build_ai_prompt(self, intervention_type: str, context: Dict[str, Any]) -> str:
        """Build prompt for AI message generation."""
        lang_names = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "zh": "Chinese",
            "hi": "Hindi",
            "ne": "Nepali",
        }
        lang_name = lang_names.get(self.language, "English")

        base_prompt = f"""Generate a brief, encouraging {intervention_type.replace('_', ' ')} message for a child who is struggling with their homework.

Language: {lang_name}
{f"Child's name: {context.get('child_name')}" if context.get('child_name') else ""}
Struggle reason: {context.get('struggle_reason', 'extended time on problem')}
Time on problem: {context.get('problem_time_seconds', 0):.0f} seconds
{f"Problem: {context.get('problem_text')[:100]}" if context.get('problem_text') else ""}

Requirements:
- Keep the message short (1-2 sentences)
- Be warm, friendly, and encouraging
- Don't give away the answer
- Use age-appropriate language for elementary students
- Respond ONLY in {lang_name}

Message:"""

        return base_prompt

    def _personalize_message(self, message: str) -> str:
        """Add child's name to message."""
        if not self.child_name:
            return message

        # Add name at the beginning naturally
        # Check if message starts with "I" or similar
        if message[0].isupper() and message[0] not in ["I", "A"]:
            # Insert name at beginning
            return f"{self.child_name}, {message[0].lower()}{message[1:]}"
        else:
            return f"{self.child_name}, {message}"

    def set_language(self, language: str) -> None:
        """Update language setting."""
        self.language = language
        logger.info(f"Intervention language set to: {language}")

    def set_child_name(self, name: str) -> None:
        """Update child's name."""
        self.child_name = name

    def get_intervention_history(self) -> List[Dict[str, Any]]:
        """Get intervention history."""
        return self._intervention_history[-10:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get intervention statistics."""
        if not self._intervention_history:
            return {
                "total_interventions": 0,
                "interventions_by_type": {},
            }

        by_type: Dict[str, int] = {}
        for h in self._intervention_history:
            itype = h["intervention"]["intervention_type"]
            by_type[itype] = by_type.get(itype, 0) + 1

        return {
            "total_interventions": len(self._intervention_history),
            "interventions_by_type": by_type,
            "language": self.language,
            "personalized": self.child_name is not None,
        }

    def get_available_languages(self) -> List[str]:
        """Get list of supported languages."""
        return list(self.TEMPLATES.keys())


# TTS integration helper
async def create_tts_callback() -> Optional[Callable[[str, str], Awaitable[bytes]]]:
    """Create TTS callback function using the TTS engine."""
    try:
        from src.audio.tts_engine import TTSBackend, TTSConfig, TTSEngine

        async def generate_tts(text: str, language: str) -> bytes:
            config = TTSConfig(
                backend=TTSBackend.EDGE_TTS,
                language=language,
                speaking_rate=0.9,  # Slightly slower for children
            )
            engine = TTSEngine(config=config)
            result = await engine.synthesize(text)
            return result.audio_data

        return generate_tts

    except ImportError:
        logger.warning("TTS engine not available")
        return None
