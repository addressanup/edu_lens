"""
Device Manager for EduLens Parental Controls

Provides remote device management capabilities.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from pathlib import Path
from queue import Queue, PriorityQueue
import threading


logger = logging.getLogger(__name__)


class DeviceStatus(Enum):
    """Device status states"""
    ONLINE = "online"
    OFFLINE = "offline"
    LOCKED = "locked"
    SYNCING = "syncing"
    ERROR = "error"


class CommandType(Enum):
    """Types of remote commands"""
    LOCK = "lock"
    UNLOCK = "unlock"
    UPDATE_SETTINGS = "update_settings"
    FORCE_SYNC = "force_sync"
    GET_STATUS = "get_status"
    RESTART_APP = "restart_app"
    CLEAR_CACHE = "clear_cache"


class CommandPriority(Enum):
    """Priority levels for commands"""
    CRITICAL = 1  # Lock/unlock commands
    HIGH = 2      # Setting updates
    NORMAL = 3    # Status requests
    LOW = 4       # Sync operations


class RemoteCommand:
    """Represents a remote management command."""

    def __init__(
        self,
        command_type: CommandType,
        payload: Optional[Dict] = None,
        priority: CommandPriority = CommandPriority.NORMAL,
        command_id: Optional[str] = None
    ):
        self.command_id = command_id or str(uuid.uuid4())
        self.command_type = command_type
        self.payload = payload or {}
        self.priority = priority
        self.created_at = datetime.now()
        self.executed_at: Optional[datetime] = None
        self.status = "pending"
        self.result: Optional[Dict] = None
        self.error: Optional[str] = None

    def __lt__(self, other):
        """For priority queue comparison."""
        return self.priority.value < other.priority.value

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage/transmission."""
        return {
            'command_id': self.command_id,
            'command_type': self.command_type.value,
            'payload': self.payload,
            'priority': self.priority.value,
            'created_at': self.created_at.isoformat(),
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'status': self.status,
            'result': self.result,
            'error': self.error
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'RemoteCommand':
        """Create from dictionary."""
        cmd = cls(
            command_type=CommandType(data['command_type']),
            payload=data.get('payload', {}),
            priority=CommandPriority(data['priority']),
            command_id=data['command_id']
        )
        cmd.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('executed_at'):
            cmd.executed_at = datetime.fromisoformat(data['executed_at'])
        cmd.status = data.get('status', 'pending')
        cmd.result = data.get('result')
        cmd.error = data.get('error')
        return cmd


class DeviceInfo:
    """Information about a managed device."""

    def __init__(
        self,
        device_id: str,
        device_name: str,
        user_id: str,
        platform: str,
        app_version: str
    ):
        self.device_id = device_id
        self.device_name = device_name
        self.user_id = user_id
        self.platform = platform
        self.app_version = app_version
        self.status = DeviceStatus.OFFLINE
        self.last_seen: Optional[datetime] = None
        self.battery_level: Optional[int] = None
        self.is_charging: bool = False
        self.connection_type: Optional[str] = None  # wifi, cellular, none
        self.is_locked: bool = False

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'device_id': self.device_id,
            'device_name': self.device_name,
            'user_id': self.user_id,
            'platform': self.platform,
            'app_version': self.app_version,
            'status': self.status.value,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'battery_level': self.battery_level,
            'is_charging': self.is_charging,
            'connection_type': self.connection_type,
            'is_locked': self.is_locked
        }


class DeviceManager:
    """
    Manages remote device control and monitoring.

    Features:
    - Remote lock/unlock
    - Settings updates
    - Device status monitoring
    - Offline command queuing
    - Secure command channel
    - Multi-device support
    """

    def __init__(self, parent_id: str, storage_path: Optional[Path] = None):
        """
        Initialize DeviceManager.

        Args:
            parent_id: Unique identifier for the parent account
            storage_path: Path to store device data
        """
        self.parent_id = parent_id
        self.storage_path = storage_path or Path(f"/tmp/edulens/devices/{parent_id}")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.devices: Dict[str, DeviceInfo] = {}
        self.command_queue: PriorityQueue = PriorityQueue()
        self.command_history: List[RemoteCommand] = []
        self.pending_commands: Dict[str, RemoteCommand] = {}

        self._lock = threading.Lock()

        self._load_state()

    def register_device(
        self,
        device_id: str,
        device_name: str,
        user_id: str,
        platform: str,
        app_version: str
    ) -> DeviceInfo:
        """
        Register a new device for management.

        Args:
            device_id: Unique device identifier
            device_name: Human-readable device name
            user_id: User ID associated with the device
            platform: Device platform (iOS, Android, etc.)
            app_version: App version installed

        Returns:
            DeviceInfo object
        """
        with self._lock:
            device = DeviceInfo(
                device_id=device_id,
                device_name=device_name,
                user_id=user_id,
                platform=platform,
                app_version=app_version
            )
            self.devices[device_id] = device

            logger.info(f"Registered device {device_id} ({device_name}) for parent {self.parent_id}")
            self._save_state()

            return device

    def unregister_device(self, device_id: str) -> bool:
        """
        Unregister a device.

        Args:
            device_id: Device to unregister

        Returns:
            True if device was found and removed
        """
        with self._lock:
            if device_id in self.devices:
                del self.devices[device_id]
                logger.info(f"Unregistered device {device_id} for parent {self.parent_id}")
                self._save_state()
                return True
            return False

    def lock_device(self, device_id: str, reason: Optional[str] = None) -> str:
        """
        Send remote lock command to a device.

        Args:
            device_id: Device to lock
            reason: Optional reason for locking

        Returns:
            Command ID

        Raises:
            ValueError: If device not found
        """
        if device_id not in self.devices:
            raise ValueError(f"Device {device_id} not found")

        command = RemoteCommand(
            command_type=CommandType.LOCK,
            payload={'reason': reason or 'Locked by parent'},
            priority=CommandPriority.CRITICAL
        )

        self._enqueue_command(device_id, command)
        logger.info(f"Lock command sent to device {device_id}: {command.command_id}")

        return command.command_id

    def unlock_device(self, device_id: str) -> str:
        """
        Send remote unlock command to a device.

        Args:
            device_id: Device to unlock

        Returns:
            Command ID

        Raises:
            ValueError: If device not found
        """
        if device_id not in self.devices:
            raise ValueError(f"Device {device_id} not found")

        command = RemoteCommand(
            command_type=CommandType.UNLOCK,
            priority=CommandPriority.CRITICAL
        )

        self._enqueue_command(device_id, command)
        logger.info(f"Unlock command sent to device {device_id}: {command.command_id}")

        return command.command_id

    def update_settings(
        self,
        device_id: str,
        settings: Dict[str, Any]
    ) -> str:
        """
        Push updated settings to a device.

        Args:
            device_id: Target device
            settings: Settings dictionary to update

        Returns:
            Command ID

        Raises:
            ValueError: If device not found
        """
        if device_id not in self.devices:
            raise ValueError(f"Device {device_id} not found")

        command = RemoteCommand(
            command_type=CommandType.UPDATE_SETTINGS,
            payload={'settings': settings},
            priority=CommandPriority.HIGH
        )

        self._enqueue_command(device_id, command)
        logger.info(f"Settings update sent to device {device_id}: {command.command_id}")

        return command.command_id

    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """
        Get current status of a device.

        Args:
            device_id: Device to query

        Returns:
            Dictionary with device status

        Raises:
            ValueError: If device not found
        """
        if device_id not in self.devices:
            raise ValueError(f"Device {device_id} not found")

        device = self.devices[device_id]

        # Determine if device is online (seen in last 5 minutes)
        is_online = False
        if device.last_seen:
            minutes_since_seen = (datetime.now() - device.last_seen).total_seconds() / 60
            is_online = minutes_since_seen < 5

        return {
            'device_id': device_id,
            'device_name': device.device_name,
            'status': DeviceStatus.ONLINE.value if is_online else DeviceStatus.OFFLINE.value,
            'is_locked': device.is_locked,
            'last_seen': device.last_seen.isoformat() if device.last_seen else None,
            'battery_level': device.battery_level,
            'is_charging': device.is_charging,
            'connection_type': device.connection_type,
            'platform': device.platform,
            'app_version': device.app_version,
            'pending_commands': len([c for c in self.pending_commands.values() if c.status == 'pending'])
        }

    def trigger_sync(self, device_id: str) -> str:
        """
        Force a data synchronization on the device.

        Args:
            device_id: Device to sync

        Returns:
            Command ID

        Raises:
            ValueError: If device not found
        """
        if device_id not in self.devices:
            raise ValueError(f"Device {device_id} not found")

        command = RemoteCommand(
            command_type=CommandType.FORCE_SYNC,
            priority=CommandPriority.LOW
        )

        self._enqueue_command(device_id, command)
        logger.info(f"Sync command sent to device {device_id}: {command.command_id}")

        return command.command_id

    def restart_app(self, device_id: str) -> str:
        """
        Request app restart on the device.

        Args:
            device_id: Device to restart app on

        Returns:
            Command ID

        Raises:
            ValueError: If device not found
        """
        if device_id not in self.devices:
            raise ValueError(f"Device {device_id} not found")

        command = RemoteCommand(
            command_type=CommandType.RESTART_APP,
            priority=CommandPriority.HIGH
        )

        self._enqueue_command(device_id, command)
        logger.info(f"App restart command sent to device {device_id}: {command.command_id}")

        return command.command_id

    def update_device_heartbeat(
        self,
        device_id: str,
        battery_level: Optional[int] = None,
        is_charging: bool = False,
        connection_type: Optional[str] = None
    ) -> None:
        """
        Update device status from heartbeat.

        Args:
            device_id: Device sending heartbeat
            battery_level: Battery percentage (0-100)
            is_charging: Whether device is charging
            connection_type: Type of network connection
        """
        if device_id not in self.devices:
            logger.warning(f"Heartbeat from unknown device {device_id}")
            return

        device = self.devices[device_id]
        device.last_seen = datetime.now()
        device.status = DeviceStatus.ONLINE

        if battery_level is not None:
            device.battery_level = battery_level
        device.is_charging = is_charging
        if connection_type:
            device.connection_type = connection_type

        self._save_state()

    def get_pending_commands(self, device_id: str) -> List[Dict]:
        """
        Get pending commands for a device (called by device during sync).

        Args:
            device_id: Device requesting commands

        Returns:
            List of command dictionaries
        """
        if device_id not in self.devices:
            return []

        pending = []
        for command in list(self.pending_commands.values()):
            if command.payload.get('device_id') == device_id and command.status == 'pending':
                pending.append(command.to_dict())

        return pending

    def report_command_result(
        self,
        command_id: str,
        success: bool,
        result: Optional[Dict] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Report result of command execution (called by device).

        Args:
            command_id: ID of executed command
            success: Whether command succeeded
            result: Optional result data
            error: Error message if failed
        """
        if command_id in self.pending_commands:
            command = self.pending_commands[command_id]
            command.executed_at = datetime.now()
            command.status = "completed" if success else "failed"
            command.result = result
            command.error = error

            # Move to history
            self.command_history.append(command)
            del self.pending_commands[command_id]

            logger.info(
                f"Command {command_id} {command.status}: "
                f"{error if error else 'success'}"
            )

            self._save_state()

    def get_command_status(self, command_id: str) -> Optional[Dict]:
        """
        Get status of a specific command.

        Args:
            command_id: Command ID to check

        Returns:
            Command status dictionary or None if not found
        """
        # Check pending commands
        if command_id in self.pending_commands:
            return self.pending_commands[command_id].to_dict()

        # Check history
        for command in self.command_history:
            if command.command_id == command_id:
                return command.to_dict()

        return None

    def get_all_devices(self) -> List[Dict]:
        """
        Get information about all registered devices.

        Returns:
            List of device dictionaries
        """
        devices = []
        for device_id in self.devices:
            devices.append(self.get_device_status(device_id))
        return devices

    def get_command_history(
        self,
        device_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get command history.

        Args:
            device_id: Filter by device (None for all devices)
            limit: Maximum number of commands to return

        Returns:
            List of command dictionaries
        """
        history = self.command_history[-limit:]

        if device_id:
            history = [
                cmd for cmd in history
                if cmd.payload.get('device_id') == device_id
            ]

        return [cmd.to_dict() for cmd in reversed(history)]

    def _enqueue_command(self, device_id: str, command: RemoteCommand) -> None:
        """Add a command to the queue."""
        command.payload['device_id'] = device_id

        with self._lock:
            self.pending_commands[command.command_id] = command
            self.command_queue.put(command)
            self._save_state()

    def _save_state(self) -> None:
        """Save manager state to disk."""
        state = {
            'parent_id': self.parent_id,
            'devices': {
                device_id: device.to_dict()
                for device_id, device in self.devices.items()
            },
            'pending_commands': {
                cmd_id: cmd.to_dict()
                for cmd_id, cmd in self.pending_commands.items()
            },
            'command_history': [
                cmd.to_dict() for cmd in self.command_history[-100:]  # Keep last 100
            ]
        }

        state_file = self.storage_path / 'device_state.json'
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def _load_state(self) -> None:
        """Load manager state from disk."""
        state_file = self.storage_path / 'device_state.json'

        if not state_file.exists():
            return

        try:
            with open(state_file, 'r') as f:
                state = json.load(f)

            # Load devices
            for device_id, device_data in state.get('devices', {}).items():
                device = DeviceInfo(
                    device_id=device_data['device_id'],
                    device_name=device_data['device_name'],
                    user_id=device_data['user_id'],
                    platform=device_data['platform'],
                    app_version=device_data['app_version']
                )
                device.status = DeviceStatus(device_data.get('status', 'offline'))
                if device_data.get('last_seen'):
                    device.last_seen = datetime.fromisoformat(device_data['last_seen'])
                device.battery_level = device_data.get('battery_level')
                device.is_charging = device_data.get('is_charging', False)
                device.connection_type = device_data.get('connection_type')
                device.is_locked = device_data.get('is_locked', False)

                self.devices[device_id] = device

            # Load pending commands
            for cmd_id, cmd_data in state.get('pending_commands', {}).items():
                command = RemoteCommand.from_dict(cmd_data)
                self.pending_commands[cmd_id] = command
                self.command_queue.put(command)

            # Load command history
            self.command_history = [
                RemoteCommand.from_dict(cmd_data)
                for cmd_data in state.get('command_history', [])
            ]

            logger.info(
                f"Loaded state for parent {self.parent_id}: "
                f"{len(self.devices)} devices, "
                f"{len(self.pending_commands)} pending commands"
            )
        except Exception as e:
            logger.error(f"Error loading device state for parent {self.parent_id}: {e}")

    def clear_old_history(self, days: int = 30) -> int:
        """
        Clear command history older than specified days.

        Args:
            days: Days of history to keep

        Returns:
            Number of commands removed
        """
        cutoff = datetime.now() - datetime.timedelta(days=days)
        original_count = len(self.command_history)

        self.command_history = [
            cmd for cmd in self.command_history
            if cmd.created_at >= cutoff
        ]

        removed = original_count - len(self.command_history)
        if removed > 0:
            logger.info(f"Removed {removed} old commands for parent {self.parent_id}")
            self._save_state()

        return removed
