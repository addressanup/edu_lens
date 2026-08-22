"""
Example Usage Script for EduLens OCR Engine

This script demonstrates how to use the OCR engine for processing
educational materials.

Author: Vision Processing Agent (VIS-001)
"""

from pathlib import Path

import cv2
import numpy as np

from src.vision.ocr_engine import DocumentType, OCRBackend, OCREngine
from src.vision.preprocessing import ImagePreprocessor


def example_basic_ocr():
    """Example: Basic OCR usage."""
    print("=" * 70)
    print("Example 1: Basic OCR")
    print("=" * 70)

    # Initialize OCR engine
    engine = OCREngine(backend=OCRBackend.TESSERACT)

    # Create a simple test image (you would normally load from file)
    test_image = np.ones((200, 800, 3), dtype=np.uint8) * 255
    cv2.putText(
        test_image,
        "The quick brown fox jumps over the lazy dog",
        (50, 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (0, 0, 0),
        2,
        cv2.LINE_AA,
    )

    # Extract text
    result = engine.extract_structured_content(test_image)

    # Print results
    print(f"Extracted Text: {result.full_text}")
    print(f"Average Confidence: {result.average_confidence:.2%}")
    print(f"Number of Regions: {len(result.regions)}")
    print(f"Processing Time: {result.processing_time_ms:.2f}ms")
    print()


def example_educational_mode():
    """Example: Educational mode configuration."""
    print("=" * 70)
    print("Example 2: Educational Mode for Worksheets")
    print("=" * 70)

    # Initialize engine
    engine = OCREngine()

    # Configure for educational content
    engine.configure_for_education(
        document_type=DocumentType.WORKSHEET, enable_math_symbols=True, enable_layout_analysis=True
    )

    # Create worksheet-like image
    worksheet = np.ones((600, 800, 3), dtype=np.uint8) * 255

    # Add grid lines (common in worksheets)
    for i in range(0, 600, 50):
        cv2.line(worksheet, (0, i), (800, i), (200, 200, 200), 1)

    # Add questions
    questions = [
        "1. What is 2 + 2?",
        "2. How many apples are there?",
        "3. Circle the correct answer",
    ]

    y_offset = 30
    for question in questions:
        cv2.putText(
            worksheet,
            question,
            (30, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 0),
            2,
            cv2.LINE_AA,
        )
        y_offset += 80

    # Process worksheet
    result = engine.extract_structured_content(worksheet)

    print(f"Extracted Text:\n{result.full_text}")
    print(f"\nDocument Type: {result.document_type.value if result.document_type else 'None'}")
    print(f"Number of Text Regions: {len(result.regions)}")
    print()


def example_preprocessing():
    """Example: Custom preprocessing pipeline."""
    print("=" * 70)
    print("Example 3: Custom Preprocessing")
    print("=" * 70)

    # Create preprocessor with custom config
    config = {
        "deskew": True,
        "denoise": True,
        "denoise_method": "bilateral",
        "enhance_contrast": True,
        "contrast_method": "clahe",
        "binarization_method": "adaptive",
        "adaptive_block_size": 11,
        "adaptive_c": 2,
    }

    preprocessor = ImagePreprocessor(config=config)

    # Create test image with noise and rotation
    test_image = np.ones((200, 800, 3), dtype=np.uint8) * 255
    cv2.putText(
        test_image,
        "Preprocessing Example",
        (100, 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.5,
        (0, 0, 0),
        2,
        cv2.LINE_AA,
    )

    # Add noise
    noise = np.random.normal(0, 25, test_image.shape).astype(np.uint8)
    noisy_image = cv2.add(test_image, noise)

    # Apply preprocessing
    processed = preprocessor.preprocess(noisy_image)

    print("Preprocessing steps applied:")
    print("  - Deskewing (rotation correction)")
    print("  - Bilateral noise reduction")
    print("  - CLAHE contrast enhancement")
    print("  - Adaptive binarization")
    print(f"\nOriginal image shape: {noisy_image.shape}")
    print(f"Processed image shape: {processed.shape}")
    print()


def example_structured_output():
    """Example: Working with structured output and bounding boxes."""
    print("=" * 70)
    print("Example 4: Structured Output with Bounding Boxes")
    print("=" * 70)

    # Initialize engine
    engine = OCREngine()

    # Create test image with multiple text regions
    image = np.ones((300, 800, 3), dtype=np.uint8) * 255

    # Add text at different locations
    texts = [
        ("Title: Animals", (50, 50)),
        ("Dogs are friendly animals", (50, 120)),
        ("Cats are independent", (50, 180)),
        ("Birds can fly", (50, 240)),
    ]

    for text, (x, y) in texts:
        cv2.putText(image, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2, cv2.LINE_AA)

    # Extract structured content
    result = engine.extract_structured_content(image)

    print(f"Total Regions Detected: {len(result.regions)}\n")

    # Print each region with details
    for i, region in enumerate(result.regions, 1):
        print(f"Region {i}:")
        print(f"  Text: {region.text}")
        print(f"  Confidence: {region.confidence:.2%}")
        print(f"  Bounding Box: {region.bounding_box.to_dict()}")
        print()


def example_document_types():
    """Example: Processing different document types."""
    print("=" * 70)
    print("Example 5: Different Document Types")
    print("=" * 70)

    engine = OCREngine()

    # Create sample images for different document types
    document_types = [DocumentType.TEXTBOOK, DocumentType.WORKSHEET, DocumentType.FLASHCARD]

    for doc_type in document_types:
        # Configure for document type
        engine.configure_for_education(document_type=doc_type)

        # Create sample image
        image = np.ones((200, 800, 3), dtype=np.uint8) * 255
        cv2.putText(
            image,
            f"Sample {doc_type.value} content",
            (100, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 0, 0),
            2,
            cv2.LINE_AA,
        )

        # Process
        result = engine.extract_structured_content(image)

        print(f"{doc_type.value.upper()}:")
        print(f"  Recognized: {result.full_text}")
        print(f"  Confidence: {result.average_confidence:.2%}")
        print()


def example_accuracy_measurement():
    """Example: Measuring OCR accuracy."""
    print("=" * 70)
    print("Example 6: Accuracy Measurement")
    print("=" * 70)

    from tests.vision.test_ocr_accuracy import AccuracyMetrics

    engine = OCREngine()
    metrics = AccuracyMetrics()

    # Test cases with ground truth
    test_cases = [
        "The cat sat on the mat",
        "1 2 3 4 5 6 7 8 9 10",
        "What is your name?",
        "Red blue green yellow",
    ]

    total_accuracy = 0.0

    for ground_truth in test_cases:
        # Create test image
        image = np.ones((150, 800, 3), dtype=np.uint8) * 255
        cv2.putText(
            image, ground_truth, (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2, cv2.LINE_AA
        )

        # Recognize
        result = engine.extract_structured_content(image)

        # Calculate accuracy
        accuracy = metrics.calculate_character_accuracy(ground_truth, result.full_text)

        total_accuracy += accuracy

        print(f"Ground Truth: '{ground_truth}'")
        print(f"Recognized:   '{result.full_text}'")
        print(f"Accuracy:     {accuracy:.2f}%")
        print()

    avg_accuracy = total_accuracy / len(test_cases)
    print(f"Average Accuracy: {avg_accuracy:.2f}%")
    print()


def main():
    """Run all examples."""
    print("\n")
    print("*" * 70)
    print("EduLens OCR Engine - Usage Examples")
    print("*" * 70)
    print("\n")

    try:
        # Run examples
        example_basic_ocr()
        example_educational_mode()
        example_preprocessing()
        example_structured_output()
        example_document_types()
        example_accuracy_measurement()

        print("=" * 70)
        print("All examples completed successfully!")
        print("=" * 70)
        print("\nFor more information, see:")
        print("  - Documentation: src/vision/README.md")
        print("  - Configuration: configs/vision/ocr_config.yaml")
        print("  - Tests: tests/vision/test_ocr_accuracy.py")
        print()

    except ImportError as e:
        print(f"\nError: Missing dependency - {e}")
        print("\nPlease install required packages:")
        print("  pip install opencv-python numpy pytesseract scipy")
        print("\nAnd ensure Tesseract OCR is installed:")
        print("  macOS: brew install tesseract")
        print("  Ubuntu: sudo apt-get install tesseract-ocr")
        print("  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
        print()

    except Exception as e:
        print(f"\nError occurred: {e}")
        print("Please check the error message and try again.")
        print()


if __name__ == "__main__":
    main()
