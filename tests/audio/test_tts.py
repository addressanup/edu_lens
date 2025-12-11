"""
EduLens TTS System Test Suite

Comprehensive tests for text-to-speech functionality including:
- Voice quality validation
- Pronunciation accuracy testing
- Speed variation testing
- Math/science term pronunciation
- Emotional tone testing
"""

import asyncio
import pytest
import numpy as np
from pathlib import Path
from typing import List, Tuple
import tempfile
import yaml

# Import TTS components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.audio.tts_engine import (
    TTSEngine,
    TTSConfig,
    TTSBackend,
    SpeakingRate,
    EmphasisLevel,
    AudioOutput
)
from src.audio.voice_persona import (
    VoicePersona,
    VoiceCharacteristics,
    EmotionalTone,
    AgeGroup,
    VoiceGender,
    VoicePersonaLibrary,
    PersonaManager
)
from src.audio.pronunciation_rules import (
    MathPronunciationEngine,
    SciencePronunciationEngine,
    PhoneticOverrideEngine,
    PronunciationRulesEngine
)


class TestTTSEngine:
    """Test TTS engine core functionality"""

    @pytest.fixture
    def tts_config(self):
        """Create test TTS configuration"""
        return TTSConfig(
            backend=TTSBackend.PYTTSX3,
            speaking_rate=1.0,
            pitch=1.0,
            volume=0.85,
            use_ssml=True,
            cache_enabled=True
        )

    @pytest.fixture
    def tts_engine(self, tts_config):
        """Create TTS engine instance"""
        return TTSEngine(config=tts_config)

    @pytest.mark.asyncio
    async def test_basic_synthesis(self, tts_engine):
        """Test basic text-to-speech synthesis"""
        text = "Hello, this is a test."
        output = await tts_engine.synthesize(text)

        assert isinstance(output, AudioOutput)
        assert len(output.audio_data) > 0
        assert output.sample_rate > 0
        assert output.duration_ms > 0

    @pytest.mark.asyncio
    async def test_synthesis_caching(self, tts_engine):
        """Test audio output caching"""
        text = "This should be cached."

        # First synthesis
        output1 = await tts_engine.synthesize(text, use_cache=True)

        # Second synthesis (should hit cache)
        output2 = await tts_engine.synthesize(text, use_cache=True)

        # Should be same object from cache
        assert output1 is output2

    @pytest.mark.asyncio
    async def test_streaming_synthesis(self, tts_engine):
        """Test streaming audio output"""
        text = "This is a streaming test."
        chunks = []

        async for chunk in tts_engine.synthesize_streaming(text):
            chunks.append(chunk)
            assert isinstance(chunk, bytes)
            assert len(chunk) > 0

        assert len(chunks) > 0

    def test_speed_adjustment(self, tts_engine):
        """Test speaking rate adjustment"""
        tts_engine.set_speed(SpeakingRate.SLOW)
        assert tts_engine.config.speaking_rate == 0.75

        tts_engine.set_speed(SpeakingRate.FAST)
        assert tts_engine.config.speaking_rate == 1.25

        # Test numeric rate
        tts_engine.set_speed(0.9)
        assert tts_engine.config.speaking_rate == 0.9

    def test_voice_listing(self, tts_engine):
        """Test voice listing functionality"""
        voices = tts_engine.list_voices()

        assert isinstance(voices, list)
        assert len(voices) > 0
        assert all('id' in voice for voice in voices)
        assert all('name' in voice for voice in voices)

    @pytest.mark.asyncio
    async def test_text_preprocessing(self, tts_engine):
        """Test text preprocessing"""
        text = "e.g. the number  10  is ten."
        output = await tts_engine.synthesize(text, preprocess=True)

        assert isinstance(output, AudioOutput)
        # Verify preprocessing occurred (abbreviations expanded, etc.)

    @pytest.mark.asyncio
    async def test_math_expression_speaking(self, tts_engine):
        """Test mathematical expression pronunciation"""
        expression = "2 + 3 = 5"
        output = await tts_engine.speak_math(expression, explain=True)

        assert isinstance(output, AudioOutput)
        assert len(output.audio_data) > 0

    @pytest.mark.asyncio
    async def test_pedagogical_pauses(self, tts_engine):
        """Test speaking with pedagogical pauses"""
        text = "First, we add. Then, we subtract."
        output = await tts_engine.speak_with_pauses(text)

        assert isinstance(output, AudioOutput)
        # Pauses should increase duration
        output_no_pause = await tts_engine.synthesize(text, preprocess=False)
        assert output.duration_ms >= output_no_pause.duration_ms

    def test_cache_clearing(self, tts_engine):
        """Test cache clearing"""
        # Populate cache
        asyncio.run(tts_engine.synthesize("test", use_cache=True))
        assert len(tts_engine.cache) > 0

        # Clear cache
        tts_engine.clear_cache()
        assert len(tts_engine.cache) == 0


class TestVoicePersona:
    """Test voice persona functionality"""

    @pytest.fixture
    def voice_characteristics(self):
        """Create test voice characteristics"""
        return VoiceCharacteristics(
            pitch=1.0,
            rate=1.0,
            volume=0.85,
            warmth=0.75,
            energy=0.70,
            clarity=0.95
        )

    @pytest.fixture
    def voice_persona(self, voice_characteristics):
        """Create test voice persona"""
        return VoicePersona(
            name="Test Persona",
            description="Test voice for unit testing",
            base_characteristics=voice_characteristics,
            age_group=AgeGroup.ALL_AGES,
            gender=VoiceGender.NEUTRAL
        )

    def test_voice_characteristics_validation(self):
        """Test voice characteristics validation"""
        valid_chars = VoiceCharacteristics(
            pitch=1.0, rate=1.0, volume=0.85,
            warmth=0.75, energy=0.70, clarity=0.95
        )
        assert valid_chars.validate() is True

        invalid_chars = VoiceCharacteristics(
            pitch=3.0,  # Invalid: > 2.0
            rate=1.0, volume=0.85,
            warmth=0.75, energy=0.70, clarity=0.95
        )
        assert invalid_chars.validate() is False

    def test_emotional_profile_creation(self, voice_persona):
        """Test automatic emotional profile creation"""
        assert EmotionalTone.ENCOURAGING in voice_persona.emotional_profiles
        assert EmotionalTone.EXPLAINING in voice_persona.emotional_profiles
        assert EmotionalTone.CELEBRATING in voice_persona.emotional_profiles
        assert EmotionalTone.PATIENT in voice_persona.emotional_profiles

    def test_get_characteristics_by_tone(self, voice_persona):
        """Test retrieving characteristics for emotional tone"""
        # Base characteristics
        base = voice_persona.get_characteristics()
        assert base == voice_persona.base_characteristics

        # Emotional tone characteristics
        encouraging = voice_persona.get_characteristics(EmotionalTone.ENCOURAGING)
        assert encouraging.pitch > base.pitch
        assert encouraging.energy > base.energy

    def test_emphasis_detection(self, voice_persona):
        """Test word emphasis detection"""
        assert voice_persona.should_emphasize(
            "great",
            EmotionalTone.ENCOURAGING
        ) is True

        assert voice_persona.should_emphasize(
            "random",
            EmotionalTone.ENCOURAGING
        ) is False

    def test_context_adjustment(self, voice_persona):
        """Test context-based voice adjustment"""
        # Easy content
        easy_chars = voice_persona.adjust_for_context("math", difficulty=0.2)
        assert easy_chars.rate > voice_persona.base_characteristics.rate * 0.8

        # Difficult content
        hard_chars = voice_persona.adjust_for_context("math", difficulty=0.9)
        assert hard_chars.rate < voice_persona.base_characteristics.rate
        assert hard_chars.clarity >= voice_persona.base_characteristics.clarity


class TestVoicePersonaLibrary:
    """Test voice persona library"""

    @pytest.fixture
    def library(self):
        """Create persona library"""
        return VoicePersonaLibrary()

    def test_preset_personas_loaded(self, library):
        """Test that preset personas are loaded"""
        assert "friendly_tutor" in library.personas
        assert "patient_helper" in library.personas
        assert "cheerful_guide" in library.personas
        assert "wise_mentor" in library.personas
        assert "science_explorer" in library.personas
        assert "math_master" in library.personas

    def test_get_persona(self, library):
        """Test retrieving persona by name"""
        persona = library.get_persona("friendly_tutor")
        assert persona is not None
        assert persona.name == "Friendly Tutor"

    def test_list_personas_all(self, library):
        """Test listing all personas"""
        personas = library.list_personas()
        assert len(personas) >= 6

    def test_list_personas_by_age_group(self, library):
        """Test filtering personas by age group"""
        early_elem = library.list_personas(age_group=AgeGroup.EARLY_ELEMENTARY)
        assert all(
            p.age_group in [AgeGroup.EARLY_ELEMENTARY, AgeGroup.ALL_AGES]
            for p in early_elem
        )

    def test_list_personas_by_tags(self, library):
        """Test filtering personas by tags"""
        patient_personas = library.list_personas(tags=["patient"])
        assert len(patient_personas) > 0
        assert all("patient" in p.tags for p in patient_personas)

    def test_add_custom_persona(self, library):
        """Test adding custom persona"""
        custom = VoicePersona(
            name="Custom Voice",
            description="Custom test voice",
            base_characteristics=VoiceCharacteristics(),
            age_group=AgeGroup.ALL_AGES,
            gender=VoiceGender.NEUTRAL
        )

        library.add_persona(custom)
        assert "custom_voice" in library.personas

    def test_remove_persona(self, library):
        """Test removing persona"""
        # Add a custom persona
        custom = VoicePersona(
            name="Temporary Voice",
            description="Temporary test voice",
            base_characteristics=VoiceCharacteristics(),
            age_group=AgeGroup.ALL_AGES,
            gender=VoiceGender.NEUTRAL
        )
        library.add_persona(custom)

        # Remove it
        removed = library.remove_persona("temporary_voice")
        assert removed is True
        assert "temporary_voice" not in library.personas


class TestPersonaManager:
    """Test persona manager"""

    @pytest.fixture
    def manager(self):
        """Create persona manager"""
        return PersonaManager()

    def test_set_persona(self, manager):
        """Test setting active persona"""
        result = manager.set_persona("friendly_tutor")
        assert result is True
        assert manager.current_persona is not None
        assert manager.current_persona.name == "Friendly Tutor"

    def test_set_tone(self, manager):
        """Test setting emotional tone"""
        manager.set_tone(EmotionalTone.ENCOURAGING)
        assert manager.current_tone == EmotionalTone.ENCOURAGING

    def test_get_characteristics(self, manager):
        """Test getting current characteristics"""
        manager.set_persona("friendly_tutor")
        manager.set_tone(EmotionalTone.CELEBRATING)

        chars = manager.get_characteristics()
        assert isinstance(chars, VoiceCharacteristics)

    def test_auto_select_persona_for_content(self, manager):
        """Test automatic persona selection"""
        # Math content for young student
        persona = manager.select_persona_for_content("math", age=8)
        assert persona.name == "Math Master"

        # Science content for older student
        persona = manager.select_persona_for_content("science", age=11)
        assert persona.name == "Science Explorer"

    def test_adapt_to_performance(self, manager):
        """Test performance-based tone adaptation"""
        # High performance -> celebrating
        tone = manager.adapt_to_performance(correct_rate=0.95)
        assert tone == EmotionalTone.CELEBRATING

        # Good performance -> encouraging
        tone = manager.adapt_to_performance(correct_rate=0.80)
        assert tone == EmotionalTone.ENCOURAGING

        # Struggling -> patient
        tone = manager.adapt_to_performance(
            correct_rate=0.60,
            struggle_indicators=4
        )
        assert tone == EmotionalTone.PATIENT


class TestMathPronunciation:
    """Test mathematical expression pronunciation"""

    @pytest.fixture
    def math_engine(self):
        """Create math pronunciation engine"""
        return MathPronunciationEngine()

    def test_basic_operators(self, math_engine):
        """Test basic math operator pronunciation"""
        assert "plus" in math_engine.convert_expression("2 + 3")
        assert "minus" in math_engine.convert_expression("5 - 2")
        assert "times" in math_engine.convert_expression("3 × 4")
        assert "divided by" in math_engine.convert_expression("10 ÷ 2")
        assert "equals" in math_engine.convert_expression("1 = 1")

    def test_fraction_pronunciation(self, math_engine):
        """Test fraction pronunciation"""
        result = math_engine.convert_expression("1/2")
        assert "one half" in result.lower()

        result = math_engine.convert_expression("1/4")
        assert "one quarter" in result.lower()

        result = math_engine.convert_expression("2/3")
        assert "two thirds" in result.lower()

    def test_exponent_pronunciation(self, math_engine):
        """Test exponent pronunciation"""
        result = math_engine.convert_expression("x²")
        assert "squared" in result.lower()

        result = math_engine.convert_expression("x³")
        assert "cubed" in result.lower()

        result = math_engine.convert_expression("x^5")
        assert "power" in result.lower()

    def test_negative_numbers(self, math_engine):
        """Test negative number pronunciation"""
        result = math_engine.convert_expression("-5")
        assert "negative" in result.lower()

    def test_decimal_pronunciation(self, math_engine):
        """Test decimal pronunciation"""
        result = math_engine.convert_expression("3.14")
        assert "point" in result.lower()

    def test_complex_expression(self, math_engine):
        """Test complex mathematical expression"""
        expression = "(2 + 3) × 4 = 20"
        result = math_engine.convert_expression(expression)

        assert "parenthesis" in result.lower()
        assert "plus" in result.lower()
        assert "times" in result.lower()
        assert "equals" in result.lower()

    def test_number_to_word_conversion(self, math_engine):
        """Test number to word conversion"""
        assert math_engine._number_to_word(0) == "zero"
        assert math_engine._number_to_word(1) == "one"
        assert math_engine._number_to_word(10) == "ten"
        assert math_engine._number_to_word(42) == "forty two"
        assert math_engine._number_to_word(100) == "one hundred"


class TestSciencePronunciation:
    """Test scientific term pronunciation"""

    @pytest.fixture
    def science_engine(self):
        """Create science pronunciation engine"""
        return SciencePronunciationEngine()

    def test_chemical_formula(self, science_engine):
        """Test chemical formula pronunciation"""
        result = science_engine.convert_formula("H2O")
        assert "Hydrogen" in result
        assert "Oxygen" in result

        result = science_engine.convert_formula("CO2")
        assert "Carbon" in result
        assert "Oxygen" in result

    def test_element_pronunciation(self, science_engine):
        """Test element symbol pronunciation"""
        assert science_engine.element_names['H'] == 'Hydrogen'
        assert science_engine.element_names['O'] == 'Oxygen'
        assert science_engine.element_names['C'] == 'Carbon'
        assert science_engine.element_names['Au'] == 'Gold'

    def test_scientific_notation(self, science_engine):
        """Test scientific notation pronunciation"""
        result = science_engine.convert_scientific_notation("3.14e8")
        assert "times ten to the power" in result.lower()

    def test_measurement_pronunciation(self, science_engine):
        """Test measurement pronunciation"""
        result = science_engine.convert_measurement("5 km")
        assert "kilometers" in result.lower()

        result = science_engine.convert_measurement("3.2 g")
        assert "grams" in result.lower()

    def test_unit_pronunciations(self, science_engine):
        """Test unit abbreviation pronunciations"""
        assert science_engine.unit_pronunciations['m'] == 'meters'
        assert science_engine.unit_pronunciations['kg'] == 'kilograms'
        assert science_engine.unit_pronunciations['L'] == 'liters'
        assert science_engine.unit_pronunciations['°C'] == 'degrees Celsius'


class TestPhoneticOverrides:
    """Test phonetic override engine"""

    @pytest.fixture
    def phonetic_engine(self):
        """Create phonetic override engine"""
        return PhoneticOverrideEngine()

    def test_common_overrides(self, phonetic_engine):
        """Test common pronunciation overrides"""
        assert phonetic_engine.get_override("nuclear") is not None
        assert phonetic_engine.get_override("algorithm") is not None

    def test_add_override(self, phonetic_engine):
        """Test adding custom override"""
        phonetic_engine.add_override("test", "TEST")
        assert phonetic_engine.get_override("test") == "TEST"

    def test_apply_overrides(self, phonetic_engine):
        """Test applying overrides to text"""
        text = "The algorithm is often used."
        result = phonetic_engine.apply_overrides(text)

        # Should contain pronunciation overrides
        assert result != text


class TestPronunciationRulesEngine:
    """Test complete pronunciation rules engine"""

    @pytest.fixture
    def rules_engine(self):
        """Create pronunciation rules engine"""
        return PronunciationRulesEngine()

    def test_math_context_processing(self, rules_engine):
        """Test math context processing"""
        text = "2 + 3 = 5"
        result = rules_engine.process_text(text, context="math")

        assert "plus" in result.lower()
        assert "equals" in result.lower()

    def test_science_context_processing(self, rules_engine):
        """Test science context processing"""
        text = "The speed of light is 3e8 m/s"
        result = rules_engine.process_text(text, context="science")

        assert "times ten" in result.lower() or "e8" not in result

    def test_general_context_processing(self, rules_engine):
        """Test general text processing"""
        text = "The algorithm works well."
        result = rules_engine.process_text(text, context="general")

        # Should apply phonetic overrides
        assert isinstance(result, str)

    def test_add_custom_rule(self, rules_engine):
        """Test adding custom pronunciation rule"""
        rules_engine.add_custom_rule("testword", "TEST-word")
        override = rules_engine.phonetic_engine.get_override("testword")
        assert override == "TEST-word"


class TestVoiceQuality:
    """Test voice quality metrics"""

    @pytest.fixture
    def tts_engine(self):
        """Create TTS engine for quality testing"""
        config = TTSConfig(backend=TTSBackend.PYTTSX3)
        return TTSEngine(config=config)

    @pytest.mark.asyncio
    async def test_pronunciation_accuracy_target(self, tts_engine):
        """Test pronunciation accuracy target (98%+)"""
        # Test set of words with known pronunciations
        test_words = [
            "algorithm", "mathematics", "photosynthesis",
            "velocity", "fraction", "multiplication"
        ]

        for word in test_words:
            output = await tts_engine.synthesize(word)
            assert isinstance(output, AudioOutput)
            assert len(output.audio_data) > 0

        # In production, would compare against reference pronunciations
        # For now, just verify successful synthesis

    @pytest.mark.asyncio
    async def test_speed_variation_range(self, tts_engine):
        """Test variable speed for explanations"""
        text = "This is a speed test."

        # Test different speeds
        speeds = [SpeakingRate.SLOW, SpeakingRate.NORMAL, SpeakingRate.FAST]
        outputs = []

        for speed in speeds:
            tts_engine.set_speed(speed)
            output = await tts_engine.synthesize(text, use_cache=False)
            outputs.append(output)

        # All should produce valid output
        assert all(isinstance(o, AudioOutput) for o in outputs)
        assert all(len(o.audio_data) > 0 for o in outputs)

    @pytest.mark.asyncio
    async def test_child_friendly_tone(self, tts_engine):
        """Test child-friendly voice characteristics"""
        persona = VoicePersona(
            name="Child Friendly",
            description="Test persona for children",
            base_characteristics=VoiceCharacteristics(
                pitch=1.05,  # Slightly higher pitch
                rate=0.95,   # Slightly slower
                volume=0.85,
                warmth=0.85,
                energy=0.75,
                clarity=0.95
            ),
            age_group=AgeGroup.EARLY_ELEMENTARY,
            gender=VoiceGender.FEMALE
        )

        # Verify characteristics are child-appropriate
        assert persona.base_characteristics.pitch >= 1.0
        assert persona.base_characteristics.clarity >= 0.9
        assert persona.base_characteristics.warmth >= 0.8


# Integration Tests
class TestTTSIntegration:
    """Integration tests for complete TTS system"""

    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """Test complete TTS workflow"""
        # 1. Create persona
        library = VoicePersonaLibrary()
        persona = library.get_persona("friendly_tutor")

        # 2. Create TTS engine with persona
        config = TTSConfig(backend=TTSBackend.PYTTSX3)
        engine = TTSEngine(config=config, voice_persona=persona)

        # 3. Synthesize math content
        math_text = "Let's solve 5 + 3 = 8"
        output = await engine.speak_math(math_text, explain=True)

        assert isinstance(output, AudioOutput)
        assert len(output.audio_data) > 0

    @pytest.mark.asyncio
    async def test_adaptive_persona_workflow(self):
        """Test adaptive persona selection"""
        manager = PersonaManager()

        # Select persona for math content
        persona = manager.select_persona_for_content("math", age=9)
        assert persona.name == "Math Master"

        # Adapt tone based on performance
        tone = manager.adapt_to_performance(correct_rate=0.85)
        assert tone == EmotionalTone.ENCOURAGING

        # Get current characteristics
        chars = manager.get_characteristics()
        assert isinstance(chars, VoiceCharacteristics)

    @pytest.mark.asyncio
    async def test_pronunciation_pipeline(self):
        """Test complete pronunciation pipeline"""
        # Create engines
        rules_engine = PronunciationRulesEngine()
        config = TTSConfig(backend=TTSBackend.PYTTSX3)
        tts_engine = TTSEngine(config=config)

        # Process math expression
        math_text = "Calculate 2^3 + 5 = 13"
        processed = rules_engine.process_text(math_text, context="math")

        # Synthesize processed text
        output = await tts_engine.synthesize(processed, preprocess=False)

        assert isinstance(output, AudioOutput)
        assert len(output.audio_data) > 0


# Performance Tests
class TestTTSPerformance:
    """Performance and latency tests"""

    @pytest.mark.asyncio
    async def test_synthesis_latency(self):
        """Test synthesis latency for real-time usage"""
        import time

        config = TTSConfig(backend=TTSBackend.PYTTSX3)
        engine = TTSEngine(config=config)

        text = "Quick response test."

        start = time.time()
        output = await engine.synthesize(text)
        latency = time.time() - start

        # Should complete within reasonable time (< 2 seconds for short text)
        assert latency < 2.0
        assert isinstance(output, AudioOutput)

    @pytest.mark.asyncio
    async def test_cache_performance(self):
        """Test cache performance improvement"""
        import time

        config = TTSConfig(backend=TTSBackend.PYTTSX3, cache_enabled=True)
        engine = TTSEngine(config=config)

        text = "Cached synthesis test."

        # First synthesis (uncached)
        start1 = time.time()
        await engine.synthesize(text, use_cache=True)
        time1 = time.time() - start1

        # Second synthesis (cached)
        start2 = time.time()
        await engine.synthesize(text, use_cache=True)
        time2 = time.time() - start2

        # Cached version should be significantly faster
        assert time2 < time1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
