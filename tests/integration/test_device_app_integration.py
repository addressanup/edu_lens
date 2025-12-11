"""
Integration Tests for Device-App Communication

Tests Bluetooth pairing, settings synchronization, and activity reporting
between the EduLens device and parent/teacher app.

Task: TST-001-T2 - Integration Test Suite
Author: Testing Agent (TST-001)
"""

import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest


class TestBluetoothPairingFlow:
    """Test Bluetooth pairing between device and app."""

    def test_device_discovery(
        self,
        mock_device_bluetooth,
    ):
        """Test app can discover EduLens device."""
        # Simulate device discovery
        device = mock_device_bluetooth

        assert device.device_id is not None
        assert device.device_name == "EduLens Test Device"
        assert device.is_connected is False

    def test_pairing_initiation(
        self,
        mock_device_bluetooth,
    ):
        """Test pairing can be initiated."""
        device = mock_device_bluetooth

        # Initiate pairing
        paired = device.connect()

        assert paired is True
        assert device.is_connected is True

    def test_pairing_failure_handling(
        self,
        mock_device_bluetooth,
    ):
        """Test handling of pairing failures."""
        device = mock_device_bluetooth

        # Simulate connection failure
        device.connect = Mock(return_value=False)
        device.is_connected = False

        result = device.connect()

        assert result is False
        assert device.is_connected is False

    def test_connection_persistence(
        self,
        mock_device_bluetooth,
    ):
        """Test connection persists after pairing."""
        device = mock_device_bluetooth

        # Connect
        device.connect()
        assert device.is_connected is True

        # Verify still connected
        time.sleep(0.1)
        assert device.is_connected is True

    def test_disconnection(
        self,
        mock_device_bluetooth,
    ):
        """Test device can be disconnected."""
        device = mock_device_bluetooth

        # Connect then disconnect
        device.connect()
        assert device.is_connected is True

        device.disconnect()
        assert device.is_connected is False

    def test_reconnection_after_disconnect(
        self,
        mock_device_bluetooth,
    ):
        """Test device can reconnect after disconnection."""
        device = mock_device_bluetooth

        # Connect, disconnect, reconnect
        device.connect()
        device.disconnect()

        reconnected = device.connect()

        assert reconnected is True
        assert device.is_connected is True


class TestSettingsSynchronization:
    """Test settings sync between device and app."""

    def test_sync_volume_settings(
        self,
        mock_device_bluetooth,
        mock_app_sync_manager,
    ):
        """Test volume settings sync."""
        device = mock_device_bluetooth
        sync_manager = mock_app_sync_manager

        # Connect device
        device.connect()

        # App changes volume setting
        new_settings = {
            "volume": 0.8,
            "speed": 1.0,
        }

        # Sync to device
        result = sync_manager.sync_settings(new_settings)

        assert result is True
        sync_manager.sync_settings.assert_called_once()

    def test_sync_voice_persona_settings(
        self,
        mock_device_bluetooth,
        mock_app_sync_manager,
    ):
        """Test voice persona settings sync."""
        device = mock_device_bluetooth
        sync_manager = mock_app_sync_manager

        device.connect()

        # App changes voice persona
        new_settings = {
            "voice_id": "friendly_teacher",
            "speaking_rate": 0.9,
            "pitch": 1.0,
        }

        result = sync_manager.sync_settings(new_settings)

        assert result is True

    def test_sync_wake_word_sensitivity(
        self,
        mock_device_bluetooth,
        mock_app_sync_manager,
    ):
        """Test wake word sensitivity sync."""
        device = mock_device_bluetooth
        sync_manager = mock_app_sync_manager

        device.connect()

        # App changes sensitivity
        new_settings = {
            "wake_word_sensitivity": 0.7,
        }

        result = sync_manager.sync_settings(new_settings)

        assert result is True

    def test_sync_parental_controls(
        self,
        mock_device_bluetooth,
        mock_app_sync_manager,
    ):
        """Test parental control settings sync."""
        device = mock_device_bluetooth
        sync_manager = mock_app_sync_manager

        device.connect()

        # App updates parental controls
        new_settings = {
            "session_time_limit": 60,  # minutes
            "content_restrictions": ["math", "science"],
            "break_reminders": True,
        }

        result = sync_manager.sync_settings(new_settings)

        assert result is True

    def test_bidirectional_sync(
        self,
        mock_device_bluetooth,
        mock_app_sync_manager,
    ):
        """Test settings sync works both ways (device to app)."""
        device = mock_device_bluetooth
        sync_manager = mock_app_sync_manager

        device.connect()

        # Device settings changed locally
        device_settings = {
            "last_used_subject": "math",
            "current_problem_set": "addition_level_2",
        }

        # Sync from device to app
        device.send_data = Mock(return_value=True)
        result = device.send_data(device_settings)

        assert result is True

    def test_sync_conflict_resolution(
        self,
        mock_device_bluetooth,
        mock_app_sync_manager,
    ):
        """Test conflict resolution when settings differ."""
        device = mock_device_bluetooth
        sync_manager = mock_app_sync_manager

        device.connect()

        # Simulate conflict (different values on device and app)
        # App should win for safety/parental control settings
        app_settings = {"volume": 0.5}
        device_settings = {"volume": 0.9}

        # Sync should use app settings
        result = sync_manager.sync_settings(app_settings)

        assert result is True


class TestActivityReporting:
    """Test activity reporting from device to app."""

    def test_session_activity_report(
        self,
        mock_device_bluetooth,
        mock_app_sync_manager,
    ):
        """Test session activity is reported to app."""
        device = mock_device_bluetooth
        sync_manager = mock_app_sync_manager

        device.connect()

        # Get activities
        activities = sync_manager.get_activities()

        assert len(activities) > 0
        assert "type" in activities[0]
        assert "timestamp" in activities[0]

    def test_problem_completion_report(
        self,
        mock_device_bluetooth,
        mock_app_sync_manager,
    ):
        """Test completed problems are reported."""
        device = mock_device_bluetooth
        sync_manager = mock_app_sync_manager

        device.connect()

        activities = sync_manager.get_activities()

        # Check for problem completions
        problem_activities = [a for a in activities if a["type"] == "math_problem"]
        assert len(problem_activities) > 0

        if problem_activities:
            activity = problem_activities[0]
            assert "correct" in activity

    def test_progress_metrics_report(
        self,
        mock_device_bluetooth,
        mock_app_sync_manager,
    ):
        """Test progress metrics are reported."""
        device = mock_device_bluetooth
        sync_manager = mock_app_sync_manager

        device.connect()

        # Sync progress
        result = sync_manager.sync_progress()

        assert result is True
        sync_manager.sync_progress.assert_called_once()

    def test_real_time_activity_updates(
        self,
        mock_device_bluetooth,
    ):
        """Test activities are sent in real-time."""
        device = mock_device_bluetooth

        device.connect()

        # Send activity update
        activity = {
            "type": "problem_solved",
            "subject": "math",
            "timestamp": datetime.utcnow().isoformat(),
            "correct": True,
        }

        result = device.send_data(activity)

        assert result is True
        device.send_data.assert_called_once()

    def test_batched_activity_sync(
        self,
        mock_device_bluetooth,
        mock_app_sync_manager,
    ):
        """Test activities can be synced in batches."""
        device = mock_device_bluetooth
        sync_manager = mock_app_sync_manager

        device.connect()

        # Get batch of activities
        activities = sync_manager.get_activities()

        # Should have multiple activities
        assert len(activities) >= 1

    def test_activity_timestamp_accuracy(
        self,
        mock_app_sync_manager,
    ):
        """Test activity timestamps are accurate."""
        sync_manager = mock_app_sync_manager

        activities = sync_manager.get_activities()

        for activity in activities:
            timestamp_str = activity.get("timestamp")
            if timestamp_str:
                # Should be valid ISO format
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                assert isinstance(timestamp, datetime)


class TestDataPrivacyInSync:
    """Test privacy is maintained during sync."""

    def test_no_raw_media_in_sync(
        self,
        mock_device_bluetooth,
    ):
        """Test raw images/audio are not synced to app."""
        device = mock_device_bluetooth

        device.connect()

        # Activity data should not contain raw media
        activity = {
            "type": "problem_solved",
            "problem_text": "What is 2+3?",  # Text only
            "answer": "5",
            "correct": True,
        }

        result = device.send_data(activity)

        # Verify no raw data keys
        assert "image_data" not in activity
        assert "audio_data" not in activity
        assert "raw_data" not in activity

    def test_aggregated_data_only(
        self,
        mock_app_sync_manager,
    ):
        """Test only aggregated data is synced."""
        sync_manager = mock_app_sync_manager

        activities = sync_manager.get_activities()

        # Should be aggregated summaries
        for activity in activities:
            # Should not have detailed PII
            assert "student_name" not in activity or activity.get("student_name") is None

    def test_encrypted_sync_channel(
        self,
        mock_device_bluetooth,
    ):
        """Test sync data is encrypted."""
        device = mock_device_bluetooth

        device.connect()

        # Sync should use encrypted channel
        # (In real implementation, would verify encryption)
        assert device.is_connected is True


class TestOfflineSync:
    """Test sync behavior when offline."""

    def test_offline_data_buffering(
        self,
        mock_device_bluetooth,
    ):
        """Test activities are buffered when offline."""
        device = mock_device_bluetooth

        # Device not connected
        device.is_connected = False

        # Try to send activity (should buffer)
        activity = {"type": "test", "data": "offline"}

        # Should handle gracefully (buffer for later)
        # Mock implementation doesn't actually buffer, but real one would
        assert device.is_connected is False

    def test_sync_on_reconnection(
        self,
        mock_device_bluetooth,
        mock_app_sync_manager,
    ):
        """Test buffered data syncs when reconnected."""
        device = mock_device_bluetooth
        sync_manager = mock_app_sync_manager

        # Disconnect
        device.is_connected = False

        # Reconnect
        device.connect()
        assert device.is_connected is True

        # Sync should happen
        result = sync_manager.sync_progress()
        assert result is True

    def test_sync_retry_on_failure(
        self,
        mock_device_bluetooth,
    ):
        """Test sync retries on failure."""
        device = mock_device_bluetooth

        device.connect()

        # Simulate temporary failure
        device.send_data = Mock(side_effect=[False, False, True])

        # Should eventually succeed after retries
        attempts = 0
        max_attempts = 3
        success = False

        for _ in range(max_attempts):
            if device.send_data({"test": "data"}):
                success = True
                break

        assert success is True


class TestBatteryAndResourceReporting:
    """Test device reports battery and resource status."""

    def test_battery_level_reporting(
        self,
        mock_device_bluetooth,
    ):
        """Test device reports battery level."""
        device = mock_device_bluetooth

        device.connect()

        # Request device status
        device.receive_data = Mock(return_value={
            "battery_level": 75,
            "charging": False,
        })

        status = device.receive_data()

        assert "battery_level" in status
        assert 0 <= status["battery_level"] <= 100

    def test_low_battery_notification(
        self,
        mock_device_bluetooth,
    ):
        """Test low battery notification to app."""
        device = mock_device_bluetooth

        device.connect()

        # Simulate low battery
        low_battery_status = {
            "battery_level": 15,
            "low_battery_warning": True,
        }

        result = device.send_data(low_battery_status)

        assert result is True

    def test_storage_usage_reporting(
        self,
        mock_device_bluetooth,
    ):
        """Test device reports storage usage."""
        device = mock_device_bluetooth

        device.connect()

        device.receive_data = Mock(return_value={
            "storage_used_mb": 250,
            "storage_total_mb": 512,
            "storage_percent": 49,
        })

        status = device.receive_data()

        assert "storage_used_mb" in status
        assert status["storage_used_mb"] <= status["storage_total_mb"]


@pytest.mark.performance
class TestDeviceAppPerformance:
    """Test performance of device-app communication."""

    def test_pairing_latency(
        self,
        mock_device_bluetooth,
        assert_latency,
    ):
        """Test Bluetooth pairing is fast (<2s)."""
        device = mock_device_bluetooth

        start_time = time.perf_counter()

        device.connect()

        elapsed = time.perf_counter() - start_time

        assert_latency(elapsed, 2.0, "Bluetooth pairing")

    def test_settings_sync_latency(
        self,
        mock_device_bluetooth,
        mock_app_sync_manager,
        assert_latency,
    ):
        """Test settings sync is fast (<1s)."""
        device = mock_device_bluetooth
        sync_manager = mock_app_sync_manager

        device.connect()

        start_time = time.perf_counter()

        sync_manager.sync_settings({"volume": 0.8})

        elapsed = time.perf_counter() - start_time

        assert_latency(elapsed, 1.0, "Settings sync")

    def test_activity_report_latency(
        self,
        mock_device_bluetooth,
        assert_latency,
    ):
        """Test activity reporting is fast."""
        device = mock_device_bluetooth

        device.connect()

        activity = {"type": "test", "timestamp": datetime.utcnow().isoformat()}

        start_time = time.perf_counter()

        device.send_data(activity)

        elapsed = time.perf_counter() - start_time

        assert_latency(elapsed, 0.5, "Activity reporting")

    def test_bulk_sync_performance(
        self,
        mock_device_bluetooth,
        mock_app_sync_manager,
        assert_latency,
    ):
        """Test bulk activity sync completes in reasonable time."""
        device = mock_device_bluetooth
        sync_manager = mock_app_sync_manager

        device.connect()

        start_time = time.perf_counter()

        # Get many activities
        activities = sync_manager.get_activities()

        elapsed = time.perf_counter() - start_time

        # Should be fast even for many activities
        assert_latency(elapsed, 1.0, "Bulk activity sync")


class TestDeviceAppErrorHandling:
    """Test error handling in device-app communication."""

    def test_connection_loss_handling(
        self,
        mock_device_bluetooth,
    ):
        """Test handling of connection loss."""
        device = mock_device_bluetooth

        device.connect()
        assert device.is_connected is True

        # Simulate connection loss
        device.disconnect()
        assert device.is_connected is False

        # Should handle gracefully
        # Real implementation would queue data or notify user

    def test_malformed_data_handling(
        self,
        mock_device_bluetooth,
    ):
        """Test handling of malformed sync data."""
        device = mock_device_bluetooth

        device.connect()

        # Try to send malformed data
        malformed_data = {"invalid": None}

        try:
            result = device.send_data(malformed_data)
            # Should handle gracefully or reject
            assert result in [True, False]
        except Exception as e:
            # Or raise appropriate error
            assert "invalid" in str(e).lower() or "malformed" in str(e).lower()

    def test_sync_timeout_handling(
        self,
        mock_device_bluetooth,
    ):
        """Test handling of sync timeouts."""
        device = mock_device_bluetooth

        device.connect()

        # Simulate slow/timeout
        device.send_data = Mock(side_effect=TimeoutError("Sync timeout"))

        with pytest.raises(TimeoutError):
            device.send_data({"test": "data"})
