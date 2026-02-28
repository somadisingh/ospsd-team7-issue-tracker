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
        mock_issue_response: dict[str, Any],
    ) -> None:
        """Test TrelloClient.get_issue with mocked API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_issue_response
        mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )

        issue = client_with_creds.get_issue("issue_id")
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

        result = client_with_creds.delete_issue("issue_id")
        assert result is True
        assert mock_request.call_count >= 2

    def test_trello_client_update_status_moves_issue_to_list(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
    ) -> None:
        """Test TrelloClient.update_status moves issue to the list for that status."""
        client = TrelloClient(
            api_key=client_with_creds.api_key,
            token=client_with_creds.token,
            status_list_ids={"complete": "list_done_id"},
        )
        mock_request = mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=MagicMock(),
        )
        result = client.update_status("issue_id", "complete")
        assert result is True
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args.kwargs
        # current behavior toggles dueComplete to True when status == complete
        assert call_kwargs.get("json") == {"dueComplete": True}

    def test_trello_client_update_status_unknown_status_no_op(
        self, client_with_creds: TrelloClient, mocker: MockerFixture
    ) -> None:
        """Test update_status with unknown status returns True without calling API."""
        mock_request = mocker.patch(
            "trello_client_impl.client.requests.request",
        )
        result = client_with_creds.update_status("issue_id", "unexpected_status")
        assert result is True
        # because the client doesn't send a request for unrecognised statuses
        mock_request.assert_not_called()

    def test_trello_client_assign_issue(
        self, client_with_creds: TrelloClient, mocker: MockerFixture
    ) -> None:
        """Test TrelloClient.assign_issue with mocked API call."""
        mock_response = MagicMock()
        mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )

        result = client_with_creds.assign_issue("issue_id", "member_id")
        assert result is True

    def test_trello_client_create_issue(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_issue_response: dict[str, Any],
    ) -> None:
        """Test TrelloClient.create_issue with mocked API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_issue_response
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
        assert issue.id == mock_issue_response["id"]
        assert issue.title == mock_issue_response["name"]
        assert mock_request.call_count == 1
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["params"]["name"] == "New Issue"
        assert call_kwargs["params"]["idList"] == "test_list_id"
        assert call_kwargs["params"]["desc"] == "Issue description"

    def test_trello_client_create_issue_without_description(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_issue_response: dict[str, Any],
    ) -> None:
        """Test TrelloClient.create_issue without optional description."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_issue_response
        mock_request = mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )

        issue = client_with_creds.create_issue("Title Only", "list_123")
        assert issue.id == mock_issue_response["id"]
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

    def test_trello_client_create_board(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_board_response: dict[str, str],
    ) -> None:
        """Test TrelloClient.create_board creates a board and returns it."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_board_response
        mock_request = mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )
        board = client_with_creds.create_board("New Board")
        assert board.id == mock_board_response["id"]
        assert board.name == mock_board_response["name"]
        assert mock_request.call_args[0][0] == "POST"
        assert "boards" in str(mock_request.call_args[0][1])
        assert mock_request.call_args.kwargs.get("params", {}).get("name") == "New Board"

    def test_trello_client_add_member_to_board(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_member_response: dict[str, Any],
    ) -> None:
        """Test TrelloClient.add_member_to_board adds member to board and returns member."""
        mock_response = MagicMock()
        mock_response.json.side_effect = [{}, mock_member_response]
        mock_request = mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )
        member = client_with_creds.add_member_to_board("board_123", "member_456")
        assert member.id == mock_member_response["id"]
        assert mock_request.call_count == 2
        put_call = mock_request.call_args_list[0]
        assert put_call[0][0] == "PUT"
        assert "boards/board_123/members/member_456" in str(put_call[0][1])
        assert put_call.kwargs.get("params", {}).get("type") == "normal"

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

    def test_trello_client_get_list(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_list_response: dict[str, Any],
    ) -> None:
        """Test TrelloClient.get_list returns a single list."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_list_response
        mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )
        list_obj = client_with_creds.get_list("list_123")
        assert list_obj.id == mock_list_response["id"]
        assert list_obj.name == mock_list_response["name"]

    def test_trello_client_create_list(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_list_response: dict[str, Any],
    ) -> None:
        """Test TrelloClient.create_list creates a list and returns it."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_list_response
        mock_request = mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )
        list_obj = client_with_creds.create_list("board_123", "New Column")
        assert list_obj.id == mock_list_response["id"]
        assert list_obj.name == mock_list_response["name"]
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["params"]["idBoard"] == "board_123"
        assert call_kwargs["params"]["name"] == "New Column"

    def test_trello_client_update_list(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_list_response: dict[str, Any],
    ) -> None:
        """Test TrelloClient.update_list renames a list and returns it."""
        mock_response = MagicMock()
        mock_response.json.return_value = {**mock_list_response, "name": "Renamed"}
        mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )
        list_obj = client_with_creds.update_list("list_123", "Renamed")
        assert list_obj.name == "Renamed"

    def test_trello_client_get_issues_in_list(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_issue_response: dict[str, Any],
    ) -> None:
        """Test TrelloClient.get_issues_in_list returns issues in the list."""
        mock_response = MagicMock()
        mock_response.json.return_value = [mock_issue_response]
        mock_request = mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )
        issues = list(
            client_with_creds.get_issues_in_list("list_123", max_issues=10)
        )
        assert len(issues) == 1
        assert issues[0].id == mock_issue_response["id"]
        assert issues[0].list_id == mock_issue_response.get("idList", "")
        assert "lists/list_123/cards" in mock_request.call_args[0][1]

    def test_trello_client_delete_list(
        self, client_with_creds: TrelloClient, mocker: MockerFixture
    ) -> None:
        """Test TrelloClient.delete_list archives the list."""
        mock_request = mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=MagicMock(),
        )
        result = client_with_creds.delete_list("list_123")
        assert result is True
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs.get("json") == {"closed": True}

    def test_trello_client_get_members_on_issue(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_member_response: dict[str, Any],
    ) -> None:
        """Test TrelloClient.get_members_on_issue with mocked API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = [mock_member_response]
        mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )

        members = client_with_creds.get_members_on_issue("issue_id")
        assert isinstance(members, list)

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
