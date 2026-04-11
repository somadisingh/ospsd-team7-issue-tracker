"""Board contract - re-exports the shared vertical Board ABC."""

from api.board import Board

__all__ = ["Board"]


def get_board(board_id: str) -> Board:
    """Return a board by its ID."""
    raise NotImplementedError("Subclasses must implement get_board")
