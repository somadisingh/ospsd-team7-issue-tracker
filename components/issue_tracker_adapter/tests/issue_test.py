"""Unit tests for ServiceIssue."""

from unittest.mock import MagicMock

import pytest
from api.issue import Status
from issue_tracker_adapter.issue import ServiceIssue
from issue_tracker_client_api.issue import Issue


@pytest.mark.unit
class TestServiceIssue:
    """Test the ServiceIssue adapter implementation."""

    def test_service_issue_initialization(self) -> None:
        issue = ServiceIssue(
            id="issue_1",
            title="Bug fix",
            desc="Description",
            members=None,
            due_date=None,
            status=Status.TO_DO,
            board_id="board_1",
        )
        assert issue.id == "issue_1"
        assert issue.title == "Bug fix"
        assert issue.desc == "Description"
        assert issue.members is None
        assert issue.due_date is None
        assert issue.status == Status.TO_DO
        assert issue.board_id == "board_1"

    def test_service_issue_is_instance_of_issue(self) -> None:
        issue = ServiceIssue(
            id="i1",
            title="T",
            desc="D",
            members=None,
            due_date=None,
            status=Status.COMPLETED,
            board_id="b1",
        )
        assert isinstance(issue, Issue)

    def test_service_issue_with_members(self) -> None:
        issue = ServiceIssue(
            id="i1",
            title="Done",
            desc="",
            members=["alice", "bob"],
            due_date="2026-04-10",
            status=Status.IN_PROGRESS,
            board_id="b1",
        )
        assert issue.members == ["alice", "bob"]
        assert issue.due_date == "2026-04-10"
        assert issue.status == Status.IN_PROGRESS

    def test_service_issue_from_response(self, mock_issue_response: MagicMock) -> None:
        issue = ServiceIssue.from_response(mock_issue_response)
        assert issue.id == mock_issue_response.id
        assert issue.title == mock_issue_response.title
        assert issue.desc == mock_issue_response.desc
        assert issue.members is None
        assert issue.due_date is None
        assert issue.status == Status.TO_DO
        assert issue.board_id == mock_issue_response.board_id
        assert isinstance(issue, ServiceIssue)
        assert isinstance(issue, Issue)

    def test_service_issue_from_response_with_members(self) -> None:
        resp = MagicMock()
        resp.id = "i2"
        resp.title = "T2"
        resp.desc = "D2"
        resp.members = ["user1"]
        resp.due_date = "2026-05-01"
        resp.status = "in_progress"
        resp.board_id = "b1"

        issue = ServiceIssue.from_response(resp)
        assert issue.members == ["user1"]
        assert issue.due_date == "2026-05-01"
        assert issue.status == Status.IN_PROGRESS
