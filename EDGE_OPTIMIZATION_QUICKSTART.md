# Edge Optimization Quick Start Guide

## Overview

This guide provides quick examples for using the edge optimization components to deploy vision models on smart glasses hardware.

## Installation

```bash
# Install required dependencies
pip install torch torchvision onnx onnxruntime psutil pyyaml

# Optional: For GPU support
pip install onnxruntime-gpu

# Optional: For TensorFlow models
pip install tensorflow tf2onnx
```

## Quick Examples

### 1. Optimize a Model

```python
from src.vision.model_optimizer import (
    ModelOptimizer,
    OptimizationConfig,
    QuantizationType,
    DeviceType
)

# Configure optimization
config = OptimizationConfig(
    quantization_type=QuantizationType.INT8,
    target_device=DeviceType.ARM_CPU,
    max_memory_mb=150,
    target_latency_ms=500,
    enable_pruning=True,
    pruning_ratio=0.3
)

# Create optimizer
optimizer = ModelOptimizer(config=config)

# Load your model (PyTorch example)
import torch
model = torch.load("my_model.pth")
model.eval()

# Run optimization pipeline
results = optimizer.optimize_pipeline(
    model=model,
    input_shape=(1, 1, 224, 224),
    output_path="models/optimized_model.onnx"
)

print(f"Original: {results['original_model']['avg_inference_time_ms']:.2f}ms")
print(f"Optimized: {results['optimized_model']['avg_inference_time_ms']:.2f}ms")
print(f"Speedup: {results['improvements']['speedup']}")
```

### 2. Deploy and Run Inference

```python
from src.vision.edge_runtime import EdgeVisionRuntime, ModelType
import numpy as np
import cv2

# Initialize runtime
runtime = EdgeVisionRuntime(
    memory_budget_mb=500,
    enable_optimization=True
)

# Load optimized model
runtime.load_optimized_model(
    model_path="models/optimized_model.onnx",
    model_type=ModelType.OCR
)

# Warm up model
runtime.warm_up(ModelType.OCR, num_iterations=5)

# Load and preprocess image
image = cv2.imread("test_image.jpg", cv2.IMREAD_GRAYSCALE)
image = cv2.resize(image, (224, 224))
image = image.astype(np.float32) / 255.0

# Run inference
result = runtime.run_inference(
    input_data=image,
    model_type=ModelType.OCR,
    preprocess=True
)

print(f"Inference time: {result.inference_time_ms:.2f}ms")
print(f"Total time: {result.total_time_ms:.2f}ms")
print(f"Output shape: {result.output.shape}")
```

### 3. Monitor Resources

```python
from src.runtime.resource_manager import (
    ResourceManager,
    ResourceLimits,
    QualityLevel
)

# Configure resource limits
limits = ResourceLimits(
    max_memory_mb=500,
    max_cpu_percent=80,
    max_temp_celsius=75,
    min_battery_percent=15
)

# Initialize manager
manager = ResourceManager(
    limits=limits,
    enable_auto_throttle=True
)

# Start background monitoring
manager.start_monitoring()

# Register callback for throttling
def on_throttle(is_active):
    if is_active:
        print("⚠️  Throttling activated - reducing quality")
    else:
        print("✅ Throttling deactivated - normal operation")

manager.register_throttle_callback(on_throttle)

# Get current status
snapshot = manager.get_current_snapshot()
print(f"CPU: {snapshot.cpu_percent:.1f}%")
print(f"Memory: {snapshot.memory_used_mb:.0f}MB / {snapshot.memory_total_mb:.0f}MB")

# Get recommended quality
quality = manager.get_recommended_quality()
print(f"Recommended quality: {quality.value}")
```

### 4. Complete Integration Example

```python
from src.vision.model_optimizer import ModelOptimizer, OptimizationConfig
from src.vision.edge_runtime import EdgeVisionRuntime, ModelType
from src.runtime.resource_manager import ResourceManager
import torch
import numpy as np

# 1. Optimize model (do this once, offline)
print("Step 1: Optimizing model...")
optimizer = ModelOptimizer()
model = torch.load("ocr_model.pth")
model.eval()

results = optimizer.optimize_pipeline(
    model=model,
    input_shape=(1, 1, 224, 224),
    output_path="models/ocr_optimized.onnx"
)
print(f"✅ Model optimized: {results['improvements']['size_reduction']} size reduction")

# 2. Initialize runtime and resource manager
print("\nStep 2: Initializing runtime...")
manager = ResourceManager(enable_auto_throttle=True)
manager.start_monitoring()

runtime = EdgeVisionRuntime(memory_budget_mb=500)
runtime.load_optimized_model(
    model_path="models/ocr_optimized.onnx",
    model_type=ModelType.OCR
)
runtime.warm_up(ModelType.OCR)
print("✅ Runtime initialized and warmed up")

# 3. Process images with adaptive quality
print("\nStep 3: Processing images...")
test_images = [np.random.randn(224, 224).astype(np.float32) for _ in range(10)]

for i, image in enumerate(test_images):
    # Check resources and adjust quality
    manager.throttle_if_needed()
    quality = manager.get_recommended_quality()

    # Run inference
    result = runtime.run_inference(image, ModelType.OCR)

    print(f"Image {i+1}: {result.inference_time_ms:.1f}ms, Quality: {quality.value}")

# 4. Get statistics
print("\nStep 4: Performance statistics...")
runtime_stats = runtime.get_performance_stats()
resource_stats = manager.get_statistics()

print(f"Average inference: {runtime_stats['ocr']['avg_inference_time_ms']:.2f}ms")
print(f"Average CPU: {resource_stats['cpu']['avg']:.1f}%")
print(f"Average Memory: {resource_stats['memory']['avg']:.1f}%")

# Cleanup
manager.stop_monitoring()
runtime.clear_all()
print("\n✅ Done!")
```

## Configuration

### Load from Config File

```python
import yaml

# Load edge configuration
with open("configs/vision/edge_config.yaml") as f:
    config = yaml.safe_load(f)

# Extract settings
memory_limit = config["device"]["constraints"]["max_memory_mb"]
ocr_time_limit = config["models"]["ocr"]["performance"]["max_inference_time_ms"]

print(f"Memory limit: {memory_limit}MB")
print(f"OCR time limit: {ocr_time_limit}ms")
```

## Batch Processing

```python
# Process multiple images efficiently
images = [load_image(f"image_{i}.jpg") for i in range(10)]

# Batch inference
results = runtime.batch_inference(
    input_batch=images,
    model_type=ModelType.OCR,
    batch_size=4
)

for i, result in enumerate(results):
    print(f"Image {i}: {result.inference_time_ms:.2f}ms")
```

## Performance Benchmarking

```python
# Benchmark a model
benchmark_result = optimizer.benchmark_model(
    model=my_model,
    input_data=dummy_input,
    num_iterations=100,
    warmup_iterations=10
)

print(f"Average: {benchmark_result.avg_inference_time_ms:.2f}ms")
print(f"P95: {benchmark_result.min_inference_time_ms:.2f}ms")
print(f"Throughput: {benchmark_result.throughput_samples_per_sec:.2f} samples/sec")
print(f"Memory: {benchmark_result.memory_usage_mb:.2f}MB")
```

## Testing

```bash
# Run all edge tests
pytest tests/vision/test_edge_performance.py -v

# Run specific test
pytest tests/vision/test_edge_performance.py::TestModelOptimization::test_quantization_int8 -v

# Run benchmarks
pytest tests/vision/test_edge_performance.py -m benchmark -v -s
```

## Troubleshooting

### Issue: ONNX Runtime not found
```bash
pip install onnxruntime
# or for GPU support:
pip install onnxruntime-gpu
```

### Issue: Model too large
```python
# Increase pruning ratio
config.pruning_ratio = 0.5  # Remove 50% of weights

# Or use more aggressive quantization
config.quantization_type = QuantizationType.INT8
```

### Issue: Inference too slow
```python
# 1. Ensure model is warmed up
runtime.warm_up(ModelType.OCR, num_iterations=10)

# 2. Enable graph optimizations
runtime.enable_optimization = True

# 3. Check execution provider
print(runtime.available_providers)
# Use GPU if available: InferenceProvider.CUDA
```

### Issue: High memory usage
```python
# 1. Unload unused models
runtime.unload_model(ModelType.LAYOUT)

# 2. Reduce batch size
batch_size = 1

# 3. Enable auto-throttling
manager.enable_auto_throttle = True
```

## Key Performance Targets

| Metric | Target | How to Verify |
|--------|--------|---------------|
| Total Memory | <500MB | `runtime.get_memory_usage()` |
| OCR Inference | <500ms | `result.inference_time_ms` |
| Handwriting Inference | <1000ms | `result.inference_time_ms` |
| Model Size (each) | <200MB | Check ONNX file size |

## Best Practices

1. **Always warm up models** before production inference
2. **Use batch inference** when processing multiple images
3. **Enable resource monitoring** for adaptive quality
4. **Cache preprocessed inputs** when possible
5. **Profile models** before deployment
6. **Test on target hardware** (ARM device if possible)

## Next Steps

1. Optimize your custom models with ModelOptimizer
2. Test on actual edge hardware (Raspberry Pi, Jetson Nano)
3. Fine-tune configuration based on real-world performance
4. Integrate with full EduLens pipeline
5. Deploy to smart glasses

## Support

For issues or questions:
- Check test suite: `tests/vision/test_edge_performance.py`
- Review documentation: `EDGE_OPTIMIZATION_IMPLEMENTATION.md`
- Examine config: `configs/vision/edge_config.yaml`
