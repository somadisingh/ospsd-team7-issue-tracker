"""Unit tests for OAuth authentication routes."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from issue_tracker_service.main import app


@pytest.mark.unit
class TestTrelloConfig:
    """Test the _trello_config helper."""

    @patch.dict("os.environ", {"TRELLO_API_KEY": "key123", "TRELLO_API_SECRET": "secret456"})
    def test_trello_config_loads_credentials(self) -> None:
        from issue_tracker_service.routes.auth import _trello_config

        config = _trello_config()
        assert config["api_key"] == "key123"
        assert config["secret"] == "secret456"
        assert "callback_url" in config

    @patch.dict(
        "os.environ",
        {
            "TRELLO_API_KEY": "key123",
            "TRELLO_API_SECRET": "secret456",
            "TRELLO_CALLBACK_URL": "https://custom/callback",
        },
    )
    def test_trello_config_custom_callback(self) -> None:
        from issue_tracker_service.routes.auth import _trello_config

        config = _trello_config()
        assert config["callback_url"] == "https://custom/callback"

    @patch.dict("os.environ", {}, clear=True)
    def test_trello_config_raises_without_credentials(self) -> None:
        from issue_tracker_service.routes.auth import _trello_config

        with pytest.raises(RuntimeError, match="Missing Trello OAuth credentials"):
            _trello_config()

    @patch.dict("os.environ", {"TRELLO_API_KEY": "key123"}, clear=True)
    def test_trello_config_raises_without_secret(self) -> None:
        from issue_tracker_service.routes.auth import _trello_config

        with pytest.raises(RuntimeError, match="Missing Trello OAuth credentials"):
            _trello_config()


@pytest.mark.unit
class TestAuthCallback:
    """Test the /auth/callback endpoint."""

    @patch("issue_tracker_service.routes.auth._trello_config")
    @patch("issue_tracker_service.routes.auth.TrelloClient")
    def test_callback_unknown_token_returns_400(
        self,
        mock_client_cls: MagicMock,
        mock_config: MagicMock,
    ) -> None:
        mock_config.return_value = {
            "api_key": "k",
            "secret": "s",
            "callback_url": "http://localhost/cb",
        }

        client = TestClient(app)
        response = client.get(
            "/auth/callback?oauth_token=unknown_token&oauth_verifier=verifier",
        )

        assert response.status_code == 400
        assert "Unknown or expired" in response.json()["detail"]

    @patch("issue_tracker_service.routes.auth._trello_config")
    @patch("issue_tracker_service.routes.auth.TrelloClient")
    def test_callback_success(
        self,
        mock_client_cls: MagicMock,
        mock_config: MagicMock,
    ) -> None:
        from issue_tracker_service.routes.auth import oauth1_request_secrets

        mock_config.return_value = {
            "api_key": "k",
            "secret": "s",
            "callback_url": "http://localhost/cb",
        }
        oauth1_request_secrets["valid_token"] = "request_secret"

        mock_instance = MagicMock()
        mock_instance.token = "access_tok"
        mock_instance.access_token_secret = "access_secret"
        mock_client_cls.return_value = mock_instance

        client = TestClient(app)
        response = client.get(
            "/auth/callback?oauth_token=valid_token&oauth_verifier=verifier_123",
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_token" in data
        assert len(data["session_token"]) > 0

    @patch("issue_tracker_service.routes.auth._trello_config")
    @patch("issue_tracker_service.routes.auth.TrelloClient")
    def test_callback_fails_when_no_access_token(
        self,
        mock_client_cls: MagicMock,
        mock_config: MagicMock,
    ) -> None:
        from issue_tracker_service.routes.auth import oauth1_request_secrets

        mock_config.return_value = {
            "api_key": "k",
            "secret": "s",
            "callback_url": "http://localhost/cb",
        }
        oauth1_request_secrets["fail_token"] = "request_secret"

        mock_instance = MagicMock()
        mock_instance.token = None
        mock_instance.access_token_secret = None
        mock_client_cls.return_value = mock_instance

        client = TestClient(app)
        response = client.get(
            "/auth/callback?oauth_token=fail_token&oauth_verifier=verifier_123",
        )

        assert response.status_code == 500
        assert "Failed to obtain access token" in response.json()["detail"]


@pytest.mark.unit
class TestAuthLogin:
    """Test the /auth/login endpoint."""

    @patch("issue_tracker_service.routes.auth._trello_config")
    @patch("issue_tracker_service.routes.auth.TrelloClient")
    def test_login_redirects_to_trello(
        self,
        mock_client_cls: MagicMock,
        mock_config: MagicMock,
    ) -> None:
        mock_config.return_value = {
            "api_key": "k",
            "secret": "s",
            "callback_url": "http://localhost/cb",
        }
        mock_instance = MagicMock()
        mock_instance.get_authorization_url.return_value = (
            "https://trello.com/1/OAuthAuthorizeToken?oauth_token=req_tok_123"
        )
        mock_instance.request_token_secret = "req_secret"
        mock_client_cls.return_value = mock_instance

        client = TestClient(app, follow_redirects=False)
        response = client.get("/auth/login")

        assert response.status_code == 302
        assert "trello.com" in response.headers.get("location", "")

    @patch("issue_tracker_service.routes.auth._trello_config")
    @patch("issue_tracker_service.routes.auth.TrelloClient")
    def test_login_fails_without_oauth_token(
        self,
        mock_client_cls: MagicMock,
        mock_config: MagicMock,
    ) -> None:
        mock_config.return_value = {
            "api_key": "k",
            "secret": "s",
            "callback_url": "http://localhost/cb",
        }
        mock_instance = MagicMock()
        mock_instance.get_authorization_url.return_value = "https://trello.com/authorize"
        mock_instance.request_token_secret = "secret"
        mock_client_cls.return_value = mock_instance

        client = TestClient(app)
        response = client.get("/auth/login")

        assert response.status_code == 500


@pytest.mark.unit
class TestGetAuthenticatedClient:
    """Test the get_authenticated_client dependency."""

    @patch("issue_tracker_service.main._trello_config")
    def test_invalid_session_token_returns_401(self, mock_config: MagicMock) -> None:
        mock_config.return_value = {
            "api_key": "k",
            "secret": "s",
            "callback_url": "http://localhost/cb",
        }
        app.dependency_overrides.clear()

        client = TestClient(app)
        response = client.get(
            "/boards",
            headers={"X-Session-Token": "nonexistent_token"},
        )

        assert response.status_code == 401
        app.dependency_overrides.clear()
