# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Sibling-file transactions with race-safe collision policies."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
import os
from pathlib import Path
import tempfile
from types import TracebackType
from typing import Literal

CollisionPolicy = Literal['replace', 'skip', 'fail', 'rename']
RENAME_ATTEMPTS = 10000
OutputPhase = Literal['created', 'finished']
_OBSERVER: ContextVar[Callable[[OutputPhase, Path, Path], None] | None] = (
    ContextVar('atomic_output_observer', default=None)
)


@contextmanager
def observe_outputs(
    observer: Callable[[OutputPhase, Path, Path], None],
) -> Iterator[None]:
    """Register each temporary and target before allowing output encoding."""
    token = _OBSERVER.set(observer)
    try:
        yield
    finally:
        _OBSERVER.reset(token)


class AtomicOutput:
    """Commit a completed sibling file; discard only this transaction's temp.

    ``committed`` is None when skip wins a collision. For rename it contains
    the actual chosen path. Link-based commits never overwrite another writer.
    """

    def __init__(
        self, target: Path | str, policy: CollisionPolicy = 'replace'
    ) -> None:
        if policy not in {'replace', 'skip', 'fail', 'rename'}:
            raise ValueError(f'Unknown collision policy: {policy}')
        self.target = Path(target)
        self.policy = policy
        self.temporary: Path | None = None
        self.committed: Path | None = None

    def __enter__(self) -> Path:
        descriptor, name = tempfile.mkstemp(
            prefix=f'.{self.target.stem}-',
            suffix=self.target.suffix,
            dir=self.target.parent,
        )
        os.close(descriptor)
        self.temporary = Path(name)
        try:
            observer = _OBSERVER.get()
            if observer is not None:
                observer('created', self.temporary, self.target)
        except BaseException:
            self.temporary.unlink(missing_ok=True)
            raise
        return self.temporary

    def _commit(self) -> None:
        assert self.temporary is not None
        with self.temporary.open('rb') as stream:
            os.fsync(stream.fileno())
        if self.policy == 'replace':
            os.replace(self.temporary, self.target)
            self.committed = self.target
            return
        candidate = self.target
        for index in range(RENAME_ATTEMPTS):
            try:
                os.link(self.temporary, candidate)
            except FileExistsError:
                if self.policy == 'skip':
                    return
                if self.policy == 'fail':
                    raise
                candidate = self.target.with_name(
                    f'{self.target.stem}-{index + 1}{self.target.suffix}'
                )
            else:
                self.committed = candidate
                return
        raise FileExistsError('Rename collision limit exceeded')

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if exc_type is None:
                self._commit()
        finally:
            if self.temporary is not None:
                self.temporary.unlink(missing_ok=True)
                observer = _OBSERVER.get()
                if observer is not None:
                    observer('finished', self.temporary, self.target)
