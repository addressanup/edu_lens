"""
Usage Controller for EduLens Parental Controls

Manages usage limits, schedules, and enforcement of time-based restrictions.
"""

import json
import logging
from datetime import datetime, time, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DayOfWeek(Enum):
    """Days of the week enumeration"""

    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class LimitStatus(Enum):
    """Status of usage limits"""

    ALLOWED = "allowed"
    LIMIT_REACHED = "limit_reached"
    OUTSIDE_SCHEDULE = "outside_schedule"
    GRACE_PERIOD = "grace_period"
    LOCKED = "locked"


class UsageController:
    """
    Manages usage limits and schedules for parental controls.

    Features:
    - Daily time limits (configurable per day)
    - Allowed usage schedules (time ranges)
    - Grace period warnings before lockout
    - Per-day-of-week configuration
    - Usage tracking and enforcement
    """

    def __init__(self, user_id: str, storage_path: Optional[Path] = None):
        """
        Initialize UsageController.

        Args:
            user_id: Unique identifier for the user
            storage_path: Path to store usage data
        """
        self.user_id = user_id
        self.storage_path = storage_path or Path(f"/tmp/edulens/usage/{user_id}")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Default settings
        self.daily_limits: Dict[DayOfWeek, int] = {}  # minutes per day
        self.schedules: Dict[DayOfWeek, List[Tuple[time, time]]] = {}  # allowed time ranges
        self.grace_period_minutes: int = 5
        self.is_locked: bool = False

        # Usage tracking
        self.usage_data: Dict[str, int] = {}  # date -> minutes used
        self.session_start: Optional[datetime] = None
        self.grace_period_notified: bool = False

        self._load_state()

    def set_daily_limit(self, day: DayOfWeek, minutes: int) -> None:
        """
        Set maximum usage time for a specific day.

        Args:
            day: Day of the week
            minutes: Maximum minutes allowed (0 = unlimited)

        Raises:
            ValueError: If minutes is negative
        """
        if minutes < 0:
            raise ValueError("Daily limit cannot be negative")

        self.daily_limits[day] = minutes
        logger.info(f"Set daily limit for {day.name} to {minutes} minutes for user {self.user_id}")
        self._save_state()

    def set_all_days_limit(self, minutes: int) -> None:
        """
        Set the same daily limit for all days of the week.

        Args:
            minutes: Maximum minutes allowed per day
        """
        for day in DayOfWeek:
            self.set_daily_limit(day, minutes)

    def set_schedule(self, day: DayOfWeek, time_ranges: List[Tuple[time, time]]) -> None:
        """
        Set allowed usage hours for a specific day.

        Args:
            day: Day of the week
            time_ranges: List of (start_time, end_time) tuples

        Raises:
            ValueError: If time ranges are invalid
        """
        # Validate time ranges
        for start, end in time_ranges:
            if not isinstance(start, time) or not isinstance(end, time):
                raise ValueError("Time ranges must be time objects")
            if start >= end:
                raise ValueError(f"Invalid time range: {start} to {end}")

        # Check for overlaps
        sorted_ranges = sorted(time_ranges, key=lambda x: x[0])
        for i in range(len(sorted_ranges) - 1):
            if sorted_ranges[i][1] > sorted_ranges[i + 1][0]:
                raise ValueError("Time ranges cannot overlap")

        self.schedules[day] = time_ranges
        logger.info(f"Set schedule for {day.name}: {time_ranges} for user {self.user_id}")
        self._save_state()

    def set_all_days_schedule(self, time_ranges: List[Tuple[time, time]]) -> None:
        """
        Set the same schedule for all days of the week.

        Args:
            time_ranges: List of (start_time, end_time) tuples
        """
        for day in DayOfWeek:
            self.set_schedule(day, time_ranges)

    def set_grace_period(self, minutes: int) -> None:
        """
        Set grace period duration before enforcing limits.

        Args:
            minutes: Grace period in minutes

        Raises:
            ValueError: If minutes is negative
        """
        if minutes < 0:
            raise ValueError("Grace period cannot be negative")

        self.grace_period_minutes = minutes
        logger.info(f"Set grace period to {minutes} minutes for user {self.user_id}")
        self._save_state()

    def check_allowed(
        self, current_time: Optional[datetime] = None
    ) -> Tuple[LimitStatus, Optional[str]]:
        """
        Check if usage is currently allowed.

        Args:
            current_time: Time to check (defaults to now)

        Returns:
            Tuple of (status, message)
        """
        if current_time is None:
            current_time = datetime.now()

        # Check if manually locked
        if self.is_locked:
            return LimitStatus.LOCKED, "Device is locked by parent"

        # Get current day
        day_of_week = DayOfWeek(current_time.weekday())
        current_time_only = current_time.time()

        # Check schedule
        if day_of_week in self.schedules:
            schedule = self.schedules[day_of_week]
            if not self._is_time_in_schedule(current_time_only, schedule):
                return LimitStatus.OUTSIDE_SCHEDULE, f"Outside allowed hours for {day_of_week.name}"

        # Check daily limit
        if day_of_week in self.daily_limits:
            limit = self.daily_limits[day_of_week]
            if limit > 0:  # 0 means unlimited
                used = self.get_usage_today(current_time)
                remaining = limit - used

                if remaining <= 0:
                    return LimitStatus.LIMIT_REACHED, f"Daily limit of {limit} minutes reached"
                elif remaining <= self.grace_period_minutes:
                    return (
                        LimitStatus.GRACE_PERIOD,
                        f"Only {remaining} minutes remaining (grace period)",
                    )

        return LimitStatus.ALLOWED, "Usage is allowed"

    def get_remaining_time(self, current_time: Optional[datetime] = None) -> Optional[int]:
        """
        Get remaining usage time for today in minutes.

        Args:
            current_time: Time to check (defaults to now)

        Returns:
            Remaining minutes, or None if unlimited
        """
        if current_time is None:
            current_time = datetime.now()

        day_of_week = DayOfWeek(current_time.weekday())

        if day_of_week not in self.daily_limits:
            return None  # No limit set

        limit = self.daily_limits[day_of_week]
        if limit == 0:
            return None  # Unlimited

        used = self.get_usage_today(current_time)
        remaining = max(0, limit - used)

        return remaining

    def get_usage_today(self, current_time: Optional[datetime] = None) -> int:
        """
        Get total usage for today in minutes.

        Args:
            current_time: Time to check (defaults to now)

        Returns:
            Minutes used today
        """
        if current_time is None:
            current_time = datetime.now()

        date_key = current_time.strftime("%Y-%m-%d")

        # Add current session time if active
        usage = self.usage_data.get(date_key, 0)
        if self.session_start:
            session_duration = (current_time - self.session_start).total_seconds() / 60
            usage += int(session_duration)

        return usage

    def start_session(self, current_time: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        Start a usage session.

        Args:
            current_time: Session start time (defaults to now)

        Returns:
            Tuple of (success, message)
        """
        if current_time is None:
            current_time = datetime.now()

        status, message = self.check_allowed(current_time)

        if status in [LimitStatus.ALLOWED, LimitStatus.GRACE_PERIOD]:
            self.session_start = current_time
            self.grace_period_notified = False
            logger.info(f"Session started for user {self.user_id} at {current_time}")
            return True, f"Session started: {message}"
        else:
            logger.warning(f"Session start denied for user {self.user_id}: {message}")
            return False, f"Session denied: {message}"

    def end_session(self, current_time: Optional[datetime] = None) -> int:
        """
        End the current usage session and record usage.

        Args:
            current_time: Session end time (defaults to now)

        Returns:
            Minutes used in this session
        """
        if current_time is None:
            current_time = datetime.now()

        if not self.session_start:
            logger.warning(f"No active session to end for user {self.user_id}")
            return 0

        # Calculate session duration
        session_duration = (current_time - self.session_start).total_seconds() / 60
        minutes_used = int(session_duration)

        # Record usage
        date_key = self.session_start.strftime("%Y-%m-%d")
        self.usage_data[date_key] = self.usage_data.get(date_key, 0) + minutes_used

        logger.info(f"Session ended for user {self.user_id}: {minutes_used} minutes")

        self.session_start = None
        self.grace_period_notified = False
        self._save_state()

        return minutes_used

    def enforce_limit(self, current_time: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        Check and enforce usage limits, locking device if necessary.

        Args:
            current_time: Time to check (defaults to now)

        Returns:
            Tuple of (should_lock, reason)
        """
        status, message = self.check_allowed(current_time)

        if status == LimitStatus.LIMIT_REACHED:
            self.lock_device()
            if self.session_start:
                self.end_session(current_time)
            return True, message
        elif status == LimitStatus.OUTSIDE_SCHEDULE:
            self.lock_device()
            if self.session_start:
                self.end_session(current_time)
            return True, message
        elif status == LimitStatus.LOCKED:
            return True, message
        elif status == LimitStatus.GRACE_PERIOD:
            if not self.grace_period_notified:
                self.grace_period_notified = True
                logger.info(f"Grace period started for user {self.user_id}: {message}")
            return False, message

        return False, "Usage allowed"

    def lock_device(self) -> None:
        """Manually lock the device."""
        self.is_locked = True
        logger.info(f"Device locked for user {self.user_id}")
        self._save_state()

    def unlock_device(self) -> None:
        """Manually unlock the device."""
        self.is_locked = False
        logger.info(f"Device unlocked for user {self.user_id}")
        self._save_state()

    def reset_daily_usage(self, date: Optional[datetime] = None) -> None:
        """
        Reset usage for a specific date (for testing/admin purposes).

        Args:
            date: Date to reset (defaults to today)
        """
        if date is None:
            date = datetime.now()

        date_key = date.strftime("%Y-%m-%d")
        if date_key in self.usage_data:
            del self.usage_data[date_key]
            logger.info(f"Reset usage for {date_key} for user {self.user_id}")
            self._save_state()

    def get_weekly_usage(self, current_time: Optional[datetime] = None) -> Dict[str, int]:
        """
        Get usage for the past 7 days.

        Args:
            current_time: Reference time (defaults to now)

        Returns:
            Dictionary mapping date strings to minutes used
        """
        if current_time is None:
            current_time = datetime.now()

        weekly_usage = {}
        for i in range(7):
            date = current_time - timedelta(days=i)
            date_key = date.strftime("%Y-%m-%d")
            weekly_usage[date_key] = self.usage_data.get(date_key, 0)

        return weekly_usage

    def _is_time_in_schedule(self, check_time: time, schedule: List[Tuple[time, time]]) -> bool:
        """Check if a time falls within any of the scheduled ranges."""
        for start, end in schedule:
            if start <= check_time <= end:
                return True
        return False

    def _save_state(self) -> None:
        """Save controller state to disk."""
        state = {
            "daily_limits": {day.value: limit for day, limit in self.daily_limits.items()},
            "schedules": {
                day.value: [(s.isoformat(), e.isoformat()) for s, e in ranges]
                for day, ranges in self.schedules.items()
            },
            "grace_period_minutes": self.grace_period_minutes,
            "is_locked": self.is_locked,
            "usage_data": self.usage_data,
            "session_start": self.session_start.isoformat() if self.session_start else None,
            "grace_period_notified": self.grace_period_notified,
        }

        state_file = self.storage_path / "usage_state.json"
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

    def _load_state(self) -> None:
        """Load controller state from disk."""
        state_file = self.storage_path / "usage_state.json"

        if not state_file.exists():
            return

        try:
            with open(state_file, "r") as f:
                state = json.load(f)

            self.daily_limits = {
                DayOfWeek(day): limit for day, limit in state.get("daily_limits", {}).items()
            }

            self.schedules = {
                DayOfWeek(int(day)): [
                    (datetime.fromisoformat(s).time(), datetime.fromisoformat(e).time())
                    for s, e in ranges
                ]
                for day, ranges in state.get("schedules", {}).items()
            }

            self.grace_period_minutes = state.get("grace_period_minutes", 5)
            self.is_locked = state.get("is_locked", False)
            self.usage_data = state.get("usage_data", {})

            session_start_str = state.get("session_start")
            self.session_start = (
                datetime.fromisoformat(session_start_str) if session_start_str else None
            )

            self.grace_period_notified = state.get("grace_period_notified", False)

            logger.info(f"Loaded state for user {self.user_id}")
        except Exception as e:
            logger.error(f"Error loading state for user {self.user_id}: {e}")

    def get_status_summary(self) -> Dict:
        """
        Get comprehensive status summary.

        Returns:
            Dictionary with current status information
        """
        status, message = self.check_allowed()
        remaining = self.get_remaining_time()

        return {
            "user_id": self.user_id,
            "status": status.value,
            "message": message,
            "remaining_minutes": remaining,
            "usage_today": self.get_usage_today(),
            "is_locked": self.is_locked,
            "session_active": self.session_start is not None,
            "grace_period_active": status == LimitStatus.GRACE_PERIOD,
        }
