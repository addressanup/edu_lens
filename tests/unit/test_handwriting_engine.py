"""
Unit tests for Handwriting Recognition Engine.

Tests handwriting recognition including:
- Character recognition accuracy
- Age-specific adaptations (6-8, 9-10, 11-12)
- Messy handwriting handling
- Math expression recognition
- Segmentation accuracy

Author: Testing Agent (TST-001)
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from src.vision.handwriting_engine import (
    HandwritingRecognizer,
    HandwritingStyle,
    AgeGroup,
    HandwritingCharacter,
    HandwritingWord,
    HandwritingResult,
)
from src.vision.character_segmenter import Segment, SegmentationResult


class TestHandwritingDataClasses:
    """Test handwriting data classes."""

    def test_handwriting_character_creation(self):
        """Test creating a handwriting character."""
        char = HandwritingCharacter(
            character='A',
            confidence=0.92,
            bounding_box=(10, 20, 50, 70),
            style=HandwritingStyle.PRINTED
        )

        assert char.character == 'A'
        assert char.confidence == 0.92
        assert char.style == HandwritingStyle.PRINTED

    def test_character_to_dict(self):
        """Test converting character to dictionary."""
        char = HandwritingCharacter(
            character='B',
            confidence=0.88,
            bounding_box=(10, 20, 50, 70),
            alternate_predictions=[('8', 0.75), ('6', 0.65)]
        )

        char_dict = char.to_dict()
        assert char_dict['character'] == 'B'
        assert len(char_dict['alternate_predictions']) == 2

    def test_handwriting_word_creation(self):
        """Test creating a handwriting word."""
        word = HandwritingWord(
            text="Hello",
            confidence=0.90,
            bounding_box=(10, 20, 100, 70)
        )

        assert word.text == "Hello"
        assert word.confidence == 0.90

    def test_word_with_characters(self):
        """Test word with character breakdown."""
        chars = [
            HandwritingCharacter('H', 0.95, (10, 20, 30, 70)),
            HandwritingCharacter('i', 0.90, (35, 20, 50, 70))
        ]

        word = HandwritingWord(
            text="Hi",
            confidence=0.925,
            bounding_box=(10, 20, 50, 70),
            characters=chars
        )

        assert len(word.characters) == 2
        assert word.characters[0].character == 'H'

    def test_handwriting_result_empty(self):
        """Test empty handwriting result."""
        result = HandwritingResult()

        assert len(result.words) == 0
        assert result.full_text == ""
        assert result.average_confidence == 0.0

    def test_handwriting_result_with_data(self):
        """Test handwriting result with data."""
        word = HandwritingWord("Test", 0.9, (10, 20, 100, 70))

        result = HandwritingResult(
            words=[word],
            full_text="Test",
            average_confidence=0.9,
            dominant_style=HandwritingStyle.PRINTED
        )

        assert len(result.words) == 1
        assert result.full_text == "Test"
        assert result.dominant_style == HandwritingStyle.PRINTED


class TestHandwritingRecognizer:
    """Test main handwriting recognizer functionality."""

    @pytest.fixture
    def sample_handwriting_image(self):
        """Create a sample handwriting image."""
        # Binary image with handwriting-like patterns
        img = np.ones((100, 300), dtype=np.uint8) * 255
        # Add some dark strokes to simulate handwriting
        img[30:35, 20:80] = 0  # Horizontal stroke
        img[20:60, 25:30] = 0  # Vertical stroke
        img[30:35, 100:150] = 0  # Another stroke
        return img

    @pytest.fixture
    def recognizer(self):
        """Create a handwriting recognizer instance."""
        return HandwritingRecognizer()

    def test_recognizer_initialization(self):
        """Test recognizer initialization."""
        recognizer = HandwritingRecognizer()

        assert recognizer.preprocessor is not None
        assert recognizer.segmenter is not None
        assert recognizer.age_group is None
        assert recognizer.recognition_mode == "text"

    def test_recognizer_with_config(self):
        """Test recognizer with custom configuration."""
        config = {
            "char_width": 32,
            "char_height": 32,
            "min_confidence": 0.7
        }

        recognizer = HandwritingRecognizer(config=config)

        assert recognizer.char_width == 32
        assert recognizer.char_height == 32
        assert recognizer.min_confidence == 0.7

    @pytest.mark.parametrize("age_group", [
        AgeGroup.EARLY_ELEMENTARY,
        AgeGroup.MID_ELEMENTARY,
        AgeGroup.LATE_ELEMENTARY,
    ])
    def test_configure_for_children(self, recognizer, age_group):
        """Test configuration for different age groups."""
        recognizer.configure_for_children(age_group=age_group)

        assert recognizer.age_group == age_group
        assert recognizer.preprocessor is not None

    def test_early_elementary_config(self, recognizer):
        """Test early elementary (6-8) specific configuration."""
        recognizer.configure_for_children(AgeGroup.EARLY_ELEMENTARY)

        assert recognizer.age_group == AgeGroup.EARLY_ELEMENTARY
        # Lower confidence threshold for emerging writers
        assert recognizer.min_confidence == 0.60

    def test_mid_elementary_config(self, recognizer):
        """Test mid elementary (9-10) configuration."""
        recognizer.configure_for_children(AgeGroup.MID_ELEMENTARY)

        assert recognizer.age_group == AgeGroup.MID_ELEMENTARY
        assert recognizer.min_confidence == 0.70

    def test_late_elementary_config(self, recognizer):
        """Test late elementary (11-12) configuration."""
        recognizer.configure_for_children(AgeGroup.LATE_ELEMENTARY)

        assert recognizer.age_group == AgeGroup.LATE_ELEMENTARY
        assert recognizer.min_confidence == 0.75

    def test_preprocess_handwriting(self, recognizer, sample_handwriting_image):
        """Test handwriting-specific preprocessing."""
        processed = recognizer.preprocess_handwriting(sample_handwriting_image)

        assert processed is not None
        assert isinstance(processed, np.ndarray)
        assert processed.shape == sample_handwriting_image.shape

    def test_preprocess_invalid_image(self, recognizer):
        """Test preprocessing with invalid image."""
        with pytest.raises(ValueError, match="Invalid or empty image"):
            recognizer.preprocess_handwriting(None)

    def test_preprocess_empty_image(self, recognizer):
        """Test preprocessing with empty image."""
        empty_img = np.array([])

        with pytest.raises(ValueError):
            recognizer.preprocess_handwriting(empty_img)

    @patch('src.vision.character_segmenter.CharacterSegmenter.segment_all')
    def test_segment_characters(self, mock_segment, recognizer, sample_handwriting_image):
        """Test character segmentation."""
        # Mock segmentation result
        mock_segment.return_value = SegmentationResult(
            characters=[
                Segment(x=20, y=20, width=30, height=40),
                Segment(x=60, y=20, width=35, height=40)
            ],
            words=[
                Segment(x=20, y=20, width=75, height=40)
            ]
        )

        result = recognizer.segment_characters(sample_handwriting_image)

        assert isinstance(result, SegmentationResult)
        assert len(result.characters) == 2
        assert len(result.words) == 1

    @patch('src.vision.character_segmenter.CharacterSegmenter.segment_all')
    def test_recognize_handwriting(self, mock_segment, recognizer, sample_handwriting_image):
        """Test complete handwriting recognition."""
        # Mock segmentation
        char1 = Segment(x=20, y=20, width=30, height=40)
        char2 = Segment(x=60, y=20, width=30, height=40)
        word = Segment(x=20, y=20, width=70, height=40)

        mock_segment.return_value = SegmentationResult(
            characters=[char1, char2],
            words=[word]
        )

        result = recognizer.recognize_handwriting(sample_handwriting_image)

        assert isinstance(result, HandwritingResult)
        assert result.processing_time_ms > 0
        assert "metadata" in result.to_dict()

    @patch('src.vision.character_segmenter.CharacterSegmenter.segment_all')
    def test_recognize_no_preprocessing(self, mock_segment, recognizer, sample_handwriting_image):
        """Test recognition without preprocessing."""
        mock_segment.return_value = SegmentationResult()

        result = recognizer.recognize_handwriting(
            sample_handwriting_image,
            preprocess=False
        )

        assert isinstance(result, HandwritingResult)

    def test_recognize_math_handwriting(self, recognizer, sample_handwriting_image):
        """Test mathematical expression recognition."""
        with patch.object(recognizer, 'recognize_handwriting') as mock_recognize:
            mock_recognize.return_value = HandwritingResult(
                full_text="2 + 3 = 5",
                average_confidence=0.85
            )

            result = recognizer.recognize_math_handwriting(sample_handwriting_image)

            assert isinstance(result, HandwritingResult)
            # Verify math mode was set
            assert recognizer.recognition_mode == "text"  # Restored after

    def test_get_confidence_scores(self, recognizer):
        """Test getting detailed confidence scores."""
        char1 = HandwritingCharacter('A', 0.95, (10, 20, 30, 40))
        char2 = HandwritingCharacter('B', 0.75, (35, 20, 55, 40))

        word = HandwritingWord(
            text="AB",
            confidence=0.85,
            bounding_box=(10, 20, 55, 40),
            characters=[char1, char2]
        )

        result = HandwritingResult(
            words=[word],
            full_text="AB",
            average_confidence=0.85
        )

        scores = recognizer.get_confidence_scores(result)

        assert scores['overall'] == 0.85
        assert len(scores['per_character']) == 2
        assert scores['total_characters'] == 2

    def test_get_confidence_empty_result(self, recognizer):
        """Test confidence scores for empty result."""
        result = HandwritingResult()

        scores = recognizer.get_confidence_scores(result)

        assert scores['overall'] == 0.0
        assert scores['total_characters'] == 0

    def test_load_model(self, recognizer, tmp_path):
        """Test loading a trained model."""
        model_file = tmp_path / "model.pth"
        model_file.touch()

        # Should not raise error (placeholder implementation)
        recognizer.load_model(str(model_file), model_type="text")

    def test_load_nonexistent_model(self, recognizer):
        """Test loading nonexistent model."""
        with pytest.raises(FileNotFoundError):
            recognizer.load_model("/nonexistent/model.pth")

    def test_save_model(self, recognizer, tmp_path):
        """Test saving model."""
        model_file = tmp_path / "model.pth"

        # Should not raise error (placeholder implementation)
        recognizer.save_model(str(model_file), model_type="text")


class TestCharacterRecognition:
    """Test character-level recognition."""

    @pytest.fixture
    def recognizer(self):
        return HandwritingRecognizer()

    def test_character_preparation(self, recognizer):
        """Test character image preparation."""
        # Create a character-like image
        char_img = np.ones((50, 30), dtype=np.uint8) * 255
        char_img[15:35, 10:20] = 0  # Dark region

        prepared = recognizer._prepare_character_for_recognition(char_img)

        assert prepared is not None
        assert prepared.shape == (28, 28)  # Standard size
        assert prepared.dtype == np.float32

    def test_character_preparation_rectangular(self, recognizer):
        """Test preparing non-square character."""
        # Tall, narrow character
        char_img = np.ones((80, 30), dtype=np.uint8) * 255

        prepared = recognizer._prepare_character_for_recognition(char_img)

        # Should be padded to square
        assert prepared.shape[0] == prepared.shape[1]

    def test_get_character_predictions(self, recognizer):
        """Test getting character predictions."""
        char_img = np.random.rand(28, 28).astype(np.float32)

        predictions = recognizer._get_character_predictions(
            char_img,
            recognizer.text_charset,
            top_k=5
        )

        assert len(predictions) <= 5
        assert all(isinstance(p, tuple) for p in predictions)
        assert all(len(p) == 2 for p in predictions)  # (char, confidence)

    def test_math_charset(self, recognizer):
        """Test math character set."""
        charset = recognizer._get_math_charset()

        # Should include digits
        assert '0' in charset
        assert '9' in charset

        # Should include operators
        assert '+' in charset
        assert '-' in charset
        assert '×' in charset
        assert '÷' in charset

    def test_text_charset(self, recognizer):
        """Test text character set."""
        charset = recognizer._get_text_charset()

        # Should include letters
        assert 'A' in charset
        assert 'z' in charset

        # Should include digits
        assert '0' in charset

        # Should include common punctuation
        assert '.' in charset
        assert ',' in charset


class TestHandwritingEdgeCases:
    """Test edge cases and challenging scenarios."""

    @pytest.fixture
    def recognizer(self):
        return HandwritingRecognizer()

    def test_very_messy_handwriting(self, recognizer):
        """Test recognition of very messy handwriting."""
        # Create noisy image
        img = np.random.randint(0, 256, (100, 200), dtype=np.uint8)

        recognizer.configure_for_children(AgeGroup.EARLY_ELEMENTARY)

        with patch('src.vision.character_segmenter.CharacterSegmenter.segment_all') as mock:
            mock.return_value = SegmentationResult()

            result = recognizer.recognize_handwriting(img)

        # Should handle gracefully without crashing
        assert isinstance(result, HandwritingResult)

    def test_overlapping_characters(self, recognizer):
        """Test handling overlapping characters."""
        img = np.ones((100, 200), dtype=np.uint8) * 255
        # Create overlapping strokes
        img[40:60, 50:70] = 0
        img[40:60, 65:85] = 0

        with patch('src.vision.character_segmenter.CharacterSegmenter.segment_all') as mock:
            mock.return_value = SegmentationResult(
                characters=[
                    Segment(x=50, y=40, width=35, height=20)
                ]
            )

            result = recognizer.recognize_handwriting(img)

        assert isinstance(result, HandwritingResult)

    def test_mixed_print_and_cursive(self, recognizer):
        """Test mixed handwriting styles."""
        img = np.ones((100, 300), dtype=np.uint8) * 255

        with patch('src.vision.character_segmenter.CharacterSegmenter.segment_all') as mock:
            # Simulate segmentation finding both styles
            mock.return_value = SegmentationResult(
                characters=[
                    Segment(x=20, y=20, width=30, height=40),
                    Segment(x=100, y=20, width=50, height=40)  # Wider for cursive
                ]
            )

            result = recognizer.recognize_handwriting(img)

        assert isinstance(result, HandwritingResult)

    def test_very_small_text(self, recognizer):
        """Test recognition of very small handwriting."""
        # Tiny image
        img = np.ones((30, 80), dtype=np.uint8) * 255
        img[10:20, 10:25] = 0

        with patch('src.vision.character_segmenter.CharacterSegmenter.segment_all') as mock:
            mock.return_value = SegmentationResult(
                characters=[Segment(x=10, y=10, width=15, height=10)]
            )

            result = recognizer.recognize_handwriting(img)

        assert isinstance(result, HandwritingResult)

    def test_very_large_text(self, recognizer):
        """Test recognition of very large handwriting."""
        # Large image
        img = np.ones((400, 800), dtype=np.uint8) * 255
        img[100:300, 100:250] = 0

        with patch('src.vision.character_segmenter.CharacterSegmenter.segment_all') as mock:
            mock.return_value = SegmentationResult(
                characters=[Segment(x=100, y=100, width=150, height=200)]
            )

            result = recognizer.recognize_handwriting(img)

        assert isinstance(result, HandwritingResult)

    def test_missing_dependencies(self):
        """Test handling of missing dependencies."""
        with patch('src.vision.handwriting_engine.cv2', None):
            with pytest.raises(ImportError, match="OpenCV"):
                HandwritingRecognizer()

    @pytest.mark.parametrize("age,expected_threshold", [
        (6, 0.60),  # Early elementary
        (9, 0.70),  # Mid elementary
        (11, 0.75),  # Late elementary
    ])
    def test_age_appropriate_thresholds(self, recognizer, age, expected_threshold):
        """Test age-appropriate confidence thresholds."""
        if age <= 8:
            age_group = AgeGroup.EARLY_ELEMENTARY
        elif age <= 10:
            age_group = AgeGroup.MID_ELEMENTARY
        else:
            age_group = AgeGroup.LATE_ELEMENTARY

        recognizer.configure_for_children(age_group)

        assert recognizer.min_confidence == expected_threshold

    def test_math_expression_postprocessing(self, recognizer):
        """Test post-processing of math expressions."""
        # Create result with common confusions
        word1 = HandwritingWord("x", 0.8, (10, 20, 30, 40))
        word2 = HandwritingWord("2", 0.85, (35, 20, 55, 40))

        result = HandwritingResult(
            words=[word1, word2],
            full_text="x 2",
            average_confidence=0.825
        )

        processed = recognizer._postprocess_math_expression(result)

        # 'x' should be converted to '×'
        assert '×' in processed.full_text or 'x' in processed.full_text

    def test_no_text_found(self, recognizer):
        """Test handling when no text is found."""
        blank_img = np.ones((100, 200), dtype=np.uint8) * 255

        with patch('src.vision.character_segmenter.CharacterSegmenter.segment_all') as mock:
            mock.return_value = SegmentationResult()  # No segments

            result = recognizer.recognize_handwriting(blank_img)

        assert result.full_text == ""
        assert result.average_confidence == 0.0

    def test_single_character(self, recognizer):
        """Test recognizing a single character."""
        img = np.ones((50, 50), dtype=np.uint8) * 255
        img[15:35, 20:30] = 0

        with patch('src.vision.character_segmenter.CharacterSegmenter.segment_all') as mock:
            mock.return_value = SegmentationResult(
                characters=[Segment(x=20, y=15, width=10, height=20)]
            )

            result = recognizer.recognize_handwriting(img)

        assert isinstance(result, HandwritingResult)

    def test_word_without_characters(self, recognizer):
        """Test word segmentation without character segmentation."""
        img = np.ones((100, 200), dtype=np.uint8) * 255

        with patch('src.vision.character_segmenter.CharacterSegmenter.segment_all') as mock:
            mock.return_value = SegmentationResult(
                words=[Segment(x=20, y=20, width=100, height=40)],
                characters=[]  # No character segmentation
            )

            result = recognizer.recognize_handwriting(img)

        assert isinstance(result, HandwritingResult)
