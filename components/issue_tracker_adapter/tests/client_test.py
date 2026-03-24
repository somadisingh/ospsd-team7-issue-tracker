"""Unit tests for ServiceClientAdapter and factory/register functions."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from issue_tracker_adapter.board import ServiceBoard
from issue_tracker_adapter.client import ServiceClientAdapter, get_client_impl, register
from issue_tracker_adapter.issue import ServiceIssue
from issue_tracker_adapter.list import ServiceList
from issue_tracker_adapter.member import ServiceMember
from issue_tracker_client_api import Client
from issue_tracker_service_client.models.board_response import BoardResponse
from issue_tracker_service_client.models.issue_response import IssueResponse
from issue_tracker_service_client.models.list_response import ListResponse
from issue_tracker_service_client.models.member_response import MemberResponse


@pytest.mark.unit
class TestServiceClientAdapter:
    """Test the ServiceClientAdapter with mocked HTTP calls."""

    @pytest.fixture
    def adapter(self, adapter_kwargs: dict[str, Any]) -> ServiceClientAdapter:
        return ServiceClientAdapter(**adapter_kwargs)

    def test_adapter_initialization(self, adapter_kwargs: dict[str, Any]) -> None:
        adapter = ServiceClientAdapter(**adapter_kwargs)
        assert adapter is not None
        assert isinstance(adapter, Client)

    def test_adapter_is_instance_of_client(self, adapter: ServiceClientAdapter) -> None:
        assert isinstance(adapter, Client)

    # ------------------------------------------------------------------
    # Board operations
    # ------------------------------------------------------------------

    @patch("issue_tracker_adapter.client.get_board_api")
    def test_get_board(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        resp = MagicMock(spec=BoardResponse)
        resp.id = "board_1"
        resp.name = "My Board"
        mock_api.sync.return_value = resp

        board = adapter.get_board("board_1")

        assert isinstance(board, ServiceBoard)
        assert board.id == "board_1"
        assert board.name == "My Board"
        mock_api.sync.assert_called_once()

    @patch("issue_tracker_adapter.client.get_board_api")
    def test_get_board_invalid_response_raises(
        self,
        mock_api: MagicMock,
        adapter: ServiceClientAdapter,
    ) -> None:
        mock_api.sync.return_value = None

        with pytest.raises(TypeError, match="Expected BoardResponse"):
            adapter.get_board("board_1")

    @patch("issue_tracker_adapter.client.list_boards_api")
    def test_get_boards(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        resp1 = MagicMock(spec=BoardResponse)
        resp1.id = "b1"
        resp1.name = "Board 1"
        resp2 = MagicMock(spec=BoardResponse)
        resp2.id = "b2"
        resp2.name = "Board 2"
        mock_api.sync.return_value = [resp1, resp2]

        boards = list(adapter.get_boards())

        assert len(boards) == 2
        assert all(isinstance(b, ServiceBoard) for b in boards)
        assert boards[0].id == "b1"
        assert boards[1].name == "Board 2"

    @patch("issue_tracker_adapter.client.list_boards_api")
    def test_get_boards_empty_list(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        mock_api.sync.return_value = []

        boards = list(adapter.get_boards())

        assert boards == []

    @patch("issue_tracker_adapter.client.list_boards_api")
    def test_get_boards_non_list_response(
        self,
        mock_api: MagicMock,
        adapter: ServiceClientAdapter,
    ) -> None:
        mock_api.sync.return_value = None

        boards = list(adapter.get_boards())

        assert boards == []

    @patch("issue_tracker_adapter.client.list_boards_api")
    def test_get_boards_filters_non_board_responses(
        self,
        mock_api: MagicMock,
        adapter: ServiceClientAdapter,
    ) -> None:
        valid = MagicMock(spec=BoardResponse)
        valid.id = "b1"
        valid.name = "Valid"
        mock_api.sync.return_value = [valid, "not_a_board"]

        boards = list(adapter.get_boards())

        assert len(boards) == 1

    @patch("issue_tracker_adapter.client.create_board_api")
    def test_create_board(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        resp = MagicMock(spec=BoardResponse)
        resp.id = "new_board"
        resp.name = "Created Board"
        mock_api.sync.return_value = resp

        board = adapter.create_board("Created Board")

        assert isinstance(board, ServiceBoard)
        assert board.name == "Created Board"
        mock_api.sync.assert_called_once()

    @patch("issue_tracker_adapter.client.create_board_api")
    def test_create_board_invalid_response_raises(
        self,
        mock_api: MagicMock,
        adapter: ServiceClientAdapter,
    ) -> None:
        mock_api.sync.return_value = None

        with pytest.raises(TypeError, match="Expected BoardResponse"):
            adapter.create_board("Test")

    def test_add_member_to_board_raises(self, adapter: ServiceClientAdapter) -> None:
        with pytest.raises(NotImplementedError, match="not exposed"):
            adapter.add_member_to_board("b1", "m1")

    # ------------------------------------------------------------------
    # List operations
    # ------------------------------------------------------------------

    @patch("issue_tracker_adapter.client.get_list_api")
    def test_get_list(self, mock_api: MagicMock, adapter: ServiceClientAdapter) -> None:
        resp = MagicMock(spec=ListResponse)
        resp.id = "list_1"
        resp.name = "To Do"
        resp.board_id = "board_1"
        mock_api.sync.return_value = resp

        lst = adapter.get_list("list_1")

        assert isinstance(lst, ServiceList)
        assert lst.id == "list_1"
        assert lst.name == "To Do"

    @patch("issue_tracker_adapter.client.get_list_api")
    def test_get_list_invalid_response_raises(
        self,
        mock_api: MagicMock,
        adapter: ServiceClientAdapter,
    ) -> None:
        mock_api.sync.return_value = None

        with pytest.raises(TypeError, match="Expected ListResponse"):
            adapter.get_list("list_1")

    def test_get_lists_raises(self, adapter: ServiceClientAdapter) -> None:
        with pytest.raises(NotImplementedError, match="not exposed"):
            list(adapter.get_lists("board_1"))

    @patch("issue_tracker_adapter.client.create_list_api")
    def test_create_list(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        resp = MagicMock(spec=ListResponse)
        resp.id = "new_list"
        resp.name = "Done"
        resp.board_id = "board_1"
        mock_api.sync.return_value = resp

        lst = adapter.create_list("board_1", "Done")

        assert isinstance(lst, ServiceList)
        assert lst.name == "Done"
        mock_api.sync.assert_called_once()

    def test_update_list_raises(self, adapter: ServiceClientAdapter) -> None:
        with pytest.raises(NotImplementedError, match="not exposed"):
            adapter.update_list("list_1", "Renamed")

    def test_delete_list_raises(self, adapter: ServiceClientAdapter) -> None:
        with pytest.raises(NotImplementedError, match="not exposed"):
            adapter.delete_list("list_1")

    # ------------------------------------------------------------------
    # Issue operations
    # ------------------------------------------------------------------

    @patch("issue_tracker_adapter.client.get_issue_api")
    def test_get_issue(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        resp = MagicMock(spec=IssueResponse)
        resp.id = "issue_1"
        resp.title = "Fix bug"
        resp.is_complete = False
        resp.list_id = "list_1"
        resp.board_id = "board_1"
        mock_api.sync.return_value = resp

        issue = adapter.get_issue("issue_1")

        assert isinstance(issue, ServiceIssue)
        assert issue.id == "issue_1"
        assert issue.title == "Fix bug"

    @patch("issue_tracker_adapter.client.get_issue_api")
    def test_get_issue_invalid_response_raises(
        self,
        mock_api: MagicMock,
        adapter: ServiceClientAdapter,
    ) -> None:
        mock_api.sync.return_value = None

        with pytest.raises(TypeError, match="Expected IssueResponse"):
            adapter.get_issue("issue_1")

    @patch("issue_tracker_adapter.client.get_issues_api")
    def test_get_issues_in_list(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        resp = MagicMock(spec=IssueResponse)
        resp.id = "i1"
        resp.title = "Task"
        resp.is_complete = False
        resp.list_id = "list_1"
        resp.board_id = "board_1"
        mock_api.sync.return_value = [resp]

        issues = list(adapter.get_issues_in_list("list_1", max_issues=50))

        assert len(issues) == 1
        assert isinstance(issues[0], ServiceIssue)
        assert issues[0].id == "i1"

    @patch("issue_tracker_adapter.client.get_issues_api")
    def test_get_issues_in_list_empty(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        mock_api.sync.return_value = []

        issues = list(adapter.get_issues_in_list("list_1"))

        assert issues == []

    @patch("issue_tracker_adapter.client.get_issues_api")
    def test_get_issues_in_list_non_list_response(
        self,
        mock_api: MagicMock,
        adapter: ServiceClientAdapter,
    ) -> None:
        mock_api.sync.return_value = None

        issues = list(adapter.get_issues_in_list("list_1"))

        assert issues == []

    @patch("issue_tracker_adapter.client.get_issues_api")
    def test_get_issues_in_list_filters_non_issue_responses(
        self,
        mock_api: MagicMock,
        adapter: ServiceClientAdapter,
    ) -> None:
        valid = MagicMock(spec=IssueResponse)
        valid.id = "i1"
        valid.title = "T"
        valid.is_complete = False
        valid.list_id = "l1"
        valid.board_id = "b1"
        mock_api.sync.return_value = [valid, "not_an_issue"]

        issues = list(adapter.get_issues_in_list("list_1"))

        assert len(issues) == 1

    @patch("issue_tracker_adapter.client.create_issue_api")
    def test_create_issue(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        resp = MagicMock(spec=IssueResponse)
        resp.id = "new_issue"
        resp.title = "New Task"
        resp.is_complete = False
        resp.list_id = "list_1"
        resp.board_id = "board_1"
        mock_api.sync.return_value = resp

        issue = adapter.create_issue("New Task", "list_1", description="Details")

        assert isinstance(issue, ServiceIssue)
        assert issue.title == "New Task"
        mock_api.sync.assert_called_once()

    @patch("issue_tracker_adapter.client.create_issue_api")
    def test_create_issue_without_description(
        self,
        mock_api: MagicMock,
        adapter: ServiceClientAdapter,
    ) -> None:
        resp = MagicMock(spec=IssueResponse)
        resp.id = "i1"
        resp.title = "No Desc"
        resp.is_complete = False
        resp.list_id = "l1"
        resp.board_id = "b1"
        mock_api.sync.return_value = resp

        issue = adapter.create_issue("No Desc", "l1")

        assert issue.title == "No Desc"

    @patch("issue_tracker_adapter.client.update_status_api")
    def test_update_status_success(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        result = MagicMock()
        result.additional_properties = {"success": True}
        mock_api.sync.return_value = result

        assert adapter.update_status("issue_1", "complete") is True

    @patch("issue_tracker_adapter.client.update_status_api")
    def test_update_status_none_response(
        self,
        mock_api: MagicMock,
        adapter: ServiceClientAdapter,
    ) -> None:
        mock_api.sync.return_value = None

        assert adapter.update_status("issue_1", "complete") is False

    @patch("issue_tracker_adapter.client.delete_issue_api")
    def test_delete_issue_success(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        result = MagicMock()
        result.additional_properties = {"success": True}
        mock_api.sync.return_value = result

        assert adapter.delete_issue("issue_1") is True

    @patch("issue_tracker_adapter.client.delete_issue_api")
    def test_delete_issue_none_response(
        self,
        mock_api: MagicMock,
        adapter: ServiceClientAdapter,
    ) -> None:
        mock_api.sync.return_value = None

        assert adapter.delete_issue("issue_1") is False

    # ------------------------------------------------------------------
    # Member operations
    # ------------------------------------------------------------------

    @patch("issue_tracker_adapter.client.get_members_api")
    def test_get_members_on_issue(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        resp = MagicMock(spec=MemberResponse)
        resp.id = "m1"
        resp.username = "alice"
        mock_api.sync.return_value = [resp]

        members = adapter.get_members_on_issue("issue_1")

        assert len(members) == 1
        assert isinstance(members[0], ServiceMember)
        assert members[0].id == "m1"

    @patch("issue_tracker_adapter.client.get_members_api")
    def test_get_members_on_issue_non_list_response(
        self,
        mock_api: MagicMock,
        adapter: ServiceClientAdapter,
    ) -> None:
        mock_api.sync.return_value = None

        members = adapter.get_members_on_issue("issue_1")

        assert members == []

    @patch("issue_tracker_adapter.client.get_members_api")
    def test_get_members_on_issue_filters_non_member_responses(
        self,
        mock_api: MagicMock,
        adapter: ServiceClientAdapter,
    ) -> None:
        valid = MagicMock(spec=MemberResponse)
        valid.id = "m1"
        valid.username = "alice"
        mock_api.sync.return_value = [valid, "not_a_member"]

        members = adapter.get_members_on_issue("issue_1")

        assert len(members) == 1

    @patch("issue_tracker_adapter.client.assign_api")
    def test_assign_issue_success(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        result = MagicMock()
        result.additional_properties = {"success": True}
        mock_api.sync.return_value = result

        assert adapter.assign_issue("issue_1", "member_1") is True

    @patch("issue_tracker_adapter.client.assign_api")
    def test_assign_issue_none_response(
        self,
        mock_api: MagicMock,
        adapter: ServiceClientAdapter,
    ) -> None:
        mock_api.sync.return_value = None

        assert adapter.assign_issue("issue_1", "member_1") is False

    # ------------------------------------------------------------------
    # OAuth — not implemented
    # ------------------------------------------------------------------

    def test_get_authorization_url_raises(self, adapter: ServiceClientAdapter) -> None:
        with pytest.raises(NotImplementedError, match="OAuth"):
            adapter.get_authorization_url()

    def test_exchange_request_token_raises(self, adapter: ServiceClientAdapter) -> None:
        with pytest.raises(NotImplementedError, match="OAuth"):
            adapter.exchange_request_token("token", "verifier")


@pytest.mark.unit
class TestGetClientImpl:
    """Test the get_client_impl factory function."""

    def test_returns_adapter_instance(self) -> None:
        client = get_client_impl(
            base_url="https://example.com",
            session_token="tok_123",
        )
        assert isinstance(client, ServiceClientAdapter)
        assert isinstance(client, Client)

    def test_raises_without_base_url(self) -> None:
        with pytest.raises(ValueError, match="base_url"):
            get_client_impl(session_token="tok_123")

    def test_raises_without_session_token(self) -> None:
        with pytest.raises(ValueError, match="session_token"):
            get_client_impl(base_url="https://example.com")

    def test_raises_with_empty_base_url(self) -> None:
        with pytest.raises(ValueError, match="base_url"):
            get_client_impl(base_url="", session_token="tok_123")

    def test_raises_with_empty_session_token(self) -> None:
        with pytest.raises(ValueError, match="session_token"):
            get_client_impl(base_url="https://example.com", session_token="")

    def test_raises_with_no_args(self) -> None:
        with pytest.raises(ValueError, match="base_url"):
            get_client_impl()


@pytest.mark.unit
class TestRegister:
    """Test the register function."""

    def test_register_is_callable(self) -> None:
        assert callable(register)

    def test_register_replaces_get_client(self) -> None:
        import issue_tracker_client_api

        original = issue_tracker_client_api.get_client
        try:
            register()
            assert issue_tracker_client_api.get_client is not original
            assert issue_tracker_client_api.get_client is get_client_impl
        finally:
            issue_tracker_client_api.get_client = original
