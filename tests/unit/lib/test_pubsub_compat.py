from __future__ import annotations

import pytest

from phatch.lib.pyWx import pubsub_compat

PUBLISHER = vars(pubsub_compat)["Publisher"]


@pytest.fixture(autouse=True)
def isolated_publisher() -> None:
    PUBLISHER.listeners.clear()


def test_topic_and_all_subscribers_receive_keyword_payload() -> None:
    received: list[tuple[str, int]] = []
    PUBLISHER.subscribe(lambda *, value: received.append(("topic", value)), "render")
    PUBLISHER.subscribe(lambda *, value: received.append(("all", value)))

    PUBLISHER.sendMessage("render", value=12)

    assert received == [("topic", 12), ("all", 12)]


def test_all_topic_is_delivered_once() -> None:
    received: list[int] = []
    PUBLISHER.subscribe(lambda *, value: received.append(value))

    PUBLISHER.sendMessage(value=13)

    assert received == [13]


def test_duplicate_subscriptions_are_independent_until_unsubscribed() -> None:
    received: list[int] = []

    def listener(*, value: int) -> None:
        received.append(value)

    PUBLISHER.subscribe(listener, "duplicate")
    PUBLISHER.subscribe(listener, "duplicate")

    PUBLISHER.sendMessage("duplicate", value=14)
    PUBLISHER.unsubscribe(listener, "duplicate")
    PUBLISHER.sendMessage("duplicate", value=15)

    assert received == [14, 14, 15]


def test_unknown_unsubscribe_and_clear_are_no_ops() -> None:
    def listener(**_payload) -> None:
        return None

    PUBLISHER.unsubscribe(listener, "missing")
    PUBLISHER.subscribe(listener, "kept")
    PUBLISHER.unsubscribe(lambda **_payload: None, "kept")
    PUBLISHER.unsubAll("missing")

    assert PUBLISHER.listeners == {"kept": [listener]}


def test_unsub_all_clears_only_requested_topic() -> None:
    received: list[str] = []
    PUBLISHER.subscribe(lambda: received.append("first"), "first")
    PUBLISHER.subscribe(lambda: received.append("second"), "second")

    PUBLISHER.unsubAll("first")
    PUBLISHER.sendMessage("first")
    PUBLISHER.sendMessage("second")

    assert received == ["second"]
    assert PUBLISHER.listeners["first"] == []


def test_listener_failures_are_reported_without_stopping_other_delivery(capsys) -> None:
    received: list[str] = []

    def fail() -> None:
        raise RuntimeError("topic failed")

    def fail_all() -> None:
        raise RuntimeError("all failed")

    PUBLISHER.subscribe(fail, "failure")
    PUBLISHER.subscribe(lambda: received.append("topic"), "failure")
    PUBLISHER.subscribe(fail_all)
    PUBLISHER.subscribe(lambda: received.append("all"))

    PUBLISHER.sendMessage("failure")

    assert received == ["topic", "all"]
    output = capsys.readouterr().out
    assert "Error in listener for topic failure: topic failed" in output
    assert "Error in 'all' listener for topic failure: all failed" in output
