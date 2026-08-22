"""
COPPA Compliance Test Suite

Comprehensive tests for COPPA compliance validation in the EduLens platform.
Tests cover data collection, parental consent, retention policies, and third-party
data sharing to ensure full compliance with 16 CFR Part 312.

Classification: SECURITY CRITICAL
Author: Security and Privacy Agent (SEC-001)
Task: SEC-001-T5 - COPPA Compliance Audit
Last Updated: 2025-12-10
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

from src.privacy.coppa_validator import (
    ComplianceCategory,
    ComplianceIssue,
    ComplianceLevel,
    ComplianceReport,
    COPPAValidator,
)
from src.privacy.data_handler import (
    ConsentRecord,
    ConsentStatus,
    DataClassification,
    DataHandler,
    DataItem,
    ProcessingLocation,
)


class TestDataCollectionValidation:
    """Test suite for data collection compliance validation."""

    def test_no_prohibited_data_collection(self):
        """Test that no prohibited child PII is collected."""
        validator = COPPAValidator()

        # Create compliant data items
        data_items = [
            DataItem(
                data_id="item_1",
                classification=DataClassification.EDUCATIONAL_CONTENT,
                content="Math problem: 2 + 2 = ?",
                created_at=datetime.utcnow(),
                processing_location=ProcessingLocation.EDGE_DEVICE,
                consent_verified=False,
            )
        ]

        level, issues = validator.validate_data_collection(data_items)

        # Should be compliant
        assert level in [ComplianceLevel.COMPLIANT, ComplianceLevel.WARNING]
        # Should not have critical issues
        critical_issues = [i for i in issues if i.level == ComplianceLevel.CRITICAL]
        assert len(critical_issues) == 0

    def test_sensitive_visual_data_not_stored(self):
        """Test that sensitive visual data (images) is never stored."""
        validator = COPPAValidator()

        # This should trigger a CRITICAL issue
        data_items = [
            DataItem(
                data_id="image_1",
                classification=DataClassification.SENSITIVE_VISUAL,
                content=b"fake_image_bytes",
                created_at=datetime.utcnow(),
                processing_location=ProcessingLocation.CLOUD_STORAGE,  # VIOLATION
                consent_verified=True,
            )
        ]

        level, issues = validator.validate_data_collection(data_items)

        # Should be CRITICAL violation
        assert level == ComplianceLevel.CRITICAL
        assert any(issue.category == ComplianceCategory.DATA_SECURITY for issue in issues)
        assert any("prohibited location" in issue.description.lower() for issue in issues)

    def test_voice_data_not_stored(self):
        """Test that voice data is never stored."""
        validator = COPPAValidator()

        # This should trigger a CRITICAL issue
        data_items = [
            DataItem(
                data_id="audio_1",
                classification=DataClassification.VOICE_DATA,
                content=b"fake_audio_bytes",
                created_at=datetime.utcnow(),
                processing_location=ProcessingLocation.CLOUD_STORAGE,  # VIOLATION
                consent_verified=True,
            )
        ]

        level, issues = validator.validate_data_collection(data_items)

        # Should be CRITICAL violation
        assert level == ComplianceLevel.CRITICAL

    def test_sensitive_data_in_volatile_ram_compliant(self):
        """Test that sensitive data in volatile RAM is compliant."""
        validator = COPPAValidator()

        data_items = [
            DataItem(
                data_id="image_1",
                classification=DataClassification.SENSITIVE_VISUAL,
                content=b"fake_image_bytes",
                created_at=datetime.utcnow(),
                processing_location=ProcessingLocation.VOLATILE_RAM,  # COMPLIANT
                consent_verified=True,
            ),
            DataItem(
                data_id="audio_1",
                classification=DataClassification.VOICE_DATA,
                content=b"fake_audio_bytes",
                created_at=datetime.utcnow(),
                processing_location=ProcessingLocation.SECURE_ENCLAVE,  # COMPLIANT
                consent_verified=True,
            ),
        ]

        level, issues = validator.validate_data_collection(data_items)

        # Should be compliant or have only warnings
        assert level in [ComplianceLevel.COMPLIANT, ComplianceLevel.WARNING]

    def test_data_minimization_principle(self):
        """Test that data minimization principles are enforced."""
        validator = COPPAValidator()
        level, issues = validator.validate_data_collection()

        # All data classifications should have retention policies
        assert validator.data_handler.policies is not None
        assert len(validator.data_handler.policies) > 0


class TestConsentValidation:
    """Test suite for parental consent compliance validation."""

    def test_missing_consent_critical(self):
        """Test that missing required consent is a critical issue."""
        handler = DataHandler()
        validator = COPPAValidator(handler)

        level, issues = validator.validate_consent(
            parent_account_id="parent_123",
            child_pseudonym="student_1",
            required_categories=[DataClassification.SENSITIVE_VISUAL],
        )

        # Should be CRITICAL (no consent provided)
        assert level == ComplianceLevel.CRITICAL
        assert any(
            "missing required parental consent" in issue.description.lower() for issue in issues
        )

    def test_valid_consent_compliant(self):
        """Test that valid parental consent passes validation."""
        handler = DataHandler()

        # Grant consent
        handler.grant_consent(
            parent_account_id="parent_123",
            child_pseudonym="student_1",
            category=DataClassification.SENSITIVE_VISUAL,
            consent_method="CREDIT_CARD",
            verification_method="STRIPE_VERIFICATION",
        )

        validator = COPPAValidator(handler)
        level, issues = validator.validate_consent(
            parent_account_id="parent_123",
            child_pseudonym="student_1",
            required_categories=[DataClassification.SENSITIVE_VISUAL],
        )

        # Should be COMPLIANT
        assert level == ComplianceLevel.COMPLIANT

    def test_expired_consent_violation(self):
        """Test that expired consent is detected as violation."""
        handler = DataHandler()

        # Create expired consent
        consent_id = handler._generate_consent_id(
            "parent_123", "student_1", DataClassification.SENSITIVE_VISUAL
        )

        expired_consent = ConsentRecord(
            consent_id=consent_id,
            parent_account_id="parent_123",
            child_pseudonym="student_1",
            category=DataClassification.SENSITIVE_VISUAL,
            status=ConsentStatus.GRANTED,
            timestamp=datetime.utcnow() - timedelta(days=400),  # Expired
            consent_method="CREDIT_CARD",
            verification_method="STRIPE_VERIFICATION",
            expires_at=datetime.utcnow() - timedelta(days=35),  # Expired 35 days ago
        )

        consent_key = f"parent_123:student_1:{DataClassification.SENSITIVE_VISUAL.name}"
        handler.consent_records[consent_key] = expired_consent

        validator = COPPAValidator(handler)
        level, issues = validator.validate_consent(
            parent_account_id="parent_123",
            child_pseudonym="student_1",
            required_categories=[DataClassification.SENSITIVE_VISUAL],
        )

        # Should detect expiration
        assert level in [ComplianceLevel.VIOLATION, ComplianceLevel.WARNING]

    def test_revoked_consent_violation(self):
        """Test that revoked consent prevents data collection."""
        handler = DataHandler()

        # Grant then revoke consent
        handler.grant_consent(
            parent_account_id="parent_123",
            child_pseudonym="student_1",
            category=DataClassification.SENSITIVE_VISUAL,
            consent_method="CREDIT_CARD",
            verification_method="STRIPE_VERIFICATION",
        )

        handler.revoke_consent(
            parent_account_id="parent_123",
            child_pseudonym="student_1",
            category=DataClassification.SENSITIVE_VISUAL,
        )

        validator = COPPAValidator(handler)
        level, issues = validator.validate_consent(
            parent_account_id="parent_123",
            child_pseudonym="student_1",
            required_categories=[DataClassification.SENSITIVE_VISUAL],
        )

        # Should detect revocation
        assert level in [ComplianceLevel.VIOLATION, ComplianceLevel.CRITICAL]

    def test_unapproved_verification_method(self):
        """Test that non-FTC-approved verification methods are flagged."""
        handler = DataHandler()

        # Create consent with unapproved method
        consent_id = handler._generate_consent_id(
            "parent_123", "student_1", DataClassification.SENSITIVE_VISUAL
        )

        consent = ConsentRecord(
            consent_id=consent_id,
            parent_account_id="parent_123",
            child_pseudonym="student_1",
            category=DataClassification.SENSITIVE_VISUAL,
            status=ConsentStatus.GRANTED,
            timestamp=datetime.utcnow(),
            consent_method="EMAIL_ONLY",  # NOT FTC-approved
            verification_method="SIMPLE_EMAIL",
            expires_at=datetime.utcnow() + timedelta(days=365),
        )

        consent_key = f"parent_123:student_1:{DataClassification.SENSITIVE_VISUAL.name}"
        handler.consent_records[consent_key] = consent

        validator = COPPAValidator(handler)
        level, issues = validator.validate_consent(
            parent_account_id="parent_123",
            child_pseudonym="student_1",
            required_categories=[DataClassification.SENSITIVE_VISUAL],
        )

        # Should flag non-compliant method
        assert level == ComplianceLevel.VIOLATION
        assert any("non-compliant" in issue.title.lower() for issue in issues)


class TestRetentionValidation:
    """Test suite for data retention compliance validation."""

    def test_immediate_deletion_sensitive_data(self):
        """Test that sensitive data has immediate deletion policy."""
        validator = COPPAValidator()
        level, issues = validator.validate_retention()

        # Check that SENSITIVE_VISUAL has 0 retention
        handler = validator.data_handler
        visual_policy = handler.policies.get(DataClassification.SENSITIVE_VISUAL)
        assert visual_policy is not None
        assert visual_policy.retention.max_retention_days == 0

        # Check that VOICE_DATA has 0 retention
        voice_policy = handler.policies.get(DataClassification.VOICE_DATA)
        assert voice_policy is not None
        assert voice_policy.retention.max_retention_days == 0

    def test_auto_deletion_enabled_sensitive_data(self):
        """Test that auto-deletion is enabled for sensitive data."""
        validator = COPPAValidator()
        level, issues = validator.validate_retention()

        handler = validator.data_handler

        # Check auto-purge enabled for sensitive classifications
        sensitive = [
            DataClassification.SENSITIVE_VISUAL,
            DataClassification.VOICE_DATA,
            DataClassification.LEARNING_INTERACTION,
        ]

        for cls in sensitive:
            policy = handler.policies.get(cls)
            if policy:
                assert policy.retention.auto_purge_enabled

    def test_data_exceeding_retention_flagged(self):
        """Test that data exceeding retention limits is flagged."""
        handler = DataHandler()

        # Create expired data item
        old_data = DataItem(
            data_id="old_item",
            classification=DataClassification.DEVICE_METADATA,
            content={"device": "test"},
            created_at=datetime.utcnow() - timedelta(days=400),  # Exceeds 365-day policy
            processing_location=ProcessingLocation.EDGE_DEVICE,
        )

        validator = COPPAValidator(handler)
        level, issues = validator.validate_retention(data_items=[old_data])

        # Should detect retention violation
        assert level == ComplianceLevel.CRITICAL
        assert any("exceeding retention" in issue.description.lower() for issue in issues)

    def test_retention_policies_defined_all_classifications(self):
        """Test that all data classifications have retention policies."""
        validator = COPPAValidator()
        level, issues = validator.validate_retention()

        # All major classifications should have policies
        handler = validator.data_handler
        important_classifications = [
            DataClassification.SENSITIVE_VISUAL,
            DataClassification.VOICE_DATA,
            DataClassification.LEARNING_INTERACTION,
            DataClassification.DEVICE_METADATA,
            DataClassification.PARENTAL_ACCOUNT,
            DataClassification.CONSENT_METADATA,
        ]

        for cls in important_classifications:
            assert cls in handler.policies, f"Missing policy for {cls.name}"


class TestThirdPartyValidation:
    """Test suite for third-party data sharing compliance validation."""

    def test_no_child_data_shared_compliant(self):
        """Test that no child data sharing is compliant."""
        validator = COPPAValidator()

        # Compliant processors (only parent data)
        processors = [
            {
                "name": "Cloud Provider",
                "data_shared": ["PARENTAL_ACCOUNT"],
                "has_dpa": True,
                "allows_secondary_use": False,
                "has_security_audit": True,
            }
        ]

        level, issues = validator.validate_third_party(processors)

        # Should be compliant
        assert level == ComplianceLevel.COMPLIANT

    def test_child_data_shared_critical(self):
        """Test that sharing child data with third parties is critical."""
        validator = COPPAValidator()

        # Violation: Sharing child images
        processors = [
            {
                "name": "Analytics Provider",
                "data_shared": ["SENSITIVE_VISUAL", "VOICE_DATA"],  # VIOLATION
                "has_dpa": True,
                "allows_secondary_use": False,
                "has_security_audit": True,
            }
        ]

        level, issues = validator.validate_third_party(processors)

        # Should be CRITICAL
        assert level == ComplianceLevel.CRITICAL
        assert any("child data shared" in issue.title.lower() for issue in issues)

    def test_missing_dpa_violation(self):
        """Test that missing DPA is a violation."""
        validator = COPPAValidator()

        processors = [
            {
                "name": "Cloud Provider",
                "data_shared": ["PARENTAL_ACCOUNT"],
                "has_dpa": False,  # VIOLATION
                "allows_secondary_use": False,
                "has_security_audit": True,
            }
        ]

        level, issues = validator.validate_third_party(processors)

        # Should be VIOLATION
        assert level == ComplianceLevel.VIOLATION
        assert any("data processing agreement" in issue.title.lower() for issue in issues)

    def test_secondary_use_violation(self):
        """Test that allowing secondary data use is a violation."""
        validator = COPPAValidator()

        processors = [
            {
                "name": "Analytics Provider",
                "data_shared": ["ANONYMOUS_TELEMETRY"],
                "has_dpa": True,
                "allows_secondary_use": True,  # VIOLATION
                "has_security_audit": True,
            }
        ]

        level, issues = validator.validate_third_party(processors)

        # Should be VIOLATION
        assert level == ComplianceLevel.VIOLATION
        assert any("unauthorized" in issue.description.lower() for issue in issues)

    def test_no_third_parties_compliant(self):
        """Test that no third parties is compliant by default."""
        validator = COPPAValidator()
        level, issues = validator.validate_third_party(third_party_processors=None)

        # Should be COMPLIANT
        assert level == ComplianceLevel.COMPLIANT
        assert len(issues) == 0


class TestComplianceReportGeneration:
    """Test suite for compliance report generation."""

    def test_generate_full_audit_report(self):
        """Test generation of comprehensive audit report."""
        handler = DataHandler()

        # Setup test scenario with consent
        handler.grant_consent(
            parent_account_id="parent_123",
            child_pseudonym="student_1",
            category=DataClassification.SENSITIVE_VISUAL,
            consent_method="CREDIT_CARD",
            verification_method="STRIPE_VERIFICATION",
        )

        validator = COPPAValidator(handler)
        report = validator.generate_audit_report(
            parent_account_id="parent_123", child_pseudonym="student_1"
        )

        # Validate report structure
        assert isinstance(report, ComplianceReport)
        assert report.report_id is not None
        assert report.generated_at is not None
        assert report.overall_status is not None
        assert report.total_checks > 0
        assert report.passed_checks >= 0
        assert len(report.categories_assessed) > 0
        assert isinstance(report.summary, dict)

    def test_report_json_export(self):
        """Test that report can be exported to JSON."""
        validator = COPPAValidator()
        report = validator.generate_audit_report()

        # Should be able to convert to JSON
        json_str = report.to_json()
        assert json_str is not None
        assert len(json_str) > 0

        # Should be valid JSON
        import json

        parsed = json.loads(json_str)
        assert "report_id" in parsed
        assert "overall_status" in parsed

    def test_report_identifies_critical_issues(self):
        """Test that report correctly identifies critical issues."""
        handler = DataHandler()

        # Create data item that violates policy (stored sensitive data)
        violation_item = DataItem(
            data_id="violation_1",
            classification=DataClassification.SENSITIVE_VISUAL,
            content=b"image_bytes",
            created_at=datetime.utcnow(),
            processing_location=ProcessingLocation.CLOUD_STORAGE,  # VIOLATION
        )

        validator = COPPAValidator(handler)
        report = validator.generate_audit_report(data_items=[violation_item])

        # Should identify critical issue
        assert report.critical_issues > 0
        assert report.overall_status == ComplianceLevel.CRITICAL

    def test_report_generates_recommendations(self):
        """Test that report generates actionable recommendations."""
        validator = COPPAValidator()
        report = validator.generate_audit_report()

        # Should have recommendations
        assert len(report.recommendations) > 0
        assert isinstance(report.recommendations, list)

    def test_compliant_scenario_passes(self):
        """Test that fully compliant scenario passes audit."""
        handler = DataHandler()

        # Grant all required consents
        handler.grant_consent(
            parent_account_id="parent_123",
            child_pseudonym="student_1",
            category=DataClassification.SENSITIVE_VISUAL,
            consent_method="CREDIT_CARD",
            verification_method="STRIPE_VERIFICATION",
        )

        handler.grant_consent(
            parent_account_id="parent_123",
            child_pseudonym="student_1",
            category=DataClassification.VOICE_DATA,
            consent_method="CREDIT_CARD",
            verification_method="STRIPE_VERIFICATION",
        )

        # Create compliant data items
        compliant_items = [
            DataItem(
                data_id="item_1",
                classification=DataClassification.EDUCATIONAL_CONTENT,
                content="Math content",
                created_at=datetime.utcnow(),
                processing_location=ProcessingLocation.EDGE_DEVICE,
            )
        ]

        validator = COPPAValidator(handler)
        report = validator.generate_audit_report(
            parent_account_id="parent_123", child_pseudonym="student_1", data_items=compliant_items
        )

        # Should be compliant or have only warnings
        assert report.overall_status in [ComplianceLevel.COMPLIANT, ComplianceLevel.WARNING]
        assert report.critical_issues == 0


class TestComplianceIssue:
    """Test suite for ComplianceIssue data structure."""

    def test_issue_creation(self):
        """Test creating compliance issue."""
        issue = ComplianceIssue(
            category=ComplianceCategory.CONSENT,
            level=ComplianceLevel.VIOLATION,
            title="Missing consent",
            description="Parental consent not obtained",
            regulation="16 CFR 312.5",
            recommendation="Obtain verifiable parental consent",
        )

        assert issue.category == ComplianceCategory.CONSENT
        assert issue.level == ComplianceLevel.VIOLATION
        assert issue.title == "Missing consent"

    def test_issue_to_dict(self):
        """Test converting issue to dictionary."""
        issue = ComplianceIssue(
            category=ComplianceCategory.DATA_SECURITY,
            level=ComplianceLevel.CRITICAL,
            title="Data stored in wrong location",
            description="Sensitive data found in cloud storage",
            regulation="16 CFR 312.8",
            recommendation="Move to volatile RAM immediately",
        )

        issue_dict = issue.to_dict()

        assert isinstance(issue_dict, dict)
        assert "category" in issue_dict
        assert "level" in issue_dict
        assert issue_dict["level"] == "critical"


class TestIntegration:
    """Integration tests for COPPA compliance system."""

    def test_end_to_end_compliance_check(self):
        """Test complete compliance check workflow."""
        # Initialize components
        handler = DataHandler()
        validator = COPPAValidator(handler)

        # Setup compliant scenario
        # 1. Grant parental consent
        handler.grant_consent(
            parent_account_id="parent_123",
            child_pseudonym="student_1",
            category=DataClassification.SENSITIVE_VISUAL,
            consent_method="CREDIT_CARD",
            verification_method="STRIPE_VERIFICATION",
        )

        # 2. Create compliant data
        data_items = [
            DataItem(
                data_id="item_1",
                classification=DataClassification.SENSITIVE_VISUAL,
                content=b"image_bytes",
                created_at=datetime.utcnow(),
                processing_location=ProcessingLocation.VOLATILE_RAM,  # Compliant
                consent_verified=True,
            )
        ]

        # 3. Define compliant third parties
        processors = [
            {
                "name": "Cloud Provider",
                "data_shared": ["PARENTAL_ACCOUNT"],  # No child data
                "has_dpa": True,
                "allows_secondary_use": False,
                "has_security_audit": True,
            }
        ]

        # 4. Generate audit report
        report = validator.generate_audit_report(
            parent_account_id="parent_123",
            child_pseudonym="student_1",
            data_items=data_items,
            third_party_processors=processors,
        )

        # Should pass compliance
        assert report.overall_status in [ComplianceLevel.COMPLIANT, ComplianceLevel.WARNING]

    def test_data_handler_coppa_validator_integration(self):
        """Test integration between DataHandler and COPPAValidator."""
        handler = DataHandler()
        validator = COPPAValidator(handler)

        # Validator should use same handler instance
        assert validator.data_handler is handler

        # Handler policies should be available to validator
        assert len(validator.data_handler.policies) > 0


# Pytest fixtures
@pytest.fixture
def data_handler():
    """Provide clean DataHandler instance for tests."""
    return DataHandler()


@pytest.fixture
def coppa_validator(data_handler):
    """Provide COPPAValidator with DataHandler."""
    return COPPAValidator(data_handler)


@pytest.fixture
def sample_data_items():
    """Provide sample data items for testing."""
    return [
        DataItem(
            data_id="item_1",
            classification=DataClassification.EDUCATIONAL_CONTENT,
            content="Sample content",
            created_at=datetime.utcnow(),
            processing_location=ProcessingLocation.EDGE_DEVICE,
        )
    ]


@pytest.fixture
def sample_processors():
    """Provide sample third-party processors for testing."""
    return [
        {
            "name": "Cloud Provider",
            "data_shared": ["PARENTAL_ACCOUNT"],
            "has_dpa": True,
            "allows_secondary_use": False,
            "has_security_audit": True,
        }
    ]


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
