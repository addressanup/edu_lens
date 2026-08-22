"""
Audio Pipeline Demo for EduLens

Demonstrates the unified audio pipeline with wake word detection,
ASR, and TTS integration.

Usage:
    python examples/audio_pipeline_demo.py
"""

import asyncio
import logging
from pathlib import Path

from src.audio.audio_pipeline import (
    AudioPipeline,
    PipelineConfig,
    PipelineEvent,
    PipelineState,
    create_pipeline,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class PipelineDemo:
    """Demo application for audio pipeline."""

    def __init__(self):
        """Initialize demo."""
        self.pipeline = None
        self.interaction_count = 0

    async def on_state_change(self, event: PipelineEvent):
        """
        Handle pipeline state changes.

        Args:
            event: Pipeline event
        """
        logger.info(f"State transition: {event.previous_state.value} -> {event.state.value}")

        if event.state == PipelineState.WAKE_DETECTED:
            logger.info("Wake word detected! Listening for your question...")

        elif event.state == PipelineState.LISTENING:
            logger.info("Listening... (speak now)")

        elif event.state == PipelineState.PROCESSING:
            logger.info("Processing your speech...")

        elif event.state == PipelineState.SPEAKING:
            logger.info("Speaking response...")
            self.interaction_count += 1

        elif event.state == PipelineState.IDLE:
            logger.info(f"Ready for next interaction (count: {self.interaction_count})")

        elif event.state == PipelineState.ERROR:
            logger.error("Pipeline encountered an error!")

    async def on_wake_detected(self, event: PipelineEvent):
        """
        Handle wake word detection specifically.

        Args:
            event: Pipeline event
        """
        if event.data and "detection" in event.data:
            detection = event.data["detection"]
            logger.info(
                f"Wake word confidence: {detection.confidence:.2%}, "
                f"latency: {detection.latency_ms:.1f}ms"
            )

    async def on_processing(self, event: PipelineEvent):
        """
        Handle processing state.

        Args:
            event: Pipeline event
        """
        if event.data and "segment" in event.data:
            segment = event.data["segment"]
            logger.info(
                f"Speech segment: duration={segment.duration:.2f}s, "
                f"level={segment.rms_level:.3f}"
            )

    async def run(self, config_path: Path = None):
        """
        Run the demo.

        Args:
            config_path: Optional path to config file
        """
        logger.info("Starting EduLens Audio Pipeline Demo")
        logger.info("=" * 60)

        # Load configuration
        if config_path and config_path.exists():
            config = PipelineConfig.from_yaml(config_path)
            logger.info(f"Loaded configuration from {config_path}")
        else:
            config = PipelineConfig()
            logger.info("Using default configuration")

        # Create and initialize pipeline
        logger.info("Initializing audio pipeline...")
        self.pipeline = AudioPipeline(config)
        await self.pipeline.initialize()

        # Register callbacks
        self.pipeline.on_event(self.on_state_change)
        self.pipeline.on_state_change(PipelineState.WAKE_DETECTED, self.on_wake_detected)
        self.pipeline.on_state_change(PipelineState.PROCESSING, self.on_processing)

        # Start pipeline
        logger.info("Starting pipeline...")
        await self.pipeline.start()

        logger.info("=" * 60)
        logger.info("Pipeline is running!")
        logger.info("Say 'Hey EduLens' to start interacting")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)

        try:
            # Run until interrupted
            while True:
                # Print status every 5 seconds
                await asyncio.sleep(5)

                state = self.pipeline.get_state()
                stats = self.pipeline.get_latency_stats()

                logger.info(
                    f"Status: state={state.value}, "
                    f"healthy={self.pipeline.is_healthy()}, "
                    f"interactions={self.interaction_count}"
                )

                if stats.get("total_sessions", 0) > 0:
                    logger.info(
                        f"Latency stats: "
                        f"avg={stats.get('avg_latency', 0):.1f}ms, "
                        f"p95={stats.get('p95_latency', 0):.1f}ms"
                    )

        except KeyboardInterrupt:
            logger.info("\nShutting down...")

        finally:
            # Stop pipeline
            await self.pipeline.stop()
            logger.info("Pipeline stopped. Goodbye!")


async def main():
    """Main entry point."""
    # Path to config file
    config_path = Path(__file__).parent.parent / "configs" / "audio" / "pipeline_config.yaml"

    # Create and run demo
    demo = PipelineDemo()
    await demo.run(config_path)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo terminated by user")
