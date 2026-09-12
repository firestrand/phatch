from __future__ import annotations

import os
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

Replace = Callable[[Path, Path], None]


def ensure_directory(path: os.PathLike[str] | str) -> Path:
    directory = Path(os.fspath(path))
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def atomic_write_bytes(
    destination: os.PathLike[str] | str,
    data: bytes,
    replace: Replace = os.replace,
) -> None:
    target = Path(os.fspath(destination))
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written == 0:
                raise OSError("temporary write made no progress")
            view = view[written:]
        os.fsync(descriptor)
        descriptor_to_close = descriptor
        descriptor = -1
        os.close(descriptor_to_close)
        replace(temporary, target)
    finally:
        active_error = sys.exception()
        close_error: BaseException | None = None
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except BaseException as error:
                close_error = error
        unlink_error: BaseException | None = None
        try:
            temporary.unlink(missing_ok=True)
        except BaseException as error:
            unlink_error = error
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                unlink_error = None
            except BaseException as error:
                unlink_error = error
            else:
                unlink_error = None
        cleanup_error = close_error or unlink_error
        if active_error is None and cleanup_error is not None:
            raise cleanup_error
