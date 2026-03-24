"""Unit tests for ServiceIssue."""

from unittest.mock import MagicMock

import pytest
from issue_tracker_adapter.issue import ServiceIssue
from issue_tracker_client_api.issue import Issue


@pytest.mark.unit
class TestServiceIssue:
    """Test the ServiceIssue adapter implementation."""

    def test_service_issue_initialization(self) -> None:
        issue = ServiceIssue(
            id="issue_1",
            title="Bug fix",
            is_complete=False,
            list_id="list_1",
            board_id="board_1",
        )
        assert issue.id == "issue_1"
        assert issue.title == "Bug fix"
        assert issue.is_complete is False
        assert issue.list_id == "list_1"
        assert issue.board_id == "board_1"

    def test_service_issue_is_instance_of_issue(self) -> None:
        issue = ServiceIssue(
            id="i1",
            title="T",
            is_complete=True,
            list_id="l1",
            board_id="b1",
        )
        assert isinstance(issue, Issue)

    def test_service_issue_complete_flag(self) -> None:
        issue = ServiceIssue(
            id="i1",
            title="Done",
            is_complete=True,
            list_id="l1",
            board_id="b1",
        )
        assert issue.is_complete is True

    def test_service_issue_none_board_id(self) -> None:
        issue = ServiceIssue(
            id="i1",
            title="T",
            is_complete=False,
            list_id="l1",
            board_id=None,
        )
        assert issue.board_id is None

    def test_service_issue_from_response(self, mock_issue_response: MagicMock) -> None:
        issue = ServiceIssue.from_response(mock_issue_response)
        assert issue.id == mock_issue_response.id
        assert issue.title == mock_issue_response.title
        assert issue.is_complete == mock_issue_response.is_complete
        assert issue.list_id == mock_issue_response.list_id
        assert issue.board_id == mock_issue_response.board_id
        assert isinstance(issue, ServiceIssue)
        assert isinstance(issue, Issue)
