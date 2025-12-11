"""
Wake Word Detection Demo for EduLens

Demonstrates basic usage of the wake word detection system.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from audio import (
    WakeWordDetector,
    AsyncWakeWordDetector,
    DetectionResult
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def demo_basic_detection():
    """Demonstrate basic wake word detection."""
    print("\n" + "=" * 60)
    print("EduLens Wake Word Detection - Basic Demo")
    print("=" * 60)
    print("\nWake word: 'Hey EduLens'")
    print("Speak the wake word to test detection...")
    print("Press Ctrl+C to stop\n")

    # Create detector
    config_path = Path(__file__).parent.parent / 'configs' / 'audio' / 'wake_word_config.yaml'

    detector = WakeWordDetector(
        model_path=None,  # Use heuristic detection for demo
        sensitivity=0.5,  # Balanced sensitivity
        config_path=str(config_path) if config_path.exists() else None
    )

    # Register callback
    def on_detection(result: DetectionResult):
        print(f"\n🎤 WAKE WORD DETECTED!")
        print(f"   Confidence: {result.confidence:.2%}")
        print(f"   Latency: {result.latency_ms:.1f}ms")
        print(f"   Time: {time.strftime('%H:%M:%S', time.localtime(result.timestamp))}")
        print("\nListening for next detection...\n")

    detector.on_wake_word(on_detection)

    try:
        # Start listening
        detector.start_listening()

        # Keep running
        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\nStopping detection...")
        detector.stop_listening()

        # Print statistics
        stats = detector.get_stats()
        print("\nDetection Statistics:")
        print(f"  Total detections: {stats.total_detections}")
        print(f"  Average confidence: {stats.avg_confidence:.2%}")
        print(f"  Average latency: {stats.avg_latency_ms:.1f}ms")

    print("\nDemo completed!")


async def demo_async_detection():
    """Demonstrate async wake word detection."""
    print("\n" + "=" * 60)
    print("EduLens Wake Word Detection - Async Demo")
    print("=" * 60)
    print("\nWake word: 'Hey EduLens'")
    print("Speak the wake word to test detection...")
    print("Press Ctrl+C to stop\n")

    # Create async detector
    config_path = Path(__file__).parent.parent / 'configs' / 'audio' / 'wake_word_config.yaml'

    detector = AsyncWakeWordDetector(
        model_path=None,
        sensitivity=0.5,
        config_path=str(config_path) if config_path.exists() else None
    )

    try:
        # Start listening
        await detector.start_listening()

        # Wait for detections
        detection_count = 0
        async for result in detector:
            detection_count += 1
            print(f"\n🎤 WAKE WORD DETECTED #{detection_count}")
            print(f"   Confidence: {result.confidence:.2%}")
            print(f"   Latency: {result.latency_ms:.1f}ms")
            print("\nListening for next detection...\n")

    except KeyboardInterrupt:
        print("\n\nStopping detection...")
        await detector.stop_listening()

    print("\nDemo completed!")


def demo_sensitivity_adjustment():
    """Demonstrate sensitivity adjustment."""
    print("\n" + "=" * 60)
    print("EduLens Wake Word Detection - Sensitivity Demo")
    print("=" * 60)

    detector = WakeWordDetector(sensitivity=0.5)

    print("\nTesting different sensitivity levels:\n")

    sensitivities = [0.2, 0.5, 0.8]
    for sens in sensitivities:
        detector.adjust_sensitivity(sens)
        print(f"Sensitivity: {sens:.1f}")
        print(f"  Threshold: {detector.threshold:.3f}")
        print(f"  Description: ", end="")

        if sens < 0.4:
            print("Conservative - fewer false positives")
        elif sens < 0.7:
            print("Balanced - recommended")
        else:
            print("Aggressive - fewer false negatives")
        print()

    print("Sensitivity can be adjusted in real-time based on user feedback!")


def demo_batch_detection():
    """Demonstrate batch detection mode."""
    print("\n" + "=" * 60)
    print("EduLens Wake Word Detection - Batch Mode Demo")
    print("=" * 60)

    detector = WakeWordDetector(sensitivity=0.5)

    print("\nProcessing synthetic audio samples...\n")

    # Generate test audio samples
    import numpy as np

    test_cases = [
        ("High energy (simulated wake word)", np.random.randn(24000).astype(np.float32) * 0.4),
        ("Low energy (silence)", np.random.randn(24000).astype(np.float32) * 0.01),
        ("Medium energy (background noise)", np.random.randn(24000).astype(np.float32) * 0.15),
    ]

    for name, audio in test_cases:
        result = detector.detect_batch(audio)

        print(f"{name}:")
        print(f"  Detected: {'Yes' if result.detected else 'No'}")
        print(f"  Confidence: {result.confidence:.2%}")
        print(f"  Latency: {result.latency_ms:.1f}ms")
        print()


def main():
    """Main demo function."""
    print("\nEduLens Wake Word Detection Demo")
    print("=" * 60)
    print("\nAvailable demos:")
    print("  1. Basic Detection (streaming)")
    print("  2. Async Detection")
    print("  3. Sensitivity Adjustment")
    print("  4. Batch Detection")
    print("  5. Run All Demos")

    try:
        choice = input("\nSelect demo (1-5): ").strip()

        if choice == "1":
            demo_basic_detection()
        elif choice == "2":
            asyncio.run(demo_async_detection())
        elif choice == "3":
            demo_sensitivity_adjustment()
        elif choice == "4":
            demo_batch_detection()
        elif choice == "5":
            demo_sensitivity_adjustment()
            demo_batch_detection()
            demo_basic_detection()
        else:
            print("Invalid choice. Please select 1-5.")

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        logger.error(f"Demo error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
