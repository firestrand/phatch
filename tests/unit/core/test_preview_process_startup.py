from __future__ import annotations

from pathlib import Path

import pytest

from phatch.services import preview_process
from phatch.services.preview_process import PreviewStartupError, start_preview
from phatch.services.preview_types import (
    PreviewExecutionSpec,
    PreviewLimits,
    PreviewReadContext,
    PreviewSize,
    PreviewSource,
)


class _Endpoint:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _FailingProcess:
    def __init__(self, starts_child: bool) -> None:
        self._starts_child = starts_child
        self.pid: int | None = None
        self.terminated = False
        self.joined = False

    def start(self) -> None:
        if self._starts_child:
            self.pid = 4321
        raise OSError("spawn unavailable")

    def is_alive(self) -> bool:
        return self.pid is not None and not self.terminated

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.terminated = True

    def join(self, timeout: float | None = None) -> None:
        if self.pid is None:
            raise AssertionError("join called before process start")
        self.joined = True


class _FailingContext:
    def __init__(self, starts_child: bool) -> None:
        self.receiver = _Endpoint()
        self.sender = _Endpoint()
        self.process = _FailingProcess(starts_child)

    def Pipe(self, duplex: bool) -> tuple[_Endpoint, _Endpoint]:
        return self.receiver, self.sender

    def Process(self, *, target, args) -> _FailingProcess:
        return self.process


def _spec() -> PreviewExecutionSpec:
    source = PreviewSource(
        Path("source.png"), "digest", PreviewSize(8, 6), "RGB", "PNG"
    )
    return PreviewExecutionSpec(
        (),
        source,
        (),
        (),
        PreviewLimits(),
        PreviewReadContext(source, ()),
        False,
    )


@pytest.mark.parametrize("starts_child", [False, True])
def test_start_preview_closes_pipe_when_process_start_fails(
    monkeypatch: pytest.MonkeyPatch,
    starts_child: bool,
) -> None:
    context = _FailingContext(starts_child)
    monkeypatch.setattr(
        preview_process.multiprocessing, "get_context", lambda _: context
    )

    with pytest.raises(PreviewStartupError) as captured:
        start_preview(_spec(), "startup-failure")

    assert isinstance(captured.value, OSError)
    assert captured.value.request_id == "startup-failure"
    assert isinstance(captured.value.__cause__, OSError)
    assert context.receiver.closed
    assert context.sender.closed
    assert context.process.terminated is starts_child
    assert context.process.joined is starts_child
