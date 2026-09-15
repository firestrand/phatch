from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from contextvars import ContextVar
from dataclasses import dataclass
from threading import Lock
from typing import Literal, NewType, TypeAlias
from uuid import uuid4

CompletionRequestId = NewType("CompletionRequestId", str)
CompletionOwner: TypeAlias = Literal["gui", "droplet", "console", "automation"]


@dataclass(frozen=True, slots=True)
class CompletionReceipt:
    request_id: CompletionRequestId
    owner: CompletionOwner


CompletionSink: TypeAlias = Callable[[CompletionReceipt], None]
_COMPLETION_SINK: ContextVar[CompletionSink | None] = ContextVar(
    "completion_sink", default=None
)


@dataclass(frozen=True, slots=True)
class CompletionOwnerMismatchError(RuntimeError):
    active_owner: CompletionOwner
    requested_owner: CompletionOwner

    def __str__(self) -> str:
        return (
            f"completion request is owned by {self.active_owner!r}, "
            f"not {self.requested_owner!r}"
        )


class CompletionDispatcher:
    __slots__ = ("_emitted", "_lock", "_receipt", "_sink")

    def __init__(self, owner: CompletionOwner) -> None:
        self._receipt = CompletionReceipt(CompletionRequestId(uuid4().hex), owner)
        self._sink = _COMPLETION_SINK.get()
        self._emitted = False
        self._lock = Lock()

    @property
    def owner(self) -> CompletionOwner:
        return self._receipt.owner

    @property
    def receipt(self) -> CompletionReceipt:
        return self._receipt

    def complete(self) -> CompletionReceipt:
        with self._lock:
            first_completion = not self._emitted
            self._emitted = True
        if first_completion and self._sink is not None:
            with suppress(Exception):
                self._sink(self._receipt)
        return self._receipt


_ACTIVE_DISPATCHER: ContextVar[CompletionDispatcher | None] = ContextVar(
    "completion_dispatcher", default=None
)


@contextmanager
def collect_completion_events(sink: CompletionSink) -> Iterator[None]:
    token = _COMPLETION_SINK.set(sink)
    try:
        yield
    finally:
        _COMPLETION_SINK.reset(token)


@contextmanager
def completion_dispatch(owner: CompletionOwner) -> Iterator[CompletionDispatcher]:
    active = _ACTIVE_DISPATCHER.get()
    if active is not None:
        if active.owner != owner:
            raise CompletionOwnerMismatchError(active.owner, owner)
        yield active
        return
    dispatcher = CompletionDispatcher(owner)
    token = _ACTIVE_DISPATCHER.set(dispatcher)
    try:
        yield dispatcher
    finally:
        dispatcher.complete()
        _ACTIVE_DISPATCHER.reset(token)
