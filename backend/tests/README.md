# FinVault Backend Test Suite

This directory contains comprehensive tests for the FinVault backend API, covering all major components and functionality.

## Test Structure

### Core Test Files

- **`conftest.py`** - Test configuration, fixtures, and mocks
- **`test_risk_engine.py`** - Risk scoring and fraud detection tests
- **`test_email_service.py`** - Email service functionality tests
- **`test_audit_log_service.py`** - Audit logging tests
- **`test_auth_api.py`** - Authentication API endpoint tests
- **`test_telemetry_service.py`** - Telemetry recording tests

### Test Categories

#### Unit Tests

- Service layer testing (risk engine, email, audit logging, telemetry)
- Business logic validation
- Data transformation and processing

#### Integration Tests

- API endpoint testing with HTTP requests
- Database operations with test sessions
- External service mocking (Redis, MongoDB, SMTP)

#### Mock Strategy

- **Redis**: Mocked for session storage and caching
- **MongoDB**: Mocked for behavioral profiles and telemetry
- **SMTP**: Mocked for email sending
- **External APIs**: Mocked for geo-IP lookups

## Running Tests

### Prerequisites

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set up environment variables (optional for most tests):

```bash
cp .env.example .env
# Edit .env with test-specific values
```

### Run All Tests

```bash
# From backend directory
python run_tests.py

# Or directly with pytest
pytest
```

### Run Specific Test Files

```bash
# Run risk engine tests
pytest tests/test_risk_engine.py -v

# Run authentication API tests
pytest tests/test_auth_api.py -v

# Run email service tests
pytest tests/test_email_service.py -v
```

### Run Tests with Coverage

```bash
pytest --cov=app --cov-report=html
```

## Test Fixtures

### Database Fixtures

- **`test_db_session`**: Async SQLAlchemy session for database operations
- **`sample_user`**: Pre-created test user for authentication tests
- **`sample_transaction`**: Test transaction data

### HTTP Client Fixtures

- **`async_client`**: HTTPX async client for API testing
- **`client`**: FastAPI test client for synchronous testing

### Mock Fixtures

- **`mock_redis`**: Mock Redis client
- **`mock_mongo`**: Mock MongoDB client
- **`mock_smtp`**: Mock SMTP server for email testing

### Data Fixtures

- **`sample_device_metrics`**: Realistic device fingerprinting data
- **`sample_geo_data`**: Geographic location data
- **`sample_behavioral_data`**: Typing and mouse behavior data

## Test Coverage

The test suite covers:

### Risk Engine (15+ test cases)

- Transaction scoring algorithms
- Device fingerprint penalties
- Geographic location analysis
- Typing behavior analysis
- Risk level classification

### Email Service (5+ test cases)

- Email sending with configuration
- Error handling and retries
- SMTP connection management
- Template rendering

### Audit Logging (8+ test cases)

- Event logging functionality
- Login attempt tracking
- Transaction auditing
- Admin action logging

### Authentication API (12+ test cases)

- User registration and validation
- Login with various scenarios
- Token-based authentication
- Password security requirements
- Error handling

### Telemetry Service (6+ test cases)

- Device data recording
- Network analysis
- Known network management
- Data retention policies

## Mocking Strategy

### External Dependencies

- **Redis**: All Redis operations are mocked to avoid test dependencies
- **MongoDB**: Behavioral profiles and telemetry storage mocked
- **SMTP**: Email sending mocked with success/failure scenarios
- **Geo-IP Services**: External IP lookup services mocked

### Test Data

- **Realistic Data**: Uses faker library for realistic test data
- **Edge Cases**: Includes invalid data, boundary conditions
- **Security**: Tests for SQL injection, XSS prevention

## Best Practices

### Test Organization

- Each test file focuses on a single service/component
- Test classes group related functionality
- Descriptive test method names

### Async Testing

- Uses `pytest-asyncio` for async test support
- Proper async fixture handling
- Database session cleanup

### Error Testing

- Tests both success and failure scenarios
- Validates error messages and status codes
- Exception handling verification

### Performance

- Fast test execution with comprehensive mocking
- Minimal external dependencies
- Parallel test execution support

## Continuous Integration

The test suite is designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    cd backend
    pip install -r requirements.txt
    pytest --cov=app --cov-report=xml
```

## Adding New Tests

### 1. Create Test File

```python
# tests/test_new_service.py
import pytest
from app.services.new_service import NewService

class TestNewService:
    @pytest.mark.asyncio
    async def test_new_functionality(self, test_db_session):
        # Test implementation
        pass
```

### 2. Add Fixtures (if needed)

Update `conftest.py` with new fixtures for your tests.

### 3. Update Documentation

Add new test cases to this README.

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Database Errors**: Check test database configuration
3. **Async Errors**: Verify `pytest-asyncio` is installed
4. **Mock Errors**: Ensure proper mock setup in fixtures

### Debug Mode

```bash
# Run with detailed output
pytest -v -s --tb=long

# Run specific failing test
pytest tests/test_problematic.py::TestClass::test_method -v -s
```

## Contributing

When adding new features:

1. Add corresponding tests
2. Ensure test coverage > 80%
3. Update this documentation
4. Follow existing patterns and naming conventions

## Test Metrics

- **Total Tests**: 50+
- **Coverage Target**: 80%+
- **Execution Time**: < 30 seconds
- **Parallel Execution**: Supported
