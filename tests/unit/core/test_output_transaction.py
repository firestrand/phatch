from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
from PIL import Image

from phatch.lib import thumbnail
from phatch.services import image_output
from phatch.services.image_output import (
    ImageSaveRequest,
    LegacyImageEncoder,
    MetadataCopyRequest,
    RenderedImage,
    render_image,
    save_metadata_transactionally,
    save_transactionally,
)
from phatch.services.output_transaction import (
    AtomicOutputTransaction,
    MetadataUnavailableError,
    MetadataWriteError,
    NativeMetadataProvider,
    NoMetadataProvider,
    OutputRequest,
    PillowEncoder,
    PillowValidator,
)


class InjectedFailure(OSError):
    pass


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("format_name", ["JPEG", "PNG", "GIF", "TIFF"])
def test_transaction_commits_valid_real_image_when_format_supported(
    tmp_path: Path, format_name: str
) -> None:
    destination = tmp_path / f"result.{format_name.lower()}"
    image = Image.new("RGBA", (7, 5), (20, 40, 60, 128))
    if format_name == "JPEG":
        image = image.convert("RGB")

    identity = AtomicOutputTransaction().execute(
        OutputRequest(
            destination,
            PillowEncoder(image, format_name),
            NoMetadataProvider(),
            PillowValidator(format_name),
        )
    )

    with Image.open(destination) as saved:
        saved.load()
        assert saved.size == (7, 5)
        assert saved.format == format_name
    assert identity.path == destination
    assert identity.sha256 == _digest(destination)
    assert not tuple(tmp_path.glob(".*.tmp"))


@pytest.mark.parametrize("boundary", ["encode", "metadata", "flush", "replace"])
def test_transaction_preserves_old_destination_and_cleans_stage_on_failure(
    tmp_path: Path, boundary: str
) -> None:
    destination = tmp_path / "result.png"
    Image.new("RGB", (3, 3), "red").save(destination)
    old_digest = _digest(destination)
    image = Image.new("RGB", (4, 4), "blue")

    def fail(*args: object) -> None:
        raise InjectedFailure(boundary)

    metadata = NoMetadataProvider()

    def fsync(descriptor: int) -> None:
        if boundary == "flush":
            fail()
        os.fsync(descriptor)

    def replace(source: Path, destination: Path) -> None:
        if boundary == "replace":
            fail()
        os.replace(source, destination)

    encoder = PillowEncoder(image, "PNG")
    if boundary == "encode":
        encoder = fail
    elif boundary == "metadata":
        metadata = fail

    transaction = AtomicOutputTransaction(fsync=fsync, replace=replace)
    with pytest.raises(InjectedFailure):
        transaction.execute(
            OutputRequest(
                destination,
                encoder,
                metadata,
                PillowValidator("PNG"),
            )
        )

    assert _digest(destination) == old_digest
    assert not tuple(tmp_path.glob(".*.tmp"))


def test_locked_destination_preserves_old_output_and_cleans_stage(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "result.png"
    destination.write_bytes(b"old destination")

    def locked_replace(source: Path, destination: Path) -> None:
        raise PermissionError(13, "destination is locked", destination)

    with pytest.raises(PermissionError):
        AtomicOutputTransaction(replace=locked_replace).execute(
            OutputRequest(
                destination,
                PillowEncoder(Image.new("RGB", (2, 2), "blue"), "PNG"),
                NoMetadataProvider(),
                PillowValidator("PNG"),
            )
        )

    assert destination.read_bytes() == b"old destination"
    assert not tuple(tmp_path.glob(".*.tmp"))


def test_transaction_rejects_corrupt_encoded_bytes_before_replace(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "result.png"
    destination.write_bytes(b"old destination")

    def corrupt(path: Path) -> None:
        path.write_bytes(b"not an image")

    with pytest.raises(OSError):
        AtomicOutputTransaction().execute(
            OutputRequest(
                destination,
                corrupt,
                NoMetadataProvider(),
                PillowValidator("PNG"),
            )
        )

    assert destination.read_bytes() == b"old destination"


def test_native_metadata_provider_exposes_unavailable_support_as_typed_error(
    tmp_path: Path,
) -> None:
    def unavailable(path: Path) -> None:
        raise ImportError("native metadata missing")

    provider = NativeMetadataProvider(unavailable)

    with pytest.raises(MetadataUnavailableError):
        provider.write(tmp_path / "image.jpg")

    assert str(MetadataUnavailableError("missing")) == "missing"


def test_validator_rejects_unexpected_encoded_format(tmp_path: Path) -> None:
    path = tmp_path / "image.bin"
    Image.new("RGB", (2, 2)).save(path, format="PNG")

    with pytest.raises(OSError, match="does not match"):
        PillowValidator("JPEG")(path)


def test_no_metadata_write_is_explicit_noop(tmp_path: Path) -> None:
    NoMetadataProvider().write(tmp_path / "unused")


def test_transaction_applies_requested_timestamp_before_publication(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "result.png"
    timestamp_ns = 1_600_000_000_123_456_789

    AtomicOutputTransaction().execute(
        OutputRequest(
            destination,
            PillowEncoder(Image.new("RGB", (2, 2)), "PNG"),
            NoMetadataProvider(),
            PillowValidator("PNG"),
            modified_time_ns=timestamp_ns,
        )
    )

    assert destination.stat().st_mtime_ns == timestamp_ns


def test_metadata_copy_transaction_preserves_destination_on_metadata_failure(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    destination = tmp_path / "destination.jpg"
    Image.new("RGB", (2, 2), "blue").save(source)
    Image.new("RGB", (2, 2), "red").save(destination)
    old_digest = _digest(destination)

    def fail_metadata(path: Path) -> None:
        raise OSError("metadata failure")

    def copy_source(staged: Path) -> None:
        staged.write_bytes(source.read_bytes())

    with pytest.raises(MetadataWriteError):
        save_metadata_transactionally(
            MetadataCopyRequest(
                source,
                destination,
                "JPEG",
                copy_source,
                fail_metadata,
            )
        )

    assert _digest(destination) == old_digest


def test_transaction_cleans_stage_when_cancelled_between_boundaries(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "result.png"
    destination.write_bytes(b"old")

    def cancel(path: Path) -> None:
        path.write_bytes(b"partial")
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        AtomicOutputTransaction().execute(
            OutputRequest(
                destination,
                cancel,
                NoMetadataProvider(),
                PillowValidator("PNG"),
            )
        )

    assert destination.read_bytes() == b"old"
    assert not tuple(tmp_path.glob(".*.tmp"))


def test_render_image_preserves_thumbnail_and_reverses_orientation(monkeypatch) -> None:
    image = Image.new("RGB", (4, 3))
    thumb = Image.new("RGB", (1, 1))
    transposed = Image.new("RGB", (3, 4))
    monkeypatch.setattr(thumbnail, "thumbnail", lambda *args: thumb)
    monkeypatch.setattr(image_output.imtools, "get_format_data", lambda *args: b"data")
    monkeypatch.setattr(image_output.imtools, "transpose", lambda *args: transposed)

    rendered = render_image(image, "JPEG", (1,), True)

    assert rendered.image is transposed
    assert rendered.thumbnail_data == b"data"


def test_libtiff_encoder_uses_native_writer(monkeypatch, tmp_path: Path) -> None:
    image = Image.new("RGB", (2, 2))
    target = tmp_path / "target.tiff"
    writer_calls: list[str] = []
    monkeypatch.setattr(image_output.openImage, "check_libtiff", lambda value: None)
    monkeypatch.setattr(
        image_output.openImage,
        "save_libtiff",
        lambda image, path, **options: writer_calls.append(path),
    )

    LegacyImageEncoder(image, "TIFF", {}, "lzw", lambda *args: None)(target)

    assert writer_calls == [str(target)]


def test_libtiff_encoder_rejects_missing_writer(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(image_output.openImage, "check_libtiff", lambda value: None)
    monkeypatch.setattr(image_output.openImage, "save_libtiff", None)
    encoder = LegacyImageEncoder(
        Image.new("RGB", (2, 2)), "TIFF", {}, "lzw", lambda *args: None
    )

    with pytest.raises(OSError, match="unavailable"):
        encoder(tmp_path / "target.tiff")


@pytest.mark.parametrize("file_mode", [None, "RGB"])
def test_pillow_encoder_handles_unchanged_or_unreported_mode(
    monkeypatch, tmp_path: Path, file_mode: str | None
) -> None:
    logs: list[tuple[str, str]] = []
    monkeypatch.setattr(
        image_output.imtools, "save_check_mode", lambda *args, **kwargs: file_mode
    )
    encoder = LegacyImageEncoder(
        Image.new("RGB", (2, 2)), "PNG", {}, "none", lambda *args: logs.append(args)
    )

    encoder(tmp_path / "target.png")

    assert logs == ([] if file_mode is None else [("RGB", "RGB")])


def test_pillow_encoder_retries_alpha_loss_as_rgba(monkeypatch, tmp_path: Path) -> None:
    modes = iter(("L", None))
    logs: list[tuple[str, str]] = []
    monkeypatch.setattr(
        image_output.imtools,
        "save_check_mode",
        lambda *args, **kwargs: next(modes),
    )
    encoder = LegacyImageEncoder(
        Image.new("LA", (2, 2)), "TIFF", {}, "none", lambda *args: logs.append(args)
    )

    encoder(tmp_path / "target.tiff")

    assert logs == [("LA", "RGBA")]


class MetadataSourceFake:
    def __init__(self) -> None:
        self.paths: list[str] = []

    def save(self, target, target_format=None, thumbdata=None):
        self.paths.append(target)
        return None


def test_image_save_transaction_writes_metadata_before_publication(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "result.png"
    metadata = MetadataSourceFake()

    save_transactionally(
        ImageSaveRequest(
            destination,
            RenderedImage(Image.new("RGB", (2, 2)), b"thumbnail"),
            "PNG",
            {},
            "none",
            metadata,
            None,
            lambda *args: None,
        )
    )

    assert destination.exists()
    assert len(metadata.paths) == 1
    assert metadata.paths[0] != str(destination)
