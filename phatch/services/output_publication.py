from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from phatch.services.output_rollback import OriginalDestination, RollbackError


@dataclass(frozen=True, slots=True)
class OutputIdentity:
    path: Path
    size: int
    sha256: str
    modified_ns: int
    original: OriginalDestination | None = None


@dataclass(frozen=True, slots=True)
class PublishedOutput:
    identity: OutputIdentity
    survived: bool


@dataclass(frozen=True, slots=True)
class PublicationSucceeded:
    outputs: tuple[PublishedOutput, ...]


@dataclass(frozen=True, slots=True)
class PublicationFailed:
    cause: OSError | KeyboardInterrupt
    outputs: tuple[PublishedOutput, ...]
    rollback_error: RollbackError | None
    cleanup_errors: tuple[OSError | KeyboardInterrupt, ...] = ()


PublicationResult: TypeAlias = PublicationSucceeded | PublicationFailed


def publication_outputs(
    identities: tuple[OutputIdentity, ...],
) -> tuple[PublishedOutput, ...]:
    return tuple(
        PublishedOutput(identity, _matches_destination(identity))
        for identity in identities
    )


def _matches_destination(identity: OutputIdentity) -> bool:
    path = identity.path
    if not path.is_file():
        return False
    stat = path.stat()
    if stat.st_size != identity.size or stat.st_mtime_ns != identity.modified_ns:
        return False
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest() == identity.sha256


def output_identity(stage: Path, destination: Path) -> OutputIdentity:
    digest = hashlib.sha256()
    with stage.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    stat = stage.stat()
    return OutputIdentity(
        destination, stat.st_size, digest.hexdigest(), stat.st_mtime_ns
    )
