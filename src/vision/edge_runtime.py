"""
Edge Inference Runtime for Vision Models

This module provides an optimized inference runtime for vision models on edge
devices with limited computational resources. It supports ONNX models and
provides memory-efficient inference with automatic resource management.

Target Requirements:
- Memory footprint: <500MB total for all models
- Inference time: <500ms for OCR, <1s for handwriting
- ARM-based processor support

Author: Vision Processing Agent (VIS-001)
"""

import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

try:
    import onnxruntime as ort
except ImportError:
    ort = None

try:
    import cv2
except ImportError:
    cv2 = None


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Supported model types."""
    OCR = "ocr"
    HANDWRITING = "handwriting"
    LAYOUT = "layout"
    PREPROCESSING = "preprocessing"


class InferenceProvider(Enum):
    """Inference execution providers."""
    CPU = "CPUExecutionProvider"
    CUDA = "CUDAExecutionProvider"
    TENSORRT = "TensorrtExecutionProvider"
    OPENVINO = "OpenVINOExecutionProvider"
    NNAPI = "NnapiExecutionProvider"  # Android Neural Networks API


@dataclass
class ModelConfig:
    """Configuration for a loaded model."""
    model_type: ModelType
    model_path: str
    input_shape: Tuple[int, ...]
    output_shape: Tuple[int, ...]
    memory_limit_mb: float = 150.0
    max_inference_time_ms: float = 500.0
    provider: InferenceProvider = InferenceProvider.CPU
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InferenceResult:
    """Result from model inference."""
    output: np.ndarray
    inference_time_ms: float
    preprocessing_time_ms: float = 0.0
    postprocessing_time_ms: float = 0.0
    total_time_ms: float = 0.0
    memory_used_mb: float = 0.0
    model_type: Optional[ModelType] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "output_shape": self.output.shape,
            "inference_time_ms": self.inference_time_ms,
            "preprocessing_time_ms": self.preprocessing_time_ms,
            "postprocessing_time_ms": self.postprocessing_time_ms,
            "total_time_ms": self.total_time_ms,
            "memory_used_mb": self.memory_used_mb,
            "model_type": self.model_type.value if self.model_type else None,
            "metadata": self.metadata
        }


class EdgeVisionRuntime:
    """
    Optimized edge inference runtime for vision models.

    This class provides a high-performance inference runtime for vision models
    on resource-constrained edge devices. It supports ONNX models and includes
    features like:
    - Memory-efficient model loading and caching
    - Automatic batch processing
    - Resource monitoring and throttling
    - Model warm-up for consistent performance
    - Automatic provider selection (CPU, GPU, etc.)

    Attributes:
        models: Dictionary of loaded models by type
        config: Runtime configuration
        memory_budget_mb: Total memory budget for all models
    """

    def __init__(
        self,
        memory_budget_mb: float = 500.0,
        enable_optimization: bool = True,
        default_provider: InferenceProvider = InferenceProvider.CPU
    ):
        """
        Initialize the edge vision runtime.

        Args:
            memory_budget_mb: Total memory budget for all models (MB)
            enable_optimization: Enable ONNX graph optimizations
            default_provider: Default execution provider
        """
        self.memory_budget_mb = memory_budget_mb
        self.enable_optimization = enable_optimization
        self.default_provider = default_provider

        # Model storage
        self.models: Dict[ModelType, Any] = {}
        self.model_configs: Dict[ModelType, ModelConfig] = {}
        self.sessions: Dict[ModelType, Any] = {}

        # Performance tracking
        self.inference_count: Dict[ModelType, int] = {}
        self.total_inference_time: Dict[ModelType, float] = {}
        self.warmup_complete: Dict[ModelType, bool] = {}

        # Validate dependencies
        self._validate_dependencies()

        # Get available providers
        self.available_providers = self._get_available_providers()

        logger.info(
            f"EdgeVisionRuntime initialized with {memory_budget_mb}MB memory budget. "
            f"Available providers: {self.available_providers}"
        )

    def _validate_dependencies(self) -> None:
        """Validate that required dependencies are available."""
        if ort is None:
            raise ImportError(
                "ONNX Runtime is required. Install with: pip install onnxruntime"
            )
        if cv2 is None:
            logger.warning(
                "OpenCV not available. Image preprocessing may be limited. "
                "Install with: pip install opencv-python"
            )

    def _get_available_providers(self) -> List[str]:
        """Get list of available execution providers."""
        if ort is None:
            return []
        return ort.get_available_providers()

    def load_optimized_model(
        self,
        model_path: Union[str, Path],
        model_type: ModelType,
        config: Optional[ModelConfig] = None
    ) -> None:
        """
        Load an optimized ONNX model for inference.

        Args:
            model_path: Path to ONNX model file
            model_type: Type of model being loaded
            config: Optional model configuration

        Raises:
            FileNotFoundError: If model file doesn't exist
            ValueError: If model exceeds memory budget
        """
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        logger.info(f"Loading {model_type.value} model from {model_path}")

        # Check memory budget
        model_size_mb = model_path.stat().st_size / (1024 * 1024)
        if model_size_mb > self.memory_budget_mb:
            raise ValueError(
                f"Model size ({model_size_mb:.2f}MB) exceeds memory budget "
                f"({self.memory_budget_mb}MB)"
            )

        # Create session options
        sess_options = ort.SessionOptions()

        # Enable optimizations
        if self.enable_optimization:
            sess_options.graph_optimization_level = (
                ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            )
            sess_options.optimized_model_filepath = str(
                model_path.parent / f"{model_path.stem}_optimized.onnx"
            )

        # Set execution mode
        sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

        # Set thread count based on available resources
        sess_options.intra_op_num_threads = 2  # Limited for edge devices
        sess_options.inter_op_num_threads = 1

        # Select execution provider
        provider = config.provider.value if config and config.provider else self.default_provider.value

        # Create inference session
        try:
            if provider in self.available_providers:
                providers = [provider]
            else:
                logger.warning(
                    f"Provider {provider} not available. Falling back to CPU."
                )
                providers = ['CPUExecutionProvider']

            session = ort.InferenceSession(
                str(model_path),
                sess_options,
                providers=providers
            )

            # Store session and config
            self.sessions[model_type] = session
            self.model_configs[model_type] = config or self._create_default_config(
                model_type, str(model_path), session
            )

            # Initialize tracking
            self.inference_count[model_type] = 0
            self.total_inference_time[model_type] = 0.0
            self.warmup_complete[model_type] = False

            # Get model info
            input_name = session.get_inputs()[0].name
            input_shape = session.get_inputs()[0].shape
            output_name = session.get_outputs()[0].name
            output_shape = session.get_outputs()[0].shape

            logger.info(
                f"Model loaded successfully: "
                f"input={input_name}{input_shape}, "
                f"output={output_name}{output_shape}, "
                f"provider={providers[0]}, "
                f"size={model_size_mb:.2f}MB"
            )

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def _create_default_config(
        self,
        model_type: ModelType,
        model_path: str,
        session: Any
    ) -> ModelConfig:
        """Create default model configuration."""
        input_shape = tuple(session.get_inputs()[0].shape)
        output_shape = tuple(session.get_outputs()[0].shape)

        # Default time limits based on model type
        max_time = 500.0 if model_type == ModelType.OCR else 1000.0

        return ModelConfig(
            model_type=model_type,
            model_path=model_path,
            input_shape=input_shape,
            output_shape=output_shape,
            max_inference_time_ms=max_time
        )

    def run_inference(
        self,
        input_data: np.ndarray,
        model_type: ModelType,
        preprocess: bool = True,
        postprocess: bool = True
    ) -> InferenceResult:
        """
        Run inference on input data.

        Args:
            input_data: Input image or tensor
            model_type: Type of model to use
            preprocess: Whether to preprocess input
            postprocess: Whether to postprocess output

        Returns:
            InferenceResult with output and timing information

        Raises:
            ValueError: If model not loaded or input invalid
        """
        if model_type not in self.sessions:
            raise ValueError(f"Model {model_type.value} not loaded")

        start_time = time.perf_counter()

        # Preprocessing
        preprocess_start = time.perf_counter()
        if preprocess:
            processed_input = self._preprocess_input(input_data, model_type)
        else:
            processed_input = input_data
        preprocess_time = (time.perf_counter() - preprocess_start) * 1000

        # Inference
        inference_start = time.perf_counter()
        session = self.sessions[model_type]
        input_name = session.get_inputs()[0].name

        try:
            output = session.run(None, {input_name: processed_input})[0]
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            raise

        inference_time = (time.perf_counter() - inference_start) * 1000

        # Postprocessing
        postprocess_start = time.perf_counter()
        if postprocess:
            processed_output = self._postprocess_output(output, model_type)
        else:
            processed_output = output
        postprocess_time = (time.perf_counter() - postprocess_start) * 1000

        total_time = (time.perf_counter() - start_time) * 1000

        # Update tracking
        self.inference_count[model_type] += 1
        self.total_inference_time[model_type] += inference_time

        # Create result
        result = InferenceResult(
            output=processed_output,
            inference_time_ms=inference_time,
            preprocessing_time_ms=preprocess_time,
            postprocessing_time_ms=postprocess_time,
            total_time_ms=total_time,
            model_type=model_type,
            metadata={
                "inference_number": self.inference_count[model_type],
                "avg_inference_time_ms": (
                    self.total_inference_time[model_type] / self.inference_count[model_type]
                )
            }
        )

        # Check if inference time exceeds limit
        config = self.model_configs[model_type]
        if inference_time > config.max_inference_time_ms:
            logger.warning(
                f"Inference time ({inference_time:.2f}ms) exceeds limit "
                f"({config.max_inference_time_ms:.2f}ms)"
            )

        return result

    def _preprocess_input(
        self,
        input_data: np.ndarray,
        model_type: ModelType
    ) -> np.ndarray:
        """
        Preprocess input data for model.

        Args:
            input_data: Raw input data
            model_type: Type of model

        Returns:
            Preprocessed input tensor
        """
        config = self.model_configs[model_type]
        input_shape = config.input_shape

        # Handle dynamic batch size
        if input_shape[0] == 'batch_size' or input_shape[0] is None or isinstance(input_shape[0], str):
            target_shape = (1,) + tuple(input_shape[1:])
        else:
            target_shape = tuple(input_shape)

        # Convert to correct shape
        if len(input_data.shape) == 2:
            # Grayscale image: add batch and channel dimensions
            processed = input_data[np.newaxis, np.newaxis, :, :]
        elif len(input_data.shape) == 3:
            if input_data.shape[2] == 3:
                # RGB/BGR image: transpose to CHW and add batch dimension
                processed = np.transpose(input_data, (2, 0, 1))[np.newaxis, :, :, :]
            else:
                # Already in CHW format: add batch dimension
                processed = input_data[np.newaxis, :, :, :]
        elif len(input_data.shape) == 4:
            # Already has batch dimension
            processed = input_data
        else:
            raise ValueError(f"Unsupported input shape: {input_data.shape}")

        # Resize if needed
        if processed.shape[2:] != target_shape[2:]:
            if cv2 is not None:
                # Resize using OpenCV (more efficient)
                batch_size, channels = processed.shape[:2]
                target_h, target_w = target_shape[2:]
                resized = np.zeros((batch_size, channels, target_h, target_w), dtype=processed.dtype)

                for b in range(batch_size):
                    for c in range(channels):
                        resized[b, c] = cv2.resize(
                            processed[b, c],
                            (target_w, target_h),
                            interpolation=cv2.INTER_LINEAR
                        )
                processed = resized

        # Normalize to [0, 1] if needed
        if processed.dtype == np.uint8:
            processed = processed.astype(np.float32) / 255.0

        return processed

    def _postprocess_output(
        self,
        output: np.ndarray,
        model_type: ModelType
    ) -> np.ndarray:
        """
        Postprocess model output.

        Args:
            output: Raw model output
            model_type: Type of model

        Returns:
            Postprocessed output
        """
        # Apply model-specific postprocessing
        if model_type == ModelType.OCR:
            # OCR output: typically logits or probabilities
            # Apply softmax if needed
            if len(output.shape) > 1 and output.max() > 1.0:
                output = self._softmax(output)

        elif model_type == ModelType.HANDWRITING:
            # Handwriting output: character predictions
            # Apply softmax if needed
            if len(output.shape) > 1 and output.max() > 1.0:
                output = self._softmax(output)

        return output

    def _softmax(self, x: np.ndarray, axis: int = -1) -> np.ndarray:
        """Apply softmax function."""
        exp_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
        return exp_x / np.sum(exp_x, axis=axis, keepdims=True)

    def batch_inference(
        self,
        input_batch: List[np.ndarray],
        model_type: ModelType,
        batch_size: int = 4
    ) -> List[InferenceResult]:
        """
        Run inference on multiple inputs with batching.

        Efficiently processes multiple inputs by batching them together,
        reducing overhead and improving throughput.

        Args:
            input_batch: List of input data
            model_type: Type of model to use
            batch_size: Maximum batch size for inference

        Returns:
            List of InferenceResult for each input
        """
        if model_type not in self.sessions:
            raise ValueError(f"Model {model_type.value} not loaded")

        results = []
        num_batches = (len(input_batch) + batch_size - 1) // batch_size

        logger.debug(
            f"Processing {len(input_batch)} inputs in {num_batches} batches "
            f"of size {batch_size}"
        )

        for i in range(num_batches):
            batch_start = i * batch_size
            batch_end = min((i + 1) * batch_size, len(input_batch))
            batch = input_batch[batch_start:batch_end]

            # Preprocess and stack inputs
            processed_batch = [
                self._preprocess_input(inp, model_type) for inp in batch
            ]
            stacked_batch = np.concatenate(processed_batch, axis=0)

            # Run batched inference
            batch_result = self.run_inference(
                stacked_batch,
                model_type,
                preprocess=False,
                postprocess=False
            )

            # Split batch results
            for j in range(len(batch)):
                output = batch_result.output[j:j+1]
                output = self._postprocess_output(output, model_type)

                result = InferenceResult(
                    output=output,
                    inference_time_ms=batch_result.inference_time_ms / len(batch),
                    preprocessing_time_ms=batch_result.preprocessing_time_ms / len(batch),
                    postprocessing_time_ms=batch_result.postprocessing_time_ms / len(batch),
                    total_time_ms=batch_result.total_time_ms / len(batch),
                    model_type=model_type
                )
                results.append(result)

        return results

    def get_memory_usage(self) -> Dict[str, float]:
        """
        Get current memory usage for all loaded models.

        Returns:
            Dictionary with memory usage information (in MB)
        """
        memory_info = {
            "total_budget_mb": self.memory_budget_mb,
            "models": {}
        }

        total_used = 0.0
        for model_type, config in self.model_configs.items():
            model_path = Path(config.model_path)
            if model_path.exists():
                size_mb = model_path.stat().st_size / (1024 * 1024)
                memory_info["models"][model_type.value] = size_mb
                total_used += size_mb

        memory_info["total_used_mb"] = total_used
        memory_info["available_mb"] = self.memory_budget_mb - total_used
        memory_info["usage_percent"] = (total_used / self.memory_budget_mb) * 100

        return memory_info

    def warm_up(
        self,
        model_type: ModelType,
        num_iterations: int = 5
    ) -> None:
        """
        Warm up model for consistent performance.

        Runs several dummy inferences to ensure the model and runtime are
        fully initialized. This prevents slow first inference times.

        Args:
            model_type: Type of model to warm up
            num_iterations: Number of warmup iterations
        """
        if model_type not in self.sessions:
            raise ValueError(f"Model {model_type.value} not loaded")

        if self.warmup_complete.get(model_type, False):
            logger.debug(f"Model {model_type.value} already warmed up")
            return

        logger.info(f"Warming up {model_type.value} model ({num_iterations} iterations)...")

        config = self.model_configs[model_type]
        input_shape = config.input_shape

        # Create dummy input
        if input_shape[0] == 'batch_size' or input_shape[0] is None or isinstance(input_shape[0], str):
            shape = (1,) + tuple(input_shape[1:])
        else:
            shape = tuple(input_shape)

        dummy_input = np.random.randn(*shape).astype(np.float32)

        # Run warmup iterations
        warmup_times = []
        for i in range(num_iterations):
            result = self.run_inference(
                dummy_input,
                model_type,
                preprocess=False,
                postprocess=False
            )
            warmup_times.append(result.inference_time_ms)

        self.warmup_complete[model_type] = True

        avg_time = np.mean(warmup_times)
        logger.info(
            f"Warmup complete for {model_type.value}. "
            f"Average inference time: {avg_time:.2f}ms"
        )

    def get_performance_stats(
        self,
        model_type: Optional[ModelType] = None
    ) -> Dict[str, Any]:
        """
        Get performance statistics for models.

        Args:
            model_type: Optional specific model type (None for all models)

        Returns:
            Dictionary with performance statistics
        """
        stats = {}

        if model_type:
            model_types = [model_type]
        else:
            model_types = list(self.sessions.keys())

        for mt in model_types:
            if mt in self.inference_count and self.inference_count[mt] > 0:
                stats[mt.value] = {
                    "total_inferences": self.inference_count[mt],
                    "total_time_ms": self.total_inference_time[mt],
                    "avg_inference_time_ms": (
                        self.total_inference_time[mt] / self.inference_count[mt]
                    ),
                    "warmup_complete": self.warmup_complete.get(mt, False),
                    "max_allowed_time_ms": self.model_configs[mt].max_inference_time_ms
                }

        return stats

    def unload_model(self, model_type: ModelType) -> None:
        """
        Unload a model to free memory.

        Args:
            model_type: Type of model to unload
        """
        if model_type in self.sessions:
            logger.info(f"Unloading {model_type.value} model")

            # Clear session
            del self.sessions[model_type]

            # Clear config
            if model_type in self.model_configs:
                del self.model_configs[model_type]

            # Clear tracking
            if model_type in self.inference_count:
                del self.inference_count[model_type]
            if model_type in self.total_inference_time:
                del self.total_inference_time[model_type]
            if model_type in self.warmup_complete:
                del self.warmup_complete[model_type]

            logger.info(f"Model {model_type.value} unloaded successfully")
        else:
            logger.warning(f"Model {model_type.value} not loaded")

    def clear_all(self) -> None:
        """Unload all models and clear runtime state."""
        logger.info("Clearing all models...")

        for model_type in list(self.sessions.keys()):
            self.unload_model(model_type)

        logger.info("All models cleared")

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.clear_all()
        except:
            pass
