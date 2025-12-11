# EduLens Audio Pipeline

Unified voice interaction pipeline integrating wake word detection, automatic speech recognition (ASR), and text-to-speech (TTS) for seamless educational voice experiences.

## Overview

The audio pipeline provides a complete voice interaction system with:

- **State Machine Architecture**: Clean state transitions from wake word → listening → processing → speaking
- **Sub-2-Second Latency**: Optimized for real-time interaction with comprehensive latency monitoring
- **Barge-in Support**: Students can interrupt TTS responses naturally
- **Educational Optimizations**: Tuned for children's voices (ages 6-12) and educational vocabulary

## Architecture

### State Flow

```
IDLE → WAKE_DETECTED → LISTENING → PROCESSING → SPEAKING → IDLE
         ↑                                            |
         └──────────── (barge-in) ──────────────────┘
```

### Components

1. **AudioPipeline** (`audio_pipeline.py`)
   - Main orchestrator integrating all components
   - State machine management
   - Event-driven callbacks
   - Async/await architecture

2. **AudioBuffer** (`audio_buffer.py`)
   - Ring buffer for continuous audio streaming
   - Automatic silence detection
   - Speech segment extraction
   - Real-time audio level monitoring

3. **LatencyMonitor** (`latency_monitor.py`)
   - End-to-end latency tracking
   - Per-stage timing breakdown
   - Automatic threshold alerts
   - Statistical analysis (p50, p95, p99)

4. **InterruptionHandler** (`interruption_handler.py`)
   - Barge-in detection during TTS
   - Configurable sensitivity
   - False positive prevention
   - Graceful playback management

## Quick Start

### Basic Usage

```python
import asyncio
from pathlib import Path
from src.audio.audio_pipeline import create_pipeline, PipelineState

async def main():
    # Create pipeline with default config
    pipeline = await create_pipeline()

    # Register callbacks
    pipeline.on_state_change(
        PipelineState.LISTENING,
        lambda e: print("Listening for speech...")
    )

    # Start pipeline
    await pipeline.start()

    # Pipeline now runs continuously
    # Say "Hey EduLens" to trigger interaction

    try:
        await asyncio.sleep(3600)  # Run for 1 hour
    finally:
        await pipeline.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### With Configuration File

```python
from pathlib import Path
from src.audio.audio_pipeline import AudioPipeline, PipelineConfig

# Load configuration
config_path = Path("configs/audio/pipeline_config.yaml")
config = PipelineConfig.from_yaml(config_path)

# Create pipeline
pipeline = AudioPipeline(config)
await pipeline.initialize()
await pipeline.start()
```

## Configuration

Configuration file: `/configs/audio/pipeline_config.yaml`

### Key Settings

```yaml
# Audio Settings
sample_rate: 16000
channels: 1
chunk_size: 1024

# Wake Word
wake_word_sensitivity: 0.5  # 0.0-1.0

# ASR
asr_model_size: "base"  # tiny, base, small, medium, large
asr_language: "en"

# TTS
tts_backend: "pyttsx3"  # pyttsx3, edge, coqui
tts_speed: 1.0

# Latency
latency_threshold: 2000.0  # milliseconds

# Barge-in
enable_barge_in: true
barge_in_sensitivity: 0.7
```

## API Reference

### AudioPipeline

Main pipeline class for voice interaction.

#### Methods

**`async initialize()`**
- Initialize all pipeline components
- Must be called before `start()`

**`async start()`**
- Start audio capture and processing
- Begins listening for wake word

**`async stop()`**
- Stop pipeline and clean up resources

**`async handle_wake_word(detection: DetectionResult)`**
- Handle wake word detection
- Transitions to LISTENING state

**`async handle_speech_end(segment: SpeechSegment)`**
- Process completed speech input
- Runs ASR and queues response

**`async play_response(text: str, priority: bool = False)`**
- Synthesize and play TTS response
- `priority=True` interrupts current speech

**`async handle_barge_in(event: InterruptionEvent)`**
- Handle student interruption during TTS
- Pauses playback and returns to LISTENING

**`on_state_change(state: PipelineState, callback: Callable)`**
- Register callback for specific state
- Called on state entry

**`on_event(callback: Callable)`**
- Register callback for all events
- Receives PipelineEvent objects

**`get_state() -> PipelineState`**
- Get current pipeline state

**`get_latency_stats() -> Dict`**
- Get latency statistics

**`is_healthy() -> bool`**
- Check pipeline health status

### AudioBuffer

Ring buffer for audio streaming with speech detection.

#### Methods

**`add_samples(samples: np.ndarray)`**
- Add audio samples to buffer

**`get_speech_segment(timeout: float = 0.0) -> Optional[SpeechSegment]`**
- Extract detected speech segment
- Returns None if no complete segment

**`get_latest(duration: float) -> np.ndarray`**
- Get most recent audio

**`clear()`**
- Clear buffer and reset state

**`get_level() -> float`**
- Get current RMS audio level

**`is_silent() -> bool`**
- Check if current audio is silent

**`has_speech() -> bool`**
- Check if buffer contains speech

### LatencyMonitor

Track and monitor pipeline latency.

#### Methods

**`start_timer(session_id: str)`**
- Start timing a new session

**`record_checkpoint(session_id: str, stage: PipelineStage, metadata: Dict = None)`**
- Record timing checkpoint

**`get_total_latency(session_id: str) -> float`**
- Get current session latency (ms)

**`get_breakdown(session_id: str) -> Dict[str, float]`**
- Get per-stage latency breakdown

**`end_timer(session_id: str) -> LatencyMetrics`**
- End session and compute metrics

**`get_statistics() -> LatencyStats`**
- Get aggregate statistics

**`is_healthy() -> bool`**
- Check if meeting latency targets (p95 < threshold)

### InterruptionHandler

Handle barge-in interruptions during TTS playback.

#### Methods

**`start_monitoring()`**
- Start monitoring for interruptions

**`stop_monitoring()`**
- Stop monitoring

**`set_playback_state(is_playing: bool)`**
- Set current TTS playback state

**`detect_interruption(audio_data: np.ndarray, sample_rate: int) -> Optional[InterruptionEvent]`**
- Detect interruption in audio
- Returns InterruptionEvent if detected

**`pause_playback() -> bool`**
- Pause current TTS playback

**`resume_playback() -> bool`**
- Resume paused playback

**`cancel_response()`**
- Cancel current response completely

**`set_sensitivity(sensitivity: float)`**
- Adjust interruption sensitivity (0.0-1.0)

**`get_statistics() -> dict`**
- Get interruption statistics

## Pipeline States

```python
class PipelineState(Enum):
    IDLE = "idle"                    # Waiting for wake word
    WAKE_DETECTED = "wake_detected"  # Wake word detected
    LISTENING = "listening"          # Listening for speech
    PROCESSING = "processing"        # Processing speech (ASR)
    SPEAKING = "speaking"            # Playing TTS response
    ERROR = "error"                  # Error state
    STOPPED = "stopped"              # Pipeline stopped
```

## Latency Targets

The pipeline is optimized for sub-2-second total latency:

| Stage | Target | Typical |
|-------|--------|---------|
| Wake word detection | <100ms | ~50ms |
| Speech start detection | <200ms | ~150ms |
| ASR (base model) | <500ms | ~300ms |
| Response generation | <500ms | ~200ms |
| TTS synthesis | <500ms | ~300ms |
| **Total (speech end → response start)** | **<2000ms** | **~1000ms** |

## Event System

### Pipeline Events

Every state transition generates a `PipelineEvent`:

```python
@dataclass
class PipelineEvent:
    state: PipelineState
    previous_state: PipelineState
    timestamp: float
    session_id: str
    data: Optional[Dict[str, Any]]
```

### Registering Callbacks

```python
# State-specific callback
def on_listening(event: PipelineEvent):
    print(f"Started listening at {event.timestamp}")

pipeline.on_state_change(PipelineState.LISTENING, on_listening)

# General event callback
def on_any_event(event: PipelineEvent):
    print(f"{event.previous_state.value} → {event.state.value}")

pipeline.on_event(on_any_event)
```

### Async Callbacks

```python
async def on_processing(event: PipelineEvent):
    print("Processing speech...")
    # Can await other async operations
    await some_async_operation()

pipeline.on_state_change(PipelineState.PROCESSING, on_processing)
```

## Barge-in Feature

Students can interrupt TTS responses naturally by speaking:

```python
# Enable barge-in (default: enabled)
config = PipelineConfig(
    enable_barge_in=True,
    barge_in_sensitivity=0.7  # 0.0-1.0
)

# Adjust sensitivity at runtime
pipeline._interruption_handler.set_sensitivity(0.8)

# Handle interruption events
def on_interrupt(event: InterruptionEvent):
    print(f"Interrupted! Level: {event.audio_level:.3f}")

pipeline._interruption_handler.on_interrupt(on_interrupt)
```

### Sensitivity Settings

- **0.0-0.3**: Very conservative (low false positives, may miss real interruptions)
- **0.4-0.6**: Balanced (good for most use cases)
- **0.7-0.9**: Sensitive (catches most interruptions, some false positives)
- **1.0**: Maximum sensitivity (very responsive, higher false positive rate)

## Monitoring & Diagnostics

### Health Check

```python
# Check overall health
is_healthy = pipeline.is_healthy()

# Get latency statistics
stats = pipeline.get_latency_stats()
print(f"Average latency: {stats['avg_latency']:.1f}ms")
print(f"P95 latency: {stats['p95_latency']:.1f}ms")
print(f"Violations: {stats['violation_rate'] * 100:.1f}%")
```

### Latency Breakdown

```python
# Get detailed breakdown for a session
session_id = pipeline._current_session_id
breakdown = pipeline._latency_monitor.get_breakdown(session_id)

for stage, latency in breakdown.items():
    print(f"{stage}: {latency:.1f}ms")
```

### Buffer Statistics

```python
# Get buffer statistics
stats = pipeline._audio_buffer.get_statistics()
print(f"Buffer fill: {stats['fill_percentage'] * 100:.1f}%")
print(f"Audio level: {stats['current_level']:.3f}")
print(f"Has speech: {stats['has_speech']}")
```

## Testing

Run integration tests:

```bash
# Run all tests
pytest tests/audio/test_audio_pipeline.py -v

# Run specific test class
pytest tests/audio/test_audio_pipeline.py::TestStateTransitions -v

# Run with coverage
pytest tests/audio/test_audio_pipeline.py --cov=src.audio --cov-report=html
```

## Examples

See `/examples/audio_pipeline_demo.py` for a complete working example.

```bash
# Run demo
python examples/audio_pipeline_demo.py
```

## Performance Optimization

### CPU Usage

- Use smaller ASR models (tiny/base) for edge devices
- Enable int8 quantization for TTS
- Adjust chunk size for balance between latency and CPU

### Memory Usage

- Reduce buffer duration for lower memory footprint
- Limit wake word model size
- Use streaming TTS for long responses

### Latency

- Use local TTS backend (pyttsx3) instead of cloud (edge-tts)
- Optimize ASR model size vs accuracy tradeoff
- Enable GPU acceleration if available

## Troubleshooting

### High Latency

1. Check latency breakdown: `pipeline.get_latency_stats()`
2. Identify bottleneck stage
3. Optimize specific component:
   - ASR: Use smaller model
   - TTS: Switch to faster backend
   - Network: Use offline models

### False Wake Word Detections

1. Reduce wake word sensitivity
2. Increase detection interval
3. Train custom wake word model

### Missed Interruptions

1. Increase barge-in sensitivity
2. Reduce speech threshold
3. Check microphone audio levels

### High CPU Usage

1. Use smaller models
2. Increase chunk size
3. Reduce sample rate (if acceptable)

## Future Enhancements

- [ ] GPU acceleration for ASR/TTS
- [ ] Streaming ASR for lower latency
- [ ] Multi-language support
- [ ] Voice activity detection improvements
- [ ] Cloud ASR/TTS fallback
- [ ] Speaker identification
- [ ] Emotion detection

## License

Copyright (c) 2025 EduLens Project
