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


class RecordingCallable:
    def __init__(
        self,
        name: str,
        received: list[tuple[str, tuple[str, ...], int]],
    ) -> None:
        self.name = name
        self.received = received

    def __call__(self, message: pubsub.Message) -> None:
        self.received.append((self.name, message.topic, message.data))


class RecordingTarget:
    def __init__(self, received: list[tuple[str, tuple[str, ...], int]]) -> None:
        self.received = received

    def notify(self, message: pubsub.Message) -> None:
        self.received.append(("bound", message.topic, message.data))


class ListenerFailure(RuntimeError):
    pass


def test_routes_message_to_all_parent_and_leaf_callable_kinds() -> None:
    publisher = pubsub.Publisher()
    received: list[tuple[str, tuple[str, ...], int]] = []
    callable_listener = RecordingCallable("parent", received)
    target = RecordingTarget(received)

    def all_topics(message: pubsub.Message) -> None:
        received.append(("all", message.topic, message.data))

    message_count = publisher.getMessageCount()
    delivery_count = publisher.getDeliveryCount()
    publisher.subscribe(all_topics)
    publisher.subscribe(callable_listener, "photos")
    publisher.subscribe(callable_listener, "photos")
    publisher.subscribe(target.notify, "photos.saved")

    publisher.sendMessage("photos.saved", 42)

    assert received == [
        ("all", ("photos", "saved"), 42),
        ("parent", ("photos", "saved"), 42),
        ("bound", ("photos", "saved"), 42),
    ]
    assert publisher.getMessageCount() - message_count == 1
    assert publisher.getDeliveryCount() - delivery_count == 3
    assert set(publisher.getAssociatedTopics(callable_listener)) == {("photos",)}
    assert publisher.isSubscribed(target.notify, ("photos", "saved"))


def test_singleton_message_and_all_topics_contract() -> None:
    publisher = pubsub.Publisher()
    message = pubsub.Message(("render",), {"quality": 90})

    assert publisher is pubsub.Publisher
    assert publisher() is publisher
    assert pubsub.getStrAllTopics() == pubsub.ALL_TOPICS == ""
    assert str(message) == "[Topic: ('render',),  Data: {'quality': 90}]"
    assert str(publisher) == "all: "


def test_unsubscribe_can_remove_one_topic_then_all_remaining_topics() -> None:
    publisher = pubsub.Publisher()
    received: list[tuple[str, tuple[str, ...], int]] = []
    listener = RecordingCallable("listener", received)
    publisher.subscribe(listener, "first")
    publisher.subscribe(listener, "second")

    publisher.unsubscribe(listener, "first")
    publisher.sendMessage("first", 1)
    publisher.sendMessage("second", 2)

    assert received == [("listener", ("second",), 2)]
    assert publisher.getAssociatedTopics(listener) == [("second",)]

    publisher.unsubscribe(listener)

    assert not publisher.isSubscribed(listener)
    assert publisher.getAssociatedTopics(listener) == []


def test_unsub_all_reports_unknown_topics_and_preserves_other_subscriptions() -> None:
    publisher = pubsub.Publisher()
    received: list[tuple[str, tuple[str, ...], int]] = []
    listener = RecordingCallable("listener", received)
    missing: list[tuple[str, ...]] = []
    publisher.subscribe(listener, "kept")
    publisher.subscribe(listener, "removed")

    publisher.unsubAll(["removed", "missing"], missing.append)
    publisher.sendMessage("kept", 3)
    publisher.sendMessage("removed", 4)

    assert received == [("listener", ("kept",), 3)]
    assert missing == [("missing",)]
    assert publisher.getAssociatedTopics(listener) == [("kept",)]


def test_unsub_all_scalar_removes_last_listener_for_topic() -> None:
    publisher = pubsub.Publisher()
    received: list[tuple[str, tuple[str, ...], int]] = []
    listener = RecordingCallable("listener", received)
    publisher.subscribe(listener, "sole")

    publisher.unsubAll("sole")
    publisher.sendMessage("sole", 4)

    assert received == []
    assert not publisher.isSubscribed(listener)


def test_unknown_topic_callback_receives_normalized_topic() -> None:
    publisher = pubsub.Publisher()
    unknown: list[tuple[str, ...]] = []

    publisher.sendMessage("never.created", onTopicNeverCreated=unknown.append)

    assert unknown == [("never", "created")]


def test_unknown_topic_without_callback_is_a_counted_no_op() -> None:
    publisher = pubsub.Publisher()
    message_count = publisher.getMessageCount()
    delivery_count = publisher.getDeliveryCount()

    publisher.sendMessage("unknown")

    assert publisher.getMessageCount() - message_count == 1
    assert publisher.getDeliveryCount() - delivery_count == 0


def test_listener_failure_propagates_without_counting_incomplete_delivery() -> None:
    publisher = pubsub.Publisher()

    def fail(_message: pubsub.Message) -> None:
        raise ListenerFailure

    message_count = publisher.getMessageCount()
    delivery_count = publisher.getDeliveryCount()
    publisher.subscribe(fail, "failure")

    with pytest.raises(ListenerFailure):
        publisher.sendMessage("failure", 5)

    assert publisher.getMessageCount() - message_count == 1
    assert publisher.getDeliveryCount() - delivery_count == 0


def test_unsubscribe_list_shape_and_unknown_listener_are_no_ops() -> None:
    publisher = pubsub.Publisher()
    received: list[tuple[str, tuple[str, ...], int]] = []
    listener = RecordingCallable("listener", received)
    unknown = RecordingCallable("unknown", received)
    publisher.subscribe(listener, "listed")

    publisher.unsubscribe(unknown)
    publisher.unsubscribe(listener, ["listed"])
    publisher.sendMessage("listed", 9)

    assert received == []
    assert not publisher.isSubscribed(listener, "listed")


def test_publisher_string_lists_function_bound_and_callable_listeners() -> None:
    publisher = pubsub.Publisher()
    received: list[tuple[str, tuple[str, ...], int]] = []
    callable_listener = RecordingCallable("callable", received)
    target = RecordingTarget(received)

    def function_listener(_message: pubsub.Message) -> None:
        return None

    publisher.subscribe(function_listener, "names")
    publisher.subscribe(target.notify, "names")
    publisher.subscribe(callable_listener, "names")

    rendered = str(publisher)

    assert "function_listener" in rendered
    assert "RecordingTarget" in rendered
    assert "RecordingCallable" in rendered
