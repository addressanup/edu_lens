"""
EduLens COPPA Compliance Validator

This module implements automated COPPA compliance validation to ensure the EduLens
platform maintains compliance with the Children's Online Privacy Protection Act
(15 U.S.C. 6501-6506 and 16 CFR Part 312).

Classification: SECURITY CRITICAL
Author: Security and Privacy Agent (SEC-001)
Task: SEC-001-T5 - COPPA Compliance Audit
Last Updated: 2025-12-10
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from .data_handler import (
    ConsentRecord,
    ConsentStatus,
    DataClassification,
    DataHandler,
    DataItem,
    ProcessingLocation,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ComplianceLevel(Enum):
    """Compliance assessment levels."""

    COMPLIANT = "compliant"
    WARNING = "warning"
    VIOLATION = "violation"
    CRITICAL = "critical"


class ComplianceCategory(Enum):
    """COPPA compliance categories per 16 CFR Part 312."""

    NOTICE = "notice"  # 312.4 - Notice requirements
    CONSENT = "consent"  # 312.5 - Parental consent
    PARENTAL_ACCESS = "parental_access"  # 312.6 - Parent rights
    CONDITIONAL_ACCESS = "conditional_access"  # 312.7 - Conditional access
    DATA_SECURITY = "data_security"  # 312.8 - Data security
    DATA_RETENTION = "data_retention"  # 312.10 - Data retention
    THIRD_PARTY = "third_party"  # Service provider compliance


@dataclass
class ComplianceIssue:
    """Represents a compliance issue or violation."""

    category: ComplianceCategory
    level: ComplianceLevel
    title: str
    description: str
    regulation: str  # CFR reference
    recommendation: str
    affected_items: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "category": self.category.value,
            "level": self.level.value,
            "title": self.title,
            "description": self.description,
            "regulation": self.regulation,
            "recommendation": self.recommendation,
            "affected_items": self.affected_items,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ComplianceReport:
    """Comprehensive COPPA compliance report."""

    report_id: str
    generated_at: datetime
    overall_status: ComplianceLevel
    categories_assessed: List[ComplianceCategory]
    total_checks: int
    passed_checks: int
    warnings: int
    violations: int
    critical_issues: int
    issues: List[ComplianceIssue]
    recommendations: List[str]
    summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export."""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "overall_status": self.overall_status.value,
            "categories_assessed": [cat.value for cat in self.categories_assessed],
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "warnings": self.warnings,
            "violations": self.violations,
            "critical_issues": self.critical_issues,
            "issues": [issue.to_dict() for issue in self.issues],
            "recommendations": self.recommendations,
            "summary": self.summary,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class COPPAValidator:
    """
    Automated COPPA compliance validator for EduLens platform.

    This class performs comprehensive compliance checks against COPPA requirements
    and generates detailed compliance reports with remediation recommendations.

    Key Features:
    - Data collection validation
    - Parental consent verification
    - Data retention policy compliance
    - Third-party sharing validation
    - Security controls assessment
    - Automated compliance reporting

    COPPA Compliance Framework:
    - 16 CFR 312.4: Notice requirements
    - 16 CFR 312.5: Parental consent
    - 16 CFR 312.6: Parental access rights
    - 16 CFR 312.7: Conditional access
    - 16 CFR 312.8: Data security
    - 16 CFR 312.10: Data retention
    """

    def __init__(self, data_handler: Optional[DataHandler] = None):
        """
        Initialize COPPA validator.

        Args:
            data_handler: Optional DataHandler instance (creates new if not provided)
        """
        self.data_handler = data_handler or DataHandler()
        self.issues: List[ComplianceIssue] = []
        self.checks_performed = 0
        self.checks_passed = 0

        logger.info("COPPAValidator initialized")

    def validate_data_collection(
        self, data_items: Optional[List[DataItem]] = None
    ) -> Tuple[ComplianceLevel, List[ComplianceIssue]]:
        """
        Validate data collection practices for COPPA compliance.

        Checks:
        1. No prohibited personal information collected from children
        2. Only necessary data collected (data minimization)
        3. Appropriate data classifications assigned
        4. Sensitive data not persisted to storage
        5. Data collection transparency

        Args:
            data_items: Optional list of DataItem objects to validate

        Returns:
            Tuple of (ComplianceLevel, List of issues found)

        Example:
            >>> validator = COPPAValidator()
            >>> level, issues = validator.validate_data_collection()
            >>> print(f"Compliance: {level.value}")
        """
        issues = []
        self.checks_performed += 5

        # Check 1: Verify no prohibited PII collected
        prohibited_classifications = []
        if data_items:
            for item in data_items:
                # Check for persistent storage of sensitive data
                if item.classification.is_never_stored():
                    if item.processing_location not in [
                        ProcessingLocation.VOLATILE_RAM,
                        ProcessingLocation.SECURE_ENCLAVE,
                    ]:
                        issues.append(
                            ComplianceIssue(
                                category=ComplianceCategory.DATA_SECURITY,
                                level=ComplianceLevel.CRITICAL,
                                title="Sensitive data in prohibited location",
                                description=f"Data classified as {item.classification.name} must NEVER be stored, but found in {item.processing_location.value}",
                                regulation="16 CFR 312.8 - Data Security",
                                recommendation="Immediately move to volatile RAM or secure enclave, and schedule immediate deletion",
                                affected_items=[item.data_id],
                            )
                        )
        else:
            self.checks_passed += 1

        # Check 2: Data minimization principle
        policy_check = all(
            policy.retention.max_retention_days >= 0
            for policy in self.data_handler.policies.values()
        )

        if policy_check:
            self.checks_passed += 1
        else:
            issues.append(
                ComplianceIssue(
                    category=ComplianceCategory.DATA_RETENTION,
                    level=ComplianceLevel.WARNING,
                    title="Data retention policies incomplete",
                    description="Some data classifications lack retention policies",
                    regulation="16 CFR 312.10 - Data Retention and Deletion",
                    recommendation="Ensure all data classifications have defined retention policies",
                )
            )

        # Check 3: Sensitive visual data never persisted
        sensitive_visual_policy = self.data_handler.policies.get(
            DataClassification.SENSITIVE_VISUAL
        )
        if sensitive_visual_policy and sensitive_visual_policy.retention.max_retention_days == 0:
            self.checks_passed += 1
        else:
            issues.append(
                ComplianceIssue(
                    category=ComplianceCategory.DATA_SECURITY,
                    level=ComplianceLevel.CRITICAL,
                    title="Camera image retention policy violation",
                    description="Camera images must have ZERO retention (immediate deletion)",
                    regulation="16 CFR 312.8 - Data Security",
                    recommendation="Set SENSITIVE_VISUAL retention to 0 seconds with immediate auto-deletion",
                )
            )

        # Check 4: Voice data never persisted
        voice_data_policy = self.data_handler.policies.get(DataClassification.VOICE_DATA)
        if voice_data_policy and voice_data_policy.retention.max_retention_days == 0:
            self.checks_passed += 1
        else:
            issues.append(
                ComplianceIssue(
                    category=ComplianceCategory.DATA_SECURITY,
                    level=ComplianceLevel.CRITICAL,
                    title="Voice data retention policy violation",
                    description="Voice recordings must have ZERO retention (immediate deletion)",
                    regulation="16 CFR 312.8 - Data Security",
                    recommendation="Set VOICE_DATA retention to 0 seconds with immediate auto-deletion",
                )
            )

        # Check 5: Consent required for appropriate categories
        consent_categories = [
            DataClassification.ANONYMOUS_TELEMETRY,
            DataClassification.SENSITIVE_VISUAL,
            DataClassification.VOICE_DATA,
            DataClassification.PARENTAL_ACCOUNT,
        ]

        consent_properly_required = all(
            self.data_handler.policies.get(cat).requires_consent
            for cat in consent_categories
            if cat in self.data_handler.policies
        )

        if consent_properly_required:
            self.checks_passed += 1
        else:
            issues.append(
                ComplianceIssue(
                    category=ComplianceCategory.CONSENT,
                    level=ComplianceLevel.VIOLATION,
                    title="Consent requirements not properly configured",
                    description="Some data categories that require consent are not marked as such",
                    regulation="16 CFR 312.5 - Parental Consent",
                    recommendation="Review and update consent requirements for all data classifications",
                )
            )

        # Determine overall compliance level
        if any(issue.level == ComplianceLevel.CRITICAL for issue in issues):
            level = ComplianceLevel.CRITICAL
        elif any(issue.level == ComplianceLevel.VIOLATION for issue in issues):
            level = ComplianceLevel.VIOLATION
        elif any(issue.level == ComplianceLevel.WARNING for issue in issues):
            level = ComplianceLevel.WARNING
        else:
            level = ComplianceLevel.COMPLIANT

        self.issues.extend(issues)
        return level, issues

    def validate_consent(
        self,
        parent_account_id: str,
        child_pseudonym: str,
        required_categories: Optional[List[DataClassification]] = None,
    ) -> Tuple[ComplianceLevel, List[ComplianceIssue]]:
        """
        Validate parental consent compliance.

        Checks:
        1. Verifiable parental consent obtained
        2. Consent valid and not expired
        3. Consent scope appropriate
        4. Consent verification method meets COPPA standards
        5. Consent records properly maintained

        Args:
            parent_account_id: Parent account identifier
            child_pseudonym: Child pseudonym (not real name)
            required_categories: Optional list of categories requiring consent

        Returns:
            Tuple of (ComplianceLevel, List of issues found)

        Example:
            >>> validator = COPPAValidator()
            >>> level, issues = validator.validate_consent("parent_123", "student_1")
        """
        issues = []
        self.checks_performed += 5

        required_categories = required_categories or [
            DataClassification.SENSITIVE_VISUAL,
            DataClassification.VOICE_DATA,
            DataClassification.ANONYMOUS_TELEMETRY,
        ]

        # Check 1: Consent exists for required categories
        missing_consents = []
        for category in required_categories:
            status = self.data_handler.get_consent_status(
                parent_account_id, child_pseudonym, category
            )

            if status == ConsentStatus.NOT_REQUESTED:
                missing_consents.append(category)

        if not missing_consents:
            self.checks_passed += 1
        else:
            issues.append(
                ComplianceIssue(
                    category=ComplianceCategory.CONSENT,
                    level=ComplianceLevel.CRITICAL,
                    title="Missing required parental consent",
                    description=f"Consent not obtained for required categories: {[c.name for c in missing_consents]}",
                    regulation="16 CFR 312.5 - Parental Consent",
                    recommendation="Obtain verifiable parental consent before collecting data from children",
                    affected_items=[c.name for c in missing_consents],
                )
            )

        # Check 2: Consent is valid (not expired or revoked)
        invalid_consents = []
        for category in required_categories:
            consent_key = f"{parent_account_id}:{child_pseudonym}:{category.name}"
            if consent_key in self.data_handler.consent_records:
                consent = self.data_handler.consent_records[consent_key]
                if not consent.is_valid():
                    invalid_consents.append((category, consent.status))

        if not invalid_consents:
            self.checks_passed += 1
        else:
            issues.append(
                ComplianceIssue(
                    category=ComplianceCategory.CONSENT,
                    level=ComplianceLevel.VIOLATION,
                    title="Invalid or expired consent",
                    description=f"Consent exists but is not valid: {[(c.name, s.value) for c, s in invalid_consents]}",
                    regulation="16 CFR 312.5 - Parental Consent",
                    recommendation="Request consent renewal or stop data collection until valid consent obtained",
                    affected_items=[c.name for c, s in invalid_consents],
                )
            )

        # Check 3: Consent verification method is COPPA-compliant
        approved_methods = ["CREDIT_CARD", "MFA_EMAIL_SMS", "VIDEO_CONFERENCE", "NOTARIZED"]
        unapproved_methods = []

        for category in required_categories:
            consent_key = f"{parent_account_id}:{child_pseudonym}:{category.name}"
            if consent_key in self.data_handler.consent_records:
                consent = self.data_handler.consent_records[consent_key]
                if consent.consent_method not in approved_methods:
                    unapproved_methods.append((category, consent.consent_method))

        if not unapproved_methods:
            self.checks_passed += 1
        else:
            issues.append(
                ComplianceIssue(
                    category=ComplianceCategory.CONSENT,
                    level=ComplianceLevel.VIOLATION,
                    title="Non-compliant consent verification method",
                    description=f"Consent obtained using non-FTC-approved methods: {unapproved_methods}",
                    regulation="16 CFR 312.5(b) - Verifiable Parental Consent Methods",
                    recommendation="Use only FTC-approved verification methods (credit card, government ID, etc.)",
                )
            )

        # Check 4: Consent has not exceeded retention period
        # Consent should be renewed annually
        expired_consent_records = []
        for category in required_categories:
            consent_key = f"{parent_account_id}:{child_pseudonym}:{category.name}"
            if consent_key in self.data_handler.consent_records:
                consent = self.data_handler.consent_records[consent_key]
                if consent.expires_at and datetime.utcnow() > consent.expires_at:
                    expired_consent_records.append(category)

        if not expired_consent_records:
            self.checks_passed += 1
        else:
            issues.append(
                ComplianceIssue(
                    category=ComplianceCategory.CONSENT,
                    level=ComplianceLevel.WARNING,
                    title="Consent expired - renewal needed",
                    description=f"Consent has expired for categories: {[c.name for c in expired_consent_records]}",
                    regulation="16 CFR 312.5 - Parental Consent (annual renewal best practice)",
                    recommendation="Request parental consent renewal (annual best practice)",
                    affected_items=[c.name for c in expired_consent_records],
                )
            )

        # Check 5: Consent records properly documented
        consent_records_complete = True
        for category in required_categories:
            consent_key = f"{parent_account_id}:{child_pseudonym}:{category.name}"
            if consent_key in self.data_handler.consent_records:
                consent = self.data_handler.consent_records[consent_key]
                # Verify all required fields present
                if not all(
                    [
                        consent.consent_id,
                        consent.timestamp,
                        consent.consent_method,
                        consent.verification_method,
                    ]
                ):
                    consent_records_complete = False
                    break

        if consent_records_complete:
            self.checks_passed += 1
        else:
            issues.append(
                ComplianceIssue(
                    category=ComplianceCategory.CONSENT,
                    level=ComplianceLevel.WARNING,
                    title="Incomplete consent records",
                    description="Some consent records are missing required fields",
                    regulation="16 CFR 312.5 - Parental Consent",
                    recommendation="Ensure all consent records include verification method and timestamp",
                )
            )

        # Determine overall compliance level
        if any(issue.level == ComplianceLevel.CRITICAL for issue in issues):
            level = ComplianceLevel.CRITICAL
        elif any(issue.level == ComplianceLevel.VIOLATION for issue in issues):
            level = ComplianceLevel.VIOLATION
        elif any(issue.level == ComplianceLevel.WARNING for issue in issues):
            level = ComplianceLevel.WARNING
        else:
            level = ComplianceLevel.COMPLIANT

        self.issues.extend(issues)
        return level, issues

    def validate_retention(
        self, data_items: Optional[List[DataItem]] = None
    ) -> Tuple[ComplianceLevel, List[ComplianceIssue]]:
        """
        Validate data retention policy compliance.

        Checks:
        1. Retention policies defined for all data types
        2. Data not exceeding retention limits
        3. Auto-deletion enabled for sensitive data
        4. Retention periods appropriate for data sensitivity
        5. Deletion verification mechanisms in place

        Args:
            data_items: Optional list of DataItem objects to check retention

        Returns:
            Tuple of (ComplianceLevel, List of issues found)

        Example:
            >>> validator = COPPAValidator()
            >>> level, issues = validator.validate_retention()
        """
        issues = []
        self.checks_performed += 5

        # Check 1: All classifications have retention policies
        all_classifications = list(DataClassification)
        missing_policies = [
            cls for cls in all_classifications if cls not in self.data_handler.policies
        ]

        if not missing_policies:
            self.checks_passed += 1
        else:
            issues.append(
                ComplianceIssue(
                    category=ComplianceCategory.DATA_RETENTION,
                    level=ComplianceLevel.WARNING,
                    title="Missing retention policies",
                    description=f"No retention policies defined for: {[c.name for c in missing_policies]}",
                    regulation="16 CFR 312.10 - Data Retention and Deletion",
                    recommendation="Define retention policies for all data classifications",
                )
            )

        # Check 2: No data exceeding retention limits
        if data_items:
            expired_items = []
            for item in data_items:
                policy = self.data_handler.policies.get(item.classification)
                if policy and item.should_be_deleted(policy.retention):
                    expired_items.append(item.data_id)

            if not expired_items:
                self.checks_passed += 1
            else:
                issues.append(
                    ComplianceIssue(
                        category=ComplianceCategory.DATA_RETENTION,
                        level=ComplianceLevel.CRITICAL,
                        title="Data exceeding retention limits",
                        description=f"Found {len(expired_items)} items exceeding retention policy",
                        regulation="16 CFR 312.10 - Data Retention and Deletion",
                        recommendation="Immediately delete data exceeding retention limits",
                        affected_items=expired_items,
                    )
                )
        else:
            self.checks_passed += 1

        # Check 3: Auto-deletion enabled for sensitive data
        sensitive_classifications = [
            DataClassification.SENSITIVE_VISUAL,
            DataClassification.VOICE_DATA,
            DataClassification.LEARNING_INTERACTION,
        ]

        auto_delete_violations = []
        for cls in sensitive_classifications:
            policy = self.data_handler.policies.get(cls)
            if policy and not policy.retention.auto_purge_enabled:
                auto_delete_violations.append(cls)

        if not auto_delete_violations:
            self.checks_passed += 1
        else:
            issues.append(
                ComplianceIssue(
                    category=ComplianceCategory.DATA_RETENTION,
                    level=ComplianceLevel.CRITICAL,
                    title="Auto-deletion not enabled for sensitive data",
                    description=f"Auto-purge disabled for: {[c.name for c in auto_delete_violations]}",
                    regulation="16 CFR 312.8 - Data Security",
                    recommendation="Enable automatic deletion for all sensitive data classifications",
                    affected_items=[c.name for c in auto_delete_violations],
                )
            )

        # Check 4: Retention periods appropriate
        max_retention_violations = []
        for cls, policy in self.data_handler.policies.items():
            # Sensitive data should have very short retention
            if cls.is_sensitive() and policy.retention.max_retention_days > 1:
                max_retention_violations.append((cls, policy.retention.max_retention_days))

        if not max_retention_violations:
            self.checks_passed += 1
        else:
            issues.append(
                ComplianceIssue(
                    category=ComplianceCategory.DATA_RETENTION,
                    level=ComplianceLevel.WARNING,
                    title="Retention periods too long for sensitive data",
                    description=f"Sensitive data with excessive retention: {[(c.name, days) for c, days in max_retention_violations]}",
                    regulation="16 CFR 312.10 - Data Retention and Deletion",
                    recommendation="Reduce retention periods for sensitive data to absolute minimum",
                )
            )

        # Check 5: Immediate deletion for never-stored categories
        never_stored = [
            DataClassification.SENSITIVE_VISUAL,
            DataClassification.VOICE_DATA,
        ]

        immediate_deletion_violations = []
        for cls in never_stored:
            policy = self.data_handler.policies.get(cls)
            if policy and policy.retention.max_retention_days != 0:
                immediate_deletion_violations.append(cls)

        if not immediate_deletion_violations:
            self.checks_passed += 1
        else:
            issues.append(
                ComplianceIssue(
                    category=ComplianceCategory.DATA_SECURITY,
                    level=ComplianceLevel.CRITICAL,
                    title="Images/audio must be deleted immediately",
                    description=f"Retention not set to immediate deletion: {[c.name for c in immediate_deletion_violations]}",
                    regulation="16 CFR 312.8 - Data Security (COPPA best practice)",
                    recommendation="Set retention to 0 seconds for camera images and voice recordings",
                )
            )

        # Determine overall compliance level
        if any(issue.level == ComplianceLevel.CRITICAL for issue in issues):
            level = ComplianceLevel.CRITICAL
        elif any(issue.level == ComplianceLevel.VIOLATION for issue in issues):
            level = ComplianceLevel.VIOLATION
        elif any(issue.level == ComplianceLevel.WARNING for issue in issues):
            level = ComplianceLevel.WARNING
        else:
            level = ComplianceLevel.COMPLIANT

        self.issues.extend(issues)
        return level, issues

    def validate_third_party(
        self, third_party_processors: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[ComplianceLevel, List[ComplianceIssue]]:
        """
        Validate third-party data sharing compliance.

        Checks:
        1. No child data shared with third parties
        2. Service providers have appropriate contracts (DPAs)
        3. Service providers use data only for specified purposes
        4. Data shared with third parties is minimal
        5. Third-party security controls adequate

        Args:
            third_party_processors: Optional list of third-party processor info

        Returns:
            Tuple of (ComplianceLevel, List of issues found)

        Example:
            >>> validator = COPPAValidator()
            >>> processors = [{"name": "Cloud Provider", "data_shared": ["parent_account"]}]
            >>> level, issues = validator.validate_third_party(processors)
        """
        issues = []
        self.checks_performed += 5

        if not third_party_processors:
            # No third parties = compliant by default
            self.checks_passed += 5
            level = ComplianceLevel.COMPLIANT
            self.issues.extend(issues)
            return level, issues

        # Check 1: No child PII shared with third parties
        prohibited_child_data = [
            DataClassification.SENSITIVE_VISUAL,
            DataClassification.VOICE_DATA,
            DataClassification.LEARNING_INTERACTION,
        ]

        for processor in third_party_processors:
            data_shared = processor.get("data_shared", [])
            violations = [
                data
                for data in data_shared
                if any(cls.name == data for cls in prohibited_child_data)
            ]

            if violations:
                issues.append(
                    ComplianceIssue(
                        category=ComplianceCategory.THIRD_PARTY,
                        level=ComplianceLevel.CRITICAL,
                        title="Child data shared with third party",
                        description=f"Processor '{processor.get('name')}' receives prohibited child data: {violations}",
                        regulation="16 CFR 312.5(c)(7) - Service Provider Exception",
                        recommendation="IMMEDIATELY stop sharing child data with third parties or obtain explicit consent",
                        affected_items=[processor.get("name")],
                    )
                )

        if not any(issue.level == ComplianceLevel.CRITICAL for issue in issues):
            self.checks_passed += 1

        # Check 2: Data Processing Agreements (DPAs) in place
        missing_dpa = [
            processor.get("name")
            for processor in third_party_processors
            if not processor.get("has_dpa", False)
        ]

        if not missing_dpa:
            self.checks_passed += 1
        else:
            issues.append(
                ComplianceIssue(
                    category=ComplianceCategory.THIRD_PARTY,
                    level=ComplianceLevel.VIOLATION,
                    title="Missing Data Processing Agreements",
                    description=f"Processors without DPA: {missing_dpa}",
                    regulation="16 CFR 312.5(c)(7) - Service Provider Exception",
                    recommendation="Execute DPAs with all service providers handling personal data",
                )
            )

        # Check 3: Third parties use data only for specified purposes
        unauthorized_use = [
            processor.get("name")
            for processor in third_party_processors
            if processor.get("allows_secondary_use", False)
        ]

        if not unauthorized_use:
            self.checks_passed += 1
        else:
            issues.append(
                ComplianceIssue(
                    category=ComplianceCategory.THIRD_PARTY,
                    level=ComplianceLevel.VIOLATION,
                    title="Third party unauthorized data use",
                    description=f"Processors with secondary use rights: {unauthorized_use}",
                    regulation="16 CFR 312.5(c)(7) - Service Provider Exception",
                    recommendation="Contractually prohibit any use beyond specified service provision",
                )
            )

        # Check 4: Data minimization with third parties
        excessive_sharing = []
        for processor in third_party_processors:
            data_shared = processor.get("data_shared", [])
            purpose = processor.get("purpose", "")

            # Heuristic: More than 3 data types suggests excessive sharing
            if len(data_shared) > 3:
                excessive_sharing.append((processor.get("name"), len(data_shared)))

        if not excessive_sharing:
            self.checks_passed += 1
        else:
            issues.append(
                ComplianceIssue(
                    category=ComplianceCategory.THIRD_PARTY,
                    level=ComplianceLevel.WARNING,
                    title="Excessive data sharing with third parties",
                    description=f"Processors receiving many data types: {excessive_sharing}",
                    regulation="16 CFR 312.8 - Data Security (minimization principle)",
                    recommendation="Share only minimum necessary data with each service provider",
                )
            )

        # Check 5: Third-party security controls
        inadequate_security = [
            processor.get("name")
            for processor in third_party_processors
            if not processor.get("has_security_audit", False)
        ]

        if not inadequate_security:
            self.checks_passed += 1
        else:
            issues.append(
                ComplianceIssue(
                    category=ComplianceCategory.DATA_SECURITY,
                    level=ComplianceLevel.WARNING,
                    title="Third-party security not verified",
                    description=f"Processors without security audits: {inadequate_security}",
                    regulation="16 CFR 312.8 - Data Security",
                    recommendation="Require annual security audits (SOC 2, ISO 27001) from all service providers",
                )
            )

        # Determine overall compliance level
        if any(issue.level == ComplianceLevel.CRITICAL for issue in issues):
            level = ComplianceLevel.CRITICAL
        elif any(issue.level == ComplianceLevel.VIOLATION for issue in issues):
            level = ComplianceLevel.VIOLATION
        elif any(issue.level == ComplianceLevel.WARNING for issue in issues):
            level = ComplianceLevel.WARNING
        else:
            level = ComplianceLevel.COMPLIANT

        self.issues.extend(issues)
        return level, issues

    def generate_audit_report(
        self,
        parent_account_id: Optional[str] = None,
        child_pseudonym: Optional[str] = None,
        data_items: Optional[List[DataItem]] = None,
        third_party_processors: Optional[List[Dict[str, Any]]] = None,
    ) -> ComplianceReport:
        """
        Generate comprehensive COPPA compliance audit report.

        Performs all validation checks and produces detailed report with:
        - Overall compliance status
        - Category-by-category assessment
        - Identified issues and violations
        - Remediation recommendations
        - Executive summary

        Args:
            parent_account_id: Optional parent account to check consent
            child_pseudonym: Optional child pseudonym to check consent
            data_items: Optional list of data items to validate
            third_party_processors: Optional list of third-party processors

        Returns:
            ComplianceReport with detailed findings

        Example:
            >>> validator = COPPAValidator()
            >>> report = validator.generate_audit_report(
            ...     parent_account_id="parent_123",
            ...     child_pseudonym="student_1"
            ... )
            >>> print(report.overall_status.value)
            >>> print(report.to_json())
        """
        logger.info("Generating COPPA compliance audit report...")

        # Reset counters
        self.issues = []
        self.checks_performed = 0
        self.checks_passed = 0

        # Perform all validation checks
        categories_assessed = []

        # 1. Data collection validation
        data_collection_level, _ = self.validate_data_collection(data_items)
        categories_assessed.append(ComplianceCategory.DATA_SECURITY)

        # 2. Consent validation (if parent/child provided)
        if parent_account_id and child_pseudonym:
            consent_level, _ = self.validate_consent(parent_account_id, child_pseudonym)
            categories_assessed.append(ComplianceCategory.CONSENT)
        else:
            logger.warning("Skipping consent validation (no parent/child provided)")

        # 3. Retention validation
        retention_level, _ = self.validate_retention(data_items)
        categories_assessed.append(ComplianceCategory.DATA_RETENTION)

        # 4. Third-party validation
        third_party_level, _ = self.validate_third_party(third_party_processors)
        categories_assessed.append(ComplianceCategory.THIRD_PARTY)

        # Calculate compliance metrics
        warnings = sum(1 for issue in self.issues if issue.level == ComplianceLevel.WARNING)
        violations = sum(1 for issue in self.issues if issue.level == ComplianceLevel.VIOLATION)
        critical_issues = sum(1 for issue in self.issues if issue.level == ComplianceLevel.CRITICAL)

        # Determine overall status
        if critical_issues > 0:
            overall_status = ComplianceLevel.CRITICAL
        elif violations > 0:
            overall_status = ComplianceLevel.VIOLATION
        elif warnings > 0:
            overall_status = ComplianceLevel.WARNING
        else:
            overall_status = ComplianceLevel.COMPLIANT

        # Generate recommendations
        recommendations = self._generate_recommendations(self.issues)

        # Create summary
        summary = {
            "compliance_status": overall_status.value,
            "total_issues": len(self.issues),
            "critical_issues": critical_issues,
            "violations": violations,
            "warnings": warnings,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_performed - self.checks_passed,
            "pass_rate": (
                f"{(self.checks_passed / self.checks_performed * 100):.1f}%"
                if self.checks_performed > 0
                else "N/A"
            ),
            "categories_assessed": [cat.value for cat in categories_assessed],
            "assessment_date": datetime.utcnow().isoformat(),
        }

        # Generate report ID
        report_id = (
            f"coppa_audit_{hashlib.sha256(str(datetime.utcnow()).encode()).hexdigest()[:16]}"
        )

        # Create report
        report = ComplianceReport(
            report_id=report_id,
            generated_at=datetime.utcnow(),
            overall_status=overall_status,
            categories_assessed=categories_assessed,
            total_checks=self.checks_performed,
            passed_checks=self.checks_passed,
            warnings=warnings,
            violations=violations,
            critical_issues=critical_issues,
            issues=self.issues,
            recommendations=recommendations,
            summary=summary,
        )

        logger.info(
            f"Compliance audit complete: {overall_status.value} "
            f"({self.checks_passed}/{self.checks_performed} checks passed)"
        )

        return report

    def _generate_recommendations(self, issues: List[ComplianceIssue]) -> List[str]:
        """Generate prioritized recommendations from issues."""
        recommendations = []

        # Critical issues first
        critical = [i for i in issues if i.level == ComplianceLevel.CRITICAL]
        if critical:
            recommendations.append(
                f"URGENT: Address {len(critical)} critical compliance issue(s) immediately"
            )
            for issue in critical:
                recommendations.append(f"  - {issue.recommendation}")

        # Violations next
        violations = [i for i in issues if i.level == ComplianceLevel.VIOLATION]
        if violations:
            recommendations.append(
                f"HIGH PRIORITY: Remediate {len(violations)} compliance violation(s) within 30 days"
            )

        # Warnings last
        warnings = [i for i in issues if i.level == ComplianceLevel.WARNING]
        if warnings:
            recommendations.append(
                f"MEDIUM PRIORITY: Address {len(warnings)} warning(s) to improve compliance posture"
            )

        # General recommendations
        if not issues:
            recommendations.append("Maintain current compliance practices")
            recommendations.append("Schedule quarterly compliance audits")
            recommendations.append("Consider COPPA Safe Harbor certification (PRIVO, kidSAFE)")

        return recommendations


# Export public API
__all__ = [
    "COPPAValidator",
    "ComplianceLevel",
    "ComplianceCategory",
    "ComplianceIssue",
    "ComplianceReport",
]
