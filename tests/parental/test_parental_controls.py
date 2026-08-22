"""
Comprehensive test suite for EduLens Parental Controls

Tests all components:
- UsageController
- ContentFilter
- ActivityMonitor
- DeviceManager
- NotificationService
"""

import shutil
import sys
import tempfile
import unittest
from datetime import datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from parental.activity_monitor import ActivityMonitor, SessionData
from parental.content_filter import (
    AgeGroup,
    ContentFilter,
    ContentType,
    DifficultyLevel,
    FilterMode,
)
from parental.device_manager import (
    CommandPriority,
    CommandType,
    DeviceManager,
    DeviceStatus,
    RemoteCommand,
)
from parental.notification_service import (
    NotificationChannel,
    NotificationPriority,
    NotificationService,
    NotificationType,
)
from parental.usage_controller import DayOfWeek, LimitStatus, UsageController


class TestUsageController(unittest.TestCase):
    """Test cases for UsageController."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.controller = UsageController(user_id="test_user_001", storage_path=Path(self.temp_dir))

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_set_daily_limit(self):
        """Test setting daily time limits."""
        self.controller.set_daily_limit(DayOfWeek.MONDAY, 60)
        self.assertEqual(self.controller.daily_limits[DayOfWeek.MONDAY], 60)

    def test_set_daily_limit_invalid(self):
        """Test that negative limits are rejected."""
        with self.assertRaises(ValueError):
            self.controller.set_daily_limit(DayOfWeek.MONDAY, -10)

    def test_set_all_days_limit(self):
        """Test setting same limit for all days."""
        self.controller.set_all_days_limit(90)
        for day in DayOfWeek:
            self.assertEqual(self.controller.daily_limits[day], 90)

    def test_set_schedule(self):
        """Test setting allowed usage hours."""
        schedule = [(time(15, 0), time(17, 0))]
        self.controller.set_schedule(DayOfWeek.MONDAY, schedule)
        self.assertEqual(self.controller.schedules[DayOfWeek.MONDAY], schedule)

    def test_set_schedule_invalid_range(self):
        """Test that invalid time ranges are rejected."""
        with self.assertRaises(ValueError):
            self.controller.set_schedule(
                DayOfWeek.MONDAY, [(time(17, 0), time(15, 0))]  # End before start
            )

    def test_set_schedule_overlapping(self):
        """Test that overlapping ranges are rejected."""
        with self.assertRaises(ValueError):
            self.controller.set_schedule(
                DayOfWeek.MONDAY, [(time(15, 0), time(17, 0)), (time(16, 0), time(18, 0))]
            )

    def test_check_allowed_no_restrictions(self):
        """Test that usage is allowed with no restrictions."""
        status, message = self.controller.check_allowed()
        self.assertEqual(status, LimitStatus.ALLOWED)

    def test_check_allowed_within_schedule(self):
        """Test checking allowed during scheduled hours."""
        # Set schedule for today
        today = datetime.now().weekday()
        day = DayOfWeek(today)
        schedule = [(time(9, 0), time(22, 0))]
        self.controller.set_schedule(day, schedule)

        # Check at 10 AM
        check_time = datetime.now().replace(hour=10, minute=0)
        status, message = self.controller.check_allowed(check_time)
        self.assertEqual(status, LimitStatus.ALLOWED)

    def test_check_allowed_outside_schedule(self):
        """Test checking allowed outside scheduled hours."""
        today = datetime.now().weekday()
        day = DayOfWeek(today)
        schedule = [(time(9, 0), time(17, 0))]
        self.controller.set_schedule(day, schedule)

        # Check at 8 AM (before schedule)
        check_time = datetime.now().replace(hour=8, minute=0)
        status, message = self.controller.check_allowed(check_time)
        self.assertEqual(status, LimitStatus.OUTSIDE_SCHEDULE)

    def test_session_tracking(self):
        """Test session start and end."""
        start_time = datetime.now()
        success, message = self.controller.start_session(start_time)
        self.assertTrue(success)

        # Simulate 30 minutes of usage
        end_time = start_time + timedelta(minutes=30)
        minutes = self.controller.end_session(end_time)
        self.assertEqual(minutes, 30)

    def test_daily_limit_enforcement(self):
        """Test that daily limits are enforced."""
        today = datetime.now().weekday()
        day = DayOfWeek(today)

        # Set 60 minute limit
        self.controller.set_daily_limit(day, 60)

        # Use 50 minutes
        date_key = datetime.now().strftime("%Y-%m-%d")
        self.controller.usage_data[date_key] = 50

        # Should be in grace period
        status, message = self.controller.check_allowed()
        self.assertIn(status, [LimitStatus.ALLOWED, LimitStatus.GRACE_PERIOD])

        # Use 65 minutes
        self.controller.usage_data[date_key] = 65

        # Should hit limit
        status, message = self.controller.check_allowed()
        self.assertEqual(status, LimitStatus.LIMIT_REACHED)

    def test_remaining_time(self):
        """Test getting remaining time."""
        today = datetime.now().weekday()
        day = DayOfWeek(today)

        self.controller.set_daily_limit(day, 120)

        date_key = datetime.now().strftime("%Y-%m-%d")
        self.controller.usage_data[date_key] = 30

        remaining = self.controller.get_remaining_time()
        self.assertEqual(remaining, 90)

    def test_lock_unlock(self):
        """Test manual lock and unlock."""
        self.controller.lock_device()
        self.assertTrue(self.controller.is_locked)

        status, message = self.controller.check_allowed()
        self.assertEqual(status, LimitStatus.LOCKED)

        self.controller.unlock_device()
        self.assertFalse(self.controller.is_locked)

    def test_state_persistence(self):
        """Test that state is saved and loaded correctly."""
        self.controller.set_daily_limit(DayOfWeek.MONDAY, 60)
        self.controller.set_grace_period(10)

        # Create new controller with same storage
        new_controller = UsageController(user_id="test_user_001", storage_path=Path(self.temp_dir))

        self.assertEqual(new_controller.daily_limits[DayOfWeek.MONDAY], 60)
        self.assertEqual(new_controller.grace_period_minutes, 10)


class TestContentFilter(unittest.TestCase):
    """Test cases for ContentFilter."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.filter = ContentFilter(user_id="test_user_001", storage_path=Path(self.temp_dir))

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_subject_whitelist(self):
        """Test subject whitelist filtering."""
        self.filter.filter_subjects(FilterMode.WHITELIST, ["mathematics", "science"])

        # Allowed subject
        allowed, reason = self.filter.check_content(subject="mathematics")
        self.assertTrue(allowed)

        # Blocked subject
        allowed, reason = self.filter.check_content(subject="history")
        self.assertFalse(allowed)

    def test_subject_blacklist(self):
        """Test subject blacklist filtering."""
        self.filter.filter_subjects(FilterMode.BLACKLIST, ["video_games"])

        # Allowed subject
        allowed, reason = self.filter.check_content(subject="mathematics")
        self.assertTrue(allowed)

        # Blocked subject
        allowed, reason = self.filter.check_content(subject="video_games")
        self.assertFalse(allowed)

    def test_difficulty_filtering(self):
        """Test difficulty level filtering."""
        self.filter.filter_difficulty(max_level=DifficultyLevel.MIDDLE_SCHOOL)

        # Allowed difficulty
        allowed, reason = self.filter.check_content(difficulty=DifficultyLevel.ELEMENTARY)
        self.assertTrue(allowed)

        # Too difficult
        allowed, reason = self.filter.check_content(difficulty=DifficultyLevel.COLLEGE)
        self.assertFalse(allowed)

    def test_content_type_filtering(self):
        """Test content type filtering."""
        self.filter.filter_content_type(
            FilterMode.WHITELIST, [ContentType.MULTIPLE_CHOICE, ContentType.MATH_PROBLEM]
        )

        # Allowed type
        allowed, reason = self.filter.check_content(content_type=ContentType.MULTIPLE_CHOICE)
        self.assertTrue(allowed)

        # Blocked type
        allowed, reason = self.filter.check_content(content_type=ContentType.ESSAY)
        self.assertFalse(allowed)

    def test_blocked_keywords(self):
        """Test keyword blocking."""
        self.filter.add_blocked_keyword("inappropriate")

        # Clean content
        allowed, reason = self.filter.check_content(keywords=["math", "learning"])
        self.assertTrue(allowed)

        # Blocked keyword
        allowed, reason = self.filter.check_content(keywords=["inappropriate", "content"])
        self.assertFalse(allowed)

    def test_age_appropriate_defaults(self):
        """Test age-appropriate default settings."""
        self.filter.set_age_appropriate_defaults(AgeGroup.AGES_5_7)

        # Should restrict to elementary difficulty
        self.assertEqual(self.filter.max_difficulty, DifficultyLevel.ELEMENTARY)

        # Should allow only certain content types
        self.assertEqual(self.filter.content_type_mode, FilterMode.WHITELIST)
        self.assertIn(ContentType.MULTIPLE_CHOICE, self.filter.allowed_content_types)

    def test_reset_filters(self):
        """Test resetting all filters."""
        self.filter.filter_subjects(FilterMode.WHITELIST, ["math"])
        self.filter.filter_difficulty(max_level=DifficultyLevel.ELEMENTARY)

        self.filter.reset_all_filters()

        self.assertEqual(self.filter.subject_mode, FilterMode.UNRESTRICTED)
        self.assertIsNone(self.filter.max_difficulty)

    def test_state_persistence(self):
        """Test that filter state persists."""
        self.filter.filter_subjects(FilterMode.WHITELIST, ["mathematics"])
        self.filter.filter_difficulty(max_level=DifficultyLevel.HIGH_SCHOOL)

        # Create new filter with same storage
        new_filter = ContentFilter(user_id="test_user_001", storage_path=Path(self.temp_dir))

        self.assertEqual(new_filter.subject_mode, FilterMode.WHITELIST)
        self.assertIn("mathematics", new_filter.allowed_subjects)
        self.assertEqual(new_filter.max_difficulty, DifficultyLevel.HIGH_SCHOOL)


class TestActivityMonitor(unittest.TestCase):
    """Test cases for ActivityMonitor."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.monitor = ActivityMonitor(user_id="test_user_001", storage_path=Path(self.temp_dir))

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_log_session(self):
        """Test logging a session."""
        start = datetime.now() - timedelta(minutes=30)
        end = datetime.now()

        self.monitor.log_session(
            session_id="session_001",
            start_time=start,
            end_time=end,
            subject="mathematics",
            problems_attempted=10,
            problems_correct=8,
            difficulty_level="middle_school",
            topics_covered=["algebra", "equations"],
        )

        self.assertEqual(len(self.monitor.sessions), 1)
        session = self.monitor.sessions[0]
        self.assertEqual(session.subject, "mathematics")
        self.assertEqual(session.problems_attempted, 10)

    def test_daily_report(self):
        """Test generating daily report."""
        # Log some sessions
        today = datetime.now()
        for i in range(3):
            start = today - timedelta(minutes=30 * (i + 1))
            end = start + timedelta(minutes=20)
            self.monitor.log_session(
                session_id=f"session_{i}",
                start_time=start,
                end_time=end,
                subject="mathematics",
                problems_attempted=10,
                problems_correct=8,
                difficulty_level="middle_school",
                topics_covered=["algebra"],
            )

        report = self.monitor.get_daily_report(today)
        self.assertEqual(report["total_sessions"], 3)
        self.assertEqual(report["total_duration_minutes"], 60)
        self.assertEqual(report["overall_accuracy"], 80.0)

    def test_weekly_report(self):
        """Test generating weekly report."""
        # Log sessions over several days
        for day_offset in range(5):
            date = datetime.now() - timedelta(days=day_offset)
            start = date.replace(hour=10, minute=0)
            end = start + timedelta(minutes=30)

            self.monitor.log_session(
                session_id=f"session_day_{day_offset}",
                start_time=start,
                end_time=end,
                subject="mathematics",
                problems_attempted=10,
                problems_correct=7,
                difficulty_level="middle_school",
                topics_covered=["algebra"],
            )

        report = self.monitor.get_weekly_report()
        self.assertEqual(report["total_sessions"], 5)
        self.assertGreater(report["total_duration_minutes"], 0)

    def test_subject_breakdown(self):
        """Test subject breakdown analysis."""
        today = datetime.now()

        # Math sessions
        for i in range(3):
            start = today - timedelta(minutes=40 * i)
            end = start + timedelta(minutes=30)
            self.monitor.log_session(
                session_id=f"math_{i}",
                start_time=start,
                end_time=end,
                subject="mathematics",
                problems_attempted=10,
                problems_correct=8,
                difficulty_level="middle_school",
                topics_covered=["algebra"],
            )

        # Science sessions
        for i in range(2):
            start = today - timedelta(minutes=40 * (i + 3))
            end = start + timedelta(minutes=25)
            self.monitor.log_session(
                session_id=f"science_{i}",
                start_time=start,
                end_time=end,
                subject="science",
                problems_attempted=5,
                problems_correct=4,
                difficulty_level="middle_school",
                topics_covered=["biology"],
            )

        breakdown = self.monitor.get_subject_breakdown()
        self.assertIn("mathematics", breakdown)
        self.assertIn("science", breakdown)
        self.assertEqual(breakdown["mathematics"]["session_count"], 3)
        self.assertEqual(breakdown["science"]["session_count"], 2)

    def test_progress_metrics(self):
        """Test progress metrics calculation."""
        # Create sessions with improving accuracy
        base_date = datetime.now() - timedelta(days=10)

        for day in range(10):
            date = base_date + timedelta(days=day)
            start = date.replace(hour=15, minute=0)
            end = start + timedelta(minutes=30)

            # Accuracy improves over time
            correct = 5 + day // 2

            self.monitor.log_session(
                session_id=f"session_{day}",
                start_time=start,
                end_time=end,
                subject="mathematics",
                problems_attempted=10,
                problems_correct=correct,
                difficulty_level="middle_school",
                topics_covered=["algebra"],
            )

        metrics = self.monitor.get_progress_metrics(days=10)
        self.assertEqual(metrics["total_sessions"], 10)
        self.assertTrue(metrics["trends"]["improving"])

    def test_learning_insights(self):
        """Test learning insights generation."""
        # Create consistent sessions with good performance
        for day in range(7):
            date = datetime.now() - timedelta(days=day)
            start = date.replace(hour=15, minute=0)
            end = start + timedelta(minutes=30)

            self.monitor.log_session(
                session_id=f"session_{day}",
                start_time=start,
                end_time=end,
                subject="mathematics",
                problems_attempted=10,
                problems_correct=9,
                difficulty_level="middle_school",
                topics_covered=["algebra"],
            )

        insights = self.monitor.get_learning_insights(days=7)
        self.assertIn("strengths", insights)
        self.assertIn("recommendations", insights)

    def test_state_persistence(self):
        """Test that sessions persist."""
        start = datetime.now() - timedelta(minutes=30)
        end = datetime.now()

        self.monitor.log_session(
            session_id="session_001",
            start_time=start,
            end_time=end,
            subject="mathematics",
            problems_attempted=10,
            problems_correct=8,
            difficulty_level="middle_school",
            topics_covered=["algebra"],
        )

        # Create new monitor with same storage
        new_monitor = ActivityMonitor(user_id="test_user_001", storage_path=Path(self.temp_dir))

        self.assertEqual(len(new_monitor.sessions), 1)


class TestDeviceManager(unittest.TestCase):
    """Test cases for DeviceManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = DeviceManager(parent_id="parent_001", storage_path=Path(self.temp_dir))

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_register_device(self):
        """Test device registration."""
        device = self.manager.register_device(
            device_id="device_001",
            device_name="Child's iPad",
            user_id="test_user_001",
            platform="iOS",
            app_version="1.0.0",
        )

        self.assertEqual(device.device_id, "device_001")
        self.assertIn("device_001", self.manager.devices)

    def test_unregister_device(self):
        """Test device unregistration."""
        self.manager.register_device(
            device_id="device_001",
            device_name="Test Device",
            user_id="test_user_001",
            platform="iOS",
            app_version="1.0.0",
        )

        result = self.manager.unregister_device("device_001")
        self.assertTrue(result)
        self.assertNotIn("device_001", self.manager.devices)

    def test_lock_device(self):
        """Test remote lock command."""
        self.manager.register_device(
            device_id="device_001",
            device_name="Test Device",
            user_id="test_user_001",
            platform="iOS",
            app_version="1.0.0",
        )

        command_id = self.manager.lock_device("device_001", "Time limit reached")
        self.assertIsNotNone(command_id)
        self.assertIn(command_id, self.manager.pending_commands)

    def test_unlock_device(self):
        """Test remote unlock command."""
        self.manager.register_device(
            device_id="device_001",
            device_name="Test Device",
            user_id="test_user_001",
            platform="iOS",
            app_version="1.0.0",
        )

        command_id = self.manager.unlock_device("device_001")
        self.assertIsNotNone(command_id)

    def test_update_settings(self):
        """Test pushing settings update."""
        self.manager.register_device(
            device_id="device_001",
            device_name="Test Device",
            user_id="test_user_001",
            platform="iOS",
            app_version="1.0.0",
        )

        settings = {"daily_limit": 60, "content_filter": "strict"}

        command_id = self.manager.update_settings("device_001", settings)
        self.assertIsNotNone(command_id)

        command = self.manager.pending_commands[command_id]
        self.assertEqual(command.command_type, CommandType.UPDATE_SETTINGS)
        self.assertEqual(command.payload["settings"], settings)

    def test_get_device_status(self):
        """Test getting device status."""
        self.manager.register_device(
            device_id="device_001",
            device_name="Test Device",
            user_id="test_user_001",
            platform="iOS",
            app_version="1.0.0",
        )

        status = self.manager.get_device_status("device_001")
        self.assertEqual(status["device_id"], "device_001")
        self.assertIn("battery_level", status)

    def test_device_heartbeat(self):
        """Test device heartbeat updates."""
        self.manager.register_device(
            device_id="device_001",
            device_name="Test Device",
            user_id="test_user_001",
            platform="iOS",
            app_version="1.0.0",
        )

        self.manager.update_device_heartbeat(
            device_id="device_001", battery_level=75, is_charging=True, connection_type="wifi"
        )

        device = self.manager.devices["device_001"]
        self.assertEqual(device.battery_level, 75)
        self.assertTrue(device.is_charging)
        self.assertEqual(device.connection_type, "wifi")

    def test_command_result_reporting(self):
        """Test reporting command execution results."""
        self.manager.register_device(
            device_id="device_001",
            device_name="Test Device",
            user_id="test_user_001",
            platform="iOS",
            app_version="1.0.0",
        )

        command_id = self.manager.lock_device("device_001")

        self.manager.report_command_result(
            command_id=command_id, success=True, result={"locked": True}
        )

        # Should be moved to history
        self.assertNotIn(command_id, self.manager.pending_commands)
        self.assertTrue(any(c.command_id == command_id for c in self.manager.command_history))

    def test_state_persistence(self):
        """Test that device state persists."""
        self.manager.register_device(
            device_id="device_001",
            device_name="Test Device",
            user_id="test_user_001",
            platform="iOS",
            app_version="1.0.0",
        )

        # Create new manager with same storage
        new_manager = DeviceManager(parent_id="parent_001", storage_path=Path(self.temp_dir))

        self.assertIn("device_001", new_manager.devices)


class TestNotificationService(unittest.TestCase):
    """Test cases for NotificationService."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.service = NotificationService(parent_id="parent_001", storage_path=Path(self.temp_dir))

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_send_daily_summary(self):
        """Test sending daily summary."""
        summary_data = {
            "date": "2024-01-15",
            "total_duration_minutes": 60,
            "total_sessions": 3,
            "overall_accuracy": 85.5,
            "subjects": {"mathematics": {}, "science": {}},
        }

        notification_id = self.service.send_daily_summary(
            user_id="test_user_001", summary_data=summary_data, force=True
        )

        self.assertIsNotNone(notification_id)
        self.assertEqual(len(self.service.notification_history), 1)

    def test_send_milestone_alert(self):
        """Test sending milestone notification."""
        milestone_data = {"description": "Completed 7-day practice streak!", "streak_days": 7}

        notification_id = self.service.send_milestone_alert(
            user_id="test_user_001",
            milestone_type="Practice Streak",
            milestone_data=milestone_data,
            force=True,
        )

        self.assertIsNotNone(notification_id)

    def test_send_concern_alert(self):
        """Test sending concern notification."""
        concern_data = {
            "description": "Accuracy dropping in mathematics",
            "accuracy": 45.0,
            "subject": "mathematics",
        }

        notification_id = self.service.send_concern_alert(
            user_id="test_user_001",
            concern_type="Low Accuracy",
            concern_data=concern_data,
            force=True,
        )

        self.assertIsNotNone(notification_id)
        notification = self.service.notification_history[-1]
        self.assertEqual(notification.priority, NotificationPriority.HIGH)

    def test_notification_throttling(self):
        """Test that notifications are throttled."""
        # Configure short throttle
        self.service.preferences.notification_throttle = 5

        summary_data = {"date": "2024-01-15"}

        # First notification should send
        id1 = self.service.send_daily_summary("test_user_001", summary_data, force=False)
        self.assertIsNotNone(id1)

        # Second immediate notification should be throttled
        id2 = self.service.send_daily_summary("test_user_001", summary_data, force=False)
        self.assertIsNone(id2)

    def test_quiet_hours(self):
        """Test quiet hours functionality."""
        # Set quiet hours to current time
        now = datetime.now()
        self.service.preferences.quiet_hours_enabled = True
        self.service.preferences.quiet_hours_start = now.time()
        self.service.preferences.quiet_hours_end = (now + timedelta(hours=1)).time()

        # Try to send non-urgent notification
        summary_data = {"date": "2024-01-15"}
        notification_id = self.service.send_daily_summary(
            "test_user_001", summary_data, force=False
        )

        # Should be blocked by quiet hours
        self.assertIsNone(notification_id)

    def test_configure_preferences(self):
        """Test configuring notification preferences."""
        self.service.configure_preferences(email="parent@example.com", quiet_hours_enabled=False)

        self.assertEqual(self.service.preferences.email_address, "parent@example.com")
        self.assertFalse(self.service.preferences.quiet_hours_enabled)

    def test_channel_preferences(self):
        """Test setting channel preferences."""
        self.service.set_channel_preferences(
            NotificationType.DAILY_SUMMARY, {NotificationChannel.EMAIL, NotificationChannel.PUSH}
        )

        channels = self.service.preferences.channel_preferences[NotificationType.DAILY_SUMMARY]
        self.assertIn(NotificationChannel.EMAIL, channels)
        self.assertIn(NotificationChannel.PUSH, channels)

    def test_notification_history(self):
        """Test retrieving notification history."""
        # Send several notifications
        for i in range(5):
            self.service.send_daily_summary(
                "test_user_001", {"date": f"2024-01-{i+1:02d}"}, force=True
            )

        history = self.service.get_notification_history(limit=3)
        self.assertEqual(len(history), 3)

    def test_state_persistence(self):
        """Test that notification state persists."""
        self.service.configure_preferences(email="parent@example.com")
        self.service.send_daily_summary("test_user_001", {"date": "2024-01-15"}, force=True)

        # Create new service with same storage
        new_service = NotificationService(parent_id="parent_001", storage_path=Path(self.temp_dir))

        self.assertEqual(new_service.preferences.email_address, "parent@example.com")
        self.assertEqual(len(new_service.notification_history), 1)


class TestIntegration(unittest.TestCase):
    """Integration tests for parental controls system."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.user_id = "test_user_001"
        self.parent_id = "parent_001"

        # Initialize all components
        self.usage_controller = UsageController(
            user_id=self.user_id, storage_path=Path(self.temp_dir) / "usage"
        )
        self.content_filter = ContentFilter(
            user_id=self.user_id, storage_path=Path(self.temp_dir) / "filters"
        )
        self.activity_monitor = ActivityMonitor(
            user_id=self.user_id, storage_path=Path(self.temp_dir) / "activity"
        )
        self.device_manager = DeviceManager(
            parent_id=self.parent_id, storage_path=Path(self.temp_dir) / "devices"
        )
        self.notification_service = NotificationService(
            parent_id=self.parent_id, storage_path=Path(self.temp_dir) / "notifications"
        )

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_complete_workflow(self):
        """Test a complete parental control workflow."""
        # 1. Setup parental controls
        self.usage_controller.set_daily_limit(DayOfWeek.MONDAY, 120)
        self.content_filter.set_age_appropriate_defaults(AgeGroup.AGES_11_13)

        # 2. Register device
        device = self.device_manager.register_device(
            device_id="device_001",
            device_name="Child's Tablet",
            user_id=self.user_id,
            platform="iOS",
            app_version="1.0.0",
        )

        # 3. Simulate learning session
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=30)

        self.activity_monitor.log_session(
            session_id="session_001",
            start_time=start_time,
            end_time=end_time,
            subject="mathematics",
            problems_attempted=20,
            problems_correct=18,
            difficulty_level="middle_school",
            topics_covered=["algebra", "equations"],
        )

        # 4. Check content filter
        allowed, reason = self.content_filter.check_content(
            subject="mathematics", difficulty=DifficultyLevel.MIDDLE_SCHOOL
        )
        self.assertTrue(allowed)

        # 5. Generate and send daily summary
        daily_report = self.activity_monitor.get_daily_report()
        notification_id = self.notification_service.send_daily_summary(
            user_id=self.user_id, summary_data=daily_report, force=True
        )
        self.assertIsNotNone(notification_id)

        # 6. Verify everything is working together
        self.assertEqual(len(self.activity_monitor.sessions), 1)
        self.assertEqual(len(self.notification_service.notification_history), 1)
        self.assertIn(device.device_id, self.device_manager.devices)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestUsageController))
    suite.addTests(loader.loadTestsFromTestCase(TestContentFilter))
    suite.addTests(loader.loadTestsFromTestCase(TestActivityMonitor))
    suite.addTests(loader.loadTestsFromTestCase(TestDeviceManager))
    suite.addTests(loader.loadTestsFromTestCase(TestNotificationService))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
