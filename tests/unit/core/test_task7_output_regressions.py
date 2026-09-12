from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from phatch.actions import save_metadata
from phatch.core.plugin_context import DefaultMetadataOperations
from phatch.services.image_output import (
    ImageSaveRequest,
    RenderedImage,
    save_transactionally,
)
from phatch.services.output_transaction import MetadataWriteError


class DiagnosticMetadata:
    def save(
        self,
        target: str,
        target_format: str | None = None,
        thumbdata: bytes | str | None = None,
    ) -> str:
        return "METADATA_WRITE_FAILED"


class DiagnosticTarget:
    def save(self, filename: str) -> str:
        return "METADATA_WRITE_FAILED"


class DiagnosticInfo(dict[str, str | tuple[int, int]]):
    def save(self, filename: str) -> str:
        return "METADATA_WRITE_FAILED"


class SaveTagsPhoto:
    def __init__(self, info: DiagnosticInfo) -> None:
        self.info = info
        self.modify_date = None
        self.report_files: list[str] = []

    def append_to_report(self, filename: str) -> None:
        self.report_files.append(filename)


def test_save_rejects_nonempty_metadata_diagnostic_before_publication(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "result.png"
    destination.write_bytes(b"OLD_DESTINATION")
    request = ImageSaveRequest(
        destination,
        RenderedImage(Image.new("RGB", (3, 2), "blue"), None),
        "PNG",
        {},
        "none",
        DiagnosticMetadata(),
        None,
        lambda _source, _target: None,
    )

    with pytest.raises(MetadataWriteError, match="METADATA_WRITE_FAILED"):
        save_transactionally(request)

    assert destination.read_bytes() == b"OLD_DESTINATION"


def test_default_metadata_operations_preserve_native_diagnostic() -> None:
    target = DiagnosticTarget()

    result = DefaultMetadataOperations().save(target, "target.jpg")

    assert result == "METADATA_WRITE_FAILED"


def test_validator_rejects_truncated_jpeg_before_publication(tmp_path: Path) -> None:
    destination = tmp_path / "result.jpg"
    destination.write_bytes(b"OLD_DESTINATION")
    valid = tmp_path / "valid.jpg"
    Image.new("RGB", (11, 7), "blue").save(valid, format="JPEG")
    truncated = valid.read_bytes()[:-1]

    def encode(path: Path) -> None:
        path.write_bytes(truncated)

    from phatch.services.output_transaction import (
        AtomicOutputTransaction,
        NoMetadataProvider,
        OutputRequest,
        PillowValidator,
    )

    with pytest.raises(OSError):
        AtomicOutputTransaction().execute(
            OutputRequest(
                destination,
                encode,
                NoMetadataProvider(),
                PillowValidator("JPEG", (11, 7)),
            )
        )

    assert destination.read_bytes() == b"OLD_DESTINATION"


def test_save_tags_diagnostic_preserves_destination_and_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "source.jpg"
    destination = tmp_path / "result.jpg"
    Image.new("RGB", (3, 2), "blue").save(source, format="JPEG")
    Image.new("RGB", (3, 2), "red").save(destination, format="JPEG")
    old_bytes = destination.read_bytes()
    info = DiagnosticInfo(
        path=str(source), type="jpg", format="JPEG", size=(3, 2)
    )
    photo = SaveTagsPhoto(info)
    action = save_metadata.Action()
    monkeypatch.setattr(
        action,
        "get_field",
        lambda label, _info: destination.stem if label == "File Name" else tmp_path,
    )
    monkeypatch.setattr(
        action, "ensure_path_or_desktop", lambda _folder, _photo, filename: filename
    )

    with pytest.raises(MetadataWriteError, match="METADATA_WRITE_FAILED"):
        action.apply(photo, None, {})

    assert destination.read_bytes() == old_bytes
    assert photo.report_files == []
