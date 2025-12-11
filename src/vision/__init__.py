"""
EduLens Vision Processing Module

This module provides OCR and image processing capabilities optimized
for elementary educational materials (ages 6-12).

Author: Vision Processing Agent (VIS-001)
"""

from src.vision.ocr_engine import (
    OCREngine,
    BaseOCREngine,
    OCRBackend,
    DocumentType,
    BoundingBox,
    TextRegion,
    OCRResult
)

from src.vision.preprocessing import ImagePreprocessor

from src.vision.layout_analyzer import (
    LayoutAnalyzer,
    LayoutRegion,
    RegionType,
    ContentType,
    DocumentStructure
)

from src.vision.problem_segmenter import (
    ProblemSegmenter,
    Problem,
    ProblemPart,
    ProblemFormat,
    ProblemDifficulty,
    WorksheetProblems,
    segment_worksheet,
    extract_problem_by_number,
    get_problems_by_format
)

__all__ = [
    # OCR Engine
    "OCREngine",
    "BaseOCREngine",
    "OCRBackend",
    "DocumentType",
    "BoundingBox",
    "TextRegion",
    "OCRResult",
    # Preprocessing
    "ImagePreprocessor",
    # Layout Analysis
    "LayoutAnalyzer",
    "LayoutRegion",
    "RegionType",
    "ContentType",
    "DocumentStructure",
    # Problem Segmentation
    "ProblemSegmenter",
    "Problem",
    "ProblemPart",
    "ProblemFormat",
    "ProblemDifficulty",
    "WorksheetProblems",
    "segment_worksheet",
    "extract_problem_by_number",
    "get_problems_by_format"
]

__version__ = "1.1.0"
