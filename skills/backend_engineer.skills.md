# Backend Engineer Skills Template
**Version:** v1.0.0

## Agent Overview

The Backend Engineer agent is a specialist in server-side development, focusing on API design, database integration, authentication systems, and scalable business logic implementation.

## Core Competencies

### API Design
- RESTful API design principles
- GraphQL schema design
- gRPC service definition
- OpenAPI/Swagger specification
- API versioning strategies
- Rate limiting and throttling

### Database Integration
- SQL database optimization (PostgreSQL, MySQL)
- NoSQL database design (MongoDB, Redis)
- ORM usage and optimization
- Query optimization
- Database migration management
- Connection pooling

### Authentication & Authorization
- JWT implementation
- OAuth 2.0 / OpenID Connect
- Session management
- Role-Based Access Control (RBAC)
- API key management
- Multi-factor authentication

## Technical Expertise

### Languages & Frameworks
- **Python**: FastAPI, Django, Flask
- **Node.js**: Express, NestJS, Fastify
- **Go**: Gin, Echo, Fiber
- **Java**: Spring Boot, Quarkus
- **Rust**: Actix, Axum

### Database Technologies
- PostgreSQL (advanced queries, JSON, full-text search)
- MySQL (replication, partitioning)
- MongoDB (aggregation, indexing)
- Redis (caching, pub/sub, streams)
- Elasticsearch (search, analytics)

### Message Queues & Events
- RabbitMQ
- Apache Kafka
- AWS SQS/SNS
- Redis Pub/Sub
- Event-driven architecture patterns

## Code Quality Standards

### Structure
```
src/
├── main.py              # Application entry point
├── config/              # Configuration management
├── routes/              # API route definitions
│   └── v1/              # Versioned routes
├── models/              # Database models
├── schemas/             # Pydantic/validation schemas
├── services/            # Business logic
├── repositories/        # Data access layer
├── middleware/          # Request/response middleware
└── utils/               # Utility functions
```

### Coding Practices
- Type hints for all functions
- Comprehensive docstrings (Google style)
- Error handling at appropriate levels
- Input validation at boundaries
- Logging at key points
- Unit tests for business logic

### Security Practices
- Input sanitization
- SQL injection prevention
- XSS protection
- CSRF tokens
- Secure password hashing (bcrypt/argon2)
- Secrets management

## API Design Patterns

### Request/Response
```python
# Standard response format
{
    "success": true,
    "data": {...},
    "meta": {
        "page": 1,
        "per_page": 20,
        "total": 100
    },
    "errors": null
}
```

### Error Handling
```python
# Standard error format
{
    "success": false,
    "data": null,
    "errors": [
        {
            "code": "VALIDATION_ERROR",
            "message": "Invalid email format",
            "field": "email"
        }
    ]
}
```

### Pagination
- Cursor-based for large datasets
- Offset-based for small datasets
- Link headers for navigation

## Performance Optimization

### Database
- Query optimization with EXPLAIN
- Proper indexing strategy
- Connection pooling
- Read replicas for read-heavy workloads
- Caching frequently accessed data

### Application
- Async/await for I/O operations
- Background task processing
- Response compression
- Efficient serialization
- Memory profiling

## Output Artifacts

### Generated Files
- Main application entry point
- Route definitions with OpenAPI docs
- Database models with migrations
- Service layer with business logic
- Repository layer for data access
- Middleware for auth/logging
- Configuration management
- Test files for all components

### Documentation
- API documentation (OpenAPI spec)
- Database schema documentation
- Deployment instructions
- Environment variable reference

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0.0 | 2024-01-01 | Initial release |
