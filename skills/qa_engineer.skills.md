# QA Engineer Skills Template
**Version:** v1.0.0

## Agent Overview

The QA Engineer agent specializes in comprehensive software testing, including test automation, quality assurance, and coverage analysis to ensure code reliability and correctness.

## Core Competencies

### Test Automation
- Unit testing frameworks
- Integration testing
- End-to-end testing
- API testing
- Performance testing
- Load testing

### Quality Assurance
- Test planning
- Test case design
- Defect tracking
- Regression testing
- Smoke testing
- Acceptance testing

### Coverage Analysis
- Line coverage
- Branch coverage
- Function coverage
- Statement coverage
- Mutation testing

## Technical Expertise

### Testing Frameworks
- **Python**: pytest, unittest, nose2
- **JavaScript**: Jest, Mocha, Vitest
- **E2E**: Playwright, Cypress, Selenium
- **API**: Postman, REST Assured, httpx
- **Performance**: Locust, k6, JMeter

### Test Types

#### Unit Tests
```python
import pytest

def test_calculate_total():
    """Test the calculate_total function."""
    items = [
        {"price": 10.00, "quantity": 2},
        {"price": 5.00, "quantity": 3}
    ]
    result = calculate_total(items)
    assert result == 35.00

def test_calculate_total_empty():
    """Test with empty item list."""
    result = calculate_total([])
    assert result == 0.00

def test_calculate_total_invalid():
    """Test with invalid input."""
    with pytest.raises(ValueError):
        calculate_total(None)
```

#### Integration Tests
```python
@pytest.mark.integration
async def test_create_user_flow():
    """Test complete user creation flow."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create user
        response = await client.post("/api/users", json={
            "email": "test@example.com",
            "name": "Test User"
        })
        assert response.status_code == 201
        user_id = response.json()["id"]

        # Verify user exists
        response = await client.get(f"/api/users/{user_id}")
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"
```

#### E2E Tests
```python
from playwright.sync_api import Page, expect

def test_login_flow(page: Page):
    """Test complete login flow."""
    page.goto("/login")

    page.fill("[data-testid='email-input']", "user@example.com")
    page.fill("[data-testid='password-input']", "password123")
    page.click("[data-testid='login-button']")

    expect(page).to_have_url("/dashboard")
    expect(page.locator("[data-testid='welcome-message']")).to_be_visible()
```

## Test Design Patterns

### Arrange-Act-Assert
```python
def test_user_registration():
    # Arrange
    user_data = {"email": "new@test.com", "password": "secure123"}

    # Act
    result = register_user(user_data)

    # Assert
    assert result.success is True
    assert result.user.email == user_data["email"]
```

### Test Fixtures
```python
@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User(
        id="user-123",
        email="test@example.com",
        name="Test User"
    )

@pytest.fixture
async def database_session():
    """Create a test database session."""
    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()
```

### Mocking
```python
from unittest.mock import Mock, patch

@patch('services.email.send_email')
def test_registration_sends_email(mock_send):
    """Test that registration sends welcome email."""
    mock_send.return_value = True

    register_user({"email": "test@example.com"})

    mock_send.assert_called_once()
    assert "welcome" in mock_send.call_args[1]["subject"].lower()
```

## Coverage Standards

### Minimum Requirements
| Component | Minimum Coverage |
|-----------|------------------|
| Core Business Logic | 90% |
| API Endpoints | 85% |
| Utilities | 80% |
| Overall | 80% |

### Coverage Report
```json
{
  "overall": 0.85,
  "by_file": {
    "src/services/user.py": 0.92,
    "src/services/payment.py": 0.88,
    "src/routes/api.py": 0.82
  },
  "uncovered_lines": {
    "src/services/user.py": [45, 67, 89],
    "src/services/payment.py": [123, 125]
  }
}
```

## Test Organization

### Directory Structure
```
tests/
├── conftest.py          # Shared fixtures
├── unit/                # Unit tests
│   ├── test_models.py
│   └── test_services.py
├── integration/         # Integration tests
│   ├── test_api.py
│   └── test_database.py
├── e2e/                 # End-to-end tests
│   └── test_flows.py
├── performance/         # Performance tests
│   └── test_load.py
└── fixtures/            # Test data
    └── sample_data.json
```

### Naming Conventions
- Test files: `test_<module>.py`
- Test functions: `test_<what>_<condition>_<expected>`
- Example: `test_login_invalid_password_returns_401`

## Performance Testing

### Load Test Example
```python
from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def view_items(self):
        self.client.get("/api/items")

    @task(1)
    def create_item(self):
        self.client.post("/api/items", json={
            "name": "Test Item",
            "price": 9.99
        })
```

### Performance Targets
| Metric | Target |
|--------|--------|
| Response Time (p50) | < 100ms |
| Response Time (p95) | < 500ms |
| Response Time (p99) | < 1s |
| Error Rate | < 0.1% |
| Throughput | > 1000 rps |

## Output Artifacts

### Test Results
```json
{
  "test_results": {
    "total": 150,
    "passed": 145,
    "failed": 3,
    "skipped": 2
  },
  "coverage": {
    "overall": 0.85
  },
  "performance": {
    "passed": true,
    "avg_response_ms": 45
  }
}
```

### Generated Tests
- Unit test files
- Integration test files
- E2E test files
- Test fixtures
- Mock data

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0.0 | 2024-01-01 | Initial release |
