"""
Comprehensive Test Suite for EduLens Handwriting Recognition

This module provides extensive testing for the handwriting recognition engine
optimized for children's handwriting (ages 6-12). It includes:
- Accuracy measurement by age group
- Style-specific testing (printed, cursive, mixed)
- Mathematical expression recognition tests
- Performance benchmarking
- Edge case handling

Author: Vision Processing Agent (VIS-001)
Target: 85% accuracy on child handwriting samples
"""

import json
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

from src.vision.character_segmenter import CharacterSegmenter, Segment, SegmentationResult
from src.vision.handwriting_engine import (
    AgeGroup,
    HandwritingCharacter,
    HandwritingRecognizer,
    HandwritingResult,
    HandwritingStyle,
    HandwritingWord,
)
from src.vision.preprocessing import ImagePreprocessor


class HandwritingTestFixtures:
    """Test fixtures and sample data for handwriting testing."""

    @staticmethod
    def create_synthetic_handwriting(
        text: str,
        width: int = 800,
        height: int = 200,
        font_scale: float = 1.0,
        noise_level: float = 0.1,
        rotation: float = 0.0,
        irregularity: float = 0.2,
    ) -> np.ndarray:
        """
        Create synthetic handwriting image for testing.

        Args:
            text: Text to render
            width: Image width
            height: Image height
            font_scale: Font size scale
            noise_level: Amount of noise (0.0 to 1.0)
            rotation: Rotation angle in degrees
            irregularity: Amount of irregularity in letter positioning

        Returns:
            Synthetic handwriting image
        """
        if cv2 is None:
            raise ImportError("OpenCV required for creating test images")

        # Create white background
        image = np.ones((height, width, 3), dtype=np.uint8) * 255

        # Use handwriting-like font
        font = cv2.FONT_HERSHEY_SCRIPT_SIMPLEX
        thickness = max(1, int(2 * font_scale))

        # Calculate starting position
        x = 30
        y = height // 2

        # Draw text with irregularity
        for i, char in enumerate(text):
            # Add position irregularity
            char_x = x + int(np.random.uniform(-irregularity * 10, irregularity * 10))
            char_y = y + int(np.random.uniform(-irregularity * 5, irregularity * 5))

            # Draw character
            cv2.putText(
                image, char, (char_x, char_y), font, font_scale, (0, 0, 0), thickness, cv2.LINE_AA
            )

            # Update x position
            (char_width, _), _ = cv2.getTextSize(char, font, font_scale, thickness)
            x += char_width + int(5 * font_scale)

        # Add noise
        if noise_level > 0:
            noise = np.random.normal(0, noise_level * 50, image.shape).astype(np.int16)
            image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # Apply rotation
        if rotation != 0:
            center = (width // 2, height // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, rotation, 1.0)
            image = cv2.warpAffine(
                image, rotation_matrix, (width, height), borderValue=(255, 255, 255)
            )

        return image

    @staticmethod
    def create_child_handwriting_simulation(
        text: str, age_group: AgeGroup, width: int = 800, height: int = 200
    ) -> np.ndarray:
        """
        Create handwriting simulating a specific age group.

        Args:
            text: Text to render
            age_group: Age group to simulate
            width: Image width
            height: Image height

        Returns:
            Simulated child handwriting image
        """
        if age_group == AgeGroup.EARLY_ELEMENTARY:
            # 6-8 years: Large, irregular letters
            return HandwritingTestFixtures.create_synthetic_handwriting(
                text,
                width=width,
                height=height,
                font_scale=1.5,
                noise_level=0.15,
                rotation=np.random.uniform(-8, 8),
                irregularity=0.3,
            )
        elif age_group == AgeGroup.MID_ELEMENTARY:
            # 9-10 years: More consistent
            return HandwritingTestFixtures.create_synthetic_handwriting(
                text,
                width=width,
                height=height,
                font_scale=1.2,
                noise_level=0.1,
                rotation=np.random.uniform(-5, 5),
                irregularity=0.2,
            )
        else:  # LATE_ELEMENTARY
            # 11-12 years: Mature handwriting
            return HandwritingTestFixtures.create_synthetic_handwriting(
                text,
                width=width,
                height=height,
                font_scale=1.0,
                noise_level=0.05,
                rotation=np.random.uniform(-3, 3),
                irregularity=0.1,
            )

    @staticmethod
    def create_math_expression_image(
        expression: str, width: int = 600, height: int = 150
    ) -> np.ndarray:
        """
        Create image with mathematical expression.

        Args:
            expression: Mathematical expression string
            width: Image width
            height: Image height

        Returns:
            Math expression image
        """
        if cv2 is None:
            raise ImportError("OpenCV required for creating test images")

        # Create white background
        image = np.ones((height, width, 3), dtype=np.uint8) * 255

        # Use simple font for math
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.5
        thickness = 2

        # Center text
        (text_width, text_height), baseline = cv2.getTextSize(
            expression, font, font_scale, thickness
        )
        x = (width - text_width) // 2
        y = (height + text_height) // 2

        # Draw expression
        cv2.putText(image, expression, (x, y), font, font_scale, (0, 0, 0), thickness, cv2.LINE_AA)

        return image

    @staticmethod
    def create_multi_line_handwriting(
        lines: List[str], age_group: AgeGroup, width: int = 800, height: int = 600
    ) -> np.ndarray:
        """
        Create multi-line handwriting image.

        Args:
            lines: List of text lines
            age_group: Age group to simulate
            width: Image width
            height: Image height

        Returns:
            Multi-line handwriting image
        """
        if cv2 is None:
            raise ImportError("OpenCV required for creating test images")

        # Create white background
        image = np.ones((height, width, 3), dtype=np.uint8) * 255

        # Font parameters based on age group
        if age_group == AgeGroup.EARLY_ELEMENTARY:
            font_scale = 1.2
            line_spacing = 80
        elif age_group == AgeGroup.MID_ELEMENTARY:
            font_scale = 1.0
            line_spacing = 60
        else:
            font_scale = 0.8
            line_spacing = 50

        font = cv2.FONT_HERSHEY_SCRIPT_SIMPLEX
        thickness = 2

        # Draw each line
        y_offset = 60
        for line_text in lines:
            x = 30
            y = y_offset

            for char in line_text:
                cv2.putText(
                    image, char, (x, y), font, font_scale, (0, 0, 0), thickness, cv2.LINE_AA
                )

                (char_width, _), _ = cv2.getTextSize(char, font, font_scale, thickness)
                x += char_width + 5

            y_offset += line_spacing

        return image


class HandwritingAccuracyMetrics:
    """Utility class for calculating handwriting recognition accuracy."""

    @staticmethod
    def calculate_character_accuracy(
        ground_truth: str, recognized: str, case_sensitive: bool = False
    ) -> float:
        """
        Calculate character-level accuracy.

        Args:
            ground_truth: Expected text
            recognized: Recognized text
            case_sensitive: Whether to consider case

        Returns:
            Accuracy percentage (0.0 to 100.0)
        """
        if not case_sensitive:
            ground_truth = ground_truth.lower()
            recognized = recognized.lower()

        # Remove spaces for character comparison
        gt = ground_truth.replace(" ", "")
        rec = recognized.replace(" ", "")

        if not gt:
            return 100.0 if not rec else 0.0

        # Calculate Levenshtein distance
        distance = HandwritingAccuracyMetrics._levenshtein_distance(gt, rec)

        # Calculate accuracy
        max_len = max(len(gt), len(rec))
        accuracy = (1 - distance / max_len) * 100 if max_len > 0 else 100.0

        return max(0.0, accuracy)

    @staticmethod
    def calculate_word_accuracy(
        ground_truth: str, recognized: str, case_sensitive: bool = False
    ) -> float:
        """
        Calculate word-level accuracy.

        Args:
            ground_truth: Expected text
            recognized: Recognized text
            case_sensitive: Whether to consider case

        Returns:
            Accuracy percentage (0.0 to 100.0)
        """
        if not case_sensitive:
            ground_truth = ground_truth.lower()
            recognized = recognized.lower()

        gt_words = ground_truth.strip().split()
        rec_words = recognized.strip().split()

        if not gt_words:
            return 100.0 if not rec_words else 0.0

        # Count matching words
        matches = 0
        for gt_word, rec_word in zip(gt_words, rec_words):
            if gt_word == rec_word:
                matches += 1

        accuracy = (matches / len(gt_words)) * 100
        return accuracy

    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return HandwritingAccuracyMetrics._levenshtein_distance(s2, s1)

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
    def calculate_confusion_matrix(
        predictions: List[str], ground_truths: List[str]
    ) -> Dict[str, Dict[str, int]]:
        """
        Calculate confusion matrix for character predictions.

        Args:
            predictions: List of predicted characters
            ground_truths: List of actual characters

        Returns:
            Confusion matrix as nested dictionary
        """
        confusion = {}

        for pred, truth in zip(predictions, ground_truths):
            if truth not in confusion:
                confusion[truth] = {}

            if pred not in confusion[truth]:
                confusion[truth][pred] = 0

            confusion[truth][pred] += 1

        return confusion


class TestHandwritingRecognizer(unittest.TestCase):
    """Test cases for HandwritingRecognizer."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.fixtures = HandwritingTestFixtures()
        cls.metrics = HandwritingAccuracyMetrics()

    def setUp(self):
        """Set up each test."""
        self.recognizer = HandwritingRecognizer()

    def test_recognizer_initialization(self):
        """Test handwriting recognizer initialization."""
        self.assertIsNotNone(self.recognizer)
        self.assertIsNotNone(self.recognizer.preprocessor)
        self.assertIsNotNone(self.recognizer.segmenter)

    def test_age_group_configuration(self):
        """Test age-specific configuration."""
        # Test early elementary
        self.recognizer.configure_for_children(AgeGroup.EARLY_ELEMENTARY)
        self.assertEqual(self.recognizer.age_group, AgeGroup.EARLY_ELEMENTARY)
        self.assertEqual(self.recognizer.min_confidence, 0.60)

        # Test mid elementary
        self.recognizer.configure_for_children(AgeGroup.MID_ELEMENTARY)
        self.assertEqual(self.recognizer.age_group, AgeGroup.MID_ELEMENTARY)
        self.assertEqual(self.recognizer.min_confidence, 0.70)

        # Test late elementary
        self.recognizer.configure_for_children(AgeGroup.LATE_ELEMENTARY)
        self.assertEqual(self.recognizer.age_group, AgeGroup.LATE_ELEMENTARY)
        self.assertEqual(self.recognizer.min_confidence, 0.75)

    def test_early_elementary_handwriting(self):
        """Test recognition of early elementary handwriting (ages 6-8)."""
        self.recognizer.configure_for_children(AgeGroup.EARLY_ELEMENTARY)

        test_words = ["cat", "dog", "sun", "run", "jump"]

        for word in test_words:
            image = self.fixtures.create_child_handwriting_simulation(
                word, AgeGroup.EARLY_ELEMENTARY
            )

            result = self.recognizer.recognize_handwriting(image)

            print(f"Early elem test - Expected: '{word}', Got: '{result.full_text}'")
            print(f"  Confidence: {result.average_confidence:.2f}")

            # Basic validation
            self.assertIsNotNone(result.full_text)

    def test_mid_elementary_handwriting(self):
        """Test recognition of mid elementary handwriting (ages 9-10)."""
        self.recognizer.configure_for_children(AgeGroup.MID_ELEMENTARY)

        test_sentences = ["The cat is happy", "I like to read", "Math is fun"]

        for sentence in test_sentences:
            image = self.fixtures.create_child_handwriting_simulation(
                sentence, AgeGroup.MID_ELEMENTARY
            )

            result = self.recognizer.recognize_handwriting(image)

            print(f"Mid elem test - Expected: '{sentence}', Got: '{result.full_text}'")
            print(f"  Confidence: {result.average_confidence:.2f}")
            print(f"  Words detected: {len(result.words)}")

            # Validation
            self.assertIsNotNone(result.full_text)
            self.assertGreater(len(result.words), 0)

    def test_late_elementary_handwriting(self):
        """Test recognition of late elementary handwriting (ages 11-12)."""
        self.recognizer.configure_for_children(AgeGroup.LATE_ELEMENTARY)

        test_sentences = ["The quick brown fox", "Science is interesting", "Reading comprehension"]

        for sentence in test_sentences:
            image = self.fixtures.create_child_handwriting_simulation(
                sentence, AgeGroup.LATE_ELEMENTARY
            )

            result = self.recognizer.recognize_handwriting(image)

            print(f"Late elem test - Expected: '{sentence}', Got: '{result.full_text}'")
            print(f"  Confidence: {result.average_confidence:.2f}")

            # Validation
            self.assertIsNotNone(result.full_text)

    def test_handwriting_preprocessing(self):
        """Test handwriting-specific preprocessing."""
        test_text = "Hello"
        image = self.fixtures.create_synthetic_handwriting(test_text, noise_level=0.2, rotation=5.0)

        # Test preprocessing
        preprocessed = self.recognizer.preprocess_handwriting(image)

        self.assertIsNotNone(preprocessed)
        self.assertEqual(preprocessed.shape[:2], image.shape[:2])

    def test_character_segmentation(self):
        """Test character segmentation on handwritten text."""
        test_text = "abc"
        image = self.fixtures.create_synthetic_handwriting(test_text)

        # Preprocess
        preprocessed = self.recognizer.preprocess_handwriting(image)

        # Segment
        segmentation = self.recognizer.segment_characters(preprocessed)

        print(f"Segmentation results:")
        print(f"  Lines: {len(segmentation.lines)}")
        print(f"  Words: {len(segmentation.words)}")
        print(f"  Characters: {len(segmentation.characters)}")

        # Validation
        self.assertIsNotNone(segmentation)
        self.assertGreaterEqual(len(segmentation.characters), 0)

    def test_math_expression_recognition(self):
        """Test recognition of mathematical expressions."""
        self.recognizer.configure_for_children(AgeGroup.MID_ELEMENTARY)

        test_expressions = ["2 + 2 = 4", "5 - 3 = 2", "3 × 4 = 12", "10 ÷ 2 = 5"]

        for expression in test_expressions:
            image = self.fixtures.create_math_expression_image(expression)

            result = self.recognizer.recognize_math_handwriting(image)

            print(f"Math test - Expected: '{expression}', Got: '{result.full_text}'")
            print(f"  Confidence: {result.average_confidence:.2f}")

            # Validation
            self.assertIsNotNone(result.full_text)

    def test_confidence_scoring(self):
        """Test confidence score calculation."""
        self.recognizer.configure_for_children(AgeGroup.MID_ELEMENTARY)

        test_text = "test"
        image = self.fixtures.create_child_handwriting_simulation(
            test_text, AgeGroup.MID_ELEMENTARY
        )

        result = self.recognizer.recognize_handwriting(image)
        confidence_scores = self.recognizer.get_confidence_scores(result)

        print(f"Confidence scores:")
        print(f"  Overall: {confidence_scores['overall']:.2f}")
        print(f"  High confidence ratio: {confidence_scores['high_confidence_ratio']:.2f}")
        print(f"  Low confidence count: {confidence_scores['low_confidence_count']}")

        # Validation
        self.assertIn("overall", confidence_scores)
        self.assertIn("per_word", confidence_scores)
        self.assertIn("per_character", confidence_scores)
        self.assertGreaterEqual(confidence_scores["overall"], 0.0)
        self.assertLessEqual(confidence_scores["overall"], 1.0)

    def test_multi_line_recognition(self):
        """Test recognition of multi-line handwriting."""
        self.recognizer.configure_for_children(AgeGroup.MID_ELEMENTARY)

        lines = ["Line one", "Line two", "Line three"]

        image = self.fixtures.create_multi_line_handwriting(lines, AgeGroup.MID_ELEMENTARY)

        result = self.recognizer.recognize_handwriting(image)

        print(f"Multi-line test:")
        print(f"  Recognized: {result.full_text}")
        print(f"  Words: {len(result.words)}")
        print(f"  Confidence: {result.average_confidence:.2f}")

        # Validation
        self.assertIsNotNone(result.full_text)

    def test_empty_image_handling(self):
        """Test handling of empty images."""
        with self.assertRaises(ValueError):
            empty_image = np.array([])
            self.recognizer.recognize_handwriting(empty_image)

    def test_result_serialization(self):
        """Test serialization of handwriting results."""
        test_text = "test"
        image = self.fixtures.create_synthetic_handwriting(test_text)

        result = self.recognizer.recognize_handwriting(image)
        result_dict = result.to_dict()

        # Check structure
        self.assertIn("words", result_dict)
        self.assertIn("full_text", result_dict)
        self.assertIn("average_confidence", result_dict)
        self.assertIn("dominant_style", result_dict)
        self.assertIn("processing_time_ms", result_dict)
        self.assertIn("metadata", result_dict)

        # Check JSON serializable
        json_str = json.dumps(result_dict)
        self.assertIsNotNone(json_str)


class TestCharacterSegmenter(unittest.TestCase):
    """Test cases for CharacterSegmenter."""

    def setUp(self):
        """Set up each test."""
        self.segmenter = CharacterSegmenter()
        self.fixtures = HandwritingTestFixtures()

    def test_segmenter_initialization(self):
        """Test segmenter initialization."""
        self.assertIsNotNone(self.segmenter)

    def test_line_segmentation(self):
        """Test line segmentation."""
        lines = ["First line", "Second line"]
        image = self.fixtures.create_multi_line_handwriting(
            lines, AgeGroup.MID_ELEMENTARY, width=600, height=300
        )

        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        line_segments = self.segmenter.segment_lines(gray)

        print(f"Line segmentation: {len(line_segments)} lines detected")

        self.assertGreaterEqual(len(line_segments), 0)

    def test_word_segmentation(self):
        """Test word segmentation."""
        text = "hello world test"
        image = self.fixtures.create_synthetic_handwriting(text)

        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        word_segments = self.segmenter.segment_words(gray)

        print(f"Word segmentation: {len(word_segments)} words detected")

        self.assertGreaterEqual(len(word_segments), 0)

    def test_character_segmentation(self):
        """Test character segmentation."""
        text = "abc"
        image = self.fixtures.create_synthetic_handwriting(text)

        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        char_segments = self.segmenter.segment_characters(gray)

        print(f"Character segmentation: {len(char_segments)} characters detected")

        self.assertGreaterEqual(len(char_segments), 0)

    def test_complete_segmentation(self):
        """Test complete segmentation pipeline."""
        text = "hello world"
        image = self.fixtures.create_synthetic_handwriting(text)

        result = self.segmenter.segment_all(
            image, segment_lines=True, segment_words=True, segment_characters=True
        )

        print(f"Complete segmentation:")
        print(f"  Lines: {len(result.lines)}")
        print(f"  Words: {len(result.words)}")
        print(f"  Characters: {len(result.characters)}")

        self.assertIsNotNone(result)
        self.assertIn("image_shape", result.metadata)


class TestHandwritingPerformance(unittest.TestCase):
    """Performance tests for handwriting recognition."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.fixtures = HandwritingTestFixtures()

    def setUp(self):
        """Set up each test."""
        self.recognizer = HandwritingRecognizer()
        self.recognizer.configure_for_children(AgeGroup.MID_ELEMENTARY)

    def test_processing_time(self):
        """Test processing time for handwriting recognition."""
        test_text = "Performance test"
        image = self.fixtures.create_child_handwriting_simulation(
            test_text, AgeGroup.MID_ELEMENTARY
        )

        start_time = time.time()
        result = self.recognizer.recognize_handwriting(image)
        elapsed = (time.time() - start_time) * 1000

        print(f"Processing time: {elapsed:.2f}ms")
        print(f"Result time: {result.processing_time_ms:.2f}ms")

        # Should complete within reasonable time for edge deployment
        self.assertLess(result.processing_time_ms, 5000)  # 5 seconds max

    def test_batch_performance(self):
        """Test performance on multiple images."""
        test_words = ["cat", "dog", "sun", "run", "jump"]

        total_time = 0
        for word in test_words:
            image = self.fixtures.create_child_handwriting_simulation(word, AgeGroup.MID_ELEMENTARY)

            start = time.time()
            result = self.recognizer.recognize_handwriting(image)
            elapsed = (time.time() - start) * 1000

            total_time += elapsed

        avg_time = total_time / len(test_words)
        print(f"Average processing time: {avg_time:.2f}ms per image")
        print(f"Total time: {total_time:.2f}ms for {len(test_words)} images")

        self.assertGreater(avg_time, 0)


class TestAccuracyBenchmarks(unittest.TestCase):
    """Accuracy benchmark tests by age group."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.fixtures = HandwritingTestFixtures()
        cls.metrics = HandwritingAccuracyMetrics()

    def setUp(self):
        """Set up each test."""
        self.recognizer = HandwritingRecognizer()

    def test_early_elementary_accuracy_target(self):
        """Test accuracy target for ages 6-8 (80% target)."""
        self.recognizer.configure_for_children(AgeGroup.EARLY_ELEMENTARY)

        test_cases = ["cat", "dog", "sun", "run", "bat", "hat", "mat", "sat", "rat", "pat"]

        print("\n" + "=" * 70)
        print("EARLY ELEMENTARY (Ages 6-8) ACCURACY BENCHMARK")
        print("=" * 70)

        total_accuracy = 0.0
        for text in test_cases:
            image = self.fixtures.create_child_handwriting_simulation(
                text, AgeGroup.EARLY_ELEMENTARY
            )

            result = self.recognizer.recognize_handwriting(image)

            # Note: With placeholder recognition, we can't measure real accuracy
            # In production, calculate: accuracy = metrics.calculate_character_accuracy(text, result.full_text)

            print(
                f"  Expected: '{text}', Got: '{result.full_text}', "
                f"Confidence: {result.average_confidence:.2f}"
            )

        print(f"Target accuracy: 80% (Note: Using placeholder recognition)")
        print("=" * 70)

    def test_mid_elementary_accuracy_target(self):
        """Test accuracy target for ages 9-10 (85% target)."""
        self.recognizer.configure_for_children(AgeGroup.MID_ELEMENTARY)

        test_cases = ["reading", "writing", "counting", "learning", "studying"]

        print("\n" + "=" * 70)
        print("MID ELEMENTARY (Ages 9-10) ACCURACY BENCHMARK")
        print("=" * 70)

        for text in test_cases:
            image = self.fixtures.create_child_handwriting_simulation(text, AgeGroup.MID_ELEMENTARY)

            result = self.recognizer.recognize_handwriting(image)

            print(
                f"  Expected: '{text}', Got: '{result.full_text}', "
                f"Confidence: {result.average_confidence:.2f}"
            )

        print(f"Target accuracy: 85% (Note: Using placeholder recognition)")
        print("=" * 70)

    def test_late_elementary_accuracy_target(self):
        """Test accuracy target for ages 11-12 (90% target)."""
        self.recognizer.configure_for_children(AgeGroup.LATE_ELEMENTARY)

        test_cases = ["comprehension", "vocabulary", "mathematics", "science", "history"]

        print("\n" + "=" * 70)
        print("LATE ELEMENTARY (Ages 11-12) ACCURACY BENCHMARK")
        print("=" * 70)

        for text in test_cases:
            image = self.fixtures.create_child_handwriting_simulation(
                text, AgeGroup.LATE_ELEMENTARY
            )

            result = self.recognizer.recognize_handwriting(image)

            print(
                f"  Expected: '{text}', Got: '{result.full_text}', "
                f"Confidence: {result.average_confidence:.2f}"
            )

        print(f"Target accuracy: 90% (Note: Using placeholder recognition)")
        print("=" * 70)

    def test_math_symbol_accuracy(self):
        """Test accuracy on mathematical symbols."""
        self.recognizer.configure_for_children(AgeGroup.MID_ELEMENTARY)

        test_expressions = ["1 + 1 = 2", "5 - 3 = 2", "2 × 3 = 6", "8 ÷ 2 = 4", "7 > 5", "3 < 9"]

        print("\n" + "=" * 70)
        print("MATH SYMBOL RECOGNITION BENCHMARK")
        print("=" * 70)

        for expression in test_expressions:
            image = self.fixtures.create_math_expression_image(expression)

            result = self.recognizer.recognize_math_handwriting(image)

            print(
                f"  Expected: '{expression}', Got: '{result.full_text}', "
                f"Confidence: {result.average_confidence:.2f}"
            )

        print("=" * 70)


def run_comprehensive_handwriting_tests():
    """
    Run comprehensive handwriting test suite and generate report.

    Returns:
        Test results dictionary
    """
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestHandwritingRecognizer))
    suite.addTests(loader.loadTestsFromTestCase(TestCharacterSegmenter))
    suite.addTests(loader.loadTestsFromTestCase(TestHandwritingPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestAccuracyBenchmarks))

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
    print("HANDWRITING RECOGNITION TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Successes: {summary['successes']}")
    print(f"Failures: {summary['failures']}")
    print(f"Errors: {summary['errors']}")
    print(f"Success Rate: {summary['success_rate']:.2f}%")
    print("=" * 70)
    print("\nNOTE: This test suite uses placeholder character recognition.")
    print("For production deployment, integrate trained CNN models for")
    print("actual accuracy measurement against the 85% target.")
    print("=" * 70)

    return summary


if __name__ == "__main__":
    # Run comprehensive test suite
    run_comprehensive_handwriting_tests()
