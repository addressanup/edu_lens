# EduLens Pipeline Integration

Complete end-to-end pipeline integration for the EduLens educational AI tutoring system.

## Overview

The EduLens pipeline orchestrates the complete Vision → AI → Voice flow, providing seamless tutoring assistance for elementary students (ages 6-12). The system processes visual input from homework, generates age-appropriate Socratic responses, and delivers them through natural speech.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    EduLens Pipeline                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐ │
│  │  Vision  │──▶│    AI    │──▶│  Voice   │──▶│   TTS   │ │
│  │ Pipeline │   │  Tutor   │   │  Bridge  │   │ Output  │ │
│  └──────────┘   └──────────┘   └──────────┘   └─────────┘ │
│       │              │               │              │        │
│       ▼              ▼               ▼              ▼        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Pipeline Coordinator                        │  │
│  │  • Task Scheduling  • Concurrency  • Priority Queue  │  │
│  └──────────────────────────────────────────────────────┘  │
│       │              │               │              │        │
│       ▼              ▼               ▼              ▼        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Error Handler & Health Checker             │  │
│  │  • Recovery  • Degradation  • Monitoring  • Alerts  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. EduLensPipeline (`edulens_pipeline.py`)

Main orchestrator for the complete tutoring system.

**Key Features:**
- Full event-driven architecture
- Component lifecycle management
- Vision → AI → Voice flow coordination
- Session management
- Performance monitoring

**Usage:**
```python
from src.pipeline.edulens_pipeline import EduLensPipeline, PipelineConfig, PipelineMode

# Configure pipeline
config = PipelineConfig(
    mode=PipelineMode.FULL,
    student_age=8,
    student_grade="3",
    enable_vision=True,
    enable_audio=True
)

# Create and initialize
pipeline = EduLensPipeline(config=config)
await pipeline.initialize()
await pipeline.start()

# Start tutoring session
session_id = await pipeline.start_session(student_id="student_123")

# Process homework frame
visual_context = await pipeline.process_frame(
    frame_data=camera_frame,
    ocr_result=ocr_data
)

# Generate and deliver response
response = await pipeline.generate_response(
    student_query="How do I solve this?",
    visual_context=visual_context
)

await pipeline.deliver_response(
    response_text=response["response"],
    response_type=response["response_type"]
)

# Or use complete interaction
await pipeline.process_interaction(
    student_query="Help me with this problem",
    visual_context=visual_context
)

# Stop when done
await pipeline.stop()
```

**Pipeline Modes:**
- `FULL`: Complete vision + audio + AI
- `AUDIO_ONLY`: Audio interaction without vision
- `VISION_ONLY`: Vision processing without audio
- `MANUAL`: Manual control for testing

### 2. PipelineCoordinator (`pipeline_coordinator.py`)

Manages concurrent task execution with priority-based scheduling.

**Key Features:**
- Worker pool management
- Priority queues (CRITICAL, HIGH, NORMAL, LOW)
- Task lifecycle tracking
- Concurrent execution limits
- Performance metrics

**Usage:**
```python
from src.pipeline.pipeline_coordinator import (
    PipelineCoordinator, TaskPriority, create_coordinator
)

# Create coordinator
coordinator = await create_coordinator(
    max_concurrent_tasks=5,
    max_queue_size=100
)

# Schedule tasks
async def process_vision_frame(frame):
    # Process frame
    return result

task_id = await coordinator.schedule_task(
    task_type="process_frame",
    coroutine=process_vision_frame(frame),
    priority=TaskPriority.NORMAL
)

# Wait for completion
result = await coordinator.wait_for_task(task_id, timeout=5.0)

# High-level operations
await coordinator.start_session(session_id, student_id)
await coordinator.process_frame(frame_data, session_id, processor)
await coordinator.generate_response(query, context, session_id, generator)
await coordinator.deliver_response(text, session_id, deliverer)

# Get statistics
stats = coordinator.get_stats()
print(f"Completed: {stats.tasks_completed}")
print(f"Average duration: {stats.average_task_duration_ms:.1f}ms")

await coordinator.stop()
```

### 3. ErrorHandler (`error_handler.py`)

Comprehensive error handling with automatic recovery strategies.

**Key Features:**
- Error classification (Vision, Audio, AI, Hardware, etc.)
- Automatic recovery attempts
- Graceful degradation
- Error escalation
- Recovery statistics

**Usage:**
```python
from src.pipeline.error_handler import (
    ErrorHandler, RecoveryConfig, create_error_handler
)

# Configure recovery
config = RecoveryConfig(
    max_retries=3,
    retry_delay_seconds=1.0,
    exponential_backoff=True,
    enable_degradation=True
)

# Create handler
async def escalation_callback(error_record):
    print(f"ESCALATED: {error_record.error_message}")
    # Notify parent/operator

error_handler = create_error_handler(
    config=config,
    escalation_callback=escalation_callback
)

# Handle errors
try:
    # Vision operation
    result = await process_camera()
except Exception as e:
    success, result = await error_handler.handle_vision_error(
        error=e,
        component="camera_module",
        context={"frame_id": 123}
    )

    if not success:
        print("Recovery failed")

# Check component status
if error_handler.is_component_degraded("camera_module"):
    print("Camera operating in degraded mode")

# Get statistics
stats = error_handler.get_error_stats()
print(f"Total errors: {stats.total_errors}")
print(f"Successful recoveries: {stats.successful_recoveries}")
```

**Recovery Strategies:**
- `RETRY`: Retry operation with exponential backoff
- `FALLBACK`: Use alternative method/component
- `DEGRADE`: Reduce functionality to maintain operation
- `RESTART_COMPONENT`: Restart the failing component
- `SKIP`: Skip operation and continue
- `ESCALATE`: Notify operator for manual intervention

### 4. HealthChecker (`health_checker.py`)

System health monitoring and diagnostics.

**Key Features:**
- Component health tracking
- System resource monitoring (CPU, memory, disk)
- Automatic health checks
- Diagnostic tests
- Health history

**Usage:**
```python
from src.pipeline.health_checker import (
    HealthChecker, HealthCheckConfig, ComponentType, create_health_checker
)

# Configure monitoring
config = HealthCheckConfig(
    check_interval_seconds=30.0,
    cpu_threshold_percent=90.0,
    memory_threshold_percent=85.0
)

# Create checker
async def health_alert(component_health):
    print(f"ALERT: {component_health.component_name} is unhealthy")

health_checker = create_health_checker(
    config=config,
    alert_callback=health_alert
)

# Register components
health_checker.register_component(
    component_name="vision_pipeline",
    component_type=ComponentType.VISION,
    component=vision_component
)

health_checker.register_component(
    component_name="audio_pipeline",
    component_type=ComponentType.AUDIO,
    component=audio_component
)

# Start monitoring
await health_checker.start_monitoring()

# Check specific component
component_health = await health_checker.get_component_status("vision_pipeline")
print(f"Status: {component_health.status.name}")
print(f"Uptime: {component_health.uptime_seconds:.1f}s")

# Check all components
system_health = await health_checker.check_all_components()
print(f"Overall: {system_health.overall_status.name}")
print(f"Components: {len(system_health.components)}")

# Run diagnostics
diagnostic_results = await health_checker.run_diagnostics()
for result in diagnostic_results:
    status = "✓" if result.passed else "✗"
    print(f"{status} {result.test_name}: {result.message}")

# Stop monitoring
await health_checker.stop_monitoring()
```

## Event Flow

The pipeline uses an event-driven architecture for loose coupling:

```python
# Event types
EventType.VISION_FRAME_CAPTURED
EventType.VISION_TEXT_DETECTED
EventType.AUDIO_WAKE_WORD_DETECTED
EventType.AUDIO_TRANSCRIPTION_READY
EventType.AI_RESPONSE_GENERATED
EventType.AUDIO_TTS_STARTED
EventType.SESSION_STARTED
EventType.SYSTEM_ERROR

# Subscribe to events
from src.core.event_bus import get_event_bus

event_bus = get_event_bus()

async def on_transcription(event):
    text = event.payload.get("transcription")
    print(f"Student said: {text}")

event_bus.subscribe(EventType.AUDIO_TRANSCRIPTION_READY, on_transcription)

# Events are published automatically by pipeline components
```

## Complete Example

```python
import asyncio
from src.pipeline.edulens_pipeline import EduLensPipeline, PipelineConfig
from src.pipeline.error_handler import create_error_handler
from src.pipeline.health_checker import create_health_checker

async def main():
    # Create error handler
    error_handler = create_error_handler()

    # Create health checker
    health_checker = create_health_checker()

    # Configure pipeline
    config = PipelineConfig(
        student_age=8,
        student_grade="3",
        enable_vision=True,
        enable_audio=True
    )

    # Create and start pipeline
    pipeline = EduLensPipeline(config=config)
    await pipeline.initialize()

    # Register with health checker
    health_checker.register_component(
        "edulens_pipeline",
        ComponentType.PIPELINE,
        pipeline
    )

    # Start everything
    await pipeline.start()
    await health_checker.start_monitoring()

    # Start tutoring session
    session_id = await pipeline.start_session(student_id="alice_123")

    # Main tutoring loop
    while True:
        try:
            # Capture and process frame
            frame = await capture_camera_frame()
            ocr_result = await perform_ocr(frame)

            visual_context = await pipeline.process_frame(
                frame_data=frame,
                ocr_result=ocr_result
            )

            # Wait for student question
            # (Audio pipeline handles wake word and ASR automatically)

            # Process interaction when student speaks
            # (This is handled by pipeline's audio event handlers)

            # Check health periodically
            health = await pipeline.health_check()
            if not health.is_healthy:
                print("Pipeline unhealthy, checking diagnostics...")
                diagnostics = await health_checker.run_diagnostics()

            await asyncio.sleep(0.1)

        except Exception as e:
            # Handle errors
            success, _ = await error_handler.handle_vision_error(
                error=e,
                component="main_loop",
                context={"session_id": session_id}
            )

            if not success:
                print("Unrecoverable error, stopping...")
                break

    # Clean shutdown
    await health_checker.stop_monitoring()
    await pipeline.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## Testing

Run the end-to-end integration tests:

```bash
# Run all integration tests
pytest tests/integration/test_e2e_pipeline.py -v

# Run specific test class
pytest tests/integration/test_e2e_pipeline.py::TestEduLensPipeline -v

# Run with coverage
pytest tests/integration/test_e2e_pipeline.py --cov=src/pipeline --cov-report=html

# Run async tests
pytest tests/integration/test_e2e_pipeline.py --asyncio-mode=auto -v
```

## Performance Characteristics

- **Latency**: < 2 seconds end-to-end (vision → AI → TTS)
- **Throughput**: 5 FPS vision processing
- **Concurrency**: Up to 5 concurrent operations
- **Recovery Time**: < 3 seconds for automatic recovery
- **Memory**: ~500MB typical operation
- **CPU**: < 70% average utilization

## Error Handling Strategies

1. **Vision Errors**
   - Camera: Restart camera module
   - OCR: Retry with adjusted settings
   - Handwriting: Fall back to printed text OCR

2. **Audio Errors**
   - Microphone: Restart audio system
   - ASR: Use fallback model
   - TTS: Switch to alternative engine

3. **AI Errors**
   - Timeout: Retry with increased timeout
   - Resource: Reduce model size/context
   - Model: Fall back to simpler model

## Monitoring & Diagnostics

The system provides comprehensive monitoring:

- **Component Health**: Real-time status of all components
- **System Resources**: CPU, memory, disk usage
- **Error Statistics**: Error counts, recovery rates
- **Performance Metrics**: Latency, throughput, task durations
- **Diagnostic Tests**: Automated component testing

## Production Deployment

For production deployment:

1. Enable health monitoring:
   ```python
   config.check_interval_seconds = 30.0
   ```

2. Configure error escalation:
   ```python
   async def escalate_to_operator(error_record):
       # Send notification to parent/operator
       await send_notification(error_record)

   error_handler = create_error_handler(escalation_callback=escalate_to_operator)
   ```

3. Set resource limits:
   ```python
   config.max_concurrent_operations = 5
   config.operation_timeout_seconds = 30.0
   ```

4. Enable graceful degradation:
   ```python
   config.enable_graceful_degradation = True
   ```

## Contributing

When adding new components to the pipeline:

1. Implement `health_check()` method
2. Publish events for key operations
3. Handle errors appropriately
4. Add integration tests
5. Update documentation

## License

Copyright © 2025 EduLens Project. All rights reserved.
