"""
Validators for Claude Agents Orchestration System.

This module provides validation utilities including schema validation,
input sanitization, and secret detection.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Pattern, Tuple, Union


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a validation issue."""

    severity: ValidationSeverity
    message: str
    field: Optional[str] = None
    value: Optional[Any] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "message": self.message,
            "field": self.field,
            "suggestion": self.suggestion,
        }


@dataclass
class ValidationResult:
    """Result of validation."""

    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)

    def add_issue(
        self,
        severity: ValidationSeverity,
        message: str,
        field: Optional[str] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        self.issues.append(
            ValidationIssue(
                severity=severity,
                message=message,
                field=field,
                suggestion=suggestion,
            )
        )
        if severity == ValidationSeverity.ERROR:
            self.valid = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "issues": [i.to_dict() for i in self.issues],
            "error_count": sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR),
            "warning_count": sum(
                1 for i in self.issues if i.severity == ValidationSeverity.WARNING
            ),
        }


class InputValidator:
    """
    Input validation and sanitization utility.

    Provides methods for validating and sanitizing user input
    to prevent injection attacks and ensure data integrity.

    Example:
        validator = InputValidator()

        # Validate string
        result = validator.validate_string(user_input, max_length=1000)

        # Sanitize for SQL
        safe_value = validator.sanitize_sql(user_input)

        # Validate email
        is_valid = validator.validate_email(email)
    """

    # Patterns for common injection attacks
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE)\b)",
        r"(--|;|/\*|\*/)",
        r"(\bOR\b\s+\b\d+\b\s*=\s*\b\d+\b)",
        r"(\bAND\b\s+\b\d+\b\s*=\s*\b\d+\b)",
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
    ]

    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$]",
        r"\$\(",
        r"`[^`]+`",
    ]

    def __init__(self):
        """Initialize the input validator."""
        self._sql_patterns = [re.compile(p, re.I) for p in self.SQL_INJECTION_PATTERNS]
        self._xss_patterns = [re.compile(p, re.I) for p in self.XSS_PATTERNS]
        self._cmd_patterns = [re.compile(p) for p in self.COMMAND_INJECTION_PATTERNS]

    def validate_string(
        self,
        value: str,
        min_length: int = 0,
        max_length: int = 10000,
        pattern: Optional[str] = None,
        allow_empty: bool = True,
    ) -> ValidationResult:
        """
        Validate a string value.

        Args:
            value: String to validate
            min_length: Minimum length
            max_length: Maximum length
            pattern: Regex pattern to match
            allow_empty: Whether empty string is allowed

        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True)

        if not isinstance(value, str):
            result.add_issue(
                ValidationSeverity.ERROR,
                "Value must be a string",
                suggestion="Convert value to string",
            )
            return result

        if not value and not allow_empty:
            result.add_issue(
                ValidationSeverity.ERROR,
                "Value cannot be empty",
            )
            return result

        if len(value) < min_length:
            result.add_issue(
                ValidationSeverity.ERROR,
                f"Value too short (min: {min_length})",
                suggestion=f"Provide at least {min_length} characters",
            )

        if len(value) > max_length:
            result.add_issue(
                ValidationSeverity.ERROR,
                f"Value too long (max: {max_length})",
                suggestion=f"Limit to {max_length} characters",
            )

        if pattern and not re.match(pattern, value):
            result.add_issue(
                ValidationSeverity.ERROR,
                "Value does not match required pattern",
            )

        return result

    def check_sql_injection(self, value: str) -> ValidationResult:
        """Check for SQL injection patterns."""
        result = ValidationResult(valid=True)

        for pattern in self._sql_patterns:
            if pattern.search(value):
                result.add_issue(
                    ValidationSeverity.ERROR,
                    "Potential SQL injection detected",
                    suggestion="Use parameterized queries",
                )
                break

        return result

    def check_xss(self, value: str) -> ValidationResult:
        """Check for XSS patterns."""
        result = ValidationResult(valid=True)

        for pattern in self._xss_patterns:
            if pattern.search(value):
                result.add_issue(
                    ValidationSeverity.ERROR,
                    "Potential XSS attack detected",
                    suggestion="Sanitize HTML content",
                )
                break

        return result

    def check_command_injection(self, value: str) -> ValidationResult:
        """Check for command injection patterns."""
        result = ValidationResult(valid=True)

        for pattern in self._cmd_patterns:
            if pattern.search(value):
                result.add_issue(
                    ValidationSeverity.ERROR,
                    "Potential command injection detected",
                    suggestion="Escape shell characters",
                )
                break

        return result

    def sanitize_html(self, value: str) -> str:
        """Sanitize HTML by escaping special characters."""
        replacements = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#x27;",
        }
        for char, replacement in replacements.items():
            value = value.replace(char, replacement)
        return value

    def sanitize_sql(self, value: str) -> str:
        """Sanitize string for SQL (escape quotes)."""
        return value.replace("'", "''").replace("\\", "\\\\")

    def validate_email(self, value: str) -> bool:
        """Validate email format."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, value))

    def validate_url(self, value: str) -> bool:
        """Validate URL format."""
        pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        return bool(re.match(pattern, value, re.I))


class SchemaValidator:
    """
    JSON schema validation utility.

    Validates data against JSON schema definitions.
    """

    def __init__(self):
        """Initialize the schema validator."""
        pass

    def validate(
        self,
        data: Dict[str, Any],
        schema: Dict[str, Any],
    ) -> ValidationResult:
        """
        Validate data against a schema.

        Args:
            data: Data to validate
            schema: JSON schema

        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True)

        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in data:
                result.add_issue(
                    ValidationSeverity.ERROR,
                    f"Missing required field: {field}",
                    field=field,
                )

        # Validate properties
        properties = schema.get("properties", {})
        for field, field_schema in properties.items():
            if field in data:
                field_result = self._validate_field(data[field], field_schema, field)
                result.issues.extend(field_result.issues)
                if not field_result.valid:
                    result.valid = False

        return result

    def _validate_field(
        self,
        value: Any,
        schema: Dict[str, Any],
        field_name: str,
    ) -> ValidationResult:
        """Validate a single field against its schema."""
        result = ValidationResult(valid=True)

        expected_type = schema.get("type")

        # Type validation
        if expected_type:
            type_map = {
                "string": str,
                "integer": int,
                "number": (int, float),
                "boolean": bool,
                "array": list,
                "object": dict,
            }

            expected_python_type = type_map.get(expected_type)
            if expected_python_type and not isinstance(value, expected_python_type):
                result.add_issue(
                    ValidationSeverity.ERROR,
                    f"Expected {expected_type}, got {type(value).__name__}",
                    field=field_name,
                )

        # String constraints
        if isinstance(value, str):
            if "minLength" in schema and len(value) < schema["minLength"]:
                result.add_issue(
                    ValidationSeverity.ERROR,
                    f"String too short (min: {schema['minLength']})",
                    field=field_name,
                )
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                result.add_issue(
                    ValidationSeverity.ERROR,
                    f"String too long (max: {schema['maxLength']})",
                    field=field_name,
                )
            if "pattern" in schema and not re.match(schema["pattern"], value):
                result.add_issue(
                    ValidationSeverity.ERROR,
                    "String does not match pattern",
                    field=field_name,
                )

        # Number constraints
        if isinstance(value, (int, float)):
            if "minimum" in schema and value < schema["minimum"]:
                result.add_issue(
                    ValidationSeverity.ERROR,
                    f"Value below minimum ({schema['minimum']})",
                    field=field_name,
                )
            if "maximum" in schema and value > schema["maximum"]:
                result.add_issue(
                    ValidationSeverity.ERROR,
                    f"Value above maximum ({schema['maximum']})",
                    field=field_name,
                )

        # Enum constraint
        if "enum" in schema and value not in schema["enum"]:
            result.add_issue(
                ValidationSeverity.ERROR,
                f"Value not in allowed values: {schema['enum']}",
                field=field_name,
            )

        return result


class SecretDetector:
    """
    Secret detection utility.

    Detects hardcoded secrets, API keys, and sensitive data in text.
    """

    # Patterns for common secrets
    SECRET_PATTERNS = [
        # API Keys
        (r"api[_-]?key['\"]?\s*[:=]\s*['\"]?[\w-]{20,}", "API Key"),
        (r"apikey['\"]?\s*[:=]\s*['\"]?[\w-]{20,}", "API Key"),
        # AWS
        (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
        (r"aws[_-]?secret[_-]?access[_-]?key['\"]?\s*[:=]\s*['\"]?[\w/+]{40}", "AWS Secret Key"),
        # GitHub
        (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Token"),
        (r"gho_[a-zA-Z0-9]{36}", "GitHub OAuth Token"),
        (r"ghu_[a-zA-Z0-9]{36}", "GitHub User Token"),
        # Generic tokens
        (r"bearer\s+[a-zA-Z0-9_.~+/=-]{20,}", "Bearer Token"),
        (r"token['\"]?\s*[:=]\s*['\"]?[a-zA-Z0-9_.~+/=-]{20,}", "Generic Token"),
        # Passwords
        (r"password['\"]?\s*[:=]\s*['\"]?[^\s'\"]{8,}", "Password"),
        (r"passwd['\"]?\s*[:=]\s*['\"]?[^\s'\"]{8,}", "Password"),
        (r"pwd['\"]?\s*[:=]\s*['\"]?[^\s'\"]{8,}", "Password"),
        # Private keys
        (r"-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----", "Private Key"),
        # Connection strings
        (r"(?:postgres|mysql|mongodb)://[^\s]+:[^\s]+@", "Database Connection"),
        # Slack
        (r"xox[baprs]-[0-9a-zA-Z]{10,}", "Slack Token"),
    ]

    def __init__(self):
        """Initialize the secret detector."""
        self._patterns = [
            (re.compile(pattern, re.I), name) for pattern, name in self.SECRET_PATTERNS
        ]

    def scan(self, text: str) -> List[Dict[str, Any]]:
        """
        Scan text for secrets.

        Args:
            text: Text to scan

        Returns:
            List of detected secrets with type and location
        """
        findings = []

        for pattern, secret_type in self._patterns:
            for match in pattern.finditer(text):
                # Mask the actual value
                value = match.group(0)
                masked = (
                    value[:5] + "*" * (len(value) - 10) + value[-5:] if len(value) > 15 else "***"
                )

                findings.append(
                    {
                        "type": secret_type,
                        "masked_value": masked,
                        "start": match.start(),
                        "end": match.end(),
                        "line": text[: match.start()].count("\n") + 1,
                    }
                )

        return findings

    def has_secrets(self, text: str) -> bool:
        """Check if text contains any secrets."""
        return len(self.scan(text)) > 0

    def redact(self, text: str) -> str:
        """Redact all secrets from text."""
        result = text

        for pattern, _ in self._patterns:
            result = pattern.sub("[REDACTED]", result)

        return result
