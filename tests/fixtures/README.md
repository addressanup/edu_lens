# Test Fixtures Guide

This directory contains test fixtures and sample data used throughout the EduLens test suite.

## Directory Structure

```
tests/fixtures/
├── README.md           # This file
├── audio/              # Audio test files
├── images/             # Image and vision test files
└── curriculum/         # Educational content and curriculum test data
```

## Overview

Test fixtures are reusable test data and resources that help ensure consistent, reliable testing across the EduLens platform. These fixtures are used in unit tests, integration tests, and end-to-end tests.

## Fixture Categories

### Audio Fixtures (`/audio`)

Contains sample audio files for testing audio processing, speech recognition, and text-to-speech functionality.

**Supported formats:**
- WAV (recommended for testing)
- MP3
- FLAC
- OGG

**Naming convention:**
- `sample_<description>_<duration>s.wav`
- Example: `sample_child_question_3s.wav`

**Best practices:**
- Keep audio files under 5 seconds for faster tests
- Use 16kHz sample rate (standard for speech)
- Mono channel preferred
- Include both clean and noisy samples

**Example audio fixtures:**
```
audio/
├── sample_child_question_3s.wav       # "What is photosynthesis?"
├── sample_teacher_response_5s.wav     # Educational explanation
├── sample_background_noise_2s.wav     # Classroom ambient noise
└── sample_silence_1s.wav              # Silent audio for edge cases
```

### Image Fixtures (`/images`)

Contains sample images for testing computer vision, OCR, and scene understanding features.

**Supported formats:**
- JPEG (recommended for testing)
- PNG
- BMP

**Naming convention:**
- `sample_<content>_<resolution>.jpg`
- Example: `sample_textbook_page_800x600.jpg`

**Best practices:**
- Use moderate resolution (640x480 to 1920x1080)
- Include diverse scenarios (books, objects, scenes)
- Test both clear and challenging images
- Include text-heavy and image-heavy samples

**Example image fixtures:**
```
images/
├── sample_textbook_page_800x600.jpg       # Textbook with text and diagrams
├── sample_math_problem_640x480.jpg        # Math worksheet
├── sample_science_diagram_1024x768.jpg    # Scientific diagram
├── sample_classroom_scene_1280x720.jpg    # Classroom environment
└── sample_handwriting_800x600.jpg         # Handwritten notes
```

### Curriculum Fixtures (`/curriculum`)

Contains educational content, lesson plans, and curriculum data for testing educational features.

**File types:**
- JSON (structured data)
- YAML (configuration)
- TXT (plain text content)
- MD (markdown documentation)

**Naming convention:**
- `<grade>_<subject>_<topic>.json`
- Example: `grade3_science_photosynthesis.json`

**Best practices:**
- Align with real curriculum standards
- Include age-appropriate content
- Cover multiple subjects (math, science, reading, etc.)
- Include different difficulty levels

**Example curriculum fixtures:**
```
curriculum/
├── grade3_science_photosynthesis.json     # 3rd grade science lesson
├── grade4_math_fractions.json             # 4th grade math lesson
├── grade5_reading_comprehension.json      # 5th grade reading
├── vocabulary_elementary.json             # Age-appropriate vocabulary
└── learning_objectives.yaml               # Standard learning objectives
```

## Adding New Fixtures

### Step 1: Create the Fixture File

Place your fixture file in the appropriate subdirectory:

```bash
# Audio fixture
cp my_audio.wav tests/fixtures/audio/sample_description.wav

# Image fixture
cp my_image.jpg tests/fixtures/images/sample_description.jpg

# Curriculum fixture
cp my_lesson.json tests/fixtures/curriculum/grade3_science_topic.json
```

### Step 2: Document the Fixture

Add documentation in this README or create a companion `.md` file:

```markdown
## New Fixture: sample_description.wav

**Purpose:** Tests speech recognition for child questions about science
**Duration:** 3 seconds
**Format:** WAV, 16kHz, mono
**Content:** "Why do leaves change color?"
**Age group:** 7-9 years old
**Use cases:**
- Speech recognition accuracy
- Age-appropriate voice detection
- Science topic identification
```

### Step 3: Use in Tests

Reference the fixture in your test using the `test_data_dir` fixture from `conftest.py`:

```python
def test_audio_processing(test_data_dir):
    """Test audio processing with fixture."""
    audio_file = test_data_dir / "audio" / "sample_description.wav"

    # Your test code here
    result = process_audio(audio_file)
    assert result.confidence > 0.8
```

### Step 4: Add to Version Control

```bash
git add tests/fixtures/audio/sample_description.wav
git commit -m "Add audio fixture for child science questions"
```

## Fixture Best Practices

### Size Constraints

- **Audio files:** < 500KB each (prefer < 100KB)
- **Image files:** < 1MB each (prefer < 500KB)
- **Text/JSON files:** < 100KB each
- **Total fixtures directory:** < 50MB

### Quality Guidelines

1. **Realistic:** Fixtures should represent real-world usage
2. **Diverse:** Cover edge cases and various scenarios
3. **Minimal:** Only include essential fixtures
4. **Documented:** Every fixture should have clear documentation
5. **Age-appropriate:** All content suitable for ages 6-12

### Privacy and Safety

- **No real student data:** Never use actual student recordings or images
- **Synthetic only:** Use generated or stock content
- **Privacy compliance:** Ensure COPPA and FERPA compliance
- **Content safety:** All fixtures must pass safety checks

## Programmatic Fixture Generation

For fixtures that can be generated programmatically, use the fixtures defined in `conftest.py`:

```python
# In conftest.py
@pytest.fixture
def sample_audio_data():
    """Generate sample audio data programmatically."""
    # Generate sine wave or other test audio
    return audio_data

# In your test
def test_with_generated_fixture(sample_audio_data):
    """Test using programmatically generated fixture."""
    result = process_audio(sample_audio_data)
    assert result.success
```

**Benefits:**
- No file storage required
- Consistent across environments
- Easy to parameterize
- Faster test execution

## Fixture Maintenance

### Regular Reviews

- **Quarterly:** Review all fixtures for relevance
- **Remove unused:** Delete fixtures not referenced in tests
- **Update outdated:** Refresh fixtures that no longer represent current usage
- **Optimize size:** Compress or reduce quality if needed

### Fixture Versioning

If a fixture changes significantly, consider versioning:

```
audio/
├── sample_question_v1.wav  # Original version
└── sample_question_v2.wav  # Updated version
```

### Testing Fixtures

Ensure fixtures themselves are valid:

```python
def test_audio_fixtures_are_valid(test_data_dir):
    """Verify all audio fixtures are valid."""
    audio_dir = test_data_dir / "audio"

    for audio_file in audio_dir.glob("*.wav"):
        # Check file is readable
        assert audio_file.exists()

        # Check file size
        assert audio_file.stat().st_size > 0
        assert audio_file.stat().st_size < 500_000  # < 500KB

        # Check audio is valid (if using soundfile)
        # data, samplerate = sf.read(audio_file)
        # assert len(data) > 0
```

## Common Issues and Solutions

### Issue: Fixture file not found

**Solution:** Use the `test_data_dir` fixture for absolute paths:

```python
# Wrong ❌
audio_file = "tests/fixtures/audio/sample.wav"

# Correct ✅
audio_file = test_data_dir / "audio" / "sample.wav"
```

### Issue: Fixture too large

**Solution:** Optimize the file:

```bash
# Compress image
convert input.jpg -quality 85 -resize 800x600 output.jpg

# Compress audio
ffmpeg -i input.wav -ar 16000 -ac 1 output.wav
```

### Issue: Fixture not in version control

**Solution:** Check `.gitignore` and add fixture:

```bash
# Remove from .gitignore if needed
git add -f tests/fixtures/audio/sample.wav
```

### Issue: Cross-platform compatibility

**Solution:** Use `pathlib.Path` for all file operations:

```python
from pathlib import Path

# Works on Windows, macOS, Linux ✅
fixture_path = Path("tests") / "fixtures" / "audio" / "sample.wav"
```

## Additional Resources

- [Pytest Fixtures Documentation](https://docs.pytest.org/en/stable/fixture.html)
- [EduLens Testing Guide](../README.md)
- [Conftest.py Fixtures](../conftest.py)

## Questions?

For questions about test fixtures, see:
- Project documentation: `/docs`
- Testing documentation: `/tests/README.md`
- File an issue: GitHub Issues

---

**Last updated:** 2025-12-10
**Maintained by:** EduLens Testing Team
