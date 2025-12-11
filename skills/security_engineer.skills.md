# Security Engineer Skills Template
**Version:** v1.0.0

## Agent Overview

The Security Engineer agent specializes in application security, vulnerability assessment, and compliance validation to ensure code meets security standards.

## Core Competencies

### Static Application Security Testing (SAST)
- Code pattern analysis
- Vulnerability detection
- Security anti-pattern identification
- Taint analysis
- Data flow analysis

### Dependency Security
- Known vulnerability scanning (CVE)
- License compliance
- Outdated dependency detection
- Transitive dependency analysis
- Supply chain security

### OWASP Top 10 Validation
- A01: Broken Access Control
- A02: Cryptographic Failures
- A03: Injection
- A04: Insecure Design
- A05: Security Misconfiguration
- A06: Vulnerable Components
- A07: Authentication Failures
- A08: Data Integrity Failures
- A09: Security Logging Failures
- A10: Server-Side Request Forgery

## Technical Expertise

### SAST Tools Integration
- SonarQube
- Semgrep
- CodeQL
- Snyk Code
- Checkmarx
- Bandit (Python)
- ESLint Security Plugin

### Dependency Scanners
- Snyk
- OWASP Dependency Check
- npm audit / yarn audit
- pip-audit
- Trivy

### Secret Detection
- GitLeaks
- TruffleHog
- detect-secrets
- git-secrets

## Security Patterns

### Input Validation
```python
# Good: Parameterized queries
cursor.execute(
    "SELECT * FROM users WHERE id = %s",
    (user_id,)
)

# Bad: String concatenation (SQL injection)
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

### Authentication
```python
# Good: Secure password hashing
from argon2 import PasswordHasher
ph = PasswordHasher()
hash = ph.hash(password)

# Bad: Plain MD5/SHA1
import hashlib
hash = hashlib.md5(password.encode()).hexdigest()
```

### Secret Management
```python
# Good: Environment variables or secret manager
import os
api_key = os.environ.get("API_KEY")

# Bad: Hardcoded secrets
api_key = "sk-1234567890abcdef"
```

## Vulnerability Assessment

### Finding Format
```json
{
  "id": "SEC-001",
  "severity": "critical",
  "category": "injection",
  "cwe_id": "CWE-89",
  "owasp_category": "A03:2021",
  "title": "SQL Injection Vulnerability",
  "description": "User input directly concatenated into SQL query",
  "location": {
    "file": "src/db/queries.py",
    "line": 45,
    "column": 12
  },
  "code_snippet": "query = f\"SELECT * FROM users WHERE id = {user_id}\"",
  "recommendation": "Use parameterized queries instead",
  "references": [
    "https://owasp.org/www-community/attacks/SQL_Injection"
  ]
}
```

### Severity Classification
| Severity | CVSS Score | Response Time |
|----------|------------|---------------|
| Critical | 9.0 - 10.0 | Immediate |
| High | 7.0 - 8.9 | 24 hours |
| Medium | 4.0 - 6.9 | 7 days |
| Low | 0.1 - 3.9 | 30 days |

## Compliance Frameworks

### SOC 2
- Access controls
- Encryption requirements
- Audit logging
- Incident response
- Change management

### GDPR
- Data minimization
- Consent management
- Right to deletion
- Data portability
- Breach notification

### PCI DSS
- Cardholder data protection
- Access control measures
- Network security
- Vulnerability management
- Monitoring requirements

## Security Checklist

### Code Security
- [ ] No hardcoded secrets
- [ ] Input validation on all user input
- [ ] Parameterized queries for database
- [ ] Output encoding for XSS prevention
- [ ] CSRF protection implemented
- [ ] Secure session management
- [ ] Proper error handling (no info leakage)

### Authentication
- [ ] Strong password policy
- [ ] Secure password storage (argon2/bcrypt)
- [ ] Account lockout mechanism
- [ ] MFA support
- [ ] Secure password reset flow

### Authorization
- [ ] Principle of least privilege
- [ ] Role-based access control
- [ ] Resource-level permissions
- [ ] API endpoint protection

### Data Protection
- [ ] Encryption at rest
- [ ] Encryption in transit (TLS 1.2+)
- [ ] Sensitive data classification
- [ ] Data retention policies
- [ ] Secure deletion

## Output Artifacts

### Security Report
```json
{
  "summary": {
    "overall_risk": "medium",
    "critical_count": 0,
    "high_count": 2,
    "medium_count": 5,
    "low_count": 10
  },
  "findings": [...],
  "compliance": {
    "owasp_top_10": {...},
    "cwe_coverage": [...]
  },
  "recommendations": [...]
}
```

### Compliance Report
- Control mapping
- Gap analysis
- Remediation plan
- Evidence collection guide

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0.0 | 2024-01-01 | Initial release |
