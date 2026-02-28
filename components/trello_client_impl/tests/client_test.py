"""Unit tests for the TrelloClient and related factory functions."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from trello_client_impl import (
    TrelloClient,
    get_client_impl,
    register,
)


@pytest.mark.unit
class TestTrelloClient:
    """Test the TrelloClient implementation with mocked requests."""

    @pytest.fixture
    def client_with_creds(self, trello_credentials: dict[str, str]) -> TrelloClient:
        """Create a TrelloClient with injected credentials."""
        return TrelloClient(**trello_credentials)

    def test_trello_client_initialization(self, trello_credentials: dict[str, str]) -> None:
        """Test TrelloClient can be initialized with credentials."""
        client = TrelloClient(**trello_credentials)
        assert client is not None
        assert client.interactive is False

    def test_trello_client_interactive_mode(
        self, trello_credentials: dict[str, str]
    ) -> None:
        """Test TrelloClient with interactive flag."""
        client = TrelloClient(**trello_credentials, interactive=True)
        assert client.interactive is True

    def test_trello_client_api_key_from_init(
        self, trello_credentials: dict[str, str]
    ) -> None:
        """Test TrelloClient stores API key from constructor."""
        client = TrelloClient(**trello_credentials)
        assert client.api_key == "test_api_key"

    def test_trello_client_token_property(
        self, trello_credentials: dict[str, str]
    ) -> None:
        """Test TrelloClient token property."""
        client = TrelloClient(**trello_credentials)
        assert client.token == "test_token"

    def test_trello_client_token_raises_when_missing(self) -> None:
        """Test TrelloClient raises ValueError when token not provided."""
        with pytest.raises(ValueError, match="api_key and token are required"):
            TrelloClient(api_key="key", token="")

    def test_trello_client_query_method(self, trello_credentials: dict[str, str]) -> None:
        """Test TrelloClient _query method includes credentials."""
        client = TrelloClient(**trello_credentials)
        query = client._query()
        assert "key" in query
        assert "token" in query
        assert query["key"] == "test_api_key"
        assert query["token"] == "test_token"

    def test_trello_client_get_issue(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_card_response: dict[str, Any],
    ) -> None:
        """Test TrelloClient.get_issue with mocked API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_card_response
        mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )

        issue = client_with_creds.get_issue("card_id")
        assert issue is not None

    def test_trello_client_delete_issue(
        self, client_with_creds: TrelloClient, mocker: MockerFixture
    ) -> None:
        """Test TrelloClient.delete_issue with mocked API call (archive then delete)."""
        mock_response = MagicMock()
        mock_request = mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )

        result = client_with_creds.delete_issue("card_id")
        assert result is True
        assert mock_request.call_count >= 2

    def test_trello_client_mark_complete(
        self, client_with_creds: TrelloClient, mocker: MockerFixture
    ) -> None:
        """Test TrelloClient.mark_complete with mocked API call."""
        mock_response = MagicMock()
        mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )

        result = client_with_creds.mark_complete("card_id")
        assert result is True

    def test_trello_client_update_status_complete(
        self, client_with_creds: TrelloClient, mocker: MockerFixture
    ) -> None:
        """Test TrelloClient.update_status with 'complete'."""
        mock_response = MagicMock()
        mock_request = mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )

        result = client_with_creds.update_status("card_id", "complete")
        assert result is True
        assert mock_request.call_count >= 1

    def test_trello_client_update_status_in_progress(
        self, client_with_creds: TrelloClient, mocker: MockerFixture
    ) -> None:
        """Test TrelloClient.update_status with 'in_progress'."""
        mock_response = MagicMock()
        mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )

        result = client_with_creds.update_status("card_id", "in_progress")
        assert result is True

    def test_trello_client_assign_issue(
        self, client_with_creds: TrelloClient, mocker: MockerFixture
    ) -> None:
        """Test TrelloClient.assign_issue with mocked API call."""
        mock_response = MagicMock()
        mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )

        result = client_with_creds.assign_issue("card_id", "member_id")
        assert result is True

    def test_trello_client_get_board(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_board_response: dict[str, str],
    ) -> None:
        """Test TrelloClient.get_board with mocked API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_board_response
        mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )

        board = client_with_creds.get_board("board_id")
        assert board is not None

    def test_trello_client_get_members_on_card(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_member_response: dict[str, Any],
    ) -> None:
        """Test TrelloClient.get_members_on_card with mocked API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = [mock_member_response]
        mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )

        members = client_with_creds.get_members_on_card("card_id")
        assert isinstance(members, list)

    def test_trello_client_get_issues(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_card_response: dict[str, Any],
    ) -> None:
        """Test TrelloClient.get_issues returns an iterator."""
        mock_response = MagicMock()
        mock_response.json.return_value = [mock_card_response]
        mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )

        issues = client_with_creds.get_issues(max_issues=10)
        assert hasattr(issues, "__iter__")

    def test_trello_client_get_issues_uses_boards_when_no_default_board(
        self,
        trello_credentials: dict[str, str],
        mocker: MockerFixture,
        mock_card_response: dict[str, Any],
    ) -> None:
        """Test get_issues fetches boards when board_id is not provided."""
        mock_response = MagicMock()
        mock_response.json.side_effect = [
            [{"id": "board_1", "name": "Board 1"}],
            [mock_card_response],
        ]
        mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )

        # Create client without board_id
        client = TrelloClient(
            api_key=trello_credentials["api_key"],
            token=trello_credentials["token"],
        )

        issues = list(client.get_issues(max_issues=10))
        assert len(issues) == 1
        assert issues[0].id == mock_card_response["id"]


@pytest.mark.unit
class TestGetClientImpl:
    """Test the get_client_impl factory function."""

    def test_get_client_impl_returns_trello_client(
        self, trello_credentials: dict[str, str]
    ) -> None:
        """Test get_client_impl returns a TrelloClient instance."""
        client = get_client_impl(**trello_credentials)
        assert isinstance(client, TrelloClient)

    def test_get_client_impl_with_interactive_flag(
        self, trello_credentials: dict[str, str]
    ) -> None:
        """Test get_client_impl passes interactive flag."""
        client = get_client_impl(**trello_credentials, interactive=True)
        assert isinstance(client, TrelloClient)
        assert client.interactive is True

    def test_get_client_impl_raises_without_credentials(self) -> None:
        """Test get_client_impl raises error without required credentials."""
        with pytest.raises(ValueError, match="Trello requires"):
            get_client_impl(api_key="key")  # Missing token


@pytest.mark.unit
class TestRegister:
    """Test the register function."""

    def test_register_function_exists(self) -> None:
        """Test that register function is callable."""
        assert callable(register)
