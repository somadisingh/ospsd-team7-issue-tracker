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

    def test_trello_client_initialization(
        self, trello_credentials: dict[str, str]
    ) -> None:
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

    def test_trello_client_query_method(
        self, trello_credentials: dict[str, str]
    ) -> None:
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

    def test_trello_client_update_status_moves_card_to_list(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
    ) -> None:
        """Test TrelloClient.update_status moves card when status_list_ids is set."""
        client = TrelloClient(
            api_key=client_with_creds.api_key,
            token=client_with_creds.token,
            status_list_ids={"complete": "list_done_id"},
        )
        mock_request = mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=MagicMock(),
        )
        result = client.update_status("card_id", "complete")
        assert result is True
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs.get("json") == {"idList": "list_done_id"}

    def test_trello_client_update_status_unknown_status_no_op(
        self, client_with_creds: TrelloClient
    ) -> None:
        """Test update_status with unknown status returns True without calling API."""
        result = client_with_creds.update_status("card_id", "complete")
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

    def test_trello_client_create_issue(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_card_response: dict[str, Any],
    ) -> None:
        """Test TrelloClient.create_issue with mocked API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_card_response
        mock_request = mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )

        issue = client_with_creds.create_issue(
            "New Issue",
            "test_list_id",
            description="Issue description",
        )
        assert issue is not None
        assert issue.id == mock_card_response["id"]
        assert issue.title == mock_card_response["name"]
        assert mock_request.call_count == 1
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["params"]["name"] == "New Issue"
        assert call_kwargs["params"]["idList"] == "test_list_id"
        assert call_kwargs["params"]["desc"] == "Issue description"

    def test_trello_client_create_issue_without_description(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_card_response: dict[str, Any],
    ) -> None:
        """Test TrelloClient.create_issue without optional description."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_card_response
        mock_request = mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )

        issue = client_with_creds.create_issue("Title Only", "list_123")
        assert issue.id == mock_card_response["id"]
        assert "desc" not in mock_request.call_args.kwargs["params"]

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

    def test_trello_client_get_lists(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_list_response: dict[str, Any],
    ) -> None:
        """Test TrelloClient.get_lists returns an iterator of lists."""
        mock_response = MagicMock()
        mock_response.json.return_value = [mock_list_response]
        mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )

        lists = list(client_with_creds.get_lists("board_123"))
        assert len(lists) == 1
        assert lists[0].id == mock_list_response["id"]
        assert lists[0].name == mock_list_response["name"]

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
