"""
Privacy and data protection modules for EduLens.

This package implements comprehensive privacy controls for COPPA compliance:
- Data classification and retention policies
- Ephemeral storage with automatic deletion
- Data minimization and PII removal
- Secure deletion with verification
- Consent management

Author: Security and Privacy Team (SEC-001)
Last Updated: 2025-12-10
"""

from .auto_deletion import (
    AutoDeletionManager,
    DeletionLog,
    DeletionMethod,
    DeletionStatus,
    DeletionTask,
    DeletionTrigger,
)
from .data_handler import (
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
from .data_minimizer import (
    DataMinimizer,
    DataType,
    LearningDataAggregate,
    MinimizationLevel,
    MinimizedAudio,
    MinimizedImage,
)
from .local_storage_manager import (
    LocalStorageManager,
    StorageContainer,
    StorageStats,
    StorageStatus,
    StorageType,
    get_storage_manager,
)

__all__ = [
    # Data Handler
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
    # Local Storage Manager
    "LocalStorageManager",
    "StorageType",
    "StorageStatus",
    "StorageStats",
    "StorageContainer",
    "get_storage_manager",
    # Data Minimizer
    "DataMinimizer",
    "DataType",
    "MinimizationLevel",
    "MinimizedImage",
    "MinimizedAudio",
    "LearningDataAggregate",
    # Auto-Deletion Manager
    "AutoDeletionManager",
    "DeletionTrigger",
    "DeletionStatus",
    "DeletionMethod",
    "DeletionTask",
    "DeletionLog",
]
