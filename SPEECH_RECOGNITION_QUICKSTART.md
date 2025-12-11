# Speech Recognition Quick Start Guide

## Installation

```bash
# Dependencies already in requirements.txt
pip install openai-whisper torch numpy scipy pyyaml
```

## Basic Usage (5 lines of code)

```python
import asyncio
from src.audio import SpeechRecognizer, SpeechConfig

async def transcribe():
    config = SpeechConfig(model_size="base", child_mode=True)
    recognizer = SpeechRecognizer(config)
    await recognizer.initialize()

    result = await recognizer.transcribe("audio.wav")
    print(f"Text: {result.text}")
    print(f"Confidence: {result.confidence:.2%}")

    await recognizer.close()

asyncio.run(transcribe())
```

## Complete Pipeline (Child Speech + Educational Vocabulary)

```python
import asyncio
from src.audio import (
    SpeechRecognizer, SpeechConfig,
    ChildSpeechAdapter, AgeGroup,
    VocabularyContextManager, Subject
)

async def complete_pipeline():
    # Initialize
    config = SpeechConfig(model_size="base", child_mode=True)
    recognizer = SpeechRecognizer(config)
    await recognizer.initialize()

    adapter = ChildSpeechAdapter(age_group=AgeGroup.EARLY_ELEMENTARY)
    context = VocabularyContextManager()

    # Setup vocabulary for math lesson
    context.set_context(Subject.MATHEMATICS)
    vocab = context.get_context_vocabulary()
    recognizer.set_vocabulary_boost(vocab)

    # Process audio
    adapted_audio = adapter.preprocess_audio(audio)
    result = await recognizer.transcribe(adapted_audio)

    # Clean up transcription
    clean_text, confidence = adapter.postprocess_transcription(
        result.text, result.confidence
    )

    print(f"Result: {clean_text} ({confidence:.2%} confidence)")
    await recognizer.close()

asyncio.run(complete_pipeline())
```

## Configuration

Edit `configs/audio/speech_config.yaml`:

```yaml
model:
  size: base              # tiny, base, small, medium, large
  device: cpu             # cpu, cuda

child_speech:
  enable: true
  age_group: 6-12         # 6-8, 9-10, 11-12, 6-12

vocabulary:
  enable: true
  default_subjects:
    - mathematics
    - science
    - reading
```

## Key Components

### 1. SpeechRecognizer
```python
recognizer = SpeechRecognizer(config)
await recognizer.initialize()

# Batch transcription
result = await recognizer.transcribe(audio)

# Streaming
async for result in recognizer.transcribe_streaming(audio_stream):
    print(result.text)

# Vocabulary boost
recognizer.set_vocabulary_boost(["addition", "multiply", "fraction"])
```

### 2. ChildSpeechAdapter
```python
adapter = ChildSpeechAdapter(age_group=AgeGroup.EARLY_ELEMENTARY)

# Preprocess audio
adapted = adapter.preprocess_audio(audio)

# Clean transcription
clean_text, confidence = adapter.postprocess_transcription(text, conf)
```

### 3. EducationalVocabulary
```python
vocab = EducationalVocabulary()

# Get vocabulary
math_terms = vocab.get_math_vocabulary("operations")
science_terms = vocab.get_science_vocabulary("life_science")

# Boost recognition
recognizer.set_vocabulary_boost(math_terms + science_terms)
```

### 4. VocabularyContextManager
```python
context = VocabularyContextManager()

# Set context
context.set_context(Subject.MATHEMATICS)

# Get context-aware vocabulary
vocab = context.get_context_vocabulary()
```

## Age Groups

```python
from src.audio import AgeGroup

# Age-specific profiles
AgeGroup.EARLY_ELEMENTARY  # 6-8 years (highest adaptations)
AgeGroup.LATE_ELEMENTARY   # 9-10 years (moderate)
AgeGroup.PRE_TEEN          # 11-12 years (minimal)
AgeGroup.GENERAL           # 6-12 years (average)
```

## Subjects

```python
from src.audio import Subject

Subject.MATHEMATICS      # Math terms (150+ words)
Subject.SCIENCE         # Science terms (120+ words)
Subject.READING         # Reading/LA terms (80+ words)
Subject.GENERAL         # General academic (30+ words)
```

## Testing

```bash
# Run all tests
pytest tests/audio/test_speech_recognition.py -v

# Run specific test
pytest tests/audio/test_speech_recognition.py::TestSpeechRecognizer -v

# With coverage
pytest tests/audio/test_speech_recognition.py --cov=src.audio
```

## Examples

```bash
# Run complete examples
python examples/speech_recognition_example.py
```

## Performance Targets

- Accuracy: 90%+ on child speech
- Latency: 0.3-0.5x real-time (batch), ~500ms (streaming)
- Memory: ~150MB (tiny model), ~300MB (base model)
- CPU: <15% (smart glasses), 20-30% (laptop)

## Common Issues

### Low Accuracy
```python
# Enable child adaptations
config = SpeechConfig(child_mode=True, age_group="6-8")

# Boost vocabulary
recognizer.set_vocabulary_boost(educational_terms)
```

### High Latency
```python
# Use smaller model
config = SpeechConfig(model_size="tiny")

# Enable low-latency streaming
config.chunk_duration = 5.0
```

### Memory Issues
```python
# Use int8 quantization
config = SpeechConfig(compute_type="int8", optimize_memory=True)
```

## Files

- Implementation: `src/audio/speech_recognizer.py`, `child_speech_adapter.py`, `educational_vocabulary.py`
- Config: `configs/audio/speech_config.yaml`
- Tests: `tests/audio/test_speech_recognition.py`
- Docs: `SPEECH_RECOGNITION_README.md`
- Examples: `examples/speech_recognition_example.py`

## Support

See full documentation: `SPEECH_RECOGNITION_README.md`

For detailed implementation: `SPEECH_RECOGNITION_IMPLEMENTATION_SUMMARY.md`

---

**Quick Reference**: Keep this guide handy for rapid development!
