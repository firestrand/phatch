from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final

_SAFE_REPLACE: Final = os.replace


@dataclass(frozen=True, slots=True)
class OriginalDestination:
    destination: Path
    existed: bool
    backup: Path | None


@dataclass(frozen=True, slots=True)
class RollbackFailure:
    destination: Path
    backup: Path | None
    error: OSError


class RollbackError(OSError):
    __slots__ = ("failures",)

    def __init__(self, failures: tuple[RollbackFailure, ...]) -> None:
        self.failures = failures
        super().__init__(str(self))

    def __str__(self) -> str:
        destinations = ", ".join(str(failure.destination) for failure in self.failures)
        return f"could not restore output destinations: {destinations}"


class PublicationRollbackError(OSError):
    __slots__ = ("publication_error", "rollback_error")

    def __init__(
        self,
        publication_error: OSError,
        rollback_error: RollbackError,
    ) -> None:
        self.publication_error = publication_error
        self.rollback_error = rollback_error
        super().__init__(str(self))

    def __str__(self) -> str:
        return f"{self.publication_error}; {self.rollback_error}"


def reserve_original(destination: Path) -> OriginalDestination:
    if not destination.exists():
        return OriginalDestination(destination, False, None)
    descriptor, raw_backup = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".bak", dir=destination.parent
    )
    os.close(descriptor)
    backup = Path(raw_backup)
    backup.unlink()
    return OriginalDestination(destination, True, backup)


def backup_originals(originals: tuple[OriginalDestination, ...]) -> None:
    backed_up: list[OriginalDestination] = []
    try:
        for original in originals:
            if original.backup is not None:
                _SAFE_REPLACE(original.destination, original.backup)
                backed_up.append(original)
    except OSError as publication_error:
        try:
            restore_originals(tuple(backed_up))
        except RollbackError as rollback_error:
            raise PublicationRollbackError(
                publication_error, rollback_error
            ) from publication_error
        raise


def restore_originals(originals: tuple[OriginalDestination, ...]) -> None:
    failures: list[RollbackFailure] = []
    for original in reversed(originals):
        try:
            if original.backup is None:
                original.destination.unlink(missing_ok=True)
            elif original.backup.exists():
                _SAFE_REPLACE(original.backup, original.destination)
        except OSError as error:
            failures.append(
                RollbackFailure(original.destination, original.backup, error)
            )
    if failures:
        raise RollbackError(tuple(failures))


def remove_backups(originals: tuple[OriginalDestination, ...]) -> None:
    for original in originals:
        if original.backup is not None:
            original.backup.unlink(missing_ok=True)
