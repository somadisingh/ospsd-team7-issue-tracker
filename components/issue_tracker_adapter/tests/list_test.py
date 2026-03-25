"""Unit tests for ServiceList."""

from unittest.mock import MagicMock

import pytest
from issue_tracker_adapter.list import ServiceList
from issue_tracker_client_api.list import List as ListContract


@pytest.mark.unit
class TestServiceList:
    """Test the ServiceList adapter implementation."""

    def test_service_list_initialization(self) -> None:
        lst = ServiceList(id="list_1", name="To Do", board_id="board_1")
        assert lst.id == "list_1"
        assert lst.name == "To Do"
        assert lst.board_id == "board_1"

    def test_service_list_is_instance_of_list(self) -> None:
        lst = ServiceList(id="l1", name="Done", board_id="b1")
        assert isinstance(lst, ListContract)

    def test_service_list_properties(self) -> None:
        lst = ServiceList(id="test_id", name="In Progress", board_id="b1")
        assert hasattr(lst, "id")
        assert hasattr(lst, "name")
        assert hasattr(lst, "board_id")

    def test_service_list_from_response(self, mock_list_response: MagicMock) -> None:
        lst = ServiceList.from_response(mock_list_response)
        assert lst.id == mock_list_response.id
        assert lst.name == mock_list_response.name
        assert lst.board_id == mock_list_response.board_id
        assert isinstance(lst, ServiceList)
        assert isinstance(lst, ListContract)
