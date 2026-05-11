"""Unit tests for the TrelloClient and related factory functions."""

from typing import Any
from unittest.mock import MagicMock

import pytest
import requests as requests_lib
from api.issue import Status
from issue_tracker_client_api.exceptions import (
    AuthenticationError,
    IssueTrackerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from pytest_mock import MockerFixture
from trello_client_impl import (
    TrelloClient,
    get_client_impl,
    register,
)


def _mock_list_response(
    list_id: str = "list_1", name: str = "To Do", board_id: str = "board_1"
) -> dict[str, Any]:
    return {"id": list_id, "name": name, "idBoard": board_id}


@pytest.mark.unit
class TestTrelloClient:
    """Test the TrelloClient implementation with mocked requests."""

    @pytest.fixture
    def client_with_creds(self, trello_credentials: dict[str, Any]) -> TrelloClient:
        return TrelloClient(**trello_credentials)

    def test_trello_client_initialization(
        self, trello_credentials: dict[str, Any]
    ) -> None:
        client = TrelloClient(**trello_credentials)
        assert client is not None
        assert client.interactive is False

    def test_trello_client_interactive_mode(
        self, trello_credentials: dict[str, Any]
    ) -> None:
        client = TrelloClient(**trello_credentials, interactive=True)
        assert client.interactive is True

    def test_trello_client_api_key_from_init(
        self, trello_credentials: dict[str, Any]
    ) -> None:
        client = TrelloClient(**trello_credentials)
        assert client.api_key == "test_api_key"

    def test_trello_client_token_property(
        self, trello_credentials: dict[str, Any]
    ) -> None:
        client = TrelloClient(**trello_credentials)
        assert client.token == "test_token"

    def test_trello_client_token_raises_when_missing(self) -> None:
        with pytest.raises(ValueError, match="api_key is required"):
            TrelloClient(api_key="", token="token")

    def test_trello_client_query_method(
        self, trello_credentials: dict[str, Any]
    ) -> None:
        client = TrelloClient(**trello_credentials)
        query = client._query()
        assert query["key"] == "test_api_key"
        assert query["token"] == "test_token"

    def test_trello_client_get_issue(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_issue_response: dict[str, Any],
    ) -> None:
        list_resp = _mock_list_response()
        mock_response = MagicMock()
        mock_response.json.side_effect = [mock_issue_response, list_resp]
        mocker.patch(
            "trello_client_impl.client.requests.request", return_value=mock_response
        )

        issue = client_with_creds.get_issue("issue_id")
        assert issue is not None
        assert issue.id == mock_issue_response["id"]

    def test_trello_client_delete_issue(
        self, client_with_creds: TrelloClient, mocker: MockerFixture
    ) -> None:
        mock_request = mocker.patch(
            "trello_client_impl.client.requests.request", return_value=MagicMock()
        )
        result = client_with_creds.delete_issue("issue_id")
        assert result is True
        assert mock_request.call_count >= 2

    def test_trello_client_create_issue(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_issue_response: dict[str, Any],
    ) -> None:
        lists_data = [
            _mock_list_response("list_todo", "To Do"),
            _mock_list_response("list_ip", "In Progress"),
        ]
        list_name_resp = _mock_list_response("list_todo", "To Do")

        mock_response = MagicMock()
        mock_response.json.side_effect = [
            lists_data,
            mock_issue_response,
            list_name_resp,
        ]
        mocker.patch(
            "trello_client_impl.client.requests.request", return_value=mock_response
        )

        issue = client_with_creds.create_issue(
            "New Issue", "test_board_id", desc="desc"
        )
        assert issue is not None
        assert issue.id == mock_issue_response["id"]

    def test_trello_client_get_board(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_board_response: dict[str, str],
    ) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_board_response
        mocker.patch(
            "trello_client_impl.client.requests.request", return_value=mock_response
        )

        board = client_with_creds.get_board("board_id")
        assert board is not None
        assert board.board_name == mock_board_response["name"]

    def test_trello_client_create_board(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_board_response: dict[str, str],
    ) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_board_response
        mock_request = mocker.patch(
            "trello_client_impl.client.requests.request", return_value=mock_response
        )
        board = client_with_creds.create_board("New Board")
        assert board.id == mock_board_response["id"]
        assert board.board_name == mock_board_response["name"]
        assert mock_request.call_args[0][0] == "POST"

    def test_trello_client_update_board(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_board_response: dict[str, str],
    ) -> None:
        updated = {**mock_board_response, "name": "Renamed"}
        mock_response = MagicMock()
        mock_response.json.return_value = updated
        mocker.patch(
            "trello_client_impl.client.requests.request", return_value=mock_response
        )

        board = client_with_creds.update_board("board_id", name="Renamed")
        assert board.board_name == "Renamed"

    def test_trello_client_delete_board(
        self, client_with_creds: TrelloClient, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "trello_client_impl.client.requests.request", return_value=MagicMock()
        )
        result = client_with_creds.delete_board("board_id")
        assert result is True

    def test_trello_client_get_issues(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_issue_response: dict[str, Any],
    ) -> None:
        lists_data = [_mock_list_response("list_todo", "To Do")]
        cards_data = [mock_issue_response]

        mock_response = MagicMock()
        mock_response.json.side_effect = [lists_data, cards_data]
        mocker.patch(
            "trello_client_impl.client.requests.request", return_value=mock_response
        )

        issues = list(client_with_creds.get_issues("board_1"))
        assert len(issues) == 1
        assert issues[0].status == Status.TO_DO

    def test_trello_client_get_issues_skips_invalid_card_collections(
        self, client_with_creds: TrelloClient, mocker: MockerFixture
    ) -> None:
        lists_data = [_mock_list_response("list_todo", "To Do")]
        mock_response = MagicMock()
        mock_response.json.side_effect = [lists_data, {"not": "a list"}]
        mocker.patch(
            "trello_client_impl.client.requests.request", return_value=mock_response
        )

        issues = list(client_with_creds.get_issues("board_1"))
        assert issues == []

    def test_trello_client_update_issue_status(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_issue_response: dict[str, Any],
    ) -> None:
        card_data = {**mock_issue_response, "idBoard": "board_1"}
        lists_data = [
            _mock_list_response("list_todo", "To Do", "board_1"),
            _mock_list_response("list_done", "Done", "board_1"),
        ]
        updated_card = {**mock_issue_response, "idList": "list_done"}
        list_name_resp = {"id": "list_done", "name": "Done"}

        mock_response = MagicMock()
        mock_response.json.side_effect = [
            card_data,
            lists_data,
            updated_card,
            list_name_resp,
        ]
        mocker.patch(
            "trello_client_impl.client.requests.request", return_value=mock_response
        )

        issue = client_with_creds.update_issue("issue_id", status=Status.COMPLETED)
        assert issue is not None

    def test_trello_client_update_issue_with_explicit_board_id(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_issue_response: dict[str, Any],
    ) -> None:
        lists_data = [
            _mock_list_response("list_todo", "To Do", "board_1"),
            _mock_list_response("list_done", "Done", "board_1"),
        ]
        updated_card = {**mock_issue_response, "idList": "list_done"}
        list_name_resp = {"id": "list_done", "name": "Done"}

        mock_response = MagicMock()
        mock_response.json.side_effect = [lists_data, updated_card, list_name_resp]
        mock_request = mocker.patch(
            "trello_client_impl.client.requests.request", return_value=mock_response
        )

        issue = client_with_creds.update_issue(
            "issue_id", status=Status.COMPLETED, board_id="board_1"
        )
        assert issue is not None
        # Does not need the extra GET /cards/{issue_id} when board_id is provided.
        card_get_calls = [
            call
            for call in mock_request.call_args_list
            if call.args[0] == "GET"
            and call.args[1] == "https://api.trello.com/1/cards/issue_id"
        ]
        assert card_get_calls == []

    def test_trello_client_create_list_and_update_list(
        self, client_with_creds: TrelloClient, mocker: MockerFixture
    ) -> None:
        created = {"id": "list_1", "name": "To Do", "idBoard": "board_1"}
        updated = {"id": "list_1", "name": "Doing", "idBoard": "board_1"}
        mock_response = MagicMock()
        mock_response.json.side_effect = [created, updated]
        mocker.patch(
            "trello_client_impl.client.requests.request", return_value=mock_response
        )

        created_list = client_with_creds.create_list("board_1", "To Do")
        updated_list = client_with_creds.update_list("list_1", "Doing")

        assert created_list.id == "list_1"
        assert updated_list.name == "Doing"

    def test_trello_client_get_members_and_assign_issue(
        self,
        client_with_creds: TrelloClient,
        mocker: MockerFixture,
        mock_member_response: dict[str, Any],
    ) -> None:
        mock_response = MagicMock()
        mock_response.json.side_effect = [[mock_member_response], {"ok": True}]
        mocker.patch(
            "trello_client_impl.client.requests.request", return_value=mock_response
        )

        members = client_with_creds.get_members_on_issue("issue_1")
        assigned = client_with_creds.assign_issue("issue_1", "member_1")

        assert len(members) == 1
        assert members[0].id == "test_member_id"
        assert assigned is True

    def test_trello_client_get_members_non_list_returns_empty(
        self, client_with_creds: TrelloClient, mocker: MockerFixture
    ) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"unexpected": "shape"}
        mocker.patch(
            "trello_client_impl.client.requests.request", return_value=mock_response
        )

        assert client_with_creds.get_members_on_issue("issue_1") == []


@pytest.mark.unit
class TestTrelloClientOAuth:
    """Test OAuth flow methods."""

    def test_get_authorization_url_success(self, mocker: MockerFixture) -> None:
        mock_session_cls = mocker.patch("trello_client_impl.client.OAuth1Session")
        mock_session = mock_session_cls.return_value
        mock_session.fetch_request_token.return_value = {
            "oauth_token": "req_tok_123",
            "oauth_token_secret": "req_sec_456",
        }
        client = TrelloClient(api_key="key", secret="secret")
        url = client.get_authorization_url(callback_url="http://localhost/cb")
        assert "oauth_token=req_tok_123" in url
        assert client.request_token_secret == "req_sec_456"

    def test_get_authorization_url_no_secret_raises(self) -> None:
        client = TrelloClient(api_key="key", token="tok")
        with pytest.raises(ValueError, match="Secret is required for OAuth"):
            client.get_authorization_url()

    def test_get_authorization_url_empty_response_raises(
        self, mocker: MockerFixture
    ) -> None:
        mock_session_cls = mocker.patch("trello_client_impl.client.OAuth1Session")
        mock_session_cls.return_value.fetch_request_token.return_value = {}
        client = TrelloClient(api_key="key", secret="secret")
        with pytest.raises(ValueError, match="did not return request token"):
            client.get_authorization_url()

    def test_exchange_request_token_success(self, mocker: MockerFixture) -> None:
        mock_session_cls = mocker.patch("trello_client_impl.client.OAuth1Session")
        mock_session_cls.return_value.fetch_access_token.return_value = {
            "oauth_token": "access_tok",
            "oauth_token_secret": "access_sec",
        }
        mock_oauth1 = mocker.patch("trello_client_impl.client.OAuth1")
        client = TrelloClient(
            api_key="key", secret="secret", request_token_secret="req_sec"
        )
        client.exchange_request_token(oauth_token="req_tok", oauth_verifier="verifier")
        assert client.token == "access_tok"
        assert client.access_token_secret == "access_sec"
        mock_oauth1.assert_called_once_with("key", "secret", "access_tok", "access_sec")

    def test_exchange_request_token_no_secret_raises(self) -> None:
        client = TrelloClient(api_key="key", token="tok")
        with pytest.raises(ValueError, match="OAuth secret and request_token_secret"):
            client.exchange_request_token("tok", "verifier")

    def test_exchange_request_token_token_mismatch_raises(self) -> None:
        client = TrelloClient(api_key="key", secret="secret", request_token_secret="rs")
        client._request_token = "original_tok"
        with pytest.raises(ValueError, match="OAuth token mismatch"):
            client.exchange_request_token("different_tok", "verifier")

    def test_exchange_request_token_empty_response_raises(
        self, mocker: MockerFixture
    ) -> None:
        mock_session_cls = mocker.patch("trello_client_impl.client.OAuth1Session")
        mock_session_cls.return_value.fetch_access_token.return_value = {}
        client = TrelloClient(api_key="key", secret="secret", request_token_secret="rs")
        with pytest.raises(ValueError, match="did not return access token"):
            client.exchange_request_token("tok", "verifier")


@pytest.mark.unit
class TestTrelloClientInit:
    """Test constructor edge cases."""

    def test_both_token_and_access_token_raises(self) -> None:
        with pytest.raises(ValueError, match="Use access_token, not token"):
            TrelloClient(api_key="key", token="tok", access_token="at")

    def test_oauth1_auth_created_with_full_credentials(self) -> None:
        client = TrelloClient(
            api_key="key", secret="secret", access_token="at", access_token_secret="ats"
        )
        assert client._oauth is not None

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"access_token": "at"},
            {"access_token_secret": "ats"},
            {"secret": "secret", "access_token": "at"},
            {"secret": "secret", "access_token_secret": "ats"},
            {"access_token": "at", "access_token_secret": "ats"},
        ],
    )
    def test_partial_oauth_credentials_raise(self, kwargs: dict[str, str]) -> None:
        with pytest.raises(
            ValueError,
            match="Trello OAuth requires api_key, secret, access_token, and access_token_secret",
        ):
            TrelloClient(api_key="key", **kwargs)

    def test_secret_only_is_allowed_for_oauth_flow_init(self) -> None:
        client = TrelloClient(api_key="key", secret="secret")
        assert client is not None

    def test_query_with_oauth_skips_key_token(self) -> None:
        client = TrelloClient(
            api_key="key", secret="secret", access_token="at", access_token_secret="ats"
        )
        query = client._query(extra="val")
        assert "key" not in query
        assert query == {"extra": "val"}

    def test_query_without_token_returns_only_key(self) -> None:
        client = TrelloClient(api_key="key", secret="secret")
        query = client._query()
        assert query == {"key": "key"}

    def test_request_returns_none_on_empty_content(self, mocker: MockerFixture) -> None:
        client = TrelloClient(api_key="key", token="tok")
        mock_resp = MagicMock()
        mock_resp.content = b""
        mocker.patch(
            "trello_client_impl.client.requests.request", return_value=mock_resp
        )
        result = client._request("DELETE", "/cards/123")
        assert result is None


@pytest.mark.unit
class TestTrelloClientErrorPaths:
    """Test error paths on invalid responses."""

    @pytest.fixture
    def client(self) -> TrelloClient:
        return TrelloClient(api_key="key", token="tok")

    def test_get_issue_invalid_response_raises(
        self, client: TrelloClient, mocker: MockerFixture
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = "not_a_dict"
        mocker.patch(
            "trello_client_impl.client.requests.request", return_value=mock_resp
        )
        with pytest.raises(TypeError, match="Expected card response"):
            client.get_issue("bad_id")

    def test_get_board_invalid_response_raises(
        self, client: TrelloClient, mocker: MockerFixture
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = "not_a_dict"
        mocker.patch(
            "trello_client_impl.client.requests.request", return_value=mock_resp
        )
        with pytest.raises(TypeError, match="Expected board response"):
            client.get_board("bad_id")

    def test_create_board_invalid_response_raises(
        self, client: TrelloClient, mocker: MockerFixture
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = "not_a_dict"
        mocker.patch(
            "trello_client_impl.client.requests.request", return_value=mock_resp
        )
        with pytest.raises(TypeError, match="Expected board response"):
            client.create_board("Test")

    def test_get_boards_non_list_response(
        self, client: TrelloClient, mocker: MockerFixture
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = "not_a_list"
        mocker.patch(
            "trello_client_impl.client.requests.request", return_value=mock_resp
        )
        boards = list(client.get_boards())
        assert boards == []

    def test_get_boards_filters_invalid_entries(
        self,
        client: TrelloClient,
        mocker: MockerFixture,
        mock_board_response: dict[str, str],
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = [mock_board_response, "invalid"]
        mocker.patch(
            "trello_client_impl.client.requests.request", return_value=mock_resp
        )
        boards = list(client.get_boards())
        assert len(boards) == 1

    def test_get_lists_non_list_response(
        self, client: TrelloClient, mocker: MockerFixture
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = "not_a_list"
        mocker.patch(
            "trello_client_impl.client.requests.request", return_value=mock_resp
        )
        lists = list(client.get_lists("board_1"))
        assert lists == []

    def test_get_lists_filters_invalid_entries(
        self, client: TrelloClient, mocker: MockerFixture
    ) -> None:
        valid = {"id": "list_1", "name": "To Do", "idBoard": "board_1"}
        mock_resp = MagicMock()
        mock_resp.json.return_value = [valid, "invalid"]
        mocker.patch(
            "trello_client_impl.client.requests.request", return_value=mock_resp
        )
        lists = list(client.get_lists("board_1"))
        assert len(lists) == 1

    def test_get_issues_in_list_respects_max_issues(
        self,
        client: TrelloClient,
        mocker: MockerFixture,
        mock_issue_response: dict[str, Any],
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.json.side_effect = [
            [mock_issue_response, mock_issue_response],
            {"name": "To Do"},
        ]
        mocker.patch(
            "trello_client_impl.client.requests.request", return_value=mock_resp
        )
        issues = list(client.get_issues_in_list("list_1", max_issues=1))
        assert len(issues) == 1

    def test_get_issues_in_list_non_list_response(
        self, client: TrelloClient, mocker: MockerFixture
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = "not_a_list"
        mocker.patch(
            "trello_client_impl.client.requests.request", return_value=mock_resp
        )
        issues = list(client.get_issues_in_list("list_1"))
        assert issues == []


@pytest.mark.unit
class TestGetClientImplEdgeCases:
    """Test factory edge cases."""

    def test_get_client_impl_with_secret_only(self) -> None:
        client = get_client_impl(api_key="key", secret="secret")
        assert isinstance(client, TrelloClient)

    def test_get_client_impl_raises_without_api_key(self) -> None:
        with pytest.raises(ValueError, match="api_key"):
            get_client_impl(token="tok")


@pytest.mark.unit
class TestGetClientImpl:
    """Test the get_client_impl factory function."""

    def test_get_client_impl_returns_trello_client(
        self, trello_credentials: dict[str, Any]
    ) -> None:
        client = get_client_impl(**trello_credentials)
        assert isinstance(client, TrelloClient)

    def test_get_client_impl_with_interactive_flag(
        self, trello_credentials: dict[str, Any]
    ) -> None:
        client = get_client_impl(**trello_credentials, interactive=True)
        assert isinstance(client, TrelloClient)
        assert client.interactive is True

    def test_get_client_impl_raises_without_credentials(self) -> None:
        with pytest.raises(ValueError, match="Issue Tracker requires either 'token'"):
            get_client_impl(api_key="key")


@pytest.mark.unit
class TestRegister:
    """Test the register function."""

    def test_register_function_exists(self) -> None:
        assert callable(register)


@pytest.mark.unit
class TestHTTPErrorTranslation:
    """Test that Trello HTTP errors are translated to domain exceptions."""

    @pytest.fixture
    def client(self) -> TrelloClient:
        return TrelloClient(api_key="key", token="tok")

    def _make_http_error(self, status_code: int) -> requests_lib.exceptions.HTTPError:
        resp = MagicMock()
        resp.status_code = status_code
        return requests_lib.exceptions.HTTPError(response=resp)

    def test_401_raises_authentication_error(
        self, client: TrelloClient, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "trello_client_impl.client.requests.request",
            side_effect=self._make_http_error(401),
        )
        with pytest.raises(AuthenticationError, match="authentication failed"):
            client.get_board("b1")

    def test_404_raises_resource_not_found(
        self, client: TrelloClient, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "trello_client_impl.client.requests.request",
            side_effect=self._make_http_error(404),
        )
        with pytest.raises(ResourceNotFoundError):
            client.get_issue("bad_id")

    def test_500_raises_service_unavailable(
        self, client: TrelloClient, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "trello_client_impl.client.requests.request",
            side_effect=self._make_http_error(500),
        )
        with pytest.raises(ServiceUnavailableError, match="server error 500"):
            client.get_board("b1")

    def test_500_raises_service_unavailable_on_iterator(
        self, client: TrelloClient, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "trello_client_impl.client.requests.request",
            side_effect=self._make_http_error(500),
        )
        with pytest.raises(ServiceUnavailableError):
            list(client.get_boards())

    def test_other_http_error_raises_tracker_error(
        self, client: TrelloClient, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "trello_client_impl.client.requests.request",
            side_effect=self._make_http_error(429),
        )
        with pytest.raises(IssueTrackerError, match="status 429"):
            client.get_board("b1")

    def test_connection_error_raises_service_unavailable(
        self, client: TrelloClient, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "trello_client_impl.client.requests.request",
            side_effect=requests_lib.exceptions.ConnectionError("refused"),
        )
        with pytest.raises(ServiceUnavailableError, match="Could not connect"):
            client.get_board("b1")

    def test_timeout_raises_service_unavailable(
        self, client: TrelloClient, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "trello_client_impl.client.requests.request",
            side_effect=requests_lib.exceptions.Timeout("timed out"),
        )
        with pytest.raises(ServiceUnavailableError, match="timed out"):
            client.get_board("b1")
