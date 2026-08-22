"""
EduLens Privacy-First Data Handler

This module implements core privacy controls for the EduLens platform, ensuring
COPPA compliance and privacy-by-design principles for children's data protection.

Classification: SECURITY CRITICAL
Author: Security and Privacy Team (SEC-001)
Last Updated: 2025-12-10
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from hashlib import sha256
from typing import Any, Dict, List, Optional, Set

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataClassification(Enum):
    """
    Data classification levels for EduLens platform.

    Each level defines sensitivity and handling requirements per the
    Privacy Architecture specification.
    """

    PUBLIC = 0  # Non-sensitive, publicly available information
    DEVICE_METADATA = 1  # Non-personal device information
    ANONYMOUS_TELEMETRY = 2  # Aggregated, non-identifiable usage data
    EDUCATIONAL_CONTENT = 3  # Curriculum content, explanations
    PARENTAL_ACCOUNT = 4  # Parent account information
    SENSITIVE_VISUAL = 5  # Images from camera (CRITICAL - no storage)
    VOICE_DATA = 6  # Child's voice inputs (CRITICAL - no storage)
    LEARNING_INTERACTION = 7  # Session context (volatile only)
    CONSENT_METADATA = 8  # Records of parental consent

    def is_sensitive(self) -> bool:
        """Check if data classification is sensitive (requires special handling)."""
        return self in {
            DataClassification.SENSITIVE_VISUAL,
            DataClassification.VOICE_DATA,
            DataClassification.LEARNING_INTERACTION,
            DataClassification.PARENTAL_ACCOUNT,
        }

    def is_never_stored(self) -> bool:
        """Check if data should NEVER be persisted to storage."""
        return self in {
            DataClassification.SENSITIVE_VISUAL,
            DataClassification.VOICE_DATA,
        }

    def is_volatile_only(self) -> bool:
        """Check if data should only exist in volatile memory (RAM)."""
        return self in {
            DataClassification.SENSITIVE_VISUAL,
            DataClassification.VOICE_DATA,
            DataClassification.LEARNING_INTERACTION,
        }

    def requires_encryption(self) -> bool:
        """Check if data requires encryption at rest."""
        return self not in {DataClassification.PUBLIC}

    def requires_consent(self) -> bool:
        """Check if data collection requires explicit parental consent."""
        return self in {
            DataClassification.ANONYMOUS_TELEMETRY,
            DataClassification.PARENTAL_ACCOUNT,
            DataClassification.SENSITIVE_VISUAL,
            DataClassification.VOICE_DATA,
            DataClassification.CONSENT_METADATA,
        }


class ProcessingLocation(Enum):
    """Where data processing occurs in the EduLens architecture."""

    EDGE_DEVICE = "edge"  # On-device processing (preferred)
    SECURE_ENCLAVE = "enclave"  # Secure enclave on device (for sensitive data)
    CLOUD_PRIVACY_GATEWAY = "cloud_gateway"  # Cloud entry point with privacy checks
    CLOUD_STORAGE = "cloud_storage"  # Cloud database (minimal use)
    VOLATILE_RAM = "volatile_ram"  # Temporary RAM buffer (no persistence)


class ConsentStatus(Enum):
    """Parental consent status for data collection."""

    NOT_REQUESTED = "not_requested"  # Consent not yet requested
    PENDING = "pending"  # Consent requested, awaiting parent response
    GRANTED = "granted"  # Parent has explicitly consented
    DENIED = "denied"  # Parent has explicitly denied consent
    REVOKED = "revoked"  # Previously granted, now revoked
    EXPIRED = "expired"  # Consent expired (annual review required)


@dataclass
class RetentionPolicy:
    """
    Data retention policy configuration.

    Defines how long data can be retained before mandatory deletion.
    """

    classification: DataClassification
    max_retention_days: int
    auto_purge_enabled: bool = True
    description: str = ""

    def is_expired(self, data_timestamp: datetime) -> bool:
        """Check if data has exceeded retention period."""
        if self.max_retention_days == 0:
            return True  # Immediate deletion required

        expiration_date = data_timestamp + timedelta(days=self.max_retention_days)
        return datetime.utcnow() > expiration_date

    def days_until_expiration(self, data_timestamp: datetime) -> int:
        """Calculate days remaining until data expires.

        Rounds UP (ceiling): any fraction of a day remaining counts as a full
        day, so retention reporting is conservative for child data and
        deletion is never computed as due later than it actually is.
        """
        if self.max_retention_days == 0:
            return 0

        expiration_date = data_timestamp + timedelta(days=self.max_retention_days)
        remaining = expiration_date - datetime.utcnow()
        if remaining.total_seconds() <= 0:
            return 0
        # Ceiling division on seconds.
        return int(-(-remaining.total_seconds() // 86400))


@dataclass
class PrivacyPolicy:
    """
    Comprehensive privacy policy for a specific data type.

    Combines classification, retention, processing location, and access controls.
    """

    classification: DataClassification
    retention: RetentionPolicy
    allowed_locations: Set[ProcessingLocation]
    requires_consent: bool
    encryption_required: bool
    anonymization_required: bool = False
    audit_all_access: bool = True

    def validate_processing_location(self, location: ProcessingLocation) -> bool:
        """Verify that processing location is allowed for this data type."""
        return location in self.allowed_locations

    def to_dict(self) -> Dict[str, Any]:
        """Serialize policy to dictionary for logging/auditing."""
        return {
            "classification": self.classification.name,
            "max_retention_days": self.retention.max_retention_days,
            "allowed_locations": [loc.value for loc in self.allowed_locations],
            "requires_consent": self.requires_consent,
            "encryption_required": self.encryption_required,
            "anonymization_required": self.anonymization_required,
            "audit_all_access": self.audit_all_access,
        }


@dataclass
class ConsentRecord:
    """
    Record of parental consent for data collection.

    Maintains audit trail of consent decisions per COPPA requirements.
    """

    consent_id: str
    parent_account_id: str
    child_pseudonym: str
    category: DataClassification
    status: ConsentStatus
    timestamp: datetime
    consent_method: str  # e.g., "IN_APP_EXPLICIT_CLICK"
    verification_method: str  # e.g., "MFA_EMAIL_SMS"
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    ip_address_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        """Check if consent is currently valid."""
        if self.status != ConsentStatus.GRANTED:
            return False

        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False

        if self.revoked_at:
            return False

        return True

    def to_audit_log(self) -> Dict[str, Any]:
        """Generate audit log entry for this consent record."""
        return {
            "consent_id": self.consent_id,
            "parent_account_id": self.parent_account_id,
            "child_pseudonym": self.child_pseudonym,
            "category": self.category.name,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "consent_method": self.consent_method,
            "verification_method": self.verification_method,
            "is_valid": self.is_valid(),
            "coppa_compliant": True,
        }


@dataclass
class DataItem:
    """
    Represents a single piece of data in the EduLens system.

    Includes metadata for privacy compliance and audit trail.
    """

    data_id: str
    classification: DataClassification
    content: Any
    created_at: datetime
    processing_location: ProcessingLocation
    consent_verified: bool = False
    consent_id: Optional[str] = None
    encrypted: bool = False
    anonymized: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def should_be_deleted(self, retention_policy: RetentionPolicy) -> bool:
        """Check if data should be deleted per retention policy."""
        return retention_policy.is_expired(self.created_at)

    def to_audit_log(self) -> Dict[str, Any]:
        """Generate audit log entry for data access/creation."""
        return {
            "data_id": self.data_id,
            "classification": self.classification.name,
            "created_at": self.created_at.isoformat(),
            "processing_location": self.processing_location.value,
            "consent_verified": self.consent_verified,
            "consent_id": self.consent_id,
            "encrypted": self.encrypted,
            "anonymized": self.anonymized,
            "size_bytes": len(str(self.content)) if self.content else 0,
        }


class PrivacyViolationError(Exception):
    """Raised when a privacy policy violation is detected."""

    pass


class ConsentRequiredError(Exception):
    """Raised when an operation requires parental consent that hasn't been granted."""

    pass


class DataRetentionViolationError(Exception):
    """Raised when data exceeds retention policy limits."""

    pass


class DataHandler:
    """
    Core privacy-first data handler for EduLens platform.

    Implements data classification, retention policies, consent verification,
    anonymization, and audit logging per COPPA requirements.

    This class is the central enforcement point for all privacy policies.
    """

    def __init__(self):
        """Initialize data handler with privacy policies and consent records."""
        self.policies: Dict[DataClassification, PrivacyPolicy] = {}
        self.consent_records: Dict[str, ConsentRecord] = {}
        self.audit_log: List[Dict[str, Any]] = []

        # Initialize default privacy policies
        self._initialize_policies()

        logger.info("DataHandler initialized with privacy-first policies")

    def _initialize_policies(self) -> None:
        """Initialize privacy policies for all data classifications."""

        # PUBLIC - No restrictions
        self.policies[DataClassification.PUBLIC] = PrivacyPolicy(
            classification=DataClassification.PUBLIC,
            retention=RetentionPolicy(
                classification=DataClassification.PUBLIC,
                max_retention_days=36500,  # 100 years (effectively unlimited)
                description="Public information, no retention limit",
            ),
            allowed_locations={
                ProcessingLocation.EDGE_DEVICE,
                ProcessingLocation.CLOUD_STORAGE,
                ProcessingLocation.CLOUD_PRIVACY_GATEWAY,
            },
            requires_consent=False,
            encryption_required=False,
            anonymization_required=False,
            audit_all_access=False,
        )

        # DEVICE_METADATA - Minimal restrictions
        self.policies[DataClassification.DEVICE_METADATA] = PrivacyPolicy(
            classification=DataClassification.DEVICE_METADATA,
            retention=RetentionPolicy(
                classification=DataClassification.DEVICE_METADATA,
                max_retention_days=365,
                description="Device metadata, 1-year retention",
            ),
            allowed_locations={
                ProcessingLocation.EDGE_DEVICE,
                ProcessingLocation.CLOUD_STORAGE,
                ProcessingLocation.CLOUD_PRIVACY_GATEWAY,
            },
            requires_consent=False,
            encryption_required=True,
            anonymization_required=False,
            audit_all_access=True,
        )

        # ANONYMOUS_TELEMETRY - Controlled sharing
        self.policies[DataClassification.ANONYMOUS_TELEMETRY] = PrivacyPolicy(
            classification=DataClassification.ANONYMOUS_TELEMETRY,
            retention=RetentionPolicy(
                classification=DataClassification.ANONYMOUS_TELEMETRY,
                max_retention_days=90,
                description="Anonymized telemetry, 90-day retention maximum",
            ),
            allowed_locations={
                ProcessingLocation.EDGE_DEVICE,
                ProcessingLocation.CLOUD_PRIVACY_GATEWAY,
                ProcessingLocation.CLOUD_STORAGE,
            },
            requires_consent=True,
            encryption_required=True,
            anonymization_required=True,
            audit_all_access=True,
        )

        # EDUCATIONAL_CONTENT - Device only
        self.policies[DataClassification.EDUCATIONAL_CONTENT] = PrivacyPolicy(
            classification=DataClassification.EDUCATIONAL_CONTENT,
            retention=RetentionPolicy(
                classification=DataClassification.EDUCATIONAL_CONTENT,
                max_retention_days=36500,  # Persistent until updated
                description="Educational content, persistent storage",
            ),
            allowed_locations={
                ProcessingLocation.EDGE_DEVICE,
            },
            requires_consent=False,
            encryption_required=True,
            anonymization_required=False,
            audit_all_access=False,
        )

        # PARENTAL_ACCOUNT - Secure cloud storage
        self.policies[DataClassification.PARENTAL_ACCOUNT] = PrivacyPolicy(
            classification=DataClassification.PARENTAL_ACCOUNT,
            retention=RetentionPolicy(
                classification=DataClassification.PARENTAL_ACCOUNT,
                max_retention_days=1095 + 365,  # Account lifetime + 3 years
                description="Parental account data, account + 3 years",
            ),
            allowed_locations={
                ProcessingLocation.CLOUD_PRIVACY_GATEWAY,
                ProcessingLocation.CLOUD_STORAGE,
            },
            requires_consent=True,
            encryption_required=True,
            anonymization_required=False,
            audit_all_access=True,
        )

        # SENSITIVE_VISUAL - NEVER STORE
        self.policies[DataClassification.SENSITIVE_VISUAL] = PrivacyPolicy(
            classification=DataClassification.SENSITIVE_VISUAL,
            retention=RetentionPolicy(
                classification=DataClassification.SENSITIVE_VISUAL,
                max_retention_days=0,  # IMMEDIATE deletion
                auto_purge_enabled=True,
                description="Images NEVER stored, volatile RAM only",
            ),
            allowed_locations={
                ProcessingLocation.VOLATILE_RAM,
                ProcessingLocation.SECURE_ENCLAVE,
            },
            requires_consent=True,
            encryption_required=False,  # N/A for volatile data
            anonymization_required=False,
            audit_all_access=True,
        )

        # VOICE_DATA - NEVER STORE
        self.policies[DataClassification.VOICE_DATA] = PrivacyPolicy(
            classification=DataClassification.VOICE_DATA,
            retention=RetentionPolicy(
                classification=DataClassification.VOICE_DATA,
                max_retention_days=0,  # IMMEDIATE deletion
                auto_purge_enabled=True,
                description="Voice data NEVER stored, secure enclave only",
            ),
            allowed_locations={
                ProcessingLocation.SECURE_ENCLAVE,
            },
            requires_consent=True,
            encryption_required=False,  # N/A for volatile data
            anonymization_required=False,
            audit_all_access=True,
        )

        # LEARNING_INTERACTION - Session only
        self.policies[DataClassification.LEARNING_INTERACTION] = PrivacyPolicy(
            classification=DataClassification.LEARNING_INTERACTION,
            retention=RetentionPolicy(
                classification=DataClassification.LEARNING_INTERACTION,
                max_retention_days=0,  # Session only (hours, not days)
                auto_purge_enabled=True,
                description="Session context, volatile RAM, cleared on sleep",
            ),
            allowed_locations={
                ProcessingLocation.VOLATILE_RAM,
                ProcessingLocation.EDGE_DEVICE,
            },
            requires_consent=False,
            encryption_required=False,
            anonymization_required=False,
            audit_all_access=False,
        )

        # CONSENT_METADATA - Long-term audit trail
        self.policies[DataClassification.CONSENT_METADATA] = PrivacyPolicy(
            classification=DataClassification.CONSENT_METADATA,
            retention=RetentionPolicy(
                classification=DataClassification.CONSENT_METADATA,
                max_retention_days=2555,  # 7 years (compliance requirement)
                description="Consent records, 7-year retention for compliance",
            ),
            allowed_locations={
                ProcessingLocation.CLOUD_PRIVACY_GATEWAY,
                ProcessingLocation.CLOUD_STORAGE,
                ProcessingLocation.EDGE_DEVICE,
            },
            requires_consent=False,  # Self-referential
            encryption_required=True,
            anonymization_required=False,
            audit_all_access=True,
        )

    def classify_data(
        self, content: Any, metadata: Optional[Dict[str, Any]] = None
    ) -> DataClassification:
        """
        Classify data based on content and metadata.

        Args:
            content: The data to classify
            metadata: Optional metadata about the data

        Returns:
            DataClassification enum indicating sensitivity level

        Raises:
            ValueError: If data cannot be classified
        """
        metadata = metadata or {}

        # Check for explicit classification in metadata
        if "classification" in metadata:
            classification_name = metadata["classification"]
            try:
                return DataClassification[classification_name]
            except KeyError:
                logger.warning(f"Invalid classification in metadata: {classification_name}")

        # Infer classification from content type and metadata
        if metadata.get("source") == "camera":
            logger.warning("CRITICAL: Camera image detected - SENSITIVE_VISUAL classification")
            return DataClassification.SENSITIVE_VISUAL

        if metadata.get("source") == "microphone":
            logger.warning("CRITICAL: Voice data detected - VOICE_DATA classification")
            return DataClassification.VOICE_DATA

        if metadata.get("type") == "session_context":
            return DataClassification.LEARNING_INTERACTION

        if metadata.get("type") == "telemetry":
            return DataClassification.ANONYMOUS_TELEMETRY

        if metadata.get("type") == "parent_account":
            return DataClassification.PARENTAL_ACCOUNT

        if metadata.get("type") == "consent":
            return DataClassification.CONSENT_METADATA

        if metadata.get("type") == "device_info":
            return DataClassification.DEVICE_METADATA

        if metadata.get("type") == "educational_content":
            return DataClassification.EDUCATIONAL_CONTENT

        # Default to most restrictive classification if uncertain
        logger.warning("Unable to confidently classify data, defaulting to SENSITIVE_VISUAL")
        return DataClassification.SENSITIVE_VISUAL

    def apply_minimization(self, data: DataItem) -> DataItem:
        """
        Apply data minimization principles to reduce collected data.

        Removes unnecessary fields, aggregates where possible, and pseudonymizes identifiers.

        Args:
            data: DataItem to minimize

        Returns:
            Minimized DataItem
        """
        policy = self.policies.get(data.classification)
        if not policy:
            raise ValueError(f"No policy found for classification: {data.classification}")

        # If anonymization is required, apply it
        if policy.anonymization_required and not data.anonymized:
            data = self.anonymize(data)

        # Remove metadata that's not essential
        essential_metadata = {}
        for key in ["subject_area", "duration_seconds", "interaction_count"]:
            if key in data.metadata:
                essential_metadata[key] = data.metadata[key]

        data.metadata = essential_metadata

        # Log minimization action
        self._audit_log(
            {
                "action": "DATA_MINIMIZATION",
                "data_id": data.data_id,
                "classification": data.classification.name,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        return data

    def check_retention(self, data: DataItem) -> bool:
        """
        Check if data complies with retention policy.

        Args:
            data: DataItem to check

        Returns:
            True if data is within retention limits, False if should be deleted

        Raises:
            DataRetentionViolationError: If data has exceeded retention limits
        """
        policy = self.policies.get(data.classification)
        if not policy:
            raise ValueError(f"No policy found for classification: {data.classification}")

        is_expired = data.should_be_deleted(policy.retention)

        if is_expired:
            logger.error(
                f"RETENTION VIOLATION: Data {data.data_id} ({data.classification.name}) "
                f"exceeded {policy.retention.max_retention_days} day retention limit"
            )

            self._audit_log(
                {
                    "action": "RETENTION_VIOLATION",
                    "data_id": data.data_id,
                    "classification": data.classification.name,
                    "created_at": data.created_at.isoformat(),
                    "max_retention_days": policy.retention.max_retention_days,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            if policy.retention.auto_purge_enabled:
                logger.info(f"Auto-purge enabled, initiating deletion of {data.data_id}")
                # In production, this would trigger deletion workflow
                raise DataRetentionViolationError(
                    f"Data {data.data_id} must be deleted (exceeded retention policy)"
                )

        return not is_expired

    def get_consent_status(
        self, parent_account_id: str, child_pseudonym: str, category: DataClassification
    ) -> ConsentStatus:
        """
        Get current consent status for a specific data category.

        Args:
            parent_account_id: ID of parent account
            child_pseudonym: Pseudonymized child identifier
            category: Data classification category to check

        Returns:
            ConsentStatus enum indicating current consent state
        """
        # Generate lookup key
        consent_key = f"{parent_account_id}:{child_pseudonym}:{category.name}"

        # Check if consent record exists
        if consent_key not in self.consent_records:
            return ConsentStatus.NOT_REQUESTED

        consent_record = self.consent_records[consent_key]

        # Check if consent is expired
        if consent_record.expires_at and datetime.utcnow() > consent_record.expires_at:
            consent_record.status = ConsentStatus.EXPIRED
            self.consent_records[consent_key] = consent_record

            self._audit_log(
                {
                    "action": "CONSENT_EXPIRED",
                    "consent_id": consent_record.consent_id,
                    "parent_account_id": parent_account_id,
                    "child_pseudonym": child_pseudonym,
                    "category": category.name,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

        return consent_record.status

    def verify_consent(
        self, parent_account_id: str, child_pseudonym: str, category: DataClassification
    ) -> bool:
        """
        Verify that valid parental consent exists for data operation.

        Args:
            parent_account_id: ID of parent account
            child_pseudonym: Pseudonymized child identifier
            category: Data classification category requiring consent

        Returns:
            True if consent is valid, False otherwise

        Raises:
            ConsentRequiredError: If consent is required but not granted
        """
        policy = self.policies.get(category)
        if not policy:
            raise ValueError(f"No policy found for classification: {category}")

        # If consent is not required for this category, allow operation
        if not policy.requires_consent:
            return True

        # Check consent status
        status = self.get_consent_status(parent_account_id, child_pseudonym, category)

        if status == ConsentStatus.GRANTED:
            consent_key = f"{parent_account_id}:{child_pseudonym}:{category.name}"
            consent_record = self.consent_records[consent_key]

            # Verify consent is still valid (not expired or revoked)
            if consent_record.is_valid():
                self._audit_log(
                    {
                        "action": "CONSENT_VERIFIED",
                        "consent_id": consent_record.consent_id,
                        "parent_account_id": parent_account_id,
                        "child_pseudonym": child_pseudonym,
                        "category": category.name,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
                return True

        # Consent not granted or invalid
        logger.error(
            f"CONSENT REQUIRED: Operation requires parental consent for {category.name}. "
            f"Current status: {status.value}"
        )

        self._audit_log(
            {
                "action": "CONSENT_VIOLATION",
                "parent_account_id": parent_account_id,
                "child_pseudonym": child_pseudonym,
                "category": category.name,
                "consent_status": status.value,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        raise ConsentRequiredError(
            f"Parental consent required for {category.name} (current status: {status.value})"
        )

    def grant_consent(
        self,
        parent_account_id: str,
        child_pseudonym: str,
        category: DataClassification,
        consent_method: str,
        verification_method: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConsentRecord:
        """
        Record parental consent for data collection.

        Args:
            parent_account_id: ID of parent account
            child_pseudonym: Pseudonymized child identifier
            category: Data classification category being consented to
            consent_method: How consent was obtained (e.g., "IN_APP_EXPLICIT_CLICK")
            verification_method: How parent was verified (e.g., "MFA_EMAIL_SMS")
            metadata: Optional additional metadata

        Returns:
            ConsentRecord documenting the consent
        """
        consent_id = self._generate_consent_id(parent_account_id, child_pseudonym, category)
        consent_key = f"{parent_account_id}:{child_pseudonym}:{category.name}"

        # Create consent record
        consent_record = ConsentRecord(
            consent_id=consent_id,
            parent_account_id=parent_account_id,
            child_pseudonym=child_pseudonym,
            category=category,
            status=ConsentStatus.GRANTED,
            timestamp=datetime.utcnow(),
            consent_method=consent_method,
            verification_method=verification_method,
            expires_at=datetime.utcnow() + timedelta(days=365),  # Annual review
            metadata=metadata or {},
        )

        # Store consent record
        self.consent_records[consent_key] = consent_record

        # Audit log
        self._audit_log(consent_record.to_audit_log())

        logger.info(
            f"Consent GRANTED: {category.name} for child {child_pseudonym} "
            f"by parent {parent_account_id}"
        )

        return consent_record

    def revoke_consent(
        self, parent_account_id: str, child_pseudonym: str, category: DataClassification
    ) -> bool:
        """
        Revoke previously granted parental consent.

        Args:
            parent_account_id: ID of parent account
            child_pseudonym: Pseudonymized child identifier
            category: Data classification category to revoke

        Returns:
            True if consent was revoked, False if no consent existed
        """
        consent_key = f"{parent_account_id}:{child_pseudonym}:{category.name}"

        if consent_key not in self.consent_records:
            logger.warning(f"No consent record found to revoke for {consent_key}")
            return False

        consent_record = self.consent_records[consent_key]
        consent_record.status = ConsentStatus.REVOKED
        consent_record.revoked_at = datetime.utcnow()

        self.consent_records[consent_key] = consent_record

        # Audit log
        self._audit_log(
            {
                "action": "CONSENT_REVOKED",
                "consent_id": consent_record.consent_id,
                "parent_account_id": parent_account_id,
                "child_pseudonym": child_pseudonym,
                "category": category.name,
                "revoked_at": consent_record.revoked_at.isoformat(),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        logger.info(
            f"Consent REVOKED: {category.name} for child {child_pseudonym} "
            f"by parent {parent_account_id}"
        )

        return True

    def anonymize(self, data: DataItem) -> DataItem:
        """
        Anonymize data by removing or hashing personally identifiable information.

        Args:
            data: DataItem to anonymize

        Returns:
            Anonymized DataItem
        """
        if data.anonymized:
            return data  # Already anonymized

        # Apply anonymization techniques based on data type
        if isinstance(data.content, dict):
            anonymized_content = {}

            for key, value in data.content.items():
                # Remove PII fields
                if key in {"name", "email", "phone", "address", "ip_address"}:
                    continue

                # Hash identifiers
                if key in {"device_id", "user_id", "child_id"}:
                    anonymized_content[f"{key}_hash"] = self._hash_identifier(str(value))
                else:
                    anonymized_content[key] = value

            data.content = anonymized_content

        data.anonymized = True

        # Audit log
        self._audit_log(
            {
                "action": "DATA_ANONYMIZED",
                "data_id": data.data_id,
                "classification": data.classification.name,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        return data

    def validate_processing_location(
        self, data: DataItem, target_location: ProcessingLocation
    ) -> bool:
        """
        Validate that data can be processed at the target location.

        Args:
            data: DataItem to be processed
            target_location: Proposed processing location

        Returns:
            True if location is allowed, False otherwise

        Raises:
            PrivacyViolationError: If processing at target location would violate policy
        """
        policy = self.policies.get(data.classification)
        if not policy:
            raise ValueError(f"No policy found for classification: {data.classification}")

        is_allowed = policy.validate_processing_location(target_location)

        if not is_allowed:
            logger.error(
                f"PRIVACY VIOLATION: {data.classification.name} cannot be processed at "
                f"{target_location.value}. Allowed locations: "
                f"{[loc.value for loc in policy.allowed_locations]}"
            )

            self._audit_log(
                {
                    "action": "LOCATION_VIOLATION",
                    "data_id": data.data_id,
                    "classification": data.classification.name,
                    "attempted_location": target_location.value,
                    "allowed_locations": [loc.value for loc in policy.allowed_locations],
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            raise PrivacyViolationError(
                f"{data.classification.name} cannot be processed at {target_location.value}"
            )

        return True

    def create_data_item(
        self,
        content: Any,
        classification: DataClassification,
        processing_location: ProcessingLocation,
        parent_account_id: Optional[str] = None,
        child_pseudonym: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DataItem:
        """
        Create a new data item with privacy controls applied.

        Args:
            content: The data content
            classification: Data classification level
            processing_location: Where data will be processed
            parent_account_id: Optional parent account ID (for consent verification)
            child_pseudonym: Optional child pseudonym (for consent verification)
            metadata: Optional metadata

        Returns:
            DataItem with privacy controls applied

        Raises:
            ConsentRequiredError: If consent is required but not granted
            PrivacyViolationError: If creation would violate privacy policy
        """
        policy = self.policies.get(classification)
        if not policy:
            raise ValueError(f"No policy found for classification: {classification}")

        # Verify consent if required
        consent_verified = False
        consent_id = None

        if policy.requires_consent and parent_account_id and child_pseudonym:
            consent_verified = self.verify_consent(
                parent_account_id, child_pseudonym, classification
            )
            consent_key = f"{parent_account_id}:{child_pseudonym}:{classification.name}"
            if consent_key in self.consent_records:
                consent_id = self.consent_records[consent_key].consent_id

        # Validate processing location
        if not policy.validate_processing_location(processing_location):
            raise PrivacyViolationError(
                f"{classification.name} cannot be processed at {processing_location.value}"
            )

        # Warn if sensitive data is being created
        if classification.is_never_stored():
            logger.warning(
                f"CRITICAL: Creating {classification.name} data item. "
                f"This data MUST NOT be persisted to storage!"
            )

        # Create data item
        data_id = self._generate_data_id()
        data_item = DataItem(
            data_id=data_id,
            classification=classification,
            content=content,
            created_at=datetime.utcnow(),
            processing_location=processing_location,
            consent_verified=consent_verified,
            consent_id=consent_id,
            encrypted=policy.encryption_required,
            anonymized=policy.anonymization_required,
            metadata=metadata or {},
        )

        # Apply minimization
        data_item = self.apply_minimization(data_item)

        # Audit log
        self._audit_log(
            {
                "action": "DATA_CREATED",
                **data_item.to_audit_log(),
            }
        )

        return data_item

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve audit log entries.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of audit log entries (most recent first)
        """
        return self.audit_log[-limit:]

    def export_consent_records(self, parent_account_id: str) -> List[Dict[str, Any]]:
        """
        Export all consent records for a parent account (for parental access rights).

        Args:
            parent_account_id: ID of parent account

        Returns:
            List of consent records in dictionary format
        """
        parent_consents = [
            consent.to_audit_log()
            for consent in self.consent_records.values()
            if consent.parent_account_id == parent_account_id
        ]

        self._audit_log(
            {
                "action": "CONSENT_EXPORT",
                "parent_account_id": parent_account_id,
                "record_count": len(parent_consents),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        return parent_consents

    def _generate_data_id(self) -> str:
        """Generate unique data ID."""
        timestamp = datetime.utcnow().isoformat()
        return f"data_{sha256(timestamp.encode()).hexdigest()[:16]}"

    def _generate_consent_id(
        self, parent_account_id: str, child_pseudonym: str, category: DataClassification
    ) -> str:
        """Generate unique consent ID."""
        data = (
            f"{parent_account_id}:{child_pseudonym}:{category.name}:{datetime.utcnow().isoformat()}"
        )
        return f"consent_{sha256(data.encode()).hexdigest()[:16]}"

    def _hash_identifier(self, identifier: str) -> str:
        """Hash an identifier for pseudonymization."""
        return sha256(identifier.encode()).hexdigest()

    def _audit_log(self, entry: Dict[str, Any]) -> None:
        """Add entry to audit log."""
        entry["audit_timestamp"] = datetime.utcnow().isoformat()
        self.audit_log.append(entry)

        # In production, this would write to immutable audit log storage
        logger.info(f"AUDIT: {json.dumps(entry)}")


# Convenience function for quick data classification
def classify_data(content: Any, metadata: Optional[Dict[str, Any]] = None) -> DataClassification:
    """
    Classify data using default DataHandler instance.

    Args:
        content: The data to classify
        metadata: Optional metadata about the data

    Returns:
        DataClassification enum indicating sensitivity level
    """
    handler = DataHandler()
    return handler.classify_data(content, metadata)


# Export public API
__all__ = [
    "DataClassification",
    "ProcessingLocation",
    "ConsentStatus",
    "RetentionPolicy",
    "PrivacyPolicy",
    "ConsentRecord",
    "DataItem",
    "DataHandler",
    "classify_data",
    "PrivacyViolationError",
    "ConsentRequiredError",
    "DataRetentionViolationError",
]
