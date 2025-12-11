"""
Character and Word Segmentation for Handwriting Recognition

This module provides sophisticated segmentation algorithms for separating
individual characters and words from handwritten text. It's optimized for
children's handwriting (ages 6-12) which often has irregular spacing and
varied letter formations.

Key Features:
- Projection-based segmentation for line and character separation
- Connected component analysis for character isolation
- Word boundary detection with adaptive spacing thresholds
- Multi-pass segmentation for challenging cases

Author: Vision Processing Agent (VIS-001)
Target: Handle varied child handwriting styles
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field
import logging

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from scipy import ndimage
    from scipy.signal import find_peaks
except ImportError:
    ndimage = None
    find_peaks = None


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Segment:
    """Represents a segmented region (character or word)."""
    x: int
    y: int
    width: int
    height: int
    image: Optional[np.ndarray] = None
    segment_type: str = "character"  # "character", "word", or "line"
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "segment_type": self.segment_type,
            "confidence": self.confidence
        }

    def get_bbox(self) -> Tuple[int, int, int, int]:
        """Get bounding box as (x, y, x+w, y+h)."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)


@dataclass
class SegmentationResult:
    """Complete segmentation result."""
    lines: List[Segment] = field(default_factory=list)
    words: List[Segment] = field(default_factory=list)
    characters: List[Segment] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "lines": [line.to_dict() for line in self.lines],
            "words": [word.to_dict() for word in self.words],
            "characters": [char.to_dict() for char in self.characters],
            "metadata": self.metadata
        }


class CharacterSegmenter:
    """
    Advanced character and word segmentation for handwritten text.

    This class implements multiple segmentation strategies optimized for
    children's handwriting, which often exhibits:
    - Inconsistent letter spacing
    - Variable letter sizes
    - Irregular baselines
    - Connected or overlapping letters
    - Mixed printed and cursive attempts

    Attributes:
        config: Configuration dictionary for segmentation parameters
        min_component_area: Minimum area for valid character components
        max_component_area: Maximum area for valid character components
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the character segmenter.

        Args:
            config: Configuration dictionary with segmentation parameters
        """
        self.config = config or {}

        # Component filtering parameters
        self.min_component_area = self.config.get("min_component_area", 20)
        self.max_component_area = self.config.get("max_component_area", 10000)

        # Spacing thresholds (adaptive based on character width)
        self.char_spacing_factor = self.config.get("char_spacing_factor", 0.3)
        self.word_spacing_factor = self.config.get("word_spacing_factor", 1.5)

        # Line detection parameters
        self.min_line_height = self.config.get("min_line_height", 15)
        self.line_spacing_threshold = self.config.get("line_spacing_threshold", 10)

        # Validation
        self._validate_dependencies()

        logger.debug("CharacterSegmenter initialized")

    def _validate_dependencies(self) -> None:
        """Validate that required dependencies are available."""
        if cv2 is None:
            raise ImportError("OpenCV (cv2) is required. Install with: pip install opencv-python")
        if ndimage is None or find_peaks is None:
            raise ImportError("SciPy is required. Install with: pip install scipy")

    def segment_all(
        self,
        image: np.ndarray,
        segment_lines: bool = True,
        segment_words: bool = True,
        segment_characters: bool = True
    ) -> SegmentationResult:
        """
        Perform complete segmentation (lines, words, characters).

        Args:
            image: Input binary or grayscale image
            segment_lines: Whether to segment lines
            segment_words: Whether to segment words
            segment_characters: Whether to segment characters

        Returns:
            SegmentationResult with all segmented regions
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        result = SegmentationResult()

        # Convert to grayscale if needed
        gray = self._ensure_grayscale(image)

        # Binarize if not already binary
        binary = self._ensure_binary(gray)

        # Segment lines
        if segment_lines:
            result.lines = self.segment_lines(binary)
            logger.debug(f"Segmented {len(result.lines)} lines")

        # Segment words
        if segment_words:
            if result.lines:
                # Segment words within each line
                for line in result.lines:
                    line_image = binary[line.y:line.y+line.height, line.x:line.x+line.width]
                    words = self.segment_words(line_image)
                    # Adjust coordinates to global space
                    for word in words:
                        word.x += line.x
                        word.y += line.y
                    result.words.extend(words)
            else:
                # Segment words from full image
                result.words = self.segment_words(binary)
            logger.debug(f"Segmented {len(result.words)} words")

        # Segment characters
        if segment_characters:
            if result.words:
                # Segment characters within each word
                for word in result.words:
                    word_image = binary[word.y:word.y+word.height, word.x:word.x+word.width]
                    chars = self.segment_characters(word_image)
                    # Adjust coordinates to global space
                    for char in chars:
                        char.x += word.x
                        char.y += word.y
                    result.characters.extend(chars)
            else:
                # Segment characters from full image
                result.characters = self.segment_characters(binary)
            logger.debug(f"Segmented {len(result.characters)} characters")

        # Add metadata
        result.metadata = {
            "image_shape": image.shape,
            "num_lines": len(result.lines),
            "num_words": len(result.words),
            "num_characters": len(result.characters)
        }

        return result

    def segment_lines(self, image: np.ndarray) -> List[Segment]:
        """
        Segment text lines using horizontal projection.

        This method uses horizontal projection profile to identify text lines.
        It's robust to slight rotations and varying line spacing.

        Args:
            image: Binary or grayscale image

        Returns:
            List of Segment objects representing text lines
        """
        if image is None or image.size == 0:
            return []

        try:
            # Ensure binary
            binary = self._ensure_binary(self._ensure_grayscale(image))

            # Invert if text is white on black
            if np.mean(binary) > 127:
                binary = cv2.bitwise_not(binary)

            # Compute horizontal projection (sum of black pixels per row)
            h_projection = np.sum(binary == 0, axis=1)

            # Smooth projection to handle small gaps
            kernel_size = max(3, min(11, image.shape[0] // 20))
            if kernel_size % 2 == 0:
                kernel_size += 1
            h_projection_smooth = cv2.GaussianBlur(
                h_projection.reshape(-1, 1).astype(np.float32),
                (1, kernel_size),
                0
            ).flatten()

            # Find valleys (spaces between lines)
            threshold = np.mean(h_projection_smooth) * 0.2
            in_line = False
            line_start = 0
            lines = []

            for i, value in enumerate(h_projection_smooth):
                if value > threshold and not in_line:
                    # Start of a line
                    line_start = i
                    in_line = True
                elif value <= threshold and in_line:
                    # End of a line
                    if i - line_start >= self.min_line_height:
                        line = Segment(
                            x=0,
                            y=line_start,
                            width=image.shape[1],
                            height=i - line_start,
                            segment_type="line"
                        )
                        lines.append(line)
                    in_line = False

            # Handle last line
            if in_line and image.shape[0] - line_start >= self.min_line_height:
                line = Segment(
                    x=0,
                    y=line_start,
                    width=image.shape[1],
                    height=image.shape[0] - line_start,
                    segment_type="line"
                )
                lines.append(line)

            return lines

        except Exception as e:
            logger.error(f"Error segmenting lines: {e}")
            return []

    def segment_words(self, image: np.ndarray) -> List[Segment]:
        """
        Segment words using vertical projection and adaptive spacing.

        This method identifies word boundaries by analyzing gaps in the
        vertical projection profile. It adapts to varying character sizes.

        Args:
            image: Binary or grayscale image (typically a single line)

        Returns:
            List of Segment objects representing words
        """
        if image is None or image.size == 0:
            return []

        try:
            # Ensure binary
            binary = self._ensure_binary(self._ensure_grayscale(image))

            # Invert if needed
            if np.mean(binary) > 127:
                binary = cv2.bitwise_not(binary)

            # Compute vertical projection
            v_projection = np.sum(binary == 0, axis=0)

            # Estimate typical character width
            non_zero_indices = np.where(v_projection > 0)[0]
            if len(non_zero_indices) == 0:
                return []

            # Find character boundaries
            gaps = []
            in_char = False
            char_start = 0
            char_widths = []

            for i, value in enumerate(v_projection):
                if value > 0 and not in_char:
                    char_start = i
                    in_char = True
                elif value == 0 and in_char:
                    char_widths.append(i - char_start)
                    in_char = False
                elif value == 0 and not in_char:
                    if i > 0 and v_projection[i-1] == 0:
                        gaps.append(i)

            # Calculate adaptive spacing threshold
            if char_widths:
                avg_char_width = np.median(char_widths)
                word_spacing_threshold = avg_char_width * self.word_spacing_factor
            else:
                word_spacing_threshold = 20  # Default fallback

            # Identify word boundaries
            word_boundaries = [0]
            current_gap_start = None

            for i, value in enumerate(v_projection):
                if value == 0:
                    if current_gap_start is None:
                        current_gap_start = i
                else:
                    if current_gap_start is not None:
                        gap_width = i - current_gap_start
                        if gap_width >= word_spacing_threshold:
                            word_boundaries.append(i)
                        current_gap_start = None

            word_boundaries.append(len(v_projection))

            # Create word segments
            words = []
            for i in range(len(word_boundaries) - 1):
                start = word_boundaries[i]
                end = word_boundaries[i + 1]

                # Find actual content bounds within this region
                region_proj = v_projection[start:end]
                non_zero = np.where(region_proj > 0)[0]

                if len(non_zero) > 0:
                    content_start = start + non_zero[0]
                    content_end = start + non_zero[-1] + 1

                    # Find vertical bounds
                    word_region = binary[:, content_start:content_end]
                    h_proj = np.sum(word_region == 0, axis=1)
                    non_zero_rows = np.where(h_proj > 0)[0]

                    if len(non_zero_rows) > 0:
                        y_start = non_zero_rows[0]
                        y_end = non_zero_rows[-1] + 1

                        word = Segment(
                            x=content_start,
                            y=y_start,
                            width=content_end - content_start,
                            height=y_end - y_start,
                            segment_type="word"
                        )
                        words.append(word)

            return words

        except Exception as e:
            logger.error(f"Error segmenting words: {e}")
            return []

    def segment_characters(self, image: np.ndarray) -> List[Segment]:
        """
        Segment individual characters using connected component analysis.

        This method uses connected component labeling combined with
        projection-based refinement for robust character segmentation.
        It handles both isolated and connected characters.

        Args:
            image: Binary or grayscale image (typically a single word)

        Returns:
            List of Segment objects representing characters
        """
        if image is None or image.size == 0:
            return []

        try:
            # Ensure binary
            binary = self._ensure_binary(self._ensure_grayscale(image))

            # Invert if needed
            if np.mean(binary) > 127:
                binary = cv2.bitwise_not(binary)

            # First try connected component analysis
            characters = self._segment_by_connected_components(binary)

            # If we get too few or merged characters, try projection method
            if len(characters) == 0:
                characters = self._segment_by_projection(binary)

            # Sort characters left to right
            characters.sort(key=lambda seg: seg.x)

            return characters

        except Exception as e:
            logger.error(f"Error segmenting characters: {e}")
            return []

    def _segment_by_connected_components(self, binary: np.ndarray) -> List[Segment]:
        """
        Segment characters using connected component analysis.

        Args:
            binary: Binary image (black text on white background)

        Returns:
            List of character segments
        """
        try:
            # Find connected components
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
                binary, connectivity=8
            )

            characters = []

            # Process each component (skip background label 0)
            for label in range(1, num_labels):
                x = stats[label, cv2.CC_STAT_LEFT]
                y = stats[label, cv2.CC_STAT_TOP]
                w = stats[label, cv2.CC_STAT_WIDTH]
                h = stats[label, cv2.CC_STAT_HEIGHT]
                area = stats[label, cv2.CC_STAT_AREA]

                # Filter by area
                if area < self.min_component_area or area > self.max_component_area:
                    continue

                # Filter by aspect ratio (avoid very thin components)
                if w < 3 or h < 5:
                    continue

                char = Segment(
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                    segment_type="character"
                )
                characters.append(char)

            return characters

        except Exception as e:
            logger.error(f"Error in connected component segmentation: {e}")
            return []

    def _segment_by_projection(self, binary: np.ndarray) -> List[Segment]:
        """
        Segment characters using vertical projection profile.

        This is a fallback method when connected components fail or
        when characters are connected.

        Args:
            binary: Binary image (black text on white background)

        Returns:
            List of character segments
        """
        try:
            # Compute vertical projection
            v_projection = np.sum(binary == 0, axis=0)

            # Find character boundaries (valleys in projection)
            in_char = False
            char_start = 0
            characters = []

            for i, value in enumerate(v_projection):
                if value > 0 and not in_char:
                    # Start of character
                    char_start = i
                    in_char = True
                elif value == 0 and in_char:
                    # End of character
                    if i - char_start >= 3:  # Minimum width
                        # Find vertical bounds
                        char_region = binary[:, char_start:i]
                        h_proj = np.sum(char_region == 0, axis=1)
                        non_zero_rows = np.where(h_proj > 0)[0]

                        if len(non_zero_rows) > 0:
                            y_start = non_zero_rows[0]
                            y_end = non_zero_rows[-1] + 1

                            char = Segment(
                                x=char_start,
                                y=y_start,
                                width=i - char_start,
                                height=y_end - y_start,
                                segment_type="character"
                            )
                            characters.append(char)

                    in_char = False

            # Handle last character
            if in_char and len(v_projection) - char_start >= 3:
                char_region = binary[:, char_start:]
                h_proj = np.sum(char_region == 0, axis=1)
                non_zero_rows = np.where(h_proj > 0)[0]

                if len(non_zero_rows) > 0:
                    y_start = non_zero_rows[0]
                    y_end = non_zero_rows[-1] + 1

                    char = Segment(
                        x=char_start,
                        y=y_start,
                        width=len(v_projection) - char_start,
                        height=y_end - y_start,
                        segment_type="character"
                    )
                    characters.append(char)

            return characters

        except Exception as e:
            logger.error(f"Error in projection-based segmentation: {e}")
            return []

    def detect_word_boundaries(
        self,
        image: np.ndarray,
        characters: List[Segment]
    ) -> List[Tuple[int, int]]:
        """
        Detect word boundaries from character segments.

        Analyzes spacing between characters to identify word boundaries.

        Args:
            image: Binary or grayscale image
            characters: List of character segments (sorted left to right)

        Returns:
            List of (start_idx, end_idx) tuples representing word boundaries
        """
        if not characters:
            return []

        try:
            # Calculate gaps between consecutive characters
            gaps = []
            char_widths = []

            for i in range(len(characters) - 1):
                char_widths.append(characters[i].width)
                gap = characters[i + 1].x - (characters[i].x + characters[i].width)
                gaps.append(gap)

            if characters:
                char_widths.append(characters[-1].width)

            if not gaps:
                return [(0, len(characters))]

            # Calculate adaptive threshold
            avg_char_width = np.median(char_widths) if char_widths else 10
            avg_gap = np.median(gaps)
            word_gap_threshold = max(avg_gap * 2, avg_char_width * self.word_spacing_factor)

            # Identify word boundaries
            word_boundaries = [(0, None)]

            for i, gap in enumerate(gaps):
                if gap >= word_gap_threshold:
                    word_boundaries[-1] = (word_boundaries[-1][0], i + 1)
                    word_boundaries.append((i + 1, None))

            # Close last word
            word_boundaries[-1] = (word_boundaries[-1][0], len(characters))

            return word_boundaries

        except Exception as e:
            logger.error(f"Error detecting word boundaries: {e}")
            return [(0, len(characters))]

    def _ensure_grayscale(self, image: np.ndarray) -> np.ndarray:
        """Convert image to grayscale if needed."""
        if len(image.shape) == 2:
            return image
        elif len(image.shape) == 3:
            if image.shape[2] == 3:
                return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                return image[:, :, 0]
        return image

    def _ensure_binary(self, gray: np.ndarray) -> np.ndarray:
        """Convert grayscale image to binary if needed."""
        # Check if already binary
        unique_values = np.unique(gray)
        if len(unique_values) <= 2:
            return gray

        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )

        return binary

    def refine_segmentation(
        self,
        segments: List[Segment],
        image: np.ndarray
    ) -> List[Segment]:
        """
        Refine segmentation by merging or splitting segments.

        This method handles cases where segmentation produces:
        - Oversegmented characters (e.g., 'i' split into dot and stem)
        - Undersegmented characters (e.g., connected letters)

        Args:
            segments: Initial segmentation results
            image: Original binary image

        Returns:
            Refined list of segments
        """
        if not segments or image is None:
            return segments

        try:
            refined = []
            i = 0

            while i < len(segments):
                current = segments[i]

                # Check if next segment should be merged
                if i < len(segments) - 1:
                    next_seg = segments[i + 1]

                    # Merge if very close and similar height
                    gap = next_seg.x - (current.x + current.width)
                    height_ratio = min(current.height, next_seg.height) / max(current.height, next_seg.height)

                    if gap < 5 and height_ratio > 0.7:
                        # Merge segments
                        merged = Segment(
                            x=current.x,
                            y=min(current.y, next_seg.y),
                            width=(next_seg.x + next_seg.width) - current.x,
                            height=max(current.y + current.height, next_seg.y + next_seg.height) - min(current.y, next_seg.y),
                            segment_type=current.segment_type
                        )
                        refined.append(merged)
                        i += 2
                        continue

                refined.append(current)
                i += 1

            return refined

        except Exception as e:
            logger.error(f"Error refining segmentation: {e}")
            return segments
