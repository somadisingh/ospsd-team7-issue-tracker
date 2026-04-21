from chat_client_api import (
    ChannelNotFoundError,
    MessageDeleteError,
    MessageNotFoundError,
    get_client,
    register_client,
)

import pytest

from chat_client_impl import get_client_impl


@pytest.fixture(autouse=True)
def local_client_registered() -> None:
    # Make sure the shared API is wired to the local implementation
    # before every test runs.
    register_client(get_client_impl)


def test_send_message_and_retrieve_it() -> None:
    client = get_client()
    message = client.send_message("general", "Hello from chat-client-api")

    assert message.channel == "general"
    assert message.text == "Hello from chat-client-api"
    assert message.sender == "local-bot"

    fetched = client.get_message(message.message_id)
    assert fetched == message


def test_get_channels_returns_empty_list() -> None:
    client = get_client()
    channels = client.get_channels()

    assert channels == []


def test_get_channel_always_raises_channel_not_found_error() -> None:
    client = get_client()

    with pytest.raises(ChannelNotFoundError):
        client.get_channel("general")


def test_get_messages_returns_recent_messages_in_order() -> None:
    client = get_client()
    first_message = client.send_message("random", "first")
    second_message = client.send_message("random", "second")

    messages = client.get_messages("random", limit=2)
    assert [message.message_id for message in messages] == [second_message.message_id, first_message.message_id]


def test_delete_message_removes_message_and_raises_afterwards() -> None:
    client = get_client()
    message = client.send_message("general", "delete me")
    client.delete_message(message.message_id)

    with pytest.raises(MessageNotFoundError):
        client.get_message(message.message_id)

    with pytest.raises(MessageDeleteError):
        client.delete_message(message.message_id)
