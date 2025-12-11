# EduLens Parental Controls

Comprehensive parental control system for the EduLens educational platform.

## Overview

The EduLens Parental Controls module provides parents with tools to manage their children's learning experience while respecting privacy and promoting healthy educational habits.

## Components

### 1. UsageController (`usage_controller.py`)
Manages time-based restrictions and usage monitoring.

**Features:**
- Daily time limits (configurable per day of week)
- Usage schedules (allowed time ranges)
- Grace period warnings before lockout
- Session tracking
- Automatic enforcement

**Example:**
```python
from parental.usage_controller import UsageController, DayOfWeek
from datetime import time

controller = UsageController(user_id="child_001")

# Set 90-minute daily limit for weekdays
controller.set_daily_limit(DayOfWeek.MONDAY, 90)

# Set allowed hours (3 PM - 7 PM)
controller.set_schedule(
    DayOfWeek.MONDAY,
    [(time(15, 0), time(19, 0))]
)

# Check if usage is allowed
status, message = controller.check_allowed()
print(f"Status: {status.value}")
```

### 2. ContentFilter (`content_filter.py`)
Filters educational content based on various criteria.

**Features:**
- Subject filtering (whitelist/blacklist)
- Difficulty level restrictions
- Content type filtering
- Keyword blocking
- Age-appropriate defaults

**Example:**
```python
from parental.content_filter import ContentFilter, AgeGroup, DifficultyLevel

filter = ContentFilter(user_id="child_001")

# Set age-appropriate defaults
filter.set_age_appropriate_defaults(AgeGroup.AGES_11_13)

# Check if content is allowed
allowed, reason = filter.check_content(
    subject="mathematics",
    difficulty=DifficultyLevel.MIDDLE_SCHOOL
)
```

### 3. ActivityMonitor (`activity_monitor.py`)
Privacy-respecting activity monitoring and reporting.

**Features:**
- Session logging (aggregated statistics only)
- Daily and weekly reports
- Subject breakdown analysis
- Progress metrics and trends
- Learning insights

**Example:**
```python
from parental.activity_monitor import ActivityMonitor
from datetime import datetime, timedelta

monitor = ActivityMonitor(user_id="child_001")

# Log a session
monitor.log_session(
    session_id="session_001",
    start_time=datetime.now() - timedelta(minutes=30),
    end_time=datetime.now(),
    subject="mathematics",
    problems_attempted=20,
    problems_correct=18,
    difficulty_level="middle_school",
    topics_covered=["algebra", "equations"]
)

# Get daily report
report = monitor.get_daily_report()
print(f"Total time: {report['total_duration_minutes']} minutes")
print(f"Accuracy: {report['overall_accuracy']}%")
```

### 4. DeviceManager (`device_manager.py`)
Remote device management and control.

**Features:**
- Device registration and tracking
- Remote lock/unlock
- Settings updates
- Device status monitoring
- Offline command queuing

**Example:**
```python
from parental.device_manager import DeviceManager

manager = DeviceManager(parent_id="parent_001")

# Register a device
device = manager.register_device(
    device_id="tablet_001",
    device_name="Child's iPad",
    user_id="child_001",
    platform="iOS",
    app_version="1.0.0"
)

# Lock device remotely
command_id = manager.lock_device(
    device_id="tablet_001",
    reason="Bedtime"
)

# Check device status
status = manager.get_device_status("tablet_001")
print(f"Battery: {status['battery_level']}%")
```

### 5. NotificationService (`notification_service.py`)
Parent notification system.

**Features:**
- Daily and weekly summaries
- Milestone notifications
- Concern alerts
- Configurable preferences
- Quiet hours
- Multiple delivery channels

**Example:**
```python
from parental.notification_service import NotificationService

service = NotificationService(parent_id="parent_001")

# Configure preferences
service.configure_preferences(
    email="parent@example.com",
    quiet_hours_start=time(22, 0),
    quiet_hours_end=time(7, 0)
)

# Send daily summary
service.send_daily_summary(
    user_id="child_001",
    summary_data=daily_report
)

# Send milestone alert
service.send_milestone_alert(
    user_id="child_001",
    milestone_type="Practice Streak",
    milestone_data={'streak_days': 7}
)
```

## Configuration

Default settings are provided in `/configs/parental/default_controls.yaml`.

### Age-Based Presets

The system includes age-appropriate presets:
- **Ages 5-7**: Elementary school, 30 min/day, restricted content
- **Ages 8-10**: Upper elementary, 60 min/day, moderate restrictions
- **Ages 11-13**: Middle school, 90 min/day, minimal restrictions
- **Ages 14-16**: High school, 120 min/day, light restrictions
- **Ages 17+**: Minimal restrictions, weekly summaries only

## Privacy Features

The parental controls system is designed with privacy in mind:

1. **No Raw Content Storage**: Only aggregated statistics are stored
2. **No Answer Recording**: Individual answers are not saved
3. **Summary Statistics Only**: Reports contain only high-level metrics
4. **Secure Communication**: Commands are encrypted (in production)
5. **Data Retention**: Configurable retention periods with automatic cleanup

## Testing

Run the comprehensive test suite:

```bash
cd /Users/anuppandey/Desktop/edu_lens
python -m pytest tests/parental/test_parental_controls.py -v
```

Or run directly:

```bash
python tests/parental/test_parental_controls.py
```

## Integration Example

Complete workflow integrating all components:

```python
from parental import (
    UsageController, ContentFilter, ActivityMonitor,
    DeviceManager, NotificationService
)

# Initialize components
usage = UsageController(user_id="child_001")
filter = ContentFilter(user_id="child_001")
monitor = ActivityMonitor(user_id="child_001")
devices = DeviceManager(parent_id="parent_001")
notifications = NotificationService(parent_id="parent_001")

# Setup controls
usage.set_daily_limit(DayOfWeek.MONDAY, 90)
filter.set_age_appropriate_defaults(AgeGroup.AGES_11_13)

# Register device
devices.register_device(
    device_id="device_001",
    device_name="Child's Device",
    user_id="child_001",
    platform="iOS",
    app_version="1.0.0"
)

# During learning session
status, message = usage.check_allowed()
if status == LimitStatus.ALLOWED:
    allowed, reason = filter.check_content(
        subject="mathematics",
        difficulty=DifficultyLevel.MIDDLE_SCHOOL
    )
    if allowed:
        # Allow learning session
        pass

# After session
monitor.log_session(...)

# Daily summary
report = monitor.get_daily_report()
notifications.send_daily_summary(
    user_id="child_001",
    summary_data=report
)
```

## Architecture

```
parental/
├── __init__.py                  # Package initialization
├── usage_controller.py          # Time limits and schedules
├── content_filter.py            # Content filtering
├── activity_monitor.py          # Activity tracking
├── device_manager.py            # Device management
├── notification_service.py      # Parent notifications
└── README.md                    # This file

configs/parental/
└── default_controls.yaml        # Default configuration

tests/parental/
└── test_parental_controls.py    # Comprehensive test suite
```

## Security Considerations

1. **Authentication**: Requires parent PIN for settings changes (in production)
2. **Encryption**: Commands and sensitive data encrypted in transit
3. **Access Control**: Role-based access to parental features
4. **Audit Logging**: All configuration changes are logged
5. **Data Protection**: Compliant with COPPA and GDPR requirements

## Performance

- **Low Overhead**: Minimal impact on device performance
- **Efficient Storage**: Aggregated statistics use minimal space
- **Offline Support**: Commands queued for offline devices
- **Scalable**: Designed to handle multiple devices per parent

## Future Enhancements

- [ ] Machine learning-based concern detection
- [ ] Collaborative learning recommendations
- [ ] Integration with school systems
- [ ] Advanced analytics dashboard
- [ ] Multi-parent support
- [ ] Sibling management features

## Support

For issues or questions, please refer to the main EduLens documentation or contact support.

## License

Part of the EduLens project. All rights reserved.
