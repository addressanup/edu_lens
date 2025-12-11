# EduLens Text-to-Speech (TTS) System

## Overview

The EduLens TTS system provides child-friendly, educational text-to-speech with advanced features for optimal learning experiences. The system is designed specifically for ages 6-12 with pronunciation accuracy of 98%+.

## Features

### Core Capabilities

- **Multiple TTS Backends**: Support for offline and online engines
  - `pyttsx3` (offline, cross-platform)
  - `edge-tts` (Microsoft Edge, requires internet)
  - `coqui-tts` (high-quality, offline)

- **Child-Friendly Voices**: Age-appropriate voice characteristics
  - Optimized pitch and speaking rate
  - Natural, encouraging tone
  - Clear articulation

- **Educational Optimizations**
  - Math expression pronunciation (÷, ×, fractions, exponents)
  - Science term pronunciation (formulas, measurements)
  - Pedagogical pauses for better comprehension
  - Variable speed for different content types

- **Voice Personas**: Pre-configured voice personalities
  - Friendly Tutor (warm, patient)
  - Patient Helper (calm, reassuring)
  - Cheerful Guide (energetic, fun)
  - Wise Mentor (authoritative, clear)
  - Science Explorer (curious, precise)
  - Math Master (methodical, clear)

- **Emotional Tones**: Context-aware emotional delivery
  - Encouraging (for positive reinforcement)
  - Explaining (for instruction)
  - Celebrating (for achievements)
  - Patient (for struggling students)
  - Reassuring (for confidence building)

## Installation

### Required Dependencies

```bash
# Core TTS engine (offline)
pip install pyttsx3

# Optional: High-quality TTS (offline)
pip install TTS

# Optional: Microsoft Edge TTS (requires internet)
pip install edge-tts

# Audio processing
pip install numpy scipy
```

### System Requirements

- **pyttsx3**: Requires system TTS engine (espeak, sapi5, nsss)
- **Coqui TTS**: Requires ~500MB for models
- **Edge TTS**: Requires internet connection

## Quick Start

### Basic Usage

```python
import asyncio
from src.audio.tts_engine import TTSEngine, TTSConfig, TTSBackend

async def main():
    # Create TTS engine
    config = TTSConfig(backend=TTSBackend.PYTTSX3)
    engine = TTSEngine(config=config)

    # Synthesize speech
    text = "Hello! Let's learn together!"
    output = await engine.synthesize(text)

    print(f"Generated {len(output.audio_data)} bytes")
    print(f"Duration: {output.duration_ms:.2f} ms")

asyncio.run(main())
```

### Using Voice Personas

```python
from src.audio.tts_engine import TTSEngine, TTSConfig
from src.audio.voice_persona import VoicePersonaLibrary

# Load persona library
library = VoicePersonaLibrary()
persona = library.get_persona("friendly_tutor")

# Create engine with persona
config = TTSConfig()
engine = TTSEngine(config=config, voice_persona=persona)

# Synthesize with persona characteristics
output = await engine.synthesize("Great job!")
```

### Math Expression Pronunciation

```python
# Automatic math pronunciation
output = await engine.speak_math("2 + 3 = 5", explain=True)

# Or use pronunciation engine directly
from src.audio.pronunciation_rules import MathPronunciationEngine

math_engine = MathPronunciationEngine()
spoken = math_engine.convert_expression("x² + 2x + 1")
# Output: "x squared plus two x plus one"
```

### Science Term Pronunciation

```python
from src.audio.pronunciation_rules import SciencePronunciationEngine

science_engine = SciencePronunciationEngine()

# Chemical formula
spoken = science_engine.convert_formula("H2O")
# Output: "Hydrogen with 2 atoms Oxygen"

# Scientific notation
spoken = science_engine.convert_scientific_notation("3.14e8")
# Output: "3.14 times ten to the power of 8"

# Measurements
spoken = science_engine.convert_measurement("5 km")
# Output: "5 kilometers"
```

### Adaptive Persona Selection

```python
from src.audio.voice_persona import PersonaManager, EmotionalTone

manager = PersonaManager()

# Auto-select persona based on content and age
persona = manager.select_persona_for_content("math", age=9)
# Returns: Math Master persona

# Adapt tone based on performance
tone = manager.adapt_to_performance(correct_rate=0.85)
# Returns: EmotionalTone.ENCOURAGING

# Get current characteristics
chars = manager.get_characteristics()
```

## Architecture

### Component Structure

```
src/audio/
├── tts_engine.py              # Main TTS engine
│   ├── TTSEngine              # Primary interface
│   ├── TTSConfig              # Configuration
│   ├── TTSBackendInterface    # Backend abstraction
│   ├── Pyttsx3Backend         # Offline backend
│   ├── EdgeTTSBackend         # Online backend
│   └── CoquiTTSBackend        # High-quality offline
│
├── voice_persona.py           # Voice personality system
│   ├── VoicePersona           # Persona definition
│   ├── VoiceCharacteristics   # Voice parameters
│   ├── EmotionalProfile       # Tone profiles
│   ├── VoicePersonaLibrary    # Preset personas
│   └── PersonaManager         # Dynamic selection
│
└── pronunciation_rules.py     # Pronunciation engine
    ├── MathPronunciationEngine      # Math expressions
    ├── SciencePronunciationEngine   # Science terms
    ├── PhoneticOverrideEngine       # Custom overrides
    └── PronunciationRulesEngine     # Main processor
```

### Configuration Files

```
configs/audio/
└── voice_persona.yaml         # Voice configuration
    ├── global                 # Global settings
    ├── defaults               # Default parameters
    ├── speed_presets          # Speed configurations
    ├── personas               # Persona definitions
    ├── emotional_tones        # Tone settings
    └── ssml_templates         # SSML templates
```

## API Reference

### TTSEngine

```python
class TTSEngine:
    def __init__(
        config: Optional[TTSConfig] = None,
        voice_persona: Optional[VoicePersona] = None
    )

    async def synthesize(
        text: str,
        use_cache: bool = True,
        preprocess: bool = True
    ) -> AudioOutput

    async def synthesize_streaming(
        text: str,
        preprocess: bool = True
    ) -> AsyncGenerator[bytes, None]

    def set_voice(voice_id: str) -> None
    def set_speed(rate: Union[float, SpeakingRate]) -> None
    def set_emphasis(level: EmphasisLevel) -> None

    async def speak_math(
        expression: str,
        explain: bool = True
    ) -> AudioOutput

    async def speak_with_pauses(
        text: str,
        pause_points: Optional[List[int]] = None,
        pause_duration_ms: int = 500
    ) -> AudioOutput

    def list_voices() -> List[Dict[str, str]]
    def clear_cache() -> None
```

### VoicePersona

```python
@dataclass
class VoicePersona:
    name: str
    description: str
    base_characteristics: VoiceCharacteristics
    age_group: AgeGroup
    gender: VoiceGender
    emotional_profiles: Dict[EmotionalTone, EmotionalProfile]

    def get_characteristics(
        tone: Optional[EmotionalTone] = None
    ) -> VoiceCharacteristics

    def adjust_for_context(
        context: str,
        difficulty: float = 0.5
    ) -> VoiceCharacteristics
```

### MathPronunciationEngine

```python
class MathPronunciationEngine:
    def convert_expression(
        expression: str,
        verbose: bool = True
    ) -> str

    # Supports:
    # - Basic operators: +, -, ×, ÷, =
    # - Fractions: 1/2 → "one half"
    # - Exponents: x² → "x squared"
    # - Parentheses: (a + b)
    # - Decimals: 3.14 → "three point one four"
```

### SciencePronunciationEngine

```python
class SciencePronunciationEngine:
    def convert_formula(formula: str) -> str
    def convert_scientific_notation(notation: str) -> str
    def convert_measurement(measurement: str) -> str
    def pronounce_term(term: str) -> str

    # Supports:
    # - Chemical formulas: H2O, CO2
    # - Scientific notation: 3.14e8
    # - Measurements: 5 km, 3.2 g, 25 °C
    # - Technical terms: photosynthesis, mitochondria
```

## Configuration

### Voice Persona Configuration

```yaml
# configs/audio/voice_persona.yaml

personas:
  friendly_tutor:
    name: "Friendly Tutor"
    description: "Warm, encouraging voice"
    characteristics:
      pitch: 1.05
      rate: 0.95
      volume: 0.85
      warmth: 0.85
      energy: 0.70
      clarity: 0.95
    age_group: "6-12"
    gender: "female"
    tags:
      - patient
      - warm
```

### Speed Presets

```yaml
speed_presets:
  slow_explanation:
    rate: 0.80
    description: "Very slow, clear pace"

  patient_teaching:
    rate: 0.90
    description: "Patient, measured pace"

  normal:
    rate: 1.0
    description: "Normal conversational pace"
```

### Emotional Tones

```yaml
emotional_tones:
  encouraging:
    pitch_adjust: 1.05
    rate_adjust: 0.95
    volume_adjust: 1.05
    warmth_adjust: 1.10
    energy_adjust: 1.20
    phrases:
      - "Great job!"
      - "Keep going!"
```

## Performance

### Pronunciation Accuracy

- **Target**: 98%+ accuracy
- **Math symbols**: 100% coverage
- **Science terms**: Common K-12 vocabulary
- **Custom overrides**: Phonetic spelling support

### Latency

- **pyttsx3**: < 500ms for short text
- **Edge TTS**: < 1s (network dependent)
- **Coqui TTS**: ~1-2s for high quality

### Caching

- Automatic caching of synthesized audio
- Cache key: text + voice parameters
- Significant speedup for repeated content

## Testing

### Run Test Suite

```bash
# Run all TTS tests
pytest tests/audio/test_tts.py -v

# Run specific test categories
pytest tests/audio/test_tts.py::TestTTSEngine -v
pytest tests/audio/test_tts.py::TestVoicePersona -v
pytest tests/audio/test_tts.py::TestMathPronunciation -v

# Run with coverage
pytest tests/audio/test_tts.py --cov=src.audio.tts_engine --cov-report=html
```

### Test Coverage

- **Voice quality tests**: Synthesis, streaming, caching
- **Pronunciation accuracy**: Math, science, general terms
- **Speed variation**: Multiple rates, accuracy
- **Persona system**: Selection, adaptation, characteristics
- **Integration tests**: Complete workflows
- **Performance tests**: Latency, cache effectiveness

## Examples

### Complete Educational Workflow

```python
from src.audio.tts_engine import TTSEngine, TTSConfig
from src.audio.voice_persona import PersonaManager, EmotionalTone
from src.audio.pronunciation_rules import PronunciationRulesEngine

# 1. Set up adaptive persona
manager = PersonaManager()
persona = manager.select_persona_for_content("math", age=9)
manager.set_tone(EmotionalTone.ENCOURAGING)

# 2. Create TTS engine
config = TTSConfig()
engine = TTSEngine(config=config, voice_persona=persona)

# 3. Process educational content
rules_engine = PronunciationRulesEngine()
content = "Great work! Now solve 2 + 3 = ?"
processed = rules_engine.process_text(content, context="math")

# 4. Synthesize with pauses
output = await engine.speak_with_pauses(processed)

# 5. Adapt based on student performance
new_tone = manager.adapt_to_performance(correct_rate=0.85)
```

### Custom Pronunciation Rules

```python
from src.audio.pronunciation_rules import PronunciationRulesEngine

rules_engine = PronunciationRulesEngine()

# Add custom pronunciation
rules_engine.add_custom_rule(
    word="eigenvalue",
    pronunciation="EYE-gen-value",
    context="math"
)

# Use in synthesis
text = "Calculate the eigenvalue of the matrix."
processed = rules_engine.process_text(text, context="math")
```

### Create Custom Persona

```python
from src.audio.voice_persona import (
    VoicePersona,
    VoiceCharacteristics,
    AgeGroup,
    VoiceGender,
    VoicePersonaLibrary
)

# Define custom persona
custom_persona = VoicePersona(
    name="Super Tutor",
    description="Energetic teaching voice",
    base_characteristics=VoiceCharacteristics(
        pitch=1.08,
        rate=1.0,
        volume=0.90,
        warmth=0.85,
        energy=0.90,
        clarity=0.95
    ),
    age_group=AgeGroup.LATE_ELEMENTARY,
    gender=VoiceGender.FEMALE,
    tags=["energetic", "teaching"]
)

# Add to library
library = VoicePersonaLibrary()
library.add_persona(custom_persona)
```

## Troubleshooting

### Common Issues

**Issue**: No audio output
- **Solution**: Check TTS backend is installed (`pip install pyttsx3`)
- **Solution**: Verify system audio is working
- **Solution**: Try different backend (Edge TTS)

**Issue**: Poor pronunciation quality
- **Solution**: Use `speak_math()` for math expressions
- **Solution**: Add custom phonetic overrides
- **Solution**: Try Coqui TTS for higher quality

**Issue**: Slow synthesis
- **Solution**: Enable caching with `use_cache=True`
- **Solution**: Use faster backend (pyttsx3)
- **Solution**: Reduce sample rate in config

### Debug Mode

```python
import logging

logging.basicConfig(level=logging.DEBUG)

# TTS engine will now log detailed information
engine = TTSEngine(config=config)
```

## Best Practices

### For Educational Content

1. **Use appropriate persona** for subject and age
2. **Enable pedagogical pauses** for complex explanations
3. **Slow down for difficult concepts** (0.85x - 0.90x rate)
4. **Process math/science terms** with pronunciation engines
5. **Adapt tone** based on student performance

### For Performance

1. **Enable caching** for frequently used phrases
2. **Use offline backends** (pyttsx3) for low latency
3. **Pre-process text** once, cache results
4. **Batch similar content** to reduce backend switches
5. **Monitor synthesis latency** and adjust settings

### For Quality

1. **Test pronunciation** of domain-specific terms
2. **Add phonetic overrides** for mispronounced words
3. **Use SSML** for fine control when needed
4. **Validate with target age group** (6-12)
5. **Measure and maintain** 98%+ accuracy

## Contributing

### Adding New Pronunciation Rules

1. Edit `src/audio/pronunciation_rules.py`
2. Add pattern to appropriate engine
3. Test with `tests/audio/test_tts.py`
4. Update documentation

### Creating New Personas

1. Define in `configs/audio/voice_persona.yaml`
2. Test with different content types
3. Validate age-appropriateness
4. Add to library initialization

## License

Part of the EduLens project. See main project LICENSE.

## Support

For issues, questions, or contributions:
- Create an issue in the EduLens repository
- Refer to the main project documentation
- Contact the EduLens development team
