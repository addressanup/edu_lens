# Layout Analysis Quick Reference

## Installation
```bash
pip install opencv-python numpy
```

## Basic Usage

### Analyze Layout
```python
from src.vision import LayoutAnalyzer
import cv2

image = cv2.imread("worksheet.jpg")
analyzer = LayoutAnalyzer()
structure = analyzer.analyze_layout(image)

print(f"Regions: {len(structure.regions)}")
print(f"Columns: {structure.num_columns}")
```

### Segment Problems
```python
from src.vision import segment_worksheet

problems = segment_worksheet(image)

for problem in problems.problems:
    print(f"Q{problem.problem_number}: {problem.question_text}")
```

### With OCR
```python
from src.vision import OCREngine, ProblemSegmenter

ocr_result = OCREngine().recognize(image)
segmenter = ProblemSegmenter()
problems = segmenter.segment_problems(image, ocr_result)
```

## Key Classes

| Class | Purpose |
|-------|---------|
| `LayoutAnalyzer` | Document layout analysis |
| `ProblemSegmenter` | Problem segmentation |
| `LayoutRegion` | Region data structure |
| `Problem` | Problem data structure |
| `DocumentStructure` | Hierarchical structure |

## Region Types

| Type | Description |
|------|-------------|
| `QUESTION` | Question/problem text |
| `ANSWER_SPACE` | Blank answer areas |
| `DIAGRAM` | Diagrams and figures |
| `HEADER` | Page headers |
| `MULTIPLE_CHOICE` | MC options |
| `INSTRUCTION` | Directions |

## Problem Formats

| Format | Description |
|--------|-------------|
| `MULTIPLE_CHOICE` | A/B/C/D options |
| `FILL_IN_BLANK` | Fill-in questions |
| `SHORT_ANSWER` | Short response |
| `TRUE_FALSE` | T/F questions |
| `CALCULATION` | Math problems |
| `ESSAY` | Long answer |

## Convenience Functions

```python
# Segment worksheet
problems = segment_worksheet(image)

# Get problem by number
problem = extract_problem_by_number(problems, "2")

# Filter by format
mc_problems = get_problems_by_format(problems, ProblemFormat.MULTIPLE_CHOICE)
```

## Common Patterns

### Get All Questions
```python
questions = structure.get_regions_by_type(RegionType.QUESTION)
```

### Iterate Reading Order
```python
for region_id in structure.reading_order:
    region = structure.get_region_by_id(region_id)
    print(region.text_content)
```

### Access Problem Parts
```python
for problem in problems.problems:
    print(f"Question: {problem.question_text}")
    print(f"Choices: {len(problem.choices)}")
    if problem.diagram:
        print("Has diagram")
```

## Configuration

Located at: `/configs/vision/layout_config.yaml`

### Key Parameters
```yaml
layout_analyzer:
  region_detection:
    min_region_size: 100
    merge_threshold: 0.5

problem_segmenter:
  detection:
    min_problem_size: 200
```

## Testing

```bash
# Run all tests
pytest tests/vision/test_layout_analysis.py -v

# Run specific test
pytest tests/vision/test_layout_analysis.py::TestLayoutAnalyzer -v
```

## Demo

```bash
python examples/layout_analysis_demo.py
```

## Files

| File | Purpose |
|------|---------|
| `src/vision/layout_analyzer.py` | Layout analysis engine |
| `src/vision/problem_segmenter.py` | Problem segmentation |
| `tests/vision/test_layout_analysis.py` | Test suite |
| `configs/vision/layout_config.yaml` | Configuration |
| `examples/layout_analysis_demo.py` | Demo script |
| `docs/layout_analysis_guide.md` | Full documentation |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Too many regions | Increase `min_region_size` |
| Too few regions | Decrease `min_region_size` |
| Wrong classification | Check OCR accuracy |
| Poor reading order | Verify column detection |

## Performance

- **Target:** 90% layout accuracy
- **Speed:** <2 seconds per page
- **Max size:** 4096x4096 pixels

---

For complete documentation, see: `/docs/layout_analysis_guide.md`
