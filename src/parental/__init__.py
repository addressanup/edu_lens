"""
Parental Controls Module for EduLens

Provides comprehensive parental control features including:
- Usage limits and schedules
- Content filtering
- Activity monitoring
- Remote device management
- Parent notifications
"""

from .usage_controller import UsageController
from .content_filter import ContentFilter
from .activity_monitor import ActivityMonitor
from .device_manager import DeviceManager
from .notification_service import NotificationService

__all__ = [
    'UsageController',
    'ContentFilter',
    'ActivityMonitor',
    'DeviceManager',
    'NotificationService',
]

__version__ = '1.0.0'
