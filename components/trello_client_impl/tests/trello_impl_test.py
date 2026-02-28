"""Unit tests for the Trello client implementation."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from trello_client_impl.trello_impl import (
    TrelloBoard,
    TrelloCard,
    TrelloClient,
    TrelloMember,
    get_client_impl,
    register,
)


@pytest.mark.unit
class TestTrelloCard:
    """Test the TrelloCard implementation."""

    def test_trello_card_initialization(self) -> None:
        """Test TrelloCard can be initialized with required fields."""
        card = TrelloCard(
            id="card_123",
            title="Test Card",
            is_complete=False,
            desc="Test description",
            due="2026-02-15",
            id_board="board_123",
            id_list="list_123",
        )
        assert card.id == "card_123"
        assert card.title == "Test Card"
        assert card.is_complete is False
        assert card.desc == "Test description"
        assert card.due == "2026-02-15"

    def test_trello_card_from_api(self, mock_card_response: Any) -> None:
        """Test TrelloCard.from_api static method."""
        card = TrelloCard.from_api(mock_card_response)
        assert card.id == mock_card_response["id"]

    def test_trello_card_properties(self) -> None:
        """Test TrelloCard properties are accessible."""
        card = TrelloCard(
            id="test_id",
            title="Test",
            is_complete=True,
            desc="Test",
            due="2026-02-15",
            id_board="board_1",
            id_list="list_1",
        )
        assert hasattr(card, "id")
        assert hasattr(card, "title")
        assert hasattr(card, "is_complete")
        assert hasattr(card, "desc")


@pytest.mark.unit
class TestTrelloBoard:
    """Test the TrelloBoard implementation."""

    def test_trello_board_initialization(self) -> None:
        """Test TrelloBoard can be initialized."""
        board = TrelloBoard(id="board_123", name="Test Board")
        assert board.id == "board_123"
        assert board.name == "Test Board"

    def test_trello_board_from_api(self, mock_board_response: Any) -> None:
        """Test TrelloBoard.from_api static method."""
        board = TrelloBoard.from_api(mock_board_response)
        assert board.id == mock_board_response["id"]
        assert board.name == mock_board_response["name"]

    def test_trello_board_properties(self) -> None:
        """Test TrelloBoard properties are accessible."""
        board = TrelloBoard(id="test_id", name="Test Board")
        assert hasattr(board, "id")
        assert hasattr(board, "name")
        assert board.id == "test_id"
        assert board.name == "Test Board"


@pytest.mark.unit
class TestTrelloMember:
    """Test the TrelloMember implementation."""

    def test_trello_member_initialization(self) -> None:
        """Test TrelloMember can be initialized."""
        member = TrelloMember(
            id="member_123", username="testuser", is_board_member=True
        )
        assert member.id == "member_123"
        assert member.username == "testuser"
        assert member.is_board_member is True

    def test_trello_member_from_api(self, mock_member_response: Any) -> None:
        """Test TrelloMember.from_api static method."""
        member = TrelloMember.from_api(mock_member_response)
        assert member.id == mock_member_response["id"]

    def test_trello_member_optional_fields(self) -> None:
        """Test TrelloMember with optional fields."""
        member = TrelloMember(id="member_123", username=None, is_board_member=None)
        assert member.id == "member_123"
        assert member.username is None
        assert member.is_board_member is None


@pytest.mark.unit
class TestTrelloClient:
    """Test the TrelloClient implementation with mocked requests."""

    @pytest.fixture
    def client_with_env(self, mock_os_environ: Any) -> TrelloClient:
        """Create a TrelloClient with mocked environment."""
        return TrelloClient()

    def test_trello_client_initialization(self, mock_os_environ: Any) -> None:
        """Test TrelloClient can be initialized."""
        client = TrelloClient()
        assert client is not None
        assert client.interactive is False

    def test_trello_client_interactive_mode(self, mock_os_environ: Any) -> None:
        """Test TrelloClient with interactive flag."""
        client = TrelloClient(interactive=True)
        assert client.interactive is True

    def test_trello_client_api_key_from_env(self, mock_os_environ: Any) -> None:
        """Test TrelloClient loads API key from environment."""
        client = TrelloClient()
        assert client.api_key == "test_api_key"

    def test_trello_client_token_property(self, mock_os_environ: Any) -> None:
        """Test TrelloClient token property."""
        client = TrelloClient()
        assert client.token == "test_token"

    def test_trello_client_token_raises_when_missing(
        self, mocker: MockerFixture
    ) -> None:
        """Test TrelloClient.token raises ValueError when token not set."""
        mocker.patch.dict(
            "os.environ",
            {"TRELLO_API_KEY": "key", "TRELLO_TOKEN": ""},
            clear=False,
        )
        mocker.patch(
            "trello_client_impl.trello_impl.Path.cwd",
            return_value=__import__("pathlib").Path("/nonexistent"),
        )
        client = TrelloClient()
        object.__setattr__(client, "_token", None)
        with pytest.raises(ValueError, match="token not set"):
            _ = client.token

    def test_trello_client_query_method(self, mock_os_environ: Any) -> None:
        """Test TrelloClient _query method includes credentials."""
        client = TrelloClient()
        query = client._query()
        assert "key" in query
        assert "token" in query
        assert query["key"] == "test_api_key"
        assert query["token"] == "test_token"

    def test_trello_client_get_issue(
        self,
        client_with_env: TrelloClient,
        mocker: MockerFixture,
        mock_card_response: dict[str, Any],
    ) -> None:
        """Test TrelloClient.get_issue with mocked API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_card_response
        mocker.patch(
            "trello_client_impl.trello_impl.requests.request",
            return_value=mock_response,
        )

        client = TrelloClient()
        client.api_key = "test_key"
        client._token = "test_token"

        issue = client.get_issue("card_id")
        assert issue is not None

    def test_trello_client_delete_issue(
        self, client_with_env: TrelloClient, mocker: MockerFixture
    ) -> None:
        """Test TrelloClient.delete_issue with mocked API call (archive then delete)."""
        mock_response = MagicMock()
        mock_request = mocker.patch(
            "trello_client_impl.trello_impl.requests.request",
            return_value=mock_response,
        )

        client = TrelloClient()
        client.api_key = "test_key"
        client._token = "test_token"

        result = client.delete_issue("card_id")
        assert result is True
        assert mock_request.call_count >= 2

    def test_trello_client_mark_complete(
        self, client_with_env: TrelloClient, mocker: MockerFixture
    ) -> None:
        """Test TrelloClient.mark_complete with mocked API call."""
        mock_response = MagicMock()
        mocker.patch(
            "trello_client_impl.trello_impl.requests.request",
            return_value=mock_response,
        )

        client = TrelloClient()
        client.api_key = "test_key"
        client._token = "test_token"

        result = client.mark_complete("card_id")
        assert result is True

    def test_trello_client_update_status_complete(
        self, client_with_env: TrelloClient, mocker: MockerFixture
    ) -> None:
        """Test TrelloClient.update_status with 'complete'."""
        mock_response = MagicMock()
        mock_request = mocker.patch(
            "trello_client_impl.trello_impl.requests.request",
            return_value=mock_response,
        )

        client = TrelloClient()
        client.api_key = "test_key"
        client._token = "test_token"

        result = client.update_status("card_id", "complete")
        assert result is True
        assert mock_request.call_count >= 1

    def test_trello_client_update_status_in_progress(
        self, client_with_env: TrelloClient, mocker: MockerFixture
    ) -> None:
        """Test TrelloClient.update_status with 'in_progress'."""
        mock_response = MagicMock()
        mocker.patch(
            "trello_client_impl.trello_impl.requests.request",
            return_value=mock_response,
        )

        client = TrelloClient()
        client.api_key = "test_key"
        client._token = "test_token"

        result = client.update_status("card_id", "in_progress")
        assert result is True

    def test_trello_client_assign_issue(
        self, client_with_env: TrelloClient, mocker: MockerFixture
    ) -> None:
        """Test TrelloClient.assign_issue with mocked API call."""
        mock_response = MagicMock()
        mocker.patch(
            "trello_client_impl.trello_impl.requests.request",
            return_value=mock_response,
        )

        client = TrelloClient()
        client.api_key = "test_key"
        client._token = "test_token"

        result = client.assign_issue("card_id", "member_id")
        assert result is True

    def test_trello_client_get_board(
        self,
        client_with_env: TrelloClient,
        mocker: MockerFixture,
        mock_board_response: dict[str, str],
    ) -> None:
        """Test TrelloClient.get_board with mocked API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_board_response
        mocker.patch(
            "trello_client_impl.trello_impl.requests.request",
            return_value=mock_response,
        )

        client = TrelloClient()
        client.api_key = "test_key"
        client._token = "test_token"

        board = client.get_board("board_id")
        assert board is not None

    def test_trello_client_get_members_on_card(
        self,
        client_with_env: TrelloClient,
        mocker: MockerFixture,
        mock_member_response: dict[str, Any],
    ) -> None:
        """Test TrelloClient.get_members_on_card with mocked API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = [mock_member_response]
        mocker.patch(
            "trello_client_impl.trello_impl.requests.request",
            return_value=mock_response,
        )

        client = TrelloClient()
        client.api_key = "test_key"
        client._token = "test_token"

        members = client.get_members_on_card("card_id")
        assert isinstance(members, list)

    def test_trello_client_get_issues(
        self,
        client_with_env: TrelloClient,
        mocker: MockerFixture,
        mock_card_response: dict[str, Any],
    ) -> None:
        """Test TrelloClient.get_issues returns an iterator."""
        mock_response = MagicMock()
        mock_response.json.return_value = [mock_card_response]
        mocker.patch(
            "trello_client_impl.trello_impl.requests.request",
            return_value=mock_response,
        )

        client = TrelloClient()
        client.api_key = "test_key"
        client._token = "test_token"
        client._default_board_id = "board_id"

        issues = client.get_issues(max_issues=10)
        assert hasattr(issues, "__iter__")

    def test_trello_client_get_issues_uses_boards_when_no_default_board(
        self,
        client_with_env: TrelloClient,
        mocker: MockerFixture,
        mock_card_response: dict[str, Any],
    ) -> None:
        """Test get_issues fetches boards when _default_board_id is not set."""
        mock_response = MagicMock()
        mock_response.json.side_effect = [
            [{"id": "board_1", "name": "Board 1"}],
            [mock_card_response],
        ]
        mocker.patch(
            "trello_client_impl.trello_impl.requests.request",
            return_value=mock_response,
        )

        client = TrelloClient()
        client.api_key = "test_key"
        client._token = "test_token"
        client._default_board_id = None

        issues = list(client.get_issues(max_issues=10))
        assert len(issues) == 1
        assert issues[0].id == mock_card_response["id"]


@pytest.mark.unit
class TestGetClientImpl:
    """Test the get_client_impl factory function."""

    def test_get_client_impl_returns_trello_client(self, mock_os_environ: Any) -> None:
        """Test get_client_impl returns a TrelloClient instance."""
        client = get_client_impl()
        assert isinstance(client, TrelloClient)

    def test_get_client_impl_with_interactive_flag(self, mock_os_environ: Any) -> None:
        """Test get_client_impl passes interactive flag."""
        client = get_client_impl(interactive=True)
        assert isinstance(client, TrelloClient)
        assert client.interactive is True


@pytest.mark.unit
class TestRegister:
    """Test the register function."""

    def test_register_function_exists(self) -> None:
        """Test that register function is callable."""
        assert callable(register)
