"""
Test Suite for Layout Analysis and Problem Segmentation

Tests the document layout analyzer and problem segmenter components
to ensure accurate detection and classification of worksheet elements.

Author: Vision Processing Agent (VIS-001)
Task: VIS-001-T3
"""

from pathlib import Path
from typing import List, Tuple

import numpy as np
import pytest

# Test imports
from src.vision.layout_analyzer import (
    ContentType,
    DocumentStructure,
    LayoutAnalyzer,
    LayoutRegion,
    RegionType,
)
from src.vision.ocr_engine import BoundingBox, OCRResult, TextRegion
from src.vision.problem_segmenter import (
    Problem,
    ProblemDifficulty,
    ProblemFormat,
    ProblemPart,
    ProblemSegmenter,
    WorksheetProblems,
    extract_problem_by_number,
    get_problems_by_format,
    segment_worksheet,
)

try:
    import cv2

    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


# Test Fixtures


@pytest.fixture
def sample_image() -> np.ndarray:
    """Create a sample test image."""
    # Create a simple 800x600 white image
    image = np.ones((600, 800, 3), dtype=np.uint8) * 255
    return image


@pytest.fixture
def worksheet_image() -> np.ndarray:
    """Create a mock worksheet image with text regions."""
    if not CV2_AVAILABLE:
        return np.ones((600, 800, 3), dtype=np.uint8) * 255

    image = np.ones((800, 600, 3), dtype=np.uint8) * 255

    # Add some text-like regions (dark rectangles)
    # Header
    cv2.rectangle(image, (50, 30), (550, 70), (0, 0, 0), -1)

    # Question 1
    cv2.rectangle(image, (50, 100), (550, 140), (0, 0, 0), -1)

    # Answer space
    cv2.rectangle(image, (50, 150), (550, 200), (200, 200, 200), 2)

    # Question 2
    cv2.rectangle(image, (50, 250), (550, 290), (0, 0, 0), -1)

    # Multiple choice options
    cv2.rectangle(image, (70, 310), (300, 330), (0, 0, 0), -1)
    cv2.rectangle(image, (70, 340), (300, 360), (0, 0, 0), -1)
    cv2.rectangle(image, (70, 370), (300, 390), (0, 0, 0), -1)

    # Diagram
    cv2.rectangle(image, (350, 300), (550, 450), (0, 0, 0), 2)
    cv2.circle(image, (450, 375), 50, (0, 0, 0), 2)

    return image


@pytest.fixture
def sample_bounding_box() -> BoundingBox:
    """Create a sample bounding box."""
    return BoundingBox(x=100, y=100, width=200, height=50)


@pytest.fixture
def sample_region(sample_bounding_box) -> LayoutRegion:
    """Create a sample layout region."""
    return LayoutRegion(
        region_id="test_region_001",
        region_type=RegionType.QUESTION,
        bounding_box=sample_bounding_box,
        content_type=ContentType.TEXT,
        confidence=0.85,
        text_content="1. What is 2 + 2?",
    )


@pytest.fixture
def sample_ocr_result() -> OCRResult:
    """Create a sample OCR result."""
    regions = [
        TextRegion(
            text="Math Worksheet",
            confidence=0.95,
            bounding_box=BoundingBox(50, 30, 500, 40),
            language="en",
        ),
        TextRegion(
            text="1. What is 2 + 2?",
            confidence=0.92,
            bounding_box=BoundingBox(50, 100, 500, 40),
            language="en",
        ),
        TextRegion(
            text="2. Choose the correct answer:",
            confidence=0.90,
            bounding_box=BoundingBox(50, 250, 500, 40),
            language="en",
        ),
        TextRegion(
            text="A. Option 1",
            confidence=0.88,
            bounding_box=BoundingBox(70, 310, 230, 20),
            language="en",
        ),
        TextRegion(
            text="B. Option 2",
            confidence=0.88,
            bounding_box=BoundingBox(70, 340, 230, 20),
            language="en",
        ),
    ]
    return OCRResult(
        regions=regions,
        full_text="Math Worksheet\n1. What is 2 + 2?\n2. Choose the correct answer:\nA. Option 1\nB. Option 2",
    )


@pytest.fixture
def layout_analyzer() -> LayoutAnalyzer:
    """Create a LayoutAnalyzer instance."""
    return LayoutAnalyzer(
        min_region_size=100, merge_threshold=0.5, whitespace_threshold=20, min_confidence=0.6
    )


@pytest.fixture
def problem_segmenter(layout_analyzer) -> ProblemSegmenter:
    """Create a ProblemSegmenter instance."""
    return ProblemSegmenter(layout_analyzer=layout_analyzer, min_problem_size=200)


# Tests for BoundingBox and LayoutRegion


class TestBoundingBox:
    """Tests for BoundingBox functionality."""

    def test_bounding_box_creation(self, sample_bounding_box):
        """Test creating a bounding box."""
        assert sample_bounding_box.x == 100
        assert sample_bounding_box.y == 100
        assert sample_bounding_box.width == 200
        assert sample_bounding_box.height == 50

    def test_to_dict(self, sample_bounding_box):
        """Test converting bounding box to dictionary."""
        bbox_dict = sample_bounding_box.to_dict()
        assert bbox_dict["x"] == 100
        assert bbox_dict["y"] == 100
        assert bbox_dict["width"] == 200
        assert bbox_dict["height"] == 50

    def test_to_coordinates(self, sample_bounding_box):
        """Test converting to coordinate format."""
        coords = sample_bounding_box.to_coordinates()
        assert coords == (100, 100, 300, 150)


class TestLayoutRegion:
    """Tests for LayoutRegion functionality."""

    def test_region_creation(self, sample_region):
        """Test creating a layout region."""
        assert sample_region.region_id == "test_region_001"
        assert sample_region.region_type == RegionType.QUESTION
        assert sample_region.confidence == 0.85

    def test_region_to_dict(self, sample_region):
        """Test converting region to dictionary."""
        region_dict = sample_region.to_dict()
        assert region_dict["region_id"] == "test_region_001"
        assert region_dict["region_type"] == "question"
        assert region_dict["confidence"] == 0.85

    def test_region_area(self, sample_region):
        """Test calculating region area."""
        area = sample_region.area()
        assert area == 200 * 50  # width * height

    def test_region_overlap(self):
        """Test detecting region overlap."""
        region1 = LayoutRegion(
            region_id="r1",
            region_type=RegionType.TEXT_BLOCK,
            bounding_box=BoundingBox(100, 100, 100, 100),
        )
        region2 = LayoutRegion(
            region_id="r2",
            region_type=RegionType.TEXT_BLOCK,
            bounding_box=BoundingBox(150, 150, 100, 100),
        )
        region3 = LayoutRegion(
            region_id="r3",
            region_type=RegionType.TEXT_BLOCK,
            bounding_box=BoundingBox(300, 300, 100, 100),
        )

        # region1 and region2 overlap
        assert region1.overlaps(region2, threshold=0.3)
        # region1 and region3 don't overlap
        assert not region1.overlaps(region3)

    def test_region_hierarchy(self):
        """Test parent-child relationships."""
        parent = LayoutRegion(
            region_id="parent",
            region_type=RegionType.QUESTION,
            bounding_box=BoundingBox(100, 100, 200, 200),
        )
        child = LayoutRegion(
            region_id="child",
            region_type=RegionType.ANSWER_SPACE,
            bounding_box=BoundingBox(110, 250, 180, 40),
            parent_id="parent",
        )

        parent.children.append(child)

        assert len(parent.children) == 1
        assert child.parent_id == "parent"


# Tests for LayoutAnalyzer


class TestLayoutAnalyzer:
    """Tests for LayoutAnalyzer functionality."""

    def test_analyzer_initialization(self, layout_analyzer):
        """Test initializing the analyzer."""
        assert layout_analyzer.min_region_size == 100
        assert layout_analyzer.merge_threshold == 0.5

    @pytest.mark.skipif(not CV2_AVAILABLE, reason="OpenCV not available")
    def test_detect_regions(self, layout_analyzer, worksheet_image, sample_ocr_result):
        """Test detecting regions in an image."""
        regions = layout_analyzer.detect_regions(worksheet_image, sample_ocr_result)

        assert len(regions) > 0
        assert all(isinstance(r, LayoutRegion) for r in regions)
        assert all(r.region_id.startswith("region_") for r in regions)

    @pytest.mark.skipif(not CV2_AVAILABLE, reason="OpenCV not available")
    def test_analyze_layout(self, layout_analyzer, worksheet_image, sample_ocr_result):
        """Test complete layout analysis."""
        structure = layout_analyzer.analyze_layout(worksheet_image, sample_ocr_result)

        assert isinstance(structure, DocumentStructure)
        assert len(structure.regions) > 0
        assert structure.num_columns >= 1
        assert structure.layout_type in ["single-column", "two-column", "multi-column", "complex"]

    def test_classify_region_question(self, layout_analyzer, sample_image):
        """Test classifying a question region."""
        region = LayoutRegion(
            region_id="test",
            region_type=RegionType.TEXT_BLOCK,
            bounding_box=BoundingBox(50, 100, 500, 40),
            text_content="1. What is 2 + 2?",
        )

        region_type = layout_analyzer.classify_region(region, sample_image)
        assert region_type == RegionType.QUESTION

    def test_classify_region_multiple_choice(self, layout_analyzer, sample_image):
        """Test classifying a multiple choice region."""
        region = LayoutRegion(
            region_id="test",
            region_type=RegionType.TEXT_BLOCK,
            bounding_box=BoundingBox(50, 100, 500, 100),
            text_content="A. First option\nB. Second option\nC. Third option",
        )

        region_type = layout_analyzer.classify_region(region, sample_image)
        assert region_type == RegionType.MULTIPLE_CHOICE

    def test_classify_region_header(self, layout_analyzer, sample_image):
        """Test classifying a header region."""
        region = LayoutRegion(
            region_id="test",
            region_type=RegionType.TEXT_BLOCK,
            bounding_box=BoundingBox(50, 20, 500, 40),
            text_content="Math Worksheet",
        )

        region_type = layout_analyzer.classify_region(region, sample_image)
        assert region_type == RegionType.HEADER

    def test_extract_structure(self, layout_analyzer, sample_image):
        """Test extracting document structure."""
        regions = [
            LayoutRegion(
                region_id="header",
                region_type=RegionType.HEADER,
                bounding_box=BoundingBox(50, 30, 500, 40),
                text_content="Worksheet Title",
            ),
            LayoutRegion(
                region_id="q1",
                region_type=RegionType.QUESTION,
                bounding_box=BoundingBox(50, 100, 500, 40),
                text_content="1. Question one?",
            ),
            LayoutRegion(
                region_id="a1",
                region_type=RegionType.ANSWER_SPACE,
                bounding_box=BoundingBox(50, 150, 500, 50),
                text_content="",
            ),
        ]

        structure = layout_analyzer.extract_structure(regions, sample_image)

        assert isinstance(structure, DocumentStructure)
        assert len(structure.regions) == 3

    def test_reading_order_single_column(self, layout_analyzer):
        """Test determining reading order for single column layout."""
        regions = [
            LayoutRegion("r3", RegionType.TEXT_BLOCK, BoundingBox(50, 300, 500, 40)),
            LayoutRegion("r1", RegionType.HEADER, BoundingBox(50, 50, 500, 40)),
            LayoutRegion("r2", RegionType.TEXT_BLOCK, BoundingBox(50, 150, 500, 40)),
        ]

        structure = DocumentStructure(regions=regions, num_columns=1)
        reading_order = layout_analyzer.get_reading_order(structure)

        # Should be ordered by Y position
        assert reading_order == ["r1", "r2", "r3"]

    def test_detect_columns(self, layout_analyzer, sample_image):
        """Test column detection."""
        # Single column regions
        regions = [
            LayoutRegion("r1", RegionType.TEXT_BLOCK, BoundingBox(50, 100, 500, 40)),
            LayoutRegion("r2", RegionType.TEXT_BLOCK, BoundingBox(50, 200, 500, 40)),
        ]

        num_columns = layout_analyzer._detect_columns(regions, sample_image.shape[1])
        assert num_columns >= 1


# Tests for ProblemSegmenter


class TestProblemSegmenter:
    """Tests for ProblemSegmenter functionality."""

    def test_segmenter_initialization(self, problem_segmenter):
        """Test initializing the segmenter."""
        assert problem_segmenter.min_problem_size == 200
        assert isinstance(problem_segmenter.layout_analyzer, LayoutAnalyzer)

    def test_detect_problem_numbers(self, problem_segmenter):
        """Test detecting problem numbers from text."""
        test_cases = [
            ("1. What is this?", "1"),
            ("2) Another question", "2"),
            ("3a. Sub-question", "3a"),
            ("Question 5: Answer this", "5"),
            ("Problem 10 - Solve", "10"),
            ("No number here", None),
        ]

        for text, expected in test_cases:
            result = problem_segmenter.detect_problem_numbers(text)
            assert result == expected, f"Failed for text: {text}"

    def test_extract_multiple_choice(self, problem_segmenter):
        """Test extracting multiple choice options."""
        text = """What is the capital?
A. Paris
B. London
C. Berlin
D. Rome"""

        bbox = BoundingBox(50, 100, 500, 100)
        choices = problem_segmenter._extract_multiple_choice(text, bbox)

        assert len(choices) == 4
        assert all(c.part_type == "choice" for c in choices)
        assert choices[0].metadata["label"] == "A"
        assert "Paris" in choices[0].content

    def test_classify_problem_format_multiple_choice(self, problem_segmenter):
        """Test classifying multiple choice problems."""
        region = LayoutRegion(
            region_id="test",
            region_type=RegionType.MULTIPLE_CHOICE,
            bounding_box=BoundingBox(50, 100, 500, 100),
            text_content="A. Option 1\nB. Option 2\nC. Option 3",
        )

        parts = [
            ProblemPart("choice", "A. Option 1", region.bounding_box),
            ProblemPart("choice", "B. Option 2", region.bounding_box),
            ProblemPart("choice", "C. Option 3", region.bounding_box),
        ]

        format_type = problem_segmenter._classify_problem_format(region, parts)
        assert format_type == ProblemFormat.MULTIPLE_CHOICE

    def test_classify_problem_format_true_false(self, problem_segmenter):
        """Test classifying true/false problems."""
        region = LayoutRegion(
            region_id="test",
            region_type=RegionType.QUESTION,
            bounding_box=BoundingBox(50, 100, 500, 40),
            text_content="1. The Earth is flat. True or False?",
        )

        format_type = problem_segmenter._classify_problem_format(region, [])
        assert format_type == ProblemFormat.TRUE_FALSE

    def test_classify_problem_format_fill_blank(self, problem_segmenter):
        """Test classifying fill-in-blank problems."""
        region = LayoutRegion(
            region_id="test",
            region_type=RegionType.QUESTION,
            bounding_box=BoundingBox(50, 100, 500, 40),
            text_content="1. The capital of France is _____.",
        )

        format_type = problem_segmenter._classify_problem_format(region, [])
        assert format_type == ProblemFormat.FILL_IN_BLANK

    def test_classify_problem_format_calculation(self, problem_segmenter):
        """Test classifying calculation problems."""
        region = LayoutRegion(
            region_id="test",
            region_type=RegionType.QUESTION,
            bounding_box=BoundingBox(50, 100, 500, 40),
            text_content="1. Solve: 2 + 2 = ?",
        )

        format_type = problem_segmenter._classify_problem_format(region, [])
        assert format_type == ProblemFormat.CALCULATION

    def test_extract_problem_parts(self, problem_segmenter):
        """Test extracting problem parts."""
        region = LayoutRegion(
            region_id="test",
            region_type=RegionType.QUESTION,
            bounding_box=BoundingBox(50, 100, 500, 100),
            text_content="1. Choose one:\nA. First\nB. Second",
        )

        structure = DocumentStructure(regions=[region])
        parts = problem_segmenter.extract_problem_parts(region, structure)

        assert len(parts) > 0
        assert any(p.part_type == "number" for p in parts)
        assert any(p.part_type == "question" for p in parts)

    @pytest.mark.skipif(not CV2_AVAILABLE, reason="OpenCV not available")
    def test_segment_problems(self, problem_segmenter, worksheet_image, sample_ocr_result):
        """Test segmenting problems from worksheet."""
        result = problem_segmenter.segment_problems(worksheet_image, sample_ocr_result)

        assert isinstance(result, WorksheetProblems)
        assert result.total_count >= 0
        assert isinstance(result.problems, list)

    def test_estimate_difficulty(self, problem_segmenter):
        """Test estimating problem difficulty."""
        # Elementary
        easy_problem = Problem(
            problem_id="p1",
            problem_number="1",
            problem_format=ProblemFormat.MULTIPLE_CHOICE,
            question_text="What is 2+2?",
        )
        difficulty = problem_segmenter._estimate_difficulty(easy_problem)
        assert difficulty == ProblemDifficulty.ELEMENTARY

        # Advanced
        hard_problem = Problem(
            problem_id="p2",
            problem_number="2",
            problem_format=ProblemFormat.ESSAY,
            question_text="Explain the process of photosynthesis in detail, including all chemical reactions.",
        )
        difficulty = problem_segmenter._estimate_difficulty(hard_problem)
        assert difficulty == ProblemDifficulty.ADVANCED


class TestProblem:
    """Tests for Problem dataclass."""

    def test_problem_creation(self):
        """Test creating a Problem."""
        problem = Problem(
            problem_id="p1",
            problem_number="1",
            problem_format=ProblemFormat.SHORT_ANSWER,
            question_text="What is 2+2?",
        )

        assert problem.problem_id == "p1"
        assert problem.problem_number == "1"
        assert problem.problem_format == ProblemFormat.SHORT_ANSWER

    def test_problem_to_dict(self):
        """Test converting Problem to dict."""
        problem = Problem(
            problem_id="p1",
            problem_number="1",
            problem_format=ProblemFormat.SHORT_ANSWER,
            question_text="What is 2+2?",
            bounding_box=BoundingBox(50, 100, 500, 40),
        )

        problem_dict = problem.to_dict()

        assert problem_dict["problem_id"] == "p1"
        assert problem_dict["problem_format"] == "short_answer"
        assert problem_dict["question_text"] == "What is 2+2?"


class TestWorksheetProblems:
    """Tests for WorksheetProblems container."""

    def test_worksheet_creation(self):
        """Test creating WorksheetProblems."""
        problems = [
            Problem("p1", "1", ProblemFormat.MULTIPLE_CHOICE, "Question 1"),
            Problem("p2", "2", ProblemFormat.SHORT_ANSWER, "Question 2"),
        ]

        worksheet = WorksheetProblems(
            problems=problems,
            total_count=2,
            format_distribution={ProblemFormat.MULTIPLE_CHOICE: 1, ProblemFormat.SHORT_ANSWER: 1},
        )

        assert worksheet.total_count == 2
        assert len(worksheet.problems) == 2

    def test_worksheet_to_dict(self):
        """Test converting WorksheetProblems to dict."""
        worksheet = WorksheetProblems(problems=[], total_count=0)

        worksheet_dict = worksheet.to_dict()

        assert "problems" in worksheet_dict
        assert "total_count" in worksheet_dict
        assert worksheet_dict["total_count"] == 0


# Tests for convenience functions


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_extract_problem_by_number(self):
        """Test extracting problem by number."""
        problems = WorksheetProblems(
            problems=[
                Problem("p1", "1", ProblemFormat.SHORT_ANSWER, "Q1"),
                Problem("p2", "2", ProblemFormat.MULTIPLE_CHOICE, "Q2"),
                Problem("p3", "3", ProblemFormat.SHORT_ANSWER, "Q3"),
            ],
            total_count=3,
        )

        result = extract_problem_by_number(problems, "2")
        assert result is not None
        assert result.problem_number == "2"
        assert result.problem_format == ProblemFormat.MULTIPLE_CHOICE

        result = extract_problem_by_number(problems, "99")
        assert result is None

    def test_get_problems_by_format(self):
        """Test filtering problems by format."""
        problems = WorksheetProblems(
            problems=[
                Problem("p1", "1", ProblemFormat.SHORT_ANSWER, "Q1"),
                Problem("p2", "2", ProblemFormat.MULTIPLE_CHOICE, "Q2"),
                Problem("p3", "3", ProblemFormat.SHORT_ANSWER, "Q3"),
            ],
            total_count=3,
        )

        short_answer = get_problems_by_format(problems, ProblemFormat.SHORT_ANSWER)
        assert len(short_answer) == 2

        multiple_choice = get_problems_by_format(problems, ProblemFormat.MULTIPLE_CHOICE)
        assert len(multiple_choice) == 1


# Integration Tests


class TestLayoutAnalysisIntegration:
    """Integration tests for complete layout analysis workflow."""

    @pytest.mark.skipif(not CV2_AVAILABLE, reason="OpenCV not available")
    def test_full_workflow(self, layout_analyzer, problem_segmenter, worksheet_image):
        """Test complete analysis workflow."""
        # Analyze layout
        structure = layout_analyzer.analyze_layout(worksheet_image)

        assert len(structure.regions) > 0

        # Segment problems
        problems = problem_segmenter.segment_problems(worksheet_image, document_structure=structure)

        assert isinstance(problems, WorksheetProblems)
        assert problems.total_count >= 0

    @pytest.mark.skipif(not CV2_AVAILABLE, reason="OpenCV not available")
    def test_segment_worksheet_convenience(self, worksheet_image, sample_ocr_result):
        """Test convenience function for worksheet segmentation."""
        problems = segment_worksheet(worksheet_image, sample_ocr_result)

        assert isinstance(problems, WorksheetProblems)


# Performance Tests


class TestPerformance:
    """Tests for performance and accuracy requirements."""

    @pytest.mark.skipif(not CV2_AVAILABLE, reason="OpenCV not available")
    def test_layout_segmentation_coverage(self, layout_analyzer, worksheet_image):
        """Test that layout segmentation covers most of the document."""
        structure = layout_analyzer.analyze_layout(worksheet_image)

        # Calculate total area covered by regions
        total_area = sum(r.area() for r in structure.regions)
        image_area = worksheet_image.shape[0] * worksheet_image.shape[1]

        # Should cover at least 10% of image (accounting for whitespace)
        coverage = total_area / image_area
        assert coverage > 0.1, f"Coverage too low: {coverage:.2%}"

    def test_region_classification_confidence(self, layout_analyzer, sample_image):
        """Test that classified regions have reasonable confidence."""
        regions = [
            LayoutRegion(
                "r1",
                RegionType.TEXT_BLOCK,
                BoundingBox(50, 100, 500, 40),
                text_content="1. What is 2+2?",
            ),
            LayoutRegion(
                "r2",
                RegionType.TEXT_BLOCK,
                BoundingBox(50, 200, 500, 40),
                text_content="A. First\nB. Second",
            ),
        ]

        for region in regions:
            layout_analyzer.classify_region(region, sample_image)
            # Confidence should be within valid range
            assert 0.0 <= region.confidence <= 1.0


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
