"""
Unit tests for OCR Engine (Vision Processing).

Tests OCR functionality including:
- Text extraction accuracy
- Different image qualities
- Various text formats
- Error handling
- Document type detection
- Educational content processing

Author: Testing Agent (TST-001)
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest
from PIL import Image

from src.vision.ocr_engine import (
    BoundingBox,
    DocumentType,
    OCRBackend,
    OCREngine,
    OCRResult,
    TextRegion,
)
from src.vision.preprocessing import ImagePreprocessor


class TestBoundingBox:
    """Test BoundingBox data class."""

    def test_bounding_box_creation(self):
        """Test creating a bounding box."""
        bbox = BoundingBox(x=10, y=20, width=100, height=50)

        assert bbox.x == 10
        assert bbox.y == 20
        assert bbox.width == 100
        assert bbox.height == 50

    def test_to_dict(self):
        """Test converting bounding box to dictionary."""
        bbox = BoundingBox(x=10, y=20, width=100, height=50)
        bbox_dict = bbox.to_dict()

        assert bbox_dict == {"x": 10, "y": 20, "width": 100, "height": 50}

    def test_to_coordinates(self):
        """Test converting to coordinates format."""
        bbox = BoundingBox(x=10, y=20, width=100, height=50)
        coords = bbox.to_coordinates()

        assert coords == (10, 20, 110, 70)


class TestTextRegion:
    """Test TextRegion data class."""

    def test_text_region_creation(self):
        """Test creating a text region."""
        bbox = BoundingBox(x=10, y=20, width=100, height=50)
        region = TextRegion(text="Hello World", confidence=0.95, bounding_box=bbox, language="en")

        assert region.text == "Hello World"
        assert region.confidence == 0.95
        assert region.language == "en"

    def test_to_dict(self):
        """Test converting text region to dictionary."""
        bbox = BoundingBox(x=10, y=20, width=100, height=50)
        region = TextRegion(text="Test", confidence=0.9, bounding_box=bbox)

        region_dict = region.to_dict()
        assert region_dict["text"] == "Test"
        assert region_dict["confidence"] == 0.9
        assert "bounding_box" in region_dict


class TestOCRResult:
    """Test OCRResult data class."""

    def test_ocr_result_empty(self):
        """Test empty OCR result."""
        result = OCRResult()

        assert len(result.regions) == 0
        assert result.full_text == ""
        assert result.average_confidence == 0.0

    def test_ocr_result_with_data(self):
        """Test OCR result with data."""
        bbox = BoundingBox(x=10, y=20, width=100, height=50)
        region = TextRegion(text="Test", confidence=0.9, bounding_box=bbox)

        result = OCRResult(
            regions=[region],
            full_text="Test",
            average_confidence=0.9,
            document_type=DocumentType.TEXTBOOK,
        )

        assert len(result.regions) == 1
        assert result.full_text == "Test"
        assert result.average_confidence == 0.9
        assert result.document_type == DocumentType.TEXTBOOK

    def test_to_dict(self):
        """Test converting OCR result to dictionary."""
        result = OCRResult(full_text="Test", average_confidence=0.9)

        result_dict = result.to_dict()
        assert "full_text" in result_dict
        assert "average_confidence" in result_dict
        assert "regions" in result_dict


class TestOCREngine:
    """Test main OCR engine functionality."""

    @pytest.fixture
    def sample_image(self):
        """Create a sample test image."""
        # Create a white image with some text-like patterns
        img = np.ones((200, 400, 3), dtype=np.uint8) * 255
        # Add some dark regions to simulate text
        img[50:80, 50:150] = 0  # Dark rectangle
        img[100:130, 50:200] = 0  # Another dark rectangle
        return img

    @pytest.fixture
    def ocr_engine(self):
        """Create an OCR engine instance."""
        return OCREngine(backend=OCRBackend.TESSERACT)

    def test_engine_initialization(self):
        """Test OCR engine initialization."""
        engine = OCREngine(backend=OCRBackend.TESSERACT)

        assert engine.backend == OCRBackend.TESSERACT
        assert engine.preprocessor is not None
        assert engine.education_mode is False

    def test_engine_with_config(self):
        """Test OCR engine with custom configuration."""
        config = {"tesseract_psm": 6, "tesseract_oem": 1, "preprocessing": {"denoise": True}}

        engine = OCREngine(config=config)
        assert engine.config == config

    def test_configure_for_education(self, ocr_engine):
        """Test educational mode configuration."""
        ocr_engine.configure_for_education(
            document_type=DocumentType.WORKSHEET, enable_math_symbols=True
        )

        assert ocr_engine.education_mode is True
        assert ocr_engine.config["document_type"] == DocumentType.WORKSHEET
        assert ocr_engine.config["math_symbols"] is True

    @pytest.mark.parametrize(
        "doc_type",
        [
            DocumentType.WORKSHEET,
            DocumentType.TEXTBOOK,
            DocumentType.FLASHCARD,
        ],
    )
    def test_configure_different_document_types(self, ocr_engine, doc_type):
        """Test configuration for different document types."""
        ocr_engine.configure_for_education(document_type=doc_type)

        assert ocr_engine.config["document_type"] == doc_type
        assert ocr_engine.education_mode is True

    def test_preprocess_image(self, ocr_engine, sample_image):
        """Test image preprocessing."""
        processed = ocr_engine.preprocess_image(sample_image)

        assert processed is not None
        assert isinstance(processed, np.ndarray)
        assert processed.shape[0] > 0
        assert processed.shape[1] > 0

    def test_preprocess_invalid_image(self, ocr_engine):
        """Test preprocessing with invalid image."""
        with pytest.raises(ValueError, match="Invalid or empty image"):
            ocr_engine.preprocess_image(None)

    def test_preprocess_empty_image(self, ocr_engine):
        """Test preprocessing with empty image."""
        empty_img = np.array([])

        with pytest.raises(ValueError):
            ocr_engine.preprocess_image(empty_img)

    def test_custom_preprocessing_pipeline(self, ocr_engine, sample_image):
        """Test custom preprocessing pipeline."""
        custom_pipeline = ["denoise", "enhance_contrast"]
        processed = ocr_engine.preprocess_image(sample_image, custom_pipeline=custom_pipeline)

        assert processed is not None

    @patch("pytesseract.image_to_data")
    def test_detect_text_regions(self, mock_image_to_data, ocr_engine, sample_image):
        """Test text region detection."""
        # Mock Tesseract output
        mock_image_to_data.return_value = {
            "text": ["Hello", "World", ""],
            "conf": [95, 90, -1],
            "left": [10, 100, 0],
            "top": [20, 20, 0],
            "width": [80, 90, 0],
            "height": [30, 30, 0],
        }

        regions = ocr_engine.detect_text_regions(sample_image, min_confidence=0.5)

        assert len(regions) == 2
        assert all(isinstance(r, BoundingBox) for r in regions)

    @patch("pytesseract.image_to_data")
    def test_detect_text_regions_low_confidence(self, mock_image_to_data, ocr_engine, sample_image):
        """Test filtering low confidence regions."""
        mock_image_to_data.return_value = {
            "text": ["Hello", "World"],
            "conf": [95, 30],  # Second word has low confidence
            "left": [10, 100],
            "top": [20, 20],
            "width": [80, 90],
            "height": [30, 30],
        }

        regions = ocr_engine.detect_text_regions(sample_image, min_confidence=0.5)

        assert len(regions) == 1  # Only high confidence region

    @patch("pytesseract.image_to_string")
    @patch("pytesseract.image_to_data")
    def test_recognize_text(
        self, mock_image_to_data, mock_image_to_string, ocr_engine, sample_image
    ):
        """Test text recognition."""
        mock_image_to_string.return_value = "Hello World"
        mock_image_to_data.return_value = {"conf": [95, 90]}

        region = ocr_engine.recognize_text(sample_image)

        assert isinstance(region, TextRegion)
        assert region.text == "Hello World"
        assert region.confidence > 0

    @patch("pytesseract.image_to_string")
    @patch("pytesseract.image_to_data")
    def test_recognize_text_with_region(
        self, mock_image_to_data, mock_image_to_string, ocr_engine, sample_image
    ):
        """Test text recognition in specific region."""
        bbox = BoundingBox(x=10, y=10, width=100, height=50)
        mock_image_to_string.return_value = "Test"
        mock_image_to_data.return_value = {"conf": [95]}

        region = ocr_engine.recognize_text(sample_image, region=bbox)

        assert region.text == "Test"

    @patch("pytesseract.image_to_data")
    def test_extract_structured_content(self, mock_image_to_data, ocr_engine, sample_image):
        """Test structured content extraction."""
        mock_image_to_data.return_value = {
            "text": ["Hello", "World"],
            "conf": [95, 90],
            "left": [10, 100],
            "top": [20, 20],
            "width": [80, 90],
            "height": [30, 30],
        }

        result = ocr_engine.extract_structured_content(sample_image)

        assert isinstance(result, OCRResult)
        assert len(result.regions) == 2
        assert result.full_text == "Hello World"
        assert result.average_confidence > 0
        assert result.processing_time_ms > 0

    @patch("pytesseract.image_to_data")
    def test_extract_structured_content_no_preprocessing(
        self, mock_image_to_data, ocr_engine, sample_image
    ):
        """Test extraction without preprocessing."""
        mock_image_to_data.return_value = {
            "text": ["Test"],
            "conf": [95],
            "left": [10],
            "top": [20],
            "width": [80],
            "height": [30],
        }

        result = ocr_engine.extract_structured_content(sample_image, preprocess=False)

        assert isinstance(result, OCRResult)

    @patch("pytesseract.image_to_data")
    def test_extract_with_confidence_threshold(self, mock_image_to_data, ocr_engine, sample_image):
        """Test extraction with confidence threshold."""
        mock_image_to_data.return_value = {
            "text": ["High", "Low"],
            "conf": [95, 40],
            "left": [10, 100],
            "top": [20, 20],
            "width": [80, 90],
            "height": [30, 30],
        }

        result = ocr_engine.extract_structured_content(sample_image, min_confidence=0.7)

        assert len(result.regions) == 1  # Only high confidence text

    def test_extract_invalid_image(self, ocr_engine):
        """Test extraction with invalid image."""
        with pytest.raises(ValueError):
            ocr_engine.extract_structured_content(None)

    @patch("cv2.imread")
    @patch("pytesseract.image_to_data")
    def test_process_document_from_file(
        self, mock_image_to_data, mock_imread, ocr_engine, tmp_path
    ):
        """Test processing document from file path."""
        # Create a temporary test file
        test_file = tmp_path / "test.jpg"
        test_file.touch()

        # Mock image loading
        mock_imread.return_value = np.ones((100, 100, 3), dtype=np.uint8) * 255
        mock_image_to_data.return_value = {
            "text": ["Test"],
            "conf": [95],
            "left": [10],
            "top": [20],
            "width": [80],
            "height": [30],
        }

        result = ocr_engine.process_document(str(test_file))

        assert isinstance(result, dict)
        assert "full_text" in result

    def test_process_document_nonexistent_file(self, ocr_engine):
        """Test processing nonexistent file."""
        with pytest.raises(FileNotFoundError):
            ocr_engine.process_document("/nonexistent/file.jpg")

    @patch("cv2.imread")
    def test_process_document_invalid_image(self, mock_imread, ocr_engine, tmp_path):
        """Test processing invalid image file."""
        test_file = tmp_path / "invalid.jpg"
        test_file.touch()

        mock_imread.return_value = None  # Simulate invalid image

        with pytest.raises(ValueError, match="Failed to load image"):
            ocr_engine.process_document(str(test_file))

    @patch("pytesseract.image_to_data")
    def test_process_document_json_output(
        self, mock_image_to_data, ocr_engine, sample_image, tmp_path
    ):
        """Test document processing with JSON output."""
        test_file = tmp_path / "test.jpg"
        Image.fromarray(sample_image).save(test_file)

        mock_image_to_data.return_value = {
            "text": ["Test"],
            "conf": [95],
            "left": [10],
            "top": [20],
            "width": [80],
            "height": [30],
        }

        with patch("cv2.imread", return_value=sample_image):
            result = ocr_engine.process_document(str(test_file), output_format="json")

        assert isinstance(result, str)  # JSON string

    @pytest.mark.parametrize(
        "image_quality,expected_regions",
        [
            ("high", 5),
            ("medium", 3),
            ("low", 1),
        ],
    )
    @patch("pytesseract.image_to_data")
    def test_different_image_qualities(
        self, mock_image_to_data, ocr_engine, sample_image, image_quality, expected_regions
    ):
        """Test OCR with different image qualities."""
        # Simulate different qualities with different confidence levels
        if image_quality == "high":
            mock_data = {
                "text": ["Word"] * 5,
                "conf": [95] * 5,
                "left": list(range(0, 500, 100)),
                "top": [20] * 5,
                "width": [80] * 5,
                "height": [30] * 5,
            }
        elif image_quality == "medium":
            mock_data = {
                "text": ["Word"] * 3,
                "conf": [75] * 3,
                "left": [10, 100, 200],
                "top": [20] * 3,
                "width": [80] * 3,
                "height": [30] * 3,
            }
        else:  # low
            mock_data = {
                "text": ["Word"],
                "conf": [65],
                "left": [10],
                "top": [20],
                "width": [80],
                "height": [30],
            }

        mock_image_to_data.return_value = mock_data

        result = ocr_engine.extract_structured_content(sample_image)

        assert len(result.regions) == expected_regions

    @pytest.mark.parametrize(
        "text_format",
        [
            "simple_sentence",
            "with_numbers_123",
            "With-Punctuation!?",
            "UPPERCASE TEXT",
        ],
    )
    @patch("pytesseract.image_to_data")
    def test_various_text_formats(self, mock_image_to_data, ocr_engine, sample_image, text_format):
        """Test OCR with various text formats."""
        mock_image_to_data.return_value = {
            "text": [text_format],
            "conf": [90],
            "left": [10],
            "top": [20],
            "width": [100],
            "height": [30],
        }

        result = ocr_engine.extract_structured_content(sample_image)

        assert text_format in result.full_text

    @patch("pytesseract.image_to_data")
    def test_error_handling_tesseract_failure(self, mock_image_to_data, ocr_engine, sample_image):
        """Test error handling when Tesseract fails."""
        mock_image_to_data.side_effect = Exception("Tesseract error")

        result = ocr_engine.extract_structured_content(sample_image)

        # Should return empty result instead of crashing
        assert isinstance(result, OCRResult)
        assert len(result.regions) == 0

    def test_metadata_inclusion(self, ocr_engine, sample_image):
        """Test that metadata is included in results."""
        with patch("pytesseract.image_to_data") as mock:
            mock.return_value = {
                "text": ["Test"],
                "conf": [95],
                "left": [10],
                "top": [20],
                "width": [80],
                "height": [30],
            }

            result = ocr_engine.extract_structured_content(sample_image)

        assert "metadata" in result.to_dict()
        assert "image_shape" in result.metadata
        assert "backend" in result.metadata


class TestOCREdgeCases:
    """Test edge cases and error conditions."""

    def test_missing_dependencies(self):
        """Test handling of missing dependencies."""
        with patch("src.vision.ocr_engine.cv2", None):
            with pytest.raises(ImportError, match="OpenCV"):
                OCREngine()

    def test_rotated_text(self):
        """Test OCR with rotated text."""
        # Create image with rotated text simulation
        img = np.ones((200, 400, 3), dtype=np.uint8) * 255
        # Add diagonal pattern
        for i in range(min(img.shape[0], img.shape[1])):
            img[i, i] = 0

        engine = OCREngine()

        with patch("pytesseract.image_to_data") as mock:
            mock.return_value = {
                "text": ["Rotated"],
                "conf": [80],
                "left": [10],
                "top": [20],
                "width": [80],
                "height": [30],
            }

            result = engine.extract_structured_content(img)

        assert isinstance(result, OCRResult)

    def test_multilingual_text(self):
        """Test OCR with multiple languages (if supported)."""
        engine = OCREngine()
        img = np.ones((200, 400, 3), dtype=np.uint8) * 255

        with patch("pytesseract.image_to_data") as mock:
            mock.return_value = {
                "text": ["Hello", "Bonjour"],
                "conf": [90, 85],
                "left": [10, 100],
                "top": [20, 20],
                "width": [80, 90],
                "height": [30, 30],
            }

            result = engine.extract_structured_content(img)

        assert len(result.regions) == 2

    def test_mathematical_expressions(self):
        """Test OCR with mathematical expressions."""
        engine = OCREngine()
        engine.configure_for_education(enable_math_symbols=True)

        img = np.ones((100, 200, 3), dtype=np.uint8) * 255

        with patch("pytesseract.image_to_data") as mock:
            mock.return_value = {
                "text": ["2", "+", "3", "=", "5"],
                "conf": [95] * 5,
                "left": [10, 30, 50, 70, 90],
                "top": [20] * 5,
                "width": [15] * 5,
                "height": [20] * 5,
            }

            result = engine.extract_structured_content(img)

        assert "2" in result.full_text
        assert "5" in result.full_text

    def test_empty_text_regions(self):
        """Test handling of empty text regions."""
        engine = OCREngine()
        img = np.ones((100, 100, 3), dtype=np.uint8) * 255

        with patch("pytesseract.image_to_data") as mock:
            mock.return_value = {
                "text": ["", "", "Valid"],
                "conf": [-1, -1, 90],
                "left": [0, 0, 10],
                "top": [0, 0, 20],
                "width": [0, 0, 80],
                "height": [0, 0, 30],
            }

            result = engine.extract_structured_content(img)

        # Should only include valid text
        assert len(result.regions) == 1
        assert result.full_text == "Valid"
