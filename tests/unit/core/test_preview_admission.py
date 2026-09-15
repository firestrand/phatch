from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest
from PIL import Image

from phatch.core.user_paths import HostPlatform
from phatch.resources.provider import ResourceProvider
from phatch.services.action_schema_types import ActionDocument, ActionSpec
from phatch.services.preview import admit_preview, validate_preview_transition
from phatch.services.preview_types import (
    PackagedPreviewRead,
    PreviewAdmissionError,
    PreviewDependencies,
    PreviewErrorCode,
    PreviewRequest,
    PreviewSize,
    SelectedPreviewRead,
)


class FixtureCatalog:
    def __init__(self) -> None:
        self.accesses = 0

    def action_id(self, label: str) -> str | None:
        self.accesses += 1
        return None

    def action_label(self, action_id: str) -> str | None:
        self.accesses += 1
        return action_id

    def field_id(self, action_id: str, label: str) -> str | None:
        self.accesses += 1
        return None

    def field_label(self, action_id: str, field_id: str) -> str | None:
        self.accesses += 1
        return field_id

    def invalid_fields(self, spec: ActionSpec) -> tuple[str, ...]:
        self.accesses += 1
        return ()


def _image(path: Path, size: tuple[int, int]) -> Path:
    with Image.new("RGB", size, "red") as image:
        image.save(path)
    return path


def _request(
    source: Path, *actions: tuple[str, tuple[tuple[str, str], ...]]
) -> PreviewRequest:
    return PreviewRequest(ActionDocument.from_values("", actions), source)


def _dependencies(catalog: FixtureCatalog, resources: Path) -> PreviewDependencies:
    resources.mkdir(parents=True, exist_ok=True)
    return PreviewDependencies(
        catalog_factory=lambda: catalog,
        resources=ResourceProvider.from_root(resources),
        platform=HostPlatform.MACOS,
    )


def test_unknown_tail_rejects_before_catalog_access(tmp_path: Path) -> None:
    # Given
    source = _image(tmp_path / "source.png", (7, 5))
    catalog = FixtureCatalog()

    # When / Then
    with pytest.raises(PreviewAdmissionError) as captured:
        admit_preview(
            _request(source, ("contrast", ()), ("user_action", (("enabled", "no"),))),
            _dependencies(catalog, tmp_path),
        )
    assert captured.value.code is PreviewErrorCode.UNKNOWN_ACTION
    assert catalog.accesses == 0


def test_unsupported_tail_rejects_whole_list_before_catalog_access(
    tmp_path: Path,
) -> None:
    # Given
    source = _image(tmp_path / "source.png", (7, 5))
    catalog = FixtureCatalog()

    # When / Then
    with pytest.raises(PreviewAdmissionError) as captured:
        admit_preview(
            _request(source, ("contrast", ()), ("geek", ())),
            _dependencies(catalog, tmp_path),
        )
    assert captured.value.code is PreviewErrorCode.BLOCKED_ACTION
    assert catalog.accesses == 0


def test_terminal_save_is_omitted_and_must_be_last(tmp_path: Path) -> None:
    # Given
    source = _image(tmp_path / "source.png", (7, 5))
    catalog = FixtureCatalog()
    dependencies = _dependencies(catalog, tmp_path)

    # When
    admitted = admit_preview(
        _request(source, ("contrast", ()), ("save", ())), dependencies
    )

    # Then
    assert tuple(action.action_id for action in admitted.actions) == ("contrast",)
    assert admitted.omitted_terminal_save
    with pytest.raises(PreviewAdmissionError, match="final enabled action"):
        admit_preview(_request(source, ("save", ()), ("contrast", ())), dependencies)


def test_source_pixel_boundary_and_hash_are_preserved(tmp_path: Path) -> None:
    # Given
    exact = _image(tmp_path / "exact.png", (4000, 2000))
    over = _image(tmp_path / "over.png", (4001, 2000))
    catalog = FixtureCatalog()
    before = sha256(over.read_bytes()).hexdigest()

    # When
    admitted = admit_preview(
        _request(exact, ("contrast", ())), _dependencies(catalog, tmp_path)
    )

    # Then
    assert admitted.source.size == PreviewSize(4000, 2000)
    assert admitted.source.sha256 == sha256(exact.read_bytes()).hexdigest()
    with pytest.raises(PreviewAdmissionError) as captured:
        admit_preview(
            _request(over, ("contrast", ())), _dependencies(catalog, tmp_path)
        )
    assert captured.value.code is PreviewErrorCode.PIXEL_LIMIT
    assert sha256(over.read_bytes()).hexdigest() == before


def test_corrupt_source_is_rejected_without_catalog_access(tmp_path: Path) -> None:
    # Given
    source = tmp_path / "corrupt.png"
    source.write_bytes(b"not an image")
    catalog = FixtureCatalog()

    # When / Then
    with pytest.raises(PreviewAdmissionError) as captured:
        admit_preview(
            _request(source, ("contrast", ())), _dependencies(catalog, tmp_path)
        )
    assert captured.value.code is PreviewErrorCode.CORRUPT_SOURCE
    assert catalog.accesses == 0


def test_transition_budget_accepts_exact_pixels_and_rejects_overages() -> None:
    # Given
    exact = PreviewSize(4000, 2000)

    # When / Then
    assert validate_preview_transition(exact, exact) == 64_065_536
    with pytest.raises(PreviewAdmissionError) as pixels:
        validate_preview_transition(exact, PreviewSize(4001, 2000))
    assert pixels.value.code is PreviewErrorCode.PIXEL_LIMIT
    with pytest.raises(PreviewAdmissionError) as memory:
        validate_preview_transition(
            PreviewSize(8_000_000, 1), PreviewSize(8_000_000, 1), 64_000_000
        )
    assert memory.value.code is PreviewErrorCode.MEMORY_LIMIT


def test_packaged_and_declared_reads_are_prebound(tmp_path: Path) -> None:
    # Given
    source = _image(tmp_path / "source.png", (7, 5))
    resources = tmp_path / "resources"
    highlight = resources / "data" / "highlights" / "sphere_top.png"
    highlight.parent.mkdir(parents=True)
    highlight.write_bytes(b"packaged")
    selected = tmp_path / "selected.png"
    selected.write_bytes(b"selected")
    catalog = FixtureCatalog()

    # When
    packaged = admit_preview(
        _request(source, ("highlight", (("highlight", "Sphere Top"),))),
        _dependencies(catalog, resources),
    )
    explicit = admit_preview(
        PreviewRequest(
            ActionDocument.from_values("", (("mask", (("mask", str(selected)),)),)),
            source,
            (selected,),
        ),
        _dependencies(catalog, resources),
    )

    # Then
    assert isinstance(packaged.reads[0], PackagedPreviewRead)
    assert packaged.reads[0].resource.value == "data/highlights/sphere_top.png"
    assert isinstance(explicit.reads[0], SelectedPreviewRead)
    assert explicit.reads[0].path == selected.resolve()


def test_background_mark_is_only_bound_for_image_fill(tmp_path: Path) -> None:
    # Given
    source = _image(tmp_path / "source.png", (7, 5))
    catalog = FixtureCatalog()

    # When
    admitted = admit_preview(
        _request(
            source,
            ("background", (("fill", "Color"), ("mark", "Missing"))),
        ),
        _dependencies(catalog, tmp_path / "resources"),
    )

    # Then
    assert admitted.reads == ()


def test_missing_undeclared_and_unsafe_expression_reads_reject(tmp_path: Path) -> None:
    # Given
    source = _image(tmp_path / "source.png", (7, 5))
    selected = tmp_path / "selected.png"
    selected.write_bytes(b"selected")
    catalog = FixtureCatalog()
    dependencies = _dependencies(catalog, tmp_path / "resources")

    # When / Then
    for value in (
        str(selected),
        str(tmp_path / "missing.png"),
        "Missing Alias",
        "<__import__('os')>",
    ):
        with pytest.raises(PreviewAdmissionError) as captured:
            admit_preview(_request(source, ("mask", (("mask", value),))), dependencies)
        assert captured.value.code in {
            PreviewErrorCode.UNDECLARED_READ,
            PreviewErrorCode.UNSAFE_EXPRESSION,
        }
    assert catalog.accesses == 0
