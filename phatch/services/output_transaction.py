from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol

from PIL import Image
from PIL.Image import Image as PillowImage

from phatch.services.output_publication import (
    OutputIdentity,
    PublicationFailed,
    PublicationResult,
    PublicationSucceeded,
    output_identity,
    publication_outputs,
)
from phatch.services.output_rollback import (
    OriginalDestination,
    RollbackError,
    backup_originals,
    remove_backups,
    reserve_original,
    restore_originals,
)


class PathOperation(Protocol):
    def __call__(self, path: Path, /) -> None: ...


class MetadataProvider(Protocol):
    def __call__(self, path: Path, /) -> str | None: ...


class ReplaceOperation(Protocol):
    def __call__(self, source: Path, destination: Path) -> None: ...


class MetadataUnavailableError(RuntimeError):
    __slots__ = ("reason",)

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)

    def __str__(self) -> str:
        return self.reason


class MetadataWriteError(RuntimeError):
    __slots__ = ("path", "reason")

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(str(self))

    def __str__(self) -> str:
        return f"metadata write failed for {self.path}: {self.reason}"


@dataclass(frozen=True, slots=True)
class OutputRequest:
    destination: Path
    encoder: PathOperation
    metadata: MetadataProvider
    validator: PathOperation
    modified_time_ns: int | None = None
    after_publish: Callable[[], None] = lambda: None


class OutputTransaction(Protocol):
    def execute(self, request: OutputRequest) -> OutputIdentity: ...


@dataclass(frozen=True, slots=True)
class PillowEncoder:
    image: PillowImage
    format_name: str

    def __call__(self, path: Path) -> None:
        self.image.save(path, format=self.format_name)


@dataclass(frozen=True, slots=True)
class PillowValidator:
    format_name: str
    expected_size: tuple[int, int] | None = None

    def __call__(self, path: Path) -> None:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.load()
            if image.format != self.format_name:
                raise OSError(
                    f"encoded format {image.format!r} does not match "
                    f"{self.format_name!r}"
                )
            if self.expected_size is not None and image.size != self.expected_size:
                raise OSError(
                    f"encoded dimensions {image.size!r} do not match "
                    f"{self.expected_size!r}"
                )


@dataclass(frozen=True, slots=True)
class NoMetadataProvider:
    def __call__(self, path: Path) -> str | None:
        return None

    def write(self, path: Path) -> None:
        self(path)


@dataclass(frozen=True, slots=True)
class NativeMetadataProvider:
    operation: MetadataProvider

    def __call__(self, path: Path) -> str | None:
        return self.write(path)

    def write(self, path: Path) -> str | None:
        try:
            diagnostic = self.operation(path)
        except ImportError as error:
            raise MetadataUnavailableError(str(error)) from error
        except (KeyError, OSError, ValueError) as error:
            raise MetadataWriteError(path, str(error)) from error
        if diagnostic:
            raise MetadataWriteError(path, diagnostic)
        return None


@dataclass(frozen=True, slots=True)
class PreparedOutput:
    stage: Path
    identity: OutputIdentity
    after_publish: Callable[[], None]


class AtomicOutputTransaction:
    __slots__ = ("_fsync", "_replace")

    def __init__(
        self,
        *,
        fsync: Callable[[int], None] = os.fsync,
        replace: ReplaceOperation | None = None,
    ) -> None:
        self._fsync = fsync
        self._replace = replace or os.replace

    def execute(self, request: OutputRequest) -> OutputIdentity:
        prepared = self.prepare(request)
        try:
            self.publish(prepared)
        finally:
            prepared.stage.unlink(missing_ok=True)
        return prepared.identity

    def prepare(self, request: OutputRequest) -> PreparedOutput:
        destination = request.destination
        descriptor, raw_stage = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        stage = Path(raw_stage)
        os.close(descriptor)
        prepared = False
        try:
            request.encoder(stage)
            request.metadata(stage)
            request.validator(stage)
            if request.modified_time_ns is not None:
                os.utime(stage, ns=(request.modified_time_ns, request.modified_time_ns))
            with stage.open("rb") as stream:
                self._fsync(stream.fileno())
            identity = output_identity(stage, destination)
            prepared = True
            return PreparedOutput(stage, identity, request.after_publish)
        finally:
            if not prepared:
                stage.unlink(missing_ok=True)

    def publish(self, prepared: PreparedOutput, *, notify: bool = True) -> None:
        self._replace(prepared.stage, prepared.identity.path)
        if notify:
            prepared.after_publish()


class DeferredOutputTransaction:
    __slots__ = ("_originals", "_outputs", "_sealed", "_transaction")

    def __init__(self) -> None:
        self._transaction = AtomicOutputTransaction()
        self._outputs: list[PreparedOutput] = []
        self._originals: dict[Path, OriginalDestination] = {}
        self._sealed = False

    def execute(self, request: OutputRequest) -> OutputIdentity:
        prepared = self._transaction.prepare(request)
        accepted = False
        try:
            destination = request.destination.resolve()
            original = self._originals.get(destination)
            if original is None:
                original = reserve_original(request.destination)
                self._originals[destination] = original
            identity = replace(prepared.identity, original=original)
            self._outputs.append(replace(prepared, identity=identity))
            accepted = True
            return identity
        finally:
            if not accepted:
                prepared.stage.unlink(missing_ok=True)

    def identities(self) -> tuple[OutputIdentity, ...]:
        if not self._sealed:
            self._refresh_originals()
            self._sealed = True
        return tuple(output.identity for output in self._outputs)

    def publish_all(self) -> PublicationResult:
        self.identities()
        outputs = tuple(self._outputs)
        originals = tuple(self._originals.values())
        identities = tuple(output.identity for output in outputs)
        try:
            backup_originals(originals)
            for output in outputs:
                self._transaction.publish(output, notify=False)
        except (OSError, KeyboardInterrupt) as publication_error:
            rollback_error = None
            try:
                restore_originals(originals)
            except RollbackError as error:
                rollback_error = error
            result: PublicationResult = PublicationFailed(
                publication_error,
                publication_outputs(identities),
                rollback_error,
            )
        else:
            try:
                remove_backups(originals)
                for output in outputs:
                    output.after_publish()
            except (OSError, KeyboardInterrupt) as publication_error:
                result = PublicationFailed(
                    publication_error,
                    publication_outputs(identities),
                    None,
                )
            else:
                result = PublicationSucceeded(publication_outputs(identities))
        try:
            self.discard()
        except (OSError, KeyboardInterrupt) as cleanup_error:
            if isinstance(result, PublicationFailed):
                return replace(
                    result,
                    cleanup_errors=(*result.cleanup_errors, cleanup_error),
                )
            return PublicationFailed(
                cleanup_error,
                publication_outputs(identities),
                None,
            )
        return result

    def discard(self) -> None:
        for output in self._outputs:
            output.stage.unlink(missing_ok=True)
        self._outputs.clear()
        self._originals.clear()
        self._sealed = False

    def _refresh_originals(self) -> None:
        for destination, original in tuple(self._originals.items()):
            if destination.exists() == original.existed:
                continue
            self._originals[destination] = reserve_original(destination)
        self._outputs = [
            replace(
                output,
                identity=replace(
                    output.identity,
                    original=self._originals[output.identity.path.resolve()],
                ),
            )
            for output in self._outputs
        ]
