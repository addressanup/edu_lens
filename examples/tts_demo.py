"""
EduLens TTS Demo

Demonstrates the child-friendly Text-to-Speech system with:
- Multiple voice personas
- Emotional tones
- Math and science pronunciation
- Pedagogical pauses
- Speed variation
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.audio.pronunciation_rules import (
    MathPronunciationEngine,
    PronunciationRulesEngine,
    SciencePronunciationEngine,
)
from src.audio.tts_engine import SpeakingRate, TTSBackend, TTSConfig, TTSEngine
from src.audio.voice_persona import EmotionalTone, PersonaManager, VoicePersonaLibrary


async def demo_basic_synthesis():
    """Demonstrate basic text-to-speech synthesis"""
    print("\n=== Basic TTS Synthesis ===")

    config = TTSConfig(backend=TTSBackend.PYTTSX3)
    engine = TTSEngine(config=config)

    text = "Hello! I'm your friendly tutor. Let's learn together!"
    print(f"Text: {text}")

    output = await engine.synthesize(text)
    print(f"Audio generated: {len(output.audio_data)} bytes")
    print(f"Duration: {output.duration_ms:.2f} ms")
    print(f"Sample rate: {output.sample_rate} Hz")


async def demo_voice_personas():
    """Demonstrate different voice personas"""
    print("\n=== Voice Personas ===")

    library = VoicePersonaLibrary()

    # List available personas
    print("\nAvailable personas:")
    for name, persona in library.personas.items():
        print(f"  - {persona.name}: {persona.description}")

    # Try different personas
    config = TTSConfig(backend=TTSBackend.PYTTSX3)
    text = "Great job! You're doing wonderful work!"

    for persona_name in ["friendly_tutor", "cheerful_guide", "patient_helper"]:
        persona = library.get_persona(persona_name)
        engine = TTSEngine(config=config, voice_persona=persona)

        print(f"\n{persona.name}:")
        output = await engine.synthesize(text)
        print(f"  Generated {len(output.audio_data)} bytes")


async def demo_emotional_tones():
    """Demonstrate emotional tone variations"""
    print("\n=== Emotional Tones ===")

    library = VoicePersonaLibrary()
    persona = library.get_persona("friendly_tutor")

    config = TTSConfig(backend=TTSBackend.PYTTSX3)
    engine = TTSEngine(config=config, voice_persona=persona)

    tones = [
        (EmotionalTone.ENCOURAGING, "Keep going, you're doing great!"),
        (EmotionalTone.EXPLAINING, "Let me explain how this works."),
        (EmotionalTone.CELEBRATING, "Fantastic! You solved it!"),
        (EmotionalTone.PATIENT, "It's okay, let's try again slowly."),
    ]

    for tone, text in tones:
        print(f"\n{tone.value.title()} Tone:")
        print(f"  Text: {text}")

        # Get characteristics for this tone
        chars = persona.get_characteristics(tone)
        print(f"  Pitch: {chars.pitch}, Rate: {chars.rate}, Energy: {chars.energy}")

        output = await engine.synthesize(text)
        print(f"  Generated {len(output.audio_data)} bytes")


async def demo_math_pronunciation():
    """Demonstrate mathematical expression pronunciation"""
    print("\n=== Math Pronunciation ===")

    math_engine = MathPronunciationEngine()

    expressions = [
        "2 + 3 = 5",
        "10 ÷ 2 = 5",
        "x² + 2x + 1",
        "1/2 + 1/4 = 3/4",
        "(5 - 3) × 4 = 8",
    ]

    print("\nMath expressions converted to speech:")
    for expr in expressions:
        spoken = math_engine.convert_expression(expr)
        print(f"  {expr:20s} → {spoken}")

    # Synthesize a math problem
    config = TTSConfig(backend=TTSBackend.PYTTSX3)
    engine = TTSEngine(config=config)

    math_text = "Let's solve 2 + 3. Two plus three equals five."
    print(f"\nSynthesizing: {math_text}")
    output = await engine.speak_math(math_text, explain=True)
    print(f"Generated {len(output.audio_data)} bytes with pedagogical pauses")


async def demo_science_pronunciation():
    """Demonstrate science term pronunciation"""
    print("\n=== Science Pronunciation ===")

    science_engine = SciencePronunciationEngine()

    # Chemical formulas
    formulas = ["H2O", "CO2", "NaCl", "C6H12O6"]
    print("\nChemical formulas:")
    for formula in formulas:
        spoken = science_engine.convert_formula(formula)
        print(f"  {formula:10s} → {spoken}")

    # Scientific notation
    notations = ["3.14e8", "6.022e23", "1.6e-19"]
    print("\nScientific notation:")
    for notation in notations:
        spoken = science_engine.convert_scientific_notation(notation)
        print(f"  {notation:10s} → {spoken}")

    # Measurements
    measurements = ["5 km", "3.2 g", "25 °C", "100 mL"]
    print("\nMeasurements:")
    for measurement in measurements:
        spoken = science_engine.convert_measurement(measurement)
        print(f"  {measurement:10s} → {spoken}")


async def demo_speed_variation():
    """Demonstrate speaking speed variation"""
    print("\n=== Speed Variation ===")

    config = TTSConfig(backend=TTSBackend.PYTTSX3)
    engine = TTSEngine(config=config)

    text = "This is a speed variation test."

    speeds = [
        (SpeakingRate.SLOW, "Slow (0.75x)"),
        (SpeakingRate.NORMAL, "Normal (1.0x)"),
        (SpeakingRate.FAST, "Fast (1.25x)"),
    ]

    print("\nSynthesizing at different speeds:")
    for speed, description in speeds:
        engine.set_speed(speed)
        output = await engine.synthesize(text, use_cache=False)
        print(
            f"  {description:20s}: {len(output.audio_data)} bytes, " f"{output.duration_ms:.2f} ms"
        )


async def demo_pedagogical_pauses():
    """Demonstrate pedagogical pauses"""
    print("\n=== Pedagogical Pauses ===")

    config = TTSConfig(backend=TTSBackend.PYTTSX3)
    engine = TTSEngine(config=config)

    text = "First, we add the numbers. Then, we multiply the result. Finally, we have our answer."

    print(f"\nText: {text}")

    # Without pauses
    output_no_pause = await engine.synthesize(text, preprocess=False)
    print(f"Without pauses: {output_no_pause.duration_ms:.2f} ms")

    # With pauses
    output_with_pause = await engine.speak_with_pauses(text)
    print(f"With pauses: {output_with_pause.duration_ms:.2f} ms")
    print(f"Pause time added: {output_with_pause.duration_ms - output_no_pause.duration_ms:.2f} ms")


async def demo_adaptive_persona():
    """Demonstrate adaptive persona selection"""
    print("\n=== Adaptive Persona Selection ===")

    manager = PersonaManager()

    # Test scenarios
    scenarios = [
        ("math", 7, "Math for 7-year-old"),
        ("science", 11, "Science for 11-year-old"),
        ("reading", 9, "Reading for 9-year-old"),
    ]

    print("\nAutomatic persona selection:")
    for subject, age, description in scenarios:
        persona = manager.select_persona_for_content(subject, age)
        print(f"  {description:30s} → {persona.name}")

    # Performance-based tone adaptation
    print("\nPerformance-based tone adaptation:")
    performance_scenarios = [
        (0.95, 0, "High performance (95% correct)"),
        (0.80, 0, "Good performance (80% correct)"),
        (0.60, 4, "Struggling (60% correct, 4 struggle indicators)"),
    ]

    for correct_rate, struggles, description in performance_scenarios:
        tone = manager.adapt_to_performance(correct_rate, struggles)
        print(f"  {description:50s} → {tone.value}")


async def demo_complete_workflow():
    """Demonstrate complete TTS workflow"""
    print("\n=== Complete Workflow ===")

    # 1. Set up persona manager
    manager = PersonaManager()

    # 2. Select persona for math tutoring
    persona = manager.select_persona_for_content("math", age=9)
    print(f"\nSelected persona: {persona.name}")

    # 3. Set encouraging tone
    manager.set_tone(EmotionalTone.ENCOURAGING)
    print(f"Emotional tone: {manager.current_tone.value}")

    # 4. Create TTS engine with persona
    config = TTSConfig(backend=TTSBackend.PYTTSX3)
    engine = TTSEngine(config=config, voice_persona=persona)

    # 5. Process math problem with pronunciation rules
    rules_engine = PronunciationRulesEngine()
    math_problem = "Great job! Now let's try 5 + 3 = 8"
    processed_text = rules_engine.process_text(math_problem, context="math")

    print(f"\nOriginal: {math_problem}")
    print(f"Processed: {processed_text}")

    # 6. Synthesize with pedagogical pauses
    output = await engine.speak_with_pauses(processed_text)

    print(f"\nFinal output:")
    print(f"  Audio size: {len(output.audio_data)} bytes")
    print(f"  Duration: {output.duration_ms:.2f} ms")
    print(f"  Sample rate: {output.sample_rate} Hz")


async def demo_pronunciation_accuracy():
    """Demonstrate pronunciation accuracy features"""
    print("\n=== Pronunciation Accuracy ===")

    rules_engine = PronunciationRulesEngine()

    # Test vocabulary
    test_words = [
        ("algorithm", "general"),
        ("photosynthesis", "science"),
        ("fraction", "math"),
    ]

    print("\nPhonetic pronunciation guides:")
    for word, context in test_words:
        # Get phonetic override if available
        phonetic = rules_engine.phonetic_engine.get_override(word)
        if phonetic:
            print(f"  {word:20s} → {phonetic}")
        else:
            print(f"  {word:20s} → (standard pronunciation)")


async def main():
    """Run all demos"""
    print("=" * 60)
    print("EduLens TTS System Demo")
    print("=" * 60)

    demos = [
        ("Basic Synthesis", demo_basic_synthesis),
        ("Voice Personas", demo_voice_personas),
        ("Emotional Tones", demo_emotional_tones),
        ("Math Pronunciation", demo_math_pronunciation),
        ("Science Pronunciation", demo_science_pronunciation),
        ("Speed Variation", demo_speed_variation),
        ("Pedagogical Pauses", demo_pedagogical_pauses),
        ("Adaptive Persona", demo_adaptive_persona),
        ("Pronunciation Accuracy", demo_pronunciation_accuracy),
        ("Complete Workflow", demo_complete_workflow),
    ]

    for name, demo_func in demos:
        try:
            await demo_func()
        except Exception as e:
            print(f"\nError in {name}: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
