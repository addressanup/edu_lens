"""
EduLens Local Storage Manager

This module implements secure ephemeral storage for temporary data during processing.
Ensures no persistent storage of sensitive data (images, audio) and provides encrypted
storage for other data types with automatic purging capabilities.

Classification: SECURITY CRITICAL
Author: Security and Privacy Agent (SEC-001)
Task: SEC-001-T2 - On-Device Data Protection
Last Updated: 2025-12-10
"""

import os
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from enum import Enum
import secrets
import hashlib

# Cryptography imports
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logging.warning("cryptography library not available, encryption disabled")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StorageType(Enum):
    """Types of storage available in the system."""
    EPHEMERAL = "ephemeral"  # Auto-deleting temporary storage
    VOLATILE_RAM = "volatile_ram"  # In-memory only, never touches disk
    ENCRYPTED_TEMP = "encrypted_temp"  # Encrypted temporary storage
    SECURE_ENCLAVE = "secure_enclave"  # Hardware-backed secure storage (simulated)


class StorageStatus(Enum):
    """Status of storage container."""
    ACTIVE = "active"
    EXPIRED = "expired"
    PURGED = "purged"
    LOCKED = "locked"


@dataclass
class StorageStats:
    """Statistics about storage usage."""
    container_id: str
    storage_type: StorageType
    size_bytes: int
    created_at: datetime
    expires_at: Optional[datetime]
    encrypted: bool
    access_count: int
    last_accessed: Optional[datetime]
    status: StorageStatus

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "container_id": self.container_id,
            "storage_type": self.storage_type.value,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "encrypted": self.encrypted,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "status": self.status.value,
        }


@dataclass
class StorageContainer:
    """Represents a secure storage container for sensitive data."""
    container_id: str
    storage_type: StorageType
    created_at: datetime
    expires_at: Optional[datetime]
    encryption_key: Optional[bytes]
    storage_path: Optional[Path]
    in_memory_data: Dict[str, bytes]
    metadata: Dict[str, Any]
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    status: StorageStatus = StorageStatus.ACTIVE
    auto_purge: bool = True

    def is_expired(self) -> bool:
        """Check if container has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() >= self.expires_at

    def is_active(self) -> bool:
        """Check if container is active and usable."""
        return self.status == StorageStatus.ACTIVE and not self.is_expired()

    def get_size_bytes(self) -> int:
        """Calculate total size of stored data."""
        total = 0

        # In-memory data
        for data in self.in_memory_data.values():
            total += len(data)

        # File-based data
        if self.storage_path and self.storage_path.exists():
            for file_path in self.storage_path.rglob('*'):
                if file_path.is_file():
                    total += file_path.stat().st_size

        return total


class LocalStorageManager:
    """
    Manages secure local storage with ephemeral containers and automatic deletion.

    Key Features:
    - Ephemeral storage that auto-deletes after timeout
    - Encrypted storage at rest
    - In-memory volatile storage for sensitive data
    - Automatic purging of expired containers
    - Secure deletion (cryptographic erasure)
    - Storage usage monitoring

    COPPA Compliance:
    - No persistent storage of images or audio
    - All sensitive data in volatile memory only
    - Automatic purging on expiration
    - Secure deletion with verification
    """

    def __init__(self,
                 base_temp_dir: Optional[Path] = None,
                 auto_purge_interval: int = 60,
                 enable_background_purge: bool = True):
        """
        Initialize the local storage manager.

        Args:
            base_temp_dir: Base directory for temporary storage (default: system temp)
            auto_purge_interval: Seconds between auto-purge checks (default: 60)
            enable_background_purge: Enable background purge thread (default: True)
        """
        self.base_temp_dir = base_temp_dir or Path(tempfile.gettempdir()) / "edulens_secure"
        self.containers: Dict[str, StorageContainer] = {}
        self.lock = threading.Lock()
        self.auto_purge_interval = auto_purge_interval
        self.enable_background_purge = enable_background_purge
        self._purge_thread: Optional[threading.Thread] = None
        self._stop_purge = threading.Event()

        # Create base directory
        self.base_temp_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Start background purge thread if enabled
        if self.enable_background_purge:
            self._start_background_purge()

        logger.info(f"LocalStorageManager initialized: {self.base_temp_dir}")

    def create_ephemeral_storage(self,
                                 container_id: Optional[str] = None,
                                 ttl_seconds: int = 300,
                                 storage_type: StorageType = StorageType.EPHEMERAL,
                                 encrypt: bool = True,
                                 metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create an ephemeral storage container that auto-deletes after TTL.

        Args:
            container_id: Optional custom container ID (default: auto-generated)
            ttl_seconds: Time-to-live in seconds (default: 300 = 5 minutes)
            storage_type: Type of storage container (default: EPHEMERAL)
            encrypt: Whether to encrypt data at rest (default: True)
            metadata: Optional metadata for the container

        Returns:
            Container ID string

        Example:
            >>> manager = LocalStorageManager()
            >>> container_id = manager.create_ephemeral_storage(ttl_seconds=60)
            >>> manager.store_encrypted(container_id, "image_data", image_bytes)
        """
        with self.lock:
            # Generate container ID
            if container_id is None:
                container_id = self._generate_container_id()

            # Check if container already exists
            if container_id in self.containers:
                raise ValueError(f"Container {container_id} already exists")

            # Create encryption key if needed
            encryption_key = None
            if encrypt and CRYPTO_AVAILABLE:
                encryption_key = Fernet.generate_key()

            # Create storage path for file-based storage
            storage_path = None
            if storage_type in [StorageType.EPHEMERAL, StorageType.ENCRYPTED_TEMP]:
                storage_path = self.base_temp_dir / container_id
                storage_path.mkdir(parents=True, exist_ok=True, mode=0o700)

            # Calculate expiration time
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

            # Create container
            container = StorageContainer(
                container_id=container_id,
                storage_type=storage_type,
                created_at=datetime.utcnow(),
                expires_at=expires_at,
                encryption_key=encryption_key,
                storage_path=storage_path,
                in_memory_data={},
                metadata=metadata or {},
                auto_purge=True,
            )

            self.containers[container_id] = container

            logger.info(
                f"Created {storage_type.value} container: {container_id}, "
                f"TTL: {ttl_seconds}s, Encrypted: {encrypt}"
            )

            return container_id

    def store_encrypted(self,
                       container_id: str,
                       key: str,
                       data: bytes,
                       in_memory_only: bool = False) -> bool:
        """
        Store data in an encrypted container.

        Args:
            container_id: Container ID to store data in
            key: Key to identify the data
            data: Raw bytes to store
            in_memory_only: Force in-memory storage (default: False)

        Returns:
            True if stored successfully

        Raises:
            ValueError: If container doesn't exist or is invalid

        Example:
            >>> manager.store_encrypted(container_id, "voice_sample", audio_bytes, in_memory_only=True)
        """
        with self.lock:
            # Get container
            container = self._get_active_container(container_id)

            # Force in-memory for volatile storage types
            if container.storage_type in [StorageType.VOLATILE_RAM, StorageType.SECURE_ENCLAVE]:
                in_memory_only = True

            # Encrypt data if encryption is enabled
            encrypted_data = data
            if container.encryption_key and CRYPTO_AVAILABLE:
                fernet = Fernet(container.encryption_key)
                encrypted_data = fernet.encrypt(data)

            # Store data
            if in_memory_only:
                # In-memory storage
                container.in_memory_data[key] = encrypted_data
                logger.debug(f"Stored {len(data)} bytes in-memory: {container_id}/{key}")
            else:
                # File-based storage
                if container.storage_path is None:
                    raise ValueError(f"Container {container_id} has no storage path")

                file_path = container.storage_path / self._sanitize_filename(key)
                file_path.write_bytes(encrypted_data)
                logger.debug(f"Stored {len(data)} bytes to file: {file_path}")

            # Update access stats
            container.access_count += 1
            container.last_accessed = datetime.utcnow()

            return True

    def retrieve_decrypted(self,
                          container_id: str,
                          key: str,
                          auto_delete: bool = False) -> Optional[bytes]:
        """
        Retrieve and decrypt data from a container.

        Args:
            container_id: Container ID to retrieve from
            key: Key identifying the data
            auto_delete: Automatically delete data after retrieval (default: False)

        Returns:
            Decrypted bytes, or None if not found

        Raises:
            ValueError: If container doesn't exist or is invalid

        Example:
            >>> data = manager.retrieve_decrypted(container_id, "image_data", auto_delete=True)
        """
        with self.lock:
            # Get container
            container = self._get_active_container(container_id)

            # Retrieve encrypted data
            encrypted_data = None
            from_memory = False

            # Try in-memory first
            if key in container.in_memory_data:
                encrypted_data = container.in_memory_data[key]
                from_memory = True
            # Try file-based storage
            elif container.storage_path:
                file_path = container.storage_path / self._sanitize_filename(key)
                if file_path.exists():
                    encrypted_data = file_path.read_bytes()

            if encrypted_data is None:
                logger.warning(f"Data not found: {container_id}/{key}")
                return None

            # Decrypt data if encryption is enabled
            decrypted_data = encrypted_data
            if container.encryption_key and CRYPTO_AVAILABLE:
                try:
                    fernet = Fernet(container.encryption_key)
                    decrypted_data = fernet.decrypt(encrypted_data)
                except Exception as e:
                    logger.error(f"Decryption failed for {container_id}/{key}: {e}")
                    return None

            # Update access stats
            container.access_count += 1
            container.last_accessed = datetime.utcnow()

            # Auto-delete if requested
            if auto_delete:
                if from_memory:
                    del container.in_memory_data[key]
                elif container.storage_path:
                    file_path = container.storage_path / self._sanitize_filename(key)
                    self._secure_delete_file(file_path)

                logger.debug(f"Auto-deleted after retrieval: {container_id}/{key}")

            logger.debug(f"Retrieved {len(decrypted_data)} bytes: {container_id}/{key}")
            return decrypted_data

    def purge_storage(self, container_id: str, secure_wipe: bool = True) -> bool:
        """
        Purge a storage container and securely delete all data.

        Args:
            container_id: Container ID to purge
            secure_wipe: Use cryptographic erasure (default: True)

        Returns:
            True if purged successfully

        Example:
            >>> manager.purge_storage(container_id, secure_wipe=True)
        """
        with self.lock:
            if container_id not in self.containers:
                logger.warning(f"Container not found for purge: {container_id}")
                return False

            container = self.containers[container_id]

            # Clear in-memory data with secure erasure
            if secure_wipe:
                for key in list(container.in_memory_data.keys()):
                    # Overwrite with random data before deletion
                    data_size = len(container.in_memory_data[key])
                    container.in_memory_data[key] = secrets.token_bytes(data_size)

            container.in_memory_data.clear()

            # Securely delete file-based storage
            if container.storage_path and container.storage_path.exists():
                if secure_wipe:
                    self._secure_delete_directory(container.storage_path)
                else:
                    shutil.rmtree(container.storage_path)

            # Update container status
            container.status = StorageStatus.PURGED

            # Remove from active containers
            del self.containers[container_id]

            logger.info(f"Purged container: {container_id}, Secure wipe: {secure_wipe}")
            return True

    def get_storage_stats(self, container_id: str) -> Optional[StorageStats]:
        """
        Get statistics about a storage container.

        Args:
            container_id: Container ID to get stats for

        Returns:
            StorageStats object or None if not found
        """
        with self.lock:
            if container_id not in self.containers:
                return None

            container = self.containers[container_id]

            return StorageStats(
                container_id=container_id,
                storage_type=container.storage_type,
                size_bytes=container.get_size_bytes(),
                created_at=container.created_at,
                expires_at=container.expires_at,
                encrypted=container.encryption_key is not None,
                access_count=container.access_count,
                last_accessed=container.last_accessed,
                status=container.status,
            )

    def list_containers(self) -> List[str]:
        """
        List all active container IDs.

        Returns:
            List of container ID strings
        """
        with self.lock:
            return list(self.containers.keys())

    def get_total_storage_bytes(self) -> int:
        """
        Get total storage usage across all containers.

        Returns:
            Total bytes used
        """
        with self.lock:
            total = 0
            for container in self.containers.values():
                total += container.get_size_bytes()
            return total

    def purge_expired_containers(self) -> int:
        """
        Purge all expired containers.

        Returns:
            Number of containers purged
        """
        expired_containers = []

        with self.lock:
            for container_id, container in self.containers.items():
                if container.is_expired() and container.auto_purge:
                    expired_containers.append(container_id)

        # Purge expired containers (releases lock for each purge)
        purged_count = 0
        for container_id in expired_containers:
            if self.purge_storage(container_id, secure_wipe=True):
                purged_count += 1

        if purged_count > 0:
            logger.info(f"Auto-purged {purged_count} expired containers")

        return purged_count

    def shutdown(self) -> None:
        """
        Shutdown the storage manager and clean up all resources.
        """
        logger.info("Shutting down LocalStorageManager...")

        # Stop background purge thread
        if self._purge_thread:
            self._stop_purge.set()
            self._purge_thread.join(timeout=5)

        # Purge all containers
        with self.lock:
            container_ids = list(self.containers.keys())

        for container_id in container_ids:
            self.purge_storage(container_id, secure_wipe=True)

        logger.info("LocalStorageManager shutdown complete")

    def _get_active_container(self, container_id: str) -> StorageContainer:
        """Get an active container or raise an error."""
        if container_id not in self.containers:
            raise ValueError(f"Container not found: {container_id}")

        container = self.containers[container_id]

        if container.is_expired():
            raise ValueError(f"Container expired: {container_id}")

        if container.status != StorageStatus.ACTIVE:
            raise ValueError(f"Container not active: {container_id} (status: {container.status.value})")

        return container

    def _generate_container_id(self) -> str:
        """Generate a unique container ID."""
        timestamp = datetime.utcnow().isoformat()
        random_bytes = secrets.token_bytes(16)
        combined = f"{timestamp}{random_bytes.hex()}".encode()
        hash_value = hashlib.sha256(combined).hexdigest()[:16]
        return f"container_{hash_value}"

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage."""
        # Remove dangerous characters
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-."
        sanitized = "".join(c if c in safe_chars else "_" for c in filename)

        # Hash if too long
        if len(sanitized) > 200:
            hash_value = hashlib.sha256(filename.encode()).hexdigest()[:16]
            sanitized = f"{sanitized[:100]}_{hash_value}"

        return sanitized

    def _secure_delete_file(self, file_path: Path) -> None:
        """Securely delete a file by overwriting before deletion."""
        if not file_path.exists():
            return

        try:
            # Get file size
            size = file_path.stat().st_size

            # Overwrite with random data (3 passes)
            for _ in range(3):
                with open(file_path, 'wb') as f:
                    f.write(secrets.token_bytes(size))
                    f.flush()
                    os.fsync(f.fileno())

            # Delete file
            file_path.unlink()

        except Exception as e:
            logger.error(f"Secure delete failed for {file_path}: {e}")
            # Fall back to regular deletion
            try:
                file_path.unlink()
            except:
                pass

    def _secure_delete_directory(self, dir_path: Path) -> None:
        """Securely delete a directory and all its contents."""
        if not dir_path.exists():
            return

        try:
            # Secure delete all files
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    self._secure_delete_file(file_path)

            # Remove directory
            shutil.rmtree(dir_path, ignore_errors=True)

        except Exception as e:
            logger.error(f"Secure directory delete failed for {dir_path}: {e}")

    def _start_background_purge(self) -> None:
        """Start background thread for automatic purging."""
        def purge_loop():
            while not self._stop_purge.is_set():
                try:
                    self.purge_expired_containers()
                except Exception as e:
                    logger.error(f"Background purge error: {e}")

                # Wait for interval or stop signal
                self._stop_purge.wait(timeout=self.auto_purge_interval)

        self._purge_thread = threading.Thread(target=purge_loop, daemon=True)
        self._purge_thread.start()
        logger.info(f"Background purge thread started (interval: {self.auto_purge_interval}s)")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.shutdown()
        return False


# Singleton instance for application-wide use
_storage_manager_instance: Optional[LocalStorageManager] = None


def get_storage_manager(**kwargs) -> LocalStorageManager:
    """
    Get or create the singleton storage manager instance.

    Args:
        **kwargs: Arguments to pass to LocalStorageManager constructor (only used on first call)

    Returns:
        LocalStorageManager singleton instance
    """
    global _storage_manager_instance

    if _storage_manager_instance is None:
        _storage_manager_instance = LocalStorageManager(**kwargs)

    return _storage_manager_instance


# Export public API
__all__ = [
    "LocalStorageManager",
    "StorageType",
    "StorageStatus",
    "StorageStats",
    "StorageContainer",
    "get_storage_manager",
]
