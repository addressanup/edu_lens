# EduLens TTS Quickstart Guide

Get started with child-friendly text-to-speech in 5 minutes!

## Installation

```bash
# Install core TTS dependencies
pip install pyttsx3 numpy scipy PyYAML

# Optional: Install high-quality online TTS
pip install edge-tts

# Install from requirements file
pip install -r requirements_audio.txt
```

## 30-Second Example

```python
import asyncio
from src.audio.tts_engine import TTSEngine, TTSConfig, TTSBackend

async def hello_world():
    # Create TTS engine
    config = TTSConfig(backend=TTSBackend.PYTTSX3)
    engine = TTSEngine(config=config)

    # Speak!
    output = await engine.synthesize("Hello! Let's learn together!")
    print(f"Generated {len(output.audio_data)} bytes of audio")

asyncio.run(hello_world())
```

## Common Use Cases

### 1. Math Tutoring

```python
from src.audio.tts_engine import TTSEngine, TTSConfig
from src.audio.voice_persona import VoicePersonaLibrary

# Use math-optimized voice
library = VoicePersonaLibrary()
persona = library.get_persona("math_master")

engine = TTSEngine(config=TTSConfig(), voice_persona=persona)

# Speak math with proper pronunciation
await engine.speak_math("2 + 3 = 5", explain=True)
# Says: "two plus three equals five"
```

### 2. Encouraging Feedback

```python
from src.audio.voice_persona import PersonaManager, EmotionalTone

manager = PersonaManager()
manager.set_persona("cheerful_guide")
manager.set_tone(EmotionalTone.CELEBRATING)

engine = TTSEngine(voice_persona=manager.current_persona)
await engine.synthesize("Fantastic! You did it!")
```

### 3. Patient Explanation

```python
# Auto-select appropriate voice for young learner
manager = PersonaManager()
persona = manager.select_persona_for_content("science", age=7)

engine = TTSEngine(voice_persona=persona)
engine.set_speed(0.85)  # Slow down for comprehension

text = "Photosynthesis is how plants make food."
await engine.speak_with_pauses(text)  # Adds helpful pauses
```

### 4. Adaptive Tone Based on Performance

```python
manager = PersonaManager()
manager.set_persona("friendly_tutor")

# Student doing well (85% correct)
tone = manager.adapt_to_performance(correct_rate=0.85)
# Returns: EmotionalTone.ENCOURAGING

# Student struggling (50% correct, 3 struggles)
tone = manager.adapt_to_performance(correct_rate=0.50, struggle_indicators=3)
# Returns: EmotionalTone.PATIENT

# Use the adapted tone
chars = manager.get_characteristics()
engine = TTSEngine(voice_persona=manager.current_persona)
```

## Voice Personas Quick Reference

| Persona | Best For | Age Group | Characteristics |
|---------|----------|-----------|-----------------|
| `friendly_tutor` | General instruction | 6-12 | Warm, patient, clear |
| `patient_helper` | Struggling students | 6-12 | Calm, reassuring, slow |
| `cheerful_guide` | Young learners | 6-8 | Energetic, fun, engaging |
| `wise_mentor` | Older students | 11-12 | Authoritative, clear |
| `science_explorer` | Science topics | 9-10 | Curious, precise |
| `math_master` | Math instruction | 6-12 | Methodical, clear |

## Speed Presets

```python
engine.set_speed(0.80)  # Slow explanation
engine.set_speed(0.90)  # Patient teaching
engine.set_speed(1.00)  # Normal
engine.set_speed(1.15)  # Quick feedback
engine.set_speed(1.25)  # Energetic
```

## Pronunciation Examples

### Math Expressions

```python
from src.audio.pronunciation_rules import MathPronunciationEngine

math = MathPronunciationEngine()

math.convert_expression("2 + 3")      # "two plus three"
math.convert_expression("10 ÷ 2")     # "ten divided by two"
math.convert_expression("x²")         # "x squared"
math.convert_expression("1/2")        # "one half"
math.convert_expression("3.14")       # "three point one four"
```

### Science Terms

```python
from src.audio.pronunciation_rules import SciencePronunciationEngine

science = SciencePronunciationEngine()

science.convert_formula("H2O")                    # "Hydrogen with 2 atoms Oxygen"
science.convert_formula("CO2")                    # "Carbon with 2 atoms Oxygen"
science.convert_scientific_notation("3.14e8")     # "3.14 times ten to the power of 8"
science.convert_measurement("5 km")               # "5 kilometers"
```

## Run the Demo

```bash
# Full feature demonstration
python examples/tts_demo.py

# Run tests
pytest tests/audio/test_tts.py -v
```

## Configuration

Edit `configs/audio/voice_persona.yaml` to customize:

- Voice characteristics (pitch, rate, volume)
- Speed presets
- Emotional tone settings
- SSML templates
- Pronunciation rules

## Troubleshooting

**Q: No audio output?**
```bash
# Check if pyttsx3 is installed
pip install pyttsx3

# Try Edge TTS instead (requires internet)
config = TTSConfig(backend=TTSBackend.EDGE_TTS)
```

**Q: Math symbols not pronounced correctly?**
```python
# Use speak_math() instead of synthesize()
await engine.speak_math("2 + 3 = 5")
```

**Q: Want better quality?**
```bash
# Install Coqui TTS (high quality, ~500MB)
pip install TTS

# Use Coqui backend
config = TTSConfig(backend=TTSBackend.COQUI)
```

## Next Steps

- Read the [full TTS documentation](TTS_SYSTEM_README.md)
- Explore [voice persona customization](../configs/audio/voice_persona.yaml)
- Learn about [pronunciation rules](../src/audio/pronunciation_rules.py)
- Check out [complete examples](../examples/tts_demo.py)

## Complete Workflow Example

```python
import asyncio
from src.audio.tts_engine import TTSEngine, TTSConfig
from src.audio.voice_persona import PersonaManager, EmotionalTone
from src.audio.pronunciation_rules import PronunciationRulesEngine

async def educational_workflow():
    # 1. Setup
    manager = PersonaManager()
    rules = PronunciationRulesEngine()

    # 2. Select persona for 9-year-old math student
    persona = manager.select_persona_for_content("math", age=9)

    # 3. Set encouraging tone
    manager.set_tone(EmotionalTone.ENCOURAGING)

    # 4. Create engine
    engine = TTSEngine(voice_persona=persona)

    # 5. Process and speak math content
    content = "Great work! Now let's solve 2 + 3 = ?"
    processed = rules.process_text(content, context="math")

    # 6. Synthesize with pauses
    output = await engine.speak_with_pauses(processed)

    print(f"Generated {len(output.audio_data)} bytes")
    print(f"Duration: {output.duration_ms:.2f} ms")

    # 7. Adapt to student performance
    tone = manager.adapt_to_performance(correct_rate=0.85)
    print(f"Next tone: {tone.value}")

asyncio.run(educational_workflow())
```

## Tips

1. **Cache frequently used phrases** - Enable caching for faster responses
2. **Use appropriate persona** - Match persona to subject and age
3. **Add pauses for complex content** - Use `speak_with_pauses()`
4. **Process math/science terms** - Always use pronunciation engines
5. **Adapt to performance** - Dynamically adjust tone based on student success

## Support

- Full docs: `docs/TTS_SYSTEM_README.md`
- Examples: `examples/tts_demo.py`
- Tests: `tests/audio/test_tts.py`
- Config: `configs/audio/voice_persona.yaml`
