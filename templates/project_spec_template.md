# Project Specification Template

## Project Overview

### Project Name
<!-- Required: Unique identifier for the project -->
```
name: my-project
```

### Description
<!-- Required: Brief description of the project (2-5 sentences) -->
```
A web application that enables users to manage their personal finances,
track expenses, and generate insights through data visualization.
```

### Project Type
<!-- Required: Select one -->
- [ ] Web Application
- [ ] Mobile Application
- [ ] API/Backend Service
- [ ] CLI Tool
- [ ] Desktop Application
- [ ] Library/Package
- [ ] Full-Stack Application

---

## Core Requirements

### Features
<!-- Required: List of main features (minimum 3) -->

1. **Feature Name**
   - Description: Brief description of the feature
   - Priority: High/Medium/Low
   - User Story: As a [user type], I want [capability] so that [benefit]

2. **Feature Name**
   - Description: Brief description of the feature
   - Priority: High/Medium/Low
   - User Story: As a [user type], I want [capability] so that [benefit]

3. **Feature Name**
   - Description: Brief description of the feature
   - Priority: High/Medium/Low
   - User Story: As a [user type], I want [capability] so that [benefit]

### User Types
<!-- Required: Define user roles/personas -->

| Role | Description | Permissions |
|------|-------------|-------------|
| Admin | System administrator | Full access |
| User | Standard user | Read/Write own data |
| Guest | Unauthenticated visitor | Read-only public data |

---

## Technical Requirements

### Technology Preferences
<!-- Optional: Preferred technologies (leave blank for agent recommendations) -->

**Frontend:**
- Framework: [React/Vue/Angular/Svelte/None]
- UI Library: [Material-UI/Tailwind/Bootstrap/Custom]
- State Management: [Redux/Zustand/Vuex/Context]

**Backend:**
- Language: [Python/Node.js/Go/Rust]
- Framework: [FastAPI/Express/Gin/Actix]
- Database: [PostgreSQL/MySQL/MongoDB/SQLite]

**Infrastructure:**
- Deployment: [Docker/Kubernetes/Serverless]
- Cloud Provider: [AWS/GCP/Azure/Self-hosted]

### Integration Requirements
<!-- Optional: External services/APIs to integrate -->

| Service | Purpose | Authentication |
|---------|---------|----------------|
| Stripe | Payment processing | API Key |
| Auth0 | Authentication | OAuth 2.0 |
| SendGrid | Email delivery | API Key |

### MCP Data Sources
<!-- Optional: External data sources via MCP -->

- [ ] Enable MCP Integration

**MCP Servers:**
1. Server Name: [name]
   - URL: [url]
   - Auth Type: [none/api_key/bearer/oauth]
   - Purpose: [what data to fetch]

---

## Non-Functional Requirements

### Performance
<!-- Optional: Performance targets -->

| Metric | Target |
|--------|--------|
| Page Load Time | < 3 seconds |
| API Response Time | < 500ms |
| Concurrent Users | 1000 |
| Uptime | 99.9% |

### Security
<!-- Optional: Security requirements -->

- [ ] HTTPS/TLS encryption
- [ ] Input validation and sanitization
- [ ] SQL injection prevention
- [ ] XSS protection
- [ ] CSRF protection
- [ ] Rate limiting
- [ ] Audit logging
- [ ] Data encryption at rest
- [ ] GDPR compliance
- [ ] SOC 2 compliance

### Scalability
<!-- Optional: Scalability requirements -->

- [ ] Horizontal scaling support
- [ ] Database sharding ready
- [ ] CDN integration
- [ ] Caching strategy
- [ ] Load balancing

---

## Constraints

### Budget
<!-- Optional: Cost constraints -->

- API Cost Budget: $[amount] USD
- Infrastructure Budget: $[amount]/month
- Development Timeline: [weeks/months]

### Technical Constraints
<!-- Optional: Technical limitations -->

- Must run on [specific platform/hardware]
- Must integrate with [existing system]
- Must support [specific browser/device]
- Cannot use [specific technology]

### Compliance
<!-- Optional: Regulatory requirements -->

- [ ] HIPAA
- [ ] PCI-DSS
- [ ] GDPR
- [ ] SOX
- [ ] Other: [specify]

---

## Deliverables

### Code Deliverables
<!-- Select expected outputs -->

- [x] Source code with documentation
- [x] Database schema and migrations
- [x] API documentation
- [x] Test suite (unit, integration, e2e)
- [x] Docker configuration
- [ ] Kubernetes manifests
- [ ] CI/CD pipeline configuration
- [ ] Infrastructure as Code (Terraform/CloudFormation)

### Documentation Deliverables

- [x] README with setup instructions
- [x] API reference documentation
- [ ] Architecture decision records (ADRs)
- [ ] User documentation
- [ ] Operations runbook

---

## Additional Context

### Background
<!-- Optional: Additional context about the project -->

```
Provide any additional background information that would help
understand the project requirements, existing systems, or
business context.
```

### Examples/References
<!-- Optional: Reference implementations or inspiration -->

- [Reference Site/App 1](https://example.com)
- [Reference Site/App 2](https://example.com)

### Notes
<!-- Optional: Any other notes or considerations -->

```
Add any additional notes, questions, or considerations
that don't fit in the sections above.
```

---

## Specification JSON Format

For programmatic use, convert the above to this JSON structure:

```json
{
  "name": "my-project",
  "description": "Project description here",
  "type": "web_application",
  "features": [
    {
      "name": "Feature 1",
      "description": "Description",
      "priority": "high",
      "user_story": "As a user, I want..."
    }
  ],
  "user_types": [
    {
      "role": "admin",
      "description": "System administrator",
      "permissions": ["all"]
    }
  ],
  "technical": {
    "frontend": {
      "framework": "react",
      "ui_library": "tailwind"
    },
    "backend": {
      "language": "python",
      "framework": "fastapi",
      "database": "postgresql"
    },
    "infrastructure": {
      "deployment": "docker",
      "cloud": "aws"
    }
  },
  "integrations": [
    {
      "service": "stripe",
      "purpose": "payments",
      "auth_type": "api_key"
    }
  ],
  "mcp": {
    "enabled": false,
    "servers": []
  },
  "requirements": {
    "performance": {
      "page_load_time_ms": 3000,
      "api_response_time_ms": 500
    },
    "security": [
      "https",
      "input_validation",
      "rate_limiting"
    ]
  },
  "constraints": {
    "budget_usd": 100,
    "timeline_weeks": 4
  },
  "deliverables": {
    "code": ["source", "tests", "docker"],
    "docs": ["readme", "api_reference"]
  }
}
```
