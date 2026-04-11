"""Issue contract - re-exports the shared vertical Issue ABC and Status enum."""

from api.issue import Issue, Status

__all__ = ["Issue", "Status"]


def get_issue(issue_id: str) -> Issue:
    """Return an issue by its ID."""
    raise NotImplementedError("Subclasses must implement get_issue")
