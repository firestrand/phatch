import gc
import sys
from collections.abc import Generator
from pathlib import Path
from weakref import ReferenceType, ref

import pytest

sys.path.insert(0, str(Path(__file__).parents[3]))

from phatch.other import pubsub


@pytest.fixture(autouse=True)
def isolated_publisher() -> Generator[None, None, None]:
    publisher = pubsub.Publisher()
    publisher.unsubAll()
    gc.collect()
    yield
    publisher.unsubAll()
    gc.collect()


class CallableListener:
    def __init__(self, received: list[int]) -> None:
        self.received = received

    def __call__(self, message: pubsub.Message) -> None:
        self.received.append(message.data)


class MethodListener:
    def __init__(self, received: list[int]) -> None:
        self.received = received

    def receive(self, message: pubsub.Message) -> None:
        self.received.append(message.data)


def test_callable_subscription_does_not_keep_listener_alive() -> None:
    publisher = pubsub.Publisher()
    received: list[int] = []
    listener = CallableListener(received)
    listener_ref: ReferenceType[CallableListener] = ref(listener)
    publisher.subscribe(listener, "weak.callable")

    del listener
    gc.collect()
    publisher.sendMessage("weak.callable", 10)

    assert listener_ref() is None
    assert received == []


def test_bound_method_subscriptions_are_removed_when_owner_dies() -> None:
    publisher = pubsub.Publisher()
    received: list[int] = []
    listener = MethodListener(received)
    listener_ref: ReferenceType[MethodListener] = ref(listener)
    publisher.subscribe(listener.receive, "weak.parent")
    publisher.subscribe(listener.receive, "weak.parent.child")

    del listener
    gc.collect()
    publisher.sendMessage("weak.parent.child", 11)

    assert listener_ref() is None
    assert received == []


def test_live_bound_method_can_be_unsubscribed_using_fresh_method_wrapper() -> None:
    publisher = pubsub.Publisher()
    received: list[int] = []
    listener = MethodListener(received)
    publisher.subscribe(listener.receive, "bound")

    publisher.unsubscribe(listener.receive, "bound")
    publisher.sendMessage("bound", 12)

    assert received == []
    assert not publisher.isSubscribed(listener.receive, "bound")
    assert publisher.getAssociatedTopics(listener.receive) == []


def test_dead_listener_cleanup_keeps_live_listener_deliverable() -> None:
    publisher = pubsub.Publisher()
    received: list[int] = []
    live = CallableListener(received)
    publisher.subscribe(live, "cleanup")

    dead_refs: list[ReferenceType[CallableListener]] = []
    for _index in range(12):
        dead = CallableListener(received)
        dead_refs.append(ref(dead))
        publisher.subscribe(dead, "cleanup")
        del dead
    gc.collect()

    publisher.sendMessage("cleanup", 13)

    assert all(listener_ref() is None for listener_ref in dead_refs)
    assert received == [13]
    assert publisher.getAssociatedTopics(live) == [("cleanup",)]
