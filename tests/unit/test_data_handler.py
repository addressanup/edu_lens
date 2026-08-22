"""
Unit tests for Privacy-First Data Handler.

Tests privacy controls including:
- Data minimization
- Encryption
- Auto-deletion
- Consent management
- COPPA compliance

Author: Testing Agent (TST-001)
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from src.privacy.data_handler import (
    ConsentRecord,
    ConsentRequiredError,
    ConsentStatus,
    DataClassification,
    DataHandler,
    DataItem,
    DataRetentionViolationError,
    PrivacyPolicy,
    PrivacyViolationError,
    ProcessingLocation,
    RetentionPolicy,
    classify_data,
)


class TestDataClassification:
    """Test data classification enum."""

    def test_sensitive_classification(self):
        """Test identifying sensitive data."""
        assert DataClassification.SENSITIVE_VISUAL.is_sensitive() is True
        assert DataClassification.VOICE_DATA.is_sensitive() is True
        assert DataClassification.PUBLIC.is_sensitive() is False

    def test_never_stored_classification(self):
        """Test identifying data that should never be stored."""
        assert DataClassification.SENSITIVE_VISUAL.is_never_stored() is True
        assert DataClassification.VOICE_DATA.is_never_stored() is True
        assert DataClassification.PUBLIC.is_never_stored() is False

    def test_volatile_only_classification(self):
        """Test volatile-only data."""
        assert DataClassification.SENSITIVE_VISUAL.is_volatile_only() is True
        assert DataClassification.LEARNING_INTERACTION.is_volatile_only() is True
        assert DataClassification.PUBLIC.is_volatile_only() is False

    def test_encryption_required(self):
        """Test encryption requirements."""
        assert DataClassification.PARENTAL_ACCOUNT.requires_encryption() is True
        assert DataClassification.PUBLIC.requires_encryption() is False

    def test_consent_required(self):
        """Test consent requirements."""
        assert DataClassification.VOICE_DATA.requires_consent() is True
        assert DataClassification.ANONYMOUS_TELEMETRY.requires_consent() is True
        assert DataClassification.PUBLIC.requires_consent() is False


class TestRetentionPolicy:
    """Test retention policy functionality."""

    def test_retention_policy_creation(self):
        """Test creating retention policy."""
        policy = RetentionPolicy(
            classification=DataClassification.DEVICE_METADATA,
            max_retention_days=365,
            description="1 year retention",
        )

        assert policy.max_retention_days == 365
        assert policy.auto_purge_enabled is True

    def test_is_expired_true(self):
        """Test data expiration check (expired)."""
        policy = RetentionPolicy(
            classification=DataClassification.ANONYMOUS_TELEMETRY, max_retention_days=90
        )

        old_timestamp = datetime.utcnow() - timedelta(days=100)

        assert policy.is_expired(old_timestamp) is True

    def test_is_expired_false(self):
        """Test data expiration check (not expired)."""
        policy = RetentionPolicy(
            classification=DataClassification.ANONYMOUS_TELEMETRY, max_retention_days=90
        )

        recent_timestamp = datetime.utcnow() - timedelta(days=30)

        assert policy.is_expired(recent_timestamp) is False

    def test_immediate_deletion_policy(self):
        """Test immediate deletion policy."""
        policy = RetentionPolicy(
            classification=DataClassification.SENSITIVE_VISUAL, max_retention_days=0
        )

        assert policy.is_expired(datetime.utcnow()) is True

    def test_days_until_expiration(self):
        """Test calculating days until expiration."""
        policy = RetentionPolicy(
            classification=DataClassification.DEVICE_METADATA, max_retention_days=30
        )

        recent_timestamp = datetime.utcnow() - timedelta(days=10)
        days_left = policy.days_until_expiration(recent_timestamp)

        assert days_left == 20


class TestConsentRecord:
    """Test consent record functionality."""

    def test_consent_record_creation(self):
        """Test creating consent record."""
        record = ConsentRecord(
            consent_id="consent_123",
            parent_account_id="parent_001",
            child_pseudonym="child_abc",
            category=DataClassification.ANONYMOUS_TELEMETRY,
            status=ConsentStatus.GRANTED,
            timestamp=datetime.utcnow(),
            consent_method="IN_APP_EXPLICIT_CLICK",
            verification_method="MFA_EMAIL_SMS",
        )

        assert record.status == ConsentStatus.GRANTED
        assert record.consent_method == "IN_APP_EXPLICIT_CLICK"

    def test_is_valid_granted(self):
        """Test validity check for granted consent."""
        record = ConsentRecord(
            consent_id="consent_123",
            parent_account_id="parent_001",
            child_pseudonym="child_abc",
            category=DataClassification.VOICE_DATA,
            status=ConsentStatus.GRANTED,
            timestamp=datetime.utcnow(),
            consent_method="IN_APP",
            verification_method="MFA",
            expires_at=datetime.utcnow() + timedelta(days=365),
        )

        assert record.is_valid() is True

    def test_is_valid_expired(self):
        """Test validity check for expired consent."""
        record = ConsentRecord(
            consent_id="consent_123",
            parent_account_id="parent_001",
            child_pseudonym="child_abc",
            category=DataClassification.VOICE_DATA,
            status=ConsentStatus.GRANTED,
            timestamp=datetime.utcnow() - timedelta(days=400),
            consent_method="IN_APP",
            verification_method="MFA",
            expires_at=datetime.utcnow() - timedelta(days=1),
        )

        assert record.is_valid() is False

    def test_is_valid_revoked(self):
        """Test validity check for revoked consent."""
        record = ConsentRecord(
            consent_id="consent_123",
            parent_account_id="parent_001",
            child_pseudonym="child_abc",
            category=DataClassification.VOICE_DATA,
            status=ConsentStatus.GRANTED,
            timestamp=datetime.utcnow(),
            consent_method="IN_APP",
            verification_method="MFA",
            revoked_at=datetime.utcnow(),
        )

        assert record.is_valid() is False


class TestDataItem:
    """Test data item functionality."""

    def test_data_item_creation(self):
        """Test creating a data item."""
        item = DataItem(
            data_id="data_123",
            classification=DataClassification.DEVICE_METADATA,
            content={"device_type": "tablet"},
            created_at=datetime.utcnow(),
            processing_location=ProcessingLocation.EDGE_DEVICE,
        )

        assert item.data_id == "data_123"
        assert item.classification == DataClassification.DEVICE_METADATA

    def test_should_be_deleted_true(self):
        """Test deletion check (should delete)."""
        policy = RetentionPolicy(
            classification=DataClassification.ANONYMOUS_TELEMETRY, max_retention_days=90
        )

        old_item = DataItem(
            data_id="old_data",
            classification=DataClassification.ANONYMOUS_TELEMETRY,
            content="test",
            created_at=datetime.utcnow() - timedelta(days=100),
            processing_location=ProcessingLocation.EDGE_DEVICE,
        )

        assert old_item.should_be_deleted(policy) is True

    def test_should_be_deleted_false(self):
        """Test deletion check (should not delete)."""
        policy = RetentionPolicy(
            classification=DataClassification.DEVICE_METADATA, max_retention_days=365
        )

        recent_item = DataItem(
            data_id="recent_data",
            classification=DataClassification.DEVICE_METADATA,
            content="test",
            created_at=datetime.utcnow() - timedelta(days=30),
            processing_location=ProcessingLocation.EDGE_DEVICE,
        )

        assert recent_item.should_be_deleted(policy) is False


class TestDataHandler:
    """Test main data handler functionality."""

    @pytest.fixture
    def handler(self):
        """Create a data handler instance."""
        return DataHandler()

    def test_handler_initialization(self, handler):
        """Test handler initialization."""
        assert handler.policies is not None
        assert handler.consent_records is not None
        assert handler.audit_log is not None
        assert len(handler.policies) > 0

    def test_policies_initialized(self, handler):
        """Test that policies are initialized for all classifications."""
        # Check key policies exist
        assert DataClassification.PUBLIC in handler.policies
        assert DataClassification.SENSITIVE_VISUAL in handler.policies
        assert DataClassification.VOICE_DATA in handler.policies


class TestDataClassificationFunction:
    """Test data classification functionality."""

    @pytest.fixture
    def handler(self):
        return DataHandler()

    def test_classify_camera_data(self, handler):
        """Test classifying camera data."""
        content = "image_data"
        metadata = {"source": "camera"}

        classification = handler.classify_data(content, metadata)

        assert classification == DataClassification.SENSITIVE_VISUAL

    def test_classify_microphone_data(self, handler):
        """Test classifying microphone data."""
        content = "audio_data"
        metadata = {"source": "microphone"}

        classification = handler.classify_data(content, metadata)

        assert classification == DataClassification.VOICE_DATA

    def test_classify_session_context(self, handler):
        """Test classifying session context."""
        content = {"session_id": "123"}
        metadata = {"type": "session_context"}

        classification = handler.classify_data(content, metadata)

        assert classification == DataClassification.LEARNING_INTERACTION

    def test_classify_telemetry(self, handler):
        """Test classifying telemetry data."""
        content = {"event": "button_click"}
        metadata = {"type": "telemetry"}

        classification = handler.classify_data(content, metadata)

        assert classification == DataClassification.ANONYMOUS_TELEMETRY

    def test_classify_explicit_metadata(self, handler):
        """Test classification with explicit metadata."""
        content = "test"
        metadata = {"classification": "PUBLIC"}

        classification = handler.classify_data(content, metadata)

        assert classification == DataClassification.PUBLIC


class TestDataMinimization:
    """Test data minimization functionality."""

    @pytest.fixture
    def handler(self):
        return DataHandler()

    def test_apply_minimization_with_anonymization(self, handler):
        """Test minimization with anonymization required."""
        item = DataItem(
            data_id="data_123",
            classification=DataClassification.ANONYMOUS_TELEMETRY,
            content={"event": "test", "metadata": "extra"},
            created_at=datetime.utcnow(),
            processing_location=ProcessingLocation.EDGE_DEVICE,
            anonymized=False,
        )

        minimized = handler.apply_minimization(item)

        assert minimized.anonymized is True

    def test_apply_minimization_metadata_removal(self, handler):
        """Test minimization removes unnecessary metadata."""
        item = DataItem(
            data_id="data_123",
            classification=DataClassification.DEVICE_METADATA,
            content="test",
            created_at=datetime.utcnow(),
            processing_location=ProcessingLocation.EDGE_DEVICE,
            metadata={
                "subject_area": "math",
                "unnecessary_field": "value",
                "another_extra": "data",
            },
        )

        minimized = handler.apply_minimization(item)

        # Should keep essential metadata only
        assert "subject_area" in minimized.metadata
        assert "unnecessary_field" not in minimized.metadata


class TestRetentionChecking:
    """Test retention policy checking."""

    @pytest.fixture
    def handler(self):
        return DataHandler()

    def test_check_retention_within_limits(self, handler):
        """Test retention check for recent data."""
        item = DataItem(
            data_id="recent_data",
            classification=DataClassification.DEVICE_METADATA,
            content="test",
            created_at=datetime.utcnow() - timedelta(days=30),
            processing_location=ProcessingLocation.EDGE_DEVICE,
        )

        is_valid = handler.check_retention(item)

        assert is_valid is True

    def test_check_retention_exceeded(self, handler):
        """Test retention check for expired data."""
        item = DataItem(
            data_id="old_data",
            classification=DataClassification.ANONYMOUS_TELEMETRY,
            content="test",
            created_at=datetime.utcnow() - timedelta(days=100),
            processing_location=ProcessingLocation.EDGE_DEVICE,
        )

        with pytest.raises(DataRetentionViolationError):
            handler.check_retention(item)

    def test_check_retention_immediate_deletion(self, handler):
        """Test retention check for immediate deletion data."""
        item = DataItem(
            data_id="sensitive_data",
            classification=DataClassification.SENSITIVE_VISUAL,
            content="image",
            created_at=datetime.utcnow(),
            processing_location=ProcessingLocation.VOLATILE_RAM,
        )

        with pytest.raises(DataRetentionViolationError):
            handler.check_retention(item)


class TestConsentManagement:
    """Test consent management functionality."""

    @pytest.fixture
    def handler(self):
        return DataHandler()

    def test_grant_consent(self, handler):
        """Test granting consent."""
        record = handler.grant_consent(
            parent_account_id="parent_001",
            child_pseudonym="child_abc",
            category=DataClassification.ANONYMOUS_TELEMETRY,
            consent_method="IN_APP_EXPLICIT_CLICK",
            verification_method="MFA_EMAIL_SMS",
        )

        assert isinstance(record, ConsentRecord)
        assert record.status == ConsentStatus.GRANTED

    def test_get_consent_status_granted(self, handler):
        """Test getting granted consent status."""
        handler.grant_consent(
            parent_account_id="parent_001",
            child_pseudonym="child_abc",
            category=DataClassification.VOICE_DATA,
            consent_method="IN_APP",
            verification_method="MFA",
        )

        status = handler.get_consent_status(
            "parent_001", "child_abc", DataClassification.VOICE_DATA
        )

        assert status == ConsentStatus.GRANTED

    def test_get_consent_status_not_requested(self, handler):
        """Test getting consent status when not requested."""
        status = handler.get_consent_status(
            "parent_999", "child_999", DataClassification.VOICE_DATA
        )

        assert status == ConsentStatus.NOT_REQUESTED

    def test_verify_consent_granted(self, handler):
        """Test verifying granted consent."""
        handler.grant_consent(
            "parent_001", "child_abc", DataClassification.ANONYMOUS_TELEMETRY, "IN_APP", "MFA"
        )

        is_valid = handler.verify_consent(
            "parent_001", "child_abc", DataClassification.ANONYMOUS_TELEMETRY
        )

        assert is_valid is True

    def test_verify_consent_not_granted(self, handler):
        """Test verifying consent when not granted."""
        with pytest.raises(ConsentRequiredError):
            handler.verify_consent("parent_999", "child_999", DataClassification.VOICE_DATA)

    def test_verify_consent_not_required(self, handler):
        """Test verifying consent when not required."""
        # PUBLIC data doesn't require consent
        is_valid = handler.verify_consent("parent_001", "child_abc", DataClassification.PUBLIC)

        assert is_valid is True

    def test_revoke_consent(self, handler):
        """Test revoking consent."""
        handler.grant_consent(
            "parent_001", "child_abc", DataClassification.VOICE_DATA, "IN_APP", "MFA"
        )

        revoked = handler.revoke_consent("parent_001", "child_abc", DataClassification.VOICE_DATA)

        assert revoked is True

        status = handler.get_consent_status(
            "parent_001", "child_abc", DataClassification.VOICE_DATA
        )

        assert status == ConsentStatus.REVOKED

    def test_revoke_nonexistent_consent(self, handler):
        """Test revoking nonexistent consent."""
        revoked = handler.revoke_consent("parent_999", "child_999", DataClassification.VOICE_DATA)

        assert revoked is False


class TestAnonymization:
    """Test data anonymization functionality."""

    @pytest.fixture
    def handler(self):
        return DataHandler()

    def test_anonymize_data(self, handler):
        """Test anonymizing data."""
        item = DataItem(
            data_id="data_123",
            classification=DataClassification.ANONYMOUS_TELEMETRY,
            content={
                "event": "click",
                "name": "John Doe",
                "email": "john@example.com",
                "device_id": "device123",
            },
            created_at=datetime.utcnow(),
            processing_location=ProcessingLocation.EDGE_DEVICE,
        )

        anonymized = handler.anonymize(item)

        assert anonymized.anonymized is True
        assert "name" not in anonymized.content
        assert "email" not in anonymized.content
        assert "device_id_hash" in anonymized.content

    def test_anonymize_already_anonymized(self, handler):
        """Test anonymizing already anonymized data."""
        item = DataItem(
            data_id="data_123",
            classification=DataClassification.ANONYMOUS_TELEMETRY,
            content={"event": "click"},
            created_at=datetime.utcnow(),
            processing_location=ProcessingLocation.EDGE_DEVICE,
            anonymized=True,
        )

        result = handler.anonymize(item)

        # Should return as-is
        assert result.anonymized is True


class TestProcessingLocationValidation:
    """Test processing location validation."""

    @pytest.fixture
    def handler(self):
        return DataHandler()

    def test_validate_allowed_location(self, handler):
        """Test validation of allowed location."""
        item = DataItem(
            data_id="data_123",
            classification=DataClassification.DEVICE_METADATA,
            content="test",
            created_at=datetime.utcnow(),
            processing_location=ProcessingLocation.EDGE_DEVICE,
        )

        is_valid = handler.validate_processing_location(item, ProcessingLocation.EDGE_DEVICE)

        assert is_valid is True

    def test_validate_disallowed_location(self, handler):
        """Test validation of disallowed location."""
        item = DataItem(
            data_id="sensitive_data",
            classification=DataClassification.SENSITIVE_VISUAL,
            content="image",
            created_at=datetime.utcnow(),
            processing_location=ProcessingLocation.VOLATILE_RAM,
        )

        with pytest.raises(PrivacyViolationError):
            handler.validate_processing_location(
                item, ProcessingLocation.CLOUD_STORAGE  # Not allowed for sensitive visual
            )


class TestDataItemCreation:
    """Test data item creation with privacy controls."""

    @pytest.fixture
    def handler(self):
        return DataHandler()

    def test_create_data_item_basic(self, handler):
        """Test creating basic data item."""
        item = handler.create_data_item(
            content="test content",
            classification=DataClassification.DEVICE_METADATA,
            processing_location=ProcessingLocation.EDGE_DEVICE,
        )

        assert isinstance(item, DataItem)
        assert item.classification == DataClassification.DEVICE_METADATA

    def test_create_data_item_with_consent(self, handler):
        """Test creating data item with consent verification."""
        # Grant consent first
        handler.grant_consent(
            "parent_001", "child_abc", DataClassification.ANONYMOUS_TELEMETRY, "IN_APP", "MFA"
        )

        item = handler.create_data_item(
            content={"event": "test"},
            classification=DataClassification.ANONYMOUS_TELEMETRY,
            processing_location=ProcessingLocation.EDGE_DEVICE,
            parent_account_id="parent_001",
            child_pseudonym="child_abc",
        )

        assert item.consent_verified is True

    def test_create_data_item_without_required_consent(self, handler):
        """Test creating data item without required consent."""
        with pytest.raises(ConsentRequiredError):
            handler.create_data_item(
                content="test",
                classification=DataClassification.VOICE_DATA,
                processing_location=ProcessingLocation.SECURE_ENCLAVE,
                parent_account_id="parent_001",
                child_pseudonym="child_abc",
            )

    def test_create_data_item_invalid_location(self, handler):
        """Test creating data item with invalid location."""
        with pytest.raises(PrivacyViolationError):
            handler.create_data_item(
                content="image",
                classification=DataClassification.SENSITIVE_VISUAL,
                processing_location=ProcessingLocation.CLOUD_STORAGE,
            )


class TestAuditLogging:
    """Test audit logging functionality."""

    @pytest.fixture
    def handler(self):
        return DataHandler()

    def test_audit_log_creation(self, handler):
        """Test that audit logs are created."""
        initial_count = len(handler.audit_log)

        handler.grant_consent(
            "parent_001", "child_abc", DataClassification.VOICE_DATA, "IN_APP", "MFA"
        )

        assert len(handler.audit_log) > initial_count

    def test_get_audit_log(self, handler):
        """Test retrieving audit log."""
        handler.grant_consent(
            "parent_001", "child_abc", DataClassification.VOICE_DATA, "IN_APP", "MFA"
        )

        logs = handler.get_audit_log(limit=10)

        assert len(logs) > 0

    def test_export_consent_records(self, handler):
        """Test exporting consent records."""
        handler.grant_consent(
            "parent_001", "child_abc", DataClassification.VOICE_DATA, "IN_APP", "MFA"
        )

        handler.grant_consent(
            "parent_001", "child_xyz", DataClassification.ANONYMOUS_TELEMETRY, "IN_APP", "MFA"
        )

        records = handler.export_consent_records("parent_001")

        assert len(records) == 2


class TestPrivacyViolationDetection:
    """Test privacy violation detection."""

    @pytest.fixture
    def handler(self):
        return DataHandler()

    def test_sensitive_visual_storage_violation(self, handler):
        """Test detecting storage of sensitive visual data."""
        with pytest.raises(PrivacyViolationError):
            handler.create_data_item(
                content="image",
                classification=DataClassification.SENSITIVE_VISUAL,
                processing_location=ProcessingLocation.CLOUD_STORAGE,
            )

    def test_voice_data_storage_violation(self, handler):
        """Test detecting storage of voice data."""
        with pytest.raises(PrivacyViolationError):
            handler.create_data_item(
                content="audio",
                classification=DataClassification.VOICE_DATA,
                processing_location=ProcessingLocation.CLOUD_STORAGE,
            )


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_classify_data_function(self):
        """Test standalone classify_data function."""
        classification = classify_data(content="image", metadata={"source": "camera"})

        assert classification == DataClassification.SENSITIVE_VISUAL


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def handler(self):
        return DataHandler()

    def test_consent_expiration(self, handler):
        """Test consent expiration handling."""
        # Grant consent that expires immediately
        record = handler.grant_consent(
            "parent_001", "child_abc", DataClassification.VOICE_DATA, "IN_APP", "MFA"
        )

        # Manually set expiration to past
        consent_key = f"parent_001:child_abc:VOICE_DATA"
        handler.consent_records[consent_key].expires_at = datetime.utcnow() - timedelta(days=1)

        status = handler.get_consent_status(
            "parent_001", "child_abc", DataClassification.VOICE_DATA
        )

        assert status == ConsentStatus.EXPIRED

    def test_multiple_consent_categories(self, handler):
        """Test managing consent for multiple categories."""
        categories = [
            DataClassification.VOICE_DATA,
            DataClassification.ANONYMOUS_TELEMETRY,
            DataClassification.PARENTAL_ACCOUNT,
        ]

        for category in categories:
            handler.grant_consent("parent_001", "child_abc", category, "IN_APP", "MFA")

        # All should be granted
        for category in categories:
            status = handler.get_consent_status("parent_001", "child_abc", category)
            assert status == ConsentStatus.GRANTED
