"""
Component Manager for EduLens

Manages lifecycle of all EduLens components including initialization,
health monitoring, graceful shutdown, and resource management.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any

from .event_bus import Event, EventBus, EventType, create_event, get_event_bus

logger = logging.getLogger(__name__)


class ComponentState(Enum):
    """Lifecycle states for EduLens components."""

    UNINITIALIZED = auto()
    INITIALIZING = auto()
    READY = auto()
    RUNNING = auto()
    PAUSED = auto()
    ERROR = auto()
    SHUTTING_DOWN = auto()
    STOPPED = auto()


@dataclass
class ComponentHealth:
    """Health status of a component."""

    is_healthy: bool
    state: ComponentState
    last_check: datetime = field(default_factory=datetime.utcnow)
    error_message: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


class Component(ABC):
    """
    Base class for all EduLens components.

    Components must implement initialization, shutdown, and health check
    methods. They receive events through the event bus.
    """

    def __init__(self, name: str, event_bus: EventBus | None = None) -> None:
        self.name = name
        self.event_bus = event_bus or get_event_bus()
        self._state = ComponentState.UNINITIALIZED
        self._error: Exception | None = None
        self._started_at: datetime | None = None

    @property
    def state(self) -> ComponentState:
        """Get current component state."""
        return self._state

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the component.

        Called once during system startup. Should set up resources,
        load models, establish connections, etc.
        """
        pass

    @abstractmethod
    async def start(self) -> None:
        """
        Start the component's main operation.

        Called after initialization. Component should begin processing.
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """
        Stop the component gracefully.

        Called during system shutdown. Should release resources cleanly.
        """
        pass

    @abstractmethod
    async def health_check(self) -> ComponentHealth:
        """
        Check component health.

        Returns current health status including any errors or metrics.
        """
        pass

    async def pause(self) -> None:
        """Pause component operation (optional)."""
        self._state = ComponentState.PAUSED

    async def resume(self) -> None:
        """Resume component operation (optional)."""
        if self._state == ComponentState.PAUSED:
            self._state = ComponentState.RUNNING

    def _publish_event(self, event_type: EventType, **payload: Any) -> None:
        """Helper to publish events from this component."""
        event = create_event(event_type, source=self.name, **payload)
        asyncio.create_task(self.event_bus.publish(event))


class ComponentManager:
    """
    Manages all EduLens components.

    Handles component registration, lifecycle management, health monitoring,
    and coordinated startup/shutdown.
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self.event_bus = event_bus or get_event_bus()
        self._components: dict[str, Component] = {}
        self._initialization_order: list[str] = []
        self._is_running: bool = False
        self._health_check_interval: float = 30.0  # seconds

    def register(
        self,
        component: Component,
        dependencies: list[str] | None = None,
    ) -> None:
        """
        Register a component with the manager.

        Args:
            component: The component to register
            dependencies: Names of components that must be initialized first
        """
        if component.name in self._components:
            raise ValueError(f"Component '{component.name}' already registered")

        self._components[component.name] = component

        # Update initialization order based on dependencies
        if dependencies:
            # Ensure dependencies are initialized before this component
            for dep in dependencies:
                if dep not in self._initialization_order:
                    if dep in self._components:
                        self._initialization_order.append(dep)

        if component.name not in self._initialization_order:
            self._initialization_order.append(component.name)

        logger.info(f"Registered component: {component.name}")

    def unregister(self, name: str) -> None:
        """Unregister a component by name."""
        if name in self._components:
            del self._components[name]
            if name in self._initialization_order:
                self._initialization_order.remove(name)
            logger.info(f"Unregistered component: {name}")

    def get_component(self, name: str) -> Component | None:
        """Get a component by name."""
        return self._components.get(name)

    async def initialize_all(self) -> None:
        """Initialize all registered components in dependency order."""
        logger.info("Initializing all components...")

        for name in self._initialization_order:
            component = self._components.get(name)
            if component is None:
                logger.warning(f"Component '{name}' in init order but not registered")
                continue

            try:
                logger.info(f"Initializing component: {name}")
                component._state = ComponentState.INITIALIZING
                await component.initialize()
                component._state = ComponentState.READY
                logger.info(f"Component '{name}' initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize component '{name}': {e}")
                component._state = ComponentState.ERROR
                component._error = e
                raise RuntimeError(f"Component initialization failed: {name}") from e

        await self.event_bus.publish(
            create_event(EventType.SYSTEM_READY, source="component_manager")
        )

    async def start_all(self) -> None:
        """Start all initialized components."""
        logger.info("Starting all components...")
        self._is_running = True

        for name in self._initialization_order:
            component = self._components.get(name)
            if component is None or component.state != ComponentState.READY:
                continue

            try:
                logger.info(f"Starting component: {name}")
                await component.start()
                component._state = ComponentState.RUNNING
                component._started_at = datetime.utcnow()
            except Exception as e:
                logger.error(f"Failed to start component '{name}': {e}")
                component._state = ComponentState.ERROR
                component._error = e

        # Start health monitoring
        asyncio.create_task(self._health_monitor())

    async def stop_all(self) -> None:
        """Stop all components in reverse order."""
        logger.info("Stopping all components...")
        self._is_running = False

        await self.event_bus.publish(
            create_event(EventType.SYSTEM_SHUTDOWN, source="component_manager")
        )

        # Stop in reverse initialization order
        for name in reversed(self._initialization_order):
            component = self._components.get(name)
            if component is None:
                continue

            try:
                logger.info(f"Stopping component: {name}")
                component._state = ComponentState.SHUTTING_DOWN
                await component.stop()
                component._state = ComponentState.STOPPED
            except Exception as e:
                logger.error(f"Error stopping component '{name}': {e}")

        logger.info("All components stopped")

    async def get_all_health(self) -> dict[str, ComponentHealth]:
        """Get health status of all components."""
        health_status = {}
        for name, component in self._components.items():
            try:
                health_status[name] = await component.health_check()
            except Exception as e:
                health_status[name] = ComponentHealth(
                    is_healthy=False,
                    state=component.state,
                    error_message=str(e),
                )
        return health_status

    async def _health_monitor(self) -> None:
        """Background task to monitor component health."""
        while self._is_running:
            try:
                health = await self.get_all_health()

                # Check for unhealthy components
                for name, status in health.items():
                    if not status.is_healthy:
                        logger.warning(f"Component '{name}' unhealthy: {status.error_message}")
                        await self.event_bus.publish(
                            create_event(
                                EventType.SYSTEM_ERROR,
                                source="component_manager",
                                component=name,
                                error=status.error_message,
                            )
                        )

                await asyncio.sleep(self._health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(self._health_check_interval)


# Global component manager instance
_component_manager: ComponentManager | None = None


def get_component_manager() -> ComponentManager:
    """Get the global component manager instance."""
    global _component_manager
    if _component_manager is None:
        _component_manager = ComponentManager()
    return _component_manager
