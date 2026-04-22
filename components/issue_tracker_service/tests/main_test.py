"""Unit tests for FastAPI service endpoints in main.py."""

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

    def test_create_board_wrong_type(self, test_client: TestClient) -> None:
        response = test_client.post("/boards", json={"name": 123}, headers={"X-Session-Token": "tok"})
        assert response.status_code == 422

    def test_create_board_no_body(self, test_client: TestClient) -> None:
        response = test_client.post("/boards", headers={"X-Session-Token": "tok"})
        assert response.status_code == 422

    def test_create_issue_missing_title(self, test_client: TestClient) -> None:
        response = test_client.post(
            "/issues",
            json={"list_id": "list_1"},
            headers={"X-Session-Token": "tok"},
        )
        assert response.status_code == 422

    def test_create_issue_missing_list_id(self, test_client: TestClient) -> None:
        response = test_client.post(
            "/issues",
            json={"title": "Task"},
            headers={"X-Session-Token": "tok"},
        )
        assert response.status_code == 422

    def test_create_issue_empty_body(self, test_client: TestClient) -> None:
        response = test_client.post("/issues", json={}, headers={"X-Session-Token": "tok"})
        assert response.status_code == 422

    def test_create_list_missing_name(self, test_client: TestClient) -> None:
        response = test_client.post(
            "/lists",
            json={"board_id": "b1"},
            headers={"X-Session-Token": "tok"},
        )
        assert response.status_code == 422

    def test_create_list_missing_board_id(self, test_client: TestClient) -> None:
        response = test_client.post(
            "/lists",
            json={"name": "Col"},
            headers={"X-Session-Token": "tok"},
        )
        assert response.status_code == 422

    def test_update_list_missing_name(self, test_client: TestClient) -> None:
        response = test_client.put("/lists/list_1", json={}, headers={"X-Session-Token": "tok"})
        assert response.status_code == 422

    def test_update_status_missing_status(self, test_client: TestClient) -> None:
        response = test_client.put("/issues/i1/status", json={}, headers={"X-Session-Token": "tok"})
        assert response.status_code == 422

    def test_add_member_missing_member_id(self, test_client: TestClient) -> None:
        response = test_client.post("/boards/b1/members", json={}, headers={"X-Session-Token": "tok"})
        assert response.status_code == 422

    def test_assign_issue_missing_member_id(self, test_client: TestClient) -> None:
        response = test_client.post("/issues/i1/assign", headers={"X-Session-Token": "tok"})
        assert response.status_code == 422

    def test_assign_issue_missing_member_id_in_body(self, test_client: TestClient) -> None:
        response = test_client.post("/issues/i1/assign", json={}, headers={"X-Session-Token": "tok"})
        assert response.status_code == 422


@pytest.mark.unit
class TestQueryParamValidation:
    """Test query parameter boundary validation."""

    def test_max_issues_zero_returns_422(self, test_client: TestClient) -> None:
        response = test_client.get(
            "/lists/list_1/issues?max_issues=0",
            headers={"X-Session-Token": "tok"},
        )
        assert response.status_code == 422

    def test_max_issues_negative_returns_422(self, test_client: TestClient) -> None:
        response = test_client.get(
            "/lists/list_1/issues?max_issues=-5",
            headers={"X-Session-Token": "tok"},
        )
        assert response.status_code == 422

    def test_max_issues_exceeds_limit_returns_422(self, test_client: TestClient) -> None:
        response = test_client.get(
            "/lists/list_1/issues?max_issues=501",
            headers={"X-Session-Token": "tok"},
        )
        assert response.status_code == 422

    def test_max_issues_not_a_number_returns_422(self, test_client: TestClient) -> None:
        response = test_client.get(
            "/lists/list_1/issues?max_issues=abc",
            headers={"X-Session-Token": "tok"},
        )
        assert response.status_code == 422

    def test_max_issues_at_lower_bound(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
        mock_issue: MagicMock,
    ) -> None:
        mock_trello_client.get_issues_in_list.return_value = [mock_issue]
        response = test_client.get(
            "/lists/list_1/issues?max_issues=1",
            headers={"X-Session-Token": "tok"},
        )
        assert response.status_code == 200

    def test_max_issues_at_upper_bound(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
    ) -> None:
        mock_trello_client.get_issues_in_list.return_value = []
        response = test_client.get(
            "/lists/list_1/issues?max_issues=500",
            headers={"X-Session-Token": "tok"},
        )
        assert response.status_code == 200


@pytest.mark.unit
class TestClientExceptionHandling:
    """Test that downstream Trello client errors surface with proper HTTP codes."""

    @pytest.fixture
    def error_client(self, mock_trello_client: MagicMock) -> TestClient:
        app.dependency_overrides[get_authenticated_client] = lambda: mock_trello_client
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client
        app.dependency_overrides.clear()

    def test_get_board_trello_error(self, error_client: TestClient, mock_trello_client: MagicMock) -> None:
        mock_trello_client.get_board.side_effect = Exception("Trello unavailable")
        response = error_client.get("/boards/board_123", headers={"X-Session-Token": "tok"})
        assert response.status_code == 500

    def test_create_issue_trello_error(self, error_client: TestClient, mock_trello_client: MagicMock) -> None:
        mock_trello_client.create_issue.side_effect = Exception("rate limited")
        response = error_client.post(
            "/issues",
            json={"title": "Task", "list_id": "l1"},
            headers={"X-Session-Token": "tok"},
        )
        assert response.status_code == 500

    def test_delete_issue_trello_error(self, error_client: TestClient, mock_trello_client: MagicMock) -> None:
        mock_trello_client.delete_issue.side_effect = Exception("timeout")
        response = error_client.delete("/issues/i1", headers={"X-Session-Token": "tok"})
        assert response.status_code == 500

    def test_get_lists_trello_error(self, error_client: TestClient, mock_trello_client: MagicMock) -> None:
        mock_trello_client.get_lists.side_effect = Exception("connection reset")
        response = error_client.get("/boards/b1/lists", headers={"X-Session-Token": "tok"})
        assert response.status_code == 500


@pytest.mark.unit
class TestDomainExceptionHandlers:
    """Test that domain-specific exceptions map to correct HTTP status codes."""

    @pytest.fixture
    def error_client(self, mock_trello_client: MagicMock) -> TestClient:
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
        response = error_client.post(
            "/boards",
            json={"name": "Test"},
            headers={"X-Session-Token": "tok"},
        )
        assert response.status_code == 500
        assert "Upstream service error" in response.json()["detail"]

    def test_not_found_on_issue_returns_404(self, error_client: TestClient, mock_trello_client: MagicMock) -> None:
        mock_trello_client.get_issue.side_effect = ResourceNotFoundError("issue", "xyz")
        response = error_client.get("/issues/xyz", headers={"X-Session-Token": "tok"})
        assert response.status_code == 404

    def test_not_found_on_list_returns_404(self, error_client: TestClient, mock_trello_client: MagicMock) -> None:
        mock_trello_client.get_list.side_effect = ResourceNotFoundError("list", "l99")
        response = error_client.get("/lists/l99", headers={"X-Session-Token": "tok"})
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

    def test_list_boards(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
        mock_board: MagicMock,
    ) -> None:
        mock_trello_client.get_boards.return_value = [mock_board]

        response = test_client.get("/boards", headers={"X-Session-Token": "tok"})

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "board_123"
        assert data[0]["name"] == "Test Board"

    def test_list_boards_empty(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
    ) -> None:
        mock_trello_client.get_boards.return_value = []

        response = test_client.get("/boards", headers={"X-Session-Token": "tok"})

        assert response.status_code == 200
        assert response.json() == []

    def test_get_board(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
        mock_board: MagicMock,
    ) -> None:
        mock_trello_client.get_board.return_value = mock_board

        response = test_client.get("/boards/board_123", headers={"X-Session-Token": "tok"})

        assert response.status_code == 200
        assert response.json()["id"] == "board_123"

    def test_create_board(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
        mock_board: MagicMock,
    ) -> None:
        mock_trello_client.create_board.return_value = mock_board

        response = test_client.post(
            "/boards",
            json={"name": "New Board"},
            headers={"X-Session-Token": "tok"},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Test Board"
        mock_trello_client.create_board.assert_called_once_with(name="New Board")

    def test_add_member_to_board(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
    ) -> None:
        mock_trello_client.add_member_to_board.return_value = True

        response = test_client.post(
            "/boards/board_123/members",
            json={"member_id": "member_abc"},
            headers={"X-Session-Token": "tok"},
        )

        assert response.status_code == 200
        assert response.json() == {"success": True}
        mock_trello_client.add_member_to_board.assert_called_once_with(board_id="board_123", member_id="member_abc")

    def test_add_member_to_board_failure(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
    ) -> None:
        mock_trello_client.add_member_to_board.return_value = False

        response = test_client.post(
            "/boards/board_123/members",
            json={"member_id": "member_abc"},
            headers={"X-Session-Token": "tok"},
        )

        assert response.status_code == 200
        assert response.json() == {"success": False}

    def test_get_lists(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
        mock_list_obj: MagicMock,
    ) -> None:
        mock_trello_client.get_lists.return_value = [mock_list_obj]

        response = test_client.get(
            "/boards/board_123/lists",
            headers={"X-Session-Token": "tok"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "list_456"
        assert data[0]["name"] == "To Do"
        assert data[0]["board_id"] == "board_123"

    def test_get_lists_empty(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
    ) -> None:
        mock_trello_client.get_lists.return_value = []

        response = test_client.get(
            "/boards/board_123/lists",
            headers={"X-Session-Token": "tok"},
        )

        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.unit
class TestListEndpoints:
    """Test list-related endpoints."""

    def test_get_list(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
        mock_list_obj: MagicMock,
    ) -> None:
        mock_trello_client.get_list.return_value = mock_list_obj

        response = test_client.get("/lists/list_456", headers={"X-Session-Token": "tok"})

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "list_456"
        assert data["name"] == "To Do"
        assert data["board_id"] == "board_123"

    def test_create_list(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
        mock_list_obj: MagicMock,
    ) -> None:
        mock_trello_client.create_list.return_value = mock_list_obj

        response = test_client.post(
            "/lists",
            json={"board_id": "board_123", "name": "In Progress"},
            headers={"X-Session-Token": "tok"},
        )

        assert response.status_code == 200
        assert response.json()["id"] == "list_456"

    def test_update_list(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
        mock_list_obj: MagicMock,
    ) -> None:
        mock_trello_client.update_list.return_value = mock_list_obj

        response = test_client.put(
            "/lists/list_456",
            json={"name": "Renamed"},
            headers={"X-Session-Token": "tok"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "list_456"
        mock_trello_client.update_list.assert_called_once_with(list_id="list_456", name="Renamed")

    def test_delete_list(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
    ) -> None:
        mock_trello_client.delete_list.return_value = True

        response = test_client.delete(
            "/lists/list_456",
            headers={"X-Session-Token": "tok"},
        )

        assert response.status_code == 200
        assert response.json() == {"success": True}

    def test_delete_list_failure(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
    ) -> None:
        mock_trello_client.delete_list.return_value = False

        response = test_client.delete(
            "/lists/list_456",
            headers={"X-Session-Token": "tok"},
        )

        assert response.status_code == 200
        assert response.json() == {"success": False}

    def test_get_issues_in_list(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
        mock_issue: MagicMock,
    ) -> None:
        mock_trello_client.get_issues_in_list.return_value = [mock_issue]

        response = test_client.get(
            "/lists/list_456/issues",
            headers={"X-Session-Token": "tok"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "issue_789"

    def test_get_issues_in_list_with_max_issues(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
        mock_issue: MagicMock,
    ) -> None:
        mock_trello_client.get_issues_in_list.return_value = [mock_issue]

        response = test_client.get(
            "/lists/list_456/issues?max_issues=50",
            headers={"X-Session-Token": "tok"},
        )

        assert response.status_code == 200
        mock_trello_client.get_issues_in_list.assert_called_once_with(
            list_id="list_456",
            max_issues=50,
        )

    def test_get_issues_in_list_empty(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
    ) -> None:
        mock_trello_client.get_issues_in_list.return_value = []

        response = test_client.get(
            "/lists/list_456/issues",
            headers={"X-Session-Token": "tok"},
        )

        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.unit
class TestIssueEndpoints:
    """Test issue-related endpoints."""

    def test_get_issue(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
        mock_issue: MagicMock,
    ) -> None:
        mock_trello_client.get_issue.return_value = mock_issue

        response = test_client.get("/issues/issue_789", headers={"X-Session-Token": "tok"})

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "issue_789"
        assert data["title"] == "Fix bug"
        assert data["is_complete"] is False

    def test_create_issue(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
        mock_issue: MagicMock,
    ) -> None:
        mock_trello_client.create_issue.return_value = mock_issue

        response = test_client.post(
            "/issues",
            json={"title": "New Task", "list_id": "list_456", "description": "Details"},
            headers={"X-Session-Token": "tok"},
        )

        assert response.status_code == 200
        assert response.json()["id"] == "issue_789"

    def test_create_issue_without_description(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
        mock_issue: MagicMock,
    ) -> None:
        mock_trello_client.create_issue.return_value = mock_issue

        response = test_client.post(
            "/issues",
            json={"title": "Minimal", "list_id": "list_456"},
            headers={"X-Session-Token": "tok"},
        )

        assert response.status_code == 200

    def test_update_issue_status(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
    ) -> None:
        mock_trello_client.update_status.return_value = True

        response = test_client.put(
            "/issues/issue_789/status",
            json={"status": "complete"},
            headers={"X-Session-Token": "tok"},
        )

        assert response.status_code == 200
        assert response.json() == {"success": True}

    def test_update_issue_status_failure(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
    ) -> None:
        mock_trello_client.update_status.return_value = False

        response = test_client.put(
            "/issues/issue_789/status",
            json={"status": "invalid"},
            headers={"X-Session-Token": "tok"},
        )

        assert response.status_code == 200
        assert response.json() == {"success": False}

    def test_delete_issue(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
    ) -> None:
        mock_trello_client.delete_issue.return_value = True

        response = test_client.delete(
            "/issues/issue_789",
            headers={"X-Session-Token": "tok"},
        )

        assert response.status_code == 200
        assert response.json() == {"success": True}

    def test_delete_issue_failure(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
    ) -> None:
        mock_trello_client.delete_issue.return_value = False

        response = test_client.delete(
            "/issues/issue_789",
            headers={"X-Session-Token": "tok"},
        )

        assert response.status_code == 200
        assert response.json() == {"success": False}


@pytest.mark.unit
class TestMemberEndpoints:
    """Test member-related endpoints."""

    def test_get_issue_members(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
        mock_member: MagicMock,
    ) -> None:
        mock_trello_client.get_members_on_issue.return_value = [mock_member]

        response = test_client.get(
            "/issues/issue_789/members",
            headers={"X-Session-Token": "tok"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "member_abc"
        assert data[0]["username"] == "testuser"

    def test_get_issue_members_empty(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
    ) -> None:
        mock_trello_client.get_members_on_issue.return_value = []

        response = test_client.get(
            "/issues/issue_789/members",
            headers={"X-Session-Token": "tok"},
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_assign_issue(
        self,
        test_client: TestClient,
        mock_trello_client: MagicMock,
    ) -> None:
        mock_trello_client.assign_issue.return_value = True

        response = test_client.post(
            "/issues/issue_789/assign",
            json={"member_id": "member_abc"},
            headers={"X-Session-Token": "tok"},
        )

        assert response.status_code == 200
        assert response.json() == {"success": True}
