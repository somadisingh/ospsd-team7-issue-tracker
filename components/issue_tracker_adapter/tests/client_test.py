"""Unit tests for ServiceClientAdapter and factory/register functions."""

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
from api.issue import Status
from issue_tracker_adapter.board import ServiceBoard
from issue_tracker_adapter.client import ServiceClientAdapter, get_client_impl, register
from issue_tracker_adapter.issue import ServiceIssue
from issue_tracker_client_api import Client
from issue_tracker_service_client import errors as api_errors
from issue_tracker_service_client.models.board_response import BoardResponse
from issue_tracker_service_client.models.http_validation_error import (
    HTTPValidationError,
)
from issue_tracker_service_client.models.issue_response import IssueResponse


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
        resp.board_name = "My Board"
        mock_api.sync.return_value = resp

        board = adapter.get_board("board_1")

        assert isinstance(board, ServiceBoard)
        assert board.id == "board_1"
        assert board.board_name == "My Board"
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
        resp1.board_name = "Board 1"
        resp2 = MagicMock(spec=BoardResponse)
        resp2.id = "b2"
        resp2.board_name = "Board 2"
        mock_api.sync.return_value = [resp1, resp2]

        boards = list(adapter.get_boards())

        assert len(boards) == 2
        assert all(isinstance(b, ServiceBoard) for b in boards)
        assert boards[0].id == "b1"
        assert boards[1].board_name == "Board 2"

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
        valid.board_name = "Valid"
        mock_api.sync.return_value = [valid, "not_a_board"]

        boards = list(adapter.get_boards())

        assert len(boards) == 1

    @patch("issue_tracker_adapter.client.create_board_api")
    def test_create_board(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        resp = MagicMock(spec=BoardResponse)
        resp.id = "new_board"
        resp.board_name = "Created Board"
        mock_api.sync.return_value = resp

        board = adapter.create_board("Created Board")

        assert isinstance(board, ServiceBoard)
        assert board.board_name == "Created Board"
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

    @patch("issue_tracker_adapter.client.update_board_api")
    def test_update_board(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        resp = MagicMock(spec=BoardResponse)
        resp.id = "b1"
        resp.board_name = "Renamed"
        mock_api.sync.return_value = resp

        board = adapter.update_board("b1", name="Renamed")

        assert isinstance(board, ServiceBoard)
        assert board.board_name == "Renamed"
        mock_api.sync.assert_called_once()

    @patch("issue_tracker_adapter.client.update_board_api")
    def test_update_board_invalid_response_raises(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        mock_api.sync.return_value = None

        with pytest.raises(TypeError, match="Expected BoardResponse"):
            adapter.update_board("b1", name="X")

    @patch("issue_tracker_adapter.client.delete_board_api")
    def test_delete_board_success(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        result = MagicMock()
        result.additional_properties = {"success": True}
        mock_api.sync.return_value = result

        assert adapter.delete_board("b1") is True
        mock_api.sync.assert_called_once()

    @patch("issue_tracker_adapter.client.delete_board_api")
    def test_delete_board_none_response(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        mock_api.sync.return_value = None

        assert adapter.delete_board("b1") is False

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
        resp.desc = "Bug desc"
        resp.members = ["alice"]
        resp.due_date = "2026-04-10"
        resp.status = "to_do"
        resp.board_id = "board_1"
        mock_api.sync.return_value = resp

        issue = adapter.get_issue("issue_1")

        assert isinstance(issue, ServiceIssue)
        assert issue.id == "issue_1"
        assert issue.title == "Fix bug"
        assert issue.status == Status.TO_DO

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
    def test_get_issues(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        resp = MagicMock(spec=IssueResponse)
        resp.id = "i1"
        resp.title = "Task"
        resp.desc = "D"
        resp.members = None
        resp.due_date = None
        resp.status = "in_progress"
        resp.board_id = "board_1"
        mock_api.sync.return_value = [resp]

        issues = list(adapter.get_issues("board_1"))

        assert len(issues) == 1
        assert isinstance(issues[0], ServiceIssue)
        assert issues[0].id == "i1"

    @patch("issue_tracker_adapter.client.get_issues_api")
    def test_get_issues_empty(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        mock_api.sync.return_value = []

        issues = list(adapter.get_issues("board_1"))

        assert issues == []

    @patch("issue_tracker_adapter.client.get_issues_api")
    def test_get_issues_non_list_response(
        self,
        mock_api: MagicMock,
        adapter: ServiceClientAdapter,
    ) -> None:
        mock_api.sync.return_value = None

        issues = list(adapter.get_issues("board_1"))

        assert issues == []

    @patch("issue_tracker_adapter.client.get_issues_api")
    def test_get_issues_filters_non_issue_responses(
        self,
        mock_api: MagicMock,
        adapter: ServiceClientAdapter,
    ) -> None:
        valid = MagicMock(spec=IssueResponse)
        valid.id = "i1"
        valid.title = "T"
        valid.desc = "D"
        valid.members = None
        valid.due_date = None
        valid.status = "to_do"
        valid.board_id = "b1"
        mock_api.sync.return_value = [valid, "not_an_issue"]

        issues = list(adapter.get_issues("board_1"))

        assert len(issues) == 1

    @patch("issue_tracker_adapter.client.create_issue_api")
    def test_create_issue(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        resp = MagicMock(spec=IssueResponse)
        resp.id = "new_issue"
        resp.title = "New Task"
        resp.desc = "Details"
        resp.members = None
        resp.due_date = None
        resp.status = "to_do"
        resp.board_id = "board_1"
        mock_api.sync.return_value = resp

        issue = adapter.create_issue("New Task", "board_1", desc="Details")

        assert isinstance(issue, ServiceIssue)
        assert issue.title == "New Task"
        mock_api.sync.assert_called_once()

    @patch("issue_tracker_adapter.client.create_issue_api")
    def test_create_issue_with_status(
        self,
        mock_api: MagicMock,
        adapter: ServiceClientAdapter,
    ) -> None:
        resp = MagicMock(spec=IssueResponse)
        resp.id = "i1"
        resp.title = "In Progress"
        resp.desc = ""
        resp.members = None
        resp.due_date = None
        resp.status = "in_progress"
        resp.board_id = "b1"
        mock_api.sync.return_value = resp

        issue = adapter.create_issue("In Progress", "b1", status=Status.IN_PROGRESS)

        assert issue.status == Status.IN_PROGRESS

    @patch("issue_tracker_adapter.client.create_issue_api")
    def test_create_issue_invalid_response_raises(
        self,
        mock_api: MagicMock,
        adapter: ServiceClientAdapter,
    ) -> None:
        mock_api.sync.return_value = None

        with pytest.raises(TypeError, match="Expected IssueResponse"):
            adapter.create_issue("Title", "b1")

    @patch("issue_tracker_adapter.client.update_issue_api")
    def test_update_issue(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        resp = MagicMock(spec=IssueResponse)
        resp.id = "i1"
        resp.title = "Updated"
        resp.desc = "New desc"
        resp.members = None
        resp.due_date = None
        resp.status = "completed"
        resp.board_id = "b1"
        mock_api.sync.return_value = resp

        issue = adapter.update_issue("i1", title="Updated", status=Status.COMPLETED)

        assert isinstance(issue, ServiceIssue)
        assert issue.title == "Updated"
        assert issue.status == Status.COMPLETED
        mock_api.sync.assert_called_once()

    @patch("issue_tracker_adapter.client.update_issue_api")
    def test_update_issue_invalid_response_raises(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        mock_api.sync.return_value = None

        with pytest.raises(TypeError, match="Expected IssueResponse"):
            adapter.update_issue("i1", title="X")

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
    # OAuth — not implemented
    # ------------------------------------------------------------------

    def test_get_authorization_url_raises(self, adapter: ServiceClientAdapter) -> None:
        with pytest.raises(NotImplementedError, match="OAuth"):
            adapter.get_authorization_url()

    def test_exchange_request_token_raises(self, adapter: ServiceClientAdapter) -> None:
        with pytest.raises(NotImplementedError, match="OAuth"):
            adapter.exchange_request_token("token", "verifier")


@pytest.mark.unit
class TestHTTPErrorHandling:
    """Test that HTTP/transport errors are caught and translated by _call_api."""

    @pytest.fixture
    def adapter(self, adapter_kwargs: dict[str, Any]) -> ServiceClientAdapter:
        return ServiceClientAdapter(**adapter_kwargs)

    # -- timeout ----------------------------------------------------------

    @patch("issue_tracker_adapter.client.get_board_api")
    def test_timeout_raises_timeout_error(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        mock_api.sync.side_effect = httpx.ReadTimeout("read timed out")

        with pytest.raises(TimeoutError, match="timed out"):
            adapter.get_board("board_1")

    @patch("issue_tracker_adapter.client.list_boards_api")
    def test_timeout_on_collection_raises_timeout_error(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        mock_api.sync.side_effect = httpx.ReadTimeout("read timed out")

        with pytest.raises(TimeoutError, match="timed out"):
            list(adapter.get_boards())

    # -- connection error -------------------------------------------------

    @patch("issue_tracker_adapter.client.get_board_api")
    def test_connect_error_raises_connection_error(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        mock_api.sync.side_effect = httpx.ConnectError("connection refused")

        with pytest.raises(ConnectionError, match="Could not connect"):
            adapter.get_board("board_1")

    @patch("issue_tracker_adapter.client.create_issue_api")
    def test_generic_http_error_raises_connection_error(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        mock_api.sync.side_effect = httpx.HTTPError("something broke")

        with pytest.raises(ConnectionError, match="HTTP transport error"):
            adapter.create_issue("Title", "b1")

    # -- unexpected status ------------------------------------------------

    @patch("issue_tracker_adapter.client.get_issue_api")
    def test_unexpected_status_raises_runtime_error(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        mock_api.sync.side_effect = api_errors.UnexpectedStatus(
            status_code=503, content=b"Service Unavailable"
        )

        with pytest.raises(RuntimeError, match="unexpected status 503"):
            adapter.get_issue("issue_1")

    @patch("issue_tracker_adapter.client.delete_board_api")
    def test_unexpected_status_on_bool_endpoint(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        mock_api.sync.side_effect = api_errors.UnexpectedStatus(
            status_code=500, content=b"Internal Server Error"
        )

        with pytest.raises(RuntimeError, match="unexpected status 500"):
            adapter.delete_board("b1")

    # -- validation error (422) -------------------------------------------

    @patch("issue_tracker_adapter.client.create_board_api")
    def test_validation_error_raises_value_error(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        validation_err = MagicMock(spec=HTTPValidationError)
        detail_item = MagicMock()
        detail_item.to_dict.return_value = {
            "loc": ["body", "name"],
            "msg": "field required",
        }
        validation_err.detail = [detail_item]
        mock_api.sync.return_value = validation_err

        with pytest.raises(ValueError, match="Validation error from service"):
            adapter.create_board("Test")

    @patch("issue_tracker_adapter.client.delete_board_api")
    def test_validation_error_on_bool_endpoint_raises_value_error(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        validation_err = MagicMock(spec=HTTPValidationError)
        validation_err.detail = None
        mock_api.sync.return_value = validation_err

        with pytest.raises(ValueError, match="Validation error from service"):
            adapter.delete_board("b1")

    @patch("issue_tracker_adapter.client.get_issues_api")
    def test_validation_error_on_collection_endpoint_raises_value_error(
        self, mock_api: MagicMock, adapter: ServiceClientAdapter
    ) -> None:
        validation_err = MagicMock(spec=HTTPValidationError)
        validation_err.detail = None
        mock_api.sync.return_value = validation_err

        with pytest.raises(ValueError, match="Validation error from service"):
            list(adapter.get_issues("board_1"))


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
