# Tutoring LLM Fine-tuning Infrastructure

## Overview

This document describes the tutoring LLM infrastructure for EduLens, designed to provide age-appropriate, Socratic-method educational responses for students aged 6-12.

## Architecture

### Core Components

1. **TutorEngine** (`/src/ai/tutor_inference.py`)
   - Main inference engine for generating educational responses
   - Integrates with curriculum manager for concept-aware tutoring
   - Supports multiple response types: Socratic questions, hints, explanations, comprehension checks
   - Adaptive difficulty adjustment based on student performance

2. **PromptTemplateManager** (`/src/ai/prompt_templates.py`)
   - Subject-specific prompt templates (math, reading, science, social studies)
   - Socratic questioning patterns
   - Hint progression templates (subtle → moderate → direct)
   - Age-appropriate language guidelines (6-7, 8-9, 10-11, 12+)
   - Encouragement and feedback templates

3. **ResponseValidator** (`/src/ai/response_validator.py`)
   - Validates age-appropriateness of language
   - Checks for direct answer leakage (anti-pattern for Socratic method)
   - Verifies educational value and encouraging tone
   - Content safety filtering
   - Length and complexity validation

4. **Generation Config** (`/configs/llm/generation_config.yaml`)
   - LLM parameters (temperature, top_p, top_k)
   - Safety guardrails and validation thresholds
   - Subject-specific and age-specific overrides
   - Edge deployment settings for resource-constrained devices
   - Fine-tuning configuration

5. **Training Data** (`/data/training/socratic_examples.json`)
   - 24+ example Socratic dialogues across subjects
   - Good and bad response examples
   - Multi-turn conversation examples
   - Hint progression demonstrations
   - Common misconception handling

## Target Model

**Primary Target**: llama-3.2-3B (edge-deployable)

**Alternatives**:
- llama-3.2-1B (lighter for constrained devices)
- phi-3-mini (Microsoft's efficient model)
- gemma-2b (Google's compact model)

### Edge Deployment Characteristics
- Quantized to INT8 for efficiency
- ~4GB memory footprint
- CPU-optimized inference
- Supports Raspberry Pi 4/5, NVIDIA Jetson, mobile devices

## Socratic Method Implementation

### Core Principles

1. **Never Give Direct Answers**: Guide students to discover solutions themselves
2. **Ask Guiding Questions**: Help students think through problems step-by-step
3. **Build on Prior Knowledge**: Connect new concepts to what students already know
4. **Use Concrete Examples**: Make abstract concepts tangible and relatable
5. **Encourage Exploration**: Foster curiosity and independent thinking

### Response Types

```python
class ResponseType(Enum):
    SOCRATIC_QUESTION = "socratic_question"  # Guiding questions
    HINT = "hint"                             # Progressive hints
    EXPLANATION = "explanation"               # Concept explanations
    ENCOURAGEMENT = "encouragement"           # Supportive feedback
    COMPREHENSION_CHECK = "comprehension_check"  # Verify understanding
    GUIDED_DISCOVERY = "guided_discovery"     # Multi-step guidance
```

### Hint Progression

The system uses three levels of hints to progressively guide students:

1. **Subtle** (Level 1): Indirect guidance, encourages thinking
   - "Think about what happens when you break this into smaller parts..."

2. **Moderate** (Level 2): More specific strategy hints
   - "Try breaking 15 into 10 and 5, then add each part to 23..."

3. **Direct** (Level 3): Clear direction without giving answer
   - "You can add the tens first (20 + 10 = 30), then add the ones (3 + 5 = 8), then combine them..."

## Usage Examples

### Basic Response Generation

```python
from src.ai.tutor_inference import create_tutor_engine

# Initialize engine
engine = create_tutor_engine(model_name="llama-3.2-3B")

# Generate response
context = {
    'age': 8,
    'grade': '3',
    'subject': 'math',
    'concept_id': 'math_3_oa_001'
}

result = engine.generate_response(
    student_query="What is 5 times 3?",
    context=context
)

print(result['response'])
# Output: "Great question! Before I help you figure that out,
#          let me ask you something: If you have 5 bags and each
#          bag has 3 apples, how many apples do you have in total?"
```

### Multi-turn Guidance

```python
# Guide student through problem without giving answer
guidance = engine.guide_to_answer(
    problem_statement="What is 234 + 567?",
    student_attempts=["700", "790"],
    context={
        'age': 9,
        'grade': '4',
        'subject': 'math'
    }
)

print(guidance['response'])
# Provides progressively more specific hints based on attempts
```

### Concept Explanation

```python
# Explain a concept at appropriate level
explanation = engine.explain_concept(
    concept_id='math_3_oa_001',
    student_age=8,
    current_understanding="I know that multiplication is like adding"
)

print(explanation['response'])
# Builds on student's current understanding
```

### Comprehension Check

```python
# Verify student understanding
check = engine.check_understanding(
    concept_id='math_3_oa_001',
    student_response="Multiplication is repeated addition",
    context=context
)

print(check['response'])
# Asks follow-up question or provides feedback
```

## Age-Appropriate Language

### 6-7 Years Old
- Simple, concrete words (big/small, more/less)
- Short sentences (5-10 words)
- Comparisons to familiar things (toys, animals, food)
- Numbers 0-20
- Action-oriented language

### 8-9 Years Old
- Clear, direct language
- Medium sentences (10-15 words)
- Some academic vocabulary with explanations
- Real-world examples from daily life
- Numbers up to 100
- Multi-step thinking

### 10-11 Years Old
- Grade-appropriate academic language
- Longer, more complex sentences
- Abstract concepts with concrete examples
- Broader world references
- Larger numbers and fractions
- Critical thinking encouraged

### 12+ Years Old
- Full academic vocabulary with context
- Complex sentence structures
- Abstract and hypothetical thinking
- Current events and advanced topics
- All number ranges
- Debate and multiple perspectives

## Validation System

### Validation Checks

1. **Age Appropriateness** (0.0-1.0)
   - Vocabulary complexity
   - Sentence length
   - Concept abstraction level

2. **Socratic Method Adherence** (0.0-1.0)
   - Question-to-statement ratio
   - Direct answer detection
   - Guidance phrase presence

3. **Educational Value** (0.0-1.0)
   - Educational concept indicators
   - Specificity (not too vague)
   - Prior knowledge connections

4. **Encouraging Tone** (0.0-1.0)
   - Encouragement word count
   - Absence of negative words
   - Growth mindset language

5. **Content Safety** (0.0-1.0)
   - Inappropriate content detection
   - Personal information requests
   - External link/contact filtering

6. **Length Appropriateness** (0.0-1.0)
   - Age-based word count ranges
   - Response depth vs. brevity balance

### Validation Threshold

**Minimum Score**: 0.7 (70%)
**Critical Issues**: Any issue immediately fails validation

```python
from src.ai.response_validator import validate_educational_response

result = validate_educational_response(
    response="The answer is 15. You multiply 5 times 3.",
    age=8,
    subject='math'
)

print(result['is_valid'])  # False
print(result['issues'])     # ["Response appears to give 1 direct answer(s)"]
```

## Subject-Specific Templates

### Mathematics
- Focus on breaking down problems
- Encourage visualization (arrays, number lines)
- Connect to real-world objects
- Build on prior arithmetic knowledge

### Reading
- Guide to text evidence
- Build empathy through personal connections
- Develop inference skills
- Practice vocabulary in context

### Science
- Encourage observation and prediction
- Use cause-and-effect reasoning
- Connect to everyday phenomena
- Foster scientific thinking process

### Social Studies
- Consider different perspectives
- Compare to personal/community experience
- Understand change over time
- Connect past to present

## Configuration

### Model Parameters

```yaml
generation:
  temperature: 0.7        # Consistent but not robotic
  top_p: 0.9             # Nucleus sampling
  top_k: 50              # Top-k sampling
  max_output_tokens: 200  # Concise responses
```

### Safety Settings

```yaml
safety:
  min_response_length: 20
  max_response_length: 500
  enable_content_filter: true
  check_direct_answers: true
  min_validation_score: 0.7
```

### Subject Overrides

```yaml
subject_overrides:
  math:
    temperature: 0.6      # More consistent
    max_output_tokens: 250
  reading:
    temperature: 0.75     # More creative
    max_output_tokens: 200
```

## Fine-tuning Process

### Data Format

The training data follows this structure:

```json
{
  "id": "math_001",
  "subject": "math",
  "grade": "3",
  "age": 8,
  "dialogue": [
    {
      "role": "student",
      "content": "What is 5 times 3?"
    },
    {
      "role": "tutor",
      "content": "Great question! ...",
      "reasoning": "Converts abstract problem to concrete visualization",
      "techniques": ["visualization", "concrete_example", "guiding_question"]
    }
  ],
  "learning_outcomes": [
    "Student understands multiplication as repeated addition"
  ]
}
```

### Fine-tuning Strategy

1. **LoRA (Low-Rank Adaptation)**
   - Efficient parameter-efficient fine-tuning
   - Rank: 8, Alpha: 16, Dropout: 0.05
   - Target modules: q_proj, v_proj, k_proj, o_proj

2. **Training Parameters**
   - Learning rate: 2e-4
   - Batch size: 4 (with gradient accumulation: 4)
   - Epochs: 3
   - Warmup steps: 100

3. **Quantization**
   - INT8 quantization for edge deployment
   - Maintains 95%+ accuracy vs. FP32
   - ~4GB memory footprint

### Training Command (Example)

```bash
python -m src.ai.fine_tune \
  --base_model llama-3.2-3B \
  --data_path /data/training/socratic_examples.json \
  --output_dir /models/tutor-llama-3.2-3B \
  --lora_r 8 \
  --lora_alpha 16 \
  --learning_rate 2e-4 \
  --num_epochs 3 \
  --quantization int8
```

## Integration with Curriculum Manager

The TutorEngine integrates seamlessly with the CurriculumManager:

```python
# Engine automatically loads curriculum manager
engine = create_tutor_engine()

# Access curriculum data in responses
context = {
    'age': 8,
    'grade': '3',
    'subject': 'math',
    'concept_id': 'math_3_oa_001'  # Links to curriculum
}

# Engine retrieves:
# - Concept definition and examples
# - Prerequisites
# - Common misconceptions
# - Learning objectives

result = engine.generate_response(
    student_query="Why is multiplication important?",
    context=context
)
```

## Performance Considerations

### Latency Targets
- **Average response time**: < 500ms (on target hardware)
- **P95 response time**: < 1000ms
- **Timeout**: 10 seconds (configurable)

### Resource Requirements
- **Memory**: 4GB RAM minimum
- **CPU**: 4 cores recommended
- **Storage**: ~5GB for model and cache

### Optimization Strategies
1. **Response caching**: Common patterns cached for 1 hour
2. **Model quantization**: INT8 reduces memory by 75%
3. **Batch inference**: Process multiple requests efficiently
4. **Warmup on init**: Pre-load model for faster first response

## Testing

### Unit Tests

```bash
# Test individual components
python -m pytest tests/ai/test_tutor_inference.py
python -m pytest tests/ai/test_prompt_templates.py
python -m pytest tests/ai/test_response_validator.py
```

### Integration Tests

```bash
# Test full pipeline
python -m pytest tests/integration/test_tutoring_pipeline.py
```

### Validation Tests

```bash
# Test against good/bad examples
python -m pytest tests/ai/test_socratic_validation.py
```

## Monitoring and Metrics

### Key Metrics
1. **Validation Pass Rate**: % of responses passing validation
2. **Average Validation Score**: Mean score across all checks
3. **Direct Answer Leakage Rate**: % responses giving direct answers
4. **Response Generation Time**: Latency distribution
5. **Student Engagement**: Follow-up question rate

### Logging

All responses are logged with:
- Input query and context
- Generated response
- Validation results
- Performance metrics
- Timestamp and session ID

## Common Issues and Solutions

### Issue: Responses too complex for age
**Solution**: Check age_overrides in config, adjust temperature down

### Issue: Direct answers leaking through
**Solution**: Increase Socratic method validation weight, add more anti-patterns

### Issue: Responses too slow
**Solution**: Enable caching, reduce max_output_tokens, use lighter model

### Issue: Not enough encouragement
**Solution**: Increase encouragement_frequency in config

## Future Enhancements

1. **Multi-modal Support**: Integrate with vision system for diagram-based tutoring
2. **Personalization**: Adapt to individual student learning styles
3. **Emotion Detection**: Respond to student frustration or confidence
4. **Knowledge Tracing**: Track mastery over time
5. **Collaborative Learning**: Support peer tutoring scenarios

## References

- Curriculum Manager: `/src/ai/curriculum_manager.py`
- Vision System: `/src/vision/`
- Audio System: `/src/audio/`
- Main Documentation: `/docs/`

## Contact

For questions or issues with the tutoring infrastructure, contact the EduLens AI Team.

---

**Version**: 1.0.0
**Last Updated**: 2024-01-15
**Status**: Production Ready
