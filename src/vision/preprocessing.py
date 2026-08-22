"""
Image Preprocessing Utilities for EduLens OCR

This module provides comprehensive image preprocessing capabilities optimized
for elementary educational materials. It includes operations for:
- Deskewing (rotation correction)
- Contrast normalization
- Noise reduction
- Binarization for text enhancement

Author: Vision Processing Agent (VIS-001)
"""

import logging
from typing import Any, Dict, Optional, Tuple

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from scipy import ndimage
except ImportError:
    ndimage = None


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """
    Comprehensive image preprocessing for OCR optimization.

    This class provides a complete preprocessing pipeline specifically
    designed for educational materials. It handles various image quality
    issues commonly found in scanned or photographed documents.

    Attributes:
        config: Configuration dictionary for preprocessing parameters
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the image preprocessor.

        Args:
            config: Configuration dictionary with preprocessing parameters
        """
        self.config = config or {}
        self._validate_dependencies()

        logger.debug("ImagePreprocessor initialized")

    def _validate_dependencies(self) -> None:
        """Validate that required dependencies are available."""
        if cv2 is None:
            raise ImportError("OpenCV (cv2) is required. Install with: pip install opencv-python")

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Apply complete preprocessing pipeline.

        This method applies all enabled preprocessing steps in the optimal order:
        1. Deskewing (if enabled)
        2. Noise reduction (if enabled)
        3. Contrast enhancement (if enabled)
        4. Sharpening (if enabled)
        5. Binarization (if enabled)

        Args:
            image: Input image as numpy array

        Returns:
            Preprocessed image as numpy array

        Raises:
            ValueError: If image is invalid
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        processed = image.copy()

        # Apply preprocessing steps based on configuration
        if self.config.get("deskew", True):
            processed = self.deskew(processed)

        if self.config.get("denoise", True):
            processed = self.denoise(processed)

        if self.config.get("enhance_contrast", True):
            processed = self.enhance_contrast(processed)

        if self.config.get("sharpen", False):
            processed = self.sharpen(processed)

        if self.config.get("binarization_method"):
            processed = self.binarize(processed)

        # Remove lines if enabled (useful for worksheets)
        if self.config.get("remove_lines", False):
            processed = self.remove_lines(processed)

        # Resize if scale factor is specified
        if self.config.get("resize_scale"):
            scale = self.config["resize_scale"]
            processed = self.resize(processed, scale)

        return processed

    def convert_to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """
        Convert image to grayscale.

        Args:
            image: Input image (can be grayscale or color)

        Returns:
            Grayscale image
        """
        if len(image.shape) == 2:
            # Already grayscale
            return image
        elif len(image.shape) == 3:
            if image.shape[2] == 1:
                # Single channel, just squeeze
                return image.squeeze()
            else:
                # Convert BGR/RGB to grayscale
                return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            raise ValueError(f"Unexpected image shape: {image.shape}")

    def deskew(self, image: np.ndarray, max_angle: float = 10.0) -> np.ndarray:
        """
        Correct image skew/rotation using projection profile method.

        This method detects and corrects rotation in scanned or photographed
        documents. It's particularly useful for images captured at an angle.

        Args:
            image: Input image as numpy array
            max_angle: Maximum rotation angle to consider (degrees)

        Returns:
            Deskewed image

        Raises:
            ValueError: If image is invalid
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        try:
            # Convert to grayscale if needed
            gray = self.convert_to_grayscale(image)

            # Calculate skew angle
            angle = self._detect_skew_angle(gray, max_angle)

            if abs(angle) < 0.1:  # No significant skew
                logger.debug("No significant skew detected")
                return image

            # Rotate image to correct skew
            deskewed = self._rotate_image(image, angle)

            logger.debug(f"Deskewed image by {angle:.2f} degrees")
            return deskewed

        except Exception as e:
            logger.warning(f"Deskewing failed: {e}. Returning original image.")
            return image

    def _detect_skew_angle(self, gray_image: np.ndarray, max_angle: float) -> float:
        """
        Detect skew angle using Hough line transform.

        Args:
            gray_image: Grayscale image
            max_angle: Maximum angle to consider

        Returns:
            Detected skew angle in degrees
        """
        # Apply edge detection
        edges = cv2.Canny(gray_image, 50, 150, apertureSize=3)

        # Detect lines using Hough transform
        lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)

        if lines is None or len(lines) == 0:
            return 0.0

        # Calculate angles
        angles = []
        for line in lines:
            rho, theta = line[0]
            angle = np.degrees(theta) - 90

            # Filter angles within max_angle range
            if abs(angle) <= max_angle:
                angles.append(angle)

        if not angles:
            return 0.0

        # Use median angle to be robust against outliers
        skew_angle = np.median(angles)

        return float(skew_angle)

    def _rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """
        Rotate image by specified angle.

        Args:
            image: Input image
            angle: Rotation angle in degrees

        Returns:
            Rotated image
        """
        height, width = image.shape[:2]
        center = (width // 2, height // 2)

        # Get rotation matrix
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

        # Calculate new image dimensions to prevent cropping
        cos = np.abs(rotation_matrix[0, 0])
        sin = np.abs(rotation_matrix[0, 1])

        new_width = int((height * sin) + (width * cos))
        new_height = int((height * cos) + (width * sin))

        # Adjust rotation matrix for new dimensions
        rotation_matrix[0, 2] += (new_width / 2) - center[0]
        rotation_matrix[1, 2] += (new_height / 2) - center[1]

        # Perform rotation with white background
        rotated = cv2.warpAffine(
            image,
            rotation_matrix,
            (new_width, new_height),
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255),
        )

        return rotated

    def denoise(
        self, image: np.ndarray, method: str = "bilateral", strength: int = 10
    ) -> np.ndarray:
        """
        Reduce noise while preserving edges.

        Args:
            image: Input image
            method: Denoising method ("bilateral", "gaussian", "median", "nlmeans")
            strength: Denoising strength (higher = more denoising)

        Returns:
            Denoised image

        Raises:
            ValueError: If invalid method specified
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        # Override method from config if specified
        method = self.config.get("denoise_method", method)

        try:
            if method == "bilateral":
                # Bilateral filter preserves edges while smoothing
                denoised = cv2.bilateralFilter(
                    image, d=9, sigmaColor=strength * 7, sigmaSpace=strength * 7
                )

            elif method == "gaussian":
                # Gaussian blur for simple smoothing
                kernel_size = strength if strength % 2 == 1 else strength + 1
                denoised = cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)

            elif method == "median":
                # Median filter good for salt-and-pepper noise
                kernel_size = strength if strength % 2 == 1 else strength + 1
                denoised = cv2.medianBlur(image, kernel_size)

            elif method == "nlmeans":
                # Non-local means denoising (slower but high quality)
                if len(image.shape) == 2:
                    denoised = cv2.fastNlMeansDenoising(
                        image, None, h=strength, templateWindowSize=7, searchWindowSize=21
                    )
                else:
                    denoised = cv2.fastNlMeansDenoisingColored(
                        image,
                        None,
                        h=strength,
                        hColor=strength,
                        templateWindowSize=7,
                        searchWindowSize=21,
                    )

            else:
                raise ValueError(f"Unknown denoising method: {method}")

            logger.debug(f"Applied {method} denoising with strength {strength}")
            return denoised

        except Exception as e:
            logger.warning(f"Denoising failed: {e}. Returning original image.")
            return image

    def enhance_contrast(self, image: np.ndarray, method: str = "clahe") -> np.ndarray:
        """
        Enhance image contrast for better text visibility.

        Args:
            image: Input image
            method: Enhancement method ("clahe", "histogram", "normalize")

        Returns:
            Contrast-enhanced image

        Raises:
            ValueError: If invalid method specified
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        # Override method from config if specified
        method = self.config.get("contrast_method", method)

        try:
            # Convert to grayscale for contrast operations
            is_color = len(image.shape) == 3 and image.shape[2] == 3
            if is_color:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()

            if method == "clahe":
                # CLAHE (Contrast Limited Adaptive Histogram Equalization)
                # Better for documents with varying lighting
                clip_limit = self.config.get("clahe_clip_limit", 2.0)
                tile_size = self.config.get("clahe_tile_size", 8)

                clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
                enhanced = clahe.apply(gray)

            elif method == "histogram":
                # Global histogram equalization
                enhanced = cv2.equalizeHist(gray)

            elif method == "normalize":
                # Normalization to full range
                enhanced = cv2.normalize(gray, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)

            else:
                raise ValueError(f"Unknown contrast enhancement method: {method}")

            # If original was color, convert back
            if is_color:
                enhanced = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)

            logger.debug(f"Applied {method} contrast enhancement")
            return enhanced

        except Exception as e:
            logger.warning(f"Contrast enhancement failed: {e}. Returning original image.")
            return image

    def binarize(self, image: np.ndarray, method: Optional[str] = None) -> np.ndarray:
        """
        Convert image to binary (black and white) for optimal text recognition.

        Args:
            image: Input image
            method: Binarization method ("otsu", "adaptive", "simple")
                   If None, uses config or defaults to "adaptive"

        Returns:
            Binary image

        Raises:
            ValueError: If invalid method specified
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        # Get method from config or parameter
        if method is None:
            method = self.config.get("binarization_method", "adaptive")

        try:
            # Convert to grayscale if needed
            gray = self.convert_to_grayscale(image)

            if method == "otsu":
                # Otsu's method automatically determines optimal threshold
                _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            elif method == "adaptive":
                # Adaptive thresholding - better for varying lighting
                block_size = self.config.get("adaptive_block_size", 11)
                c = self.config.get("adaptive_c", 2)

                binary = cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, c
                )

            elif method == "simple":
                # Simple thresholding with fixed threshold
                threshold = self.config.get("binary_threshold", 127)
                _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)

            else:
                raise ValueError(f"Unknown binarization method: {method}")

            logger.debug(f"Applied {method} binarization")
            return binary

        except Exception as e:
            logger.warning(f"Binarization failed: {e}. Returning original image.")
            return image

    def sharpen(self, image: np.ndarray, strength: float = 1.0) -> np.ndarray:
        """
        Sharpen image to enhance text edges.

        Args:
            image: Input image
            strength: Sharpening strength (0.0 to 2.0, default 1.0)

        Returns:
            Sharpened image
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        try:
            # Create sharpening kernel
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)

            # Adjust kernel strength
            kernel = (kernel - 1) * strength + 1

            # Apply filter
            sharpened = cv2.filter2D(image, -1, kernel)

            logger.debug(f"Applied sharpening with strength {strength}")
            return sharpened

        except Exception as e:
            logger.warning(f"Sharpening failed: {e}. Returning original image.")
            return image

    def remove_lines(self, image: np.ndarray, line_type: str = "both") -> np.ndarray:
        """
        Remove horizontal and/or vertical lines from image.

        This is particularly useful for worksheet images that contain grid lines
        which can interfere with text recognition.

        Args:
            image: Input image
            line_type: Type of lines to remove ("horizontal", "vertical", "both")

        Returns:
            Image with lines removed

        Raises:
            ValueError: If invalid line_type specified
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        if line_type not in ["horizontal", "vertical", "both"]:
            raise ValueError(f"Invalid line_type: {line_type}")

        try:
            # Convert to grayscale if needed
            gray = self.convert_to_grayscale(image)

            # Binarize
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            result = binary.copy()

            # Remove horizontal lines
            if line_type in ["horizontal", "both"]:
                horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
                horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
                result = cv2.subtract(result, horizontal_lines)

            # Remove vertical lines
            if line_type in ["vertical", "both"]:
                vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
                vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
                result = cv2.subtract(result, vertical_lines)

            # Invert back
            result = cv2.bitwise_not(result)

            logger.debug(f"Removed {line_type} lines from image")
            return result

        except Exception as e:
            logger.warning(f"Line removal failed: {e}. Returning original image.")
            return image

    def resize(
        self, image: np.ndarray, scale: float = 1.0, interpolation: Optional[int] = None
    ) -> np.ndarray:
        """
        Resize image by scale factor.

        Args:
            image: Input image
            scale: Scale factor (e.g., 2.0 for 2x size)
            interpolation: OpenCV interpolation method
                          (default: INTER_CUBIC for upscaling, INTER_AREA for downscaling)

        Returns:
            Resized image
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        if scale == 1.0:
            return image

        try:
            # Choose interpolation method based on scale
            if interpolation is None:
                interpolation = cv2.INTER_CUBIC if scale > 1.0 else cv2.INTER_AREA

            # Calculate new dimensions
            height, width = image.shape[:2]
            new_width = int(width * scale)
            new_height = int(height * scale)

            # Resize
            resized = cv2.resize(image, (new_width, new_height), interpolation=interpolation)

            logger.debug(f"Resized image by factor {scale} to {new_width}x{new_height}")
            return resized

        except Exception as e:
            logger.warning(f"Resizing failed: {e}. Returning original image.")
            return image

    def auto_crop(self, image: np.ndarray, padding: int = 10) -> np.ndarray:
        """
        Automatically crop image to content boundaries.

        Removes unnecessary white space around the document content.

        Args:
            image: Input image
            padding: Padding to add around detected content (pixels)

        Returns:
            Cropped image
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        try:
            # Convert to grayscale
            gray = self.convert_to_grayscale(image)

            # Threshold to binary
            _, binary = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY_INV)

            # Find contours
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if not contours:
                return image

            # Get bounding box of all contours
            x_min, y_min = float("inf"), float("inf")
            x_max, y_max = 0, 0

            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                x_min = min(x_min, x)
                y_min = min(y_min, y)
                x_max = max(x_max, x + w)
                y_max = max(y_max, y + h)

            # Add padding
            height, width = image.shape[:2]
            x_min = max(0, int(x_min) - padding)
            y_min = max(0, int(y_min) - padding)
            x_max = min(width, int(x_max) + padding)
            y_max = min(height, int(y_max) + padding)

            # Crop
            cropped = image[y_min:y_max, x_min:x_max]

            logger.debug(f"Auto-cropped image to {cropped.shape}")
            return cropped

        except Exception as e:
            logger.warning(f"Auto-crop failed: {e}. Returning original image.")
            return image
