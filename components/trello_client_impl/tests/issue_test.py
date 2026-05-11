"""Unit tests for the TrelloCard implementation."""

from typing import Any

import pytest
from api.issue import Status
from trello_client_impl.issue import (
    TrelloCard,
    _infer_status,
    _warned_unknown_status_lists,
)


@pytest.mark.unit
class TestTrelloCard:
    """Test the TrelloCard implementation."""

    def test_trello_card_initialization(self) -> None:
        card = TrelloCard(
            id="card_123",
            title="Test Card",
            desc="A description",
            status=Status.TO_DO,
            board_id="board_123",
        )
        assert card.id == "card_123"
        assert card.title == "Test Card"
        assert card.desc == "A description"
        assert card.status == Status.TO_DO
        assert card.board_id == "board_123"

    def test_trello_card_from_api(self, mock_card_response: Any) -> None:
        card = TrelloCard.from_api(mock_card_response, list_name="To Do")
        assert card.id == mock_card_response["id"]
        assert card.title == mock_card_response["name"]
        assert card.desc == mock_card_response["desc"]
        assert card.status == Status.TO_DO

    def test_trello_card_properties(self) -> None:
        card = TrelloCard(
            id="test_id",
            title="Test",
            desc="desc",
            members=["m1"],
            due_date="2024-01-01",
            status=Status.COMPLETED,
            board_id="board_1",
        )
        assert card.id == "test_id"
        assert card.title == "Test"
        assert card.desc == "desc"
        assert card.members == ["m1"]
        assert card.due_date == "2024-01-01"
        assert card.status == Status.COMPLETED
        assert card.board_id == "board_1"


@pytest.mark.unit
class TestInferStatus:
    """Test the list-name to status inference logic."""

    def test_to_do_list(self) -> None:
        assert _infer_status("To Do") == Status.TO_DO

    def test_backlog_list(self) -> None:
        assert _infer_status("Backlog") == Status.TO_DO

    def test_in_progress_list(self) -> None:
        assert _infer_status("In Progress") == Status.IN_PROGRESS

    def test_doing_list(self) -> None:
        assert _infer_status("Doing") == Status.IN_PROGRESS

    def test_done_list(self) -> None:
        assert _infer_status("Done") == Status.COMPLETED

    def test_completed_list(self) -> None:
        assert _infer_status("Completed") == Status.COMPLETED

    def test_unknown_defaults_to_todo(self) -> None:
        assert _infer_status("Random Column") == Status.TO_DO

    def test_unknown_list_logs_warning_once(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        _warned_unknown_status_lists.clear()
        caplog.set_level("WARNING")

        assert _infer_status("Custom Stage") == Status.TO_DO
        assert _infer_status("Custom Stage") == Status.TO_DO

        warning_records = [
            r for r in caplog.records if "Unknown Trello list name" in r.message
        ]
        assert len(warning_records) == 1
