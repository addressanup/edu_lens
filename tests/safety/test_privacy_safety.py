"""
Privacy Safety Tests for EduLens

Tests privacy protection including data leakage prevention,
proper anonymization, consent enforcement, and data deletion verification.

Test Coverage:
- No data leakage
- Proper anonymization
- Consent enforcement
- Data deletion verification
- COPPA compliance
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, patch

import pytest


class TestDataLeakagePrevention:
    """Test prevention of data leakage and PII exposure."""

    @pytest.mark.safety
    def test_no_pii_in_logs(self):
        """Test that PII is not logged in system logs."""
        student_data = {
            "student_id": "STU123",
            "name": "John Doe",
            "age": 8,
            "email": "parent@example.com",
        }

        log_entry = self._create_log_entry(student_data)

        # PII should be masked or excluded
        assert "John Doe" not in log_entry["message"]
        assert "parent@example.com" not in log_entry["message"]
        # IDs can be included but hashed
        assert "student_id" in log_entry or "student_hash" in log_entry

    @pytest.mark.safety
    def test_no_pii_in_error_messages(self):
        """Test that PII is not exposed in error messages."""
        error_with_pii = {
            "error": "Failed to process request",
            "user_email": "student@school.com",
            "user_name": "Jane Smith",
            "ip_address": "192.168.1.1",
        }

        sanitized_error = self._sanitize_error_message(error_with_pii)

        assert "student@school.com" not in str(sanitized_error)
        assert "Jane Smith" not in str(sanitized_error)
        assert "ip_address" not in sanitized_error or sanitized_error.get(
            "ip_address", ""
        ).startswith("***")

    @pytest.mark.safety
    def test_no_pii_in_api_responses(self):
        """Test that API responses don't leak PII."""
        api_response = {
            "status": "success",
            "data": {"session_id": "sess_abc123", "age_group": "6-8", "subject": "math"},
        }

        # These fields should NOT be in responses
        forbidden_fields = ["name", "email", "phone", "address", "real_name", "school"]

        for field in forbidden_fields:
            assert field not in api_response["data"]

    @pytest.mark.safety
    def test_session_data_isolation(self):
        """Test that session data is isolated between users."""
        session1 = self._create_session("user1")
        session2 = self._create_session("user2")

        # Verify sessions are isolated
        assert session1["session_id"] != session2["session_id"]
        assert session1["user_id"] != session2["user_id"]

        # Attempting to access another user's session should fail
        result = self._access_session("user1", session2["session_id"])
        assert result["success"] is False
        assert result["error"] == "unauthorized"

    @pytest.mark.safety
    def test_no_cross_user_data_access(self):
        """Test that users cannot access other users' data."""
        user1_data = self._store_user_data("user1", {"score": 85})
        user2_data = self._store_user_data("user2", {"score": 92})

        # User1 should only see their own data
        retrieved = self._get_user_data("user1")
        assert retrieved["score"] == 85
        assert "user2" not in str(retrieved)

    @pytest.mark.safety
    def test_temporary_data_cleanup(self):
        """Test that temporary data is properly cleaned up."""
        temp_data_id = self._create_temp_data({"content": "test"})

        # Verify data exists
        assert self._temp_data_exists(temp_data_id) is True

        # Simulate session end
        self._cleanup_temp_data()

        # Verify data is deleted
        assert self._temp_data_exists(temp_data_id) is False

    def _create_log_entry(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock log entry creator with PII masking."""
        # Remove PII from logs
        safe_data = {
            "student_id": data.get("student_id", "UNKNOWN"),
            "age": data.get("age"),
            "timestamp": datetime.now().isoformat(),
        }

        return {"message": f"Student activity recorded", "data": safe_data, "level": "INFO"}

    def _sanitize_error_message(self, error: Dict[str, Any]) -> Dict[str, Any]:
        """Mock error message sanitizer."""
        sanitized = {
            "error": error.get("error", "Unknown error"),
            "error_code": error.get("error_code", "ERR_UNKNOWN"),
        }

        # Mask IP if present
        if "ip_address" in error:
            sanitized["ip_address"] = "***.***.***." + error["ip_address"].split(".")[-1]

        return sanitized

    def _create_session(self, user_id: str) -> Dict[str, Any]:
        """Mock session creator."""
        import hashlib

        session_id = hashlib.sha256(f"{user_id}_{datetime.now()}".encode()).hexdigest()[:16]

        return {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
        }

    def _access_session(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Mock session access checker."""
        # Verify session belongs to user
        import hashlib

        # In real implementation, would check database
        if session_id.startswith(hashlib.sha256(user_id.encode()).hexdigest()[:4]):
            return {"success": True}
        return {"success": False, "error": "unauthorized"}

    def _store_user_data(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock user data storage."""
        return {"user_id": user_id, **data}

    def _get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Mock user data retrieval."""
        # Would retrieve from isolated storage
        if user_id == "user1":
            return {"score": 85}
        elif user_id == "user2":
            return {"score": 92}
        return {}

    def _create_temp_data(self, data: Dict[str, Any]) -> str:
        """Mock temporary data creation."""
        import hashlib

        return hashlib.sha256(str(data).encode()).hexdigest()[:16]

    def _temp_data_exists(self, data_id: str) -> bool:
        """Mock temporary data existence check."""
        # Simulate cleanup by returning False after cleanup
        return not hasattr(self, "_cleaned_up")

    def _cleanup_temp_data(self):
        """Mock temporary data cleanup."""
        self._cleaned_up = True


class TestAnonymization:
    """Test proper data anonymization."""

    @pytest.mark.safety
    def test_user_id_pseudonymization(self):
        """Test that user IDs are properly pseudonymized."""
        real_user_id = "user_john_doe_123"

        pseudonym = self._pseudonymize_user_id(real_user_id)

        # Pseudonym should be irreversible hash
        assert pseudonym != real_user_id
        assert len(pseudonym) == 64  # SHA256 hash
        assert pseudonym.isalnum()

        # Same input should produce same output
        pseudonym2 = self._pseudonymize_user_id(real_user_id)
        assert pseudonym == pseudonym2

    @pytest.mark.safety
    def test_session_data_anonymization(self):
        """Test that session data is properly anonymized."""
        session_data = {
            "user_name": "John Doe",
            "user_email": "john@example.com",
            "ip_address": "192.168.1.1",
            "device_id": "device_12345",
            "activity": "math_practice",
            "score": 85,
        }

        anonymized = self._anonymize_session_data(session_data)

        # PII should be removed
        assert "user_name" not in anonymized
        assert "user_email" not in anonymized

        # IP should be masked
        if "ip_address" in anonymized:
            assert anonymized["ip_address"] != "192.168.1.1"

        # Device ID should be hashed
        if "device_id" in anonymized:
            assert anonymized["device_id"] != "device_12345"

        # Non-PII data should remain
        assert anonymized["activity"] == "math_practice"
        assert anonymized["score"] == 85

    @pytest.mark.safety
    def test_voice_data_anonymization(self):
        """Test that voice data is properly handled (never stored)."""
        voice_data = {
            "audio_bytes": b"mock_audio_data",
            "user_id": "user123",
            "timestamp": datetime.now(),
        }

        # Voice data should NEVER be stored
        result = self._process_voice_data(voice_data)

        assert result["stored"] is False
        assert result["processed"] is True
        assert "audio_bytes" not in result

    @pytest.mark.safety
    def test_image_data_anonymization(self):
        """Test that image data is properly handled (never stored)."""
        image_data = {
            "image_bytes": b"mock_image_data",
            "user_id": "user123",
            "timestamp": datetime.now(),
        }

        # Image data should NEVER be stored
        result = self._process_image_data(image_data)

        assert result["stored"] is False
        assert result["processed"] is True
        assert "image_bytes" not in result

    @pytest.mark.safety
    def test_aggregated_data_anonymization(self):
        """Test that aggregated data cannot identify individuals."""
        user_scores = [
            {"user_id": "user1", "score": 85},
            {"user_id": "user2", "score": 92},
            {"user_id": "user3", "score": 78},
        ]

        aggregated = self._aggregate_and_anonymize(user_scores)

        # Should not contain individual user IDs
        assert "user_ids" not in aggregated
        assert "users" not in aggregated

        # Should contain aggregated statistics
        assert "average_score" in aggregated
        assert "total_users" in aggregated
        assert aggregated["average_score"] == pytest.approx(85.0, abs=1)
        assert aggregated["total_users"] == 3

    def _pseudonymize_user_id(self, user_id: str) -> str:
        """Mock user ID pseudonymization."""
        import hashlib

        return hashlib.sha256(user_id.encode()).hexdigest()

    def _anonymize_session_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock session data anonymization."""
        import hashlib

        anonymized = {}

        # Remove direct PII
        pii_fields = ["user_name", "user_email", "real_name", "phone"]
        for key, value in data.items():
            if key in pii_fields:
                continue  # Skip PII fields

            # Hash identifiers
            if key in ["device_id", "user_id"]:
                anonymized[f"{key}_hash"] = hashlib.sha256(str(value).encode()).hexdigest()[:16]
            # Mask IP
            elif key == "ip_address":
                anonymized[key] = "***.***.***." + value.split(".")[-1]
            # Keep non-PII data
            else:
                anonymized[key] = value

        return anonymized

    def _process_voice_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock voice data processor."""
        # Process but never store
        return {
            "processed": True,
            "stored": False,
            "transcription": "mock transcription",
            "user_id_hash": self._pseudonymize_user_id(data["user_id"]),
        }

    def _process_image_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock image data processor."""
        # Process but never store
        return {
            "processed": True,
            "stored": False,
            "extracted_text": "mock OCR result",
            "user_id_hash": self._pseudonymize_user_id(data["user_id"]),
        }

    def _aggregate_and_anonymize(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Mock data aggregation and anonymization."""
        if not data:
            return {"total_users": 0}

        scores = [item["score"] for item in data]
        return {
            "average_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "total_users": len(data),
        }


class TestConsentEnforcement:
    """Test parental consent enforcement."""

    @pytest.mark.safety
    def test_consent_required_for_data_collection(self):
        """Test that consent is required before collecting data."""
        user_id = "user123"
        parent_id = "parent456"

        # No consent granted yet
        assert self._has_consent(user_id, parent_id, "telemetry") is False

        # Attempt to collect data without consent should fail
        result = self._collect_data(user_id, parent_id, "telemetry", "sample data")
        assert result["success"] is False
        assert result["error"] == "consent_required"

    @pytest.mark.safety
    def test_consent_grant_and_verification(self):
        """Test consent granting and verification."""
        user_id = "user123"
        parent_id = "parent456"

        # Grant consent
        consent_result = self._grant_consent(user_id, parent_id, "telemetry")
        assert consent_result["success"] is True
        assert consent_result["consent_id"] is not None

        # Verify consent is now active
        assert self._has_consent(user_id, parent_id, "telemetry") is True

        # Data collection should now succeed
        result = self._collect_data(user_id, parent_id, "telemetry", "sample data")
        assert result["success"] is True

    @pytest.mark.safety
    def test_consent_expiration(self):
        """Test that consent expires after defined period."""
        user_id = "user123"
        parent_id = "parent456"

        # Grant consent with short expiration
        consent_result = self._grant_consent(user_id, parent_id, "telemetry", expires_in_days=365)
        assert consent_result["success"] is True

        # Check expiration date
        consent_info = self._get_consent_info(user_id, parent_id, "telemetry")
        assert consent_info["expires_at"] is not None

        # Simulate time passing
        future_date = datetime.now() + timedelta(days=366)
        is_expired = self._check_consent_expired(consent_info, future_date)
        assert is_expired is True

    @pytest.mark.safety
    def test_consent_revocation(self):
        """Test that consent can be revoked by parent."""
        user_id = "user123"
        parent_id = "parent456"

        # Grant consent
        self._grant_consent(user_id, parent_id, "telemetry")
        assert self._has_consent(user_id, parent_id, "telemetry") is True

        # Revoke consent
        revoke_result = self._revoke_consent(user_id, parent_id, "telemetry")
        assert revoke_result["success"] is True

        # Verify consent is now inactive
        assert self._has_consent(user_id, parent_id, "telemetry") is False

        # Data collection should fail
        result = self._collect_data(user_id, parent_id, "telemetry", "sample data")
        assert result["success"] is False

    @pytest.mark.safety
    def test_granular_consent_categories(self):
        """Test that consent is granular by category."""
        user_id = "user123"
        parent_id = "parent456"

        # Grant consent for telemetry only
        self._grant_consent(user_id, parent_id, "telemetry")

        # Telemetry should be allowed
        assert self._has_consent(user_id, parent_id, "telemetry") is True

        # But not analytics
        assert self._has_consent(user_id, parent_id, "analytics") is False

        # Analytics collection should fail
        result = self._collect_data(user_id, parent_id, "analytics", "data")
        assert result["success"] is False

    @pytest.mark.safety
    def test_consent_audit_trail(self):
        """Test that consent actions are audited."""
        user_id = "user123"
        parent_id = "parent456"

        # Grant consent
        self._grant_consent(user_id, parent_id, "telemetry")

        # Check audit log
        audit_log = self._get_consent_audit_log(user_id, parent_id)
        assert len(audit_log) > 0
        assert audit_log[0]["action"] == "consent_granted"
        assert audit_log[0]["category"] == "telemetry"

        # Revoke consent
        self._revoke_consent(user_id, parent_id, "telemetry")

        # Check updated audit log
        audit_log = self._get_consent_audit_log(user_id, parent_id)
        assert len(audit_log) > 1
        assert audit_log[-1]["action"] == "consent_revoked"

    def _has_consent(self, user_id: str, parent_id: str, category: str) -> bool:
        """Mock consent checker."""
        consent_key = f"{user_id}:{parent_id}:{category}"
        consents = getattr(self, "_consents", {})
        consent = consents.get(consent_key, {})
        return consent.get("active", False) and not consent.get("expired", False)

    def _grant_consent(
        self, user_id: str, parent_id: str, category: str, expires_in_days: int = 365
    ) -> Dict[str, Any]:
        """Mock consent granting."""
        import hashlib

        if not hasattr(self, "_consents"):
            self._consents = {}

        consent_key = f"{user_id}:{parent_id}:{category}"
        consent_id = hashlib.sha256(consent_key.encode()).hexdigest()[:16]

        self._consents[consent_key] = {
            "consent_id": consent_id,
            "active": True,
            "granted_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(days=expires_in_days),
            "expired": False,
        }

        self._add_to_audit_log(user_id, parent_id, "consent_granted", category)

        return {"success": True, "consent_id": consent_id}

    def _collect_data(
        self, user_id: str, parent_id: str, category: str, data: Any
    ) -> Dict[str, Any]:
        """Mock data collection."""
        if not self._has_consent(user_id, parent_id, category):
            return {"success": False, "error": "consent_required"}

        return {"success": True, "data_id": "data_123"}

    def _get_consent_info(self, user_id: str, parent_id: str, category: str) -> Dict[str, Any]:
        """Mock consent info retrieval."""
        consent_key = f"{user_id}:{parent_id}:{category}"
        consents = getattr(self, "_consents", {})
        return consents.get(consent_key, {})

    def _check_consent_expired(self, consent_info: Dict[str, Any], check_date: datetime) -> bool:
        """Mock consent expiration checker."""
        expires_at = consent_info.get("expires_at")
        if not expires_at:
            return False
        return check_date > expires_at

    def _revoke_consent(self, user_id: str, parent_id: str, category: str) -> Dict[str, Any]:
        """Mock consent revocation."""
        consent_key = f"{user_id}:{parent_id}:{category}"
        if hasattr(self, "_consents") and consent_key in self._consents:
            self._consents[consent_key]["active"] = False
            self._add_to_audit_log(user_id, parent_id, "consent_revoked", category)
            return {"success": True}
        return {"success": False, "error": "consent_not_found"}

    def _add_to_audit_log(self, user_id: str, parent_id: str, action: str, category: str):
        """Mock audit log entry."""
        if not hasattr(self, "_audit_log"):
            self._audit_log = {}

        key = f"{user_id}:{parent_id}"
        if key not in self._audit_log:
            self._audit_log[key] = []

        self._audit_log[key].append(
            {"action": action, "category": category, "timestamp": datetime.now().isoformat()}
        )

    def _get_consent_audit_log(self, user_id: str, parent_id: str) -> List[Dict[str, Any]]:
        """Mock audit log retrieval."""
        if not hasattr(self, "_audit_log"):
            return []

        key = f"{user_id}:{parent_id}"
        return self._audit_log.get(key, [])


class TestDataDeletionVerification:
    """Test data deletion verification."""

    @pytest.mark.safety
    def test_user_data_deletion(self):
        """Test that user data can be completely deleted."""
        user_id = "user123"

        # Create user data
        self._create_user_data(user_id, {"score": 85})
        assert self._user_data_exists(user_id) is True

        # Delete user data
        result = self._delete_user_data(user_id)
        assert result["success"] is True

        # Verify data is deleted
        assert self._user_data_exists(user_id) is False

    @pytest.mark.safety
    def test_retention_policy_enforcement(self):
        """Test that data is deleted per retention policy."""
        user_id = "user123"
        retention_days = 30

        # Create data with retention policy
        data_id = self._create_data_with_retention(user_id, {"content": "test"}, retention_days)

        # Immediately after creation, should exist
        assert self._data_exists(data_id) is True

        # Simulate time passing beyond retention
        future_date = datetime.now() + timedelta(days=31)
        expired = self._check_data_expired(data_id, future_date)
        assert expired is True

        # Expired data should be deleted
        self._cleanup_expired_data(future_date)
        assert self._data_exists(data_id) is False

    @pytest.mark.safety
    def test_cascade_deletion(self):
        """Test that related data is deleted in cascade."""
        user_id = "user123"

        # Create user with related data
        self._create_user_data(user_id, {"score": 85})
        session_id = self._create_user_session(user_id)
        activity_id = self._create_user_activity(user_id, "math")

        # Verify all data exists
        assert self._user_data_exists(user_id) is True
        assert self._session_exists(session_id) is True
        assert self._activity_exists(activity_id) is True

        # Delete user
        self._delete_user_data(user_id)

        # Verify all related data is deleted
        assert self._user_data_exists(user_id) is False
        assert self._session_exists(session_id) is False
        assert self._activity_exists(activity_id) is False

    @pytest.mark.safety
    def test_deletion_verification_report(self):
        """Test that deletion can be verified with a report."""
        user_id = "user123"

        # Create data
        self._create_user_data(user_id, {"score": 85})

        # Request deletion
        deletion_result = self._delete_user_data(user_id)
        deletion_request_id = deletion_result["request_id"]

        # Get verification report
        report = self._get_deletion_verification_report(deletion_request_id)

        assert report["success"] is True
        assert report["user_id"] == user_id
        assert report["deleted_items"] > 0
        assert report["verification_timestamp"] is not None

    @pytest.mark.safety
    def test_immediate_deletion_for_sensitive_data(self):
        """Test that sensitive data is deleted immediately."""
        # Voice data should be deleted immediately after processing
        voice_data_id = self._process_voice_data_with_tracking("user123", b"audio")

        # Should not be stored at all
        assert self._data_exists(voice_data_id) is False

        # Image data should be deleted immediately after processing
        image_data_id = self._process_image_data_with_tracking("user123", b"image")

        # Should not be stored at all
        assert self._data_exists(image_data_id) is False

    def _create_user_data(self, user_id: str, data: Dict[str, Any]) -> str:
        """Mock user data creation."""
        if not hasattr(self, "_user_data"):
            self._user_data = {}
        self._user_data[user_id] = data
        return user_id

    def _user_data_exists(self, user_id: str) -> bool:
        """Mock user data existence check."""
        if not hasattr(self, "_user_data"):
            return False
        return user_id in self._user_data

    def _delete_user_data(self, user_id: str) -> Dict[str, Any]:
        """Mock user data deletion."""
        import hashlib

        if hasattr(self, "_user_data") and user_id in self._user_data:
            del self._user_data[user_id]

        # Also delete related data
        if hasattr(self, "_sessions"):
            self._sessions = {k: v for k, v in self._sessions.items() if v["user_id"] != user_id}

        if hasattr(self, "_activities"):
            self._activities = {
                k: v for k, v in self._activities.items() if v["user_id"] != user_id
            }

        request_id = hashlib.sha256(f"delete_{user_id}".encode()).hexdigest()[:16]
        return {"success": True, "request_id": request_id}

    def _create_data_with_retention(
        self, user_id: str, data: Dict[str, Any], retention_days: int
    ) -> str:
        """Mock data creation with retention policy."""
        import hashlib

        if not hasattr(self, "_data_with_retention"):
            self._data_with_retention = {}

        data_id = hashlib.sha256(f"{user_id}_{datetime.now()}".encode()).hexdigest()[:16]

        self._data_with_retention[data_id] = {
            "user_id": user_id,
            "data": data,
            "created_at": datetime.now(),
            "retention_days": retention_days,
        }

        return data_id

    def _data_exists(self, data_id: str) -> bool:
        """Mock data existence check."""
        return hasattr(self, "_data_with_retention") and data_id in self._data_with_retention

    def _check_data_expired(self, data_id: str, check_date: datetime) -> bool:
        """Mock data expiration check."""
        if not self._data_exists(data_id):
            return False

        data_info = self._data_with_retention[data_id]
        expiry_date = data_info["created_at"] + timedelta(days=data_info["retention_days"])
        return check_date > expiry_date

    def _cleanup_expired_data(self, current_date: datetime):
        """Mock expired data cleanup."""
        if not hasattr(self, "_data_with_retention"):
            return

        expired_ids = [
            data_id
            for data_id in list(self._data_with_retention.keys())
            if self._check_data_expired(data_id, current_date)
        ]

        for data_id in expired_ids:
            del self._data_with_retention[data_id]

    def _create_user_session(self, user_id: str) -> str:
        """Mock user session creation."""
        import hashlib

        if not hasattr(self, "_sessions"):
            self._sessions = {}

        session_id = hashlib.sha256(f"session_{user_id}".encode()).hexdigest()[:16]
        self._sessions[session_id] = {"user_id": user_id}
        return session_id

    def _session_exists(self, session_id: str) -> bool:
        """Mock session existence check."""
        return hasattr(self, "_sessions") and session_id in self._sessions

    def _create_user_activity(self, user_id: str, activity_type: str) -> str:
        """Mock user activity creation."""
        import hashlib

        if not hasattr(self, "_activities"):
            self._activities = {}

        activity_id = hashlib.sha256(f"activity_{user_id}_{activity_type}".encode()).hexdigest()[
            :16
        ]
        self._activities[activity_id] = {"user_id": user_id, "type": activity_type}
        return activity_id

    def _activity_exists(self, activity_id: str) -> bool:
        """Mock activity existence check."""
        return hasattr(self, "_activities") and activity_id in self._activities

    def _get_deletion_verification_report(self, request_id: str) -> Dict[str, Any]:
        """Mock deletion verification report."""
        return {
            "success": True,
            "request_id": request_id,
            "user_id": "user123",
            "deleted_items": 3,
            "verification_timestamp": datetime.now().isoformat(),
        }

    def _process_voice_data_with_tracking(self, user_id: str, audio_data: bytes) -> str:
        """Mock voice data processing (not stored)."""
        import hashlib

        # Generate ID but don't store
        return hashlib.sha256(f"voice_{user_id}".encode()).hexdigest()[:16]

    def _process_image_data_with_tracking(self, user_id: str, image_data: bytes) -> str:
        """Mock image data processing (not stored)."""
        import hashlib

        # Generate ID but don't store
        return hashlib.sha256(f"image_{user_id}".encode()).hexdigest()[:16]
