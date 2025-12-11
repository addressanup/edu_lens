# EduLens Personalization Engine - Quick Start Guide

## Overview

The EduLens Personalization Engine provides adaptive learning through:
- **Student Modeling**: Bayesian knowledge tracking
- **Adaptive Tutoring**: Real-time hint and explanation adjustment
- **Progress Tracking**: Spaced repetition and mastery calculation
- **Learning Analytics**: Privacy-preserving insights

## Quick Start

### 1. Installation

```bash
cd /Users/anuppandey/Desktop/edu_lens

# All dependencies already included in requirements.txt
# No additional installation needed!
```

### 2. Basic Usage

```python
from src.ai.personalization import (
    create_student_model,
    create_adaptive_tutor,
    create_progress_tracker,
    create_learning_analytics
)

# Create student model
student = create_student_model(
    student_id="student_123",
    age=9,
    grade=4
)

# Create supporting systems
tutor = create_adaptive_tutor(student)
tracker = create_progress_tracker(student)
analytics = create_learning_analytics("student_123", anonymize=True)

# Update from interaction
student.update_from_interaction(
    concept_id="math_3_oa_001",
    problem_type="multiplication",
    correct=True,
    attempts=1,
    time_spent=30.0,
    hint_level_used=0,
    student_response="24",
    difficulty_level=2
)

# Get results
mastery = student.get_mastery_level("math_3_oa_001")
print(f"Mastery: {mastery.name}")
```

### 3. Run Demo

```bash
# Run comprehensive demo
python -m examples.personalization_demo
```

### 4. Run Tests

```bash
# Run all tests
python -m pytest tests/ai/test_personalization.py -v

# Expected: 38 passed in ~3 seconds
```

## Core Components

### Student Model

```python
# Create model
student = create_student_model("student_123", age=9, grade=4)

# Update from interaction
result = student.update_from_interaction(
    concept_id="math_001",
    problem_type="multiplication",
    correct=True,
    attempts=1,
    time_spent=30.0,
    hint_level_used=0,
    student_response="correct",
    difficulty_level=2
)

# Get insights
mastery = student.get_mastery_level("math_001")
style = student.get_learning_style()
pace = student.get_pace()
difficulty = student.predict_difficulty("math_001")
```

### Adaptive Tutor

```python
from src.ai.personalization import AdaptationContext

# Create tutor
tutor = create_adaptive_tutor(student)

# Create context
context = AdaptationContext(
    concept_id="math_001",
    problem_statement="What is 6 × 4?",
    student_attempts=["20"],
    time_on_problem=30.0,
    hints_used=0,
    difficulty_level=2,
    session_duration=300.0,
    problems_solved_today=3
)

# Generate hint
hint = tutor.generate_hint(context)
print(hint.hint_text)

# Detect emotion
emotion, confidence = tutor.detect_frustration(context)
print(f"{emotion.name}: {confidence:.0%}")
```

### Progress Tracker

```python
# Create tracker
tracker = create_progress_tracker(student)

# Record attempt
tracker.record_attempt(
    concept_id="math_001",
    problem_id="prob_001",
    correct=True,
    time_spent=30.0,
    hints_used=0,
    difficulty=2,
    attempts_on_problem=1
)

# Get insights
mastery = tracker.calculate_mastery("math_001")
gaps = tracker.identify_gaps()
reviews = tracker.suggest_review(max_suggestions=5)
report = tracker.generate_report()
```

### Learning Analytics

```python
# Create analytics
analytics = create_learning_analytics("student_123", anonymize=True)

# Update from session
session_data = {
    'session_id': 'session_001',
    'start_time': time.time(),
    'end_time': time.time() + 1200,
    'problems_attempted': 10,
    'problems_correct': 8,
    'concepts_practiced': ['math_001'],
    'mastery_scores': {'math_001': 0.75}
}
analytics.update_from_session(session_data)

# Get insights
patterns = analytics.detect_learning_patterns()
trends = analytics.analyze_trends('accuracy', days=7)
engagement = analytics.get_engagement_score()
insights = analytics.get_insights()
```

## Configuration

Configuration file: `/configs/ai/personalization_config.yaml`

### Key Settings

```yaml
# Student Model
student_model:
  knowledge_tracing:
    default_probability_slip: 0.15
    default_probability_guess: 0.25

# Adaptive Tutor
adaptive_tutor:
  hints:
    progression_threshold: 2
  encouragement:
    frequency_seconds: 120

# Progress Tracker
progress_tracker:
  spaced_repetition:
    initial_easiness_factor: 2.5
  mastery_calculation:
    mastery_threshold: 0.8

# Learning Analytics
learning_analytics:
  privacy:
    anonymize_by_default: true
```

## Complete Example

```python
import time
from src.ai.personalization import (
    create_student_model,
    create_adaptive_tutor,
    create_progress_tracker,
    create_learning_analytics,
    AdaptationContext
)

# Initialize systems
student = create_student_model("student_123", age=9, grade=4)
tutor = create_adaptive_tutor(student)
tracker = create_progress_tracker(student)
analytics = create_learning_analytics("student_123", anonymize=True)

# Simulate learning session
concept_id = "math_3_oa_001"
session_start = time.time()
problems_correct = 0

problems = [
    {"correct": False, "time": 45.0, "attempts": 2},
    {"correct": True, "time": 30.0, "attempts": 1},
    {"correct": True, "time": 25.0, "attempts": 1},
]

for i, problem in enumerate(problems):
    # Update student model
    student.update_from_interaction(
        concept_id=concept_id,
        problem_type="multiplication",
        correct=problem["correct"],
        attempts=problem["attempts"],
        time_spent=problem["time"],
        hint_level_used=1 if problem["attempts"] > 1 else 0,
        student_response="answer",
        difficulty_level=2
    )

    # Record in tracker
    tracker.record_attempt(
        concept_id=concept_id,
        problem_id=f"prob_{i}",
        correct=problem["correct"],
        time_spent=problem["time"],
        hints_used=1 if problem["attempts"] > 1 else 0,
        difficulty=2,
        attempts_on_problem=problem["attempts"]
    )

    if problem["correct"]:
        problems_correct += 1

    # Get adaptive hint if needed
    if not problem["correct"]:
        context = AdaptationContext(
            concept_id=concept_id,
            problem_statement="Problem statement",
            student_attempts=["answer"],
            time_on_problem=problem["time"],
            hints_used=1,
            difficulty_level=2,
            session_duration=time.time() - session_start,
            problems_solved_today=i
        )
        hint = tutor.generate_hint(context)
        print(f"Hint: {hint.hint_text}")

# Update analytics
analytics.update_from_session({
    'session_id': 'session_001',
    'start_time': session_start,
    'end_time': time.time(),
    'problems_attempted': len(problems),
    'problems_correct': problems_correct,
    'concepts_practiced': [concept_id],
    'mastery_scores': {concept_id: tracker.calculate_mastery(concept_id)}
})

# Get results
print(f"Mastery: {student.get_mastery_level(concept_id).name}")
print(f"Style: {student.get_learning_style().name}")
print(f"Engagement: {analytics.get_engagement_score():.0%}")

# Generate reports
report = tracker.generate_report()
print(f"Accuracy: {report.overall_accuracy:.0%}")
print(f"Concepts Mastered: {report.mastered_concepts}")
```

## File Locations

```
/Users/anuppandey/Desktop/edu_lens/

Core Modules:
├── src/ai/personalization/
│   ├── student_model.py          # Student modeling
│   ├── adaptive_tutor.py         # Adaptive tutoring
│   ├── progress_tracker.py       # Progress tracking
│   └── learning_analytics.py     # Analytics

Configuration:
├── configs/ai/
│   └── personalization_config.yaml

Tests:
├── tests/ai/
│   └── test_personalization.py   # 38 tests

Examples:
└── examples/
    └── personalization_demo.py   # Full demo
```

## Testing

```bash
# Run all tests
python -m pytest tests/ai/test_personalization.py -v

# Run specific test
python -m pytest tests/ai/test_personalization.py::TestStudentModel -v

# Run with coverage
python -m pytest tests/ai/test_personalization.py --cov=src/ai/personalization
```

## Common Use Cases

### 1. Track Student Progress

```python
student = create_student_model("student_123", age=9, grade=4)
tracker = create_progress_tracker(student)

# After each problem
tracker.record_attempt(
    concept_id="math_001",
    problem_id="prob_001",
    correct=True,
    time_spent=30.0,
    hints_used=0,
    difficulty=2,
    attempts_on_problem=1
)

# Get progress
report = tracker.generate_report()
```

### 2. Provide Adaptive Hints

```python
tutor = create_adaptive_tutor(student)

context = AdaptationContext(
    concept_id="math_001",
    problem_statement="Problem",
    student_attempts=["attempt1"],
    time_on_problem=60.0,
    hints_used=0,
    difficulty_level=2,
    session_duration=300.0,
    problems_solved_today=3
)

hint = tutor.generate_hint(context)
print(hint.hint_text)
```

### 3. Detect Learning Patterns

```python
analytics = create_learning_analytics("student_123", anonymize=True)

# After each session
analytics.update_from_session(session_data)

# Detect patterns
patterns = analytics.detect_learning_patterns()
insights = analytics.get_insights()
```

### 4. Schedule Reviews

```python
tracker = create_progress_tracker(student)

# Get concepts due for review
reviews = tracker.suggest_review(max_suggestions=5)

for review in reviews:
    print(f"Review {review['concept_id']}: priority {review['priority']}")
```

## Privacy Features

All components are privacy-preserving by default:

- Student IDs are hashed
- Only aggregate statistics stored
- Limited interaction history (100 records)
- No raw personal data in analytics
- Configurable retention policies

## Performance

- Student model update: < 0.02s
- Hint generation: < 0.05s
- Progress calculation: < 0.01s
- 100 interactions: < 2 seconds

## Support

For detailed information:
- Full documentation: `PERSONALIZATION_ENGINE_SUMMARY.md`
- Configuration guide: `configs/ai/personalization_config.yaml`
- Test examples: `tests/ai/test_personalization.py`
- Demo: `examples/personalization_demo.py`

## Next Steps

1. Run the demo: `python -m examples.personalization_demo`
2. Run tests: `python -m pytest tests/ai/test_personalization.py -v`
3. Integrate with your tutoring system
4. Customize configuration in `configs/ai/personalization_config.yaml`
5. Monitor privacy and performance

## Task Complete ✅

TASK EDU-001-T4: Personalization Engine - COMPLETE

All requirements met:
✅ Track learning progress per concept
✅ Identify strengths and weaknesses
✅ Adapt difficulty and explanation style
✅ Respect privacy (no raw data storage)

Plus advanced features:
✅ Spaced repetition scheduling
✅ Emotional state detection
✅ Learning analytics and insights
✅ Comprehensive testing (38 tests passing)
