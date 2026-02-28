"""
Comprehensive Testing Setup Guide
==================================

This project includes a complete testing framework with unit tests, integration tests,
and end-to-end (e2e) tests. All tests are configured with pytest and include coverage reporting.
"""

# Testing Framework Setup

## Overview

The testing framework includes:

### 1. **Unit Tests** (fast)
   - **Location**: `components/*/tests/`
   - **Marker**: `@pytest.mark.unit`
   - **Coverage**: Abstract interfaces and concrete implementations
   - **Mocking**: All external dependencies mocked

   **Components tested:**
   - `issue_tracker_client_api/tests/`:
     - `board_tests.py` - Board abstract class interface
     - `client_tests.py` - Client abstract class interface
     - `issue_tests.py` - Issue abstract class interface
     - `member_tests.py` - Member abstract class interface

   - `trello_client_impl/tests/`:
     - `board_test.py` - TrelloBoard (Board implementation) tests
     - `client_test.py` - TrelloClient and factory functions tests
     - `issue_test.py` - TrelloCard (Issue implementation) tests
     - `member_test.py` - TrelloMember (Member implementation) tests

### 2. **Integration Tests** (real dependencies)
   - **Location**: `tests/integration/`
   - **Marker**: `@pytest.mark.integration`
   - **Purpose**: Test components working together
   - **Mocking**: HTTP requests mocked, but component interactions are real

   **Test Coverage:**
   - Interface implementation compliance
   - Multi-step workflows
   - Factory functions
   - Inter-component communications

### 3. **End-to-End Tests** (full system)
   - **Location**: `tests/e2e/`
   - **Marker**: `@pytest.mark.e2e`
   - **Purpose**: Test against actual Trello API
   - **Mocking**: None - tests real API calls
   - **Requirements**: Valid Trello credentials

   **Test Coverage:**
   - Real API interactions
   - Error handling with actual responses
   - Interface compliance in production scenarios
   - Authentication workflows

## Directory Structure

```
ospsd-team-07/
├── pyproject.toml                        # test dependencies
│
├── components/
│   ├── issue_tracker_client_api/
│   │   ├── src/issue_tracker_client_api/ # Abstract interfaces
│   │   └── tests/
│   │       ├── conftest.py               # API test fixtures
│   │       ├── board_tests.py            # Board interface tests
│   │       ├── client_tests.py           # Client interface tests
│   │       ├── issue_tests.py            # Issue interface tests
│   │       └── member_tests.py           # Member interface tests
│   │
│   └── trello_client_impl/
│       ├── src/trello_client_impl/       # Concrete Trello implementation
│       └── tests/
│           ├── conftest.py               # Trello test fixtures
│           ├── board_test.py             # TrelloBoard tests
│           ├── client_test.py            # TrelloClient tests
│           ├── issue_test.py             # TrelloCard tests
│           └── member_test.py            # TrelloMember tests
│
└── tests/
    ├── integration/
    │   ├── conftest.py                   # Integration test fixtures
    │   └── integration_tests.py           # Component integration tests
    │
    └── e2e/
        ├── conftest.py                   # E2E test fixtures
        └── e2e_tests.py                  # End-to-end tests
```

## Installation & Setup

### 1. Install Dependencies

Using `uv` (recommended):
```bash
cd /path/to/ospsd-team-07
uv sync --all-extras
```

### 2. Verify Installation

```bash
pytest --version
pytest-cov --version
```

## Running Tests

### Run All Tests

```bash
# Run all tests with coverage
pytest

# Run all tests without coverage
pytest --no-cov
```

### Run Tests by Category

```bash
# Unit tests only (fast, ~seconds)
pytest -m unit

# Integration tests (medium, ~10-30 seconds)
pytest -m integration

# E2E tests (slow, requires credentials)
pytest -m e2e

# Unit + Integration tests (skip E2E)
pytest -m "unit or integration"
```

### Run Tests for Specific Component

```bash
# Test abstract interface
pytest components/issue_tracker_client_api/tests/ -v

# Test Trello implementation
pytest components/trello_client_impl/tests/ -v

# Test integration layer
pytest tests/integration/ -v
```

### Run Specific Test File

```bash
pytest components/issue_tracker_client_api/tests/client_tests.py -v
pytest components/trello_client_impl/tests/board_test.py -v
pytest components/trello_client_impl/tests/client_test.py -v
pytest components/trello_client_impl/tests/issue_test.py -v
pytest components/trello_client_impl/tests/member_test.py -v
```

### Run Specific Test Class or Function

```bash
# Run a specific test class
pytest components/issue_tracker_client_api/tests/client_tests.py::TestClientAbstractClass -v

# Run a specific test function
pytest components/issue_tracker_client_api/tests/client_tests.py::TestClientAbstractClass::test_client_is_abstract -v
```

## Coverage Reporting

### Generate Coverage Report

```bash
# Terminal report with missing lines highlighted
pytest --cov=components --cov-report=term-missing

# HTML coverage report (opens in browser)
pytest --cov=components --cov-report=html

# Open the HTML report
open htmlcov/index.html
```

### Coverage Settings

- **Minimum threshold**: 85% (configured in `pyproject.toml`)
- **Configuration file**: `.coveragerc`
- **HTML output directory**: `htmlcov/`

Current coverage thresholds:
- Exclude: `*/tests/*`, `*/__main__.py`
- Abstract methods: `@abstractmethod` excluded from coverage

## E2E Testing Setup

E2E tests require valid Trello credentials. They are automatically skipped if credentials are unavailable.

### Setting Up E2E Tests

1. **Get Trello Credentials:**
   - Visit: https://trello.com/app-key
   - Generate API key and token
   - Note your test board ID

2. **Set Environment Variables:**

   ```bash
   export TRELLO_API_KEY="your_api_key_here"
   export TRELLO_TOKEN="your_token_here"
   export TRELLO_BOARD_ID="your_test_board_id"
   ```

   Or create a `.env` file:
   ```
   TRELLO_API_KEY=your_api_key_here
   TRELLO_TOKEN=your_token_here
   TRELLO_BOARD_ID=your_test_board_id
   ```

3. **Run E2E Tests:**

   ```bash
   # Configure Python-dotenv to load .env file if present
   export $(cat .env | xargs)
   pytest -m e2e -v
   ```

### E2E Test Notes

- E2E tests may modify test data (use a dedicated test board)
- Some tests demonstrate expected API errors (they should pass)
- Network connectivity required
- Tests skip gracefully if credentials are missing

## Test Fixtures

### Component-Specific Fixtures

#### `issue_tracker_client_api/tests/conftest.py`
- `sample_board_data()` - Board fixture
- `sample_issue_data()` - Issue fixture
- `sample_member_data()` - Member fixture

#### `trello_client_impl/tests/conftest.py`
- `mock_requests()` - Mocked requests module
- `mock_os_environ()` - Mocked environment variables
- `trello_client_data()` - Client configuration
- `mock_card_response()` - Card API response
- `mock_board_response()` - Board API response
- `mock_member_response()` - Member API response

#### `tests/integration/conftest.py`
- `mock_requests_integration()` - Integration test requests mock
- `integration_env_setup()` - Environment setup for integration
- `mock_client_implementation()` - Mock client for integration tests

#### `tests/e2e/conftest.py`
- `e2e_skip_if_no_credentials()` - Skip tests if credentials missing
- `e2e_client_config()` - E2E test configuration

## Mocking Strategy

### Unit Tests
- **All external dependencies mocked**
- Use `pytest-mock` and `unittest.mock`
- Mocked: HTTP requests, file I/O, environment variables
- Real: Component logic, interfaces

### Integration Tests
- **HTTP layer mocked**
- Component interactions are real
- Mocked: `requests` library calls
- Real: Component interface implementations

### E2E Tests
- **No mocking**
- Real Trello API calls
- Real network I/O
- Entire system tested end-to-end

## Best Practices

### Writing Tests

1. **One assertion per test** (when possible)
   ```python
   def test_board_has_id_property(self):
       assert hasattr(Board, "id")
   ```

2. **Use descriptive test names**
   ```python
   def test_client_is_abstract()  # ✓ Good
   def test_client()               # ✗ Vague
   ```

3. **Use fixtures for setup**
   ```python
   def test_card_from_api(self, mock_card_response):
       card = TrelloCard.from_api(mock_card_response)
   ```

4. **Group related tests in classes**
   ```python
   @pytest.mark.unit
   class TestClientAbstractClass:
       def test_client_is_abstract(self): ...
       def test_client_has_required_methods(self): ...
   ```

5. **Mock external dependencies**
   ```python
   def test_get_issue(self, mocker, mock_card_response):
       mocker.patch("requests.request", return_value=mock_response)
   ```

### Running Tests Locally

```bash
# Watch mode (re-run on file changes) - requires pytest-watch
ptw

# Parallel execution (faster) - requires pytest-xdist
pytest -n auto

# Verbose output with print statements
pytest -vv -s

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf

# Run failed tests first
pytest --ff
```

## Troubleshooting

### Tests Not Found
```bash
# Ensure pytest can discover tests
pytest --collect-only

# Check Python path
pytest --collect-only -q
```

### Import Errors
```bash
# Check if components are installed in development mode
pip list | grep issue-tracker

# Reinstall if necessary
pip install -e components/issue_tracker_client_api
pip install -e components/trello_client_impl
```

### Coverage Too Low
```bash
# See which lines are not covered
pytest --cov=components --cov-report=term-missing

# Open HTML report to investigate
open htmlcov/index.html
```

### E2E Tests Skipped
```bash
# Check if credentials are set
echo $TRELLO_API_KEY
echo $TRELLO_TOKEN
echo $TRELLO_BOARD_ID

# If not set, configure them and retry
export TRELLO_API_KEY="your_key"
export TRELLO_TOKEN="your_token"
export TRELLO_BOARD_ID="your_board_id"
pytest -m e2e -v
```

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [pytest-mock Documentation](https://pytest-mock.readthedocs.io/)
- [Trello API Documentation](https://developer.atlassian.com/cloud/trello/rest/api-group-cards/)

## Contributing

When adding new tests:

1. Follow the existing structure and naming conventions
2. Mark tests with appropriate markers (`@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`)
3. Add descriptive docstrings to test functions and classes
4. Use fixtures for common setup
5. Keep tests isolated and independent
6. Maintain or improve coverage (target: 85%+)
7. Update this guide if adding new test categories or fixtures
