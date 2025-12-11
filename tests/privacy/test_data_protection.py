"""
EduLens Data Protection Test Suite

Comprehensive tests for on-device data protection features including:
- Ephemeral storage with auto-deletion
- Secure data deletion and verification
- Data minimization pipelines
- Retention policy enforcement

Classification: SECURITY CRITICAL
Author: Security and Privacy Agent (SEC-001)
Task: SEC-001-T2 - On-Device Data Protection
Last Updated: 2025-12-10
"""

import hashlib
import os
import secrets
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Import modules under test
from src.privacy.local_storage_manager import (
    LocalStorageManager,
    StorageType,
    StorageStatus,
    get_storage_manager,
)
from src.privacy.data_minimizer import (
    DataMinimizer,
    MinimizationLevel,
    DataType,
)
from src.privacy.auto_deletion import (
    AutoDeletionManager,
    DeletionTrigger,
    DeletionStatus,
    DeletionMethod,
    RetentionPolicy,
)


# =============================================================================
# LocalStorageManager Tests
# =============================================================================

class TestLocalStorageManager:
    """Tests for LocalStorageManager - ephemeral storage and auto-deletion."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        # Cleanup
        import shutil
        if temp_path.exists():
            shutil.rmtree(temp_path)

    @pytest.fixture
    def storage_manager(self, temp_dir):
        """Create storage manager instance for testing."""
        manager = LocalStorageManager(
            base_temp_dir=temp_dir,
            enable_background_purge=False  # Disable for testing
        )
        yield manager
        manager.shutdown()

    def test_create_ephemeral_storage(self, storage_manager):
        """Test creating ephemeral storage container."""
        container_id = storage_manager.create_ephemeral_storage(
            ttl_seconds=300,
            storage_type=StorageType.EPHEMERAL,
            encrypt=True
        )

        assert container_id is not None
        assert container_id in storage_manager.list_containers()

        # Get stats
        stats = storage_manager.get_storage_stats(container_id)
        assert stats is not None
        assert stats.storage_type == StorageType.EPHEMERAL
        assert stats.encrypted is True
        assert stats.status == StorageStatus.ACTIVE

    def test_store_and_retrieve_encrypted(self, storage_manager):
        """Test storing and retrieving encrypted data."""
        container_id = storage_manager.create_ephemeral_storage(ttl_seconds=300)

        # Store data
        test_data = b"sensitive test data"
        success = storage_manager.store_encrypted(container_id, "test_key", test_data)
        assert success is True

        # Retrieve data
        retrieved_data = storage_manager.retrieve_decrypted(container_id, "test_key")
        assert retrieved_data == test_data

    def test_in_memory_only_storage(self, storage_manager):
        """Test volatile in-memory storage (never touches disk)."""
        container_id = storage_manager.create_ephemeral_storage(
            ttl_seconds=300,
            storage_type=StorageType.VOLATILE_RAM
        )

        # Store data in memory only
        test_data = b"volatile sensitive data"
        storage_manager.store_encrypted(container_id, "voice_sample", test_data, in_memory_only=True)

        # Verify data is in memory
        container = storage_manager.containers[container_id]
        assert "voice_sample" in container.in_memory_data

        # Verify no files were created
        if container.storage_path:
            assert not container.storage_path.exists() or not any(container.storage_path.iterdir())

        # Retrieve data
        retrieved = storage_manager.retrieve_decrypted(container_id, "voice_sample")
        assert retrieved == test_data

    def test_auto_delete_on_retrieval(self, storage_manager):
        """Test automatic deletion after data retrieval."""
        container_id = storage_manager.create_ephemeral_storage(ttl_seconds=300)

        test_data = b"auto-delete test data"
        storage_manager.store_encrypted(container_id, "temp_key", test_data)

        # Retrieve with auto-delete
        retrieved = storage_manager.retrieve_decrypted(container_id, "temp_key", auto_delete=True)
        assert retrieved == test_data

        # Verify data is deleted
        retrieved_again = storage_manager.retrieve_decrypted(container_id, "temp_key")
        assert retrieved_again is None

    def test_container_expiration(self, storage_manager):
        """Test that containers expire after TTL."""
        # Create container with 1 second TTL
        container_id = storage_manager.create_ephemeral_storage(ttl_seconds=1)

        # Wait for expiration
        time.sleep(1.5)

        # Verify container is expired
        container = storage_manager.containers[container_id]
        assert container.is_expired() is True

        # Attempt to use expired container should raise error
        with pytest.raises(ValueError, match="expired"):
            storage_manager.store_encrypted(container_id, "key", b"data")

    def test_purge_storage(self, storage_manager):
        """Test secure purging of storage container."""
        container_id = storage_manager.create_ephemeral_storage(ttl_seconds=300)

        # Store some data
        storage_manager.store_encrypted(container_id, "key1", b"data1")
        storage_manager.store_encrypted(container_id, "key2", b"data2")

        # Purge container
        success = storage_manager.purge_storage(container_id, secure_wipe=True)
        assert success is True

        # Verify container is removed
        assert container_id not in storage_manager.list_containers()

        # Verify stats are not available
        stats = storage_manager.get_storage_stats(container_id)
        assert stats is None

    def test_secure_wipe(self, storage_manager, temp_dir):
        """Test secure file wiping with overwrite."""
        # Create a test file
        test_file = temp_dir / "test_secure_wipe.bin"
        test_data = secrets.token_bytes(1024)
        test_file.write_bytes(test_data)

        # Calculate hash before deletion
        original_hash = hashlib.sha256(test_data).hexdigest()

        # Verify file exists
        assert test_file.exists()

        # Perform secure wipe
        from src.privacy.local_storage_manager import LocalStorageManager
        manager = LocalStorageManager(base_temp_dir=temp_dir, enable_background_purge=False)
        success = manager._secure_delete_file(test_file)

        assert success is True
        assert not test_file.exists()

    def test_storage_stats(self, storage_manager):
        """Test storage usage statistics."""
        container_id = storage_manager.create_ephemeral_storage(ttl_seconds=300)

        # Store data
        data1 = b"a" * 100
        data2 = b"b" * 200
        storage_manager.store_encrypted(container_id, "key1", data1)
        storage_manager.store_encrypted(container_id, "key2", data2)

        # Get stats
        stats = storage_manager.get_storage_stats(container_id)
        assert stats.size_bytes > 0  # Should be at least the size of stored data
        assert stats.access_count == 2  # Two store operations

    def test_background_purge(self, temp_dir):
        """Test background purging of expired containers."""
        # Create manager with background purge enabled
        manager = LocalStorageManager(
            base_temp_dir=temp_dir,
            enable_background_purge=True,
            auto_purge_interval=1
        )

        # Create container with short TTL
        container_id = manager.create_ephemeral_storage(ttl_seconds=1)
        manager.store_encrypted(container_id, "key", b"data")

        # Wait for expiration and auto-purge
        time.sleep(2.5)

        # Manually trigger purge
        purged_count = manager.purge_expired_containers()

        # Container should be purged
        assert container_id not in manager.list_containers()

        manager.shutdown()

    def test_get_total_storage_bytes(self, storage_manager):
        """Test total storage calculation across containers."""
        # Create multiple containers with data
        c1 = storage_manager.create_ephemeral_storage(ttl_seconds=300)
        c2 = storage_manager.create_ephemeral_storage(ttl_seconds=300)

        storage_manager.store_encrypted(c1, "key", b"a" * 100)
        storage_manager.store_encrypted(c2, "key", b"b" * 200)

        total = storage_manager.get_total_storage_bytes()
        assert total > 0


# =============================================================================
# DataMinimizer Tests
# =============================================================================

class TestDataMinimizer:
    """Tests for DataMinimizer - extracting features and discarding raw data."""

    @pytest.fixture
    def minimizer(self):
        """Create DataMinimizer instance."""
        return DataMinimizer(default_minimization_level=MinimizationLevel.STANDARD)

    def test_minimize_image(self, minimizer):
        """Test image minimization - raw data should be discarded."""
        # Create fake image data
        image_data = secrets.token_bytes(10000)

        # Minimize image
        minimized = minimizer.minimize_image(
            image_data=image_data,
            detected_objects=["textbook", "desk", "pencil"],
            detected_text=["Chapter 5", "Photosynthesis", "Plants"],
            scene_type="textbook"
        )

        # Verify minimized representation
        assert minimized is not None
        assert minimized.feature_digest is not None
        assert len(minimized.feature_digest) == 64  # SHA-256 hex digest
        assert "textbook" in minimized.detected_objects
        assert "Chapter 5" in minimized.detected_text
        assert minimized.scene_type == "textbook"
        assert 0.0 <= minimized.quality_score <= 1.0

        # Verify raw image data is not in minimized representation
        minimized_dict = minimized.to_dict()
        assert "image_data" not in minimized_dict
        assert "raw_bytes" not in minimized_dict

    def test_minimize_audio(self, minimizer):
        """Test audio minimization - raw audio should be discarded."""
        # Create fake audio data
        audio_data = secrets.token_bytes(32000)  # ~1 second of audio

        # Minimize audio
        minimized = minimizer.minimize_audio(
            audio_data=audio_data,
            transcription="What is photosynthesis?",
            intent="question",
            duration_seconds=2.5,
            language="en"
        )

        # Verify minimized representation
        assert minimized is not None
        assert minimized.feature_digest is not None
        assert minimized.transcription == "What is photosynthesis?"
        assert minimized.intent == "question"
        assert minimized.duration_seconds == 2.5
        assert len(minimized.keywords) > 0

        # Verify raw audio data is not in minimized representation
        minimized_dict = minimized.to_dict()
        assert "audio_data" not in minimized_dict
        assert "raw_bytes" not in minimized_dict

    def test_strip_pii_email(self, minimizer):
        """Test PII removal - email addresses."""
        text = "My email is john.smith@example.com and I need help"
        cleaned = minimizer.strip_pii(text)

        assert "john.smith@example.com" not in cleaned
        assert "[EMAIL_REDACTED]" in cleaned

    def test_strip_pii_phone(self, minimizer):
        """Test PII removal - phone numbers."""
        text = "Call me at 555-123-4567 or (555) 987-6543"
        cleaned = minimizer.strip_pii(text)

        assert "555-123-4567" not in cleaned
        assert "(555) 987-6543" not in cleaned
        assert "[PHONE_REDACTED]" in cleaned

    def test_strip_pii_multiple(self, minimizer):
        """Test PII removal - multiple types."""
        text = "I am John Smith, email john@test.com, phone 555-1234, IP 192.168.1.1"
        cleaned = minimizer.strip_pii(text)

        assert "john@test.com" not in cleaned
        assert "555-1234" not in cleaned
        assert "192.168.1.1" not in cleaned
        assert "[EMAIL_REDACTED]" in cleaned
        assert "[PHONE_REDACTED]" in cleaned
        assert "[IP_REDACTED]" in cleaned

    def test_aggregate_learning_data(self, minimizer):
        """Test learning data aggregation and anonymization."""
        events = [
            {"type": "question", "subject": "science", "success": True, "indicator": "correct_answer"},
            {"type": "question", "subject": "science", "success": True, "indicator": "correct_answer"},
            {"type": "hint", "subject": "science", "success": False, "duration_seconds": 5.0},
        ]

        aggregate = minimizer.aggregate_learning_data(events, anonymize=True)

        # Verify aggregation
        assert aggregate.interaction_count == 3
        assert aggregate.question_count == 2
        assert aggregate.subject_area == "science"
        assert len(aggregate.success_indicators) == 2

        # Verify anonymization - session ID should be hashed
        assert len(aggregate.session_id) == 16  # Truncated hash

        # Verify only hour is stored (not precise timestamp)
        assert isinstance(aggregate.timestamp_hour, int)
        assert 0 <= aggregate.timestamp_hour <= 23

    def test_create_digest(self, minimizer):
        """Test non-reversible digest creation."""
        data1 = {"test": "data", "value": 123}
        data2 = {"test": "data", "value": 123}
        data3 = {"test": "different", "value": 456}

        digest1 = minimizer.create_digest(data1)
        digest2 = minimizer.create_digest(data2)
        digest3 = minimizer.create_digest(data3)

        # Same data should produce same digest
        assert digest1 == digest2

        # Different data should produce different digest
        assert digest1 != digest3

        # Digest should be SHA-256 hex (64 characters)
        assert len(digest1) == 64

    def test_minimize_metadata(self, minimizer):
        """Test metadata minimization."""
        metadata = {
            "timestamp": datetime.utcnow(),
            "type": "image",
            "subject_area": "science",
            "user_id": "user_123",  # Should be removed
            "device_serial": "ABC123",  # Should be removed
            "location": "classroom",  # Should be removed
        }

        minimized = minimizer.minimize_metadata(metadata)

        # Essential fields should be kept
        assert "type" in minimized
        assert "subject_area" in minimized

        # Non-essential fields should be removed
        assert "user_id" not in minimized
        assert "device_serial" not in minimized
        assert "location" not in minimized

        # Timestamp should be converted to hour only
        assert "timestamp" not in minimized
        assert "timestamp_hour" in minimized


# =============================================================================
# AutoDeletionManager Tests
# =============================================================================

class TestAutoDeletionManager:
    """Tests for AutoDeletionManager - automatic deletion and secure erasure."""

    @pytest.fixture
    def deletion_manager(self):
        """Create AutoDeletionManager instance."""
        manager = AutoDeletionManager(enable_background_cleanup=False)
        yield manager
        manager.shutdown()

    def test_schedule_deletion(self, deletion_manager):
        """Test scheduling a deletion task."""
        task_id = deletion_manager.schedule_deletion(
            target_id="test_image_123",
            target_type="image",
            trigger=DeletionTrigger.PROCESS_COMPLETE,
            delay_seconds=5,
            deletion_method=DeletionMethod.SECURE_WIPE
        )

        assert task_id is not None
        assert task_id in deletion_manager.deletion_tasks

        # Get task status
        status = deletion_manager.get_task_status(task_id)
        assert status is not None
        assert status["status"] == DeletionStatus.SCHEDULED.value

    def test_delete_on_process_complete(self, deletion_manager):
        """Test immediate deletion after processing."""
        deleted_items = []

        def deletion_callback(target_id):
            deleted_items.append(target_id)
            return True

        task_id = deletion_manager.delete_on_process_complete(
            target_id="voice_sample_456",
            target_type="audio",
            deletion_callback=deletion_callback,
            deletion_method=DeletionMethod.SECURE_WIPE
        )

        # Verify deletion was executed
        assert "voice_sample_456" in deleted_items

        # Verify task status
        status = deletion_manager.get_task_status(task_id)
        assert status["status"] == DeletionStatus.COMPLETED.value

    def test_secure_wipe(self, deletion_manager):
        """Test secure file wiping."""
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"sensitive data to be wiped")
            tmp_path = Path(tmp.name)

        # Verify file exists
        assert tmp_path.exists()

        # Secure wipe
        success = deletion_manager.secure_wipe(tmp_path, passes=3, verify=True)

        assert success is True
        assert not tmp_path.exists()

    def test_crypto_erase(self, deletion_manager):
        """Test cryptographic erasure by deleting encryption key."""
        # Create temporary key file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(secrets.token_bytes(32))
            key_path = tmp.name

        # Verify key exists
        assert Path(key_path).exists()

        # Crypto erase
        success = deletion_manager.crypto_erase("encrypted_data_789", key_path)

        assert success is True
        assert not Path(key_path).exists()

    def test_verify_deletion(self, deletion_manager):
        """Test deletion verification."""
        verified_targets = []

        def verification_callback(target_id):
            verified_targets.append(target_id)
            return True  # Simulate successful verification

        # Schedule and execute deletion
        task_id = deletion_manager.schedule_deletion(
            target_id="test_data_999",
            target_type="data",
            trigger=DeletionTrigger.TIME_BASED,
            delay_seconds=0
        )

        # Mark as completed (simulate)
        with deletion_manager.lock:
            deletion_manager.deletion_tasks[task_id].status = DeletionStatus.COMPLETED

        # Verify deletion
        is_verified = deletion_manager.verify_deletion(task_id, verification_callback)

        assert is_verified is True
        assert "test_data_999" in verified_targets

        # Check task status
        status = deletion_manager.get_task_status(task_id)
        assert status["status"] == DeletionStatus.VERIFIED.value

    def test_retention_policy(self, deletion_manager):
        """Test retention policy enforcement."""
        # Add custom retention policy
        policy = RetentionPolicy(
            policy_id="test_retention",
            data_type="test_data",
            max_age_seconds=60,
            deletion_method=DeletionMethod.SIMPLE_DELETE,
            auto_delete=True
        )
        deletion_manager.add_retention_policy(policy)

        # Check policy exists
        assert "test_retention" in deletion_manager.retention_policies

        # Test with recent data (not expired)
        recent_time = datetime.utcnow() - timedelta(seconds=30)
        violated_policy = deletion_manager.check_retention_policy("test_data", recent_time)
        assert violated_policy is None

        # Test with old data (expired)
        old_time = datetime.utcnow() - timedelta(seconds=120)
        violated_policy = deletion_manager.check_retention_policy("test_data", old_time)
        assert violated_policy is not None
        assert violated_policy.policy_id == "test_retention"

    def test_get_deletion_log(self, deletion_manager):
        """Test deletion audit log."""
        # Schedule some deletions
        task_id1 = deletion_manager.schedule_deletion(
            target_id="data_1",
            target_type="image",
            trigger=DeletionTrigger.PROCESS_COMPLETE
        )

        task_id2 = deletion_manager.schedule_deletion(
            target_id="data_2",
            target_type="audio",
            trigger=DeletionTrigger.TIME_BASED
        )

        # Get deletion log
        logs = deletion_manager.get_deletion_log()

        assert len(logs) >= 2
        assert any(log["target_id"] == "data_1" for log in logs)
        assert any(log["target_id"] == "data_2" for log in logs)

        # Test filtering by target_id
        filtered_logs = deletion_manager.get_deletion_log(target_id="data_1")
        assert all(log["target_id"] == "data_1" for log in filtered_logs)

    def test_default_retention_policies(self, deletion_manager):
        """Test that default retention policies are initialized."""
        # Should have policies for sensitive data types
        assert any(p.data_type == "image" for p in deletion_manager.retention_policies.values())
        assert any(p.data_type == "audio" for p in deletion_manager.retention_policies.values())

        # Image policy should require immediate deletion
        image_policy = next(p for p in deletion_manager.retention_policies.values() if p.data_type == "image")
        assert image_policy.max_age_seconds == 0
        assert image_policy.deletion_method == DeletionMethod.SECURE_WIPE

    def test_shutdown_cleanup(self):
        """Test that shutdown properly cleans up resources."""
        manager = AutoDeletionManager(enable_background_cleanup=True)

        # Schedule some deletions
        manager.schedule_deletion("data_1", "image", DeletionTrigger.PROCESS_COMPLETE)

        # Shutdown should not raise errors
        manager.shutdown()


# =============================================================================
# Integration Tests
# =============================================================================

class TestDataProtectionIntegration:
    """Integration tests combining multiple components."""

    def test_full_image_protection_workflow(self):
        """Test complete image protection workflow."""
        # 1. Create ephemeral storage
        with LocalStorageManager(enable_background_purge=False) as storage_mgr:
            container_id = storage_mgr.create_ephemeral_storage(
                ttl_seconds=60,
                storage_type=StorageType.VOLATILE_RAM
            )

            # 2. Store raw image temporarily
            raw_image = secrets.token_bytes(5000)
            storage_mgr.store_encrypted(container_id, "raw_image", raw_image, in_memory_only=True)

            # 3. Minimize image (extract features)
            minimizer = DataMinimizer()
            minimized_image = minimizer.minimize_image(
                image_data=raw_image,
                detected_objects=["book", "table"],
                detected_text=["Chapter 7"],
                scene_type="homework"
            )

            # 4. Schedule deletion of raw image
            deletion_mgr = AutoDeletionManager(enable_background_cleanup=False)

            def delete_callback(target_id):
                # Delete from storage
                retrieved = storage_mgr.retrieve_decrypted(container_id, target_id, auto_delete=True)
                return retrieved is None or True

            task_id = deletion_mgr.delete_on_process_complete(
                target_id="raw_image",
                target_type="image",
                deletion_callback=delete_callback
            )

            # 5. Verify deletion
            status = deletion_mgr.get_task_status(task_id)
            assert status["status"] == DeletionStatus.COMPLETED.value

            # 6. Verify only minimized data remains
            assert minimized_image.feature_digest is not None
            assert len(minimized_image.detected_objects) == 2

            deletion_mgr.shutdown()

    def test_full_audio_protection_workflow(self):
        """Test complete audio protection workflow."""
        with LocalStorageManager(enable_background_purge=False) as storage_mgr:
            # Create volatile storage
            container_id = storage_mgr.create_ephemeral_storage(
                ttl_seconds=60,
                storage_type=StorageType.SECURE_ENCLAVE
            )

            # Store raw audio
            raw_audio = secrets.token_bytes(16000)  # ~0.5s of audio
            storage_mgr.store_encrypted(container_id, "voice_sample", raw_audio, in_memory_only=True)

            # Minimize audio
            minimizer = DataMinimizer()
            minimized_audio = minimizer.minimize_audio(
                audio_data=raw_audio,
                transcription="What is the capital of France?",
                intent="question",
                duration_seconds=1.5
            )

            # Delete raw audio immediately
            retrieved = storage_mgr.retrieve_decrypted(container_id, "voice_sample", auto_delete=True)
            assert retrieved is not None

            # Verify raw audio is deleted
            retrieved_again = storage_mgr.retrieve_decrypted(container_id, "voice_sample")
            assert retrieved_again is None

            # Verify minimized audio exists
            assert minimized_audio.transcription == "What is the capital of France?"
            assert "capital" in minimized_audio.keywords or "France" in minimized_audio.keywords


# =============================================================================
# Performance Tests
# =============================================================================

class TestDataProtectionPerformance:
    """Performance tests for data protection operations."""

    def test_encryption_performance(self):
        """Test encryption/decryption performance."""
        manager = LocalStorageManager(enable_background_purge=False)
        container_id = manager.create_ephemeral_storage(ttl_seconds=300)

        # Test with various data sizes
        data_sizes = [1024, 10240, 102400]  # 1KB, 10KB, 100KB

        for size in data_sizes:
            data = secrets.token_bytes(size)

            # Measure store time
            start = time.time()
            manager.store_encrypted(container_id, f"key_{size}", data)
            store_time = time.time() - start

            # Measure retrieve time
            start = time.time()
            retrieved = manager.retrieve_decrypted(container_id, f"key_{size}")
            retrieve_time = time.time() - start

            # Basic sanity check (should be fast)
            assert store_time < 1.0  # Less than 1 second
            assert retrieve_time < 1.0
            assert retrieved == data

        manager.shutdown()

    def test_minimization_performance(self):
        """Test data minimization performance."""
        minimizer = DataMinimizer()

        # Test image minimization
        image_data = secrets.token_bytes(100000)  # 100KB
        start = time.time()
        minimized = minimizer.minimize_image(
            image_data=image_data,
            detected_objects=["item1", "item2"],
            detected_text=["text1", "text2"],
            scene_type="test"
        )
        elapsed = time.time() - start

        assert elapsed < 1.0  # Should be fast
        assert minimized is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
