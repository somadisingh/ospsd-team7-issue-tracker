"""Unit tests for the Issue abstract class."""

from abc import ABC
from typing import Any

import pytest
from issue_tracker_client_api.issue import Issue, get_issue


@pytest.mark.unit
class TestIssueAbstractClass:
    """Test that Issue is an abstract base class with required properties."""

    def test_issue_is_abstract(self) -> None:
        """Test that Issue cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            _ = Issue()  # type: ignore[abstract]

    def test_issue_is_abc(self) -> None:
        """Test that Issue is an ABC."""
        assert issubclass(Issue, ABC)

    def test_issue_has_id_property(self) -> None:
        """Test that Issue has an id property."""
        assert hasattr(Issue, "id")
        assert isinstance(Issue.id, property)

    def test_issue_has_title_property(self) -> None:
        """Test that Issue has a title property."""
        assert hasattr(Issue, "title")
        assert isinstance(Issue.title, property)

    def test_issue_has_is_complete_property(self) -> None:
        """Test that Issue has an is_complete property."""
        assert hasattr(Issue, "is_complete")
        assert isinstance(Issue.is_complete, property)

    def test_concrete_issue_implementation(
        self, sample_issue_data: dict[str, Any]
    ) -> None:
        """Test a concrete Issue implementation."""

        class ConcreteIssue(Issue):
            """Concrete implementation of Issue for testing."""

            def __init__(self, id: str, title: str, is_complete: bool) -> None:
                self._id = id
                self._title = title
                self._is_complete = is_complete

            @property
            def id(self) -> str:
                return self._id

            @property
            def title(self) -> str:
                return self._title

            @property
            def is_complete(self) -> bool:
                return self._is_complete

        issue = ConcreteIssue(
            id=sample_issue_data["id"],
            title=sample_issue_data["title"],
            is_complete=sample_issue_data["is_complete"],
        )
        assert issue.id == sample_issue_data["id"]
        assert issue.title == sample_issue_data["title"]
        assert issue.is_complete == sample_issue_data["is_complete"]


@pytest.mark.unit
class TestGetIssueFactory:
    """Test the get_issue factory function."""

    def test_get_issue_not_implemented(self) -> None:
        """Test that get_issue raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Subclasses must implement"):
            get_issue("test_issue_id")

    def test_get_issue_marks_abstract_interface(self) -> None:
        """Test that get_issue is part of the abstract interface."""
        assert callable(get_issue)
