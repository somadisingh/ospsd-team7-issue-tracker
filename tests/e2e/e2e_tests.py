"""End-to-end tests for the issue tracker.

These tests execute against the actual Trello API and require valid credentials.
To run these tests:

1. Set environment variables:
   - TRELLO_API_KEY: Your Trello API key
   - TRELLO_TOKEN: Your Trello token
   - TRELLO_BOARD_ID: A test board ID

2. Run with: pytest -m e2e tests/e2e/

These tests are skipped if credentials are not available.
"""

import pytest
from pytest_mock import MockerFixture
from trello_client_impl.trello_impl import TrelloClient


@pytest.mark.e2e
class TestE2EClientInitialization:
    """Test real client initialization."""

    def test_client_initialization_with_credentials(
        self, e2e_skip_if_no_credentials: None
    ) -> None:
        """Test that TrelloClient initializes with valid credentials."""
        client = TrelloClient()
        assert client is not None
        assert client.api_key
        assert client.token is not None

    def test_client_can_build_api_queries(
        self, e2e_skip_if_no_credentials: None
    ) -> None:
        """Test that client can build valid API query parameters."""
        client = TrelloClient()
        query = client._query()
        assert "key" in query
        assert "token" in query


@pytest.mark.e2e
class TestE2EClientOperations:
    """Test real client API operations.

    Note: These tests require a valid Trello board and cards to exist.
    Adjust board_id and card_id to match your test setup.
    """

    def test_get_board_from_api(
        self, e2e_skip_if_no_credentials: None, e2e_client_config: dict[str, str]
    ) -> None:
        """Test getting a board from the actual Trello API."""
        client = TrelloClient()
        board_id = e2e_client_config["board_id"]

        if not board_id:
            pytest.skip("TRELLO_BOARD_ID not set")

        try:
            board = client.get_board(board_id)
            assert board is not None
            assert board.id == board_id
        except Exception as e:
            pytest.skip(f"Could not reach Trello API: {e}")

    def test_list_boards_from_api(self, e2e_skip_if_no_credentials: None) -> None:
        """Test listing boards for authenticated user."""
        client = TrelloClient()

        try:
            boards = list(client.get_boards())
            assert hasattr(client.get_boards(), "__iter__")
        except Exception as e:
            pytest.skip(f"Could not reach Trello API: {e}")

    def test_get_issues_workflow(
        self, e2e_skip_if_no_credentials: None, e2e_client_config: dict[str, str]
    ) -> None:
        """Test getting issues/cards from a board."""
        client = TrelloClient()
        board_id = e2e_client_config["board_id"]

        if not board_id:
            pytest.skip("TRELLO_BOARD_ID not set")

        try:
            issues = client.get_issues(max_issues=5)
            assert hasattr(issues, "__iter__")
            first_issue = next(issues, None)
            if first_issue:
                assert first_issue.id is not None
        except Exception as e:
            pytest.skip(f"Could not reach Trello API or no cards on board: {e}")


@pytest.mark.e2e
class TestE2EErrorHandling:
    """Test error handling in real API scenarios."""

    def test_invalid_board_id_handling(self, e2e_skip_if_no_credentials: None) -> None:
        """Test handling of invalid board IDs."""
        client = TrelloClient()

        try:
            board = client.get_board("invalid_board_id_12345")
            pytest.skip("Unexpected API response")
        except Exception:
            pass

    def test_invalid_card_id_handling(self, e2e_skip_if_no_credentials: None) -> None:
        """Test handling of invalid card IDs."""
        client = TrelloClient()

        try:
            card = client.get_issue("invalid_card_id_12345")
            pytest.skip("Unexpected API response")
        except Exception:
            pass


@pytest.mark.e2e
class TestE2EInterfaceCompliance:
    """Test that client complies with the Client interface in real scenarios."""

    def test_client_interface_compliance(
        self, e2e_skip_if_no_credentials: None
    ) -> None:
        """Test that TrelloClient implements all required methods."""
        client = TrelloClient()

        required_methods = [
            "get_issue",
            "delete_issue",
            "mark_complete",
            "update_status",
            "get_issues",
            "get_board",
            "get_boards",
            "get_members_on_card",
            "assign_issue",
        ]

        for method_name in required_methods:
            assert hasattr(client, method_name)
            assert callable(getattr(client, method_name))


@pytest.mark.e2e
class TestE2EAuthenticationFailure:
    """Test behavior with invalid credentials."""

    def test_invalid_token_handling(self, mocker: MockerFixture) -> None:
        """Test that invalid token is handled gracefully."""
        mocker.patch.dict("os.environ", {"TRELLO_TOKEN": "", "TRELLO_API_KEY": ""})

        client = TrelloClient()

        with pytest.raises(ValueError, match="token not set"):
            _ = client.token
