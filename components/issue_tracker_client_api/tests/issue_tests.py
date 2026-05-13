"""Unit tests for the Issue abstract class and Status enum."""

from abc import ABC
from typing import Any

import pytest
from api.issue import Status
from issue_tracker_client_api.issue import Issue, get_issue


@pytest.mark.unit
class TestIssueAbstractClass:
    """Test that Issue is an abstract base class with required properties."""

    def test_issue_is_abstract(self) -> None:
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            _ = Issue()  # type: ignore[abstract]

    def test_issue_is_abc(self) -> None:
        assert issubclass(Issue, ABC)

    def test_issue_has_id_property(self) -> None:
        assert hasattr(Issue, "id")
        assert isinstance(Issue.id, property)

    def test_issue_has_title_property(self) -> None:
        assert hasattr(Issue, "title")
        assert isinstance(Issue.title, property)

    def test_issue_has_desc_property(self) -> None:
        assert hasattr(Issue, "desc")
        assert isinstance(Issue.desc, property)

    def test_issue_has_status_property(self) -> None:
        assert hasattr(Issue, "status")
        assert isinstance(Issue.status, property)

    def test_issue_has_board_id_property(self) -> None:
        assert hasattr(Issue, "board_id")
        assert isinstance(Issue.board_id, property)

    def test_concrete_issue_implementation(
        self, sample_issue_data: dict[str, Any]
    ) -> None:
        class ConcreteIssue(Issue):  # type: ignore[misc]
            def __init__(
                self, id: str, title: str, desc: str, status: Status, board_id: str
            ) -> None:
                self._id = id
                self._title = title
                self._desc = desc
                self._status = status
                self._board_id = board_id

            @property
            def id(self) -> str:
                return self._id

            @property
            def title(self) -> str:
                return self._title

            @property
            def desc(self) -> str:
                return self._desc

            @property
            def members(self) -> list[str] | None:
                return None

            @property
            def due_date(self) -> str | None:
                return None

            @property
            def status(self) -> Status:
                return self._status

            @property
            def board_id(self) -> str:
                return self._board_id

        issue = ConcreteIssue(
            id=sample_issue_data["id"],
            title=sample_issue_data["title"],
            desc=sample_issue_data["desc"],
            status=Status(sample_issue_data["status"]),
            board_id=sample_issue_data["board_id"],
        )
        assert issue.id == sample_issue_data["id"]
        assert issue.title == sample_issue_data["title"]
        assert issue.desc == sample_issue_data["desc"]
        assert issue.status == Status.TO_DO
        assert issue.board_id == sample_issue_data["board_id"]


@pytest.mark.unit
class TestStatusEnum:
    """Test the Status enum values."""

    def test_status_to_do(self) -> None:
        assert Status.TO_DO.value == "to_do"

    def test_status_in_progress(self) -> None:
        assert Status.IN_PROGRESS.value == "in_progress"

    def test_status_completed(self) -> None:
        assert Status.COMPLETED.value == "completed"


@pytest.mark.unit
class TestGetIssueFactory:
    """Test the get_issue factory function."""

    def test_get_issue_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError, match="Subclasses must implement"):
            get_issue("test_issue_id")

    def test_get_issue_marks_abstract_interface(self) -> None:
        assert callable(get_issue)
