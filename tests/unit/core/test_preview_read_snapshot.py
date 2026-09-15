from hashlib import sha256
from pathlib import Path

import pytest
from PIL import Image

from phatch.lib import metadata
from phatch.services.preview_inspection import inspect_preview_source
from phatch.services.preview_read_snapshot import (
    snapshot_selected_read,
    snapshot_verified_file,
)
from phatch.services.preview_types import (
    PreviewAdmissionError,
    PreviewErrorCode,
    SelectedPreviewRead,
)


def test_snapshot_binds_verified_bytes_to_private_copy(tmp_path: Path) -> None:
    selected = tmp_path / "mark.png"
    selected.write_bytes(b"approved")
    read = SelectedPreviewRead(
        0,
        "mark",
        selected,
        sha256(selected.read_bytes()).hexdigest(),
    )

    with snapshot_selected_read(read) as snapshot:
        assert snapshot != selected
        assert snapshot.read_bytes() == b"approved"

    assert not snapshot.exists()


def test_snapshot_rejects_missing_authorized_read(tmp_path: Path) -> None:
    read = SelectedPreviewRead(0, "mark", tmp_path / "missing.png", "unused")

    with (
        pytest.raises(PreviewAdmissionError) as captured,
        snapshot_selected_read(read),
    ):
        pass

    assert captured.value.code is PreviewErrorCode.SOURCE_CHANGED
    assert str(tmp_path) not in str(captured.value)


def test_snapshot_rejects_changed_authorized_read(tmp_path: Path) -> None:
    selected = tmp_path / "mark.png"
    selected.write_bytes(b"changed")
    read = SelectedPreviewRead(0, "mark", selected, "stale")

    with (
        pytest.raises(PreviewAdmissionError) as captured,
        snapshot_selected_read(read),
    ):
        pass

    assert captured.value.code is PreviewErrorCode.SOURCE_CHANGED
    assert str(tmp_path) not in str(captured.value)


def test_verified_source_is_consumed_from_snapshot(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    source.write_bytes(b"source")
    expected = sha256(source.read_bytes()).hexdigest()

    with snapshot_verified_file(source, expected) as snapshot:
        source.write_bytes(b"replacement")
        assert snapshot.read_bytes() == b"source"

    assert not snapshot.exists()


def test_admitted_file_identity_and_snapshot_bytes_survive_source_mutation(
    tmp_path: Path,
) -> None:
    source = tmp_path / "admitted-original.png"
    with Image.new("RGB", (4, 3), "red") as image:
        image.save(source)
    expected_bytes = source.read_bytes()
    expected_info = metadata.InfoExtract(
        str(source.resolve()), vars=list(metadata.InfoFile.possible_vars)
    ).dump()
    admitted = inspect_preview_source(source)

    with snapshot_verified_file(source, admitted.sha256) as snapshot:
        with Image.new("RGB", (4, 3), "blue") as image:
            image.save(source)

        assert snapshot.read_bytes() == expected_bytes
        assert dict(admitted.logical_file_info) == expected_info
