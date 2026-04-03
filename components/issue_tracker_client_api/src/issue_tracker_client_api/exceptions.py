"""Domain-specific exceptions for the issue tracker API.

These exception types form part of the public contract so that both
implementations (direct Trello, service adapter) and consumers can
handle errors without depending on transport-level details like HTTP
status codes or ``requests`` exceptions.
"""


class IssueTrackerError(Exception):
    """Base exception for all issue tracker domain errors."""


class ResourceNotFoundError(IssueTrackerError):
    """Raised when a requested resource (board, issue, list, member) does not exist."""

    def __init__(self, resource_type: str, resource_id: str) -> None:
        """Initialize with the resource type and identifier that was not found."""
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f"{resource_type} '{resource_id}' not found")


class AuthenticationError(IssueTrackerError):
    """Raised when authentication fails or credentials are invalid/expired."""


class ServiceUnavailableError(IssueTrackerError):
    """Raised when the upstream service is unreachable or returns a server-level error."""


class ValidationError(IssueTrackerError):
    """Raised when input data fails validation at the domain level."""
