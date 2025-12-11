"""
Document Layout Analyzer for EduLens - Educational Worksheet Structure Detection

This module provides comprehensive layout analysis capabilities for educational
worksheets, identifying problem boundaries, diagrams, answer spaces, and document
structure. Designed to handle multi-column layouts and mixed content types.

Author: Vision Processing Agent (VIS-001)
Target: 90% layout segmentation accuracy
Task: VIS-001-T3
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional, Any, Set
import numpy as np
from pathlib import Path
import logging
from collections import defaultdict

try:
    import cv2
except ImportError:
    cv2 = None

from src.vision.ocr_engine import BoundingBox, TextRegion, OCRResult


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RegionType(Enum):
    """Types of regions that can be detected in educational documents."""
    QUESTION = "question"
    ANSWER_SPACE = "answer_space"
    DIAGRAM = "diagram"
    IMAGE = "image"
    HEADER = "header"
    FOOTER = "footer"
    TITLE = "title"
    INSTRUCTION = "instruction"
    MULTIPLE_CHOICE = "multiple_choice"
    TABLE = "table"
    TEXT_BLOCK = "text_block"
    MARGIN = "margin"
    SEPARATOR = "separator"
    PAGE_NUMBER = "page_number"


class ContentType(Enum):
    """Content types within regions."""
    TEXT = "text"
    MATH = "math"
    IMAGE = "image"
    MIXED = "mixed"
    EMPTY = "empty"


@dataclass
class LayoutRegion:
    """
    Represents a detected region in the document layout.

    Attributes:
        region_id: Unique identifier for the region
        region_type: Type of region (question, diagram, etc.)
        bounding_box: Spatial bounds of the region
        content_type: Type of content within region
        confidence: Detection confidence score (0-1)
        text_content: Extracted text from region
        metadata: Additional region-specific metadata
        children: Child regions (for hierarchical structure)
        parent_id: ID of parent region if part of hierarchy
        reading_order: Position in document reading order
    """
    region_id: str
    region_type: RegionType
    bounding_box: BoundingBox
    content_type: ContentType = ContentType.TEXT
    confidence: float = 0.0
    text_content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    children: List['LayoutRegion'] = field(default_factory=list)
    parent_id: Optional[str] = None
    reading_order: int = -1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "region_id": self.region_id,
            "region_type": self.region_type.value,
            "bounding_box": self.bounding_box.to_dict(),
            "content_type": self.content_type.value,
            "confidence": self.confidence,
            "text_content": self.text_content,
            "metadata": self.metadata,
            "children": [child.to_dict() for child in self.children],
            "parent_id": self.parent_id,
            "reading_order": self.reading_order
        }

    def area(self) -> int:
        """Calculate region area in pixels."""
        return self.bounding_box.width * self.bounding_box.height

    def overlaps(self, other: 'LayoutRegion', threshold: float = 0.5) -> bool:
        """
        Check if this region overlaps with another region.

        Args:
            other: Another LayoutRegion to check against
            threshold: Minimum overlap ratio to consider as overlapping

        Returns:
            True if regions overlap above threshold
        """
        x1_1, y1_1, x2_1, y2_1 = self.bounding_box.to_coordinates()
        x1_2, y1_2, x2_2, y2_2 = other.bounding_box.to_coordinates()

        # Calculate intersection
        x_left = max(x1_1, x1_2)
        y_top = max(y1_1, y1_2)
        x_right = min(x2_1, x2_2)
        y_bottom = min(y2_1, y2_2)

        if x_right < x_left or y_bottom < y_top:
            return False

        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        min_area = min(self.area(), other.area())

        return (intersection_area / min_area) >= threshold if min_area > 0 else False


@dataclass
class DocumentStructure:
    """
    Represents the hierarchical structure of a document.

    Attributes:
        regions: All detected regions in the document
        hierarchy: Hierarchical organization of regions
        reading_order: Ordered list of region IDs for reading
        metadata: Document-level metadata
        num_columns: Detected number of columns
        layout_type: Type of layout (single-column, multi-column, etc.)
    """
    regions: List[LayoutRegion] = field(default_factory=list)
    hierarchy: Dict[str, List[str]] = field(default_factory=dict)
    reading_order: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    num_columns: int = 1
    layout_type: str = "single-column"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "regions": [region.to_dict() for region in self.regions],
            "hierarchy": self.hierarchy,
            "reading_order": self.reading_order,
            "metadata": self.metadata,
            "num_columns": self.num_columns,
            "layout_type": self.layout_type
        }

    def get_region_by_id(self, region_id: str) -> Optional[LayoutRegion]:
        """Get region by ID."""
        for region in self.regions:
            if region.region_id == region_id:
                return region
        return None

    def get_regions_by_type(self, region_type: RegionType) -> List[LayoutRegion]:
        """Get all regions of a specific type."""
        return [r for r in self.regions if r.region_type == region_type]


class LayoutAnalyzer:
    """
    Analyzes document layout to identify structure and content regions.

    This class provides comprehensive layout analysis for educational worksheets,
    including region detection, classification, and hierarchical structure extraction.
    """

    def __init__(
        self,
        min_region_size: int = 100,
        merge_threshold: float = 0.5,
        whitespace_threshold: int = 20,
        min_confidence: float = 0.6
    ):
        """
        Initialize the LayoutAnalyzer.

        Args:
            min_region_size: Minimum area for a valid region (pixels)
            merge_threshold: Threshold for merging nearby regions (0-1)
            whitespace_threshold: Minimum whitespace for region separation (pixels)
            min_confidence: Minimum confidence for region classification
        """
        self.min_region_size = min_region_size
        self.merge_threshold = merge_threshold
        self.whitespace_threshold = whitespace_threshold
        self.min_confidence = min_confidence
        self._region_counter = 0

        if cv2 is None:
            logger.warning("OpenCV not available. Some layout analysis features will be limited.")

    def analyze_layout(
        self,
        image: np.ndarray,
        ocr_result: Optional[OCRResult] = None
    ) -> DocumentStructure:
        """
        Perform complete layout analysis on a document image.

        Args:
            image: Document image as numpy array
            ocr_result: Optional OCR results to enhance analysis

        Returns:
            DocumentStructure containing all detected regions and hierarchy
        """
        logger.info("Starting document layout analysis")

        # Detect all regions in the document
        regions = self.detect_regions(image, ocr_result)

        # Classify each region
        for region in regions:
            self._classify_region(region, image, ocr_result)

        # Extract hierarchical structure
        structure = self.extract_structure(regions, image)

        # Determine reading order
        reading_order = self.get_reading_order(structure)
        structure.reading_order = reading_order

        # Detect layout type and columns
        structure.num_columns = self._detect_columns(regions, image.shape[1])
        structure.layout_type = self._determine_layout_type(structure)

        logger.info(f"Layout analysis complete: {len(regions)} regions detected, "
                   f"{structure.num_columns} columns, {structure.layout_type} layout")

        return structure

    def detect_regions(
        self,
        image: np.ndarray,
        ocr_result: Optional[OCRResult] = None
    ) -> List[LayoutRegion]:
        """
        Detect distinct content regions in the document.

        Uses a combination of:
        - Whitespace analysis
        - Connected component analysis
        - OCR text region grouping
        - Visual feature detection

        Args:
            image: Document image as numpy array
            ocr_result: Optional OCR results to guide region detection

        Returns:
            List of detected LayoutRegion objects
        """
        regions = []

        if cv2 is None:
            logger.warning("OpenCV not available, falling back to OCR-based detection")
            if ocr_result:
                return self._regions_from_ocr(ocr_result)
            return regions

        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )

        # Detect text regions using morphological operations
        text_regions = self._detect_text_regions(binary)

        # Detect image/diagram regions
        image_regions = self._detect_image_regions(gray, binary)

        # Detect whitespace/separator regions
        whitespace_regions = self._detect_whitespace_regions(binary)

        # Combine and merge overlapping regions
        all_regions = text_regions + image_regions
        merged_regions = self._merge_regions(all_regions)

        # Convert to LayoutRegion objects
        for bbox in merged_regions:
            region = LayoutRegion(
                region_id=self._get_next_region_id(),
                region_type=RegionType.TEXT_BLOCK,  # Will be classified later
                bounding_box=bbox,
                confidence=0.7
            )
            regions.append(region)

        # Add OCR information if available
        if ocr_result:
            self._enhance_with_ocr(regions, ocr_result)

        logger.info(f"Detected {len(regions)} initial regions")
        return regions

    def classify_region(
        self,
        region: LayoutRegion,
        image: np.ndarray,
        ocr_result: Optional[OCRResult] = None
    ) -> RegionType:
        """
        Classify a region into its type (question, answer, diagram, etc.).

        Uses multiple classification strategies:
        - Text pattern analysis (question numbers, keywords)
        - Visual features (blank spaces, lines)
        - Position and size heuristics
        - Content analysis

        Args:
            region: LayoutRegion to classify
            image: Document image
            ocr_result: Optional OCR results for text analysis

        Returns:
            Classified RegionType
        """
        return self._classify_region(region, image, ocr_result)

    def _classify_region(
        self,
        region: LayoutRegion,
        image: np.ndarray,
        ocr_result: Optional[OCRResult] = None
    ) -> RegionType:
        """Internal method for region classification."""
        # Extract region image
        x1, y1, x2, y2 = region.bounding_box.to_coordinates()
        region_img = image[y1:y2, x1:x2] if cv2 is not None else None

        # Analyze text content
        text = region.text_content.lower().strip()

        # Classification rules
        confidence_scores = {}

        # Header detection (top of page, short text, larger font)
        if y1 < image.shape[0] * 0.15 and len(text) < 100:
            confidence_scores[RegionType.HEADER] = 0.8

        # Title detection (bold, centered, short)
        if self._is_title_region(region, image):
            confidence_scores[RegionType.TITLE] = 0.75

        # Question detection (starts with number, question words)
        if self._is_question_region(region, text):
            confidence_scores[RegionType.QUESTION] = 0.85

        # Answer space detection (blank area, lines, boxes)
        if region_img is not None and self._is_answer_space(region_img):
            confidence_scores[RegionType.ANSWER_SPACE] = 0.8

        # Multiple choice detection (A. B. C. D. pattern)
        if self._is_multiple_choice(text):
            confidence_scores[RegionType.MULTIPLE_CHOICE] = 0.85

        # Diagram/image detection (low text density, high visual complexity)
        if region_img is not None and self._is_diagram_region(region_img, text):
            confidence_scores[RegionType.DIAGRAM] = 0.75

        # Instruction detection (keywords: "directions", "instructions")
        if self._is_instruction_region(text):
            confidence_scores[RegionType.INSTRUCTION] = 0.8

        # Footer detection (bottom of page, page numbers)
        if y1 > image.shape[0] * 0.85:
            confidence_scores[RegionType.FOOTER] = 0.7

        # Select best classification
        if confidence_scores:
            best_type = max(confidence_scores, key=confidence_scores.get)
            region.region_type = best_type
            region.confidence = confidence_scores[best_type]
            return best_type

        # Default to text block
        region.region_type = RegionType.TEXT_BLOCK
        region.confidence = 0.5
        return RegionType.TEXT_BLOCK

    def extract_structure(
        self,
        regions: List[LayoutRegion],
        image: np.ndarray
    ) -> DocumentStructure:
        """
        Extract hierarchical document structure from regions.

        Builds a tree structure where:
        - Questions are parents of answer spaces
        - Sections contain multiple questions
        - Headers/titles are high-level nodes

        Args:
            regions: List of detected and classified regions
            image: Document image for spatial analysis

        Returns:
            DocumentStructure with hierarchical organization
        """
        structure = DocumentStructure(regions=regions)

        # Build spatial index for efficient queries
        spatial_index = self._build_spatial_index(regions)

        # Group related regions
        for region in regions:
            if region.region_type == RegionType.QUESTION:
                # Find associated answer spaces below the question
                answer_spaces = self._find_answer_spaces_for_question(
                    region, regions, spatial_index
                )
                for answer in answer_spaces:
                    answer.parent_id = region.region_id
                    region.children.append(answer)
                    structure.hierarchy.setdefault(region.region_id, []).append(answer.region_id)

            elif region.region_type == RegionType.DIAGRAM:
                # Find nearby questions that might reference this diagram
                nearby_questions = self._find_nearby_questions(
                    region, regions, spatial_index
                )
                region.metadata['related_questions'] = [q.region_id for q in nearby_questions]

        # Identify section headers and their content
        headers = [r for r in regions if r.region_type in [RegionType.HEADER, RegionType.TITLE]]
        for header in headers:
            section_content = self._find_section_content(header, regions, image.shape[0])
            for content_region in section_content:
                if content_region.parent_id is None:  # Don't override existing parent
                    content_region.parent_id = header.region_id
                    header.children.append(content_region)
                    structure.hierarchy.setdefault(header.region_id, []).append(content_region.region_id)

        return structure

    def get_reading_order(self, structure: DocumentStructure) -> List[str]:
        """
        Determine the logical reading order of regions.

        Handles:
        - Single-column layouts (top to bottom)
        - Multi-column layouts (column-wise reading)
        - Headers and footers (read first/last)
        - Question-answer groupings (keep together)

        Args:
            structure: DocumentStructure to order

        Returns:
            Ordered list of region IDs
        """
        regions = structure.regions

        if not regions:
            return []

        # Separate by type
        headers = [r for r in regions if r.region_type in [RegionType.HEADER, RegionType.TITLE]]
        footers = [r for r in regions if r.region_type == RegionType.FOOTER]
        content = [r for r in regions if r.region_type not in [RegionType.HEADER, RegionType.TITLE, RegionType.FOOTER]]

        # Sort headers by vertical position
        headers.sort(key=lambda r: r.bounding_box.y)

        # Sort content based on column layout
        if structure.num_columns > 1:
            content_ordered = self._sort_multi_column(content, structure.num_columns)
        else:
            content_ordered = self._sort_single_column(content)

        # Sort footers
        footers.sort(key=lambda r: r.bounding_box.y)

        # Combine in reading order
        ordered = headers + content_ordered + footers

        # Update reading_order field on each region
        for idx, region in enumerate(ordered):
            region.reading_order = idx

        return [r.region_id for r in ordered]

    # Helper methods

    def _get_next_region_id(self) -> str:
        """Generate unique region ID."""
        self._region_counter += 1
        return f"region_{self._region_counter:04d}"

    def _detect_text_regions(self, binary: np.ndarray) -> List[BoundingBox]:
        """Detect text regions using morphological operations."""
        if cv2 is None:
            return []

        # Dilate to connect nearby text
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 5))
        dilated = cv2.dilate(binary, kernel, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        bboxes = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w * h >= self.min_region_size:
                bboxes.append(BoundingBox(x, y, w, h))

        return bboxes

    def _detect_image_regions(self, gray: np.ndarray, binary: np.ndarray) -> List[BoundingBox]:
        """Detect image/diagram regions using edge detection."""
        if cv2 is None:
            return []

        # Edge detection
        edges = cv2.Canny(gray, 50, 150)

        # Dilate edges
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        dilated = cv2.dilate(edges, kernel, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        bboxes = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            # Look for rectangular regions with substantial area
            if w * h >= self.min_region_size * 5:  # Images are typically larger
                bboxes.append(BoundingBox(x, y, w, h))

        return bboxes

    def _detect_whitespace_regions(self, binary: np.ndarray) -> List[BoundingBox]:
        """Detect significant whitespace that separates regions."""
        # Not implemented in basic version
        return []

    def _merge_regions(self, regions: List[BoundingBox]) -> List[BoundingBox]:
        """Merge overlapping or nearby regions."""
        if not regions:
            return []

        # Sort by y-coordinate
        regions = sorted(regions, key=lambda b: (b.y, b.x))

        merged = [regions[0]]

        for current in regions[1:]:
            last = merged[-1]

            # Check if regions should be merged
            if self._should_merge_boxes(last, current):
                # Merge boxes
                x1 = min(last.x, current.x)
                y1 = min(last.y, current.y)
                x2 = max(last.x + last.width, current.x + current.width)
                y2 = max(last.y + last.height, current.y + current.height)
                merged[-1] = BoundingBox(x1, y1, x2 - x1, y2 - y1)
            else:
                merged.append(current)

        return merged

    def _should_merge_boxes(self, box1: BoundingBox, box2: BoundingBox) -> bool:
        """Determine if two bounding boxes should be merged."""
        x1_1, y1_1, x2_1, y2_1 = box1.to_coordinates()
        x1_2, y1_2, x2_2, y2_2 = box2.to_coordinates()

        # Check for overlap or proximity
        h_overlap = not (x2_1 < x1_2 - self.whitespace_threshold or x2_2 < x1_1 - self.whitespace_threshold)
        v_overlap = not (y2_1 < y1_2 - self.whitespace_threshold or y2_2 < y1_1 - self.whitespace_threshold)

        return h_overlap and v_overlap

    def _regions_from_ocr(self, ocr_result: OCRResult) -> List[LayoutRegion]:
        """Create regions from OCR text regions."""
        regions = []
        for text_region in ocr_result.regions:
            region = LayoutRegion(
                region_id=self._get_next_region_id(),
                region_type=RegionType.TEXT_BLOCK,
                bounding_box=text_region.bounding_box,
                text_content=text_region.text,
                confidence=text_region.confidence
            )
            regions.append(region)
        return regions

    def _enhance_with_ocr(self, regions: List[LayoutRegion], ocr_result: OCRResult):
        """Add OCR text content to detected regions."""
        for region in regions:
            # Find OCR text regions within this layout region
            x1, y1, x2, y2 = region.bounding_box.to_coordinates()
            region_text = []

            for text_region in ocr_result.regions:
                tx1, ty1, tx2, ty2 = text_region.bounding_box.to_coordinates()

                # Check if OCR region is within layout region
                if tx1 >= x1 and ty1 >= y1 and tx2 <= x2 and ty2 <= y2:
                    region_text.append(text_region.text)

            region.text_content = " ".join(region_text)

    def _is_title_region(self, region: LayoutRegion, image: np.ndarray) -> bool:
        """Check if region is likely a title."""
        text = region.text_content.strip()
        y_pos = region.bounding_box.y / image.shape[0]

        # Title characteristics: short, near top, possibly centered
        return (len(text) < 80 and
                y_pos < 0.2 and
                not text.endswith('?') and
                not any(c.isdigit() for c in text[:3]))

    def _is_question_region(self, region: LayoutRegion, text: str) -> bool:
        """Check if region contains a question."""
        question_patterns = [
            r'^\d+[\.\)]\s',  # Starts with number
            r'\?',  # Contains question mark
            r'\bwhat\b', r'\bwhere\b', r'\bwhen\b', r'\bwho\b', r'\bwhy\b', r'\bhow\b',
            r'\bsolve\b', r'\bcalculate\b', r'\bfind\b', r'\bwrite\b'
        ]

        import re
        for pattern in question_patterns:
            if re.search(pattern, text):
                return True
        return False

    def _is_answer_space(self, region_img: np.ndarray) -> bool:
        """Check if region is an answer space (blank area with lines/boxes)."""
        if cv2 is None:
            return False

        # Convert to grayscale if needed
        if len(region_img.shape) == 3:
            gray = cv2.cvtColor(region_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = region_img

        # Check for horizontal lines (common in answer spaces)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=50, maxLineGap=10)

        # Answer spaces typically have lines and low text density
        has_lines = lines is not None and len(lines) > 0

        # Check text density (answer spaces should be mostly empty)
        binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        text_density = np.sum(binary == 0) / binary.size

        return has_lines and text_density < 0.1

    def _is_multiple_choice(self, text: str) -> bool:
        """Check if region contains multiple choice options."""
        import re
        # Look for A. B. C. D. or (A) (B) (C) pattern
        pattern = r'[A-D][\.\)]\s+\w+'
        matches = re.findall(pattern, text)
        return len(matches) >= 2

    def _is_diagram_region(self, region_img: np.ndarray, text: str) -> bool:
        """Check if region contains a diagram or image."""
        if cv2 is None:
            return False

        # Low text density and high edge density suggests diagram
        if len(region_img.shape) == 3:
            gray = cv2.cvtColor(region_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = region_img

        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size

        # Diagrams have high edge density and low text
        return edge_density > 0.05 and len(text) < 50

    def _is_instruction_region(self, text: str) -> bool:
        """Check if region contains instructions."""
        instruction_keywords = [
            'directions', 'instructions', 'read carefully', 'complete',
            'fill in', 'circle', 'underline', 'match', 'draw'
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in instruction_keywords)

    def _detect_columns(self, regions: List[LayoutRegion], page_width: int) -> int:
        """Detect number of columns in the layout."""
        if not regions:
            return 1

        # Analyze horizontal distribution of regions
        x_positions = [r.bounding_box.x + r.bounding_box.width // 2 for r in regions]

        # Use histogram to detect column structure
        hist, bins = np.histogram(x_positions, bins=10)

        # Count peaks (potential columns)
        peaks = 0
        threshold = len(regions) * 0.1
        for count in hist:
            if count > threshold:
                peaks += 1

        return max(1, min(peaks, 3))  # Limit to 3 columns

    def _determine_layout_type(self, structure: DocumentStructure) -> str:
        """Determine overall layout type."""
        if structure.num_columns == 1:
            return "single-column"
        elif structure.num_columns == 2:
            return "two-column"
        elif structure.num_columns >= 3:
            return "multi-column"
        return "complex"

    def _build_spatial_index(self, regions: List[LayoutRegion]) -> Dict[str, Any]:
        """Build spatial index for efficient region queries."""
        return {
            'regions': regions,
            'sorted_by_y': sorted(regions, key=lambda r: r.bounding_box.y),
            'sorted_by_x': sorted(regions, key=lambda r: r.bounding_box.x)
        }

    def _find_answer_spaces_for_question(
        self,
        question: LayoutRegion,
        all_regions: List[LayoutRegion],
        spatial_index: Dict[str, Any]
    ) -> List[LayoutRegion]:
        """Find answer spaces associated with a question."""
        answer_spaces = []
        q_bottom = question.bounding_box.y + question.bounding_box.height

        for region in all_regions:
            if region.region_type == RegionType.ANSWER_SPACE:
                # Answer space should be below or near the question
                if region.bounding_box.y >= q_bottom - 10:
                    # Check horizontal alignment
                    h_overlap = not (
                        question.bounding_box.x + question.bounding_box.width < region.bounding_box.x or
                        region.bounding_box.x + region.bounding_box.width < question.bounding_box.x
                    )
                    if h_overlap:
                        answer_spaces.append(region)

        return answer_spaces

    def _find_nearby_questions(
        self,
        diagram: LayoutRegion,
        all_regions: List[LayoutRegion],
        spatial_index: Dict[str, Any]
    ) -> List[LayoutRegion]:
        """Find questions near a diagram."""
        nearby = []
        d_center_x = diagram.bounding_box.x + diagram.bounding_box.width // 2
        d_center_y = diagram.bounding_box.y + diagram.bounding_box.height // 2

        for region in all_regions:
            if region.region_type == RegionType.QUESTION:
                r_center_x = region.bounding_box.x + region.bounding_box.width // 2
                r_center_y = region.bounding_box.y + region.bounding_box.height // 2

                # Calculate distance
                distance = np.sqrt((d_center_x - r_center_x)**2 + (d_center_y - r_center_y)**2)

                # Consider nearby if within reasonable distance
                if distance < 300:  # pixels
                    nearby.append(region)

        return nearby

    def _find_section_content(
        self,
        header: LayoutRegion,
        all_regions: List[LayoutRegion],
        page_height: int
    ) -> List[LayoutRegion]:
        """Find content belonging to a section header."""
        content = []
        header_bottom = header.bounding_box.y + header.bounding_box.height

        # Find next header or end of page
        next_header_y = page_height
        for region in all_regions:
            if (region.region_type in [RegionType.HEADER, RegionType.TITLE] and
                region.region_id != header.region_id and
                region.bounding_box.y > header_bottom):
                next_header_y = region.bounding_box.y
                break

        # Collect regions between this header and next
        for region in all_regions:
            if (region.region_id != header.region_id and
                header_bottom <= region.bounding_box.y < next_header_y):
                content.append(region)

        return content

    def _sort_single_column(self, regions: List[LayoutRegion]) -> List[LayoutRegion]:
        """Sort regions for single-column layout (top to bottom)."""
        return sorted(regions, key=lambda r: (r.bounding_box.y, r.bounding_box.x))

    def _sort_multi_column(
        self,
        regions: List[LayoutRegion],
        num_columns: int
    ) -> List[LayoutRegion]:
        """Sort regions for multi-column layout."""
        if not regions:
            return []

        # Determine column boundaries
        x_positions = sorted([r.bounding_box.x for r in regions])
        column_boundaries = []

        # Simple column division
        min_x = min(x_positions)
        max_x = max([r.bounding_box.x + r.bounding_box.width for r in regions])
        column_width = (max_x - min_x) / num_columns

        for i in range(num_columns):
            column_boundaries.append((
                min_x + i * column_width,
                min_x + (i + 1) * column_width
            ))

        # Assign regions to columns
        columns = [[] for _ in range(num_columns)]
        for region in regions:
            center_x = region.bounding_box.x + region.bounding_box.width // 2
            for col_idx, (col_start, col_end) in enumerate(column_boundaries):
                if col_start <= center_x < col_end:
                    columns[col_idx].append(region)
                    break

        # Sort within each column and combine
        sorted_regions = []
        for column in columns:
            sorted_column = sorted(column, key=lambda r: r.bounding_box.y)
            sorted_regions.extend(sorted_column)

        return sorted_regions
