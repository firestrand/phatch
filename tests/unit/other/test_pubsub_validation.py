import sys
from collections.abc import Generator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[3]))

from phatch.other import pubsub


@pytest.fixture(autouse=True)
def isolated_publisher() -> Generator[None, None, None]:
    publisher = pubsub.Publisher()
    publisher.unsubAll()
    yield
    publisher.unsubAll()


@pytest.mark.parametrize(
    "listener",
    [
        7,
        lambda: None,
        lambda _message, _required: None,
        lambda **_keywords: None,
    ],
)
def test_rejects_listener_that_cannot_accept_exactly_one_message(listener) -> None:
    publisher = pubsub.Publisher()

    with pytest.raises(TypeError):
        publisher.subscribe(listener, "invalid")


def test_accepts_defaulted_and_variadic_listener_signatures() -> None:
    publisher = pubsub.Publisher()
    received: list[int] = []

    def defaulted(message: pubsub.Message | None = None) -> None:
        assert message is not None
        received.append(message.data)

    def variadic(*messages: pubsub.Message) -> None:
        received.append(messages[0].data)

    publisher.subscribe(defaulted, "valid")
    publisher.subscribe(variadic, "valid")

    publisher.sendMessage("valid", 8)

    assert received == [8, 8]
    assert publisher.isValid(defaulted)
    assert publisher.isValid(variadic)


def test_is_valid_returns_false_for_invalid_listener() -> None:
    publisher = pubsub.Publisher()

    assert not publisher.isValid(lambda: None)


@pytest.mark.parametrize(
    ("topic", "error_type"),
    [
        (None, TypeError),
        (["not", "a", "topic"], TypeError),
        (("valid", ""), ValueError),
    ],
)
def test_rejects_invalid_topic_shapes(topic, error_type) -> None:
    publisher = pubsub.Publisher()

    def listener(_message: pubsub.Message) -> None:
        return None

    with pytest.raises(error_type):
        publisher.subscribe(listener, topic)
