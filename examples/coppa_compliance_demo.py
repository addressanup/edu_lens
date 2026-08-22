"""
COPPA Compliance Validator Demo

This script demonstrates the COPPA compliance validation system for EduLens.
Shows how to perform automated compliance checks and generate audit reports.

Classification: EXAMPLE / DEMO
Author: Security and Privacy Agent (SEC-001)
Last Updated: 2025-12-10
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))

from datetime import datetime

from src.privacy.coppa_validator import (
    ComplianceLevel,
    COPPAValidator,
)
from src.privacy.data_handler import (
    DataClassification,
    DataHandler,
    DataItem,
    ProcessingLocation,
)


def demo_compliant_scenario():
    """Demonstrate a fully compliant scenario."""
    print("=" * 70)
    print("COPPA COMPLIANCE DEMO: Compliant Scenario")
    print("=" * 70)
    print()

    # Initialize components
    handler = DataHandler()
    validator = COPPAValidator(handler)

    # Setup compliant scenario: Grant parental consent
    print("1. Granting parental consent...")
    handler.grant_consent(
        parent_account_id="demo_parent_001",
        child_pseudonym="Demo Student",
        category=DataClassification.SENSITIVE_VISUAL,
        consent_method="CREDIT_CARD",
        verification_method="STRIPE_VERIFICATION",
    )
    print("   ✓ Consent granted for camera image processing")
    print()

    handler.grant_consent(
        parent_account_id="demo_parent_001",
        child_pseudonym="Demo Student",
        category=DataClassification.VOICE_DATA,
        consent_method="CREDIT_CARD",
        verification_method="STRIPE_VERIFICATION",
    )
    print("   ✓ Consent granted for voice command processing")
    print()

    # Create compliant data items
    print("2. Creating compliant data items...")
    data_items = [
        DataItem(
            data_id="demo_item_1",
            classification=DataClassification.EDUCATIONAL_CONTENT,
            content="Math problem: 2 + 2 = ?",
            created_at=datetime.utcnow(),
            processing_location=ProcessingLocation.EDGE_DEVICE,
            consent_verified=False,  # Not required for educational content
        )
    ]
    print("   ✓ Educational content item created (on-device)")
    print()

    # Define compliant third-party processors
    print("3. Configuring third-party processors...")
    processors = [
        {
            "name": "Cloud Storage Provider",
            "data_shared": ["PARENTAL_ACCOUNT"],  # No child data
            "has_dpa": True,
            "allows_secondary_use": False,
            "has_security_audit": True,
        }
    ]
    print("   ✓ Cloud provider configured (no child data shared)")
    print()

    # Generate compliance audit report
    print("4. Generating COPPA compliance audit report...")
    print()
    report = validator.generate_audit_report(
        parent_account_id="demo_parent_001",
        child_pseudonym="Demo Student",
        data_items=data_items,
        third_party_processors=processors,
    )

    # Display results
    print("-" * 70)
    print("AUDIT REPORT SUMMARY")
    print("-" * 70)
    print(f"Report ID: {report.report_id}")
    print(f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    print(f"Overall Status: {report.overall_status.value.upper()}")
    print(f"Checks Performed: {report.total_checks}")
    print(
        f"Checks Passed: {report.passed_checks} ({report.passed_checks/report.total_checks*100:.1f}%)"
    )
    print()
    print(f"Issues Found:")
    print(f"  - Critical: {report.critical_issues}")
    print(f"  - Violations: {report.violations}")
    print(f"  - Warnings: {report.warnings}")
    print()

    if report.issues:
        print("Issues Details:")
        for issue in report.issues:
            print(f"  [{issue.level.value.upper()}] {issue.title}")
            print(f"    {issue.description}")
            print()

    print("Recommendations:")
    for rec in report.recommendations:
        print(f"  • {rec}")
    print()

    print("-" * 70)
    print()


def demo_violation_scenario():
    """Demonstrate a compliance violation scenario."""
    print("=" * 70)
    print("COPPA COMPLIANCE DEMO: Violation Scenario")
    print("=" * 70)
    print()

    # Initialize components
    handler = DataHandler()
    validator = COPPAValidator(handler)

    # Create violation: Storing sensitive data in cloud
    print("1. Creating data item with VIOLATION...")
    violation_item = DataItem(
        data_id="violation_item",
        classification=DataClassification.SENSITIVE_VISUAL,
        content=b"fake_image_bytes",
        created_at=datetime.utcnow(),
        processing_location=ProcessingLocation.CLOUD_STORAGE,  # VIOLATION!
        consent_verified=True,
    )
    print("   ⚠ Camera image stored in CLOUD_STORAGE (VIOLATION)")
    print()

    # Run validation
    print("2. Running compliance validation...")
    level, issues = validator.validate_data_collection(data_items=[violation_item])
    print()

    # Display results
    print("-" * 70)
    print("VALIDATION RESULTS")
    print("-" * 70)
    print(f"Compliance Level: {level.value.upper()}")
    print(f"Issues Found: {len(issues)}")
    print()

    if issues:
        for issue in issues:
            print(f"[{issue.level.value.upper()}] {issue.title}")
            print(f"Description: {issue.description}")
            print(f"Regulation: {issue.regulation}")
            print(f"Recommendation: {issue.recommendation}")
            print()

    print("-" * 70)
    print()


def demo_consent_validation():
    """Demonstrate consent validation."""
    print("=" * 70)
    print("COPPA COMPLIANCE DEMO: Consent Validation")
    print("=" * 70)
    print()

    # Scenario 1: Missing consent
    print("Scenario 1: Missing Consent")
    print("-" * 70)
    handler = DataHandler()
    validator = COPPAValidator(handler)

    level, issues = validator.validate_consent(
        parent_account_id="demo_parent_002",
        child_pseudonym="Demo Student 2",
        required_categories=[DataClassification.SENSITIVE_VISUAL],
    )

    print(f"Status: {level.value.upper()}")
    print(f"Issues: {len(issues)}")
    if issues:
        for issue in issues:
            print(f"  - {issue.title}")
    print()

    # Scenario 2: Valid consent
    print("Scenario 2: Valid Consent")
    print("-" * 70)
    handler.grant_consent(
        parent_account_id="demo_parent_002",
        child_pseudonym="Demo Student 2",
        category=DataClassification.SENSITIVE_VISUAL,
        consent_method="CREDIT_CARD",
        verification_method="STRIPE_VERIFICATION",
    )

    level, issues = validator.validate_consent(
        parent_account_id="demo_parent_002",
        child_pseudonym="Demo Student 2",
        required_categories=[DataClassification.SENSITIVE_VISUAL],
    )

    print(f"Status: {level.value.upper()}")
    print(f"Issues: {len(issues)}")
    if not issues:
        print("  ✓ All consent requirements met")
    print()

    print("-" * 70)
    print()


def main():
    """Run all demo scenarios."""
    print()
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║         EduLens COPPA Compliance Validator - Demo Suite           ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print()

    try:
        # Demo 1: Compliant scenario
        demo_compliant_scenario()

        # Demo 2: Violation scenario
        demo_violation_scenario()

        # Demo 3: Consent validation
        demo_consent_validation()

        print("=" * 70)
        print("DEMO COMPLETE")
        print("=" * 70)
        print()
        print("The COPPA compliance validator has been successfully demonstrated.")
        print()
        print("Key Features Demonstrated:")
        print("  ✓ Automated compliance validation")
        print("  ✓ Comprehensive audit report generation")
        print("  ✓ Data collection compliance checks")
        print("  ✓ Parental consent verification")
        print("  ✓ Violation detection and reporting")
        print("  ✓ Actionable remediation recommendations")
        print()
        print("For more information, see:")
        print("  - docs/compliance/coppa_audit_report.md")
        print("  - docs/compliance/privacy_policy.md")
        print("  - docs/compliance/parental_consent_flow.md")
        print()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
