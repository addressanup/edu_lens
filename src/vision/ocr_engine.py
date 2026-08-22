"""
OCR Engine for EduLens - Optimized for Elementary Educational Materials

This module provides the core OCR functionality for processing printed educational
materials such as textbooks, worksheets, and workbooks. It's designed to be
edge-deployable and optimized for elementary-level content (ages 6-12).

Author: Vision Processing Agent (VIS-001)
Target Accuracy: 95% on printed text
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

from src.vision.preprocessing import ImagePreprocessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Types of educational documents supported."""

    WORKSHEET = "worksheet"
    TEXTBOOK = "textbook"
    HANDOUT = "handout"
    WORKBOOK = "workbook"
    FLASHCARD = "flashcard"


class OCRBackend(Enum):
    """Supported OCR backend engines."""

    TESSERACT = "tesseract"
    EASYOCR = "easyocr"
    PADDLEOCR = "paddleocr"


@dataclass
class BoundingBox:
    """Represents a bounding box for detected text region."""

    x: int
    y: int
    width: int
    height: int

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary representation."""
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}

    def to_coordinates(self) -> Tuple[int, int, int, int]:
        """Convert to (x1, y1, x2, y2) coordinates."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)


@dataclass
class TextRegion:
    """Represents a detected text region with recognition results."""

    text: str
    confidence: float
    bounding_box: BoundingBox
    language: str = "en"
    font_size: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "text": self.text,
            "confidence": self.confidence,
            "bounding_box": self.bounding_box.to_dict(),
            "language": self.language,
            "font_size": self.font_size,
        }


@dataclass
class OCRResult:
    """Complete OCR result for a document."""

    regions: List[TextRegion] = field(default_factory=list)
    full_text: str = ""
    average_confidence: float = 0.0
    document_type: Optional[DocumentType] = None
    processing_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "regions": [region.to_dict() for region in self.regions],
            "full_text": self.full_text,
            "average_confidence": self.average_confidence,
            "document_type": self.document_type.value if self.document_type else None,
            "processing_time_ms": self.processing_time_ms,
            "metadata": self.metadata,
        }


class BaseOCREngine(ABC):
    """Abstract base class for OCR engine implementations."""

    @abstractmethod
    def preprocess_image(self, image: np.ndarray, **kwargs) -> np.ndarray:
        """Preprocess image for OCR."""
        pass

    @abstractmethod
    def detect_text_regions(self, image: np.ndarray) -> List[BoundingBox]:
        """Detect text regions in the image."""
        pass

    @abstractmethod
    def recognize_text(self, image: np.ndarray, region: Optional[BoundingBox] = None) -> TextRegion:
        """Perform OCR on image or specific region."""
        pass

    @abstractmethod
    def extract_structured_content(self, image: np.ndarray) -> OCRResult:
        """Extract structured content with bounding boxes."""
        pass


class OCREngine(BaseOCREngine):
    """
    Main OCR engine optimized for elementary educational materials.

    This implementation uses Tesseract OCR as the default backend with
    optimizations for educational content including:
    - Enhanced preprocessing for printed materials
    - Educational font recognition
    - Layout analysis for structured content
    - Confidence scoring for quality assurance

    Attributes:
        backend: OCR backend engine to use
        config: Configuration dictionary
        preprocessor: Image preprocessing utility
        education_mode: Whether educational optimizations are enabled
    """

    def __init__(
        self, backend: OCRBackend = OCRBackend.TESSERACT, config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the OCR engine.

        Args:
            backend: OCR backend to use (default: Tesseract)
            config: Configuration dictionary for OCR parameters
        """
        self.backend = backend
        self.config = config or {}
        self.preprocessor = ImagePreprocessor(config=self.config.get("preprocessing", {}))
        self.education_mode = False
        self._tesseract_config = self._build_tesseract_config()

        # Validate dependencies
        self._validate_dependencies()

        logger.info(f"OCR Engine initialized with backend: {backend.value}")

    def _validate_dependencies(self) -> None:
        """Validate that required dependencies are available."""
        if cv2 is None:
            raise ImportError("OpenCV (cv2) is required. Install with: pip install opencv-python")

        if self.backend == OCRBackend.TESSERACT and pytesseract is None:
            raise ImportError("pytesseract is required. Install with: pip install pytesseract")

    def _build_tesseract_config(self) -> str:
        """Build Tesseract configuration string."""
        # PSM (Page Segmentation Mode) options:
        # 3 = Fully automatic page segmentation (default)
        # 6 = Assume a single uniform block of text
        # 11 = Sparse text. Find as much text as possible in no particular order
        psm = self.config.get("tesseract_psm", 3)

        # OEM (OCR Engine Mode) options:
        # 3 = Default, based on what is available (recommended)
        # 1 = Neural nets LSTM engine only
        oem = self.config.get("tesseract_oem", 3)

        config = f"--psm {psm} --oem {oem}"

        # Add character whitelist for educational content if enabled
        if self.education_mode:
            # Include alphanumeric, common punctuation, and math symbols
            whitelist = (
                "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,!?;:'\"-+=×÷<>()[]"
            )
            config += f" -c tessedit_char_whitelist={whitelist}"

        return config

    def configure_for_education(
        self,
        document_type: DocumentType = DocumentType.TEXTBOOK,
        enable_math_symbols: bool = True,
        enable_layout_analysis: bool = True,
    ) -> None:
        """
        Configure OCR engine for educational materials.

        This method optimizes the OCR engine for elementary educational content
        by adjusting preprocessing parameters, character recognition, and layout
        analysis settings.

        Args:
            document_type: Type of educational document
            enable_math_symbols: Whether to recognize mathematical symbols
            enable_layout_analysis: Whether to perform layout analysis
        """
        self.education_mode = True
        self.config["document_type"] = document_type
        self.config["math_symbols"] = enable_math_symbols
        self.config["layout_analysis"] = enable_layout_analysis

        # Update preprocessing configuration for educational materials
        preprocessing_config = {
            "deskew": True,
            "denoise": True,
            "enhance_contrast": True,
            "binarization_method": "adaptive",  # Better for varied lighting
            "adaptive_block_size": 11,  # Optimized for typical educational fonts
            "adaptive_c": 2,
        }

        # Document-specific optimizations
        if document_type == DocumentType.WORKSHEET:
            preprocessing_config["remove_lines"] = True  # Remove grid lines
            preprocessing_config["adaptive_block_size"] = 15
        elif document_type == DocumentType.TEXTBOOK:
            preprocessing_config["enhance_contrast"] = True
            preprocessing_config["sharpen"] = True
        elif document_type == DocumentType.FLASHCARD:
            preprocessing_config["resize_scale"] = 2.0  # Upscale for better recognition

        self.config["preprocessing"] = preprocessing_config
        self.preprocessor = ImagePreprocessor(config=preprocessing_config)

        # Rebuild Tesseract config
        self._tesseract_config = self._build_tesseract_config()

        logger.info(f"Configured for educational mode: {document_type.value}")

    def preprocess_image(
        self, image: np.ndarray, custom_pipeline: Optional[List[str]] = None
    ) -> np.ndarray:
        """
        Preprocess image for optimal OCR performance.

        Applies a series of image preprocessing operations including:
        - Deskewing to correct rotation
        - Noise reduction
        - Contrast enhancement
        - Binarization

        Args:
            image: Input image as numpy array (BGR or RGB format)
            custom_pipeline: Optional list of specific preprocessing steps

        Returns:
            Preprocessed image as numpy array

        Raises:
            ValueError: If image is invalid or empty
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        logger.debug(f"Preprocessing image of shape: {image.shape}")

        # Use custom pipeline if provided, otherwise use full preprocessing
        if custom_pipeline:
            processed = image.copy()
            for step in custom_pipeline:
                if step == "deskew":
                    processed = self.preprocessor.deskew(processed)
                elif step == "denoise":
                    processed = self.preprocessor.denoise(processed)
                elif step == "enhance_contrast":
                    processed = self.preprocessor.enhance_contrast(processed)
                elif step == "binarize":
                    processed = self.preprocessor.binarize(processed)
                elif step == "sharpen":
                    processed = self.preprocessor.sharpen(processed)
        else:
            processed = self.preprocessor.preprocess(image)

        return processed

    def detect_text_regions(
        self, image: np.ndarray, min_confidence: float = 0.5
    ) -> List[BoundingBox]:
        """
        Detect text regions in the image.

        Uses OCR engine's built-in text detection to identify regions
        containing text with associated confidence scores.

        Args:
            image: Preprocessed image as numpy array
            min_confidence: Minimum confidence threshold for detection

        Returns:
            List of bounding boxes for detected text regions
        """
        if self.backend == OCRBackend.TESSERACT:
            return self._detect_text_regions_tesseract(image, min_confidence)
        else:
            raise NotImplementedError(f"Text detection not implemented for {self.backend.value}")

    def _detect_text_regions_tesseract(
        self, image: np.ndarray, min_confidence: float
    ) -> List[BoundingBox]:
        """Detect text regions using Tesseract."""
        try:
            # Get detailed detection data
            data = pytesseract.image_to_data(
                image, config=self._tesseract_config, output_type=pytesseract.Output.DICT
            )

            regions = []
            n_boxes = len(data["text"])

            for i in range(n_boxes):
                # Filter by confidence
                conf = float(data["conf"][i])
                if conf < min_confidence * 100:  # Tesseract uses 0-100 scale
                    continue

                # Filter empty text
                text = data["text"][i].strip()
                if not text:
                    continue

                # Create bounding box
                x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                bbox = BoundingBox(x=x, y=y, width=w, height=h)
                regions.append(bbox)

            logger.debug(f"Detected {len(regions)} text regions")
            return regions

        except Exception as e:
            logger.error(f"Error detecting text regions: {e}")
            return []

    def recognize_text(self, image: np.ndarray, region: Optional[BoundingBox] = None) -> TextRegion:
        """
        Perform OCR on image or specific region.

        Args:
            image: Input image as numpy array
            region: Optional bounding box to restrict OCR to specific region

        Returns:
            TextRegion object with recognized text and metadata
        """
        if self.backend == OCRBackend.TESSERACT:
            return self._recognize_text_tesseract(image, region)
        else:
            raise NotImplementedError(f"Text recognition not implemented for {self.backend.value}")

    def _recognize_text_tesseract(
        self, image: np.ndarray, region: Optional[BoundingBox]
    ) -> TextRegion:
        """Recognize text using Tesseract."""
        try:
            # Extract region if specified
            if region:
                x1, y1, x2, y2 = region.to_coordinates()
                roi = image[y1:y2, x1:x2]
            else:
                roi = image
                region = BoundingBox(0, 0, image.shape[1], image.shape[0])

            # Perform OCR
            text = pytesseract.image_to_string(roi, config=self._tesseract_config).strip()

            # Get confidence
            data = pytesseract.image_to_data(
                roi, config=self._tesseract_config, output_type=pytesseract.Output.DICT
            )

            # Calculate average confidence
            confidences = [float(c) for c in data["conf"] if c != "-1"]
            avg_confidence = np.mean(confidences) / 100.0 if confidences else 0.0

            return TextRegion(
                text=text, confidence=avg_confidence, bounding_box=region, language="en"
            )

        except Exception as e:
            logger.error(f"Error recognizing text: {e}")
            return TextRegion(
                text="",
                confidence=0.0,
                bounding_box=region or BoundingBox(0, 0, 0, 0),
                language="en",
            )

    def extract_structured_content(
        self, image: np.ndarray, preprocess: bool = True, min_confidence: float = 0.6
    ) -> OCRResult:
        """
        Extract structured content with bounding boxes and confidence scores.

        This is the main method for comprehensive OCR processing. It:
        1. Preprocesses the image (optional)
        2. Detects all text regions
        3. Recognizes text in each region
        4. Compiles structured results with metadata

        Args:
            image: Input image as numpy array
            preprocess: Whether to preprocess the image
            min_confidence: Minimum confidence threshold for including results

        Returns:
            OCRResult object with complete structured content

        Raises:
            ValueError: If image is invalid
        """
        import time

        start_time = time.time()

        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        logger.info("Starting structured content extraction")

        # Preprocess image
        if preprocess:
            processed_image = self.preprocess_image(image)
        else:
            processed_image = image

        # Perform OCR with detailed data
        if self.backend == OCRBackend.TESSERACT:
            result = self._extract_structured_tesseract(processed_image, min_confidence)
        else:
            raise NotImplementedError(
                f"Structured extraction not implemented for {self.backend.value}"
            )

        # Add processing time
        processing_time = (time.time() - start_time) * 1000
        result.processing_time_ms = processing_time

        # Add document type if configured
        if "document_type" in self.config:
            result.document_type = self.config["document_type"]

        # Add metadata
        result.metadata = {
            "image_shape": image.shape,
            "backend": self.backend.value,
            "education_mode": self.education_mode,
            "num_regions": len(result.regions),
        }

        logger.info(
            f"Extraction complete: {len(result.regions)} regions, "
            f"avg confidence: {result.average_confidence:.2f}, "
            f"time: {processing_time:.2f}ms"
        )

        return result

    def _extract_structured_tesseract(self, image: np.ndarray, min_confidence: float) -> OCRResult:
        """Extract structured content using Tesseract."""
        try:
            # Get detailed OCR data
            data = pytesseract.image_to_data(
                image, config=self._tesseract_config, output_type=pytesseract.Output.DICT
            )

            regions = []
            full_text_parts = []
            confidences = []

            n_boxes = len(data["text"])

            for i in range(n_boxes):
                # Get confidence
                conf = float(data["conf"][i])
                if conf < 0:  # Invalid confidence
                    continue

                # Normalize confidence to 0-1 range
                normalized_conf = conf / 100.0

                # Filter by confidence threshold
                if normalized_conf < min_confidence:
                    continue

                # Get text
                text = data["text"][i].strip()
                if not text:
                    continue

                # Create bounding box
                x = data["left"][i]
                y = data["top"][i]
                w = data["width"][i]
                h = data["height"][i]
                bbox = BoundingBox(x=x, y=y, width=w, height=h)

                # Create text region
                region = TextRegion(
                    text=text, confidence=normalized_conf, bounding_box=bbox, language="en"
                )

                regions.append(region)
                full_text_parts.append(text)
                confidences.append(normalized_conf)

            # Compile full text
            full_text = " ".join(full_text_parts)

            # Calculate average confidence
            avg_confidence = np.mean(confidences) if confidences else 0.0

            return OCRResult(
                regions=regions, full_text=full_text, average_confidence=float(avg_confidence)
            )

        except Exception as e:
            logger.error(f"Error extracting structured content: {e}")
            return OCRResult(regions=[], full_text="", average_confidence=0.0)

    def process_document(self, image_path: str, output_format: str = "dict") -> Dict[str, Any]:
        """
        Process a complete document from file path.

        Convenience method for processing a document from a file path.

        Args:
            image_path: Path to image file
            output_format: Output format ("dict" or "json")

        Returns:
            Dictionary or JSON string with OCR results

        Raises:
            FileNotFoundError: If image file doesn't exist
            ValueError: If image cannot be loaded
        """
        import json

        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # Load image
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")

        logger.info(f"Processing document: {image_path}")

        # Extract content
        result = self.extract_structured_content(image)

        # Convert to requested format
        result_dict = result.to_dict()

        if output_format == "json":
            return json.dumps(result_dict, indent=2)
        else:
            return result_dict
