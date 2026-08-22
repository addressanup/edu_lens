#!/usr/bin/env python3
"""
Example usage of EduLens Parental Controls

Demonstrates how to use all parental control components together.
"""

import sys
from datetime import datetime, time, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parental.activity_monitor import ActivityMonitor
from parental.content_filter import (
    AgeGroup,
    ContentFilter,
    ContentType,
    DifficultyLevel,
    FilterMode,
)
from parental.device_manager import DeviceManager
from parental.notification_service import NotificationChannel, NotificationService, NotificationType
from parental.usage_controller import DayOfWeek, LimitStatus, UsageController


def example_usage_controller():
    """Demonstrate usage controller features."""
    print("\n" + "=" * 60)
    print("USAGE CONTROLLER EXAMPLE")
    print("=" * 60)

    controller = UsageController(user_id="child_demo")

    # Set daily limits for weekdays
    print("\n1. Setting up daily limits...")
    for day in [
        DayOfWeek.MONDAY,
        DayOfWeek.TUESDAY,
        DayOfWeek.WEDNESDAY,
        DayOfWeek.THURSDAY,
        DayOfWeek.FRIDAY,
    ]:
        controller.set_daily_limit(day, 90)  # 90 minutes on weekdays

    for day in [DayOfWeek.SATURDAY, DayOfWeek.SUNDAY]:
        controller.set_daily_limit(day, 120)  # 120 minutes on weekends

    print("   ✓ Weekdays: 90 minutes")
    print("   ✓ Weekends: 120 minutes")

    # Set allowed schedules
    print("\n2. Setting up schedules...")
    weekday_schedule = [(time(15, 0), time(20, 0))]  # 3 PM - 8 PM
    weekend_schedule = [(time(9, 0), time(12, 0)), (time(14, 0), time(19, 0))]

    for day in [
        DayOfWeek.MONDAY,
        DayOfWeek.TUESDAY,
        DayOfWeek.WEDNESDAY,
        DayOfWeek.THURSDAY,
        DayOfWeek.FRIDAY,
    ]:
        controller.set_schedule(day, weekday_schedule)

    for day in [DayOfWeek.SATURDAY, DayOfWeek.SUNDAY]:
        controller.set_schedule(day, weekend_schedule)

    print("   ✓ Weekday schedule: 3:00 PM - 8:00 PM")
    print("   ✓ Weekend schedule: 9:00 AM - 12:00 PM, 2:00 PM - 7:00 PM")

    # Set grace period
    controller.set_grace_period(5)
    print("\n3. Grace period: 5 minutes")

    # Check current status
    print("\n4. Checking current status...")
    status, message = controller.check_allowed()
    print(f"   Status: {status.value}")
    print(f"   Message: {message}")

    # Get status summary
    summary = controller.get_status_summary()
    print("\n5. Status Summary:")
    for key, value in summary.items():
        print(f"   {key}: {value}")


def example_content_filter():
    """Demonstrate content filter features."""
    print("\n" + "=" * 60)
    print("CONTENT FILTER EXAMPLE")
    print("=" * 60)

    filter = ContentFilter(user_id="child_demo")

    # Set age-appropriate defaults
    print("\n1. Setting age-appropriate defaults for ages 11-13...")
    filter.set_age_appropriate_defaults(AgeGroup.AGES_11_13)
    print("   ✓ Difficulty limited to high school level")
    print("   ✓ All content types allowed")

    # Add subject whitelist
    print("\n2. Setting up subject whitelist...")
    filter.filter_subjects(
        FilterMode.WHITELIST, ["mathematics", "science", "history", "language_arts"]
    )
    print("   ✓ Allowed subjects: math, science, history, language arts")

    # Test content filtering
    print("\n3. Testing content filter...")

    test_cases = [
        ("mathematics", DifficultyLevel.MIDDLE_SCHOOL, ContentType.MATH_PROBLEM),
        ("video_games", DifficultyLevel.MIDDLE_SCHOOL, ContentType.INTERACTIVE),
        ("mathematics", DifficultyLevel.COLLEGE, ContentType.MATH_PROBLEM),
    ]

    for subject, difficulty, content_type in test_cases:
        allowed, reason = filter.check_content(
            subject=subject, difficulty=difficulty, content_type=content_type
        )
        status = "✓ ALLOWED" if allowed else "✗ BLOCKED"
        print(f"   {status}: {subject} ({difficulty.name}, {content_type.value})")
        if not allowed:
            print(f"            Reason: {reason}")

    # Get filter summary
    print("\n4. Filter Summary:")
    summary = filter.get_filter_summary()
    for key, value in summary.items():
        if key != "user_id":
            print(f"   {key}: {value}")


def example_activity_monitor():
    """Demonstrate activity monitor features."""
    print("\n" + "=" * 60)
    print("ACTIVITY MONITOR EXAMPLE")
    print("=" * 60)

    monitor = ActivityMonitor(user_id="child_demo")

    # Log some sample sessions
    print("\n1. Logging sample sessions...")

    sessions = [
        {
            "session_id": "session_001",
            "subject": "mathematics",
            "duration": 30,
            "attempted": 20,
            "correct": 18,
            "difficulty": "middle_school",
            "topics": ["algebra", "equations"],
        },
        {
            "session_id": "session_002",
            "subject": "science",
            "duration": 25,
            "attempted": 15,
            "correct": 13,
            "difficulty": "middle_school",
            "topics": ["biology", "cells"],
        },
        {
            "session_id": "session_003",
            "subject": "mathematics",
            "duration": 35,
            "attempted": 25,
            "correct": 22,
            "difficulty": "middle_school",
            "topics": ["geometry", "triangles"],
        },
    ]

    for session in sessions:
        start = datetime.now() - timedelta(minutes=session["duration"])
        end = datetime.now()

        monitor.log_session(
            session_id=session["session_id"],
            start_time=start,
            end_time=end,
            subject=session["subject"],
            problems_attempted=session["attempted"],
            problems_correct=session["correct"],
            difficulty_level=session["difficulty"],
            topics_covered=session["topics"],
        )
        print(
            f"   ✓ Logged {session['subject']} session: {session['duration']} min, "
            f"{session['correct']}/{session['attempted']} correct"
        )

    # Get daily report
    print("\n2. Daily Report:")
    report = monitor.get_daily_report()
    print(f"   Total Sessions: {report['total_sessions']}")
    print(f"   Total Duration: {report['total_duration_minutes']} minutes")
    print(f"   Overall Accuracy: {report['overall_accuracy']}%")
    print(f"   Problems Attempted: {report['problems_attempted']}")
    print(f"   Problems Correct: {report['problems_correct']}")

    # Get subject breakdown
    print("\n3. Subject Breakdown:")
    breakdown = monitor.get_subject_breakdown()
    for subject, stats in breakdown.items():
        print(f"   {subject.title()}:")
        print(f"      Duration: {stats['total_duration']} min")
        print(f"      Accuracy: {stats['accuracy']}%")
        print(f"      Sessions: {stats['session_count']}")

    # Get learning insights
    print("\n4. Learning Insights:")
    insights = monitor.get_learning_insights()

    if insights.get("strengths"):
        print("   Strengths:")
        for strength in insights["strengths"]:
            print(f"      ✓ {strength}")

    if insights.get("recommendations"):
        print("   Recommendations:")
        for rec in insights["recommendations"]:
            print(f"      → {rec}")


def example_device_manager():
    """Demonstrate device manager features."""
    print("\n" + "=" * 60)
    print("DEVICE MANAGER EXAMPLE")
    print("=" * 60)

    manager = DeviceManager(parent_id="parent_demo")

    # Register devices
    print("\n1. Registering devices...")

    devices = [
        {
            "device_id": "ipad_001",
            "device_name": "Child's iPad",
            "user_id": "child_demo",
            "platform": "iOS",
            "app_version": "1.0.0",
        },
        {
            "device_id": "tablet_001",
            "device_name": "Child's Tablet",
            "user_id": "child_demo",
            "platform": "Android",
            "app_version": "1.0.0",
        },
    ]

    for device in devices:
        manager.register_device(**device)
        print(f"   ✓ Registered: {device['device_name']} ({device['platform']})")

    # Update device heartbeats
    print("\n2. Updating device status...")
    for device in devices:
        manager.update_device_heartbeat(
            device_id=device["device_id"],
            battery_level=75,
            is_charging=False,
            connection_type="wifi",
        )
    print("   ✓ Heartbeats updated")

    # Send commands
    print("\n3. Sending remote commands...")

    # Update settings
    cmd_id = manager.update_settings("ipad_001", {"daily_limit": 90, "content_filter": "moderate"})
    print(f"   ✓ Settings update sent to iPad (command: {cmd_id[:8]}...)")

    # Lock device (example)
    cmd_id = manager.lock_device("tablet_001", "Time limit reached")
    print(f"   ✓ Lock command sent to Tablet (command: {cmd_id[:8]}...)")

    # Get device status
    print("\n4. Device Status:")
    for device in devices:
        status = manager.get_device_status(device["device_id"])
        print(f"   {status['device_name']}:")
        print(f"      Status: {status['status']}")
        print(f"      Battery: {status['battery_level']}%")
        print(f"      Connection: {status['connection_type']}")
        print(f"      Pending Commands: {status['pending_commands']}")


def example_notification_service():
    """Demonstrate notification service features."""
    print("\n" + "=" * 60)
    print("NOTIFICATION SERVICE EXAMPLE")
    print("=" * 60)

    service = NotificationService(parent_id="parent_demo")

    # Configure preferences
    print("\n1. Configuring notification preferences...")
    service.configure_preferences(
        email="parent@example.com",
        quiet_hours_enabled=True,
        quiet_hours_start=time(22, 0),
        quiet_hours_end=time(7, 0),
        daily_summary_time=time(20, 0),
    )
    print("   ✓ Email: parent@example.com")
    print("   ✓ Quiet hours: 10:00 PM - 7:00 AM")
    print("   ✓ Daily summary: 8:00 PM")

    # Set channel preferences
    print("\n2. Setting notification channels...")
    service.set_channel_preferences(NotificationType.DAILY_SUMMARY, {NotificationChannel.EMAIL})
    service.set_channel_preferences(
        NotificationType.MILESTONE, {NotificationChannel.PUSH, NotificationChannel.IN_APP}
    )
    print("   ✓ Daily summaries via email")
    print("   ✓ Milestones via push and in-app")

    # Send sample notifications
    print("\n3. Sending sample notifications...")

    # Daily summary
    summary_data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "total_duration_minutes": 90,
        "total_sessions": 3,
        "overall_accuracy": 87.5,
        "subjects": {"mathematics": {}, "science": {}},
    }

    notif_id = service.send_daily_summary(
        user_id="child_demo", summary_data=summary_data, force=True
    )
    print(f"   ✓ Daily summary sent (ID: {notif_id[:10]}...)")

    # Milestone alert
    milestone_data = {"description": "Completed 7-day practice streak!", "streak_days": 7}

    notif_id = service.send_milestone_alert(
        user_id="child_demo",
        milestone_type="Practice Streak",
        milestone_data=milestone_data,
        force=True,
    )
    print(f"   ✓ Milestone alert sent (ID: {notif_id[:10]}...)")

    # Get notification history
    print("\n4. Notification History:")
    history = service.get_notification_history(limit=5)
    for notif in history:
        print(f"   [{notif['notification_type']}] {notif['title']}")
        print(f"      Sent: {notif['sent_at']}")
        print(f"      Channels: {', '.join(notif['channels_used'])}")


def integrated_example():
    """Demonstrate integrated usage of all components."""
    print("\n" + "=" * 60)
    print("INTEGRATED EXAMPLE")
    print("=" * 60)

    print("\nSimulating a complete parental control workflow...")

    # Initialize all components
    user_id = "child_integrated"
    parent_id = "parent_integrated"

    usage = UsageController(user_id=user_id)
    filter = ContentFilter(user_id=user_id)
    monitor = ActivityMonitor(user_id=user_id)
    devices = DeviceManager(parent_id=parent_id)
    notifications = NotificationService(parent_id=parent_id)

    print("\n1. Parent sets up controls for 11-year-old child...")

    # Setup usage limits
    usage.set_daily_limit(DayOfWeek.MONDAY, 90)
    usage.set_schedule(DayOfWeek.MONDAY, [(time(15, 0), time(20, 0))])

    # Setup content filters
    filter.set_age_appropriate_defaults(AgeGroup.AGES_11_13)

    # Register device
    devices.register_device(
        device_id="device_integrated",
        device_name="Child's Device",
        user_id=user_id,
        platform="iOS",
        app_version="1.0.0",
    )

    # Configure notifications
    notifications.configure_preferences(email="parent@example.com")

    print("   ✓ All controls configured")

    print("\n2. Child starts learning session at 4:00 PM...")

    # Check if allowed
    check_time = datetime.now().replace(hour=16, minute=0)
    status, message = usage.check_allowed(check_time)

    if status == LimitStatus.ALLOWED:
        print(f"   ✓ Session allowed: {message}")

        # Check content
        allowed, reason = filter.check_content(
            subject="mathematics", difficulty=DifficultyLevel.MIDDLE_SCHOOL
        )

        if allowed:
            print("   ✓ Content allowed")

            # Start session
            success, msg = usage.start_session(check_time)
            print(f"   ✓ Session started")

    print("\n3. Child completes learning session...")

    # End session
    end_time = check_time + timedelta(minutes=35)
    minutes = usage.end_session(end_time)

    # Log activity
    monitor.log_session(
        session_id="integrated_session",
        start_time=check_time,
        end_time=end_time,
        subject="mathematics",
        problems_attempted=25,
        problems_correct=22,
        difficulty_level="middle_school",
        topics_covered=["algebra", "equations"],
    )

    print(f"   ✓ Session completed: {minutes} minutes")
    print(f"   ✓ Activity logged: 22/25 correct (88% accuracy)")

    print("\n4. Parent receives daily summary...")

    # Generate and send report
    report = monitor.get_daily_report()
    notif_id = notifications.send_daily_summary(user_id=user_id, summary_data=report, force=True)

    print(f"   ✓ Summary sent to parent@example.com")
    print(f"      Duration: {report['total_duration_minutes']} minutes")
    print(f"      Accuracy: {report['overall_accuracy']}%")

    print("\n5. Checking remaining time for today...")
    remaining = usage.get_remaining_time()
    if remaining is not None:
        print(f"   ✓ Remaining time: {remaining} minutes")
    else:
        print("   ✓ Unlimited time remaining")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("EDULENS PARENTAL CONTROLS - DEMONSTRATION")
    print("=" * 60)
    print("\nThis demonstration shows all features of the parental controls system.")

    try:
        example_usage_controller()
        example_content_filter()
        example_activity_monitor()
        example_device_manager()
        example_notification_service()
        integrated_example()

        print("\n" + "=" * 60)
        print("DEMONSTRATION COMPLETE")
        print("=" * 60)
        print("\nAll parental control features demonstrated successfully!")
        print("See README.md for detailed documentation.")
        print("\n")

    except Exception as e:
        print(f"\n\nError during demonstration: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
