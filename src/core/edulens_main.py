"""
EduLens Main Application Entry Point

Orchestrates the initialization and runtime of the complete EduLens
AI-powered smart glasses system for elementary education.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path

from .component_manager import ComponentManager, get_component_manager
from .event_bus import EventBus, EventType, get_event_bus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class EduLensApplication:
    """
    Main EduLens application controller.

    Manages system lifecycle including initialization, runtime operation,
    and graceful shutdown of all subsystems.
    """

    def __init__(self) -> None:
        self.event_bus: EventBus = get_event_bus()
        self.component_manager: ComponentManager = get_component_manager()
        self._shutdown_event: asyncio.Event = asyncio.Event()
        self._is_running: bool = False

    async def initialize(self) -> None:
        """
        Initialize all EduLens subsystems.

        This method registers and initializes components in the correct
        dependency order:
        1. Privacy/Security (foundation layer)
        2. Vision Processing
        3. Audio Processing
        4. Educational AI
        5. Integration layer
        6. Pipeline orchestration
        """
        logger.info("=" * 60)
        logger.info("EduLens - AI-Powered Smart Glasses for Elementary Learning")
        logger.info("=" * 60)
        logger.info("Initializing EduLens system...")

        # Register core components
        # Note: Actual component implementations will be imported and registered
        # as they are developed by the respective agents

        # Example registration (will be replaced with actual imports):
        # from ..privacy.data_handler import PrivacyComponent
        # from ..vision.ocr_engine import VisionComponent
        # from ..audio.wake_word_engine import AudioComponent
        # from ..ai.tutor_inference import EducationalAIComponent
        # from ..integration.vision_to_ai_bridge import IntegrationComponent
        # from ..pipeline.homework_assistant import PipelineComponent

        # self.component_manager.register(PrivacyComponent(), dependencies=[])
        # self.component_manager.register(VisionComponent(), dependencies=["privacy"])
        # self.component_manager.register(AudioComponent(), dependencies=["privacy"])
        # self.component_manager.register(EducationalAIComponent(), dependencies=["privacy"])
        # self.component_manager.register(IntegrationComponent(), dependencies=["vision", "audio", "ai"])
        # self.component_manager.register(PipelineComponent(), dependencies=["integration"])

        logger.info("Component registration complete")

        # Initialize all components
        await self.component_manager.initialize_all()

        logger.info("EduLens system initialized successfully")

    async def start(self) -> None:
        """Start the EduLens system."""
        logger.info("Starting EduLens system...")
        self._is_running = True

        # Start event bus processing
        asyncio.create_task(self.event_bus.start_processing())

        # Start all components
        await self.component_manager.start_all()

        logger.info("EduLens system is now running")
        logger.info("Say 'Hey EduLens' to begin!")

    async def run(self) -> None:
        """Main run loop - waits for shutdown signal."""
        await self._shutdown_event.wait()

    async def shutdown(self) -> None:
        """Gracefully shutdown the EduLens system."""
        logger.info("Shutting down EduLens system...")
        self._is_running = False

        # Stop event bus
        self.event_bus.stop_processing()

        # Stop all components
        await self.component_manager.stop_all()

        # Signal shutdown complete
        self._shutdown_event.set()

        logger.info("EduLens system shutdown complete")

    def request_shutdown(self) -> None:
        """Request system shutdown (can be called from signal handler)."""
        if self._is_running:
            asyncio.create_task(self.shutdown())


async def main() -> int:
    """Main entry point for EduLens application."""
    app = EduLensApplication()

    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler() -> None:
        logger.info("Received shutdown signal")
        app.request_shutdown()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        # Initialize and start the system
        await app.initialize()
        await app.start()

        # Run until shutdown
        await app.run()

        return 0

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        await app.shutdown()
        return 0

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        await app.shutdown()
        return 1


def run() -> None:
    """Entry point for package execution."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    run()
