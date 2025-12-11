"""
Health Checks for Claude Agents Orchestration System.

This module provides health check utilities for monitoring system
components including databases, Redis, MCP servers, and external services.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import httpx


class HealthStatus(str, Enum):
    """Health status of a component."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status of a single component."""

    name: str
    status: HealthStatus
    latency_ms: float = 0.0
    message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "message": self.message,
            "details": self.details,
            "last_check": self.last_check.isoformat(),
        }


@dataclass
class SystemHealth:
    """Overall system health."""

    status: HealthStatus
    components: List[ComponentHealth]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def healthy_count(self) -> int:
        return sum(1 for c in self.components if c.status == HealthStatus.HEALTHY)

    @property
    def unhealthy_count(self) -> int:
        return sum(1 for c in self.components if c.status == HealthStatus.UNHEALTHY)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "healthy_count": self.healthy_count,
            "unhealthy_count": self.unhealthy_count,
            "total_components": len(self.components),
            "components": [c.to_dict() for c in self.components],
            "timestamp": self.timestamp.isoformat(),
        }


class HealthChecker:
    """
    Health check coordinator for system components.

    Provides configurable health checks for various system components
    with timeout handling and aggregated status reporting.

    Example:
        checker = HealthChecker()

        # Add checks
        checker.add_check("database", db_health_check)
        checker.add_check("redis", redis_health_check)
        checker.add_check("mcp_server", mcp_health_check)

        # Run all checks
        system_health = await checker.check_all()

        # Run specific check
        db_health = await checker.check("database")
    """

    def __init__(
        self,
        default_timeout: float = 5.0,
        parallel: bool = True,
    ):
        """
        Initialize the health checker.

        Args:
            default_timeout: Default timeout for health checks
            parallel: Whether to run checks in parallel
        """
        self._default_timeout = default_timeout
        self._parallel = parallel
        self._checks: Dict[str, Callable] = {}
        self._timeouts: Dict[str, float] = {}
        self._last_results: Dict[str, ComponentHealth] = {}

    def add_check(
        self,
        name: str,
        check_func: Callable[[], ComponentHealth],
        timeout: Optional[float] = None,
    ) -> None:
        """
        Add a health check.

        Args:
            name: Component name
            check_func: Async function that returns ComponentHealth
            timeout: Check timeout (uses default if not specified)
        """
        self._checks[name] = check_func
        self._timeouts[name] = timeout or self._default_timeout

    def remove_check(self, name: str) -> None:
        """Remove a health check."""
        if name in self._checks:
            del self._checks[name]
            del self._timeouts[name]

    async def check(self, name: str) -> ComponentHealth:
        """
        Run a specific health check.

        Args:
            name: Component name

        Returns:
            ComponentHealth result
        """
        if name not in self._checks:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"No check registered for: {name}",
            )

        check_func = self._checks[name]
        timeout = self._timeouts[name]

        import time
        start = time.time()

        try:
            if asyncio.iscoroutinefunction(check_func):
                result = await asyncio.wait_for(check_func(), timeout=timeout)
            else:
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, check_func),
                    timeout=timeout,
                )

            result.latency_ms = (time.time() - start) * 1000
            self._last_results[name] = result
            return result

        except asyncio.TimeoutError:
            result = ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.time() - start) * 1000,
                message=f"Health check timed out after {timeout}s",
            )
            self._last_results[name] = result
            return result

        except Exception as e:
            result = ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.time() - start) * 1000,
                message=f"Health check failed: {str(e)}",
            )
            self._last_results[name] = result
            return result

    async def check_all(self) -> SystemHealth:
        """
        Run all registered health checks.

        Returns:
            SystemHealth with aggregated status
        """
        if not self._checks:
            return SystemHealth(
                status=HealthStatus.UNKNOWN,
                components=[],
            )

        if self._parallel:
            # Run all checks in parallel
            tasks = [self.check(name) for name in self._checks]
            components = await asyncio.gather(*tasks)
        else:
            # Run checks sequentially
            components = []
            for name in self._checks:
                result = await self.check(name)
                components.append(result)

        # Determine overall status
        if all(c.status == HealthStatus.HEALTHY for c in components):
            overall_status = HealthStatus.HEALTHY
        elif any(c.status == HealthStatus.UNHEALTHY for c in components):
            overall_status = HealthStatus.UNHEALTHY
        elif any(c.status == HealthStatus.DEGRADED for c in components):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.UNKNOWN

        return SystemHealth(
            status=overall_status,
            components=list(components),
        )

    def get_last_result(self, name: str) -> Optional[ComponentHealth]:
        """Get the last result for a component."""
        return self._last_results.get(name)

    def get_all_last_results(self) -> Dict[str, ComponentHealth]:
        """Get all last results."""
        return self._last_results.copy()


# Pre-built health check functions

async def check_database(database_url: str) -> ComponentHealth:
    """
    Check database connectivity.

    Args:
        database_url: Database connection URL

    Returns:
        ComponentHealth result
    """
    from sqlalchemy import create_engine, text

    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        return ComponentHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            message="Database connection successful",
            details={"url": database_url[:20] + "..."},
        )

    except Exception as e:
        return ComponentHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=f"Database connection failed: {str(e)}",
        )


async def check_redis(redis_url: str) -> ComponentHealth:
    """
    Check Redis connectivity.

    Args:
        redis_url: Redis connection URL

    Returns:
        ComponentHealth result
    """
    import redis.asyncio as redis_client

    try:
        client = redis_client.from_url(redis_url)
        await client.ping()
        await client.close()

        return ComponentHealth(
            name="redis",
            status=HealthStatus.HEALTHY,
            message="Redis connection successful",
        )

    except Exception as e:
        return ComponentHealth(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            message=f"Redis connection failed: {str(e)}",
        )


async def check_http_endpoint(
    url: str,
    name: str = "http_endpoint",
    expected_status: int = 200,
) -> ComponentHealth:
    """
    Check HTTP endpoint health.

    Args:
        url: Endpoint URL
        name: Component name
        expected_status: Expected HTTP status code

    Returns:
        ComponentHealth result
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)

            if response.status_code == expected_status:
                return ComponentHealth(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    message=f"Endpoint returned {response.status_code}",
                    details={"url": url},
                )
            else:
                return ComponentHealth(
                    name=name,
                    status=HealthStatus.DEGRADED,
                    message=f"Unexpected status: {response.status_code}",
                    details={"url": url, "status": response.status_code},
                )

    except Exception as e:
        return ComponentHealth(
            name=name,
            status=HealthStatus.UNHEALTHY,
            message=f"Request failed: {str(e)}",
            details={"url": url},
        )


async def check_disk_space(
    path: str = "/",
    warning_threshold: float = 0.8,
    critical_threshold: float = 0.9,
) -> ComponentHealth:
    """
    Check disk space availability.

    Args:
        path: Path to check
        warning_threshold: Usage ratio for warning (0-1)
        critical_threshold: Usage ratio for critical (0-1)

    Returns:
        ComponentHealth result
    """
    import shutil

    try:
        usage = shutil.disk_usage(path)
        used_ratio = usage.used / usage.total

        if used_ratio >= critical_threshold:
            status = HealthStatus.UNHEALTHY
            message = f"Disk usage critical: {used_ratio:.0%}"
        elif used_ratio >= warning_threshold:
            status = HealthStatus.DEGRADED
            message = f"Disk usage high: {used_ratio:.0%}"
        else:
            status = HealthStatus.HEALTHY
            message = f"Disk usage normal: {used_ratio:.0%}"

        return ComponentHealth(
            name="disk_space",
            status=status,
            message=message,
            details={
                "path": path,
                "total_gb": usage.total / (1024 ** 3),
                "used_gb": usage.used / (1024 ** 3),
                "free_gb": usage.free / (1024 ** 3),
                "used_percent": used_ratio * 100,
            },
        )

    except Exception as e:
        return ComponentHealth(
            name="disk_space",
            status=HealthStatus.UNKNOWN,
            message=f"Failed to check disk space: {str(e)}",
        )
