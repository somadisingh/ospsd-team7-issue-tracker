"""Unit tests for ServiceMember."""

from unittest.mock import MagicMock

import pytest
from issue_tracker_adapter.member import ServiceMember
from issue_tracker_client_api.member import Member


@pytest.mark.unit
class TestServiceMember:
    """Test the ServiceMember adapter implementation."""

    def test_service_member_initialization(self) -> None:
        member = ServiceMember(id="m1", username="alice", is_board_member=True)
        assert member.id == "m1"
        assert member.username == "alice"
        assert member.is_board_member is True

    def test_service_member_is_instance_of_member(self) -> None:
        member = ServiceMember(id="m1", username="bob")
        assert isinstance(member, Member)

    def test_service_member_defaults(self) -> None:
        member = ServiceMember(id="m1")
        assert member.username is None
        assert member.is_board_member is None

    def test_service_member_properties(self) -> None:
        member = ServiceMember(id="m1", username="charlie", is_board_member=False)
        assert hasattr(member, "id")
        assert hasattr(member, "username")
        assert hasattr(member, "is_board_member")

    def test_service_member_from_response(
        self, mock_member_response: MagicMock
    ) -> None:
        member = ServiceMember.from_response(mock_member_response)
        assert member.id == mock_member_response.id
        assert member.username == mock_member_response.username
        assert isinstance(member, ServiceMember)
        assert isinstance(member, Member)
