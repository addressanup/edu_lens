"""
Battery Manager for EduLens Smart Glasses

Monitors battery status and optimizes power consumption
to achieve 4+ hour battery life target.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Callable

logger = logging.getLogger(__name__)


class BatteryState(Enum):
    """Battery charge states."""

    FULL = auto()  # 80-100%
    NORMAL = auto()  # 20-80%
    LOW = auto()  # 10-20%
    CRITICAL = auto()  # 0-10%
    CHARGING = auto()


class ChargingState(Enum):
    """Charging states."""

    NOT_CHARGING = auto()
    CHARGING = auto()
    FULLY_CHARGED = auto()


@dataclass
class BatteryStatus:
    """Current battery status."""

    percent: int
    state: BatteryState
    charging_state: ChargingState
    voltage_mv: int
    current_ma: int
    temperature_celsius: float
    time_to_empty_minutes: int | None
    time_to_full_minutes: int | None
    health_percent: int
    cycle_count: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "percent": self.percent,
            "state": self.state.name,
            "charging_state": self.charging_state.name,
            "voltage_mv": self.voltage_mv,
            "current_ma": self.current_ma,
            "temperature_celsius": self.temperature_celsius,
            "time_to_empty_minutes": self.time_to_empty_minutes,
            "time_to_full_minutes": self.time_to_full_minutes,
            "health_percent": self.health_percent,
            "cycle_count": self.cycle_count,
        }


@dataclass
class PowerBudget:
    """Power budget allocation for components."""

    # Budget in milliwatts
    total_budget_mw: int = 2500  # ~2.5W total

    # Component allocations
    vision_mw: int = 800  # Camera + processing
    audio_mw: int = 400  # Mic + speaker + processing
    ai_mw: int = 600  # LLM inference
    display_mw: int = 100  # Status LED
    communication_mw: int = 300  # Bluetooth
    base_mw: int = 300  # System baseline

    def get_available(self) -> int:
        """Get remaining power budget."""
        used = (
            self.vision_mw
            + self.audio_mw
            + self.ai_mw
            + self.display_mw
            + self.communication_mw
            + self.base_mw
        )
        return max(0, self.total_budget_mw - used)


class BatteryManager:
    """
    Manages battery monitoring and power optimization.

    Goals:
    - 4+ hour battery life during active use
    - 8+ hour standby time
    - Graceful degradation as battery depletes
    """

    def __init__(
        self,
        low_threshold: int = 20,
        critical_threshold: int = 10,
    ) -> None:
        self.low_threshold = low_threshold
        self.critical_threshold = critical_threshold

        # State
        self._current_percent = 100
        self._charging = False
        self._power_budget = PowerBudget()

        # History for estimation
        self._drain_history: list[tuple[datetime, int]] = []
        self._charge_history: list[tuple[datetime, int]] = []

        # Callbacks
        self._on_low_battery: Callable[[int], None] | None = None
        self._on_critical_battery: Callable[[int], None] | None = None
        self._on_charging_change: Callable[[bool], None] | None = None

        # Monitor task
        self._monitor_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start battery monitoring."""
        logger.info("Starting battery manager")
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        """Stop battery monitoring."""
        logger.info("Stopping battery manager")
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                await self._update_battery_status()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Battery monitor error: {e}")
                await asyncio.sleep(60)

    async def _update_battery_status(self) -> None:
        """Update battery status from hardware."""
        # Read from hardware (platform-specific)
        percent = await self._read_battery_percent()
        charging = await self._read_charging_status()

        # Record history
        now = datetime.utcnow()
        if charging:
            self._charge_history.append((now, percent))
            # Keep last 20 samples
            self._charge_history = self._charge_history[-20:]
        else:
            self._drain_history.append((now, percent))
            self._drain_history = self._drain_history[-20:]

        # Check thresholds
        old_percent = self._current_percent
        self._current_percent = percent

        if not charging:
            if percent <= self.critical_threshold and old_percent > self.critical_threshold:
                logger.warning(f"Critical battery: {percent}%")
                if self._on_critical_battery:
                    self._on_critical_battery(percent)

            elif percent <= self.low_threshold and old_percent > self.low_threshold:
                logger.warning(f"Low battery: {percent}%")
                if self._on_low_battery:
                    self._on_low_battery(percent)

        # Check charging state change
        if charging != self._charging:
            self._charging = charging
            logger.info(f"Charging state changed: {charging}")
            if self._on_charging_change:
                self._on_charging_change(charging)

    async def _read_battery_percent(self) -> int:
        """Read battery percentage from hardware."""
        # Platform-specific implementation
        # This is a placeholder that simulates battery
        return self._current_percent

    async def _read_charging_status(self) -> bool:
        """Read charging status from hardware."""
        # Platform-specific implementation
        return self._charging

    def get_status(self) -> BatteryStatus:
        """Get current battery status."""
        # Determine state
        if self._charging:
            if self._current_percent >= 100:
                state = BatteryState.FULL
            else:
                state = BatteryState.CHARGING
        elif self._current_percent >= 80:
            state = BatteryState.FULL
        elif self._current_percent >= 20:
            state = BatteryState.NORMAL
        elif self._current_percent >= 10:
            state = BatteryState.LOW
        else:
            state = BatteryState.CRITICAL

        # Determine charging state
        if self._charging:
            if self._current_percent >= 100:
                charging_state = ChargingState.FULLY_CHARGED
            else:
                charging_state = ChargingState.CHARGING
        else:
            charging_state = ChargingState.NOT_CHARGING

        return BatteryStatus(
            percent=self._current_percent,
            state=state,
            charging_state=charging_state,
            voltage_mv=3700 + (self._current_percent * 5),  # Simulated
            current_ma=-300 if not self._charging else 500,  # Simulated
            temperature_celsius=35.0,  # Simulated
            time_to_empty_minutes=self._estimate_time_to_empty(),
            time_to_full_minutes=self._estimate_time_to_full(),
            health_percent=95,  # Simulated
            cycle_count=50,  # Simulated
        )

    def _estimate_time_to_empty(self) -> int | None:
        """Estimate minutes until battery empty."""
        if self._charging or len(self._drain_history) < 2:
            return None

        # Calculate drain rate from history
        first = self._drain_history[0]
        last = self._drain_history[-1]

        time_delta = (last[0] - first[0]).total_seconds() / 60  # minutes
        percent_delta = first[1] - last[1]

        if time_delta <= 0 or percent_delta <= 0:
            return None

        drain_rate = percent_delta / time_delta  # percent per minute
        minutes_remaining = self._current_percent / drain_rate

        return int(minutes_remaining)

    def _estimate_time_to_full(self) -> int | None:
        """Estimate minutes until battery full."""
        if not self._charging or len(self._charge_history) < 2:
            return None

        # Calculate charge rate from history
        first = self._charge_history[0]
        last = self._charge_history[-1]

        time_delta = (last[0] - first[0]).total_seconds() / 60  # minutes
        percent_delta = last[1] - first[1]

        if time_delta <= 0 or percent_delta <= 0:
            return None

        charge_rate = percent_delta / time_delta  # percent per minute
        percent_remaining = 100 - self._current_percent
        minutes_to_full = percent_remaining / charge_rate

        return int(minutes_to_full)

    def get_power_budget(self) -> PowerBudget:
        """Get current power budget."""
        return self._power_budget

    def adjust_power_budget(
        self,
        vision_mw: int | None = None,
        audio_mw: int | None = None,
        ai_mw: int | None = None,
    ) -> None:
        """Adjust component power budgets."""
        if vision_mw is not None:
            self._power_budget.vision_mw = vision_mw
        if audio_mw is not None:
            self._power_budget.audio_mw = audio_mw
        if ai_mw is not None:
            self._power_budget.ai_mw = ai_mw

        logger.debug(
            f"Power budget adjusted: vision={self._power_budget.vision_mw}mW, "
            f"audio={self._power_budget.audio_mw}mW, ai={self._power_budget.ai_mw}mW"
        )

    def get_recommended_power_mode(self) -> str:
        """Get recommended power mode based on battery state."""
        if self._current_percent >= 50:
            return "full"
        elif self._current_percent >= 20:
            return "balanced"
        elif self._current_percent >= 10:
            return "power_saver"
        else:
            return "ultra_low"

    def on_low_battery(self, callback: Callable[[int], None]) -> None:
        """Register low battery callback."""
        self._on_low_battery = callback

    def on_critical_battery(self, callback: Callable[[int], None]) -> None:
        """Register critical battery callback."""
        self._on_critical_battery = callback

    def on_charging_change(self, callback: Callable[[bool], None]) -> None:
        """Register charging state change callback."""
        self._on_charging_change = callback

    # Simulation methods for testing
    def simulate_drain(self, percent: int) -> None:
        """Simulate battery drain (for testing)."""
        self._current_percent = max(0, self._current_percent - percent)
        self._drain_history.append((datetime.utcnow(), self._current_percent))

    def simulate_charge(self, percent: int) -> None:
        """Simulate battery charge (for testing)."""
        self._current_percent = min(100, self._current_percent + percent)
        self._charge_history.append((datetime.utcnow(), self._current_percent))

    def simulate_set_charging(self, charging: bool) -> None:
        """Simulate charging state (for testing)."""
        self._charging = charging


def create_battery_manager(
    low_threshold: int = 20,
    critical_threshold: int = 10,
) -> BatteryManager:
    """Factory function to create battery manager."""
    return BatteryManager(
        low_threshold=low_threshold,
        critical_threshold=critical_threshold,
    )
