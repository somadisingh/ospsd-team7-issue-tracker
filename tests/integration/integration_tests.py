"""Integration tests for the issue tracker components."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from issue_tracker_client_api import Board, Client, Issue, List, Member
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
        card = TrelloCard(id="test_id", title="Test", is_complete=False)
        assert isinstance(card, Issue)

    def test_trello_card_implements_issue_interface(self) -> None:
        """Test that TrelloCard implements all Issue properties."""
        card = TrelloCard(id="test_id", title="Test", is_complete=False)
        assert hasattr(card, "id")
        assert hasattr(card, "is_complete")


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
        list_obj = TrelloList(id="list_id", name="To Do")
        assert isinstance(list_obj, List)

    def test_trello_list_implements_list_interface(self) -> None:
        """Test that TrelloList implements all List properties."""
        list_obj = TrelloList(id="list_id", name="To Do")
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
