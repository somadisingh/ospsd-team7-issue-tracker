"""Unit tests for FastAPI service endpoints in main.py."""

from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from issue_tracker_client_api.exceptions import (
    AuthenticationError,
    IssueTrackerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from issue_tracker_service.main import app, get_authenticated_client


@pytest.mark.unit
class TestAuthValidation:
    """Test authentication and session token validation."""

    def test_missing_session_token_returns_422(self, raw_client: TestClient) -> None:
        response = raw_client.get("/boards")
        assert response.status_code == 422

    def test_invalid_session_token_returns_401(self, raw_client: TestClient) -> None:
        response = raw_client.get("/boards", headers={"X-Session-Token": "nonexistent"})
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]


@pytest.mark.unit
class TestRequestBodyValidation:
    """Test that invalid request bodies are rejected with 422."""

    def test_create_board_missing_name(self, test_client: TestClient) -> None:
        response = test_client.post("/boards", json={}, headers={"X-Session-Token": "tok"})
        assert response.status_code == 422

    def test_create_board_no_body(self, test_client: TestClient) -> None:
        response = test_client.post("/boards", headers={"X-Session-Token": "tok"})
        assert response.status_code == 422

    def test_create_issue_missing_title(self, test_client: TestClient) -> None:
        response = test_client.post("/issues", json={"board_id": "b1"}, headers={"X-Session-Token": "tok"})
        assert response.status_code == 422

    def test_create_issue_missing_board_id(self, test_client: TestClient) -> None:
        response = test_client.post("/issues", json={"title": "Task"}, headers={"X-Session-Token": "tok"})
        assert response.status_code == 422

    def test_create_issue_empty_body(self, test_client: TestClient) -> None:
        response = test_client.post("/issues", json={}, headers={"X-Session-Token": "tok"})
        assert response.status_code == 422


@pytest.mark.unit
class TestClientExceptionHandling:
    """Test that downstream errors surface with proper HTTP codes."""

    @pytest.fixture
    def error_client(self, mock_trello_client: MagicMock) -> Generator[TestClient]:
        app.dependency_overrides[get_authenticated_client] = lambda: mock_trello_client
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client
        app.dependency_overrides.clear()

    def test_get_board_trello_error(self, error_client: TestClient, mock_trello_client: MagicMock) -> None:
        mock_trello_client.get_board.side_effect = Exception("Trello unavailable")
        response = error_client.get("/boards/board_123", headers={"X-Session-Token": "tok"})
        assert response.status_code == 500

    def test_delete_issue_trello_error(self, error_client: TestClient, mock_trello_client: MagicMock) -> None:
        mock_trello_client.delete_issue.side_effect = Exception("timeout")
        response = error_client.delete("/issues/i1", headers={"X-Session-Token": "tok"})
        assert response.status_code == 500


@pytest.mark.unit
class TestDomainExceptionHandlers:
    """Test that domain-specific exceptions map to correct HTTP status codes."""

    @pytest.fixture
    def error_client(self, mock_trello_client: MagicMock) -> Generator[TestClient]:
        app.dependency_overrides[get_authenticated_client] = lambda: mock_trello_client
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client
        app.dependency_overrides.clear()

    def test_resource_not_found_returns_404(self, error_client: TestClient, mock_trello_client: MagicMock) -> None:
        mock_trello_client.get_board.side_effect = ResourceNotFoundError("board", "bad_id")
        response = error_client.get("/boards/bad_id", headers={"X-Session-Token": "tok"})
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_authentication_error_returns_401(self, error_client: TestClient, mock_trello_client: MagicMock) -> None:
        mock_trello_client.get_boards.side_effect = AuthenticationError("bad creds")
        response = error_client.get("/boards", headers={"X-Session-Token": "tok"})
        assert response.status_code == 401

    def test_service_unavailable_returns_502(self, error_client: TestClient, mock_trello_client: MagicMock) -> None:
        mock_trello_client.get_issue.side_effect = ServiceUnavailableError("Trello down")
        response = error_client.get("/issues/i1", headers={"X-Session-Token": "tok"})
        assert response.status_code == 502

    def test_generic_tracker_error_returns_500(self, error_client: TestClient, mock_trello_client: MagicMock) -> None:
        mock_trello_client.create_board.side_effect = IssueTrackerError("something broke")
        response = error_client.post("/boards", json={"name": "Test"}, headers={"X-Session-Token": "tok"})
        assert response.status_code == 500
        assert "Upstream service error" in response.json()["detail"]

    def test_not_found_on_issue_returns_404(self, error_client: TestClient, mock_trello_client: MagicMock) -> None:
        mock_trello_client.get_issue.side_effect = ResourceNotFoundError("issue", "xyz")
        response = error_client.get("/issues/xyz", headers={"X-Session-Token": "tok"})
        assert response.status_code == 404

    def test_service_unavailable_on_delete_returns_502(
        self, error_client: TestClient, mock_trello_client: MagicMock
    ) -> None:
        mock_trello_client.delete_issue.side_effect = ServiceUnavailableError("timeout")
        response = error_client.delete("/issues/i1", headers={"X-Session-Token": "tok"})
        assert response.status_code == 502


@pytest.mark.unit
class TestHealthEndpoints:
    """Test health and root endpoints."""

    def test_root_redirects_to_docs(self, test_client: TestClient) -> None:
        response = test_client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/docs" in response.headers.get("location", "")

    def test_health_check(self, test_client: TestClient) -> None:
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        # With DATABASE_URL set (conftest uses SQLite), the response includes DB status
        assert data.get("database") == "connected"


@pytest.mark.unit
class TestBoardEndpoints:
    """Test board-related endpoints."""

    def test_list_boards(self, test_client: TestClient, mock_trello_client: MagicMock, mock_board: MagicMock) -> None:
        mock_trello_client.get_boards.return_value = [mock_board]
        response = test_client.get("/boards", headers={"X-Session-Token": "tok"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "board_123"
        assert data[0]["board_name"] == "Test Board"

    def test_list_boards_empty(self, test_client: TestClient, mock_trello_client: MagicMock) -> None:
        mock_trello_client.get_boards.return_value = []
        response = test_client.get("/boards", headers={"X-Session-Token": "tok"})
        assert response.status_code == 200
        assert response.json() == []

    def test_get_board(self, test_client: TestClient, mock_trello_client: MagicMock, mock_board: MagicMock) -> None:
        mock_trello_client.get_board.return_value = mock_board
        response = test_client.get("/boards/board_123", headers={"X-Session-Token": "tok"})
        assert response.status_code == 200
        assert response.json()["id"] == "board_123"

    def test_create_board(self, test_client: TestClient, mock_trello_client: MagicMock, mock_board: MagicMock) -> None:
        mock_trello_client.create_board.return_value = mock_board
        response = test_client.post("/boards", json={"name": "New Board"}, headers={"X-Session-Token": "tok"})
        assert response.status_code == 200
        assert response.json()["board_name"] == "Test Board"

    def test_update_board(self, test_client: TestClient, mock_trello_client: MagicMock, mock_board: MagicMock) -> None:
        mock_trello_client.update_board.return_value = mock_board
        response = test_client.put("/boards/board_123", json={"name": "Renamed"}, headers={"X-Session-Token": "tok"})
        assert response.status_code == 200
        assert response.json()["board_name"] == "Test Board"

    def test_delete_board(self, test_client: TestClient, mock_trello_client: MagicMock) -> None:
        mock_trello_client.delete_board.return_value = True
        response = test_client.delete("/boards/board_123", headers={"X-Session-Token": "tok"})
        assert response.status_code == 200
        assert response.json() == {"success": True}


@pytest.mark.unit
class TestIssueEndpoints:
    """Test issue-related endpoints."""

    def test_get_issue(self, test_client: TestClient, mock_trello_client: MagicMock, mock_issue: MagicMock) -> None:
        mock_trello_client.get_issue.return_value = mock_issue
        response = test_client.get("/issues/issue_789", headers={"X-Session-Token": "tok"})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "issue_789"
        assert data["title"] == "Fix bug"
        assert data["desc"] == "A bug description"
        assert data["members"] is None
        assert data["due_date"] is None
        assert data["status"] == "to_do"
        assert data["board_id"] == "board_123"

    def test_get_issues(self, test_client: TestClient, mock_trello_client: MagicMock, mock_issue: MagicMock) -> None:
        mock_trello_client.get_issues.return_value = [mock_issue]
        response = test_client.get("/boards/board_123/issues", headers={"X-Session-Token": "tok"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "issue_789"
        assert data[0]["title"] == "Fix bug"
        assert data[0]["board_id"] == "board_123"

    def test_get_issues_empty(self, test_client: TestClient, mock_trello_client: MagicMock) -> None:
        mock_trello_client.get_issues.return_value = []
        response = test_client.get("/boards/board_123/issues", headers={"X-Session-Token": "tok"})
        assert response.status_code == 200
        assert response.json() == []

    def test_create_issue(self, test_client: TestClient, mock_trello_client: MagicMock, mock_issue: MagicMock) -> None:
        mock_trello_client.create_issue.return_value = mock_issue
        response = test_client.post(
            "/issues",
            json={"title": "New Task", "board_id": "board_123", "desc": "Details"},
            headers={"X-Session-Token": "tok"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "issue_789"
        assert data["status"] == "to_do"
        assert data["board_id"] == "board_123"

    def test_create_issue_with_all_fields(
        self, test_client: TestClient, mock_trello_client: MagicMock, mock_issue: MagicMock
    ) -> None:
        mock_trello_client.create_issue.return_value = mock_issue
        response = test_client.post(
            "/issues",
            json={
                "title": "Full Task",
                "board_id": "board_123",
                "desc": "Full description",
                "members": ["alice", "bob"],
                "due_date": "2026-05-01",
                "status": "in_progress",
            },
            headers={"X-Session-Token": "tok"},
        )
        assert response.status_code == 200
        mock_trello_client.create_issue.assert_called_once()

    def test_update_issue(self, test_client: TestClient, mock_trello_client: MagicMock, mock_issue: MagicMock) -> None:
        mock_trello_client.update_issue.return_value = mock_issue
        response = test_client.put(
            "/issues/issue_789",
            json={"status": "in_progress"},
            headers={"X-Session-Token": "tok"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "issue_789"

    def test_update_issue_multiple_fields(
        self, test_client: TestClient, mock_trello_client: MagicMock, mock_issue: MagicMock
    ) -> None:
        mock_trello_client.update_issue.return_value = mock_issue
        response = test_client.put(
            "/issues/issue_789",
            json={"title": "Updated", "desc": "New desc", "board_id": "board_999"},
            headers={"X-Session-Token": "tok"},
        )
        assert response.status_code == 200
        mock_trello_client.update_issue.assert_called_once()

    def test_delete_issue(self, test_client: TestClient, mock_trello_client: MagicMock) -> None:
        mock_trello_client.delete_issue.return_value = True
        response = test_client.delete("/issues/issue_789", headers={"X-Session-Token": "tok"})
        assert response.status_code == 200
        assert response.json() == {"success": True}
