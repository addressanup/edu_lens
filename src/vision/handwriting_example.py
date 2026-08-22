"""
Example Usage of EduLens Handwriting Recognition Engine

This script demonstrates how to use the handwriting recognition system
for different age groups and use cases.

Author: Vision Processing Agent (VIS-001)
"""

from pathlib import Path

import cv2
import numpy as np

from src.vision.character_segmenter import CharacterSegmenter
from src.vision.handwriting_engine import AgeGroup, HandwritingRecognizer, HandwritingStyle


def example_basic_recognition():
    """Example: Basic handwriting recognition."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Basic Handwriting Recognition")
    print("=" * 70)

    # Initialize recognizer
    recognizer = HandwritingRecognizer()

    # Configure for middle elementary (ages 9-10)
    recognizer.configure_for_children(AgeGroup.MID_ELEMENTARY)

    # Create sample image (in production, load from file)
    # image = cv2.imread("path/to/handwriting.jpg")

    # For demo, create synthetic image
    image = np.ones((200, 800, 3), dtype=np.uint8) * 255
    cv2.putText(
        image,
        "Hello World",
        (50, 100),
        cv2.FONT_HERSHEY_SCRIPT_SIMPLEX,
        2.0,
        (0, 0, 0),
        2,
        cv2.LINE_AA,
    )

    # Recognize handwriting
    result = recognizer.recognize_handwriting(image)

    # Display results
    print(f"Recognized Text: {result.full_text}")
    print(f"Confidence: {result.average_confidence:.2%}")
    print(f"Words Detected: {len(result.words)}")
    print(f"Processing Time: {result.processing_time_ms:.2f}ms")
    print(f"Style: {result.dominant_style.value}")


def example_age_specific_recognition():
    """Example: Age-specific handwriting recognition."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Age-Specific Recognition")
    print("=" * 70)

    # Create recognizer
    recognizer = HandwritingRecognizer()

    # Sample text
    sample_text = "The cat sat"

    # Test with different age groups
    age_groups = [AgeGroup.EARLY_ELEMENTARY, AgeGroup.MID_ELEMENTARY, AgeGroup.LATE_ELEMENTARY]

    for age_group in age_groups:
        print(f"\nAge Group: {age_group.value}")

        # Configure for age group
        recognizer.configure_for_children(age_group)

        # Create sample image
        image = np.ones((200, 800, 3), dtype=np.uint8) * 255
        cv2.putText(
            image,
            sample_text,
            (50, 100),
            cv2.FONT_HERSHEY_SCRIPT_SIMPLEX,
            1.5,
            (0, 0, 0),
            2,
            cv2.LINE_AA,
        )

        # Recognize
        result = recognizer.recognize_handwriting(image)

        print(f"  Recognized: {result.full_text}")
        print(f"  Confidence: {result.average_confidence:.2%}")
        print(f"  Min Confidence Threshold: {recognizer.min_confidence:.2%}")


def example_math_recognition():
    """Example: Mathematical expression recognition."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Mathematical Expression Recognition")
    print("=" * 70)

    # Initialize recognizer
    recognizer = HandwritingRecognizer()
    recognizer.configure_for_children(AgeGroup.MID_ELEMENTARY)

    # Sample math expressions
    expressions = ["2 + 2 = 4", "10 - 5 = 5", "3 × 4 = 12"]

    for expr in expressions:
        print(f"\nExpression: {expr}")

        # Create sample image
        image = np.ones((150, 600, 3), dtype=np.uint8) * 255
        cv2.putText(image, expr, (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2, cv2.LINE_AA)

        # Recognize math handwriting
        result = recognizer.recognize_math_handwriting(image)

        print(f"  Recognized: {result.full_text}")
        print(f"  Confidence: {result.average_confidence:.2%}")


def example_confidence_analysis():
    """Example: Detailed confidence score analysis."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Confidence Score Analysis")
    print("=" * 70)

    # Initialize recognizer
    recognizer = HandwritingRecognizer()
    recognizer.configure_for_children(AgeGroup.MID_ELEMENTARY)

    # Create sample
    image = np.ones((200, 800, 3), dtype=np.uint8) * 255
    cv2.putText(
        image,
        "Reading Test",
        (50, 100),
        cv2.FONT_HERSHEY_SCRIPT_SIMPLEX,
        2.0,
        (0, 0, 0),
        2,
        cv2.LINE_AA,
    )

    # Recognize
    result = recognizer.recognize_handwriting(image)

    # Get detailed confidence scores
    confidence_scores = recognizer.get_confidence_scores(result)

    print(f"Overall Confidence: {confidence_scores['overall']:.2%}")
    print(f"High Confidence Ratio: {confidence_scores['high_confidence_ratio']:.2%}")
    print(f"Low Confidence Count: {confidence_scores['low_confidence_count']}")
    print(f"Total Characters: {confidence_scores['total_characters']}")

    print("\nPer-Word Confidence:")
    for word_score in confidence_scores["per_word"]:
        print(f"  '{word_score['text']}': {word_score['confidence']:.2%}")


def example_character_segmentation():
    """Example: Character segmentation demonstration."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Character Segmentation")
    print("=" * 70)

    # Initialize segmenter
    segmenter = CharacterSegmenter()

    # Create sample text image
    image = np.ones((200, 800, 3), dtype=np.uint8) * 255
    cv2.putText(
        image,
        "Hello World",
        (50, 100),
        cv2.FONT_HERSHEY_SCRIPT_SIMPLEX,
        2.0,
        (0, 0, 0),
        2,
        cv2.LINE_AA,
    )

    # Perform segmentation
    result = segmenter.segment_all(
        image, segment_lines=True, segment_words=True, segment_characters=True
    )

    print(f"Lines Detected: {len(result.lines)}")
    print(f"Words Detected: {len(result.words)}")
    print(f"Characters Detected: {len(result.characters)}")

    print("\nWord Segments:")
    for i, word in enumerate(result.words, 1):
        print(f"  Word {i}: Position ({word.x}, {word.y}), " f"Size {word.width}x{word.height}")

    print("\nCharacter Segments:")
    for i, char in enumerate(result.characters[:10], 1):  # Show first 10
        print(f"  Char {i}: Position ({char.x}, {char.y}), " f"Size {char.width}x{char.height}")


def example_preprocessing():
    """Example: Preprocessing pipeline demonstration."""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Handwriting Preprocessing")
    print("=" * 70)

    # Initialize recognizer
    recognizer = HandwritingRecognizer()

    # Create noisy, rotated sample
    image = np.ones((200, 800, 3), dtype=np.uint8) * 255

    # Add text
    cv2.putText(
        image,
        "Noisy Text",
        (50, 100),
        cv2.FONT_HERSHEY_SCRIPT_SIMPLEX,
        2.0,
        (0, 0, 0),
        2,
        cv2.LINE_AA,
    )

    # Add noise
    noise = np.random.normal(0, 10, image.shape).astype(np.int16)
    image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Rotate
    center = (image.shape[1] // 2, image.shape[0] // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, 5, 1.0)
    image = cv2.warpAffine(image, rotation_matrix, (image.shape[1], image.shape[0]))

    print("Original Image: Noisy and rotated")
    print(f"  Shape: {image.shape}")
    print(f"  Mean pixel value: {np.mean(image):.2f}")

    # Preprocess
    preprocessed = recognizer.preprocess_handwriting(image)

    print("\nPreprocessed Image:")
    print(f"  Shape: {preprocessed.shape}")
    print(f"  Mean pixel value: {np.mean(preprocessed):.2f}")
    print("  Applied: Deskew, Denoise, Contrast Enhancement, Binarization")


def example_batch_processing():
    """Example: Batch processing multiple images."""
    print("\n" + "=" * 70)
    print("EXAMPLE 7: Batch Processing")
    print("=" * 70)

    # Initialize recognizer
    recognizer = HandwritingRecognizer()
    recognizer.configure_for_children(AgeGroup.MID_ELEMENTARY)

    # Sample words
    words = ["cat", "dog", "sun", "run", "jump"]

    results = []

    print("Processing batch of handwriting samples...\n")

    for i, word in enumerate(words, 1):
        # Create sample
        image = np.ones((150, 400, 3), dtype=np.uint8) * 255
        cv2.putText(
            image, word, (50, 80), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 1.5, (0, 0, 0), 2, cv2.LINE_AA
        )

        # Recognize
        result = recognizer.recognize_handwriting(image)
        results.append(result)

        print(f"Sample {i}: '{word}'")
        print(f"  Recognized: {result.full_text}")
        print(f"  Confidence: {result.average_confidence:.2%}")
        print(f"  Time: {result.processing_time_ms:.2f}ms\n")

    # Summary statistics
    avg_confidence = np.mean([r.average_confidence for r in results])
    total_time = sum([r.processing_time_ms for r in results])

    print("Batch Summary:")
    print(f"  Total Samples: {len(results)}")
    print(f"  Average Confidence: {avg_confidence:.2%}")
    print(f"  Total Processing Time: {total_time:.2f}ms")
    print(f"  Average Time per Sample: {total_time/len(results):.2f}ms")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("EDULENS HANDWRITING RECOGNITION - EXAMPLE USAGE")
    print("=" * 70)

    try:
        # Run examples
        example_basic_recognition()
        example_age_specific_recognition()
        example_math_recognition()
        example_confidence_analysis()
        example_character_segmentation()
        example_preprocessing()
        example_batch_processing()

        print("\n" + "=" * 70)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print("\nNOTE: These examples use placeholder character recognition.")
        print("For production deployment, integrate trained CNN models.")
        print("=" * 70)

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
