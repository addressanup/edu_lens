"""
Notification Service for EduLens Parental Controls

Sends notifications to parents about their child's activities and progress.
"""

import json
import logging
from datetime import datetime, time
from typing import Dict, List, Optional, Set
from enum import Enum
from pathlib import Path


logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications"""
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_SUMMARY = "weekly_summary"
    MILESTONE = "milestone"
    CONCERN = "concern"
    LIMIT_REACHED = "limit_reached"
    DEVICE_STATUS = "device_status"
    CONTENT_BLOCKED = "content_blocked"


class NotificationChannel(Enum):
    """Notification delivery channels"""
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"
    IN_APP = "in_app"


class NotificationPriority(Enum):
    """Priority levels for notifications"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Notification:
    """Represents a notification to be sent."""

    def __init__(
        self,
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        data: Optional[Dict] = None
    ):
        self.notification_id = str(datetime.now().timestamp())
        self.notification_type = notification_type
        self.title = title
        self.message = message
        self.priority = priority
        self.data = data or {}
        self.created_at = datetime.now()
        self.sent = False
        self.sent_at: Optional[datetime] = None
        self.channels_used: List[str] = []

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'notification_id': self.notification_id,
            'notification_type': self.notification_type.value,
            'title': self.title,
            'message': self.message,
            'priority': self.priority.value,
            'data': self.data,
            'created_at': self.created_at.isoformat(),
            'sent': self.sent,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'channels_used': self.channels_used
        }


class NotificationPreferences:
    """Parent's notification preferences."""

    def __init__(self):
        # Enabled notification types
        self.enabled_types: Set[NotificationType] = {
            NotificationType.DAILY_SUMMARY,
            NotificationType.MILESTONE,
            NotificationType.CONCERN,
            NotificationType.LIMIT_REACHED
        }

        # Channel preferences per notification type
        self.channel_preferences: Dict[NotificationType, Set[NotificationChannel]] = {
            NotificationType.DAILY_SUMMARY: {NotificationChannel.EMAIL},
            NotificationType.WEEKLY_SUMMARY: {NotificationChannel.EMAIL},
            NotificationType.MILESTONE: {NotificationChannel.PUSH, NotificationChannel.IN_APP},
            NotificationType.CONCERN: {NotificationChannel.EMAIL, NotificationChannel.PUSH},
            NotificationType.LIMIT_REACHED: {NotificationChannel.PUSH, NotificationChannel.IN_APP},
            NotificationType.DEVICE_STATUS: {NotificationChannel.PUSH},
            NotificationType.CONTENT_BLOCKED: {NotificationChannel.IN_APP}
        }

        # Quiet hours (no notifications during this time)
        self.quiet_hours_enabled = True
        self.quiet_hours_start = time(22, 0)  # 10 PM
        self.quiet_hours_end = time(7, 0)     # 7 AM

        # Daily summary timing
        self.daily_summary_time = time(20, 0)  # 8 PM

        # Weekly summary day and time
        self.weekly_summary_day = 6  # Sunday
        self.weekly_summary_time = time(18, 0)  # 6 PM

        # Minimum time between similar notifications (minutes)
        self.notification_throttle = 60

        # Contact information
        self.email_address: Optional[str] = None
        self.phone_number: Optional[str] = None
        self.push_token: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'enabled_types': [nt.value for nt in self.enabled_types],
            'channel_preferences': {
                nt.value: [ch.value for ch in channels]
                for nt, channels in self.channel_preferences.items()
            },
            'quiet_hours_enabled': self.quiet_hours_enabled,
            'quiet_hours_start': self.quiet_hours_start.isoformat(),
            'quiet_hours_end': self.quiet_hours_end.isoformat(),
            'daily_summary_time': self.daily_summary_time.isoformat(),
            'weekly_summary_day': self.weekly_summary_day,
            'weekly_summary_time': self.weekly_summary_time.isoformat(),
            'notification_throttle': self.notification_throttle,
            'email_address': self.email_address,
            'phone_number': self.phone_number,
            'push_token': self.push_token
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'NotificationPreferences':
        """Create from dictionary."""
        prefs = cls()

        prefs.enabled_types = {
            NotificationType(nt) for nt in data.get('enabled_types', [])
        }

        channel_prefs = data.get('channel_preferences', {})
        prefs.channel_preferences = {
            NotificationType(nt): {NotificationChannel(ch) for ch in channels}
            for nt, channels in channel_prefs.items()
        }

        prefs.quiet_hours_enabled = data.get('quiet_hours_enabled', True)
        prefs.quiet_hours_start = time.fromisoformat(data.get('quiet_hours_start', '22:00:00'))
        prefs.quiet_hours_end = time.fromisoformat(data.get('quiet_hours_end', '07:00:00'))
        prefs.daily_summary_time = time.fromisoformat(data.get('daily_summary_time', '20:00:00'))
        prefs.weekly_summary_day = data.get('weekly_summary_day', 6)
        prefs.weekly_summary_time = time.fromisoformat(data.get('weekly_summary_time', '18:00:00'))
        prefs.notification_throttle = data.get('notification_throttle', 60)
        prefs.email_address = data.get('email_address')
        prefs.phone_number = data.get('phone_number')
        prefs.push_token = data.get('push_token')

        return prefs


class NotificationService:
    """
    Manages parent notifications.

    Features:
    - Daily and weekly summaries
    - Milestone notifications
    - Concern alerts
    - Configurable preferences
    - Quiet hours
    - Multiple delivery channels
    - Notification throttling
    """

    def __init__(self, parent_id: str, storage_path: Optional[Path] = None):
        """
        Initialize NotificationService.

        Args:
            parent_id: Unique identifier for the parent
            storage_path: Path to store notification data
        """
        self.parent_id = parent_id
        self.storage_path = storage_path or Path(f"/tmp/edulens/notifications/{parent_id}")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.preferences = NotificationPreferences()
        self.notification_history: List[Notification] = []
        self.pending_notifications: List[Notification] = []

        # Track last notification time per type to enable throttling
        self.last_notification_time: Dict[NotificationType, datetime] = {}

        self._load_state()

    def send_daily_summary(
        self,
        user_id: str,
        summary_data: Dict,
        force: bool = False
    ) -> Optional[str]:
        """
        Send daily activity summary to parent.

        Args:
            user_id: User ID for the child
            summary_data: Dictionary with daily statistics
            force: Force send even if throttled

        Returns:
            Notification ID if sent, None if skipped
        """
        notification_type = NotificationType.DAILY_SUMMARY

        if not self._should_send(notification_type, force):
            logger.info(f"Daily summary skipped for parent {self.parent_id} (throttled or disabled)")
            return None

        # Format summary message
        title = f"Daily Summary for {summary_data.get('date', 'Today')}"

        message_parts = [
            f"Total time: {summary_data.get('total_duration_minutes', 0)} minutes",
            f"Sessions: {summary_data.get('total_sessions', 0)}",
            f"Accuracy: {summary_data.get('overall_accuracy', 0)}%",
        ]

        if summary_data.get('subjects'):
            subjects = ", ".join(summary_data['subjects'].keys())
            message_parts.append(f"Subjects: {subjects}")

        message = "\n".join(message_parts)

        notification = Notification(
            notification_type=notification_type,
            title=title,
            message=message,
            priority=NotificationPriority.LOW,
            data={'user_id': user_id, 'summary': summary_data}
        )

        return self._send_notification(notification)

    def send_weekly_summary(
        self,
        user_id: str,
        summary_data: Dict,
        force: bool = False
    ) -> Optional[str]:
        """
        Send weekly activity summary to parent.

        Args:
            user_id: User ID for the child
            summary_data: Dictionary with weekly statistics
            force: Force send even if throttled

        Returns:
            Notification ID if sent, None if skipped
        """
        notification_type = NotificationType.WEEKLY_SUMMARY

        if not self._should_send(notification_type, force):
            logger.info(f"Weekly summary skipped for parent {self.parent_id} (throttled or disabled)")
            return None

        title = f"Weekly Summary ({summary_data.get('start_date')} - {summary_data.get('end_date')})"

        message_parts = [
            f"Total time: {summary_data.get('total_duration_minutes', 0)} minutes",
            f"Active days: {summary_data.get('active_days', 0)}/7",
            f"Average daily: {summary_data.get('average_daily_duration', 0)} minutes",
            f"Overall accuracy: {summary_data.get('overall_accuracy', 0)}%",
        ]

        message = "\n".join(message_parts)

        notification = Notification(
            notification_type=notification_type,
            title=title,
            message=message,
            priority=NotificationPriority.LOW,
            data={'user_id': user_id, 'summary': summary_data}
        )

        return self._send_notification(notification)

    def send_milestone_alert(
        self,
        user_id: str,
        milestone_type: str,
        milestone_data: Dict,
        force: bool = False
    ) -> Optional[str]:
        """
        Send notification about achievement milestone.

        Args:
            user_id: User ID for the child
            milestone_type: Type of milestone achieved
            milestone_data: Details about the milestone
            force: Force send even if throttled

        Returns:
            Notification ID if sent, None if skipped
        """
        notification_type = NotificationType.MILESTONE

        if not self._should_send(notification_type, force):
            logger.info(f"Milestone alert skipped for parent {self.parent_id} (throttled or disabled)")
            return None

        # Format milestone message
        title = f"Milestone Achieved: {milestone_type}"
        message = milestone_data.get('description', 'Great progress!')

        notification = Notification(
            notification_type=notification_type,
            title=title,
            message=message,
            priority=NotificationPriority.NORMAL,
            data={
                'user_id': user_id,
                'milestone_type': milestone_type,
                'milestone_data': milestone_data
            }
        )

        return self._send_notification(notification)

    def send_concern_alert(
        self,
        user_id: str,
        concern_type: str,
        concern_data: Dict,
        force: bool = False
    ) -> Optional[str]:
        """
        Send notification about learning concerns.

        Args:
            user_id: User ID for the child
            concern_type: Type of concern (struggling, low_engagement, etc.)
            concern_data: Details about the concern
            force: Force send even if throttled

        Returns:
            Notification ID if sent, None if skipped
        """
        notification_type = NotificationType.CONCERN

        if not self._should_send(notification_type, force):
            logger.info(f"Concern alert skipped for parent {self.parent_id} (throttled or disabled)")
            return None

        # Format concern message
        title = f"Learning Concern: {concern_type}"
        message = concern_data.get('description', 'May need additional support')

        notification = Notification(
            notification_type=notification_type,
            title=title,
            message=message,
            priority=NotificationPriority.HIGH,
            data={
                'user_id': user_id,
                'concern_type': concern_type,
                'concern_data': concern_data
            }
        )

        return self._send_notification(notification)

    def send_limit_reached_alert(
        self,
        user_id: str,
        limit_type: str,
        limit_data: Dict,
        force: bool = True  # Usually want to send these
    ) -> Optional[str]:
        """
        Send notification when usage limit is reached.

        Args:
            user_id: User ID for the child
            limit_type: Type of limit (daily, time_slot, etc.)
            limit_data: Details about the limit
            force: Force send even if throttled

        Returns:
            Notification ID if sent, None if skipped
        """
        notification_type = NotificationType.LIMIT_REACHED

        if not self._should_send(notification_type, force):
            return None

        title = f"Usage Limit Reached"
        message = limit_data.get('message', f"{limit_type} limit reached")

        notification = Notification(
            notification_type=notification_type,
            title=title,
            message=message,
            priority=NotificationPriority.NORMAL,
            data={
                'user_id': user_id,
                'limit_type': limit_type,
                'limit_data': limit_data
            }
        )

        return self._send_notification(notification)

    def send_device_status_alert(
        self,
        device_id: str,
        status_type: str,
        status_data: Dict,
        force: bool = False
    ) -> Optional[str]:
        """
        Send notification about device status changes.

        Args:
            device_id: Device ID
            status_type: Type of status change (offline, low_battery, etc.)
            status_data: Details about the status
            force: Force send even if throttled

        Returns:
            Notification ID if sent, None if skipped
        """
        notification_type = NotificationType.DEVICE_STATUS

        if not self._should_send(notification_type, force):
            return None

        title = f"Device Status: {status_type}"
        message = status_data.get('message', 'Device status changed')

        priority = NotificationPriority.HIGH if status_type == 'offline' else NotificationPriority.NORMAL

        notification = Notification(
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority,
            data={
                'device_id': device_id,
                'status_type': status_type,
                'status_data': status_data
            }
        )

        return self._send_notification(notification)

    def send_content_blocked_alert(
        self,
        user_id: str,
        content_info: Dict,
        force: bool = False
    ) -> Optional[str]:
        """
        Send notification when content is blocked by filters.

        Args:
            user_id: User ID for the child
            content_info: Information about blocked content
            force: Force send even if throttled

        Returns:
            Notification ID if sent, None if skipped
        """
        notification_type = NotificationType.CONTENT_BLOCKED

        if not self._should_send(notification_type, force):
            return None

        title = "Content Blocked"
        message = f"Content blocked: {content_info.get('reason', 'Filter violation')}"

        notification = Notification(
            notification_type=notification_type,
            title=title,
            message=message,
            priority=NotificationPriority.LOW,
            data={
                'user_id': user_id,
                'content_info': content_info
            }
        )

        return self._send_notification(notification)

    def configure_preferences(
        self,
        enabled_types: Optional[Set[NotificationType]] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        push_token: Optional[str] = None,
        quiet_hours_enabled: Optional[bool] = None,
        quiet_hours_start: Optional[time] = None,
        quiet_hours_end: Optional[time] = None,
        daily_summary_time: Optional[time] = None
    ) -> None:
        """
        Configure notification preferences.

        Args:
            enabled_types: Set of enabled notification types
            email: Email address for notifications
            phone: Phone number for SMS notifications
            push_token: Device token for push notifications
            quiet_hours_enabled: Enable/disable quiet hours
            quiet_hours_start: Start time for quiet hours
            quiet_hours_end: End time for quiet hours
            daily_summary_time: Time to send daily summaries
        """
        if enabled_types is not None:
            self.preferences.enabled_types = enabled_types

        if email is not None:
            self.preferences.email_address = email

        if phone is not None:
            self.preferences.phone_number = phone

        if push_token is not None:
            self.preferences.push_token = push_token

        if quiet_hours_enabled is not None:
            self.preferences.quiet_hours_enabled = quiet_hours_enabled

        if quiet_hours_start is not None:
            self.preferences.quiet_hours_start = quiet_hours_start

        if quiet_hours_end is not None:
            self.preferences.quiet_hours_end = quiet_hours_end

        if daily_summary_time is not None:
            self.preferences.daily_summary_time = daily_summary_time

        logger.info(f"Updated notification preferences for parent {self.parent_id}")
        self._save_state()

    def set_channel_preferences(
        self,
        notification_type: NotificationType,
        channels: Set[NotificationChannel]
    ) -> None:
        """
        Set preferred delivery channels for a notification type.

        Args:
            notification_type: Type of notification
            channels: Set of channels to use
        """
        self.preferences.channel_preferences[notification_type] = channels
        logger.info(
            f"Set channels for {notification_type.value}: "
            f"{[c.value for c in channels]} for parent {self.parent_id}"
        )
        self._save_state()

    def get_notification_history(
        self,
        notification_type: Optional[NotificationType] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get notification history.

        Args:
            notification_type: Filter by type (None for all)
            limit: Maximum number to return

        Returns:
            List of notification dictionaries
        """
        history = self.notification_history[-limit:]

        if notification_type:
            history = [n for n in history if n.notification_type == notification_type]

        return [n.to_dict() for n in reversed(history)]

    def _should_send(self, notification_type: NotificationType, force: bool) -> bool:
        """Check if notification should be sent."""
        if force:
            return True

        # Check if type is enabled
        if notification_type not in self.preferences.enabled_types:
            return False

        # Check quiet hours (except for urgent notifications)
        if self.preferences.quiet_hours_enabled:
            current_time = datetime.now().time()
            start = self.preferences.quiet_hours_start
            end = self.preferences.quiet_hours_end

            # Handle overnight quiet hours
            if start > end:
                in_quiet_hours = current_time >= start or current_time <= end
            else:
                in_quiet_hours = start <= current_time <= end

            if in_quiet_hours and notification_type != NotificationType.CONCERN:
                logger.info(f"Notification skipped due to quiet hours: {notification_type.value}")
                return False

        # Check throttling
        if notification_type in self.last_notification_time:
            last_time = self.last_notification_time[notification_type]
            minutes_since = (datetime.now() - last_time).total_seconds() / 60

            if minutes_since < self.preferences.notification_throttle:
                logger.info(f"Notification throttled: {notification_type.value}")
                return False

        return True

    def _send_notification(self, notification: Notification) -> str:
        """Send a notification through configured channels."""
        notification_type = notification.notification_type
        channels = self.preferences.channel_preferences.get(
            notification_type,
            {NotificationChannel.IN_APP}
        )

        # Simulate sending through each channel
        for channel in channels:
            if self._send_via_channel(notification, channel):
                notification.channels_used.append(channel.value)

        if notification.channels_used:
            notification.sent = True
            notification.sent_at = datetime.now()
            self.last_notification_time[notification_type] = datetime.now()

            self.notification_history.append(notification)
            logger.info(
                f"Sent {notification_type.value} notification to parent {self.parent_id} "
                f"via {notification.channels_used}"
            )

            self._save_state()
            return notification.notification_id
        else:
            logger.warning(
                f"Failed to send notification {notification.notification_id} "
                f"to parent {self.parent_id}"
            )
            return None

    def _send_via_channel(
        self,
        notification: Notification,
        channel: NotificationChannel
    ) -> bool:
        """
        Send notification via specific channel.

        This is a stub - in production, integrate with actual services.
        """
        if channel == NotificationChannel.EMAIL:
            if self.preferences.email_address:
                # Integrate with email service (e.g., SendGrid, AWS SES)
                logger.info(f"EMAIL: {self.preferences.email_address} - {notification.title}")
                return True

        elif channel == NotificationChannel.PUSH:
            if self.preferences.push_token:
                # Integrate with push service (e.g., FCM, APNs)
                logger.info(f"PUSH: {self.preferences.push_token} - {notification.title}")
                return True

        elif channel == NotificationChannel.SMS:
            if self.preferences.phone_number:
                # Integrate with SMS service (e.g., Twilio)
                logger.info(f"SMS: {self.preferences.phone_number} - {notification.title}")
                return True

        elif channel == NotificationChannel.IN_APP:
            # Store for in-app retrieval
            logger.info(f"IN-APP: {notification.title}")
            return True

        return False

    def _save_state(self) -> None:
        """Save service state to disk."""
        state = {
            'parent_id': self.parent_id,
            'preferences': self.preferences.to_dict(),
            'notification_history': [
                n.to_dict() for n in self.notification_history[-100:]  # Keep last 100
            ],
            'last_notification_time': {
                nt.value: dt.isoformat()
                for nt, dt in self.last_notification_time.items()
            }
        }

        state_file = self.storage_path / 'notification_state.json'
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def _load_state(self) -> None:
        """Load service state from disk."""
        state_file = self.storage_path / 'notification_state.json'

        if not state_file.exists():
            return

        try:
            with open(state_file, 'r') as f:
                state = json.load(f)

            self.preferences = NotificationPreferences.from_dict(
                state.get('preferences', {})
            )

            # Load notification history
            self.notification_history = []
            for notif_data in state.get('notification_history', []):
                notif = Notification(
                    notification_type=NotificationType(notif_data['notification_type']),
                    title=notif_data['title'],
                    message=notif_data['message'],
                    priority=NotificationPriority(notif_data['priority']),
                    data=notif_data.get('data', {})
                )
                notif.notification_id = notif_data['notification_id']
                notif.created_at = datetime.fromisoformat(notif_data['created_at'])
                notif.sent = notif_data.get('sent', False)
                if notif_data.get('sent_at'):
                    notif.sent_at = datetime.fromisoformat(notif_data['sent_at'])
                notif.channels_used = notif_data.get('channels_used', [])

                self.notification_history.append(notif)

            # Load last notification times
            last_times = state.get('last_notification_time', {})
            self.last_notification_time = {
                NotificationType(nt): datetime.fromisoformat(dt)
                for nt, dt in last_times.items()
            }

            logger.info(f"Loaded notification state for parent {self.parent_id}")
        except Exception as e:
            logger.error(f"Error loading notification state for parent {self.parent_id}: {e}")
