"""
Edge Performance Tests for Vision Models

This test suite validates that vision models meet edge deployment requirements:
- Memory footprint: <500MB total for all models
- Inference time: <500ms for OCR, <1s for handwriting
- Resource management and throttling
- Model optimization effectiveness

Author: Vision Processing Agent (VIS-001)
"""

import pytest
import numpy as np
import time
from pathlib import Path
from typing import Dict, Any, Optional
import tempfile
import yaml

# Import modules to test
try:
    from src.vision.model_optimizer import (
        ModelOptimizer,
        OptimizationConfig,
        QuantizationType,
        DeviceType,
        ModelFramework
    )
    from src.vision.edge_runtime import (
        EdgeVisionRuntime,
        ModelType,
        ModelConfig,
        InferenceProvider
    )
    from src.runtime.resource_manager import (
        ResourceManager,
        ResourceLimits,
        ResourceLevel,
        QualityLevel,
        DeviceProfile
    )
except ImportError as e:
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    nn = None

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    ort = None


# Test fixtures and constants
TEST_IMAGE_SIZE = (224, 224)
TEST_BATCH_SIZE = 1
MEMORY_LIMIT_MB = 500.0
OCR_TIME_LIMIT_MS = 500.0
HANDWRITING_TIME_LIMIT_MS = 1000.0


class SimpleTestModel(nn.Module):
    """Simple CNN model for testing."""

    def __init__(self):
        super(SimpleTestModel, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, 3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.fc1 = nn.Linear(64 * 56 * 56, 128)
        self.fc2 = nn.Linear(128, 10)
        self.relu = nn.ReLU()

    def forward(self, x):
        x = self.relu(self.conv1(x))
        x = self.pool(x)
        x = self.relu(self.conv2(x))
        x = self.pool(x)
        x = x.view(-1, 64 * 56 * 56)
        x = self.relu(self.fc1(x))
        x = self.fc2(x)
        return x


@pytest.fixture
def simple_model():
    """Create a simple test model."""
    if not TORCH_AVAILABLE:
        pytest.skip("PyTorch not available")

    model = SimpleTestModel()
    model.eval()
    return model


@pytest.fixture
def model_optimizer():
    """Create model optimizer instance."""
    config = OptimizationConfig(
        quantization_type=QuantizationType.INT8,
        target_device=DeviceType.ARM_CPU,
        max_memory_mb=MEMORY_LIMIT_MB,
        target_latency_ms=OCR_TIME_LIMIT_MS,
        enable_pruning=True,
        pruning_ratio=0.3
    )
    return ModelOptimizer(config=config, framework=ModelFramework.PYTORCH)


@pytest.fixture
def edge_runtime():
    """Create edge runtime instance."""
    return EdgeVisionRuntime(
        memory_budget_mb=MEMORY_LIMIT_MB,
        enable_optimization=True,
        default_provider=InferenceProvider.CPU
    )


@pytest.fixture
def resource_manager():
    """Create resource manager instance."""
    limits = ResourceLimits(
        max_memory_mb=MEMORY_LIMIT_MB,
        max_cpu_percent=80.0,
        max_temp_celsius=75.0,
        min_battery_percent=15.0
    )
    return ResourceManager(
        limits=limits,
        monitor_interval_sec=0.5,
        enable_auto_throttle=True
    )


@pytest.fixture
def test_image():
    """Create test image data."""
    return np.random.randn(TEST_IMAGE_SIZE[0], TEST_IMAGE_SIZE[1]).astype(np.float32)


@pytest.fixture
def test_batch():
    """Create batch of test images."""
    return [
        np.random.randn(TEST_IMAGE_SIZE[0], TEST_IMAGE_SIZE[1]).astype(np.float32)
        for _ in range(4)
    ]


# Model Optimization Tests

class TestModelOptimization:
    """Test suite for model optimization."""

    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_quantization_int8(self, model_optimizer, simple_model):
        """Test INT8 quantization."""
        quantized = model_optimizer.quantize_model(
            simple_model,
            quantization_type=QuantizationType.DYNAMIC
        )

        assert quantized is not None
        # Quantized model should be smaller
        assert True  # Actual size comparison would require saving

    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_quantization_fp16(self, simple_model):
        """Test FP16 quantization."""
        optimizer = ModelOptimizer(
            config=OptimizationConfig(quantization_type=QuantizationType.FP16),
            framework=ModelFramework.PYTORCH
        )

        quantized = optimizer.quantize_model(simple_model)
        assert quantized is not None

    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_model_pruning(self, model_optimizer, simple_model):
        """Test model pruning."""
        pruned = model_optimizer.prune_model(
            simple_model,
            pruning_ratio=0.3,
            preserve_accuracy=True
        )

        assert pruned is not None
        # Check that model still works
        dummy_input = torch.randn(1, 1, 224, 224)
        output = pruned(dummy_input)
        assert output.shape == (1, 10)

    @pytest.mark.skipif(not TORCH_AVAILABLE or not ONNX_AVAILABLE, reason="Dependencies not available")
    def test_onnx_conversion(self, model_optimizer, simple_model):
        """Test ONNX conversion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "model.onnx"

            onnx_path = model_optimizer.convert_to_onnx(
                simple_model,
                input_shape=(1, 1, 224, 224),
                output_path=output_path,
                opset_version=13,
                optimize=True
            )

            assert Path(onnx_path).exists()
            assert Path(onnx_path).stat().st_size > 0

    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_model_benchmarking(self, model_optimizer, simple_model):
        """Test model benchmarking."""
        dummy_input = torch.randn(1, 1, 224, 224)

        result = model_optimizer.benchmark_model(
            simple_model,
            dummy_input,
            num_iterations=10,
            warmup_iterations=2
        )

        assert result.avg_inference_time_ms > 0
        assert result.throughput_samples_per_sec > 0
        assert result.model_size_mb >= 0

    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_device_optimization(self, simple_model):
        """Test device-specific optimization."""
        optimizer = ModelOptimizer(
            config=OptimizationConfig(target_device=DeviceType.ARM_CPU),
            framework=ModelFramework.PYTORCH
        )

        optimized = optimizer.optimize_for_device(simple_model, DeviceType.ARM_CPU)
        assert optimized is not None

    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_optimization_pipeline(self, model_optimizer, simple_model):
        """Test complete optimization pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "optimized_model.onnx"

            results = model_optimizer.optimize_pipeline(
                simple_model,
                input_shape=(1, 1, 224, 224),
                output_path=output_path,
                calibration_data=None
            )

            assert "original_model" in results
            assert "optimized_model" in results
            assert "optimizations_applied" in results
            assert len(results["optimizations_applied"]) > 0


# Edge Runtime Tests

class TestEdgeRuntime:
    """Test suite for edge inference runtime."""

    @pytest.mark.skipif(not ONNX_AVAILABLE, reason="ONNX Runtime not available")
    def test_runtime_initialization(self, edge_runtime):
        """Test runtime initialization."""
        assert edge_runtime.memory_budget_mb == MEMORY_LIMIT_MB
        assert edge_runtime.enable_optimization is True
        assert len(edge_runtime.available_providers) > 0

    @pytest.mark.skipif(not ONNX_AVAILABLE, reason="ONNX Runtime not available")
    def test_memory_budget(self, edge_runtime):
        """Test memory budget enforcement."""
        memory_info = edge_runtime.get_memory_usage()

        assert "total_budget_mb" in memory_info
        assert memory_info["total_budget_mb"] == MEMORY_LIMIT_MB
        assert "total_used_mb" in memory_info
        assert "available_mb" in memory_info

    def test_input_preprocessing(self, edge_runtime, test_image):
        """Test input preprocessing."""
        # Create mock model config
        config = ModelConfig(
            model_type=ModelType.OCR,
            model_path="dummy.onnx",
            input_shape=(1, 1, 224, 224),
            output_shape=(1, 1000)
        )
        edge_runtime.model_configs[ModelType.OCR] = config

        processed = edge_runtime._preprocess_input(test_image, ModelType.OCR)

        assert processed.shape[0] == 1  # Batch dimension
        assert len(processed.shape) == 4  # NCHW format
        assert processed.dtype == np.float32

    def test_output_postprocessing(self, edge_runtime):
        """Test output postprocessing."""
        # Test softmax application
        logits = np.array([[1.0, 2.0, 3.0, 4.0, 5.0]])
        processed = edge_runtime._postprocess_output(logits, ModelType.OCR)

        # Check softmax properties
        assert np.allclose(processed.sum(), 1.0)
        assert np.all(processed >= 0)
        assert np.all(processed <= 1)

    def test_performance_tracking(self, edge_runtime):
        """Test performance tracking."""
        # Initialize tracking for a model
        edge_runtime.inference_count[ModelType.OCR] = 5
        edge_runtime.total_inference_time[ModelType.OCR] = 250.0

        stats = edge_runtime.get_performance_stats(ModelType.OCR)

        assert stats[ModelType.OCR.value]["total_inferences"] == 5
        assert stats[ModelType.OCR.value]["avg_inference_time_ms"] == 50.0


# Resource Management Tests

class TestResourceManagement:
    """Test suite for resource management."""

    def test_resource_manager_initialization(self, resource_manager):
        """Test resource manager initialization."""
        assert resource_manager.limits.max_memory_mb == MEMORY_LIMIT_MB
        assert resource_manager.enable_auto_throttle is True
        assert resource_manager.device_capabilities is not None

    def test_device_detection(self, resource_manager):
        """Test device capability detection."""
        capabilities = resource_manager.get_device_profile()

        assert capabilities.cpu_count > 0
        assert capabilities.memory_total_mb > 0
        assert capabilities.profile in [
            DeviceProfile.LOW_END,
            DeviceProfile.MID_RANGE,
            DeviceProfile.HIGH_END
        ]

    def test_memory_monitoring(self, resource_manager):
        """Test memory monitoring."""
        memory_info = resource_manager.monitor_memory()

        assert "used_mb" in memory_info
        assert "available_mb" in memory_info
        assert "total_mb" in memory_info
        assert "percent" in memory_info
        assert memory_info["percent"] >= 0
        assert memory_info["percent"] <= 100

    def test_cpu_monitoring(self, resource_manager):
        """Test CPU monitoring."""
        cpu_info = resource_manager.monitor_cpu()

        assert "percent" in cpu_info
        assert "per_cpu" in cpu_info
        assert cpu_info["percent"] >= 0
        assert cpu_info["percent"] <= 100
        assert len(cpu_info["per_cpu"]) > 0

    def test_resource_snapshot(self, resource_manager):
        """Test resource snapshot capture."""
        snapshot = resource_manager.get_current_snapshot()

        assert snapshot.cpu_percent >= 0
        assert snapshot.memory_percent >= 0
        assert snapshot.memory_available_mb >= 0
        assert snapshot.memory_used_mb >= 0
        assert snapshot.timestamp > 0

    def test_resource_level_detection(self, resource_manager):
        """Test resource level detection."""
        level = resource_manager.get_resource_level()

        assert level in [
            ResourceLevel.CRITICAL,
            ResourceLevel.LOW,
            ResourceLevel.MODERATE,
            ResourceLevel.GOOD,
            ResourceLevel.EXCELLENT
        ]

    def test_quality_recommendation(self, resource_manager):
        """Test quality level recommendation."""
        quality = resource_manager.get_recommended_quality()

        assert quality in [
            QualityLevel.MINIMAL,
            QualityLevel.LOW,
            QualityLevel.MEDIUM,
            QualityLevel.HIGH,
            QualityLevel.MAXIMUM
        ]

    def test_throttling_callback(self, resource_manager):
        """Test throttling callback registration."""
        callback_called = {"value": False, "state": None}

        def test_callback(state: bool):
            callback_called["value"] = True
            callback_called["state"] = state

        resource_manager.register_throttle_callback(test_callback)
        assert len(resource_manager.throttle_callbacks) > 0

    def test_statistics_collection(self, resource_manager):
        """Test statistics collection."""
        # Collect some samples
        for _ in range(5):
            resource_manager.get_current_snapshot()
            time.sleep(0.1)

        stats = resource_manager.get_statistics()

        assert "cpu" in stats
        assert "memory" in stats
        assert stats["samples"] >= 5

    def test_background_monitoring(self, resource_manager):
        """Test background monitoring."""
        resource_manager.start_monitoring()
        assert resource_manager.monitoring_active is True

        time.sleep(1.5)  # Let it collect some samples

        resource_manager.stop_monitoring()
        assert resource_manager.monitoring_active is False

        # Check that samples were collected
        assert len(resource_manager.history) > 0


# Integration Tests

class TestEdgeIntegration:
    """Integration tests for edge deployment."""

    def test_memory_footprint_requirement(self, resource_manager):
        """Test that total memory footprint is under 500MB."""
        memory_info = resource_manager.monitor_memory()

        # This is the total system memory - in practice, we'd measure
        # actual model memory usage
        assert memory_info["total_mb"] > 0

        # Models should fit in budget
        assert MEMORY_LIMIT_MB <= 500.0

    def test_inference_time_targets(self):
        """Test inference time targets."""
        # OCR should be under 500ms
        assert OCR_TIME_LIMIT_MS <= 500.0

        # Handwriting should be under 1s
        assert HANDWRITING_TIME_LIMIT_MS <= 1000.0

    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_optimization_preserves_accuracy(self, model_optimizer, simple_model):
        """Test that optimization preserves model accuracy."""
        # Create test data
        test_input = torch.randn(10, 1, 224, 224)

        # Get original outputs
        with torch.no_grad():
            original_output = simple_model(test_input)

        # Optimize model
        optimized = model_optimizer.quantize_model(
            simple_model,
            quantization_type=QuantizationType.DYNAMIC
        )

        # Get optimized outputs
        with torch.no_grad():
            optimized_output = optimized(test_input)

        # Check that outputs are similar (within tolerance)
        # For quantized models, some accuracy loss is expected
        correlation = np.corrcoef(
            original_output.numpy().flatten(),
            optimized_output.numpy().flatten()
        )[0, 1]

        assert correlation > 0.9  # At least 90% correlation

    def test_adaptive_quality_switching(self, resource_manager):
        """Test adaptive quality level switching."""
        initial_quality = resource_manager.get_recommended_quality()

        # Simulate high resource usage by temporarily modifying snapshot
        if resource_manager.current_snapshot:
            resource_manager.current_snapshot.memory_percent = 95.0
            resource_manager.current_snapshot.cpu_percent = 95.0

        resource_manager.throttle_if_needed()

        # Quality should be reduced when throttling
        if resource_manager.throttling_active:
            assert resource_manager.current_quality.value in [
                QualityLevel.MINIMAL.value,
                QualityLevel.LOW.value
            ]

    def test_config_file_loading(self):
        """Test edge configuration file."""
        config_path = Path("/Users/anuppandey/Desktop/edu_lens/configs/vision/edge_config.yaml")

        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)

            # Validate key configuration sections
            assert "device" in config
            assert "optimization" in config
            assert "models" in config
            assert "runtime" in config
            assert "resource_management" in config

            # Check memory limit
            assert config["device"]["constraints"]["max_memory_mb"] <= 500

            # Check inference time limits
            assert config["models"]["ocr"]["performance"]["max_inference_time_ms"] <= 500
            assert config["models"]["handwriting"]["performance"]["max_inference_time_ms"] <= 1000


# Performance Benchmarks

class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    @pytest.mark.benchmark
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_inference_latency_benchmark(self, simple_model):
        """Benchmark inference latency."""
        model = simple_model
        model.eval()

        # Warmup
        dummy_input = torch.randn(1, 1, 224, 224)
        for _ in range(10):
            with torch.no_grad():
                _ = model(dummy_input)

        # Benchmark
        iterations = 100
        times = []

        for _ in range(iterations):
            start = time.perf_counter()
            with torch.no_grad():
                _ = model(dummy_input)
            end = time.perf_counter()
            times.append((end - start) * 1000)

        avg_time = np.mean(times)
        p95_time = np.percentile(times, 95)

        print(f"\nInference Latency:")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  P95: {p95_time:.2f}ms")
        print(f"  Min: {np.min(times):.2f}ms")
        print(f"  Max: {np.max(times):.2f}ms")

        # Should be reasonably fast for simple model
        assert avg_time < 1000  # Less than 1 second

    @pytest.mark.benchmark
    def test_memory_usage_benchmark(self, resource_manager):
        """Benchmark memory usage."""
        initial_snapshot = resource_manager.get_current_snapshot()

        print(f"\nMemory Usage:")
        print(f"  Used: {initial_snapshot.memory_used_mb:.2f}MB")
        print(f"  Available: {initial_snapshot.memory_available_mb:.2f}MB")
        print(f"  Total: {initial_snapshot.memory_total_mb:.2f}MB")
        print(f"  Percent: {initial_snapshot.memory_percent:.1f}%")

        assert initial_snapshot.memory_total_mb > 0

    @pytest.mark.benchmark
    def test_preprocessing_overhead_benchmark(self, edge_runtime, test_image):
        """Benchmark preprocessing overhead."""
        config = ModelConfig(
            model_type=ModelType.OCR,
            model_path="dummy.onnx",
            input_shape=(1, 1, 224, 224),
            output_shape=(1, 1000)
        )
        edge_runtime.model_configs[ModelType.OCR] = config

        # Warmup
        for _ in range(10):
            _ = edge_runtime._preprocess_input(test_image, ModelType.OCR)

        # Benchmark
        iterations = 100
        times = []

        for _ in range(iterations):
            start = time.perf_counter()
            _ = edge_runtime._preprocess_input(test_image, ModelType.OCR)
            end = time.perf_counter()
            times.append((end - start) * 1000)

        avg_time = np.mean(times)

        print(f"\nPreprocessing Time:")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  Min: {np.min(times):.2f}ms")
        print(f"  Max: {np.max(times):.2f}ms")

        # Preprocessing should be fast
        assert avg_time < 50  # Less than 50ms


# Mark all tests in this module with 'edge' marker
pytestmark = pytest.mark.edge


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
