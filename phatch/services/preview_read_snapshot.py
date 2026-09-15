from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from phatch.services.preview_types import (
    PreviewAdmissionError,
    PreviewErrorCode,
    SelectedPreviewRead,
)


@contextmanager
def snapshot_verified_file(path: Path, expected_sha256: str) -> Iterator[Path]:
    with TemporaryDirectory(prefix="phatch-preview-read-") as directory:
        snapshot = Path(directory) / path.name
        digest = sha256()
        try:
            with path.open("rb") as source, snapshot.open("xb") as target:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
                    target.write(chunk)
        except OSError as error:
            raise PreviewAdmissionError(
                PreviewErrorCode.SOURCE_CHANGED,
                "preview input changed before it could be read",
            ) from error
        if digest.hexdigest() != expected_sha256:
            raise PreviewAdmissionError(
                PreviewErrorCode.SOURCE_CHANGED,
                "preview input changed before it could be read",
            )
        yield snapshot


@contextmanager
def snapshot_selected_read(read: SelectedPreviewRead) -> Iterator[Path]:
    with snapshot_verified_file(read.path, read.sha256) as snapshot:
        yield snapshot
