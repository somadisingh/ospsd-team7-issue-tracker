"""Conftest for end-to-end tests.

Note: E2E tests should be configured to run against actual Trello API or a test instance.
For development, these may be skipped if credentials are not available.
"""

import os

import pytest
from issue_tracker_adapter.client import ServiceClientAdapter


@pytest.fixture
def e2e_credentials() -> dict[str, str]:
    """Provide e2e test credentials from environment.

    Returns only the credentials needed for TrelloClient construction
    (api_key, token). board_id is available via e2e_board_id fixture.
    """
    return {
        "api_key": os.getenv("TRELLO_API_KEY", ""),
        "token": os.getenv("TRELLO_TOKEN", ""),
    }


@pytest.fixture
def e2e_board_id() -> str:
    """Provide a test board ID from environment."""
    return os.getenv("TRELLO_BOARD_ID", "")


@pytest.fixture
def e2e_skip_if_no_credentials(
    e2e_credentials: dict[str, str], e2e_board_id: str
) -> None:
    """Skip e2e tests if Trello credentials are not available."""
    api_key = e2e_credentials.get("api_key")
    token = e2e_credentials.get("token")

    if not all([api_key, token, e2e_board_id]):
        pytest.skip(
            "Skipping e2e tests: TRELLO_API_KEY, TRELLO_TOKEN, and TRELLO_BOARD_ID required"
        )


@pytest.fixture
def e2e_client_config(e2e_credentials: dict[str, str]) -> dict[str, str]:
    """Provide e2e test client configuration from credentials."""
    return e2e_credentials


@pytest.fixture
def e2e_service_url() -> str:
    """Provide the deployed service URL from environment."""
    return os.getenv(
        "SERVICE_BASE_URL",
        "https://issue-tracker-service-688420327904.us-central1.run.app",
    )


@pytest.fixture
def e2e_session_token() -> str:
    """Provide an OAuth session token for the deployed service."""
    return os.getenv("SERVICE_SESSION_TOKEN", "")


@pytest.fixture
def e2e_skip_if_no_service_credentials(
    e2e_service_url: str, e2e_session_token: str
) -> None:
    """Skip adapter E2E tests if service credentials are not available."""
    if not e2e_session_token:
        pytest.skip(
            "Skipping adapter e2e tests: SERVICE_SESSION_TOKEN required "
            "(obtain via /auth/login + /auth/callback on the deployed service)"
        )


@pytest.fixture
def e2e_adapter(e2e_service_url: str, e2e_session_token: str) -> ServiceClientAdapter:
    """Provide a ServiceClientAdapter pointed at the deployed service."""
    return ServiceClientAdapter(
        base_url=e2e_service_url, session_token=e2e_session_token
    )
