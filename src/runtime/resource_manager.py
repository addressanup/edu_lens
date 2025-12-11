"""
Resource Management for Edge Devices

This module provides comprehensive resource monitoring and management for edge
devices with limited computational resources. It tracks CPU, memory, battery,
and thermal state, and implements adaptive quality controls to maintain stable
operation within device constraints.

Target Requirements:
- Memory monitoring and limits enforcement
- CPU usage tracking and throttling
- Thermal management
- Battery-aware operation
- Adaptive quality based on available resources

Author: Vision Processing Agent (VIS-001)
"""

import logging
import time
import platform
import os
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
from threading import Thread, Lock
import warnings

try:
    import psutil
except ImportError:
    psutil = None


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResourceLevel(Enum):
    """System resource availability levels."""
    CRITICAL = "critical"  # <10% available
    LOW = "low"           # 10-30% available
    MODERATE = "moderate"  # 30-60% available
    GOOD = "good"         # 60-85% available
    EXCELLENT = "excellent"  # >85% available


class DeviceProfile(Enum):
    """Device capability profiles."""
    LOW_END = "low_end"      # <2GB RAM, ARM Cortex-A53
    MID_RANGE = "mid_range"  # 2-4GB RAM, ARM Cortex-A72
    HIGH_END = "high_end"    # >4GB RAM, ARM Cortex-A76+


class QualityLevel(Enum):
    """Processing quality levels."""
    MINIMAL = "minimal"      # Lowest quality, fastest
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"      # Highest quality, slowest


@dataclass
class ResourceSnapshot:
    """Snapshot of system resource usage."""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    memory_used_mb: float
    memory_total_mb: float
    cpu_temp_celsius: Optional[float] = None
    battery_percent: Optional[float] = None
    battery_plugged: Optional[bool] = None
    throttling_active: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_available_mb": self.memory_available_mb,
            "memory_used_mb": self.memory_used_mb,
            "memory_total_mb": self.memory_total_mb,
            "cpu_temp_celsius": self.cpu_temp_celsius,
            "battery_percent": self.battery_percent,
            "battery_plugged": self.battery_plugged,
            "throttling_active": self.throttling_active
        }


@dataclass
class ResourceLimits:
    """Resource usage limits."""
    max_memory_mb: float = 500.0
    max_cpu_percent: float = 80.0
    max_temp_celsius: float = 75.0
    min_battery_percent: float = 15.0
    throttle_memory_threshold: float = 0.85  # Throttle at 85% of max
    throttle_cpu_threshold: float = 0.90     # Throttle at 90% of max


@dataclass
class DeviceCapabilities:
    """Device hardware capabilities."""
    profile: DeviceProfile
    cpu_count: int
    memory_total_mb: float
    has_gpu: bool = False
    has_npu: bool = False
    architecture: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "profile": self.profile.value,
            "cpu_count": self.cpu_count,
            "memory_total_mb": self.memory_total_mb,
            "has_gpu": self.has_gpu,
            "has_npu": self.has_npu,
            "architecture": self.architecture,
            "metadata": self.metadata
        }


class ResourceManager:
    """
    Comprehensive resource monitoring and management for edge devices.

    This class provides real-time monitoring of system resources (CPU, memory,
    battery, thermal) and implements adaptive quality controls to ensure stable
    operation within device constraints.

    Key Features:
    - Real-time CPU and memory monitoring
    - Thermal management and throttling
    - Battery-aware operation
    - Adaptive quality levels based on resources
    - Device capability detection
    - Resource usage history and analytics
    - Automatic throttling when limits approached

    Attributes:
        limits: Resource usage limits
        device_capabilities: Detected device capabilities
        current_quality: Current processing quality level
    """

    def __init__(
        self,
        limits: Optional[ResourceLimits] = None,
        monitor_interval_sec: float = 1.0,
        enable_auto_throttle: bool = True
    ):
        """
        Initialize the resource manager.

        Args:
            limits: Resource usage limits
            monitor_interval_sec: Monitoring update interval
            enable_auto_throttle: Enable automatic throttling
        """
        self.limits = limits or ResourceLimits()
        self.monitor_interval_sec = monitor_interval_sec
        self.enable_auto_throttle = enable_auto_throttle

        # Validate dependencies
        self._validate_dependencies()

        # Device capabilities
        self.device_capabilities = self._detect_device_capabilities()

        # Resource state
        self.current_snapshot: Optional[ResourceSnapshot] = None
        self.resource_level = ResourceLevel.GOOD
        self.current_quality = QualityLevel.HIGH

        # History tracking
        self.history: List[ResourceSnapshot] = []
        self.max_history_size = 100

        # Throttling state
        self.throttling_active = False
        self.throttle_callbacks: List[Callable] = []

        # Thread safety
        self.lock = Lock()

        # Background monitoring
        self.monitoring_active = False
        self.monitor_thread: Optional[Thread] = None

        logger.info(
            f"ResourceManager initialized. Device: {self.device_capabilities.profile.value}, "
            f"Memory limit: {self.limits.max_memory_mb}MB"
        )

    def _validate_dependencies(self) -> None:
        """Validate that required dependencies are available."""
        if psutil is None:
            warnings.warn(
                "psutil not available. Resource monitoring will be limited. "
                "Install with: pip install psutil"
            )

    def _detect_device_capabilities(self) -> DeviceCapabilities:
        """
        Detect device hardware capabilities.

        Returns:
            DeviceCapabilities with detected hardware info
        """
        # Get CPU info
        cpu_count = os.cpu_count() or 1

        # Get memory info
        if psutil:
            memory_info = psutil.virtual_memory()
            memory_total_mb = memory_info.total / (1024 * 1024)
        else:
            memory_total_mb = 2048.0  # Default assumption

        # Detect architecture
        arch = platform.machine().lower()
        is_arm = 'arm' in arch or 'aarch' in arch

        # Classify device profile
        if memory_total_mb < 2048:
            profile = DeviceProfile.LOW_END
        elif memory_total_mb < 4096:
            profile = DeviceProfile.MID_RANGE
        else:
            profile = DeviceProfile.HIGH_END

        capabilities = DeviceCapabilities(
            profile=profile,
            cpu_count=cpu_count,
            memory_total_mb=memory_total_mb,
            architecture=arch,
            metadata={
                "platform": platform.system(),
                "platform_version": platform.version(),
                "is_arm": is_arm
            }
        )

        logger.info(f"Detected device: {capabilities.to_dict()}")
        return capabilities

    def monitor_memory(self) -> Dict[str, float]:
        """
        Monitor current memory usage.

        Returns:
            Dictionary with memory usage information (MB and percentages)
        """
        if psutil is None:
            return {
                "used_mb": 0.0,
                "available_mb": self.limits.max_memory_mb,
                "total_mb": self.device_capabilities.memory_total_mb,
                "percent": 0.0
            }

        try:
            memory = psutil.virtual_memory()
            return {
                "used_mb": memory.used / (1024 * 1024),
                "available_mb": memory.available / (1024 * 1024),
                "total_mb": memory.total / (1024 * 1024),
                "percent": memory.percent
            }
        except Exception as e:
            logger.error(f"Memory monitoring failed: {e}")
            return {
                "used_mb": 0.0,
                "available_mb": self.limits.max_memory_mb,
                "total_mb": self.device_capabilities.memory_total_mb,
                "percent": 0.0
            }

    def monitor_cpu(self) -> Dict[str, float]:
        """
        Monitor current CPU usage.

        Returns:
            Dictionary with CPU usage information (percentages)
        """
        if psutil is None:
            return {
                "percent": 0.0,
                "per_cpu": [0.0] * self.device_capabilities.cpu_count
            }

        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            per_cpu = psutil.cpu_percent(interval=0.1, percpu=True)
            return {
                "percent": cpu_percent,
                "per_cpu": per_cpu
            }
        except Exception as e:
            logger.error(f"CPU monitoring failed: {e}")
            return {
                "percent": 0.0,
                "per_cpu": [0.0] * self.device_capabilities.cpu_count
            }

    def monitor_thermal(self) -> Optional[float]:
        """
        Monitor device temperature.

        Returns:
            Temperature in Celsius, or None if not available
        """
        if psutil is None:
            return None

        try:
            temps = psutil.sensors_temperatures()
            if not temps:
                return None

            # Try to get CPU temperature
            for name, entries in temps.items():
                if 'cpu' in name.lower() or 'core' in name.lower():
                    if entries:
                        return entries[0].current

            # Fallback: return first available temperature
            for name, entries in temps.items():
                if entries:
                    return entries[0].current

            return None

        except Exception as e:
            logger.debug(f"Thermal monitoring not available: {e}")
            return None

    def monitor_battery(self) -> Optional[Dict[str, Any]]:
        """
        Monitor battery status.

        Returns:
            Dictionary with battery info, or None if not available
        """
        if psutil is None:
            return None

        try:
            battery = psutil.sensors_battery()
            if battery is None:
                return None

            return {
                "percent": battery.percent,
                "plugged": battery.power_plugged,
                "time_left_sec": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None
            }
        except Exception as e:
            logger.debug(f"Battery monitoring not available: {e}")
            return None

    def get_current_snapshot(self) -> ResourceSnapshot:
        """
        Get current resource usage snapshot.

        Returns:
            ResourceSnapshot with current system state
        """
        memory_info = self.monitor_memory()
        cpu_info = self.monitor_cpu()
        temp = self.monitor_thermal()
        battery = self.monitor_battery()

        snapshot = ResourceSnapshot(
            timestamp=time.time(),
            cpu_percent=cpu_info["percent"],
            memory_percent=memory_info["percent"],
            memory_available_mb=memory_info["available_mb"],
            memory_used_mb=memory_info["used_mb"],
            memory_total_mb=memory_info["total_mb"],
            cpu_temp_celsius=temp,
            battery_percent=battery["percent"] if battery else None,
            battery_plugged=battery["plugged"] if battery else None,
            throttling_active=self.throttling_active
        )

        with self.lock:
            self.current_snapshot = snapshot

            # Add to history
            self.history.append(snapshot)
            if len(self.history) > self.max_history_size:
                self.history.pop(0)

        return snapshot

    def throttle_if_needed(self) -> bool:
        """
        Check resource usage and throttle if needed.

        Returns:
            True if throttling was activated, False otherwise
        """
        if not self.enable_auto_throttle:
            return False

        snapshot = self.get_current_snapshot()

        # Check memory threshold
        memory_usage_ratio = snapshot.memory_used_mb / self.limits.max_memory_mb
        if memory_usage_ratio > self.limits.throttle_memory_threshold:
            if not self.throttling_active:
                logger.warning(
                    f"Memory threshold exceeded ({memory_usage_ratio*100:.1f}%). "
                    "Activating throttling."
                )
                self._activate_throttling()
            return True

        # Check CPU threshold
        cpu_usage_ratio = snapshot.cpu_percent / self.limits.max_cpu_percent
        if cpu_usage_ratio > self.limits.throttle_cpu_threshold:
            if not self.throttling_active:
                logger.warning(
                    f"CPU threshold exceeded ({cpu_usage_ratio*100:.1f}%). "
                    "Activating throttling."
                )
                self._activate_throttling()
            return True

        # Check thermal threshold
        if snapshot.cpu_temp_celsius:
            if snapshot.cpu_temp_celsius > self.limits.max_temp_celsius:
                if not self.throttling_active:
                    logger.warning(
                        f"Thermal threshold exceeded ({snapshot.cpu_temp_celsius:.1f}°C). "
                        "Activating throttling."
                    )
                    self._activate_throttling()
                return True

        # Check battery threshold (only if not plugged)
        if snapshot.battery_percent and not snapshot.battery_plugged:
            if snapshot.battery_percent < self.limits.min_battery_percent:
                if not self.throttling_active:
                    logger.warning(
                        f"Low battery ({snapshot.battery_percent:.1f}%). "
                        "Activating throttling."
                    )
                    self._activate_throttling()
                return True

        # If throttling was active but conditions improved, deactivate
        if self.throttling_active:
            if (memory_usage_ratio < self.limits.throttle_memory_threshold * 0.8 and
                cpu_usage_ratio < self.limits.throttle_cpu_threshold * 0.8):
                logger.info("Resource usage normalized. Deactivating throttling.")
                self._deactivate_throttling()

        return False

    def _activate_throttling(self) -> None:
        """Activate resource throttling."""
        with self.lock:
            self.throttling_active = True

            # Reduce quality level
            if self.current_quality != QualityLevel.MINIMAL:
                self._reduce_quality_level()

            # Notify callbacks
            for callback in self.throttle_callbacks:
                try:
                    callback(True)
                except Exception as e:
                    logger.error(f"Throttle callback failed: {e}")

    def _deactivate_throttling(self) -> None:
        """Deactivate resource throttling."""
        with self.lock:
            self.throttling_active = False

            # Notify callbacks
            for callback in self.throttle_callbacks:
                try:
                    callback(False)
                except Exception as e:
                    logger.error(f"Throttle callback failed: {e}")

    def _reduce_quality_level(self) -> None:
        """Reduce processing quality level."""
        quality_levels = [
            QualityLevel.MAXIMUM,
            QualityLevel.HIGH,
            QualityLevel.MEDIUM,
            QualityLevel.LOW,
            QualityLevel.MINIMAL
        ]

        current_idx = quality_levels.index(self.current_quality)
        if current_idx < len(quality_levels) - 1:
            self.current_quality = quality_levels[current_idx + 1]
            logger.info(f"Reduced quality level to {self.current_quality.value}")

    def get_resource_level(self) -> ResourceLevel:
        """
        Get current resource availability level.

        Returns:
            ResourceLevel indicating overall resource availability
        """
        snapshot = self.current_snapshot or self.get_current_snapshot()

        # Calculate composite resource score
        memory_available_ratio = snapshot.memory_available_mb / snapshot.memory_total_mb
        cpu_available_ratio = (100 - snapshot.cpu_percent) / 100

        # Weight memory more heavily than CPU for vision tasks
        composite_score = (memory_available_ratio * 0.6) + (cpu_available_ratio * 0.4)

        if composite_score < 0.10:
            level = ResourceLevel.CRITICAL
        elif composite_score < 0.30:
            level = ResourceLevel.LOW
        elif composite_score < 0.60:
            level = ResourceLevel.MODERATE
        elif composite_score < 0.85:
            level = ResourceLevel.GOOD
        else:
            level = ResourceLevel.EXCELLENT

        with self.lock:
            self.resource_level = level

        return level

    def get_device_profile(self) -> DeviceCapabilities:
        """
        Get device capabilities profile.

        Returns:
            DeviceCapabilities with hardware information
        """
        return self.device_capabilities

    def get_recommended_quality(self) -> QualityLevel:
        """
        Get recommended quality level based on current resources.

        Returns:
            Recommended QualityLevel
        """
        if self.throttling_active:
            return QualityLevel.LOW

        level = self.get_resource_level()

        quality_map = {
            ResourceLevel.CRITICAL: QualityLevel.MINIMAL,
            ResourceLevel.LOW: QualityLevel.LOW,
            ResourceLevel.MODERATE: QualityLevel.MEDIUM,
            ResourceLevel.GOOD: QualityLevel.HIGH,
            ResourceLevel.EXCELLENT: QualityLevel.MAXIMUM
        }

        # Also consider device profile
        if self.device_capabilities.profile == DeviceProfile.LOW_END:
            # Cap quality for low-end devices
            recommended = quality_map[level]
            if recommended in [QualityLevel.MAXIMUM, QualityLevel.HIGH]:
                recommended = QualityLevel.MEDIUM
            return recommended

        return quality_map[level]

    def register_throttle_callback(self, callback: Callable[[bool], None]) -> None:
        """
        Register callback for throttling state changes.

        Args:
            callback: Function to call when throttling state changes.
                     Receives boolean: True when activated, False when deactivated
        """
        with self.lock:
            self.throttle_callbacks.append(callback)

    def start_monitoring(self) -> None:
        """Start background resource monitoring."""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return

        self.monitoring_active = True
        self.monitor_thread = Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()

        logger.info("Background monitoring started")

    def stop_monitoring(self) -> None:
        """Stop background resource monitoring."""
        if not self.monitoring_active:
            return

        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)

        logger.info("Background monitoring stopped")

    def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self.monitoring_active:
            try:
                # Update snapshot
                self.get_current_snapshot()

                # Check throttling
                self.throttle_if_needed()

                # Sleep
                time.sleep(self.monitor_interval_sec)

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get resource usage statistics.

        Returns:
            Dictionary with statistical summary of resource usage
        """
        if not self.history:
            return {}

        import numpy as np

        cpu_values = [s.cpu_percent for s in self.history]
        memory_values = [s.memory_percent for s in self.history]

        stats = {
            "cpu": {
                "current": cpu_values[-1],
                "avg": float(np.mean(cpu_values)),
                "max": float(np.max(cpu_values)),
                "min": float(np.min(cpu_values)),
                "std": float(np.std(cpu_values))
            },
            "memory": {
                "current": memory_values[-1],
                "avg": float(np.mean(memory_values)),
                "max": float(np.max(memory_values)),
                "min": float(np.min(memory_values)),
                "std": float(np.std(memory_values))
            },
            "throttling": {
                "currently_active": self.throttling_active,
                "activations": sum(1 for s in self.history if s.throttling_active)
            },
            "resource_level": self.resource_level.value,
            "current_quality": self.current_quality.value,
            "samples": len(self.history)
        }

        return stats

    def reset_statistics(self) -> None:
        """Reset resource usage history."""
        with self.lock:
            self.history.clear()
        logger.info("Resource statistics reset")

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.stop_monitoring()
        except:
            pass
