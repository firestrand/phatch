from __future__ import annotations

import runpy
from collections.abc import Generator
from pathlib import Path

import pytest

from phatch.lib import events
from phatch.other import pubsub


@pytest.fixture(autouse=True)
def isolated_publisher() -> Generator[None, None, None]:
    publisher = events.Publisher()
    publisher.unsubAll()
    yield
    publisher.unsubAll()


class RecordingReceiver(events.Receiver):
    def __init__(self) -> None:
        super().__init__("recording")
        self.received: list[tuple[int, str]] = []

    def record(self, value: int, *, label: str) -> str:
        self.received.append((value, label))
        return label


class DirectReceiver:
    def __init__(self) -> None:
        self.messages: list[pubsub.Message] = []

    def direct(self, message: pubsub.Message) -> None:
        self.messages.append(message)


def test_dynamic_sender_delivers_typed_arguments_to_receiver() -> None:
    receiver = RecordingReceiver()
    receiver.subscribe("record")

    events.send.recording_record(7, label="ready")

    assert receiver.received == [(7, "ready")]
    assert len(receiver._listeners) == 1


def test_receiver_unsubscribe_stops_delivery_and_removes_retained_listener() -> None:
    receiver = RecordingReceiver()
    receiver.subscribe("record")

    receiver.unsubscribe("record")
    events.send.recording_record(8, label="ignored")

    assert receiver.received == []
    assert receiver._listeners == []


def test_receiver_unsubscribe_all_stops_every_retained_listener() -> None:
    receiver = RecordingReceiver()
    receiver.subscribe("record")
    receiver.subscribe("record")

    receiver.unsubscribe_all()
    events.send.recording_record(9, label="ignored")

    assert receiver.received == []
    assert receiver._listeners == []


def test_receive_listener_forwards_return_value() -> None:
    receiver = RecordingReceiver()
    listener = events.ReceiveListener(receiver, "record")
    message = pubsub.Message(("manual",), ((10,), {"label": "forwarded"}))

    result = listener(message)

    assert result == "forwarded"
    assert receiver.received == [(10, "forwarded")]


def test_direct_subscribe_uses_named_bound_method_and_topic() -> None:
    receiver = DirectReceiver()
    events.subscribe("direct", receiver)

    events.Publisher().sendMessage("direct", 11)

    assert [message.data for message in receiver.messages] == [11]


def test_example_updates_state_and_writes_both_output_streams(capsys) -> None:
    events.example()

    output = capsys.readouterr()
    assert output.out == "hello world\n"
    assert output.err == "(No error.)"


def test_script_entrypoint_runs_the_example(capsys) -> None:
    runpy.run_path(str(Path(events.__file__)), run_name="__main__")

    output = capsys.readouterr()
    assert output.out == "hello world\n"
    assert output.err == "(No error.)"
