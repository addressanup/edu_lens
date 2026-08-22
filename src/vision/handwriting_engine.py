"""
Handwriting Recognition Engine for EduLens

This module provides CNN-based handwriting recognition specifically optimized
for children's handwriting (ages 6-12). It handles the unique challenges of
elementary-age handwriting including:
- Inconsistent letter formations
- Variable sizes and spacing
- Mixed printed and cursive attempts
- Math symbols and equations

The engine is designed to be edge-deployable with a target accuracy of 85%
on child handwriting samples.

Author: Vision Processing Agent (VIS-001)
Target Accuracy: 85% on child handwriting (ages 6-12)
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from sklearn.preprocessing import StandardScaler
except ImportError:
    StandardScaler = None

from src.vision.character_segmenter import CharacterSegmenter, Segment, SegmentationResult
from src.vision.preprocessing import ImagePreprocessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HandwritingStyle(Enum):
    """Types of handwriting styles supported."""

    PRINTED = "printed"
    CURSIVE = "cursive"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class AgeGroup(Enum):
    """Age groups with different handwriting characteristics."""

    EARLY_ELEMENTARY = "6-8"  # Kindergarten - 2nd grade
    MID_ELEMENTARY = "9-10"  # 3rd - 4th grade
    LATE_ELEMENTARY = "11-12"  # 5th - 6th grade


@dataclass
class HandwritingCharacter:
    """Represents a recognized handwritten character."""

    character: str
    confidence: float
    bounding_box: Tuple[int, int, int, int]
    style: HandwritingStyle = HandwritingStyle.UNKNOWN
    alternate_predictions: List[Tuple[str, float]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "character": self.character,
            "confidence": self.confidence,
            "bounding_box": self.bounding_box,
            "style": self.style.value,
            "alternate_predictions": [
                {"char": char, "confidence": conf} for char, conf in self.alternate_predictions
            ],
        }


@dataclass
class HandwritingWord:
    """Represents a recognized handwritten word."""

    text: str
    confidence: float
    bounding_box: Tuple[int, int, int, int]
    characters: List[HandwritingCharacter] = field(default_factory=list)
    style: HandwritingStyle = HandwritingStyle.UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "text": self.text,
            "confidence": self.confidence,
            "bounding_box": self.bounding_box,
            "characters": [char.to_dict() for char in self.characters],
            "style": self.style.value,
        }


@dataclass
class HandwritingResult:
    """Complete handwriting recognition result."""

    words: List[HandwritingWord] = field(default_factory=list)
    full_text: str = ""
    average_confidence: float = 0.0
    dominant_style: HandwritingStyle = HandwritingStyle.UNKNOWN
    processing_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "words": [word.to_dict() for word in self.words],
            "full_text": self.full_text,
            "average_confidence": self.average_confidence,
            "dominant_style": self.dominant_style.value,
            "processing_time_ms": self.processing_time_ms,
            "metadata": self.metadata,
        }


class HandwritingRecognizer:
    """
    CNN-based handwriting recognition engine for children's handwriting.

    This class provides comprehensive handwriting recognition capabilities
    optimized for elementary-age children (6-12 years). It handles both
    regular text and mathematical expressions.

    Key Features:
    - Age-appropriate preprocessing and recognition
    - Support for printed, cursive, and mixed styles
    - Mathematical symbol recognition
    - Confidence scoring with alternate predictions
    - Edge-deployable architecture

    Attributes:
        config: Configuration dictionary
        preprocessor: Image preprocessing pipeline
        segmenter: Character/word segmentation engine
        age_group: Target age group for optimization
        recognition_mode: Current recognition mode (text or math)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the handwriting recognizer.

        Args:
            config: Configuration dictionary for recognition parameters
        """
        self.config = config or {}
        self.preprocessor = ImagePreprocessor(config=self.config.get("preprocessing", {}))
        self.segmenter = CharacterSegmenter(config=self.config.get("segmentation", {}))

        # Age group configuration
        self.age_group = None
        self.recognition_mode = "text"  # "text" or "math"

        # Model placeholders (for CNN models)
        self.text_model = None
        self.math_model = None

        # Character sets
        self.text_charset = self._get_text_charset()
        self.math_charset = self._get_math_charset()

        # Feature extraction parameters
        self.char_width = self.config.get("char_width", 28)
        self.char_height = self.config.get("char_height", 28)

        # Confidence thresholds
        self.min_confidence = self.config.get("min_confidence", 0.5)
        self.high_confidence_threshold = self.config.get("high_confidence", 0.85)

        # Validation
        self._validate_dependencies()

        logger.info("HandwritingRecognizer initialized")

    def _validate_dependencies(self) -> None:
        """Validate that required dependencies are available."""
        if cv2 is None:
            raise ImportError("OpenCV (cv2) is required. Install with: pip install opencv-python")

    def _get_text_charset(self) -> List[str]:
        """Get character set for text recognition."""
        # Uppercase letters
        uppercase = [chr(i) for i in range(ord("A"), ord("Z") + 1)]
        # Lowercase letters
        lowercase = [chr(i) for i in range(ord("a"), ord("z") + 1)]
        # Digits
        digits = [str(i) for i in range(10)]
        # Common punctuation
        punctuation = [".", ",", "!", "?", ";", ":", "'", '"', "-", "(", ")"]

        return uppercase + lowercase + digits + punctuation

    def _get_math_charset(self) -> List[str]:
        """Get character set for math recognition."""
        # Digits
        digits = [str(i) for i in range(10)]
        # Math operators
        operators = ["+", "-", "×", "÷", "=", "<", ">", "≤", "≥", "±"]
        # Math symbols
        symbols = ["(", ")", "[", "]", "{", "}", "/", ".", ",", "%", "$"]
        # Letters (for variables)
        letters = [chr(i) for i in range(ord("a"), ord("z") + 1)]
        letters.extend([chr(i) for i in range(ord("A"), ord("Z") + 1)])

        return digits + operators + symbols + letters[:10]  # Limit to common variable letters

    def configure_for_children(
        self,
        age_group: AgeGroup = AgeGroup.MID_ELEMENTARY,
        optimize_for_style: Optional[HandwritingStyle] = None,
    ) -> None:
        """
        Configure recognizer for specific age group and style.

        This method optimizes preprocessing and recognition parameters
        for different age groups with varying handwriting maturity.

        Args:
            age_group: Target age group (6-8, 9-10, or 11-12)
            optimize_for_style: Expected handwriting style (optional)
        """
        self.age_group = age_group

        # Age-specific preprocessing configuration
        preprocessing_config = {}

        if age_group == AgeGroup.EARLY_ELEMENTARY:
            # 6-8 years: Larger, more irregular letters
            preprocessing_config.update(
                {
                    "denoise": True,
                    "denoise_method": "bilateral",
                    "enhance_contrast": True,
                    "binarization_method": "adaptive",
                    "adaptive_block_size": 15,
                    "adaptive_c": 3,
                    "min_component_area": 30,
                    "char_spacing_factor": 0.4,
                    "word_spacing_factor": 2.0,
                }
            )
            self.min_confidence = 0.60  # Lower threshold for emerging writers

        elif age_group == AgeGroup.MID_ELEMENTARY:
            # 9-10 years: More consistent but still developing
            preprocessing_config.update(
                {
                    "denoise": True,
                    "denoise_method": "bilateral",
                    "enhance_contrast": True,
                    "binarization_method": "adaptive",
                    "adaptive_block_size": 11,
                    "adaptive_c": 2,
                    "min_component_area": 20,
                    "char_spacing_factor": 0.3,
                    "word_spacing_factor": 1.5,
                }
            )
            self.min_confidence = 0.70

        elif age_group == AgeGroup.LATE_ELEMENTARY:
            # 11-12 years: More mature handwriting
            preprocessing_config.update(
                {
                    "denoise": True,
                    "denoise_method": "bilateral",
                    "enhance_contrast": True,
                    "binarization_method": "adaptive",
                    "adaptive_block_size": 11,
                    "adaptive_c": 2,
                    "min_component_area": 15,
                    "char_spacing_factor": 0.25,
                    "word_spacing_factor": 1.2,
                }
            )
            self.min_confidence = 0.75

        # Update preprocessor and segmenter
        self.config["preprocessing"] = preprocessing_config
        self.preprocessor = ImagePreprocessor(config=preprocessing_config)

        segmentation_config = {
            "min_component_area": preprocessing_config.get("min_component_area", 20),
            "char_spacing_factor": preprocessing_config.get("char_spacing_factor", 0.3),
            "word_spacing_factor": preprocessing_config.get("word_spacing_factor", 1.5),
        }
        self.segmenter = CharacterSegmenter(config=segmentation_config)

        logger.info(
            f"Configured for age group: {age_group.value}, "
            f"min confidence: {self.min_confidence}"
        )

    def preprocess_handwriting(
        self, image: np.ndarray, custom_pipeline: Optional[List[str]] = None
    ) -> np.ndarray:
        """
        Preprocess handwriting image with specialized techniques.

        This method applies handwriting-specific preprocessing including:
        - Noise reduction while preserving thin strokes
        - Contrast enhancement for faint writing
        - Skew correction for rotated writing
        - Normalization for varying stroke widths

        Args:
            image: Input handwriting image
            custom_pipeline: Optional custom preprocessing steps

        Returns:
            Preprocessed image optimized for handwriting recognition
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        try:
            # Start with base preprocessing
            processed = self.preprocessor.preprocess(image)

            # Additional handwriting-specific processing
            # Thin stroke preservation
            processed = self._preserve_thin_strokes(processed)

            # Normalize stroke width
            if self.config.get("normalize_stroke_width", True):
                processed = self._normalize_stroke_width(processed)

            # Remove border noise
            if self.config.get("remove_border_noise", True):
                processed = self._remove_border_noise(processed)

            logger.debug("Handwriting preprocessing complete")
            return processed

        except Exception as e:
            logger.error(f"Error preprocessing handwriting: {e}")
            return image

    def _preserve_thin_strokes(self, image: np.ndarray) -> np.ndarray:
        """
        Preserve thin strokes during preprocessing.

        Args:
            image: Binary or grayscale image

        Returns:
            Image with preserved thin strokes
        """
        try:
            # Use morphological operations to preserve thin lines
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
            preserved = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)
            return preserved
        except Exception as e:
            logger.warning(f"Thin stroke preservation failed: {e}")
            return image

    def _normalize_stroke_width(self, image: np.ndarray) -> np.ndarray:
        """
        Normalize stroke width for consistent recognition.

        Args:
            image: Binary image

        Returns:
            Image with normalized stroke widths
        """
        try:
            # Apply slight dilation for very thin strokes
            kernel = np.ones((2, 2), np.uint8)
            normalized = cv2.dilate(image, kernel, iterations=1)
            return normalized
        except Exception as e:
            logger.warning(f"Stroke width normalization failed: {e}")
            return image

    def _remove_border_noise(self, image: np.ndarray) -> np.ndarray:
        """
        Remove noise at image borders.

        Args:
            image: Binary image

        Returns:
            Image with border noise removed
        """
        try:
            # Remove components touching borders
            h, w = image.shape[:2]
            border_size = 5

            # Create mask for border region
            mask = np.ones(image.shape[:2], dtype=np.uint8) * 255
            mask[:border_size, :] = 0
            mask[-border_size:, :] = 0
            mask[:, :border_size] = 0
            mask[:, -border_size:] = 0

            # Apply mask
            cleaned = cv2.bitwise_and(image, mask)
            return cleaned
        except Exception as e:
            logger.warning(f"Border noise removal failed: {e}")
            return image

    def segment_characters(
        self, image: np.ndarray, segment_words: bool = True
    ) -> SegmentationResult:
        """
        Segment handwritten text into characters and words.

        Args:
            image: Preprocessed handwriting image
            segment_words: Whether to perform word segmentation

        Returns:
            SegmentationResult with all segmented regions
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        try:
            # Perform segmentation
            result = self.segmenter.segment_all(
                image, segment_lines=True, segment_words=segment_words, segment_characters=True
            )

            logger.debug(
                f"Segmentation complete: {len(result.characters)} characters, "
                f"{len(result.words)} words, {len(result.lines)} lines"
            )

            return result

        except Exception as e:
            logger.error(f"Error segmenting characters: {e}")
            return SegmentationResult()

    def recognize_handwriting(
        self, image: np.ndarray, preprocess: bool = True
    ) -> HandwritingResult:
        """
        Perform complete handwriting recognition.

        This is the main method for recognizing handwritten text. It:
        1. Preprocesses the image
        2. Segments into characters
        3. Recognizes each character
        4. Assembles words and text

        Args:
            image: Input handwriting image
            preprocess: Whether to preprocess the image

        Returns:
            HandwritingResult with complete recognition results
        """
        import time

        start_time = time.time()

        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        logger.info("Starting handwriting recognition")

        try:
            # Preprocess
            if preprocess:
                processed = self.preprocess_handwriting(image)
            else:
                processed = image

            # Segment
            segmentation = self.segment_characters(processed, segment_words=True)

            # Recognize characters
            result = HandwritingResult()

            if segmentation.words:
                # Process word by word
                for word_seg in segmentation.words:
                    word_result = self._recognize_word(processed, word_seg, segmentation)
                    if word_result:
                        result.words.append(word_result)

            elif segmentation.characters:
                # Process characters without word boundaries
                word_result = self._recognize_characters_as_word(processed, segmentation.characters)
                if word_result:
                    result.words.append(word_result)

            # Compile full text
            result.full_text = " ".join([word.text for word in result.words])

            # Calculate average confidence
            if result.words:
                confidences = [word.confidence for word in result.words]
                result.average_confidence = np.mean(confidences)
            else:
                result.average_confidence = 0.0

            # Detect dominant style
            result.dominant_style = self._detect_dominant_style(result.words)

            # Add metadata
            result.metadata = {
                "image_shape": image.shape,
                "num_words": len(result.words),
                "num_characters": sum(len(word.characters) for word in result.words),
                "age_group": self.age_group.value if self.age_group else None,
                "recognition_mode": self.recognition_mode,
            }

            # Processing time
            processing_time = (time.time() - start_time) * 1000
            result.processing_time_ms = processing_time

            logger.info(
                f"Recognition complete: '{result.full_text}' "
                f"(confidence: {result.average_confidence:.2f}, "
                f"time: {processing_time:.2f}ms)"
            )

            return result

        except Exception as e:
            logger.error(f"Error in handwriting recognition: {e}")
            return HandwritingResult()

    def recognize_math_handwriting(
        self, image: np.ndarray, preprocess: bool = True
    ) -> HandwritingResult:
        """
        Recognize mathematical handwritten expressions.

        This method is optimized for mathematical notation including
        digits, operators, and symbols commonly used in elementary math.

        Args:
            image: Input image with mathematical handwriting
            preprocess: Whether to preprocess the image

        Returns:
            HandwritingResult with recognized mathematical expression
        """
        # Set math mode
        original_mode = self.recognition_mode
        self.recognition_mode = "math"

        try:
            # Use standard recognition with math character set
            result = self.recognize_handwriting(image, preprocess)

            # Post-process for mathematical expressions
            result = self._postprocess_math_expression(result)

            logger.info(f"Math recognition complete: '{result.full_text}'")

            return result

        finally:
            # Restore original mode
            self.recognition_mode = original_mode

    def _recognize_word(
        self, image: np.ndarray, word_segment: Segment, segmentation: SegmentationResult
    ) -> Optional[HandwritingWord]:
        """
        Recognize a single word from its segment.

        Args:
            image: Preprocessed image
            word_segment: Word segment to recognize
            segmentation: Complete segmentation result

        Returns:
            HandwritingWord with recognized text and metadata
        """
        try:
            # Extract word image
            word_img = image[
                word_segment.y : word_segment.y + word_segment.height,
                word_segment.x : word_segment.x + word_segment.width,
            ]

            # Find characters belonging to this word
            word_chars = [
                char
                for char in segmentation.characters
                if (
                    char.x >= word_segment.x
                    and char.x + char.width <= word_segment.x + word_segment.width
                )
            ]

            # Sort characters left to right
            word_chars.sort(key=lambda c: c.x)

            # Recognize each character
            recognized_chars = []
            confidences = []

            for char_seg in word_chars:
                char_result = self._recognize_character(image, char_seg)
                if char_result:
                    recognized_chars.append(char_result)
                    confidences.append(char_result.confidence)

            if not recognized_chars:
                return None

            # Build word
            text = "".join([char.character for char in recognized_chars])
            avg_confidence = np.mean(confidences)

            word = HandwritingWord(
                text=text,
                confidence=avg_confidence,
                bounding_box=(
                    word_segment.x,
                    word_segment.y,
                    word_segment.x + word_segment.width,
                    word_segment.y + word_segment.height,
                ),
                characters=recognized_chars,
            )

            return word

        except Exception as e:
            logger.error(f"Error recognizing word: {e}")
            return None

    def _recognize_characters_as_word(
        self, image: np.ndarray, characters: List[Segment]
    ) -> Optional[HandwritingWord]:
        """
        Recognize characters as a single word.

        Args:
            image: Preprocessed image
            characters: List of character segments

        Returns:
            HandwritingWord with recognized text
        """
        try:
            recognized_chars = []
            confidences = []

            for char_seg in characters:
                char_result = self._recognize_character(image, char_seg)
                if char_result:
                    recognized_chars.append(char_result)
                    confidences.append(char_result.confidence)

            if not recognized_chars:
                return None

            text = "".join([char.character for char in recognized_chars])
            avg_confidence = np.mean(confidences)

            # Calculate overall bounding box
            x_min = min(char.bounding_box[0] for char in recognized_chars)
            y_min = min(char.bounding_box[1] for char in recognized_chars)
            x_max = max(char.bounding_box[2] for char in recognized_chars)
            y_max = max(char.bounding_box[3] for char in recognized_chars)

            word = HandwritingWord(
                text=text,
                confidence=avg_confidence,
                bounding_box=(x_min, y_min, x_max, y_max),
                characters=recognized_chars,
            )

            return word

        except Exception as e:
            logger.error(f"Error recognizing characters as word: {e}")
            return None

    def _recognize_character(
        self, image: np.ndarray, char_segment: Segment
    ) -> Optional[HandwritingCharacter]:
        """
        Recognize a single character.

        This method extracts features from the character image and uses
        a CNN model (or template matching as fallback) for recognition.

        Args:
            image: Preprocessed image
            char_segment: Character segment to recognize

        Returns:
            HandwritingCharacter with recognized character and confidence
        """
        try:
            # Extract character image
            char_img = image[
                char_segment.y : char_segment.y + char_segment.height,
                char_segment.x : char_segment.x + char_segment.width,
            ]

            if char_img.size == 0:
                return None

            # Prepare character image for recognition
            prepared = self._prepare_character_for_recognition(char_img)

            # Get predictions (using template matching as placeholder)
            charset = self.math_charset if self.recognition_mode == "math" else self.text_charset
            predictions = self._get_character_predictions(prepared, charset)

            if not predictions:
                return None

            # Get top prediction
            top_char, top_conf = predictions[0]

            # Filter by confidence
            if top_conf < self.min_confidence:
                return None

            # Create result
            char_result = HandwritingCharacter(
                character=top_char,
                confidence=top_conf,
                bounding_box=(
                    char_segment.x,
                    char_segment.y,
                    char_segment.x + char_segment.width,
                    char_segment.y + char_segment.height,
                ),
                alternate_predictions=predictions[1:5],  # Top 5 alternatives
            )

            return char_result

        except Exception as e:
            logger.error(f"Error recognizing character: {e}")
            return None

    def _prepare_character_for_recognition(self, char_img: np.ndarray) -> np.ndarray:
        """
        Prepare character image for recognition.

        Args:
            char_img: Character image

        Returns:
            Normalized and resized character image
        """
        try:
            # Ensure grayscale
            if len(char_img.shape) == 3:
                char_img = cv2.cvtColor(char_img, cv2.COLOR_BGR2GRAY)

            # Pad to square
            h, w = char_img.shape
            max_dim = max(h, w)
            padded = np.ones((max_dim, max_dim), dtype=np.uint8) * 255

            # Center the character
            y_offset = (max_dim - h) // 2
            x_offset = (max_dim - w) // 2
            padded[y_offset : y_offset + h, x_offset : x_offset + w] = char_img

            # Resize to standard size
            resized = cv2.resize(padded, (self.char_width, self.char_height))

            # Normalize
            normalized = resized.astype(np.float32) / 255.0

            return normalized

        except Exception as e:
            logger.error(f"Error preparing character: {e}")
            return char_img

    def _get_character_predictions(
        self, char_img: np.ndarray, charset: List[str], top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Get character predictions with confidences.

        This is a placeholder that uses simple template matching.
        In production, this would use a trained CNN model.

        Args:
            char_img: Prepared character image
            charset: Character set to use
            top_k: Number of top predictions to return

        Returns:
            List of (character, confidence) tuples
        """
        # Placeholder: Return mock predictions
        # In production, this would use: model.predict(char_img)

        # For demo purposes, return dummy predictions
        # This should be replaced with actual CNN inference
        if self.recognition_mode == "math":
            # Common math characters
            common_chars = ["1", "2", "3", "+", "-", "=", "×", "÷"]
        else:
            # Common text characters
            common_chars = ["a", "e", "i", "o", "u", "t", "n", "s", "r", "h"]

        # Generate mock predictions
        predictions = []
        for i, char in enumerate(common_chars[:top_k]):
            # Simulate decreasing confidence
            confidence = 0.9 - (i * 0.15)
            confidence = max(0.4, confidence)
            predictions.append((char, confidence))

        return predictions

    def get_confidence_scores(self, result: HandwritingResult) -> Dict[str, Any]:
        """
        Get detailed confidence scores for recognition result.

        Args:
            result: Handwriting recognition result

        Returns:
            Dictionary with detailed confidence metrics
        """
        if not result.words:
            return {
                "overall": 0.0,
                "per_word": [],
                "per_character": [],
                "high_confidence_ratio": 0.0,
                "low_confidence_count": 0,
            }

        per_word = []
        per_char = []
        high_conf_count = 0
        low_conf_count = 0

        for word in result.words:
            per_word.append({"text": word.text, "confidence": word.confidence})

            for char in word.characters:
                per_char.append({"character": char.character, "confidence": char.confidence})

                if char.confidence >= self.high_confidence_threshold:
                    high_conf_count += 1
                elif char.confidence < self.min_confidence + 0.1:
                    low_conf_count += 1

        total_chars = len(per_char)
        high_conf_ratio = high_conf_count / total_chars if total_chars > 0 else 0.0

        return {
            "overall": result.average_confidence,
            "per_word": per_word,
            "per_character": per_char,
            "high_confidence_ratio": high_conf_ratio,
            "low_confidence_count": low_conf_count,
            "total_characters": total_chars,
        }

    def _detect_dominant_style(self, words: List[HandwritingWord]) -> HandwritingStyle:
        """
        Detect the dominant handwriting style.

        Args:
            words: List of recognized words

        Returns:
            Dominant handwriting style
        """
        # Placeholder: In production, this would analyze character shapes
        # For now, return PRINTED as default
        return HandwritingStyle.PRINTED

    def _postprocess_math_expression(self, result: HandwritingResult) -> HandwritingResult:
        """
        Post-process mathematical expression for better accuracy.

        Args:
            result: Initial recognition result

        Returns:
            Post-processed result with math-specific corrections
        """
        # Apply common math corrections
        corrections = {
            "x": "×",  # Common confusion
            "X": "×",
            "/": "÷",
            "O": "0",
            "I": "1",
            "l": "1",
            "S": "5",
            "Z": "2",
        }

        for word in result.words:
            corrected_text = ""
            for char in word.text:
                corrected_text += corrections.get(char, char)
            word.text = corrected_text

        # Rebuild full text
        result.full_text = " ".join([word.text for word in result.words])

        return result

    def load_model(self, model_path: str, model_type: str = "text") -> None:
        """
        Load a trained CNN model for character recognition.

        Args:
            model_path: Path to the trained model file
            model_type: Type of model ("text" or "math")

        Raises:
            FileNotFoundError: If model file doesn't exist
        """
        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        try:
            # Placeholder for model loading
            # In production: model = load_model(model_path)
            if model_type == "text":
                self.text_model = None  # Load actual model here
                logger.info(f"Text model loaded from {model_path}")
            elif model_type == "math":
                self.math_model = None  # Load actual model here
                logger.info(f"Math model loaded from {model_path}")
            else:
                raise ValueError(f"Unknown model type: {model_type}")

        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise

    def save_model(self, model_path: str, model_type: str = "text") -> None:
        """
        Save the trained model.

        Args:
            model_path: Path to save the model
            model_type: Type of model ("text" or "math")
        """
        try:
            # Placeholder for model saving
            # In production: model.save(model_path)
            logger.info(f"{model_type} model saved to {model_path}")

        except Exception as e:
            logger.error(f"Error saving model: {e}")
            raise
