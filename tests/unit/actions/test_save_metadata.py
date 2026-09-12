from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from phatch.actions import save_metadata
from phatch.services.image_output import MetadataCopyRequest


def test_action_declares_lossless_metadata_contract() -> None:
    action = save_metadata.Action()

    assert action.label == "Save Tags"
    assert {"file", "metadata"}.issubset(action.tags)
    assert action.is_overwrite_existing_images_forced() is True


def test_apply_builds_transaction_for_same_file(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "image.jpg"
    source.write_bytes(b"source")
    captured: list[MetadataCopyRequest] = []
    action = save_metadata.Action()
    monkeypatch.setattr(
        action, "get_lossless_filename", lambda photo, info: str(source)
    )
    monkeypatch.setattr(
        save_metadata,
        "save_metadata_transactionally",
        lambda request: captured.append(request),
    )
    photo = Mock(
        info={"path": str(source), "size": (1, 1)},
        modify_date=None,
        output_transaction=None,
    )

    result = action.apply(photo, Mock(), {})

    assert result is photo
    assert captured[0].source == source
    assert captured[0].destination == source
    assert captured[0].format_name == "JPEG"
    assert captured[0].modified_time_ns is None


def test_apply_builds_unicode_destination_and_utc_scale_timestamp(
    monkeypatch, tmp_path: Path
) -> None:
    source = tmp_path / "image.jpg"
    destination = tmp_path / "图片.jpg"
    source.write_bytes(b"source")
    captured: list[MetadataCopyRequest] = []
    action = save_metadata.Action()
    monkeypatch.setattr(
        action, "get_lossless_filename", lambda photo, info: str(destination)
    )
    monkeypatch.setattr(
        save_metadata,
        "save_metadata_transactionally",
        lambda request: captured.append(request),
    )
    photo = Mock(
        info={"path": str(source), "size": (1, 1)},
        modify_date=1_234_567_890,
        output_transaction=None,
    )

    action.apply(photo, Mock(), {})

    assert captured[0].destination == destination
    assert captured[0].modified_time_ns == 1_234_567_890_000_000_000


def test_apply_transaction_callbacks_use_staged_path(
    monkeypatch, tmp_path: Path
) -> None:
    source = tmp_path / "image.jpg"
    destination = tmp_path / "result.jpg"
    staged = tmp_path / ".result.jpg.stage"
    source.write_bytes(b"source")
    action = save_metadata.Action()
    files = Mock()
    metadata = Mock()
    action.plugin_context = Mock(files=files, metadata=metadata)
    monkeypatch.setattr(
        action, "get_lossless_filename", lambda photo, info: str(destination)
    )

    def exercise(request: MetadataCopyRequest) -> None:
        request.copy_source(staged)
        request.write_metadata(staged)

    monkeypatch.setattr(save_metadata, "save_metadata_transactionally", exercise)
    info: dict[str, str | tuple[int, int]] = {"path": str(source)}

    info["size"] = (1, 1)
    action.apply(
        Mock(info=info, modify_date=None, output_transaction=None), Mock(), {}
    )

    files.copy2.assert_called_once_with(str(source), str(staged))
    metadata.save.assert_called_once_with(info, str(staged))


def test_apply_uses_photo_output_transaction(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "image.jpg"
    destination = tmp_path / "result.jpg"
    source.write_bytes(b"source")
    action = save_metadata.Action()
    transaction = Mock()
    captured: list[tuple[MetadataCopyRequest, Mock]] = []
    monkeypatch.setattr(
        action, "get_lossless_filename", lambda photo, info: str(destination)
    )
    monkeypatch.setattr(
        save_metadata,
        "save_metadata_transactionally",
        lambda request, selected: captured.append((request, selected)),
    )
    photo = Mock(
        info={"path": str(source), "size": (1, 1)},
        modify_date=None,
        output_transaction=transaction,
    )

    action.apply(photo, Mock(), {})

    assert len(captured) == 1
    request, selected = captured[0]
    assert request.destination == destination
    assert selected is transaction
