"""
Validation Gates for Claude Agents Orchestration System.

This module implements 5 validation gates that verify quality and completeness
at each phase of the orchestration pipeline. Each gate includes confidence
scoring and issue identification.
"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Set
import uuid


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationStatus(str, Enum):
    """Status of validation gate."""

    PASSED = "passed"
    FAILED = "failed"
    REVIEW_REQUIRED = "review_required"
    SKIPPED = "skipped"


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    severity: ValidationSeverity = ValidationSeverity.WARNING
    category: str = ""
    message: str = ""
    location: str = ""
    suggestion: str = ""
    auto_fixable: bool = False
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity.value,
            "category": self.category,
            "message": self.message,
            "location": self.location,
            "suggestion": self.suggestion,
            "auto_fixable": self.auto_fixable,
            "context": self.context,
        }


@dataclass
class ValidationResult:
    """Result of a validation gate execution."""

    gate_name: str
    phase: int
    status: ValidationStatus
    confidence_score: float  # 0.0 to 1.0
    issues: List[ValidationIssue] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    execution_time_ms: float = 0.0

    @property
    def passed(self) -> bool:
        return self.status == ValidationStatus.PASSED

    @property
    def critical_issues(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.CRITICAL]

    @property
    def error_issues(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate_name": self.gate_name,
            "phase": self.phase,
            "status": self.status.value,
            "confidence_score": self.confidence_score,
            "passed": self.passed,
            "issues": [i.to_dict() for i in self.issues],
            "recommendations": self.recommendations,
            "metrics": self.metrics,
            "timestamp": self.timestamp.isoformat(),
            "execution_time_ms": self.execution_time_ms,
        }


class ValidationGate(ABC):
    """
    Abstract base class for validation gates.

    Each gate validates a specific phase of the orchestration pipeline
    and returns a ValidationResult with confidence scoring.

    Thresholds:
    - >70%: Pass automatically
    - 50-70%: Human review required
    - <50%: Pipeline halt
    """

    def __init__(
        self,
        pass_threshold: float = 0.70,
        review_threshold: float = 0.50,
    ):
        """
        Initialize the validation gate.

        Args:
            pass_threshold: Confidence score threshold for automatic pass
            review_threshold: Confidence score threshold for review (below = halt)
        """
        self.pass_threshold = pass_threshold
        self.review_threshold = review_threshold
        self._rules: List[callable] = []

    @property
    @abstractmethod
    def gate_name(self) -> str:
        """Name of the validation gate."""
        pass

    @property
    @abstractmethod
    def phase(self) -> int:
        """Phase number this gate validates."""
        pass

    @abstractmethod
    async def validate(self, context: Dict[str, Any]) -> ValidationResult:
        """
        Execute validation for this gate.

        Args:
            context: Validation context containing artifacts and metadata

        Returns:
            ValidationResult with status, confidence, and issues
        """
        pass

    def _calculate_status(self, confidence: float) -> ValidationStatus:
        """Calculate validation status based on confidence score."""
        if confidence >= self.pass_threshold:
            return ValidationStatus.PASSED
        elif confidence >= self.review_threshold:
            return ValidationStatus.REVIEW_REQUIRED
        else:
            return ValidationStatus.FAILED

    def _calculate_confidence(
        self,
        issues: List[ValidationIssue],
        checks_passed: int,
        total_checks: int,
    ) -> float:
        """
        Calculate confidence score based on issues and checks.

        Args:
            issues: List of validation issues
            checks_passed: Number of checks that passed
            total_checks: Total number of checks

        Returns:
            Confidence score (0.0 to 1.0)
        """
        if total_checks == 0:
            return 1.0

        # Base score from passed checks
        base_score = checks_passed / total_checks

        # Deductions for issues
        deductions = 0.0
        for issue in issues:
            if issue.severity == ValidationSeverity.CRITICAL:
                deductions += 0.25
            elif issue.severity == ValidationSeverity.ERROR:
                deductions += 0.15
            elif issue.severity == ValidationSeverity.WARNING:
                deductions += 0.05
            # INFO issues don't affect score

        return max(0.0, min(1.0, base_score - deductions))


class Gate1ConceptDesign(ValidationGate):
    """
    Gate 1: Concept Design Validation

    Validates the output of the Concept Designer agent, ensuring:
    - Project requirements are complete and clear
    - Architecture decisions are documented
    - Technology stack is defined
    - Deliverables are specified
    """

    @property
    def gate_name(self) -> str:
        return "Gate1_ConceptDesign"

    @property
    def phase(self) -> int:
        return 1

    async def validate(self, context: Dict[str, Any]) -> ValidationResult:
        """Validate concept design phase output."""
        import time
        start_time = time.time()

        issues = []
        recommendations = []
        checks_passed = 0
        total_checks = 0

        spec = context.get("project_spec", {})

        # Check 1: Project overview exists
        total_checks += 1
        if spec.get("project_overview"):
            checks_passed += 1
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="completeness",
                message="Project overview is missing",
                suggestion="Add a clear project overview describing the purpose and scope",
            ))

        # Check 2: Requirements are defined
        total_checks += 1
        requirements = spec.get("requirements", [])
        if requirements and len(requirements) >= 3:
            checks_passed += 1
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="completeness",
                message=f"Insufficient requirements defined (found {len(requirements)})",
                suggestion="Define at least 3 clear requirements",
            ))

        # Check 3: Architecture is documented
        total_checks += 1
        architecture = spec.get("architecture", {})
        if architecture.get("components") and architecture.get("data_flow"):
            checks_passed += 1
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="documentation",
                message="Architecture documentation is incomplete",
                suggestion="Document system components and data flow",
            ))

        # Check 4: Technology stack is defined
        total_checks += 1
        tech_stack = spec.get("technology_stack", {})
        required_categories = ["backend", "database"]
        if all(tech_stack.get(cat) for cat in required_categories):
            checks_passed += 1
        else:
            missing = [c for c in required_categories if not tech_stack.get(c)]
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="completeness",
                message=f"Technology stack missing: {', '.join(missing)}",
                suggestion="Define technologies for all required categories",
            ))

        # Check 5: Deliverables are specified
        total_checks += 1
        deliverables = spec.get("deliverables", [])
        if deliverables and len(deliverables) >= 2:
            checks_passed += 1
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="planning",
                message="Insufficient deliverables specified",
                suggestion="Define clear project deliverables",
            ))

        # Check 6: Risk assessment exists
        total_checks += 1
        if spec.get("risks"):
            checks_passed += 1
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                category="planning",
                message="No risk assessment provided",
                suggestion="Consider adding risk assessment for better planning",
            ))
            recommendations.append("Add risk assessment for identified challenges")

        # Check 7: Acceptance criteria defined
        total_checks += 1
        if spec.get("acceptance_criteria"):
            checks_passed += 1
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="quality",
                message="Acceptance criteria not defined",
                suggestion="Define clear acceptance criteria for deliverables",
            ))

        # Calculate confidence
        confidence = self._calculate_confidence(issues, checks_passed, total_checks)
        status = self._calculate_status(confidence)

        execution_time = (time.time() - start_time) * 1000

        return ValidationResult(
            gate_name=self.gate_name,
            phase=self.phase,
            status=status,
            confidence_score=confidence,
            issues=issues,
            recommendations=recommendations,
            metrics={
                "checks_passed": checks_passed,
                "total_checks": total_checks,
                "requirements_count": len(requirements),
                "deliverables_count": len(deliverables),
            },
            execution_time_ms=execution_time,
        )


class Gate2MCPData(ValidationGate):
    """
    Gate 2: MCP Data Validation

    Validates MCP data retrieval phase, ensuring:
    - MCP servers are accessible
    - Required data is retrieved
    - Data schema is valid
    - Caching is working
    """

    @property
    def gate_name(self) -> str:
        return "Gate2_MCPData"

    @property
    def phase(self) -> int:
        return 2

    async def validate(self, context: Dict[str, Any]) -> ValidationResult:
        """Validate MCP data retrieval phase."""
        import time
        start_time = time.time()

        issues = []
        recommendations = []
        checks_passed = 0
        total_checks = 0

        mcp_status = context.get("mcp_status", {})
        retrieved_data = context.get("retrieved_data", {})

        # Check 1: MCP server connectivity
        total_checks += 1
        server_status = mcp_status.get("server_status", "unknown")
        if server_status == "active":
            checks_passed += 1
        elif server_status == "dormant":
            checks_passed += 0.5  # Partial credit for dormant (expected when no MCP)
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                category="connectivity",
                message="MCP servers are dormant (no external data needed)",
            ))
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="connectivity",
                message=f"MCP server status: {server_status}",
                suggestion="Check MCP server configuration and connectivity",
            ))

        # Check 2: Data retrieval success
        total_checks += 1
        if retrieved_data.get("success", False):
            checks_passed += 1
        elif mcp_status.get("server_status") == "dormant":
            checks_passed += 1  # No data needed
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="data",
                message="Data retrieval failed",
                suggestion="Review MCP query and retry data retrieval",
            ))

        # Check 3: Data schema validation
        total_checks += 1
        schema_valid = retrieved_data.get("schema_valid", True)
        if schema_valid:
            checks_passed += 1
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="schema",
                message="Retrieved data does not match expected schema",
                suggestion="Verify data source schema and transform logic",
            ))

        # Check 4: Cache status
        total_checks += 1
        cache_hit = mcp_status.get("cache_hit", False)
        if cache_hit or mcp_status.get("server_status") == "dormant":
            checks_passed += 1
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                category="performance",
                message="Cache miss - data fetched from source",
            ))
            checks_passed += 0.8  # Slight penalty for cache miss

        # Check 5: Rate limiting compliance
        total_checks += 1
        rate_limited = mcp_status.get("rate_limited", False)
        if not rate_limited:
            checks_passed += 1
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="performance",
                message="Rate limiting was triggered",
                suggestion="Consider implementing request batching",
            ))

        confidence = self._calculate_confidence(issues, checks_passed, total_checks)
        status = self._calculate_status(confidence)

        execution_time = (time.time() - start_time) * 1000

        return ValidationResult(
            gate_name=self.gate_name,
            phase=self.phase,
            status=status,
            confidence_score=confidence,
            issues=issues,
            recommendations=recommendations,
            metrics={
                "checks_passed": checks_passed,
                "total_checks": total_checks,
                "mcp_status": server_status,
                "data_retrieved": retrieved_data.get("success", False),
            },
            execution_time_ms=execution_time,
        )


class Gate3Infrastructure(ValidationGate):
    """
    Gate 3: Infrastructure Validation

    Validates infrastructure setup phase, ensuring:
    - Cloud resources are provisioned
    - Database is configured
    - CI/CD pipeline is set up
    - Security configurations are applied
    """

    @property
    def gate_name(self) -> str:
        return "Gate3_Infrastructure"

    @property
    def phase(self) -> int:
        return 3

    async def validate(self, context: Dict[str, Any]) -> ValidationResult:
        """Validate infrastructure setup phase."""
        import time
        start_time = time.time()

        issues = []
        recommendations = []
        checks_passed = 0
        total_checks = 0

        infra = context.get("infrastructure", {})

        # Check 1: Database provisioned
        total_checks += 1
        db_status = infra.get("database", {})
        if db_status.get("provisioned") and db_status.get("accessible"):
            checks_passed += 1
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="infrastructure",
                message="Database not properly provisioned",
                suggestion="Verify database credentials and connectivity",
            ))

        # Check 2: Repository configured
        total_checks += 1
        repo_status = infra.get("repository", {})
        if repo_status.get("created") and repo_status.get("branch_protection"):
            checks_passed += 1
        elif repo_status.get("created"):
            checks_passed += 0.5
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="security",
                message="Branch protection not configured",
                suggestion="Enable branch protection rules on main branch",
            ))
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="infrastructure",
                message="Repository not configured",
                suggestion="Create and configure source repository",
            ))

        # Check 3: CI/CD pipeline
        total_checks += 1
        cicd_status = infra.get("cicd", {})
        if cicd_status.get("configured") and cicd_status.get("passing"):
            checks_passed += 1
        elif cicd_status.get("configured"):
            checks_passed += 0.7
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="automation",
                message="CI/CD pipeline configured but not passing",
                suggestion="Review pipeline configuration and fix failures",
            ))
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="automation",
                message="CI/CD pipeline not configured",
                suggestion="Set up automated build and deployment pipeline",
            ))

        # Check 4: Environment variables set
        total_checks += 1
        env_vars = infra.get("environment_variables", {})
        required_vars = ["DATABASE_URL", "API_KEY", "SECRET_KEY"]
        missing_vars = [v for v in required_vars if v not in env_vars]
        if not missing_vars:
            checks_passed += 1
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="configuration",
                message=f"Missing environment variables: {', '.join(missing_vars)}",
                suggestion="Configure all required environment variables",
            ))

        # Check 5: Security configuration
        total_checks += 1
        security = infra.get("security", {})
        if security.get("ssl_enabled") and security.get("firewall_configured"):
            checks_passed += 1
        else:
            missing = []
            if not security.get("ssl_enabled"):
                missing.append("SSL")
            if not security.get("firewall_configured"):
                missing.append("firewall")
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="security",
                message=f"Security not fully configured: {', '.join(missing)}",
                suggestion="Enable SSL and configure firewall rules",
            ))

        confidence = self._calculate_confidence(issues, checks_passed, total_checks)
        status = self._calculate_status(confidence)

        execution_time = (time.time() - start_time) * 1000

        return ValidationResult(
            gate_name=self.gate_name,
            phase=self.phase,
            status=status,
            confidence_score=confidence,
            issues=issues,
            recommendations=recommendations,
            metrics={
                "checks_passed": checks_passed,
                "total_checks": total_checks,
            },
            execution_time_ms=execution_time,
        )


class Gate4CodeGenerated(ValidationGate):
    """
    Gate 4: Code Generation Validation

    Validates generated code quality, ensuring:
    - Code compiles/parses successfully
    - Tests are included
    - Code style is consistent
    - Security best practices followed
    """

    @property
    def gate_name(self) -> str:
        return "Gate4_CodeGenerated"

    @property
    def phase(self) -> int:
        return 4

    async def validate(self, context: Dict[str, Any]) -> ValidationResult:
        """Validate code generation phase."""
        import time
        start_time = time.time()

        issues = []
        recommendations = []
        checks_passed = 0
        total_checks = 0

        code_output = context.get("code_output", {})

        # Check 1: Code compiles/parses
        total_checks += 1
        if code_output.get("compilation_success", False):
            checks_passed += 1
        else:
            errors = code_output.get("compilation_errors", [])
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="compilation",
                message=f"Code compilation failed with {len(errors)} errors",
                suggestion="Fix compilation errors before proceeding",
                context={"errors": errors[:5]},
            ))

        # Check 2: Tests exist
        total_checks += 1
        test_count = code_output.get("test_count", 0)
        if test_count >= 5:
            checks_passed += 1
        elif test_count > 0:
            checks_passed += 0.5
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="testing",
                message=f"Low test count: {test_count}",
                suggestion="Add more tests for better coverage",
            ))
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="testing",
                message="No tests generated",
                suggestion="Generate unit tests for critical functionality",
            ))

        # Check 3: Code style compliance
        total_checks += 1
        style_issues = code_output.get("style_issues", [])
        if len(style_issues) == 0:
            checks_passed += 1
        elif len(style_issues) < 10:
            checks_passed += 0.7
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                category="style",
                message=f"Found {len(style_issues)} style issues",
                auto_fixable=True,
            ))
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="style",
                message=f"Found {len(style_issues)} style issues",
                suggestion="Run code formatter to fix style issues",
                auto_fixable=True,
            ))

        # Check 4: Security scan
        total_checks += 1
        security_issues = code_output.get("security_issues", [])
        critical_security = [i for i in security_issues if i.get("severity") == "critical"]
        if not critical_security and len(security_issues) < 3:
            checks_passed += 1
        elif critical_security:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="security",
                message=f"Found {len(critical_security)} critical security issues",
                suggestion="Address security vulnerabilities immediately",
                context={"issues": critical_security[:3]},
            ))
        else:
            checks_passed += 0.5
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="security",
                message=f"Found {len(security_issues)} security issues",
                suggestion="Review and fix security warnings",
            ))

        # Check 5: Documentation
        total_checks += 1
        doc_coverage = code_output.get("documentation_coverage", 0)
        if doc_coverage >= 0.8:
            checks_passed += 1
        elif doc_coverage >= 0.5:
            checks_passed += 0.7
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                category="documentation",
                message=f"Documentation coverage: {doc_coverage:.0%}",
                suggestion="Add documentation for public APIs",
            ))
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="documentation",
                message=f"Low documentation coverage: {doc_coverage:.0%}",
                suggestion="Document public classes and functions",
            ))

        confidence = self._calculate_confidence(issues, checks_passed, total_checks)
        status = self._calculate_status(confidence)

        execution_time = (time.time() - start_time) * 1000

        return ValidationResult(
            gate_name=self.gate_name,
            phase=self.phase,
            status=status,
            confidence_score=confidence,
            issues=issues,
            recommendations=recommendations,
            metrics={
                "checks_passed": checks_passed,
                "total_checks": total_checks,
                "test_count": test_count,
                "security_issues": len(security_issues),
            },
            execution_time_ms=execution_time,
        )


class Gate5IntegrationTest(ValidationGate):
    """
    Gate 5: Integration Test Validation

    Validates integration testing phase, ensuring:
    - All integration tests pass
    - Performance meets requirements
    - Error handling works correctly
    - End-to-end flows succeed
    """

    @property
    def gate_name(self) -> str:
        return "Gate5_IntegrationTest"

    @property
    def phase(self) -> int:
        return 5

    async def validate(self, context: Dict[str, Any]) -> ValidationResult:
        """Validate integration testing phase."""
        import time
        start_time = time.time()

        issues = []
        recommendations = []
        checks_passed = 0
        total_checks = 0

        test_results = context.get("test_results", {})

        # Check 1: Test pass rate
        total_checks += 1
        total_tests = test_results.get("total", 0)
        passed_tests = test_results.get("passed", 0)
        pass_rate = passed_tests / total_tests if total_tests > 0 else 0

        if pass_rate >= 0.95:
            checks_passed += 1
        elif pass_rate >= 0.80:
            checks_passed += 0.7
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="testing",
                message=f"Test pass rate: {pass_rate:.0%}",
                suggestion="Fix failing tests before deployment",
            ))
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="testing",
                message=f"Low test pass rate: {pass_rate:.0%}",
                suggestion="Review and fix failing tests",
            ))

        # Check 2: Performance tests
        total_checks += 1
        perf_results = test_results.get("performance", {})
        if perf_results.get("passed", False):
            checks_passed += 1
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="performance",
                message="Performance tests did not meet requirements",
                suggestion="Optimize slow operations or adjust thresholds",
                context=perf_results.get("metrics", {}),
            ))

        # Check 3: Error handling tests
        total_checks += 1
        error_handling = test_results.get("error_handling", {})
        if error_handling.get("coverage", 0) >= 0.8:
            checks_passed += 1
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="resilience",
                message=f"Error handling coverage: {error_handling.get('coverage', 0):.0%}",
                suggestion="Add tests for error scenarios",
            ))

        # Check 4: End-to-end tests
        total_checks += 1
        e2e_results = test_results.get("e2e", {})
        if e2e_results.get("passed", False):
            checks_passed += 1
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="integration",
                message="End-to-end tests failed",
                suggestion="Review integration points and fix issues",
            ))

        # Check 5: Code coverage
        total_checks += 1
        coverage = test_results.get("coverage", 0)
        if coverage >= 0.80:
            checks_passed += 1
        elif coverage >= 0.60:
            checks_passed += 0.7
            recommendations.append(f"Consider increasing test coverage from {coverage:.0%}")
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="coverage",
                message=f"Low test coverage: {coverage:.0%}",
                suggestion="Add tests to improve coverage",
            ))

        confidence = self._calculate_confidence(issues, checks_passed, total_checks)
        status = self._calculate_status(confidence)

        execution_time = (time.time() - start_time) * 1000

        return ValidationResult(
            gate_name=self.gate_name,
            phase=self.phase,
            status=status,
            confidence_score=confidence,
            issues=issues,
            recommendations=recommendations,
            metrics={
                "checks_passed": checks_passed,
                "total_checks": total_checks,
                "test_pass_rate": pass_rate,
                "coverage": coverage,
            },
            execution_time_ms=execution_time,
        )


# Gate registry
VALIDATION_GATES: Dict[int, type] = {
    1: Gate1ConceptDesign,
    2: Gate2MCPData,
    3: Gate3Infrastructure,
    4: Gate4CodeGenerated,
    5: Gate5IntegrationTest,
}


def get_gate_for_phase(
    phase: int,
    pass_threshold: float = 0.70,
    review_threshold: float = 0.50,
) -> Optional[ValidationGate]:
    """
    Get the validation gate for a specific phase.

    Args:
        phase: Phase number
        pass_threshold: Confidence threshold for pass
        review_threshold: Confidence threshold for review

    Returns:
        ValidationGate instance or None
    """
    gate_class = VALIDATION_GATES.get(phase)
    if gate_class:
        return gate_class(
            pass_threshold=pass_threshold,
            review_threshold=review_threshold,
        )
    return None
