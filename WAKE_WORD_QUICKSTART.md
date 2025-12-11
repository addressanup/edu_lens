# Wake Word Detection - Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies

```bash
cd /Users/anuppandey/Desktop/edu_lens
pip install -r requirements_audio.txt
```

### 2. Run Demo

```bash
python examples/wake_word_demo.py
```

Select option **1** for basic streaming detection.

### 3. Speak "Hey EduLens"

The system will detect the wake word and display:
- Detection confidence
- Latency
- Timestamp

### 4. Stop with Ctrl+C

Press `Ctrl+C` to stop and see statistics.

## Quick Code Example

```python
from audio import WakeWordDetector

# Create detector
detector = WakeWordDetector(sensitivity=0.5)

# Register callback
detector.on_wake_word(lambda r: print(f"Detected! {r.confidence:.0%}"))

# Start listening
detector.start_listening()

# Keep running
import time
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    detector.stop_listening()
```

## Adjusting Sensitivity

```python
# More conservative (fewer false positives)
detector.adjust_sensitivity(0.3)

# More aggressive (fewer false negatives)
detector.adjust_sensitivity(0.8)

# Balanced (recommended for children)
detector.adjust_sensitivity(0.5)
```

## File Locations

- **Source Code**: `/src/audio/`
- **Configuration**: `/configs/audio/wake_word_config.yaml`
- **Tests**: `/tests/audio/test_wake_word.py`
- **Examples**: `/examples/wake_word_demo.py`
- **Full Documentation**: `WAKE_WORD_README.md`

## Testing

```bash
# Run all tests
python -m pytest tests/audio/test_wake_word.py -v

# Run performance benchmarks
python -m pytest tests/audio/test_wake_word.py::TestPerformanceBenchmarks -v -s
```

## Troubleshooting

**No audio detected?**
- Check microphone permissions
- Verify microphone is connected
- Test with system audio recorder

**Too many false positives?**
- Lower sensitivity: `detector.adjust_sensitivity(0.3)`
- Increase threshold in config file

**Missing detections?**
- Increase sensitivity: `detector.adjust_sensitivity(0.7)`
- Speak louder and clearer
- Check microphone placement

## Next Steps

1. Read full documentation: `WAKE_WORD_README.md`
2. Customize configuration: `configs/audio/wake_word_config.yaml`
3. Run comprehensive tests: `tests/audio/test_wake_word.py`
4. Integrate into EduLens application

## Performance Targets

- ✓ True Positive Rate: 95%+
- ✓ False Positive Rate: <2%
- ✓ Detection Latency: <100ms
- ✓ Memory Usage: <50MB
- ✓ CPU Usage: <15%

## Support

Questions? Check `WAKE_WORD_README.md` or contact the development team.

---

**Version**: 1.0.0
**Status**: Production Ready
