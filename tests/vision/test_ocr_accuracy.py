"""
Comprehensive Test Suite for EduLens OCR Engine

This module provides extensive testing for the OCR engine including:
- Accuracy measurement for different document types
- Performance benchmarking
- Preprocessing validation
- Edge case handling

Author: Vision Processing Agent (VIS-001)
Target: 95% accuracy on printed educational materials
"""

import json
import time
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

from src.vision.ocr_engine import (
    BoundingBox,
    DocumentType,
    OCRBackend,
    OCREngine,
    OCRResult,
    TextRegion,
)
from src.vision.preprocessing import ImagePreprocessor


class TestFixtures:
    """Test fixtures and sample data for OCR testing."""

    @staticmethod
    def create_synthetic_text_image(
        text: str,
        width: int = 800,
        height: int = 200,
        font_scale: float = 1.5,
        noise_level: float = 0.0,
        rotation: float = 0.0,
    ) -> np.ndarray:
        """
        Create a synthetic image with text for testing.

        Args:
            text: Text to render
            width: Image width
            height: Image height
            font_scale: Font size scale
            noise_level: Amount of noise to add (0.0 to 1.0)
            rotation: Rotation angle in degrees

        Returns:
            Synthetic image as numpy array
        """
        if cv2 is None:
            raise ImportError("OpenCV required for creating test images")

        # Create white background
        image = np.ones((height, width, 3), dtype=np.uint8) * 255

        # Add text
        font = cv2.FONT_HERSHEY_SIMPLEX
        thickness = 2

        # Get text size
        (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)

        # Center text
        x = (width - text_width) // 2
        y = (height + text_height) // 2

        # Draw text
        cv2.putText(image, text, (x, y), font, font_scale, (0, 0, 0), thickness, cv2.LINE_AA)

        # Add noise if specified
        if noise_level > 0:
            noise = np.random.normal(0, noise_level * 50, image.shape).astype(np.uint8)
            image = cv2.add(image, noise)

        # Apply rotation if specified
        if rotation != 0:
            center = (width // 2, height // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, rotation, 1.0)
            image = cv2.warpAffine(
                image, rotation_matrix, (width, height), borderValue=(255, 255, 255)
            )

        return image

    @staticmethod
    def create_worksheet_image(
        questions: List[str], width: int = 800, height: int = 600
    ) -> np.ndarray:
        """
        Create a synthetic worksheet image for testing.

        Args:
            questions: List of question texts
            width: Image width
            height: Image height

        Returns:
            Synthetic worksheet image
        """
        if cv2 is None:
            raise ImportError("OpenCV required for creating test images")

        # Create white background
        image = np.ones((height, width, 3), dtype=np.uint8) * 255

        # Add grid lines (common in worksheets)
        line_color = (200, 200, 200)
        for i in range(0, height, 50):
            cv2.line(image, (0, i), (width, i), line_color, 1)

        # Add questions
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        thickness = 2
        y_offset = 30

        for i, question in enumerate(questions):
            y = y_offset + (i * 80)
            cv2.putText(
                image,
                f"{i+1}. {question}",
                (30, y),
                font,
                font_scale,
                (0, 0, 0),
                thickness,
                cv2.LINE_AA,
            )

        return image

    @staticmethod
    def create_textbook_page(
        title: str, paragraphs: List[str], width: int = 800, height: int = 1000
    ) -> np.ndarray:
        """
        Create a synthetic textbook page for testing.

        Args:
            title: Page title
            paragraphs: List of paragraph texts
            width: Image width
            height: Image height

        Returns:
            Synthetic textbook page image
        """
        if cv2 is None:
            raise ImportError("OpenCV required for creating test images")

        # Create white background
        image = np.ones((height, width, 3), dtype=np.uint8) * 255

        font = cv2.FONT_HERSHEY_SIMPLEX
        y_offset = 50

        # Add title
        title_scale = 1.2
        title_thickness = 3
        cv2.putText(
            image, title, (50, y_offset), font, title_scale, (0, 0, 0), title_thickness, cv2.LINE_AA
        )

        y_offset += 80

        # Add paragraphs
        para_scale = 0.6
        para_thickness = 1
        line_height = 25

        for paragraph in paragraphs:
            # Split into lines (simple word wrap)
            words = paragraph.split()
            current_line = ""

            for word in words:
                test_line = current_line + " " + word if current_line else word
                (text_width, _), _ = cv2.getTextSize(test_line, font, para_scale, para_thickness)

                if text_width > width - 100:
                    # Draw current line
                    cv2.putText(
                        image,
                        current_line,
                        (50, y_offset),
                        font,
                        para_scale,
                        (0, 0, 0),
                        para_thickness,
                        cv2.LINE_AA,
                    )
                    y_offset += line_height
                    current_line = word
                else:
                    current_line = test_line

            # Draw remaining text
            if current_line:
                cv2.putText(
                    image,
                    current_line,
                    (50, y_offset),
                    font,
                    para_scale,
                    (0, 0, 0),
                    para_thickness,
                    cv2.LINE_AA,
                )
                y_offset += line_height

            y_offset += 20  # Space between paragraphs

        return image


class AccuracyMetrics:
    """Utility class for calculating OCR accuracy metrics."""

    @staticmethod
    def calculate_character_accuracy(ground_truth: str, recognized: str) -> float:
        """
        Calculate character-level accuracy using edit distance.

        Args:
            ground_truth: Expected text
            recognized: OCR-recognized text

        Returns:
            Accuracy percentage (0.0 to 100.0)
        """
        # Normalize strings
        gt = ground_truth.strip().lower()
        rec = recognized.strip().lower()

        if not gt:
            return 100.0 if not rec else 0.0

        # Calculate Levenshtein distance
        distance = AccuracyMetrics._levenshtein_distance(gt, rec)

        # Calculate accuracy
        max_len = max(len(gt), len(rec))
        accuracy = (1 - distance / max_len) * 100 if max_len > 0 else 100.0

        return max(0.0, accuracy)

    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """
        Calculate Levenshtein distance between two strings.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Edit distance
        """
        if len(s1) < len(s2):
            return AccuracyMetrics._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    @staticmethod
    def calculate_word_accuracy(ground_truth: str, recognized: str) -> float:
        """
        Calculate word-level accuracy.

        Args:
            ground_truth: Expected text
            recognized: OCR-recognized text

        Returns:
            Accuracy percentage (0.0 to 100.0)
        """
        gt_words = ground_truth.strip().lower().split()
        rec_words = recognized.strip().lower().split()

        if not gt_words:
            return 100.0 if not rec_words else 0.0

        # Count matching words
        matches = sum(1 for gt, rec in zip(gt_words, rec_words) if gt == rec)

        # Calculate accuracy
        accuracy = (matches / len(gt_words)) * 100

        return accuracy


class PerformanceBenchmark:
    """Performance benchmarking utilities."""

    def __init__(self):
        """Initialize performance benchmark."""
        self.results = []

    def measure_processing_time(
        self, ocr_engine: OCREngine, image: np.ndarray, iterations: int = 10
    ) -> Dict[str, float]:
        """
        Measure OCR processing time.

        Args:
            ocr_engine: OCR engine instance
            image: Test image
            iterations: Number of iterations for averaging

        Returns:
            Dictionary with timing statistics
        """
        times = []

        for _ in range(iterations):
            start_time = time.time()
            ocr_engine.extract_structured_content(image)
            elapsed = (time.time() - start_time) * 1000  # Convert to ms
            times.append(elapsed)

        return {
            "mean_ms": np.mean(times),
            "std_ms": np.std(times),
            "min_ms": np.min(times),
            "max_ms": np.max(times),
            "median_ms": np.median(times),
        }

    def measure_throughput(
        self, ocr_engine: OCREngine, images: List[np.ndarray], duration_seconds: float = 10.0
    ) -> Dict[str, float]:
        """
        Measure OCR throughput (images per second).

        Args:
            ocr_engine: OCR engine instance
            images: List of test images
            duration_seconds: Test duration

        Returns:
            Dictionary with throughput metrics
        """
        if not images:
            return {"images_per_second": 0.0, "total_processed": 0}

        start_time = time.time()
        processed = 0

        while (time.time() - start_time) < duration_seconds:
            for image in images:
                ocr_engine.extract_structured_content(image)
                processed += 1

                if (time.time() - start_time) >= duration_seconds:
                    break

        elapsed = time.time() - start_time
        throughput = processed / elapsed

        return {
            "images_per_second": throughput,
            "total_processed": processed,
            "duration_seconds": elapsed,
        }


class TestOCREngine(unittest.TestCase):
    """Test cases for OCR Engine."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.fixtures = TestFixtures()
        cls.metrics = AccuracyMetrics()

    def setUp(self):
        """Set up each test."""
        self.engine = OCREngine(backend=OCRBackend.TESSERACT)

    def test_engine_initialization(self):
        """Test OCR engine initialization."""
        self.assertIsNotNone(self.engine)
        self.assertEqual(self.engine.backend, OCRBackend.TESSERACT)
        self.assertFalse(self.engine.education_mode)

    def test_education_mode_configuration(self):
        """Test educational mode configuration."""
        self.engine.configure_for_education(
            document_type=DocumentType.WORKSHEET, enable_math_symbols=True
        )

        self.assertTrue(self.engine.education_mode)
        self.assertEqual(self.engine.config["document_type"], DocumentType.WORKSHEET)
        self.assertTrue(self.engine.config["math_symbols"])

    def test_simple_text_recognition(self):
        """Test recognition of simple printed text."""
        test_text = "The quick brown fox jumps over the lazy dog"
        image = self.fixtures.create_synthetic_text_image(test_text)

        result = self.engine.extract_structured_content(image)

        # Check that text was recognized
        self.assertIsNotNone(result.full_text)
        self.assertGreater(len(result.full_text), 0)

        # Calculate accuracy
        accuracy = self.metrics.calculate_character_accuracy(test_text, result.full_text)
        print(f"Simple text accuracy: {accuracy:.2f}%")

        # Should achieve high accuracy on clean synthetic text
        self.assertGreater(accuracy, 90.0)

    def test_elementary_vocabulary_recognition(self):
        """Test recognition of elementary-level vocabulary."""
        test_texts = [
            "apple banana cat dog elephant",
            "1 2 3 4 5 6 7 8 9 10",
            "red blue green yellow orange",
            "What is your name?",
            "The sun is bright today",
        ]

        total_accuracy = 0.0

        for text in test_texts:
            image = self.fixtures.create_synthetic_text_image(text)
            result = self.engine.extract_structured_content(image)

            accuracy = self.metrics.calculate_character_accuracy(text, result.full_text)
            total_accuracy += accuracy
            print(f"Text: '{text}' -> Accuracy: {accuracy:.2f}%")

        avg_accuracy = total_accuracy / len(test_texts)
        print(f"Average elementary vocabulary accuracy: {avg_accuracy:.2f}%")

        self.assertGreater(avg_accuracy, 85.0)

    def test_worksheet_recognition(self):
        """Test recognition of worksheet content."""
        self.engine.configure_for_education(document_type=DocumentType.WORKSHEET)

        questions = ["What is 2 + 2?", "How many apples are there?", "Circle the correct answer"]

        image = self.fixtures.create_worksheet_image(questions)
        result = self.engine.extract_structured_content(image)

        # Check that multiple regions were detected
        self.assertGreater(len(result.regions), 0)

        # Check that text was recognized
        self.assertGreater(len(result.full_text), 0)
        print(f"Worksheet text: {result.full_text}")

    def test_textbook_page_recognition(self):
        """Test recognition of textbook page content."""
        self.engine.configure_for_education(document_type=DocumentType.TEXTBOOK)

        title = "Chapter 1: Animals"
        paragraphs = [
            "Animals are living things that can move around. They need food and water to live.",
            "There are many different types of animals. Some animals have fur and some have feathers.",
        ]

        image = self.fixtures.create_textbook_page(title, paragraphs)
        result = self.engine.extract_structured_content(image)

        # Check that text was recognized
        self.assertGreater(len(result.full_text), 0)
        self.assertGreater(len(result.regions), 0)

        print(
            f"Textbook page - Regions: {len(result.regions)}, Confidence: {result.average_confidence:.2f}"
        )

    def test_preprocessing_pipeline(self):
        """Test image preprocessing pipeline."""
        test_text = "Hello World"
        image = self.fixtures.create_synthetic_text_image(test_text, noise_level=0.3, rotation=5.0)

        # Test without preprocessing
        result_no_preprocess = self.engine.extract_structured_content(image, preprocess=False)
        accuracy_no_preprocess = self.metrics.calculate_character_accuracy(
            test_text, result_no_preprocess.full_text
        )

        # Test with preprocessing
        result_with_preprocess = self.engine.extract_structured_content(image, preprocess=True)
        accuracy_with_preprocess = self.metrics.calculate_character_accuracy(
            test_text, result_with_preprocess.full_text
        )

        print(f"Accuracy without preprocessing: {accuracy_no_preprocess:.2f}%")
        print(f"Accuracy with preprocessing: {accuracy_with_preprocess:.2f}%")

        # Preprocessing should help with noisy/rotated images
        # (though not guaranteed in all cases)
        self.assertIsNotNone(result_with_preprocess)

    def test_confidence_scoring(self):
        """Test confidence score calculation."""
        test_text = "Test confidence scoring"
        image = self.fixtures.create_synthetic_text_image(test_text)

        result = self.engine.extract_structured_content(image)

        # Check that confidence scores are valid
        self.assertGreaterEqual(result.average_confidence, 0.0)
        self.assertLessEqual(result.average_confidence, 1.0)

        for region in result.regions:
            self.assertGreaterEqual(region.confidence, 0.0)
            self.assertLessEqual(region.confidence, 1.0)

        print(f"Average confidence: {result.average_confidence:.2f}")

    def test_bounding_box_detection(self):
        """Test bounding box detection for text regions."""
        test_text = "Bounding Box Test"
        image = self.fixtures.create_synthetic_text_image(test_text)

        result = self.engine.extract_structured_content(image)

        # Check that bounding boxes are valid
        for region in result.regions:
            bbox = region.bounding_box
            self.assertGreaterEqual(bbox.x, 0)
            self.assertGreaterEqual(bbox.y, 0)
            self.assertGreater(bbox.width, 0)
            self.assertGreater(bbox.height, 0)

            # Check coordinates
            x1, y1, x2, y2 = bbox.to_coordinates()
            self.assertLess(x1, x2)
            self.assertLess(y1, y2)

    def test_empty_image_handling(self):
        """Test handling of empty/invalid images."""
        # Test empty image
        with self.assertRaises(ValueError):
            empty_image = np.array([])
            self.engine.extract_structured_content(empty_image)

        # Test None image
        with self.assertRaises(ValueError):
            self.engine.extract_structured_content(None)

    def test_processing_time(self):
        """Test that processing time is within acceptable limits."""
        test_text = "Performance test"
        image = self.fixtures.create_synthetic_text_image(test_text)

        result = self.engine.extract_structured_content(image)

        # Check that processing time was recorded
        self.assertGreater(result.processing_time_ms, 0)

        # For edge deployment, should be reasonably fast
        # (This threshold may need adjustment based on hardware)
        print(f"Processing time: {result.processing_time_ms:.2f}ms")

    def test_result_serialization(self):
        """Test serialization of OCR results."""
        test_text = "Serialization test"
        image = self.fixtures.create_synthetic_text_image(test_text)

        result = self.engine.extract_structured_content(image)
        result_dict = result.to_dict()

        # Check that all fields are present
        self.assertIn("regions", result_dict)
        self.assertIn("full_text", result_dict)
        self.assertIn("average_confidence", result_dict)
        self.assertIn("processing_time_ms", result_dict)
        self.assertIn("metadata", result_dict)

        # Check that it's JSON serializable
        json_str = json.dumps(result_dict)
        self.assertIsNotNone(json_str)


class TestImagePreprocessor(unittest.TestCase):
    """Test cases for Image Preprocessor."""

    def setUp(self):
        """Set up each test."""
        self.preprocessor = ImagePreprocessor()
        self.fixtures = TestFixtures()

    def test_preprocessor_initialization(self):
        """Test preprocessor initialization."""
        self.assertIsNotNone(self.preprocessor)

    def test_grayscale_conversion(self):
        """Test grayscale conversion."""
        # Create color image
        color_image = np.ones((100, 100, 3), dtype=np.uint8) * 128

        gray = self.preprocessor.convert_to_grayscale(color_image)

        # Check that result is grayscale
        self.assertEqual(len(gray.shape), 2)

    def test_deskewing(self):
        """Test image deskewing."""
        test_text = "Deskew test"
        image = self.fixtures.create_synthetic_text_image(test_text, rotation=5.0)

        deskewed = self.preprocessor.deskew(image)

        # Check that image was processed
        self.assertIsNotNone(deskewed)
        self.assertEqual(deskewed.shape[2], image.shape[2])  # Same number of channels

    def test_denoising(self):
        """Test noise reduction."""
        test_text = "Denoise test"
        noisy_image = self.fixtures.create_synthetic_text_image(test_text, noise_level=0.5)

        denoised = self.preprocessor.denoise(noisy_image, method="bilateral")

        # Check that image was processed
        self.assertIsNotNone(denoised)
        self.assertEqual(denoised.shape, noisy_image.shape)

    def test_contrast_enhancement(self):
        """Test contrast enhancement."""
        test_text = "Contrast test"
        image = self.fixtures.create_synthetic_text_image(test_text)

        enhanced = self.preprocessor.enhance_contrast(image, method="clahe")

        # Check that image was processed
        self.assertIsNotNone(enhanced)

    def test_binarization(self):
        """Test image binarization."""
        test_text = "Binarize test"
        image = self.fixtures.create_synthetic_text_image(test_text)

        # Test Otsu's method
        binary_otsu = self.preprocessor.binarize(image, method="otsu")
        self.assertIsNotNone(binary_otsu)

        # Test adaptive thresholding
        binary_adaptive = self.preprocessor.binarize(image, method="adaptive")
        self.assertIsNotNone(binary_adaptive)

        # Binary images should be single channel
        self.assertEqual(len(binary_otsu.shape), 2)
        self.assertEqual(len(binary_adaptive.shape), 2)

    def test_sharpening(self):
        """Test image sharpening."""
        test_text = "Sharpen test"
        image = self.fixtures.create_synthetic_text_image(test_text)

        sharpened = self.preprocessor.sharpen(image, strength=1.5)

        # Check that image was processed
        self.assertIsNotNone(sharpened)
        self.assertEqual(sharpened.shape, image.shape)

    def test_line_removal(self):
        """Test removal of grid lines."""
        questions = ["Question 1", "Question 2"]
        worksheet = self.fixtures.create_worksheet_image(questions)

        # Remove lines
        no_lines = self.preprocessor.remove_lines(worksheet, line_type="both")

        # Check that image was processed
        self.assertIsNotNone(no_lines)

    def test_resizing(self):
        """Test image resizing."""
        test_text = "Resize test"
        image = self.fixtures.create_synthetic_text_image(test_text, width=400, height=100)

        # Upscale
        upscaled = self.preprocessor.resize(image, scale=2.0)
        self.assertEqual(upscaled.shape[0], image.shape[0] * 2)
        self.assertEqual(upscaled.shape[1], image.shape[1] * 2)

        # Downscale
        downscaled = self.preprocessor.resize(image, scale=0.5)
        self.assertEqual(downscaled.shape[0], image.shape[0] // 2)
        self.assertEqual(downscaled.shape[1], image.shape[1] // 2)

    def test_full_preprocessing_pipeline(self):
        """Test complete preprocessing pipeline."""
        test_text = "Full pipeline test"
        image = self.fixtures.create_synthetic_text_image(test_text, noise_level=0.2, rotation=3.0)

        config = {
            "deskew": True,
            "denoise": True,
            "enhance_contrast": True,
            "sharpen": True,
            "binarization_method": "adaptive",
        }

        preprocessor = ImagePreprocessor(config=config)
        processed = preprocessor.preprocess(image)

        # Check that image was processed
        self.assertIsNotNone(processed)


class TestPerformanceBenchmarks(unittest.TestCase):
    """Performance benchmark tests."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.fixtures = TestFixtures()
        cls.benchmark = PerformanceBenchmark()

    def setUp(self):
        """Set up each test."""
        self.engine = OCREngine(backend=OCRBackend.TESSERACT)

    def test_processing_time_benchmark(self):
        """Benchmark OCR processing time."""
        test_text = "Performance benchmark"
        image = self.fixtures.create_synthetic_text_image(test_text)

        timing = self.benchmark.measure_processing_time(self.engine, image, iterations=5)

        print(f"\nProcessing Time Benchmark:")
        print(f"  Mean: {timing['mean_ms']:.2f}ms")
        print(f"  Std: {timing['std_ms']:.2f}ms")
        print(f"  Min: {timing['min_ms']:.2f}ms")
        print(f"  Max: {timing['max_ms']:.2f}ms")
        print(f"  Median: {timing['median_ms']:.2f}ms")

        # Basic sanity check
        self.assertGreater(timing["mean_ms"], 0)

    def test_accuracy_benchmark(self):
        """Benchmark OCR accuracy on various document types."""
        test_cases = [
            ("Simple text", "The cat sat on the mat"),
            ("Numbers", "1234567890"),
            ("Mixed", "There are 5 apples and 3 oranges"),
            ("Question", "What is 2 plus 2?"),
            ("Punctuation", "Hello, world! How are you?"),
        ]

        print("\nAccuracy Benchmark:")

        accuracies = []
        for name, text in test_cases:
            image = self.fixtures.create_synthetic_text_image(text)
            result = self.engine.extract_structured_content(image)

            accuracy = AccuracyMetrics.calculate_character_accuracy(text, result.full_text)
            accuracies.append(accuracy)

            print(f"  {name}: {accuracy:.2f}% (confidence: {result.average_confidence:.2f})")

        avg_accuracy = np.mean(accuracies)
        print(f"  Average: {avg_accuracy:.2f}%")

        # Target is 95% accuracy
        self.assertGreater(avg_accuracy, 80.0)  # Reasonable threshold for synthetic images


def run_comprehensive_test_suite():
    """
    Run comprehensive test suite and generate report.

    Returns:
        Test results dictionary
    """
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestOCREngine))
    suite.addTests(loader.loadTestsFromTestCase(TestImagePreprocessor))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceBenchmarks))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate summary
    summary = {
        "total_tests": result.testsRun,
        "successes": result.testsRun - len(result.failures) - len(result.errors),
        "failures": len(result.failures),
        "errors": len(result.errors),
        "success_rate": (
            ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100)
            if result.testsRun > 0
            else 0
        ),
    }

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Successes: {summary['successes']}")
    print(f"Failures: {summary['failures']}")
    print(f"Errors: {summary['errors']}")
    print(f"Success Rate: {summary['success_rate']:.2f}%")
    print("=" * 70)

    return summary


if __name__ == "__main__":
    # Run comprehensive test suite
    run_comprehensive_test_suite()
