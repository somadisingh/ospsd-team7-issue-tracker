"""Integration tests for the issue tracker components."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from issue_tracker_adapter import ServiceClientAdapter
from issue_tracker_adapter import register as adapter_register
from issue_tracker_adapter.board import ServiceBoard
from issue_tracker_adapter.client import get_client_impl as adapter_get_client_impl
from issue_tracker_adapter.issue import ServiceIssue
from issue_tracker_adapter.list import ServiceList
from issue_tracker_adapter.member import ServiceMember
from issue_tracker_client_api import Board, Client, Issue, List, Member
from issue_tracker_service_client.models.board_response import BoardResponse
from issue_tracker_service_client.models.issue_response import IssueResponse
from issue_tracker_service_client.models.list_response import ListResponse
from issue_tracker_service_client.models.member_response import MemberResponse
from pytest_mock import MockerFixture
from trello_client_impl import (
    TrelloBoard,
    TrelloCard,
    TrelloClient,
    TrelloList,
    TrelloMember,
    get_client_impl,
)


@pytest.mark.integration
class TestClientInterfaceImplementation:
    """Test that TrelloClient properly implements the Client interface."""

    def test_trello_client_is_instance_of_client(
        self, integration_credentials: dict[str, str], mocker: MockerFixture
    ) -> None:
        """Test that TrelloClient is an instance of Client."""
        client = TrelloClient(**integration_credentials)
        assert isinstance(client, Client)

    def test_trello_client_implements_all_methods(
        self, integration_credentials: dict[str, str], mocker: MockerFixture
    ) -> None:
        """Test that TrelloClient implements all required Client methods."""
        client = TrelloClient(**integration_credentials)
        required_methods = [
            "get_issue",
            "delete_issue",
            "update_status",
            "get_board",
            "get_boards",
            "create_board",
            "add_member_to_board",
            "get_list",
            "get_lists",
            "get_issues_in_list",
            "create_list",
            "update_list",
            "delete_list",
            "get_members_on_issue",
            "assign_issue",
            "create_issue",
        ]
        for method in required_methods:
            assert hasattr(client, method)
            assert callable(getattr(client, method))


@pytest.mark.integration
class TestTrelloCardInterfaceImplementation:
    """Test that TrelloCard properly implements the Issue interface."""

    def test_trello_card_is_instance_of_issue(self) -> None:
        """Test that TrelloCard is an instance of Issue."""
        card = TrelloCard(
            id="test_id",
            title="Test",
            is_complete=False,
            board_id="board_1",
            list_id="test_list_id",
        )
        assert isinstance(card, Issue)

    def test_trello_card_implements_issue_interface(self) -> None:
        """Test that TrelloCard implements all Issue properties."""
        card = TrelloCard(
            id="test_id",
            title="Test",
            is_complete=False,
            board_id="board_1",
            list_id="test_list_id",
        )
        assert hasattr(card, "id")
        assert hasattr(card, "title")
        assert hasattr(card, "is_complete")
        assert hasattr(card, "list_id")
        assert hasattr(card, "board_id")


@pytest.mark.integration
class TestTrelloBoardInterfaceImplementation:
    """Test that TrelloBoard properly implements the Board interface."""

    def test_trello_board_is_instance_of_board(self) -> None:
        """Test that TrelloBoard is an instance of Board."""
        board = TrelloBoard(id="board_id", name="Test Board")
        assert isinstance(board, Board)

    def test_trello_board_implements_board_interface(self) -> None:
        """Test that TrelloBoard implements all Board properties."""
        board = TrelloBoard(id="board_id", name="Test Board")
        assert hasattr(board, "id")
        assert hasattr(board, "name")
        assert board.id == "board_id"
        assert board.name == "Test Board"


@pytest.mark.integration
class TestTrelloListInterfaceImplementation:
    """Test that TrelloList properly implements the List interface."""

    def test_trello_list_is_instance_of_list(self) -> None:
        """Test that TrelloList is an instance of List."""
        list_obj = TrelloList(id="list_id", name="To Do", board_id="board_1")
        assert isinstance(list_obj, List)

    def test_trello_list_implements_list_interface(self) -> None:
        """Test that TrelloList implements all List properties."""
        list_obj = TrelloList(id="list_id", name="To Do", board_id="board_1")
        assert hasattr(list_obj, "id")
        assert hasattr(list_obj, "name")
        assert list_obj.id == "list_id"
        assert list_obj.name == "To Do"


@pytest.mark.integration
class TestTrelloMemberInterfaceImplementation:
    """Test that TrelloMember properly implements the Member interface."""

    def test_trello_member_is_instance_of_member(self) -> None:
        """Test that TrelloMember is an instance of Member."""
        member = TrelloMember(id="member_id", username="testuser")
        assert isinstance(member, Member)

    def test_trello_member_implements_member_interface(self) -> None:
        """Test that TrelloMember implements all Member properties."""
        member = TrelloMember(id="member_id", username="testuser", is_board_member=True)
        assert hasattr(member, "id")
        assert hasattr(member, "username")
        assert hasattr(member, "is_board_member")


@pytest.mark.integration
class TestClientWorkflows:
    """Test multi-step client workflows with mocked requests."""

    def test_get_issue_and_update_status_workflow(
        self,
        integration_credentials: dict[str, str],
        mocker: MockerFixture,
        mock_issue_response: dict[str, Any],
    ) -> None:
        """Test workflow: get issue then update its status."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_issue_response
        mock_request = mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )

        client = TrelloClient(
            **integration_credentials,
            status_list_ids={"complete": "list_done_id"},
        )

        issue = client.get_issue("issue_id")
        assert issue is not None

        result = client.update_status("issue_id", "complete")
        assert result is True
        assert mock_request.call_count >= 2

    def test_get_board_and_lists_and_issues_workflow(
        self,
        integration_credentials: dict[str, str],
        mocker: MockerFixture,
        mock_board_response: dict[str, Any],
        mock_list_response: dict[str, Any],
        mock_issue_response: dict[str, Any],
    ) -> None:
        """Test workflow: get board, get lists, then get issues in a list."""
        mock_response = MagicMock()
        mock_response.json.side_effect = [
            mock_board_response,
            [mock_list_response],
            [mock_issue_response],
        ]
        mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )

        client = TrelloClient(**integration_credentials)

        board = client.get_board("board_id")
        assert board is not None
        assert isinstance(board, Board)

        lists = list(client.get_lists("board_id"))
        assert isinstance(lists, list)
        if lists:
            issues = list(client.get_issues_in_list(lists[0].id, max_issues=10))
            assert isinstance(issues, list)

    def test_get_issue_members_workflow(
        self,
        integration_credentials: dict[str, str],
        mocker: MockerFixture,
        mock_member_response: dict[str, Any],
    ) -> None:
        """Test workflow: get issue and its members."""
        mock_response = MagicMock()
        mock_response.json.return_value = [mock_member_response]
        mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )

        client = TrelloClient(**integration_credentials)

        members = client.get_members_on_issue("issue_id")
        assert isinstance(members, list)
        assert len(members) > 0
        assert isinstance(members[0], Member)


@pytest.mark.integration
class TestFactoryFunctions:
    """Test factory functions work correctly."""

    def test_get_client_impl_returns_proper_client(
        self, integration_credentials: dict[str, str], mocker: MockerFixture
    ) -> None:
        """Test get_client_impl returns a working Client instance."""
        client = get_client_impl(**integration_credentials)
        assert isinstance(client, Client)
        assert isinstance(client, TrelloClient)

    def test_client_from_factory_is_usable(
        self,
        integration_credentials: dict[str, str],
        mocker: MockerFixture,
        mock_issue_response: dict[str, Any],
    ) -> None:
        """Test that client from factory can perform operations."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_issue_response
        mocker.patch(
            "trello_client_impl.client.requests.request",
            return_value=mock_response,
        )

        client = get_client_impl(**integration_credentials)
        issue = client.get_issue("test_id")
        assert issue is not None


# ======================================================================
# Adapter component integration tests
# ======================================================================


@pytest.mark.integration
class TestAdapterInterfaceImplementation:
    """Test that ServiceClientAdapter properly implements the Client interface."""

    def test_adapter_is_instance_of_client(self) -> None:
        adapter = ServiceClientAdapter(
            base_url="https://example.com",
            session_token="tok",
        )
        assert isinstance(adapter, Client)

    def test_adapter_implements_all_methods(self) -> None:
        adapter = ServiceClientAdapter(
            base_url="https://example.com",
            session_token="tok",
        )
        required_methods = [
            "get_issue",
            "delete_issue",
            "update_status",
            "get_board",
            "get_boards",
            "create_board",
            "add_member_to_board",
            "get_list",
            "get_lists",
            "get_issues_in_list",
            "create_list",
            "update_list",
            "delete_list",
            "get_members_on_issue",
            "assign_issue",
            "create_issue",
        ]
        for method in required_methods:
            assert hasattr(adapter, method)
            assert callable(getattr(adapter, method))


@pytest.mark.integration
class TestAdapterDomainObjects:
    """Test that adapter domain objects implement the correct interfaces."""

    def test_service_board_is_instance_of_board(self) -> None:
        board = ServiceBoard(id="b1", name="Test")
        assert isinstance(board, Board)

    def test_service_issue_is_instance_of_issue(self) -> None:
        issue = ServiceIssue(
            id="i1",
            title="T",
            is_complete=False,
            list_id="l1",
            board_id="b1",
        )
        assert isinstance(issue, Issue)

    def test_service_list_is_instance_of_list(self) -> None:
        lst = ServiceList(id="l1", name="To Do", board_id="b1")
        assert isinstance(lst, List)

    def test_service_member_is_instance_of_member(self) -> None:
        member = ServiceMember(id="m1", username="alice")
        assert isinstance(member, Member)


@pytest.mark.integration
class TestAdapterFactoryAndRegistration:
    """Test adapter factory function and DI registration."""

    def test_adapter_factory_returns_client(self) -> None:
        client = adapter_get_client_impl(
            base_url="https://example.com",
            session_token="tok",
        )
        assert isinstance(client, Client)
        assert isinstance(client, ServiceClientAdapter)

    def test_adapter_register_replaces_global_factory(self) -> None:
        import issue_tracker_client_api

        original = issue_tracker_client_api.get_client
        try:
            adapter_register()
            client = issue_tracker_client_api.get_client(
                base_url="https://example.com",
                session_token="tok",
            )
            assert isinstance(client, ServiceClientAdapter)
        finally:
            issue_tracker_client_api.get_client = original

    @patch("issue_tracker_adapter.client.list_boards_api")
    def test_adapter_get_boards_with_service_client(self, mock_api: MagicMock) -> None:
        """Verify adapter correctly converts auto-generated BoardResponse to Board ABC."""
        resp = MagicMock(spec=BoardResponse)
        resp.id = "b1"
        resp.name = "Board"
        mock_api.sync.return_value = [resp]

        client = adapter_get_client_impl(
            base_url="https://example.com",
            session_token="tok",
        )
        boards = list(client.get_boards())
        assert len(boards) == 1
        assert isinstance(boards[0], Board)
        assert boards[0].id == "b1"

    @patch("issue_tracker_adapter.client.get_issue_api")
    def test_adapter_get_issue_with_service_client(self, mock_api: MagicMock) -> None:
        """Verify adapter correctly converts auto-generated IssueResponse to Issue ABC."""
        resp = MagicMock(spec=IssueResponse)
        resp.id = "i1"
        resp.title = "Task"
        resp.is_complete = False
        resp.list_id = "l1"
        resp.board_id = "b1"
        mock_api.sync.return_value = resp

        client = adapter_get_client_impl(
            base_url="https://example.com",
            session_token="tok",
        )
        issue = client.get_issue("i1")
        assert isinstance(issue, Issue)
        assert issue.title == "Task"

    @patch("issue_tracker_adapter.client.get_list_api")
    def test_adapter_get_list_with_service_client(self, mock_api: MagicMock) -> None:
        """Verify adapter correctly converts auto-generated ListResponse to List ABC."""
        resp = MagicMock(spec=ListResponse)
        resp.id = "l1"
        resp.name = "To Do"
        resp.board_id = "b1"
        mock_api.sync.return_value = resp

        client = adapter_get_client_impl(
            base_url="https://example.com",
            session_token="tok",
        )
        lst = client.get_list("l1")
        assert isinstance(lst, List)
        assert lst.name == "To Do"

    @patch("issue_tracker_adapter.client.get_members_api")
    def test_adapter_get_members_with_service_client(self, mock_api: MagicMock) -> None:
        """Verify adapter correctly converts auto-generated MemberResponse to Member ABC."""
        resp = MagicMock(spec=MemberResponse)
        resp.id = "m1"
        resp.username = "alice"
        mock_api.sync.return_value = [resp]

        client = adapter_get_client_impl(
            base_url="https://example.com",
            session_token="tok",
        )
        members = client.get_members_on_issue("i1")
        assert len(members) == 1
        assert isinstance(members[0], Member)
        assert members[0].username == "alice"

    @patch("issue_tracker_adapter.client.get_lists_api")
    def test_adapter_get_lists_with_service_client(self, mock_api: MagicMock) -> None:
        """Verify adapter correctly converts auto-generated ListResponse to List ABC."""
        resp = MagicMock(spec=ListResponse)
        resp.id = "l1"
        resp.name = "To Do"
        resp.board_id = "b1"
        mock_api.sync.return_value = [resp]

        client = adapter_get_client_impl(
            base_url="https://example.com",
            session_token="tok",
        )
        lists = list(client.get_lists("b1"))
        assert len(lists) == 1
        assert isinstance(lists[0], List)
        assert lists[0].name == "To Do"

    @patch("issue_tracker_adapter.client.update_list_api")
    def test_adapter_update_list_with_service_client(self, mock_api: MagicMock) -> None:
        """Verify adapter correctly converts auto-generated ListResponse after update."""
        resp = MagicMock(spec=ListResponse)
        resp.id = "l1"
        resp.name = "Renamed"
        resp.board_id = "b1"
        mock_api.sync.return_value = resp

        client = adapter_get_client_impl(
            base_url="https://example.com",
            session_token="tok",
        )
        lst = client.update_list("l1", "Renamed")
        assert isinstance(lst, List)
        assert lst.name == "Renamed"

    @patch("issue_tracker_adapter.client.delete_list_api")
    def test_adapter_delete_list_with_service_client(self, mock_api: MagicMock) -> None:
        """Verify adapter delete_list returns bool."""
        result = MagicMock()
        result.additional_properties = {"success": True}
        mock_api.sync.return_value = result

        client = adapter_get_client_impl(
            base_url="https://example.com",
            session_token="tok",
        )
        assert client.delete_list("l1") is True

    @patch("issue_tracker_adapter.client.add_member_api")
    def test_adapter_add_member_to_board_with_service_client(
        self, mock_api: MagicMock
    ) -> None:
        """Verify adapter add_member_to_board returns bool."""
        result = MagicMock()
        result.additional_properties = {"success": True}
        mock_api.sync.return_value = result

        client = adapter_get_client_impl(
            base_url="https://example.com",
            session_token="tok",
        )
        assert client.add_member_to_board("b1", "m1") is True
