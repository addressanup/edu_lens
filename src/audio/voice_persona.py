"""
EduLens Voice Persona Management

Defines voice personalities optimized for child education with
age-appropriate characteristics and emotional tones.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, List
import logging


logger = logging.getLogger(__name__)


class EmotionalTone(Enum):
    """Emotional tones for voice delivery"""
    NEUTRAL = "neutral"
    ENCOURAGING = "encouraging"
    EXPLAINING = "explaining"
    CELEBRATING = "celebrating"
    PATIENT = "patient"
    EXCITED = "excited"
    THOUGHTFUL = "thoughtful"
    REASSURING = "reassuring"


class AgeGroup(Enum):
    """Target age groups for voice optimization"""
    EARLY_ELEMENTARY = "6-8"   # Ages 6-8
    LATE_ELEMENTARY = "9-10"   # Ages 9-10
    MIDDLE_SCHOOL = "11-12"    # Ages 11-12
    ALL_AGES = "6-12"          # General


class VoiceGender(Enum):
    """Voice gender preferences"""
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


@dataclass
class VoiceCharacteristics:
    """Voice characteristic parameters"""
    pitch: float = 1.0           # Pitch multiplier (0.5 - 2.0)
    rate: float = 1.0            # Speaking rate (0.5 - 2.0)
    volume: float = 1.0          # Volume level (0.0 - 1.0)
    warmth: float = 0.7          # Voice warmth (0.0 - 1.0)
    energy: float = 0.6          # Energy level (0.0 - 1.0)
    clarity: float = 0.9         # Clarity/articulation (0.0 - 1.0)

    def validate(self) -> bool:
        """Validate characteristic ranges"""
        return (
            0.5 <= self.pitch <= 2.0 and
            0.5 <= self.rate <= 2.0 and
            0.0 <= self.volume <= 1.0 and
            0.0 <= self.warmth <= 1.0 and
            0.0 <= self.energy <= 1.0 and
            0.0 <= self.clarity <= 1.0
        )


@dataclass
class EmotionalProfile:
    """Emotional tone profile"""
    tone: EmotionalTone
    characteristics: VoiceCharacteristics
    phrase_templates: List[str] = field(default_factory=list)
    emphasis_words: List[str] = field(default_factory=list)


@dataclass
class VoicePersona:
    """
    Complete voice persona definition

    Defines all aspects of a voice personality including pitch,
    rate, emotional characteristics, and context-appropriate behaviors.
    """
    name: str
    description: str
    base_characteristics: VoiceCharacteristics
    age_group: AgeGroup
    gender: VoiceGender
    emotional_profiles: Dict[EmotionalTone, EmotionalProfile] = field(default_factory=dict)
    voice_id: Optional[str] = None  # Backend-specific voice ID
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialize emotional profiles if not provided"""
        if not self.emotional_profiles:
            self._create_default_profiles()

    def _create_default_profiles(self):
        """Create default emotional profiles"""
        base = self.base_characteristics

        # Encouraging tone
        self.emotional_profiles[EmotionalTone.ENCOURAGING] = EmotionalProfile(
            tone=EmotionalTone.ENCOURAGING,
            characteristics=VoiceCharacteristics(
                pitch=base.pitch * 1.05,
                rate=base.rate * 0.95,
                volume=base.volume * 1.05,
                warmth=min(1.0, base.warmth * 1.1),
                energy=min(1.0, base.energy * 1.2),
                clarity=base.clarity
            ),
            phrase_templates=[
                "Great job!",
                "You're doing wonderful!",
                "Keep going!",
                "Excellent work!",
                "That's the right idea!"
            ],
            emphasis_words=["great", "excellent", "wonderful", "amazing", "perfect"]
        )

        # Explaining tone
        self.emotional_profiles[EmotionalTone.EXPLAINING] = EmotionalProfile(
            tone=EmotionalTone.EXPLAINING,
            characteristics=VoiceCharacteristics(
                pitch=base.pitch * 0.98,
                rate=base.rate * 0.85,
                volume=base.volume,
                warmth=base.warmth,
                energy=base.energy * 0.8,
                clarity=min(1.0, base.clarity * 1.1)
            ),
            phrase_templates=[
                "Let me explain...",
                "Here's how it works...",
                "Think about it this way...",
                "Let's break this down...",
                "So what this means is..."
            ],
            emphasis_words=["important", "key", "notice", "remember", "understand"]
        )

        # Celebrating tone
        self.emotional_profiles[EmotionalTone.CELEBRATING] = EmotionalProfile(
            tone=EmotionalTone.CELEBRATING,
            characteristics=VoiceCharacteristics(
                pitch=base.pitch * 1.1,
                rate=base.rate * 1.05,
                volume=base.volume * 1.1,
                warmth=min(1.0, base.warmth * 1.15),
                energy=min(1.0, base.energy * 1.3),
                clarity=base.clarity
            ),
            phrase_templates=[
                "Fantastic!",
                "You did it!",
                "Amazing achievement!",
                "Way to go!",
                "I knew you could do it!"
            ],
            emphasis_words=["fantastic", "amazing", "brilliant", "outstanding", "spectacular"]
        )

        # Patient tone
        self.emotional_profiles[EmotionalTone.PATIENT] = EmotionalProfile(
            tone=EmotionalTone.PATIENT,
            characteristics=VoiceCharacteristics(
                pitch=base.pitch * 0.95,
                rate=base.rate * 0.80,
                volume=base.volume * 0.95,
                warmth=min(1.0, base.warmth * 1.2),
                energy=base.energy * 0.7,
                clarity=min(1.0, base.clarity * 1.15)
            ),
            phrase_templates=[
                "It's okay, let's try again...",
                "Take your time...",
                "No rush, we'll figure this out...",
                "Let's look at this together...",
                "Everyone learns at their own pace..."
            ],
            emphasis_words=["together", "slowly", "carefully", "step", "gentle"]
        )

        # Reassuring tone
        self.emotional_profiles[EmotionalTone.REASSURING] = EmotionalProfile(
            tone=EmotionalTone.REASSURING,
            characteristics=VoiceCharacteristics(
                pitch=base.pitch,
                rate=base.rate * 0.90,
                volume=base.volume,
                warmth=min(1.0, base.warmth * 1.25),
                energy=base.energy * 0.75,
                clarity=base.clarity
            ),
            phrase_templates=[
                "Don't worry...",
                "It's perfectly normal...",
                "You're on the right track...",
                "Mistakes help us learn...",
                "That's a common challenge..."
            ],
            emphasis_words=["okay", "normal", "fine", "right", "good"]
        )

    def get_characteristics(
        self,
        tone: Optional[EmotionalTone] = None
    ) -> VoiceCharacteristics:
        """
        Get voice characteristics for a specific emotional tone

        Args:
            tone: Emotional tone (None for base characteristics)

        Returns:
            VoiceCharacteristics for the tone
        """
        if tone is None or tone not in self.emotional_profiles:
            return self.base_characteristics

        return self.emotional_profiles[tone].characteristics

    def get_encouragement_phrase(self, tone: EmotionalTone) -> Optional[str]:
        """Get a random encouragement phrase for tone"""
        if tone not in self.emotional_profiles:
            return None

        import random
        phrases = self.emotional_profiles[tone].phrase_templates
        return random.choice(phrases) if phrases else None

    def should_emphasize(self, word: str, tone: EmotionalTone) -> bool:
        """Check if word should be emphasized in given tone"""
        if tone not in self.emotional_profiles:
            return False

        emphasis_words = self.emotional_profiles[tone].emphasis_words
        return word.lower() in emphasis_words

    def adjust_for_context(
        self,
        context: str,
        difficulty: float = 0.5
    ) -> VoiceCharacteristics:
        """
        Adjust voice characteristics based on context and difficulty

        Args:
            context: Context (e.g., "math", "reading", "science")
            difficulty: Content difficulty (0.0 - 1.0)

        Returns:
            Adjusted VoiceCharacteristics
        """
        base = self.base_characteristics

        # Slow down for difficult content
        rate_adjustment = 1.0 - (difficulty * 0.3)

        # Increase clarity for complex topics
        clarity_adjustment = 1.0 + (difficulty * 0.1)

        return VoiceCharacteristics(
            pitch=base.pitch,
            rate=base.rate * rate_adjustment,
            volume=base.volume,
            warmth=base.warmth,
            energy=base.energy,
            clarity=min(1.0, base.clarity * clarity_adjustment)
        )


class VoicePersonaLibrary:
    """Library of preset voice personas"""

    def __init__(self):
        self.personas: Dict[str, VoicePersona] = {}
        self._initialize_presets()

    def _initialize_presets(self):
        """Initialize preset personas"""

        # Friendly Tutor - Warm, encouraging, patient
        self.personas["friendly_tutor"] = VoicePersona(
            name="Friendly Tutor",
            description="Warm, encouraging voice perfect for patient instruction",
            base_characteristics=VoiceCharacteristics(
                pitch=1.05,
                rate=0.95,
                volume=0.85,
                warmth=0.85,
                energy=0.7,
                clarity=0.95
            ),
            age_group=AgeGroup.ALL_AGES,
            gender=VoiceGender.FEMALE,
            tags=["patient", "warm", "educational"]
        )

        # Patient Helper - Very calm, slow-paced, reassuring
        self.personas["patient_helper"] = VoicePersona(
            name="Patient Helper",
            description="Calm, reassuring voice for struggling students",
            base_characteristics=VoiceCharacteristics(
                pitch=0.98,
                rate=0.85,
                volume=0.80,
                warmth=0.90,
                energy=0.6,
                clarity=1.0
            ),
            age_group=AgeGroup.ALL_AGES,
            gender=VoiceGender.NEUTRAL,
            tags=["calm", "reassuring", "slow"]
        )

        # Cheerful Guide - Upbeat, energetic, fun
        self.personas["cheerful_guide"] = VoicePersona(
            name="Cheerful Guide",
            description="Energetic, fun voice to keep students engaged",
            base_characteristics=VoiceCharacteristics(
                pitch=1.10,
                rate=1.05,
                volume=0.90,
                warmth=0.80,
                energy=0.85,
                clarity=0.90
            ),
            age_group=AgeGroup.EARLY_ELEMENTARY,
            gender=VoiceGender.FEMALE,
            tags=["energetic", "fun", "engaging"]
        )

        # Wise Mentor - Authoritative, clear, measured
        self.personas["wise_mentor"] = VoicePersona(
            name="Wise Mentor",
            description="Clear, authoritative voice for older students",
            base_characteristics=VoiceCharacteristics(
                pitch=0.95,
                rate=1.0,
                volume=0.85,
                warmth=0.70,
                energy=0.65,
                clarity=0.95
            ),
            age_group=AgeGroup.MIDDLE_SCHOOL,
            gender=VoiceGender.MALE,
            tags=["clear", "authoritative", "measured"]
        )

        # Science Explorer - Curious, precise, engaging
        self.personas["science_explorer"] = VoicePersona(
            name="Science Explorer",
            description="Curious, precise voice for science topics",
            base_characteristics=VoiceCharacteristics(
                pitch=1.02,
                rate=0.95,
                volume=0.85,
                warmth=0.75,
                energy=0.80,
                clarity=0.98
            ),
            age_group=AgeGroup.LATE_ELEMENTARY,
            gender=VoiceGender.NEUTRAL,
            tags=["curious", "precise", "scientific"]
        )

        # Math Master - Clear, methodical, encouraging
        self.personas["math_master"] = VoicePersona(
            name="Math Master",
            description="Clear, methodical voice for math instruction",
            base_characteristics=VoiceCharacteristics(
                pitch=1.0,
                rate=0.90,
                volume=0.85,
                warmth=0.75,
                energy=0.70,
                clarity=1.0
            ),
            age_group=AgeGroup.ALL_AGES,
            gender=VoiceGender.MALE,
            tags=["methodical", "clear", "mathematical"]
        )

    def get_persona(self, name: str) -> Optional[VoicePersona]:
        """Get persona by name"""
        return self.personas.get(name)

    def list_personas(
        self,
        age_group: Optional[AgeGroup] = None,
        tags: Optional[List[str]] = None
    ) -> List[VoicePersona]:
        """
        List available personas with optional filtering

        Args:
            age_group: Filter by age group
            tags: Filter by tags

        Returns:
            List of matching personas
        """
        personas = list(self.personas.values())

        if age_group:
            personas = [
                p for p in personas
                if p.age_group == age_group or p.age_group == AgeGroup.ALL_AGES
            ]

        if tags:
            personas = [
                p for p in personas
                if any(tag in p.tags for tag in tags)
            ]

        return personas

    def add_persona(self, persona: VoicePersona) -> None:
        """Add a custom persona to the library"""
        if not persona.base_characteristics.validate():
            raise ValueError("Invalid voice characteristics")

        self.personas[persona.name.lower().replace(" ", "_")] = persona
        logger.info(f"Added persona: {persona.name}")

    def remove_persona(self, name: str) -> bool:
        """Remove a persona from the library"""
        if name in self.personas:
            del self.personas[name]
            logger.info(f"Removed persona: {name}")
            return True
        return False


class PersonaManager:
    """
    Manages voice persona selection and adaptation

    Handles dynamic persona switching based on:
    - Content type
    - Student performance
    - Time of day
    - Difficulty level
    """

    def __init__(self, library: Optional[VoicePersonaLibrary] = None):
        self.library = library or VoicePersonaLibrary()
        self.current_persona: Optional[VoicePersona] = None
        self.current_tone: EmotionalTone = EmotionalTone.NEUTRAL

    def set_persona(self, name: str) -> bool:
        """
        Set active persona by name

        Args:
            name: Persona name

        Returns:
            True if successful
        """
        persona = self.library.get_persona(name)
        if persona:
            self.current_persona = persona
            logger.info(f"Active persona set to: {persona.name}")
            return True
        return False

    def set_tone(self, tone: EmotionalTone) -> None:
        """Set current emotional tone"""
        self.current_tone = tone
        logger.info(f"Emotional tone set to: {tone.value}")

    def get_characteristics(self) -> VoiceCharacteristics:
        """Get current voice characteristics"""
        if not self.current_persona:
            # Return default characteristics
            return VoiceCharacteristics()

        return self.current_persona.get_characteristics(self.current_tone)

    def select_persona_for_content(
        self,
        subject: str,
        age: int,
        difficulty: float = 0.5
    ) -> VoicePersona:
        """
        Auto-select appropriate persona for content

        Args:
            subject: Subject area (math, science, reading, etc.)
            age: Student age
            difficulty: Content difficulty (0.0 - 1.0)

        Returns:
            Selected VoicePersona
        """
        # Determine age group
        if age <= 8:
            age_group = AgeGroup.EARLY_ELEMENTARY
        elif age <= 10:
            age_group = AgeGroup.LATE_ELEMENTARY
        else:
            age_group = AgeGroup.MIDDLE_SCHOOL

        # Subject-specific selection
        subject_personas = {
            "math": "math_master",
            "science": "science_explorer",
            "reading": "friendly_tutor"
        }

        persona_name = subject_personas.get(subject.lower(), "friendly_tutor")
        persona = self.library.get_persona(persona_name)

        if persona:
            self.current_persona = persona
            return persona

        # Fallback to age-appropriate persona
        personas = self.library.list_personas(age_group=age_group)
        if personas:
            self.current_persona = personas[0]
            return personas[0]

        # Ultimate fallback
        self.current_persona = self.library.get_persona("friendly_tutor")
        return self.current_persona

    def adapt_to_performance(
        self,
        correct_rate: float,
        struggle_indicators: int = 0
    ) -> EmotionalTone:
        """
        Adapt emotional tone based on student performance

        Args:
            correct_rate: Percentage of correct answers (0.0 - 1.0)
            struggle_indicators: Number of struggle indicators detected

        Returns:
            Recommended EmotionalTone
        """
        if correct_rate >= 0.9:
            tone = EmotionalTone.CELEBRATING
        elif correct_rate >= 0.7:
            tone = EmotionalTone.ENCOURAGING
        elif struggle_indicators >= 3:
            tone = EmotionalTone.PATIENT
        elif correct_rate < 0.5:
            tone = EmotionalTone.REASSURING
        else:
            tone = EmotionalTone.EXPLAINING

        self.set_tone(tone)
        return tone
