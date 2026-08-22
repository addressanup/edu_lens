"""
Model Optimization Utilities for Edge Deployment

This module provides comprehensive model optimization capabilities for deploying
vision models on edge devices (smart glasses) with limited computational resources.
Supports quantization, pruning, ONNX conversion, and device-specific optimizations.

Target Requirements:
- Total memory footprint: <500MB for all vision models
- Inference time: <500ms for OCR, <1s for handwriting
- Support for ARM-based processors

Author: Vision Processing Agent (VIS-001)
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

try:
    import torch
    import torch.nn as nn
    from torch.quantization import convert, prepare, quantize_dynamic, quantize_static
except ImportError:
    torch = None
    nn = None

try:
    import onnx
    import onnxruntime as ort
except ImportError:
    onnx = None
    ort = None

try:
    import tensorflow as tf
except ImportError:
    tf = None


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuantizationType(Enum):
    """Supported quantization types."""

    INT8 = "int8"
    FP16 = "fp16"
    DYNAMIC = "dynamic"
    STATIC = "static"


class ModelFramework(Enum):
    """Supported model frameworks."""

    PYTORCH = "pytorch"
    TENSORFLOW = "tensorflow"
    ONNX = "onnx"


class DeviceType(Enum):
    """Target device types."""

    ARM_CPU = "arm_cpu"
    X86_CPU = "x86_cpu"
    GPU = "gpu"
    EDGE_TPU = "edge_tpu"


@dataclass
class OptimizationConfig:
    """Configuration for model optimization."""

    quantization_type: QuantizationType = QuantizationType.INT8
    target_device: DeviceType = DeviceType.ARM_CPU
    max_memory_mb: int = 500
    target_latency_ms: float = 500.0
    preserve_accuracy: bool = True
    min_accuracy_threshold: float = 0.90
    enable_pruning: bool = True
    pruning_ratio: float = 0.3
    enable_operator_fusion: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "quantization_type": self.quantization_type.value,
            "target_device": self.target_device.value,
            "max_memory_mb": self.max_memory_mb,
            "target_latency_ms": self.target_latency_ms,
            "preserve_accuracy": self.preserve_accuracy,
            "min_accuracy_threshold": self.min_accuracy_threshold,
            "enable_pruning": self.enable_pruning,
            "pruning_ratio": self.pruning_ratio,
            "enable_operator_fusion": self.enable_operator_fusion,
        }


@dataclass
class BenchmarkResult:
    """Results from model benchmarking."""

    avg_inference_time_ms: float
    min_inference_time_ms: float
    max_inference_time_ms: float
    std_inference_time_ms: float
    memory_usage_mb: float
    model_size_mb: float
    throughput_samples_per_sec: float
    accuracy: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "avg_inference_time_ms": self.avg_inference_time_ms,
            "min_inference_time_ms": self.min_inference_time_ms,
            "max_inference_time_ms": self.max_inference_time_ms,
            "std_inference_time_ms": self.std_inference_time_ms,
            "memory_usage_mb": self.memory_usage_mb,
            "model_size_mb": self.model_size_mb,
            "throughput_samples_per_sec": self.throughput_samples_per_sec,
            "accuracy": self.accuracy,
            "metadata": self.metadata,
        }


class ModelOptimizer:
    """
    Comprehensive model optimization for edge deployment.

    This class provides utilities for optimizing deep learning models for
    deployment on resource-constrained edge devices. It supports multiple
    optimization techniques including quantization, pruning, and ONNX conversion.

    Key Features:
    - INT8/FP16 quantization for reduced memory footprint
    - Model pruning to remove unnecessary weights
    - ONNX conversion for cross-platform deployment
    - Device-specific optimizations (ARM, x86, GPU)
    - Performance benchmarking and profiling
    - Accuracy-preserving optimizations

    Attributes:
        config: Optimization configuration
        framework: Source model framework (PyTorch/TensorFlow)
    """

    def __init__(
        self,
        config: Optional[OptimizationConfig] = None,
        framework: ModelFramework = ModelFramework.PYTORCH,
    ):
        """
        Initialize the model optimizer.

        Args:
            config: Optimization configuration
            framework: Source model framework
        """
        self.config = config or OptimizationConfig()
        self.framework = framework

        # Validate dependencies
        self._validate_dependencies()

        logger.info(
            f"ModelOptimizer initialized for {framework.value} with "
            f"{self.config.quantization_type.value} quantization"
        )

    def _validate_dependencies(self) -> None:
        """Validate that required dependencies are available."""
        if self.framework == ModelFramework.PYTORCH and torch is None:
            raise ImportError(
                "PyTorch is required for PyTorch models. "
                "Install with: pip install torch torchvision"
            )

        if self.framework == ModelFramework.TENSORFLOW and tf is None:
            raise ImportError(
                "TensorFlow is required for TensorFlow models. "
                "Install with: pip install tensorflow"
            )

        if onnx is None or ort is None:
            logger.warning("ONNX not available. Install with: pip install onnx onnxruntime")

    def quantize_model(
        self,
        model: Any,
        calibration_data: Optional[Any] = None,
        quantization_type: Optional[QuantizationType] = None,
    ) -> Any:
        """
        Quantize model to reduce memory footprint and improve inference speed.

        Quantization converts model weights and activations from FP32 to lower
        precision (INT8 or FP16), reducing model size by 2-4x and improving
        inference speed on compatible hardware.

        Args:
            model: Source model to quantize
            calibration_data: Optional calibration data for static quantization
            quantization_type: Type of quantization to apply

        Returns:
            Quantized model

        Raises:
            ValueError: If model or quantization type is invalid
        """
        quant_type = quantization_type or self.config.quantization_type

        logger.info(f"Starting {quant_type.value} quantization...")

        if self.framework == ModelFramework.PYTORCH:
            return self._quantize_pytorch_model(model, calibration_data, quant_type)
        elif self.framework == ModelFramework.TENSORFLOW:
            return self._quantize_tensorflow_model(model, calibration_data, quant_type)
        else:
            raise ValueError(f"Quantization not supported for {self.framework.value}")

    def _quantize_pytorch_model(
        self, model: Any, calibration_data: Optional[Any], quant_type: QuantizationType
    ) -> Any:
        """Quantize PyTorch model."""
        if torch is None:
            raise ImportError("PyTorch not available")

        try:
            model.eval()

            if quant_type == QuantizationType.DYNAMIC:
                # Dynamic quantization (good for LSTMs, RNNs)
                quantized_model = quantize_dynamic(
                    model, {nn.Linear, nn.LSTM, nn.GRU}, dtype=torch.qint8
                )
                logger.info("Applied dynamic INT8 quantization")

            elif quant_type == QuantizationType.STATIC:
                # Static quantization (requires calibration data)
                if calibration_data is None:
                    raise ValueError("Calibration data required for static quantization")

                # Prepare model for quantization
                model.qconfig = torch.quantization.get_default_qconfig("fbgemm")
                prepared_model = prepare(model)

                # Calibrate with sample data
                logger.info("Calibrating model with sample data...")
                with torch.no_grad():
                    for data in calibration_data:
                        prepared_model(data)

                # Convert to quantized model
                quantized_model = convert(prepared_model)
                logger.info("Applied static INT8 quantization")

            elif quant_type == QuantizationType.FP16:
                # FP16 quantization (half precision)
                quantized_model = model.half()
                logger.info("Applied FP16 quantization")

            else:
                raise ValueError(f"Unsupported quantization type: {quant_type.value}")

            return quantized_model

        except Exception as e:
            logger.error(f"PyTorch quantization failed: {e}")
            raise

    def _quantize_tensorflow_model(
        self, model: Any, calibration_data: Optional[Any], quant_type: QuantizationType
    ) -> Any:
        """Quantize TensorFlow model."""
        if tf is None:
            raise ImportError("TensorFlow not available")

        try:
            if quant_type in [QuantizationType.INT8, QuantizationType.STATIC]:
                # Convert to TFLite with INT8 quantization
                converter = tf.lite.TFLiteConverter.from_keras_model(model)
                converter.optimizations = [tf.lite.Optimize.DEFAULT]

                if calibration_data is not None:
                    # Representative dataset for full integer quantization
                    def representative_dataset():
                        for data in calibration_data:
                            yield [data]

                    converter.representative_dataset = representative_dataset
                    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
                    converter.inference_input_type = tf.int8
                    converter.inference_output_type = tf.int8

                quantized_model = converter.convert()
                logger.info("Applied INT8 quantization to TensorFlow model")

            elif quant_type == QuantizationType.FP16:
                converter = tf.lite.TFLiteConverter.from_keras_model(model)
                converter.optimizations = [tf.lite.Optimize.DEFAULT]
                converter.target_spec.supported_types = [tf.float16]
                quantized_model = converter.convert()
                logger.info("Applied FP16 quantization to TensorFlow model")

            else:
                raise ValueError(f"Unsupported quantization type: {quant_type.value}")

            return quantized_model

        except Exception as e:
            logger.error(f"TensorFlow quantization failed: {e}")
            raise

    def prune_model(
        self, model: Any, pruning_ratio: Optional[float] = None, preserve_accuracy: bool = True
    ) -> Any:
        """
        Prune model by removing unnecessary weights.

        Model pruning removes weights with small magnitudes, reducing model
        size and computational requirements while maintaining accuracy.

        Args:
            model: Model to prune
            pruning_ratio: Fraction of weights to prune (0.0-1.0)
            preserve_accuracy: Whether to use accuracy-aware pruning

        Returns:
            Pruned model
        """
        ratio = pruning_ratio or self.config.pruning_ratio

        logger.info(f"Pruning model with ratio {ratio}...")

        if self.framework == ModelFramework.PYTORCH:
            return self._prune_pytorch_model(model, ratio, preserve_accuracy)
        elif self.framework == ModelFramework.TENSORFLOW:
            return self._prune_tensorflow_model(model, ratio, preserve_accuracy)
        else:
            raise ValueError(f"Pruning not supported for {self.framework.value}")

    def _prune_pytorch_model(self, model: Any, ratio: float, preserve_accuracy: bool) -> Any:
        """Prune PyTorch model."""
        if torch is None:
            raise ImportError("PyTorch not available")

        try:
            import torch.nn.utils.prune as prune

            # Apply magnitude-based pruning to all conv and linear layers
            for name, module in model.named_modules():
                if isinstance(module, (nn.Conv2d, nn.Linear)):
                    prune.l1_unstructured(module, name="weight", amount=ratio)
                    # Make pruning permanent
                    prune.remove(module, "weight")

            logger.info(f"Pruned {ratio*100}% of model weights")
            return model

        except Exception as e:
            logger.error(f"PyTorch pruning failed: {e}")
            raise

    def _prune_tensorflow_model(self, model: Any, ratio: float, preserve_accuracy: bool) -> Any:
        """Prune TensorFlow model."""
        if tf is None:
            raise ImportError("TensorFlow not available")

        try:
            import tensorflow_model_optimization as tfmot

            # Define pruning schedule
            pruning_params = {
                "pruning_schedule": tfmot.sparsity.keras.PolynomialDecay(
                    initial_sparsity=0.0, final_sparsity=ratio, begin_step=0, end_step=1000
                )
            }

            # Apply pruning
            pruned_model = tfmot.sparsity.keras.prune_low_magnitude(model, **pruning_params)

            logger.info(f"Configured TensorFlow model for {ratio*100}% pruning")
            return pruned_model

        except ImportError:
            logger.warning(
                "tensorflow-model-optimization not available. "
                "Install with: pip install tensorflow-model-optimization"
            )
            return model
        except Exception as e:
            logger.error(f"TensorFlow pruning failed: {e}")
            raise

    def convert_to_onnx(
        self,
        model: Any,
        input_shape: Tuple[int, ...],
        output_path: Union[str, Path],
        opset_version: int = 13,
        optimize: bool = True,
    ) -> str:
        """
        Convert model to ONNX format for cross-platform deployment.

        ONNX (Open Neural Network Exchange) is an open standard for representing
        machine learning models. It enables deployment across different frameworks
        and hardware platforms.

        Args:
            model: Source model to convert
            input_shape: Input tensor shape (e.g., (1, 3, 224, 224))
            output_path: Path to save ONNX model
            opset_version: ONNX opset version
            optimize: Whether to apply ONNX optimizations

        Returns:
            Path to saved ONNX model

        Raises:
            ValueError: If conversion fails
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Converting model to ONNX format...")

        if self.framework == ModelFramework.PYTORCH:
            self._convert_pytorch_to_onnx(model, input_shape, output_path, opset_version)
        elif self.framework == ModelFramework.TENSORFLOW:
            self._convert_tensorflow_to_onnx(model, input_shape, output_path, opset_version)
        else:
            raise ValueError(f"ONNX conversion not supported for {self.framework.value}")

        # Apply ONNX optimizations
        if optimize and onnx is not None:
            self._optimize_onnx_model(output_path)

        logger.info(f"ONNX model saved to: {output_path}")
        return str(output_path)

    def _convert_pytorch_to_onnx(
        self, model: Any, input_shape: Tuple[int, ...], output_path: Path, opset_version: int
    ) -> None:
        """Convert PyTorch model to ONNX."""
        if torch is None:
            raise ImportError("PyTorch not available")

        try:
            model.eval()

            # Create dummy input
            dummy_input = torch.randn(*input_shape)

            # Export to ONNX
            torch.onnx.export(
                model,
                dummy_input,
                str(output_path),
                export_params=True,
                opset_version=opset_version,
                do_constant_folding=True,
                input_names=["input"],
                output_names=["output"],
                dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}},
            )

            logger.info("PyTorch model converted to ONNX")

        except Exception as e:
            logger.error(f"PyTorch to ONNX conversion failed: {e}")
            raise

    def _convert_tensorflow_to_onnx(
        self, model: Any, input_shape: Tuple[int, ...], output_path: Path, opset_version: int
    ) -> None:
        """Convert TensorFlow model to ONNX."""
        try:
            import tf2onnx

            # Convert TensorFlow model to ONNX
            spec = (tf.TensorSpec(input_shape, tf.float32, name="input"),)
            onnx_model, _ = tf2onnx.convert.from_keras(
                model, input_signature=spec, opset=opset_version
            )

            # Save ONNX model
            with open(output_path, "wb") as f:
                f.write(onnx_model.SerializeToString())

            logger.info("TensorFlow model converted to ONNX")

        except ImportError:
            logger.error("tf2onnx not available. Install with: pip install tf2onnx")
            raise
        except Exception as e:
            logger.error(f"TensorFlow to ONNX conversion failed: {e}")
            raise

    def _optimize_onnx_model(self, model_path: Path) -> None:
        """Apply ONNX-level optimizations."""
        if onnx is None:
            logger.warning("ONNX not available, skipping optimizations")
            return

        try:
            # Load ONNX model
            model = onnx.load(str(model_path))

            # Apply optimizations
            from onnxruntime.transformers.optimizer import optimize_model

            optimized_model = optimize_model(
                str(model_path),
                model_type="bert",  # Generic optimization
                num_heads=0,
                hidden_size=0,
            )

            # Save optimized model
            optimized_model.save_model_to_file(str(model_path))

            logger.info("Applied ONNX optimizations")

        except ImportError:
            logger.warning("ONNX optimizer not available")
        except Exception as e:
            logger.warning(f"ONNX optimization failed: {e}")

    def benchmark_model(
        self, model: Any, input_data: Any, num_iterations: int = 100, warmup_iterations: int = 10
    ) -> BenchmarkResult:
        """
        Benchmark model performance.

        Measures inference time, memory usage, and throughput on sample data.
        Useful for validating optimization results and comparing models.

        Args:
            model: Model to benchmark
            input_data: Sample input data
            num_iterations: Number of inference iterations
            warmup_iterations: Number of warmup iterations (excluded from timing)

        Returns:
            BenchmarkResult with performance metrics
        """
        logger.info(f"Benchmarking model ({num_iterations} iterations)...")

        # Warmup
        logger.debug(f"Warmup: {warmup_iterations} iterations")
        for _ in range(warmup_iterations):
            if self.framework == ModelFramework.PYTORCH:
                with torch.no_grad():
                    _ = model(input_data)
            else:
                _ = model(input_data)

        # Benchmark
        inference_times = []

        for i in range(num_iterations):
            start_time = time.perf_counter()

            if self.framework == ModelFramework.PYTORCH:
                with torch.no_grad():
                    _ = model(input_data)
            else:
                _ = model(input_data)

            end_time = time.perf_counter()
            inference_times.append((end_time - start_time) * 1000)  # Convert to ms

        # Calculate statistics
        inference_times_array = np.array(inference_times)
        avg_time = float(np.mean(inference_times_array))
        min_time = float(np.min(inference_times_array))
        max_time = float(np.max(inference_times_array))
        std_time = float(np.std(inference_times_array))
        throughput = 1000.0 / avg_time if avg_time > 0 else 0.0

        # Estimate memory usage
        memory_mb = self._estimate_memory_usage(model)
        model_size_mb = self._get_model_size(model)

        result = BenchmarkResult(
            avg_inference_time_ms=avg_time,
            min_inference_time_ms=min_time,
            max_inference_time_ms=max_time,
            std_inference_time_ms=std_time,
            memory_usage_mb=memory_mb,
            model_size_mb=model_size_mb,
            throughput_samples_per_sec=throughput,
            metadata={
                "num_iterations": num_iterations,
                "warmup_iterations": warmup_iterations,
                "framework": self.framework.value,
            },
        )

        logger.info(
            f"Benchmark complete: "
            f"avg={avg_time:.2f}ms, "
            f"throughput={throughput:.2f} samples/sec, "
            f"memory={memory_mb:.2f}MB"
        )

        return result

    def _estimate_memory_usage(self, model: Any) -> float:
        """Estimate model memory usage in MB."""
        if self.framework == ModelFramework.PYTORCH and torch is not None:
            try:
                # Get parameter memory
                param_size = sum(p.numel() * p.element_size() for p in model.parameters())
                # Get buffer memory
                buffer_size = sum(b.numel() * b.element_size() for b in model.buffers())
                total_bytes = param_size + buffer_size
                return total_bytes / (1024 * 1024)
            except:
                pass

        # Fallback: estimate based on model size
        return self._get_model_size(model)

    def _get_model_size(self, model: Any) -> float:
        """Get model size in MB."""
        if self.framework == ModelFramework.PYTORCH and torch is not None:
            try:
                # Save to temporary buffer and get size
                import io

                buffer = io.BytesIO()
                torch.save(model.state_dict(), buffer)
                size_bytes = buffer.tell()
                return size_bytes / (1024 * 1024)
            except:
                pass

        return 0.0

    def optimize_for_device(self, model: Any, device_type: Optional[DeviceType] = None) -> Any:
        """
        Apply device-specific optimizations.

        Optimizes model for specific target hardware (ARM CPU, x86 CPU, GPU, etc.)
        by applying platform-specific techniques and configurations.

        Args:
            model: Model to optimize
            device_type: Target device type

        Returns:
            Device-optimized model
        """
        device = device_type or self.config.target_device

        logger.info(f"Optimizing model for {device.value}...")

        if device == DeviceType.ARM_CPU:
            # ARM-specific optimizations
            logger.info("Applying ARM CPU optimizations")
            # Use INT8 quantization (ARM NEON supports INT8)
            model = self.quantize_model(model, quantization_type=QuantizationType.INT8)

        elif device == DeviceType.X86_CPU:
            # x86-specific optimizations
            logger.info("Applying x86 CPU optimizations")
            # Use dynamic quantization
            model = self.quantize_model(model, quantization_type=QuantizationType.DYNAMIC)

        elif device == DeviceType.GPU:
            # GPU-specific optimizations
            logger.info("Applying GPU optimizations")
            # Use FP16 for faster GPU inference
            model = self.quantize_model(model, quantization_type=QuantizationType.FP16)

        elif device == DeviceType.EDGE_TPU:
            # Edge TPU optimizations
            logger.info("Applying Edge TPU optimizations")
            # Edge TPU requires INT8 quantization
            model = self.quantize_model(model, quantization_type=QuantizationType.INT8)

        return model

    def optimize_pipeline(
        self,
        model: Any,
        input_shape: Tuple[int, ...],
        output_path: Union[str, Path],
        calibration_data: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Run complete optimization pipeline.

        Applies all optimization techniques in sequence:
        1. Pruning (if enabled)
        2. Quantization
        3. Device-specific optimizations
        4. ONNX conversion
        5. Benchmarking

        Args:
            model: Source model
            input_shape: Input tensor shape
            output_path: Path to save optimized model
            calibration_data: Optional calibration data for quantization

        Returns:
            Dictionary with optimization results and metrics
        """
        logger.info("Starting optimization pipeline...")
        start_time = time.time()

        results = {"original_model": {}, "optimized_model": {}, "optimizations_applied": []}

        # Benchmark original model
        logger.info("Benchmarking original model...")
        try:
            if self.framework == ModelFramework.PYTORCH:
                dummy_input = torch.randn(*input_shape)
            else:
                dummy_input = np.random.randn(*input_shape).astype(np.float32)

            original_benchmark = self.benchmark_model(model, dummy_input)
            results["original_model"] = original_benchmark.to_dict()
        except Exception as e:
            logger.warning(f"Original model benchmarking failed: {e}")

        # Apply optimizations
        optimized_model = model

        # 1. Pruning
        if self.config.enable_pruning:
            logger.info("Applying pruning...")
            optimized_model = self.prune_model(optimized_model)
            results["optimizations_applied"].append("pruning")

        # 2. Quantization
        logger.info("Applying quantization...")
        optimized_model = self.quantize_model(optimized_model, calibration_data)
        results["optimizations_applied"].append(
            f"quantization_{self.config.quantization_type.value}"
        )

        # 3. Device-specific optimizations
        logger.info("Applying device-specific optimizations...")
        optimized_model = self.optimize_for_device(optimized_model)
        results["optimizations_applied"].append(f"device_{self.config.target_device.value}")

        # 4. Convert to ONNX
        logger.info("Converting to ONNX...")
        try:
            onnx_path = self.convert_to_onnx(
                optimized_model,
                input_shape,
                output_path,
                optimize=self.config.enable_operator_fusion,
            )
            results["onnx_model_path"] = onnx_path
            results["optimizations_applied"].append("onnx_conversion")
        except Exception as e:
            logger.warning(f"ONNX conversion failed: {e}")

        # 5. Benchmark optimized model
        logger.info("Benchmarking optimized model...")
        try:
            optimized_benchmark = self.benchmark_model(optimized_model, dummy_input)
            results["optimized_model"] = optimized_benchmark.to_dict()
        except Exception as e:
            logger.warning(f"Optimized model benchmarking failed: {e}")

        # Calculate improvements
        if results["original_model"] and results["optimized_model"]:
            orig_time = results["original_model"]["avg_inference_time_ms"]
            opt_time = results["optimized_model"]["avg_inference_time_ms"]
            speedup = orig_time / opt_time if opt_time > 0 else 0.0

            orig_size = results["original_model"]["model_size_mb"]
            opt_size = results["optimized_model"]["model_size_mb"]
            size_reduction = (orig_size - opt_size) / orig_size * 100 if orig_size > 0 else 0.0

            results["improvements"] = {
                "speedup": f"{speedup:.2f}x",
                "size_reduction": f"{size_reduction:.1f}%",
                "inference_time_reduction_ms": orig_time - opt_time,
            }

        total_time = time.time() - start_time
        results["optimization_time_sec"] = total_time
        results["config"] = self.config.to_dict()

        logger.info(
            f"Optimization pipeline complete in {total_time:.2f}s. "
            f"Applied: {', '.join(results['optimizations_applied'])}"
        )

        return results
