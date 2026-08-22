"""
EduLens Dependency Injection Container

This module implements a dependency injection container for managing component
lifecycle, registration, and dependency resolution in the EduLens system.

Features:
- Constructor injection
- Singleton and transient lifetimes
- Lazy initialization
- Circular dependency detection
- Thread-safe operations
- Lifecycle management (initialize, start, stop, cleanup)

Author: Integration Agent (INT-001)
Version: 1.0.0
Date: 2025-12-10
"""

import asyncio
import inspect
import logging
from contextlib import asynccontextmanager
from enum import Enum
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Generic,
    Optional,
    Type,
    TypeVar,
    cast,
    get_type_hints,
)

from .interfaces import ComponentType, EduLensError, ILifecycle

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class DIError(EduLensError):
    """Dependency injection related errors"""

    pass


class ComponentNotFoundError(DIError):
    """Component not registered in container"""

    pass


class CircularDependencyError(DIError):
    """Circular dependency detected"""

    pass


class LifecycleError(DIError):
    """Component lifecycle error"""

    pass


# ============================================================================
# Component Lifetime
# ============================================================================


class ComponentLifetime(Enum):
    """Component lifetime strategies"""

    SINGLETON = "singleton"  # Single instance shared
    TRANSIENT = "transient"  # New instance every time
    SCOPED = "scoped"  # One instance per scope


# ============================================================================
# Component Registration
# ============================================================================

T = TypeVar("T")


class ComponentRegistration(Generic[T]):
    """Registration information for a component"""

    def __init__(
        self,
        interface: Type[T],
        implementation: Type[T],
        lifetime: ComponentLifetime,
        factory: Optional[Callable[..., T]] = None,
        instance: Optional[T] = None,
    ) -> None:
        """
        Initialize component registration

        Args:
            interface: Interface type (abstract base class)
            implementation: Concrete implementation class
            lifetime: Component lifetime strategy
            factory: Optional factory function for creating instances
            instance: Optional pre-created instance (for singletons)
        """
        self.interface = interface
        self.implementation = implementation
        self.lifetime = lifetime
        self.factory = factory
        self.instance = instance
        self.dependencies: list[Type[Any]] = []
        self.is_initializing = False  # For circular dependency detection

    def __repr__(self) -> str:
        return (
            f"ComponentRegistration("
            f"interface={self.interface.__name__}, "
            f"implementation={self.implementation.__name__}, "
            f"lifetime={self.lifetime.value})"
        )


# ============================================================================
# Service Container
# ============================================================================


class ServiceContainer:
    """
    Dependency injection container for managing component lifecycle
    and dependency resolution.

    Example usage:
        container = ServiceContainer()

        # Register components
        container.register(IFrameCapture, CameraFrameCapture, ComponentLifetime.SINGLETON)
        container.register(IObjectDetector, YOLODetector, ComponentLifetime.TRANSIENT)

        # Resolve dependencies
        frame_capture = await container.resolve(IFrameCapture)

        # Start all components
        await container.start_all()

        # ... use components ...

        # Stop all components
        await container.stop_all()
    """

    def __init__(self) -> None:
        """Initialize service container"""
        self._registrations: Dict[Type[Any], ComponentRegistration[Any]] = {}
        self._singletons: Dict[Type[Any], Any] = {}
        self._scoped_instances: Dict[str, Dict[Type[Any], Any]] = {}
        self._lock = asyncio.Lock()
        self._started = False
        self._config: Dict[str, Any] = {}

    def set_config(self, config: Dict[str, Any]) -> None:
        """
        Set configuration for dependency injection

        Args:
            config: Configuration dictionary
        """
        self._config = config

    def register(
        self,
        interface: Type[T],
        implementation: Type[T],
        lifetime: ComponentLifetime = ComponentLifetime.TRANSIENT,
    ) -> "ServiceContainer":
        """
        Register a component implementation for an interface

        Args:
            interface: Interface type (abstract base class)
            implementation: Concrete implementation class
            lifetime: Component lifetime strategy

        Returns:
            Self for method chaining

        Raises:
            DIError: If registration fails
        """
        logger.info(
            f"Registering {implementation.__name__} for {interface.__name__} "
            f"with {lifetime.value} lifetime"
        )

        registration = ComponentRegistration(
            interface=interface,
            implementation=implementation,
            lifetime=lifetime,
        )

        # Extract constructor dependencies
        registration.dependencies = self._extract_dependencies(implementation)

        self._registrations[interface] = registration
        return self

    def register_instance(
        self,
        interface: Type[T],
        instance: T,
    ) -> "ServiceContainer":
        """
        Register a pre-created instance

        Args:
            interface: Interface type
            instance: Instance to register

        Returns:
            Self for method chaining
        """
        logger.info(f"Registering instance for {interface.__name__}")

        registration = ComponentRegistration(
            interface=interface,
            implementation=type(instance),
            lifetime=ComponentLifetime.SINGLETON,
            instance=instance,
        )

        self._registrations[interface] = registration
        self._singletons[interface] = instance
        return self

    def register_factory(
        self,
        interface: Type[T],
        factory: Callable[..., T],
        lifetime: ComponentLifetime = ComponentLifetime.TRANSIENT,
    ) -> "ServiceContainer":
        """
        Register a factory function for creating instances

        Args:
            interface: Interface type
            factory: Factory function
            lifetime: Component lifetime strategy

        Returns:
            Self for method chaining
        """
        logger.info(
            f"Registering factory for {interface.__name__} " f"with {lifetime.value} lifetime"
        )

        registration = ComponentRegistration(
            interface=interface,
            implementation=interface,  # Use interface as placeholder
            lifetime=lifetime,
            factory=factory,
        )

        # Extract factory dependencies
        registration.dependencies = self._extract_dependencies(factory)

        self._registrations[interface] = registration
        return self

    async def resolve(self, interface: Type[T]) -> T:
        """
        Resolve and return an instance of the requested interface

        Args:
            interface: Interface type to resolve

        Returns:
            Instance of the interface

        Raises:
            ComponentNotFoundError: If component not registered
            CircularDependencyError: If circular dependency detected
        """
        async with self._lock:
            return await self._resolve_internal(interface, set())

    async def _resolve_internal(
        self,
        interface: Type[T],
        resolving: set[Type[Any]],
    ) -> T:
        """
        Internal resolve method with circular dependency detection

        Args:
            interface: Interface type to resolve
            resolving: Set of types currently being resolved

        Returns:
            Instance of the interface

        Raises:
            ComponentNotFoundError: If component not registered
            CircularDependencyError: If circular dependency detected
        """
        # Check if registered
        if interface not in self._registrations:
            raise ComponentNotFoundError(f"Component {interface.__name__} not registered")

        registration = self._registrations[interface]

        # Check for circular dependencies
        if interface in resolving:
            raise CircularDependencyError(f"Circular dependency detected: {interface.__name__}")

        # Handle singleton lifetime
        if registration.lifetime == ComponentLifetime.SINGLETON:
            if interface in self._singletons:
                return cast(T, self._singletons[interface])

            # Create singleton instance
            resolving.add(interface)
            instance = await self._create_instance(registration, resolving)
            resolving.remove(interface)

            self._singletons[interface] = instance
            return cast(T, instance)

        # Handle transient lifetime
        if registration.lifetime == ComponentLifetime.TRANSIENT:
            resolving.add(interface)
            instance = await self._create_instance(registration, resolving)
            resolving.remove(interface)
            return cast(T, instance)

        # Handle scoped lifetime (not implemented in this version)
        raise NotImplementedError("Scoped lifetime not yet implemented")

    async def _create_instance(
        self,
        registration: ComponentRegistration[T],
        resolving: set[Type[Any]],
    ) -> T:
        """
        Create an instance of the registered component

        Args:
            registration: Component registration
            resolving: Set of types currently being resolved

        Returns:
            Created instance
        """
        # Use pre-created instance if available
        if registration.instance is not None:
            return registration.instance

        # Use factory if available
        if registration.factory is not None:
            dependencies = await self._resolve_dependencies(
                registration.dependencies,
                resolving,
            )
            if inspect.iscoroutinefunction(registration.factory):
                return await registration.factory(**dependencies)
            else:
                return registration.factory(**dependencies)

        # Create instance using constructor
        dependencies = await self._resolve_dependencies(
            registration.dependencies,
            resolving,
        )

        try:
            instance = registration.implementation(**dependencies)
            return instance
        except Exception as e:
            logger.error(
                f"Failed to create instance of {registration.implementation.__name__}: {e}"
            )
            raise DIError(
                f"Failed to create instance of {registration.implementation.__name__}: {e}"
            )

    async def _resolve_dependencies(
        self,
        dependencies: list[Type[Any]],
        resolving: set[Type[Any]],
    ) -> Dict[str, Any]:
        """
        Resolve all dependencies for a component

        Args:
            dependencies: List of dependency types
            resolving: Set of types currently being resolved

        Returns:
            Dictionary of resolved dependencies
        """
        resolved: Dict[str, Any] = {}

        for dep_type in dependencies:
            # Get parameter name from type
            param_name = self._get_parameter_name(dep_type)
            if param_name:
                resolved[param_name] = await self._resolve_internal(
                    dep_type,
                    resolving,
                )

        return resolved

    def _extract_dependencies(
        self,
        target: Type[Any] | Callable[..., Any],
    ) -> list[Type[Any]]:
        """
        Extract constructor dependencies from a class or factory function

        Args:
            target: Class or factory function

        Returns:
            List of dependency types
        """
        try:
            if inspect.isclass(target):
                # Get __init__ method signature
                init_method = target.__init__
                type_hints = get_type_hints(init_method)
            else:
                # Get function signature
                type_hints = get_type_hints(target)

            # Extract parameter types (excluding 'self' and 'return')
            dependencies: list[Type[Any]] = []
            for param_name, param_type in type_hints.items():
                if param_name not in ("self", "return"):
                    dependencies.append(param_type)

            return dependencies

        except Exception as e:
            logger.warning(f"Failed to extract dependencies: {e}")
            return []

    def _get_parameter_name(self, param_type: Type[Any]) -> Optional[str]:
        """
        Get parameter name from type

        Args:
            param_type: Parameter type

        Returns:
            Parameter name or None
        """
        # For now, use simple heuristic: convert type name to snake_case
        type_name = param_type.__name__
        if type_name.startswith("I"):
            type_name = type_name[1:]  # Remove 'I' prefix from interface names

        # Convert CamelCase to snake_case
        import re

        snake_case = re.sub(r"(?<!^)(?=[A-Z])", "_", type_name).lower()
        return snake_case

    async def start_all(self) -> None:
        """
        Start all registered singleton components

        Raises:
            LifecycleError: If start fails
        """
        if self._started:
            logger.warning("Container already started")
            return

        logger.info("Starting all components")

        for interface, instance in self._singletons.items():
            if isinstance(instance, ILifecycle):
                try:
                    await instance.initialize()
                    await instance.start()
                    logger.info(f"Started {interface.__name__}")
                except Exception as e:
                    logger.error(f"Failed to start {interface.__name__}: {e}")
                    raise LifecycleError(f"Failed to start {interface.__name__}: {e}")

        self._started = True

    async def stop_all(self) -> None:
        """
        Stop all registered singleton components

        Raises:
            LifecycleError: If stop fails
        """
        if not self._started:
            logger.warning("Container not started")
            return

        logger.info("Stopping all components")

        # Stop in reverse order
        for interface, instance in reversed(list(self._singletons.items())):
            if isinstance(instance, ILifecycle):
                try:
                    await instance.stop()
                    await instance.cleanup()
                    logger.info(f"Stopped {interface.__name__}")
                except Exception as e:
                    logger.error(f"Failed to stop {interface.__name__}: {e}")
                    # Continue stopping other components

        self._started = False

    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of all singleton components

        Returns:
            Dictionary mapping component names to health status
        """
        health_status: Dict[str, bool] = {}

        for interface, instance in self._singletons.items():
            if isinstance(instance, ILifecycle):
                try:
                    is_healthy = instance.is_healthy()
                    health_status[interface.__name__] = is_healthy
                except Exception as e:
                    logger.error(f"Health check failed for {interface.__name__}: {e}")
                    health_status[interface.__name__] = False

        return health_status

    @asynccontextmanager
    async def lifecycle_scope(self) -> AsyncIterator["ServiceContainer"]:
        """
        Context manager for automatic lifecycle management

        Example:
            async with container.lifecycle_scope():
                frame_capture = await container.resolve(IFrameCapture)
                # ... use components ...
            # Components automatically stopped and cleaned up
        """
        try:
            await self.start_all()
            yield self
        finally:
            await self.stop_all()

    def is_registered(self, interface: Type[Any]) -> bool:
        """
        Check if an interface is registered

        Args:
            interface: Interface type

        Returns:
            True if registered
        """
        return interface in self._registrations

    def get_registrations(self) -> Dict[Type[Any], ComponentRegistration[Any]]:
        """
        Get all component registrations

        Returns:
            Dictionary of registrations
        """
        return self._registrations.copy()

    def clear(self) -> None:
        """Clear all registrations and singletons"""
        self._registrations.clear()
        self._singletons.clear()
        self._scoped_instances.clear()
        self._started = False
        logger.info("Container cleared")

    def __repr__(self) -> str:
        return (
            f"ServiceContainer("
            f"registrations={len(self._registrations)}, "
            f"singletons={len(self._singletons)}, "
            f"started={self._started})"
        )


# ============================================================================
# Global Container Instance
# ============================================================================

_global_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """
    Get the global service container instance

    Returns:
        Global ServiceContainer instance
    """
    global _global_container
    if _global_container is None:
        _global_container = ServiceContainer()
    return _global_container


def set_container(container: ServiceContainer) -> None:
    """
    Set the global service container instance

    Args:
        container: ServiceContainer to use as global
    """
    global _global_container
    _global_container = container


def reset_container() -> None:
    """Reset the global service container"""
    global _global_container
    if _global_container is not None:
        _global_container.clear()
    _global_container = None


# ============================================================================
# Decorator for Injectable Components
# ============================================================================


def injectable(
    interface: Optional[Type[T]] = None,
    lifetime: ComponentLifetime = ComponentLifetime.TRANSIENT,
) -> Callable[[Type[T]], Type[T]]:
    """
    Decorator to mark a class as injectable and auto-register it

    Args:
        interface: Interface type to register for
        lifetime: Component lifetime strategy

    Returns:
        Decorator function

    Example:
        @injectable(IFrameCapture, ComponentLifetime.SINGLETON)
        class CameraFrameCapture(IFrameCapture):
            pass
    """

    def decorator(cls: Type[T]) -> Type[T]:
        # Get interface from class bases if not provided
        target_interface = interface
        if target_interface is None:
            # Find first abstract base class
            for base in cls.__bases__:
                if inspect.isabstract(base):
                    target_interface = base
                    break

        if target_interface is None:
            raise DIError(
                f"Cannot determine interface for {cls.__name__}. "
                "Provide explicit interface parameter."
            )

        # Auto-register with global container
        container = get_container()
        container.register(target_interface, cls, lifetime)

        return cls

    return decorator
