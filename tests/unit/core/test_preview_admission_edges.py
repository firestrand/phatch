from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from phatch.core.user_paths import HostPlatform
from phatch.resources.provider import ResourceProvider
from phatch.services.action_schema_types import ActionDocument, ActionSpec
from phatch.services.preview import admit_preview
from phatch.services.preview_types import (
    PreviewAdmissionError,
    PreviewDependencies,
    PreviewErrorCode,
    PreviewRequest,
)


class EdgeCatalog:
    def __init__(
        self,
        missing_action: bool = False,
        missing_field: bool = False,
        invalid_fields: tuple[str, ...] = (),
    ) -> None:
        self.missing_action = missing_action
        self.missing_field = missing_field
        self.invalid = invalid_fields

    def action_label(self, action_id: str) -> str | None:
        return None if self.missing_action else action_id

    def field_label(self, action_id: str, field_id: str) -> str | None:
        return None if self.missing_field else field_id

    def invalid_fields(self, spec: ActionSpec) -> tuple[str, ...]:
        return self.invalid


def _source(root: Path) -> Path:
    path = root / "source.png"
    with Image.new("RGB", (7, 5), "blue") as image:
        image.save(path)
    return path


def _dependencies(root: Path, catalog: EdgeCatalog) -> PreviewDependencies:
    resources = root / "resources"
    resources.mkdir(exist_ok=True)
    return PreviewDependencies(
        lambda: catalog,
        ResourceProvider.from_root(resources),
        HostPlatform.MACOS,
    )


def _request(
    source: Path,
    actions: tuple[tuple[str, tuple[tuple[str, str], ...]], ...],
    selected: tuple[Path, ...] = (),
) -> PreviewRequest:
    return PreviewRequest(ActionDocument.from_values("", actions), source, selected)


def test_multiple_enabled_saves_are_rejected(tmp_path: Path) -> None:
    # Given
    request = _request(_source(tmp_path), (("save", ()), ("save", ())))

    # When / Then
    with pytest.raises(PreviewAdmissionError) as captured:
        admit_preview(request, _dependencies(tmp_path, EdgeCatalog()))
    assert captured.value.code is PreviewErrorCode.INVALID_SEQUENCE


@pytest.mark.parametrize(
    ("catalog", "code"),
    [
        (EdgeCatalog(missing_action=True), PreviewErrorCode.UNKNOWN_ACTION),
        (EdgeCatalog(missing_field=True), PreviewErrorCode.INVALID_FIELD),
        (EdgeCatalog(invalid_fields=("amount",)), PreviewErrorCode.INVALID_FIELD),
    ],
)
def test_catalog_rejections_are_typed(
    tmp_path: Path, catalog: EdgeCatalog, code: PreviewErrorCode
) -> None:
    # Given
    request = _request(_source(tmp_path), (("contrast", (("amount", "1.2"),)),))

    # When / Then
    with pytest.raises(PreviewAdmissionError) as captured:
        admit_preview(request, _dependencies(tmp_path, catalog))
    assert captured.value.code is code


def test_required_read_field_must_exist(tmp_path: Path) -> None:
    # Given
    request = _request(_source(tmp_path), (("mask", ()),))

    # When / Then
    with pytest.raises(PreviewAdmissionError) as captured:
        admit_preview(request, _dependencies(tmp_path, EdgeCatalog()))
    assert captured.value.code is PreviewErrorCode.INVALID_FIELD


def test_declared_read_must_be_a_file(tmp_path: Path) -> None:
    # Given
    directory = tmp_path / "selected"
    directory.mkdir()
    request = _request(
        _source(tmp_path),
        (("mask", (("mask", str(directory)),)),),
        (directory,),
    )

    # When / Then
    with pytest.raises(PreviewAdmissionError) as captured:
        admit_preview(request, _dependencies(tmp_path, EdgeCatalog()))
    assert captured.value.code is PreviewErrorCode.READ_NOT_FOUND


def test_declared_missing_read_is_rejected(tmp_path: Path) -> None:
    # Given
    missing = tmp_path / "missing.png"
    request = _request(_source(tmp_path), (("contrast", ()),), (missing,))

    # When / Then
    with pytest.raises(PreviewAdmissionError) as captured:
        admit_preview(request, _dependencies(tmp_path, EdgeCatalog()))
    assert captured.value.code is PreviewErrorCode.READ_NOT_FOUND


def test_metadata_expression_is_preserved_as_required_source_info(
    tmp_path: Path,
) -> None:
    # Given
    request = _request(
        _source(tmp_path),
        (("contrast", (("amount", "<Exif_Image_DateTime.year>"),)),),
    )

    # When
    admitted = admit_preview(request, _dependencies(tmp_path, EdgeCatalog()))

    # Then
    assert "Exif_Image_DateTime" in admitted.required_variables


def test_read_context_denies_every_mutating_capability(tmp_path: Path) -> None:
    # Given
    admitted = admit_preview(
        _request(_source(tmp_path), (("contrast", ()),)),
        _dependencies(tmp_path, EdgeCatalog()),
    )

    # When / Then
    for operation in (
        lambda: admitted.context.open_output(tmp_path / "output.png"),
        lambda: admitted.context.persist_metadata(tmp_path / "source.png"),
        lambda: admitted.context.run_process("tool"),
    ):
        with pytest.raises(PreviewAdmissionError) as captured:
            operation()
        assert captured.value.code is PreviewErrorCode.CONTEXT_DENIED
