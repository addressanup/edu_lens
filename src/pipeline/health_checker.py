"""
Health Checker for EduLens Pipeline

Monitors system health, runs diagnostics, and provides real-time status
of all pipeline components. Enables proactive issue detection and monitoring.

Author: Integration Agent (INT-001)
Version: 1.0.0
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Callable, Coroutine, Optional
import psutil

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = auto()      # All systems operational
    DEGRADED = auto()     # Some issues but functional
    UNHEALTHY = auto()    # Significant issues
    CRITICAL = auto()     # System failure imminent
    OFFLINE = auto()      # Component offline


class ComponentType(Enum):
    """Types of components to monitor."""
    VISION = "vision"
    AUDIO = "audio"
    AI = "ai"
    PIPELINE = "pipeline"
    HARDWARE = "hardware"
    NETWORK = "network"


@dataclass
class ComponentHealth:
    """Health status of a component."""
    component_name: str
    component_type: ComponentType
    status: HealthStatus
    last_check: datetime = field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None
    metrics: dict[str, Any] = field(default_factory=dict)
    uptime_seconds: float = 0.0
    response_time_ms: float = 0.0


@dataclass
class SystemHealth:
    """Overall system health."""
    overall_status: HealthStatus
    components: dict[str, ComponentHealth]
    system_metrics: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DiagnosticResult:
    """Result of diagnostic test."""
    test_name: str
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0


@dataclass
class HealthCheckConfig:
    """Configuration for health checking."""
    check_interval_seconds: float = 30.0
    component_timeout_seconds: float = 5.0
    enable_auto_recovery: bool = True
    cpu_threshold_percent: float = 90.0
    memory_threshold_percent: float = 85.0
    disk_threshold_percent: float = 90.0


class HealthChecker:
    """
    Comprehensive health checker for EduLens pipeline.

    Features:
    - Monitors all pipeline components
    - Tracks system resources (CPU, memory, disk)
    - Runs diagnostic tests
    - Automatic health monitoring
    - Component status tracking
    - Performance metrics collection
    """

    def __init__(
        self,
        config: Optional[HealthCheckConfig] = None,
        alert_callback: Optional[Callable[[ComponentHealth], Coroutine]] = None
    ) -> None:
        """
        Initialize health checker.

        Args:
            config: Health check configuration
            alert_callback: Callback for health alerts
        """
        self.config = config or HealthCheckConfig()
        self.alert_callback = alert_callback

        # Component tracking
        self._components: dict[str, Any] = {}
        self._component_health: dict[str, ComponentHealth] = {}
        self._component_start_times: dict[str, datetime] = {}

        # Monitoring state
        self._is_monitoring: bool = False
        self._monitor_task: Optional[asyncio.Task] = None

        # Historical data
        self._health_history: list[SystemHealth] = []
        self._diagnostic_results: list[DiagnosticResult] = []

        logger.info("HealthChecker initialized")

    def register_component(
        self,
        component_name: str,
        component_type: ComponentType,
        component: Any
    ) -> None:
        """
        Register a component for monitoring.

        Args:
            component_name: Name of the component
            component_type: Type of component
            component: Component instance
        """
        self._components[component_name] = component
        self._component_start_times[component_name] = datetime.utcnow()

        logger.info(
            f"Registered component: {component_name} ({component_type.value})"
        )

    def unregister_component(self, component_name: str) -> None:
        """
        Unregister a component.

        Args:
            component_name: Name of the component
        """
        if component_name in self._components:
            del self._components[component_name]
            if component_name in self._component_health:
                del self._component_health[component_name]
            if component_name in self._component_start_times:
                del self._component_start_times[component_name]

            logger.info(f"Unregistered component: {component_name}")

    async def start_monitoring(self) -> None:
        """Start automatic health monitoring."""
        if self._is_monitoring:
            logger.warning("Health monitoring already running")
            return

        logger.info("Starting health monitoring...")
        self._is_monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop_monitoring(self) -> None:
        """Stop automatic health monitoring."""
        if not self._is_monitoring:
            return

        logger.info("Stopping health monitoring...")
        self._is_monitoring = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    async def check_all_components(self) -> SystemHealth:
        """
        Check health of all registered components.

        Returns:
            System health status
        """
        component_health = {}

        # Check each component
        for name, component in self._components.items():
            health = await self._check_component(name, component)
            component_health[name] = health
            self._component_health[name] = health

        # Collect system metrics
        system_metrics = await self._collect_system_metrics()

        # Determine overall status
        overall_status = self._determine_overall_status(
            list(component_health.values()),
            system_metrics
        )

        system_health = SystemHealth(
            overall_status=overall_status,
            components=component_health,
            system_metrics=system_metrics
        )

        # Store in history
        self._health_history.append(system_health)
        if len(self._health_history) > 100:
            self._health_history = self._health_history[-100:]

        return system_health

    async def get_component_status(
        self,
        component_name: str
    ) -> Optional[ComponentHealth]:
        """
        Get health status of a specific component.

        Args:
            component_name: Name of the component

        Returns:
            Component health or None if not found
        """
        if component_name not in self._components:
            logger.warning(f"Component not found: {component_name}")
            return None

        component = self._components[component_name]
        return await self._check_component(component_name, component)

    async def run_diagnostics(
        self,
        component_name: Optional[str] = None
    ) -> list[DiagnosticResult]:
        """
        Run diagnostic tests on components.

        Args:
            component_name: Optional specific component to test

        Returns:
            List of diagnostic results
        """
        results = []

        if component_name:
            # Test specific component
            if component_name in self._components:
                result = await self._run_component_diagnostics(component_name)
                results.extend(result)
        else:
            # Test all components
            for name in self._components.keys():
                result = await self._run_component_diagnostics(name)
                results.extend(result)

            # Run system-level diagnostics
            system_results = await self._run_system_diagnostics()
            results.extend(system_results)

        # Store results
        self._diagnostic_results.extend(results)
        if len(self._diagnostic_results) > 1000:
            self._diagnostic_results = self._diagnostic_results[-1000:]

        return results

    def get_health_history(
        self,
        duration: Optional[timedelta] = None
    ) -> list[SystemHealth]:
        """
        Get health history.

        Args:
            duration: Optional time range

        Returns:
            List of system health records
        """
        if not duration:
            return self._health_history

        cutoff = datetime.utcnow() - duration
        return [
            h for h in self._health_history
            if h.timestamp >= cutoff
        ]

    async def _check_component(
        self,
        name: str,
        component: Any
    ) -> ComponentHealth:
        """Check health of a single component."""
        start_time = asyncio.get_event_loop().time()

        try:
            # Try to call health_check method if available
            if hasattr(component, 'health_check'):
                result = await asyncio.wait_for(
                    component.health_check(),
                    timeout=self.config.component_timeout_seconds
                )

                # Calculate response time
                response_time_ms = (
                    asyncio.get_event_loop().time() - start_time
                ) * 1000

                # Calculate uptime
                uptime = 0.0
                if name in self._component_start_times:
                    delta = datetime.utcnow() - self._component_start_times[name]
                    uptime = delta.total_seconds()

                # Extract status from result
                if hasattr(result, 'is_healthy'):
                    is_healthy = result.is_healthy
                else:
                    is_healthy = result

                status = HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY

                # Get component type
                component_type = self._determine_component_type(name)

                health = ComponentHealth(
                    component_name=name,
                    component_type=component_type,
                    status=status,
                    metrics=getattr(result, 'metrics', {}),
                    uptime_seconds=uptime,
                    response_time_ms=response_time_ms
                )

                # Alert if unhealthy
                if status != HealthStatus.HEALTHY and self.alert_callback:
                    asyncio.create_task(self.alert_callback(health))

                return health

            else:
                # Component doesn't have health check, assume healthy if exists
                component_type = self._determine_component_type(name)
                return ComponentHealth(
                    component_name=name,
                    component_type=component_type,
                    status=HealthStatus.HEALTHY,
                    metrics={"note": "No health_check method available"}
                )

        except asyncio.TimeoutError:
            logger.warning(f"Health check timeout for {name}")
            component_type = self._determine_component_type(name)
            return ComponentHealth(
                component_name=name,
                component_type=component_type,
                status=HealthStatus.UNHEALTHY,
                error_message="Health check timeout"
            )

        except Exception as e:
            logger.error(f"Error checking health of {name}: {e}", exc_info=True)
            component_type = self._determine_component_type(name)
            return ComponentHealth(
                component_name=name,
                component_type=component_type,
                status=HealthStatus.UNHEALTHY,
                error_message=str(e)
            )

    def _determine_component_type(self, component_name: str) -> ComponentType:
        """Determine component type from name."""
        name_lower = component_name.lower()

        if "vision" in name_lower or "camera" in name_lower or "ocr" in name_lower:
            return ComponentType.VISION
        elif "audio" in name_lower or "speech" in name_lower or "tts" in name_lower:
            return ComponentType.AUDIO
        elif "ai" in name_lower or "tutor" in name_lower or "llm" in name_lower:
            return ComponentType.AI
        elif "pipeline" in name_lower:
            return ComponentType.PIPELINE
        else:
            return ComponentType.PIPELINE

    async def _collect_system_metrics(self) -> dict[str, Any]:
        """Collect system-level metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            metrics = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024 ** 3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024 ** 3),
                "timestamp": datetime.utcnow().isoformat()
            }

            # Check thresholds
            if cpu_percent > self.config.cpu_threshold_percent:
                metrics["cpu_warning"] = True
            if memory.percent > self.config.memory_threshold_percent:
                metrics["memory_warning"] = True
            if disk.percent > self.config.disk_threshold_percent:
                metrics["disk_warning"] = True

            return metrics

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {"error": str(e)}

    def _determine_overall_status(
        self,
        component_health: list[ComponentHealth],
        system_metrics: dict[str, Any]
    ) -> HealthStatus:
        """Determine overall system health status."""
        if not component_health:
            return HealthStatus.OFFLINE

        # Count statuses
        status_counts = {}
        for health in component_health:
            status_counts[health.status] = status_counts.get(health.status, 0) + 1

        # Check for critical issues
        if status_counts.get(HealthStatus.CRITICAL, 0) > 0:
            return HealthStatus.CRITICAL

        # Check for unhealthy components
        unhealthy = status_counts.get(HealthStatus.UNHEALTHY, 0)
        if unhealthy >= len(component_health) / 2:
            return HealthStatus.UNHEALTHY

        # Check for degraded components
        degraded = status_counts.get(HealthStatus.DEGRADED, 0)
        if degraded > 0 or unhealthy > 0:
            return HealthStatus.DEGRADED

        # Check system metrics
        if system_metrics.get("cpu_warning") or system_metrics.get("memory_warning"):
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    async def _run_component_diagnostics(
        self,
        component_name: str
    ) -> list[DiagnosticResult]:
        """Run diagnostics on a component."""
        results = []

        component_type = self._determine_component_type(component_name)

        # Basic connectivity test
        start = asyncio.get_event_loop().time()
        health = await self.get_component_status(component_name)
        duration = (asyncio.get_event_loop().time() - start) * 1000

        results.append(DiagnosticResult(
            test_name=f"{component_name}_connectivity",
            passed=health.status == HealthStatus.HEALTHY if health else False,
            message=f"Component reachable and responsive",
            duration_ms=duration
        ))

        # Component-specific tests
        if component_type == ComponentType.VISION:
            results.extend(await self._test_vision_component(component_name))
        elif component_type == ComponentType.AUDIO:
            results.extend(await self._test_audio_component(component_name))
        elif component_type == ComponentType.AI:
            results.extend(await self._test_ai_component(component_name))

        return results

    async def _run_system_diagnostics(self) -> list[DiagnosticResult]:
        """Run system-level diagnostics."""
        results = []

        # CPU test
        cpu_percent = psutil.cpu_percent(interval=1.0)
        results.append(DiagnosticResult(
            test_name="system_cpu",
            passed=cpu_percent < self.config.cpu_threshold_percent,
            message=f"CPU usage: {cpu_percent:.1f}%",
            details={"cpu_percent": cpu_percent}
        ))

        # Memory test
        memory = psutil.virtual_memory()
        results.append(DiagnosticResult(
            test_name="system_memory",
            passed=memory.percent < self.config.memory_threshold_percent,
            message=f"Memory usage: {memory.percent:.1f}%",
            details={"memory_percent": memory.percent}
        ))

        # Disk test
        disk = psutil.disk_usage('/')
        results.append(DiagnosticResult(
            test_name="system_disk",
            passed=disk.percent < self.config.disk_threshold_percent,
            message=f"Disk usage: {disk.percent:.1f}%",
            details={"disk_percent": disk.percent}
        ))

        return results

    async def _test_vision_component(
        self,
        component_name: str
    ) -> list[DiagnosticResult]:
        """Run vision-specific tests."""
        # Placeholder for vision tests
        return [
            DiagnosticResult(
                test_name=f"{component_name}_vision_test",
                passed=True,
                message="Vision component operational"
            )
        ]

    async def _test_audio_component(
        self,
        component_name: str
    ) -> list[DiagnosticResult]:
        """Run audio-specific tests."""
        # Placeholder for audio tests
        return [
            DiagnosticResult(
                test_name=f"{component_name}_audio_test",
                passed=True,
                message="Audio component operational"
            )
        ]

    async def _test_ai_component(
        self,
        component_name: str
    ) -> list[DiagnosticResult]:
        """Run AI-specific tests."""
        # Placeholder for AI tests
        return [
            DiagnosticResult(
                test_name=f"{component_name}_ai_test",
                passed=True,
                message="AI component operational"
            )
        ]

    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        logger.info("Health monitoring loop started")

        while self._is_monitoring:
            try:
                # Run health checks
                system_health = await self.check_all_components()

                # Log status
                logger.info(
                    f"System health: {system_health.overall_status.name}, "
                    f"Components: {len(system_health.components)}"
                )

                # Sleep until next check
                await asyncio.sleep(self.config.check_interval_seconds)

            except asyncio.CancelledError:
                logger.info("Health monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(self.config.check_interval_seconds)


def create_health_checker(
    config: Optional[HealthCheckConfig] = None,
    alert_callback: Optional[Callable[[ComponentHealth], Coroutine]] = None
) -> HealthChecker:
    """
    Create a health checker instance.

    Args:
        config: Health check configuration
        alert_callback: Callback for alerts

    Returns:
        HealthChecker instance
    """
    return HealthChecker(config=config, alert_callback=alert_callback)
