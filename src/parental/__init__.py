"""
Parental Controls Module for EduLens

Provides comprehensive parental control features including:
- Usage limits and schedules
- Content filtering
- Activity monitoring
- Remote device management
- Parent notifications
"""

from .activity_monitor import ActivityMonitor
from .content_filter import ContentFilter
from .device_manager import DeviceManager
from .notification_service import NotificationService
from .usage_controller import UsageController

__all__ = [
    "UsageController",
    "ContentFilter",
    "ActivityMonitor",
    "DeviceManager",
    "NotificationService",
]

__version__ = "1.0.0"
