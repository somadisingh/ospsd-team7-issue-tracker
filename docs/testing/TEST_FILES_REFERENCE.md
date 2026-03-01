# Test Files Reference

Quick reference guide for all test files and their contents.

## Unit Tests - Abstract Interfaces

### [board_tests.py](components/issue_tracker_client_api/tests/board_tests.py)
**Purpose:** Test the Board abstract class interface

**Test Classes:**
- `TestBoardAbstractClass` - Abstract class behavior
  - `test_board_is_abstract` - Board cannot be instantiated
  - `test_board_is_abc` - Board inherits from ABC
  - `test_board_has_id_property` - id property exists
  - `test_board_has_name_property` - name property exists
  - `test_concrete_board_implementation` - Test concrete implementation
- `TestGetBoardFactory` - Factory function tests
  - `test_get_board_not_implemented` - Factory raises NotImplementedError

**Marked:** `@pytest.mark.unit`

---

### [client_tests.py](components/issue_tracker_client_api/tests/client_tests.py)
**Purpose:** Test the Client abstract class interface

**Test Classes:**
- `TestClientAbstractClass` - Abstract class behavior
  - `test_client_is_abstract` - Client cannot be instantiated
  - `test_client_is_abc` - Client inherits from ABC
  - `test_client_has_required_methods` - All required methods exist
  - `test_concrete_client_implementation` - Test concrete implementation
- `TestGetClientFactory` - Factory function tests
  - `test_get_client_not_implemented` - Factory raises NotImplementedError
  - `test_get_client_with_interactive_flag` - Interactive flag handling

**Marked:** `@pytest.mark.unit`

---

### [issue_tests.py](components/issue_tracker_client_api/tests/issue_tests.py)
**Purpose:** Test the Issue abstract class interface

**Test Classes:**
- `TestIssueAbstractClass` - Abstract class behavior
  - `test_issue_is_abstract` - Issue cannot be instantiated
  - `test_issue_is_abc` - Issue inherits from ABC
  - `test_issue_has_id_property` - id property exists
  - `test_issue_has_title_property` - title property exists
  - `test_issue_has_is_complete_property` - is_complete property exists
  - `test_issue_has_list_id_property` - list_id property exists
  - `test_issue_has_board_id_property` - board_id property exists
  - `test_concrete_issue_implementation` - Test concrete implementation
- `TestGetIssueFactory` - Factory function tests
  - `test_get_issue_not_implemented` - Factory raises NotImplementedError
  - `test_get_issue_marks_abstract_interface` - Function is callable

**Marked:** `@pytest.mark.unit`

---

### [member_tests.py](components/issue_tracker_client_api/tests/member_tests.py)
**Purpose:** Test the Member abstract class interface

**Test Classes:**
- `TestMemberAbstractClass` - Abstract class behavior
  - `test_member_is_abstract` - Member cannot be instantiated
  - `test_member_is_abc` - Member inherits from ABC
  - `test_member_has_id_property` - id property exists
  - `test_member_has_username_property` - username property exists
  - `test_member_has_is_board_member_property` - is_board_member property exists
  - `test_concrete_member_implementation` - Test concrete implementation
  - `test_member_with_none_properties` - Test None property values
- `TestGetMemberFactory` - Factory function tests
  - `test_get_member_not_implemented` - Factory raises NotImplementedError

**Marked:** `@pytest.mark.unit`

---

## Unit Tests - Concrete Implementation

### [board_test.py](components/trello_client_impl/tests/board_test.py)
**Purpose:** Test the TrelloBoard concrete implementation of Board interface

**Test Classes:**
- `TestTrelloBoard` - TrelloBoard (Board implementation) tests
  - `test_trello_board_initialization` - Board creation
  - `test_trello_board_from_api` - Static factory method from API response
  - `test_trello_board_properties` - Property access (id, name)

**Marked:** `@pytest.mark.unit`

---

### [client_test.py](components/trello_client_impl/tests/client_test.py)
**Purpose:** Test the TrelloClient concrete implementation and factory functions

**Test Classes:**
- `TestTrelloClient` - TrelloClient (Client implementation) tests
  - `test_trello_client_initialization` - Client creation
  - `test_trello_client_interactive_mode` - Interactive flag handling
  - `test_trello_client_api_key_from_env` - Environment variable loading
  - `test_trello_client_token_property` - Token property access
  - `test_trello_client_token_raises_when_missing` - Error handling for missing token
  - `test_trello_client_query_method` - Query parameter building with credentials
  - `test_trello_client_get_issue` - get_issue with mocked requests
  - `test_trello_client_delete_issue` - delete_issue with mocked requests
  - `test_trello_client_update_status_moves_issue_to_list` - update_status moves issue when status_list_ids set
  - `test_trello_client_update_status_unknown_status_no_op` - update_status no-op for unknown status
  - `test_trello_client_assign_issue` - assign_issue with mocked requests
  - `test_trello_client_get_board` - get_board with mocked requests
  - `test_trello_client_get_members_on_issue` - get_members_on_issue with mocked requests
  - `test_trello_client_get_issues_in_list` - get_issues_in_list returns issues in list
- `TestGetClientImpl` - Factory function tests
  - `test_get_client_impl_returns_trello_client` - Factory returns TrelloClient instance
  - `test_get_client_impl_with_interactive_flag` - Interactive flag passed through factory
- `TestRegister` - Register function tests
  - `test_register_function_exists` - Register function is callable

**Marked:** `@pytest.mark.unit`
**Mocking:** All requests to Trello API are mocked

---

### [issue_test.py](components/trello_client_impl/tests/issue_test.py)
**Purpose:** Test the TrelloCard concrete implementation of Issue interface

**Test Classes:**
- `TestTrelloCard` - TrelloCard (Issue implementation) tests
  - `test_trello_issue_initialization` - Issue creation and properties
  - `test_trello_card_from_api` - Static factory method from API response
  - `test_trello_card_properties` - Property access (id, title, is_complete, list_id, board_id)

**Marked:** `@pytest.mark.unit`

---

### [member_test.py](components/trello_client_impl/tests/member_test.py)
**Purpose:** Test the TrelloMember concrete implementation of Member interface

**Test Classes:**
- `TestTrelloMember` - TrelloMember (Member implementation) tests
  - `test_trello_member_initialization` - Member creation
  - `test_trello_member_from_api` - Static factory method from API response
  - `test_trello_member_optional_fields` - Optional field handling (username, is_board_member)

**Marked:** `@pytest.mark.unit`

---

## Integration Tests

### [integration_tests.py](tests/integration/integration_tests.py)
**Purpose:** Test component interactions and interface compliance

**Test Classes:**
- `TestClientInterfaceImplementation` - Verify TrelloClient implements Client
  - `test_trello_client_is_instance_of_client` - TrelloClient is a Client
  - `test_trello_client_implements_all_methods` - All methods implemented
- `TestTrelloCardInterfaceImplementation` - Verify TrelloCard implements Issue
  - `test_trello_card_is_instance_of_issue` - TrelloCard is an Issue
  - `test_trello_card_implements_issue_interface` - Interface implemented
- `TestTrelloBoardInterfaceImplementation` - Verify TrelloBoard implements Board
  - `test_trello_board_is_instance_of_board` - TrelloBoard is a Board
  - `test_trello_board_implements_board_interface` - Interface implemented
- `TestTrelloMemberInterfaceImplementation` - Verify TrelloMember implements Member
  - `test_trello_member_is_instance_of_member` - TrelloMember is a Member
  - `test_trello_member_implements_member_interface` - Interface implemented
- `TestClientWorkflows` - Multi-step workflows with mocked requests
  - `test_get_issue_and_update_status_workflow` - Get issue then update status
  - `test_get_board_and_lists_and_issues_workflow` - Get board then get lists and issues in list
  - `test_get_issue_members_workflow` - Get members on issue
- `TestFactoryFunctions` - Factory function integration tests
  - `test_get_client_impl_returns_proper_client` - Factory returns working client
  - `test_client_from_factory_is_usable` - Client performs operations

**Marked:** `@pytest.mark.integration`
**Mocking:** HTTP requests mocked, component interactions real

---

## End-to-End Tests

### [e2e_tests.py](tests/e2e/e2e_tests.py)
**Purpose:** Test against actual Trello API

**Test Classes:**
- `TestE2EClientInitialization` - Real client setup
  - `test_client_initialization_with_credentials` - Client initializes with real credentials
  - `test_client_can_build_api_queries` - API query building works
- `TestE2EClientOperations` - Real API operations
  - `test_get_board_from_api` - Fetch board from real API
  - `test_list_boards_from_api` - List user's boards from real API
  - `test_get_issues_in_list_workflow` - Get issues in list from real API
- `TestE2EErrorHandling` - Real error scenarios
  - `test_invalid_board_id_handling` - Invalid board ID handling
  - `test_invalid_issue_id_handling` - Invalid issue ID handling
- `TestE2EInterfaceCompliance` - Interface compliance to real API
  - `test_client_interface_compliance` - All methods present and callable
- `TestE2EAuthenticationFailure` - Authentication error handling
  - `test_invalid_token_handling` - Invalid token raises error

**Marked:** `@pytest.mark.e2e`
**Mocking:** None - real API calls
**Requirements:** TRELLO_API_KEY, TRELLO_TOKEN, TRELLO_BOARD_ID environment variables
**Auto-skip:** If credentials not available

---

## Fixture Reference

### API Component Fixtures ([components/issue_tracker_client_api/tests/conftest.py](components/issue_tracker_client_api/tests/conftest.py))
- `sample_board_data()` → `dict`
- `sample_issue_data()` → `dict`
- `sample_member_data()` → `dict`

### Trello Impl Fixtures ([components/trello_client_impl/tests/conftest.py](components/trello_client_impl/tests/conftest.py))
- `mock_requests()` → Mocked requests module
- `mock_os_environ()` → Mocked environment
- `trello_client_data()` → `dict`
- `mock_card_response()` → `dict`
- `mock_board_response()` → `dict`
- `mock_member_response()` → `dict`

### Integration Fixtures ([tests/integration/conftest.py](tests/integration/conftest.py))
- `mock_requests_integration()` → Mocked requests.request
- `integration_env_setup()` → Mocked environment
- `mock_client_implementation()` → Mock Client instance

### E2E Fixtures ([tests/e2e/conftest.py](tests/e2e/conftest.py))
- `e2e_skip_if_no_credentials()` → Fixture that skips if credentials missing
- `e2e_client_config()` → `dict` with credentials

---

## Coverage

Generate coverage: `pytest --cov=components --cov-report=term-missing --cov-report=html`

---

## Markers

| Marker | When to Use | Speed | Mocking |
|--------|------------|-------|---------|
| `@pytest.mark.unit` | Testing individual components | Fast (~seconds) | All deps mocked |
| `@pytest.mark.integration` | Testing interactions | Medium (~seconds) | HTTP mocked |
| `@pytest.mark.e2e` | Testing full system | Slow (~minutes) | No mocking |

---

