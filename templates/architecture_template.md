# Architecture Document Template

## Document Information

| Field | Value |
|-------|-------|
| Project Name | [Project Name] |
| Version | 1.0.0 |
| Date | [Date] |
| Author | Claude Agents Orchestration System |
| Status | Draft / Review / Approved |

---

## 1. Executive Summary

### 1.1 Purpose
<!-- Brief description of what this architecture achieves -->

This document describes the technical architecture for [Project Name], a [project type]
that [brief description of main functionality].

### 1.2 Scope
<!-- What is covered and not covered -->

**In Scope:**
- [Component/Feature 1]
- [Component/Feature 2]
- [Component/Feature 3]

**Out of Scope:**
- [Component/Feature that will be addressed later]

### 1.3 Key Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Frontend Framework | React | Component-based, large ecosystem |
| Backend Framework | FastAPI | Async support, auto-documentation |
| Database | PostgreSQL | ACID compliance, JSON support |
| Deployment | Docker + K8s | Scalability, portability |

---

## 2. System Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CLIENTS                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │   Web    │  │  Mobile  │  │   CLI    │  │   API    │            │
│  │  Client  │  │   App    │  │  Client  │  │ Consumer │            │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │
└───────┼─────────────┼─────────────┼─────────────┼───────────────────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                            │
                    ┌───────▼───────┐
                    │  API Gateway  │
                    │  (Load Balancer)│
                    └───────┬───────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
│   Service A   │   │   Service B   │   │   Service C   │
│  (Feature 1)  │   │  (Feature 2)  │   │  (Feature 3)  │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                    ┌───────▼───────┐
                    │   Database    │
                    │  (PostgreSQL) │
                    └───────────────┘
```

### 2.2 Component Overview

| Component | Technology | Purpose | Owner |
|-----------|------------|---------|-------|
| Web Client | React + TypeScript | User interface | Frontend Team |
| API Gateway | NGINX/Kong | Routing, rate limiting | Platform Team |
| Auth Service | FastAPI | Authentication/Authorization | Backend Team |
| Core Service | FastAPI | Business logic | Backend Team |
| Database | PostgreSQL | Data persistence | Data Team |
| Cache | Redis | Session, caching | Platform Team |
| Queue | Redis/RabbitMQ | Async processing | Platform Team |

---

## 3. Component Architecture

### 3.1 Frontend Architecture

```
src/
├── components/           # Reusable UI components
│   ├── common/          # Shared components
│   ├── forms/           # Form components
│   └── layout/          # Layout components
├── pages/               # Page components (routes)
├── hooks/               # Custom React hooks
├── services/            # API service layer
├── store/               # State management
├── utils/               # Utility functions
├── types/               # TypeScript types
└── styles/              # Global styles
```

**Key Patterns:**
- Component composition for reusability
- Custom hooks for logic extraction
- Service layer for API abstraction
- Centralized state management

### 3.2 Backend Architecture

```
app/
├── api/                 # API routes
│   ├── v1/             # Version 1 endpoints
│   └── deps.py         # Dependencies
├── core/               # Core configurations
│   ├── config.py       # Settings
│   └── security.py     # Auth utilities
├── models/             # Database models
├── schemas/            # Pydantic schemas
├── services/           # Business logic
├── repositories/       # Data access layer
└── utils/              # Utilities
```

**Key Patterns:**
- Repository pattern for data access
- Service layer for business logic
- Dependency injection
- Schema-based validation

### 3.3 Database Schema

```sql
-- Core entities

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE [entity_name] (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    -- additional fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_[entity]_user_id ON [entity](user_id);
```

---

## 4. Integration Architecture

### 4.1 API Design

**Base URL:** `https://api.example.com/v1`

**Authentication:** Bearer Token (JWT)

**Standard Response Format:**
```json
{
  "success": true,
  "data": { },
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 100
  },
  "errors": []
}
```

**Key Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /auth/login | User authentication |
| POST | /auth/register | User registration |
| GET | /users/me | Current user profile |
| GET | /[resource] | List resources |
| POST | /[resource] | Create resource |
| GET | /[resource]/{id} | Get resource |
| PUT | /[resource]/{id} | Update resource |
| DELETE | /[resource]/{id} | Delete resource |

### 4.2 External Integrations

```
┌─────────────────┐     ┌─────────────────┐
│   Application   │────▶│   Stripe API    │
│                 │     │   (Payments)    │
└────────┬────────┘     └─────────────────┘
         │
         │              ┌─────────────────┐
         ├─────────────▶│   SendGrid      │
         │              │   (Email)       │
         │              └─────────────────┘
         │
         │              ┌─────────────────┐
         └─────────────▶│   AWS S3        │
                        │   (Storage)     │
                        └─────────────────┘
```

| Service | Purpose | Auth Method | Rate Limit |
|---------|---------|-------------|------------|
| Stripe | Payments | API Key | 100 req/s |
| SendGrid | Email | API Key | 600 req/min |
| AWS S3 | File storage | IAM Role | N/A |

---

## 5. Security Architecture

### 5.1 Authentication Flow

```
┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐
│ Client │────▶│  API   │────▶│  Auth  │────▶│   DB   │
│        │     │Gateway │     │Service │     │        │
└────────┘     └────────┘     └────────┘     └────────┘
     │              │              │              │
     │  1. Login    │              │              │
     │─────────────▶│              │              │
     │              │  2. Validate │              │
     │              │─────────────▶│              │
     │              │              │  3. Query    │
     │              │              │─────────────▶│
     │              │              │◀─────────────│
     │              │◀─────────────│  4. User     │
     │◀─────────────│  5. JWT      │              │
     │  6. Token    │              │              │
```

### 5.2 Security Controls

| Control | Implementation | Layer |
|---------|----------------|-------|
| HTTPS | TLS 1.3 | Transport |
| Authentication | JWT + Refresh Token | Application |
| Authorization | RBAC | Application |
| Input Validation | Pydantic/Zod | Application |
| SQL Injection | Parameterized queries | Data |
| XSS | Content Security Policy | Transport |
| CSRF | SameSite cookies | Application |
| Rate Limiting | Redis-based | API Gateway |

### 5.3 Data Protection

- **At Rest:** AES-256 encryption
- **In Transit:** TLS 1.3
- **Sensitive Data:** Hashed (bcrypt) or encrypted
- **PII:** Masked in logs, encrypted in DB

---

## 6. Infrastructure Architecture

### 6.1 Deployment Topology

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Kubernetes Cluster                          │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                        Ingress Controller                      │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                  │                                  │
│         ┌────────────────────────┼────────────────────────┐        │
│         │                        │                        │        │
│  ┌──────▼──────┐          ┌──────▼──────┐          ┌──────▼──────┐ │
│  │  Frontend   │          │   Backend   │          │   Worker    │ │
│  │  (3 pods)   │          │  (3 pods)   │          │  (2 pods)   │ │
│  └─────────────┘          └──────┬──────┘          └──────┬──────┘ │
│                                  │                        │        │
│                    ┌─────────────┴─────────────┐          │        │
│                    │                           │          │        │
│             ┌──────▼──────┐             ┌──────▼──────┐   │        │
│             │  PostgreSQL │             │    Redis    │◀──┘        │
│             │  (Primary)  │             │  (Cluster)  │            │
│             └──────┬──────┘             └─────────────┘            │
│                    │                                               │
│             ┌──────▼──────┐                                        │
│             │  PostgreSQL │                                        │
│             │  (Replica)  │                                        │
│             └─────────────┘                                        │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 Resource Requirements

| Component | CPU | Memory | Storage | Replicas |
|-----------|-----|--------|---------|----------|
| Frontend | 0.5 | 512Mi | - | 3 |
| Backend | 1.0 | 1Gi | - | 3 |
| Worker | 0.5 | 512Mi | - | 2 |
| PostgreSQL | 2.0 | 4Gi | 100Gi | 2 |
| Redis | 0.5 | 1Gi | 10Gi | 3 |

### 6.3 Scaling Strategy

| Component | Metric | Threshold | Scale |
|-----------|--------|-----------|-------|
| Frontend | CPU | 70% | +1 pod |
| Backend | CPU/Request Count | 70%/1000 | +1 pod |
| Worker | Queue Depth | 100 | +1 pod |

---

## 7. Observability

### 7.1 Logging

**Log Levels:**
- ERROR: System errors requiring attention
- WARN: Potential issues
- INFO: Normal operations
- DEBUG: Detailed debugging (dev only)

**Log Format:**
```json
{
  "timestamp": "2024-01-01T00:00:00Z",
  "level": "INFO",
  "service": "backend",
  "trace_id": "abc123",
  "message": "Request processed",
  "context": {}
}
```

### 7.2 Metrics

| Metric | Type | Description |
|--------|------|-------------|
| request_count | Counter | Total requests |
| request_duration_ms | Histogram | Request latency |
| error_rate | Gauge | Error percentage |
| active_users | Gauge | Active user sessions |
| queue_depth | Gauge | Background job queue |

### 7.3 Alerting

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| High Error Rate | error_rate > 5% | Critical | Page on-call |
| High Latency | p99 > 2s | Warning | Notify team |
| Service Down | health_check fail | Critical | Auto-restart, page |
| Disk Space | usage > 80% | Warning | Scale storage |

---

## 8. Development Guidelines

### 8.1 Code Organization

```
project/
├── .github/            # GitHub workflows
├── docs/               # Documentation
├── frontend/           # Frontend application
├── backend/            # Backend application
├── infrastructure/     # IaC (Terraform/K8s)
├── scripts/            # Utility scripts
├── docker-compose.yml  # Local development
└── Makefile           # Common commands
```

### 8.2 Development Workflow

1. Create feature branch from `main`
2. Implement changes with tests
3. Run linting and tests locally
4. Create pull request
5. Code review (1 approval minimum)
6. Merge to `main`
7. Automatic deployment to staging
8. Manual promotion to production

### 8.3 Testing Strategy

| Type | Coverage Target | Tools |
|------|-----------------|-------|
| Unit | 80% | pytest/Jest |
| Integration | 60% | pytest/Supertest |
| E2E | Critical paths | Playwright/Cypress |
| Performance | Key endpoints | k6/Locust |

---

## 9. Appendices

### A. Glossary

| Term | Definition |
|------|------------|
| API | Application Programming Interface |
| JWT | JSON Web Token |
| K8s | Kubernetes |
| RBAC | Role-Based Access Control |

### B. References

- [Project Specification](./project_spec.md)
- [API Documentation](./api_docs.md)
- [Deployment Guide](./deployment.md)

### C. Decision Records

| ADR | Title | Date | Status |
|-----|-------|------|--------|
| ADR-001 | Use PostgreSQL for primary database | 2024-01-01 | Accepted |
| ADR-002 | Adopt React for frontend | 2024-01-01 | Accepted |
| ADR-003 | Implement JWT authentication | 2024-01-01 | Accepted |
