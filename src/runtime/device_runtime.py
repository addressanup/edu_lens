"""
Device Runtime for EduLens Smart Glasses

Main runtime environment that coordinates all on-device components
and manages the device lifecycle.
"""

from __future__ import annotations

import asyncio
import logging
import signal
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable

logger = logging.getLogger(__name__)


class DeviceState(Enum):
    """Device operational states."""

    OFF = auto()
    BOOTING = auto()
    READY = auto()
    ACTIVE = auto()          # Actively tutoring
    IDLE = auto()            # Waiting for wake word
    LOW_POWER = auto()       # Battery saving mode
    UPDATING = auto()        # Firmware/model update
    ERROR = auto()
    SHUTTING_DOWN = auto()


class PowerMode(Enum):
    """Power consumption modes."""

    FULL = auto()            # All features active
    BALANCED = auto()        # Normal operation
    POWER_SAVER = auto()     # Reduced features
    ULTRA_LOW = auto()       # Minimum for wake word only


@dataclass
class DeviceStatus:
    """Current device status."""

    state: DeviceState
    power_mode: PowerMode
    battery_percent: int
    is_charging: bool
    uptime_seconds: float
    temperature_celsius: float
    memory_used_mb: float
    cpu_percent: float
    active_session: bool = False
    last_activity: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "state": self.state.name,
            "power_mode": self.power_mode.name,
            "battery_percent": self.battery_percent,
            "is_charging": self.is_charging,
            "uptime_seconds": self.uptime_seconds,
            "temperature_celsius": self.temperature_celsius,
            "memory_used_mb": self.memory_used_mb,
            "cpu_percent": self.cpu_percent,
            "active_session": self.active_session,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
        }


@dataclass
class DeviceConfig:
    """Device configuration."""

    # Battery thresholds
    low_battery_threshold: int = 20
    critical_battery_threshold: int = 5

    # Temperature limits
    max_temperature_celsius: float = 45.0
    throttle_temperature_celsius: float = 40.0

    # Idle timeouts
    idle_timeout_seconds: int = 300  # 5 minutes
    deep_sleep_timeout_seconds: int = 900  # 15 minutes

    # Wake word
    wake_word: str = "Hey EduLens"
    wake_word_sensitivity: float = 0.7


class DeviceRuntime:
    """
    Main runtime environment for EduLens smart glasses.

    Coordinates all device components:
    - Vision pipeline (camera, OCR, handwriting)
    - Audio pipeline (wake word, ASR, TTS)
    - AI engine (tutoring, reasoning)
    - Privacy controls (data minimization, deletion)
    - Communication (Bluetooth, sync)
    """

    def __init__(
        self,
        config: DeviceConfig | None = None,
    ) -> None:
        self.config = config or DeviceConfig()

        # State
        self._state = DeviceState.OFF
        self._power_mode = PowerMode.BALANCED
        self._start_time: datetime | None = None
        self._last_activity: datetime | None = None

        # Components (injected during initialization)
        self._vision_pipeline: Any | None = None
        self._audio_pipeline: Any | None = None
        self._ai_engine: Any | None = None
        self._privacy_manager: Any | None = None
        self._communication: Any | None = None

        # Callbacks
        self._on_state_change: Callable[[DeviceState], None] | None = None
        self._on_low_battery: Callable[[int], None] | None = None

        # Background tasks
        self._monitor_task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()

    async def initialize(self) -> None:
        """
        Initialize the device runtime.

        Loads models, starts components, and prepares for operation.
        """
        logger.info("Initializing EduLens device runtime...")
        self._set_state(DeviceState.BOOTING)
        self._start_time = datetime.utcnow()

        try:
            # Initialize components in order
            await self._initialize_privacy()
            await self._initialize_vision()
            await self._initialize_audio()
            await self._initialize_ai()
            await self._initialize_communication()

            # Start background monitoring
            self._monitor_task = asyncio.create_task(self._monitor_loop())

            self._set_state(DeviceState.READY)
            logger.info("Device runtime initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize device: {e}")
            self._set_state(DeviceState.ERROR)
            raise

    async def _initialize_privacy(self) -> None:
        """Initialize privacy and data protection components."""
        logger.debug("Initializing privacy manager...")
        # Privacy manager would be injected or created here
        # self._privacy_manager = PrivacyManager()
        # await self._privacy_manager.initialize()

    async def _initialize_vision(self) -> None:
        """Initialize vision processing pipeline."""
        logger.debug("Initializing vision pipeline...")
        # Vision pipeline would be injected or created here
        # self._vision_pipeline = VisionPipeline()
        # await self._vision_pipeline.initialize()

    async def _initialize_audio(self) -> None:
        """Initialize audio processing pipeline."""
        logger.debug("Initializing audio pipeline...")
        # Audio pipeline would be injected or created here
        # self._audio_pipeline = AudioPipeline()
        # await self._audio_pipeline.initialize()

    async def _initialize_ai(self) -> None:
        """Initialize AI tutoring engine."""
        logger.debug("Initializing AI engine...")
        # AI engine would be injected or created here
        # self._ai_engine = TutorEngine()
        # await self._ai_engine.initialize()

    async def _initialize_communication(self) -> None:
        """Initialize communication (Bluetooth, sync)."""
        logger.debug("Initializing communication...")
        # Communication would be injected or created here

    async def start(self) -> None:
        """
        Start the device runtime.

        Begins listening for wake word and processing.
        """
        if self._state != DeviceState.READY:
            raise RuntimeError(f"Cannot start from state {self._state.name}")

        logger.info("Starting EduLens device...")
        self._set_state(DeviceState.IDLE)

        # Start wake word detection
        if self._audio_pipeline:
            await self._audio_pipeline.start_wake_word_detection()

        logger.info("Device started - listening for wake word")

    async def run(self) -> None:
        """
        Main run loop.

        Runs until shutdown is requested.
        """
        logger.info("Device runtime running...")

        try:
            await self._shutdown_event.wait()
        except asyncio.CancelledError:
            logger.info("Runtime cancelled")
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the device.

        Ensures all data is properly handled before shutdown.
        """
        logger.info("Shutting down device runtime...")
        self._set_state(DeviceState.SHUTTING_DOWN)

        # Cancel monitor task
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        # Shutdown components in reverse order
        if self._communication:
            await self._shutdown_component(self._communication, "communication")

        if self._ai_engine:
            await self._shutdown_component(self._ai_engine, "AI engine")

        if self._audio_pipeline:
            await self._shutdown_component(self._audio_pipeline, "audio pipeline")

        if self._vision_pipeline:
            await self._shutdown_component(self._vision_pipeline, "vision pipeline")

        if self._privacy_manager:
            # Ensure all data is purged before shutdown
            await self._shutdown_component(self._privacy_manager, "privacy manager")

        self._set_state(DeviceState.OFF)
        logger.info("Device shutdown complete")

    async def _shutdown_component(self, component: Any, name: str) -> None:
        """Safely shutdown a component."""
        try:
            if hasattr(component, "shutdown"):
                await component.shutdown()
            elif hasattr(component, "stop"):
                await component.stop()
            logger.debug(f"Shutdown {name}")
        except Exception as e:
            logger.error(f"Error shutting down {name}: {e}")

    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        self._shutdown_event.set()

    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while not self._shutdown_event.is_set():
            try:
                await self._check_battery()
                await self._check_temperature()
                await self._check_idle_timeout()
                await asyncio.sleep(10)  # Check every 10 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")

    async def _check_battery(self) -> None:
        """Check battery level and adjust power mode."""
        battery = await self._get_battery_percent()

        if battery <= self.config.critical_battery_threshold:
            logger.warning(f"Critical battery: {battery}%")
            await self._enter_low_power_mode()
            if self._on_low_battery:
                self._on_low_battery(battery)

        elif battery <= self.config.low_battery_threshold:
            if self._power_mode != PowerMode.POWER_SAVER:
                logger.info(f"Low battery ({battery}%), entering power saver mode")
                self._power_mode = PowerMode.POWER_SAVER
                await self._apply_power_mode()

    async def _check_temperature(self) -> None:
        """Check device temperature and throttle if needed."""
        temp = await self._get_temperature()

        if temp >= self.config.max_temperature_celsius:
            logger.warning(f"High temperature: {temp}°C - throttling")
            await self._throttle_performance()

        elif temp >= self.config.throttle_temperature_celsius:
            if self._power_mode == PowerMode.FULL:
                logger.info(f"Temperature ({temp}°C), reducing to balanced mode")
                self._power_mode = PowerMode.BALANCED
                await self._apply_power_mode()

    async def _check_idle_timeout(self) -> None:
        """Check for idle timeout and enter low power if needed."""
        if self._state != DeviceState.IDLE:
            return

        if self._last_activity is None:
            return

        idle_seconds = (datetime.utcnow() - self._last_activity).total_seconds()

        if idle_seconds >= self.config.deep_sleep_timeout_seconds:
            logger.info("Deep sleep timeout - entering ultra low power")
            await self._enter_low_power_mode()

        elif idle_seconds >= self.config.idle_timeout_seconds:
            if self._power_mode != PowerMode.POWER_SAVER:
                logger.info("Idle timeout - entering power saver")
                self._power_mode = PowerMode.POWER_SAVER
                await self._apply_power_mode()

    async def _enter_low_power_mode(self) -> None:
        """Enter ultra low power mode."""
        self._power_mode = PowerMode.ULTRA_LOW
        self._set_state(DeviceState.LOW_POWER)
        await self._apply_power_mode()

    async def _apply_power_mode(self) -> None:
        """Apply current power mode settings to components."""
        logger.debug(f"Applying power mode: {self._power_mode.name}")

        if self._power_mode == PowerMode.ULTRA_LOW:
            # Disable vision, reduce audio to wake word only
            if self._vision_pipeline and hasattr(self._vision_pipeline, "disable"):
                await self._vision_pipeline.disable()
        elif self._power_mode == PowerMode.POWER_SAVER:
            # Reduce frame rate, smaller models
            pass
        elif self._power_mode == PowerMode.BALANCED:
            # Normal operation
            if self._vision_pipeline and hasattr(self._vision_pipeline, "enable"):
                await self._vision_pipeline.enable()

    async def _throttle_performance(self) -> None:
        """Throttle performance due to temperature."""
        self._power_mode = PowerMode.POWER_SAVER
        await self._apply_power_mode()

    async def _get_battery_percent(self) -> int:
        """Get current battery percentage."""
        # Platform-specific implementation
        # This is a placeholder
        return 100

    async def _get_temperature(self) -> float:
        """Get device temperature in Celsius."""
        # Platform-specific implementation
        # This is a placeholder
        return 35.0

    def _set_state(self, new_state: DeviceState) -> None:
        """Update device state."""
        old_state = self._state
        self._state = new_state

        logger.info(f"Device state: {old_state.name} -> {new_state.name}")

        if self._on_state_change:
            self._on_state_change(new_state)

    def record_activity(self) -> None:
        """Record user activity (resets idle timer)."""
        self._last_activity = datetime.utcnow()

        # Wake up from power saver if needed
        if self._power_mode in (PowerMode.POWER_SAVER, PowerMode.ULTRA_LOW):
            self._power_mode = PowerMode.BALANCED
            asyncio.create_task(self._apply_power_mode())

        if self._state == DeviceState.LOW_POWER:
            self._set_state(DeviceState.IDLE)

    def get_status(self) -> DeviceStatus:
        """Get current device status."""
        uptime = 0.0
        if self._start_time:
            uptime = (datetime.utcnow() - self._start_time).total_seconds()

        return DeviceStatus(
            state=self._state,
            power_mode=self._power_mode,
            battery_percent=100,  # Placeholder
            is_charging=False,    # Placeholder
            uptime_seconds=uptime,
            temperature_celsius=35.0,  # Placeholder
            memory_used_mb=256.0,      # Placeholder
            cpu_percent=25.0,          # Placeholder
            active_session=self._state == DeviceState.ACTIVE,
            last_activity=self._last_activity,
        )

    def on_state_change(self, callback: Callable[[DeviceState], None]) -> None:
        """Register state change callback."""
        self._on_state_change = callback

    def on_low_battery(self, callback: Callable[[int], None]) -> None:
        """Register low battery callback."""
        self._on_low_battery = callback

    # Component injection methods
    def set_vision_pipeline(self, pipeline: Any) -> None:
        """Inject vision pipeline component."""
        self._vision_pipeline = pipeline

    def set_audio_pipeline(self, pipeline: Any) -> None:
        """Inject audio pipeline component."""
        self._audio_pipeline = pipeline

    def set_ai_engine(self, engine: Any) -> None:
        """Inject AI engine component."""
        self._ai_engine = engine

    def set_privacy_manager(self, manager: Any) -> None:
        """Inject privacy manager component."""
        self._privacy_manager = manager

    def set_communication(self, comm: Any) -> None:
        """Inject communication component."""
        self._communication = comm


def create_device_runtime(config: DeviceConfig | None = None) -> DeviceRuntime:
    """Factory function to create device runtime."""
    return DeviceRuntime(config=config)


async def main() -> None:
    """Main entry point for device runtime."""
    # Setup signal handlers
    runtime = create_device_runtime()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, runtime.request_shutdown)

    await runtime.initialize()
    await runtime.start()
    await runtime.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
