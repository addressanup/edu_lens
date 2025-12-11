# Quick Start: EduLens Parental Controls

## Installation & Setup

### Import the Module
```python
from parental.usage_controller import UsageController, DayOfWeek
from parental.content_filter import ContentFilter, AgeGroup
from parental.activity_monitor import ActivityMonitor
from parental.device_manager import DeviceManager
from parental.notification_service import NotificationService
```

## 5-Minute Setup Guide

### 1. Set Up Usage Limits (30 seconds)
```python
controller = UsageController(user_id="child_001")

# Set daily limit: 90 minutes on weekdays
controller.set_daily_limit(DayOfWeek.MONDAY, 90)

# Set allowed hours: 3 PM - 8 PM
from datetime import time
controller.set_schedule(DayOfWeek.MONDAY, [(time(15, 0), time(20, 0))])

# Check if usage is allowed
status, message = controller.check_allowed()
```

### 2. Configure Content Filters (30 seconds)
```python
filter = ContentFilter(user_id="child_001")

# Use age-appropriate defaults
filter.set_age_appropriate_defaults(AgeGroup.AGES_11_13)

# Or customize
filter.filter_subjects(FilterMode.WHITELIST, ["mathematics", "science"])

# Check content
allowed, reason = filter.check_content(subject="mathematics")
```

### 3. Monitor Activity (1 minute)
```python
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
print(f"Time: {report['total_duration_minutes']} min")
print(f"Accuracy: {report['overall_accuracy']}%")
```

### 4. Manage Devices (1 minute)
```python
manager = DeviceManager(parent_id="parent_001")

# Register device
manager.register_device(
    device_id="ipad_001",
    device_name="Child's iPad",
    user_id="child_001",
    platform="iOS",
    app_version="1.0.0"
)

# Lock device remotely
manager.lock_device("ipad_001", reason="Bedtime")

# Get status
status = manager.get_device_status("ipad_001")
```

### 5. Setup Notifications (1 minute)
```python
service = NotificationService(parent_id="parent_001")

# Configure
service.configure_preferences(
    email="parent@example.com",
    quiet_hours_start=time(22, 0),
    quiet_hours_end=time(7, 0)
)

# Send daily summary
service.send_daily_summary(
    user_id="child_001",
    summary_data=report
)
```

## Common Use Cases

### Use Case 1: School Night Restrictions
```python
# 60 minutes, only between 6-8 PM
controller = UsageController("child_001")
controller.set_daily_limit(DayOfWeek.MONDAY, 60)
controller.set_schedule(DayOfWeek.MONDAY, [(time(18, 0), time(20, 0))])
```

### Use Case 2: Age-Appropriate Content
```python
# 8-10 year old
filter = ContentFilter("child_001")
filter.set_age_appropriate_defaults(AgeGroup.AGES_8_10)
# Auto-sets: max difficulty = middle school, appropriate content types
```

### Use Case 3: Track Progress
```python
monitor = ActivityMonitor("child_001")

# After each session
monitor.log_session(...)

# Weekly review
weekly = monitor.get_weekly_report()
insights = monitor.get_learning_insights()
```

### Use Case 4: Multi-Device Family
```python
manager = DeviceManager("parent_001")

# Register all devices
devices = ["ipad_001", "tablet_001", "phone_001"]
for device_id in devices:
    manager.register_device(device_id, ...)

# Update all devices
for device_id in devices:
    manager.update_settings(device_id, new_settings)
```

## Testing Your Setup

### Run Example Script
```bash
cd /Users/anuppandey/Desktop/edu_lens
python3 examples/parental_controls_example.py
```

### Run Tests
```bash
python3 tests/parental/test_parental_controls.py
```

### Quick Verification
```python
from parental.usage_controller import UsageController, DayOfWeek
from parental.content_filter import ContentFilter, AgeGroup

# Should print success messages
controller = UsageController("test")
controller.set_daily_limit(DayOfWeek.MONDAY, 90)
print("✓ Usage controller working")

filter = ContentFilter("test")
filter.set_age_appropriate_defaults(AgeGroup.AGES_11_13)
print("✓ Content filter working")
```

## Configuration Files

### Load Default Settings
```python
import yaml
from pathlib import Path

config_path = Path("/Users/anuppandey/Desktop/edu_lens/configs/parental/default_controls.yaml")
with open(config_path) as f:
    config = yaml.safe_load(f)

# Apply age preset
age_preset = config['age_presets']['ages_11_13']
daily_limit = age_preset['usage']['daily_limit_minutes']
```

## Troubleshooting

### Issue: Imports not working
```bash
# Make sure you're in the right directory
cd /Users/anuppandey/Desktop/edu_lens

# Add to Python path
export PYTHONPATH=/Users/anuppandey/Desktop/edu_lens/src:$PYTHONPATH
```

### Issue: State not persisting
```python
# Explicitly set storage path
controller = UsageController(
    user_id="child_001",
    storage_path=Path("/path/to/storage")
)
```

### Issue: Need to reset everything
```python
# Clear usage data
controller.reset_daily_usage()

# Reset filters
filter.reset_all_filters()

# Clear old sessions
monitor.clear_old_sessions(days_to_keep=0)
```

## Best Practices

1. **Set Grace Periods**: Give 5-10 minute warnings
   ```python
   controller.set_grace_period(5)
   ```

2. **Use Age Defaults**: Start with age-appropriate presets
   ```python
   filter.set_age_appropriate_defaults(AgeGroup.AGES_11_13)
   ```

3. **Regular Reports**: Send weekly summaries
   ```python
   weekly = monitor.get_weekly_report()
   service.send_weekly_summary(user_id, weekly)
   ```

4. **Monitor Battery**: Check device status
   ```python
   status = manager.get_device_status(device_id)
   if status['battery_level'] < 20:
       # Send notification
   ```

5. **Respect Privacy**: Don't store raw content
   ```python
   # ActivityMonitor already does this by default
   # Only aggregated stats are stored
   ```

## Integration with Your App

### During App Startup
```python
# Initialize components
controller = UsageController(user_id)
filter = ContentFilter(user_id)

# Check if allowed
status, msg = controller.check_allowed()
if status != LimitStatus.ALLOWED:
    show_blocked_screen(msg)
```

### Before Showing Content
```python
allowed, reason = filter.check_content(
    subject=content.subject,
    difficulty=content.difficulty,
    content_type=content.type
)

if not allowed:
    show_content_blocked(reason)
```

### After Each Session
```python
# End usage tracking
minutes = controller.end_session()

# Log activity
monitor.log_session(
    session_id=generate_id(),
    start_time=session_start,
    end_time=datetime.now(),
    subject=subject,
    problems_attempted=total,
    problems_correct=correct,
    difficulty_level=difficulty,
    topics_covered=topics
)

# Check if limit reached
should_lock, reason = controller.enforce_limit()
if should_lock:
    lock_app(reason)
```

### End of Day
```python
# Generate report
report = monitor.get_daily_report()

# Send to parent
service.send_daily_summary(user_id, report)
```

## Production Deployment Checklist

- [ ] Replace JSON storage with encrypted database
- [ ] Add authentication layer
- [ ] Enable HTTPS for all communications
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy
- [ ] Test on actual devices
- [ ] Add rate limiting
- [ ] Security audit
- [ ] Performance testing
- [ ] User acceptance testing

## Support & Documentation

- Full documentation: `/src/parental/README.md`
- Example code: `/examples/parental_controls_example.py`
- Test suite: `/tests/parental/test_parental_controls.py`
- Configuration: `/configs/parental/default_controls.yaml`

## File Locations

All files are in: `/Users/anuppandey/Desktop/edu_lens/`

```
src/parental/           # Source code
configs/parental/       # Configuration
tests/parental/         # Tests
examples/               # Examples
```

---

**Quick Start Complete!** You now have a fully functional parental controls system.

For detailed information, see `PARENTAL_CONTROLS_SUMMARY.md` or `src/parental/README.md`.
