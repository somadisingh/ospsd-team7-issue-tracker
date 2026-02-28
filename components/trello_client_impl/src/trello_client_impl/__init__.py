"""Public exports for the Issue Tracker client implementation package."""

from .board import TrelloBoard as TrelloBoard
from .client import TrelloClient as TrelloClient
from .client import get_client_impl as get_client_impl
from .client import register as register
from .issue import TrelloCard as TrelloCard
from .member import TrelloMember as TrelloMember

# Dependency Injection happens at import time
register()
