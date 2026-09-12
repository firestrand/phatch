from pathlib import Path

from PIL import Image

from phatch.services.action_schema import ActionDocument
from phatch.services.parallel_save import build_image_jobs
from phatch.services.parallel_save_spec import (
    ParallelSaveSettings,
    ParallelSaveUnsupported,
    SaveJobSpec,
    select_parallel_save,
)
from phatch.services.preflight import PreflightResult


def _preflight(source: Path, destination: Path) -> PreflightResult:
    return PreflightResult((source,), (destination,), (), (), (), (), 1)


def _settings(
    *,
    max_workers: int = 2,
    overwrite_existing: bool = True,
    resume: bool = False,
) -> ParallelSaveSettings:
    return ParallelSaveSettings(
        max_workers=max_workers,
        overwrite_existing=overwrite_existing,
        resume=resume,
        no_save=False,
        repeat=1,
    )


def _document(*fields: tuple[str, str]) -> ActionDocument:
    return ActionDocument.from_values("", (("save", fields),))


def test_default_save_fields_use_legacy_serial_path(tmp_path: Path) -> None:
    # Given
    source = tmp_path / "source.png"
    Image.new("RGB", (4, 3)).save(source)

    # When
    selection = select_parallel_save(
        _document(), _preflight(source, tmp_path / "output.png"), _settings()
    )

    # Then
    assert isinstance(selection, ParallelSaveUnsupported)
    assert "Metadata" in selection.reason


def test_one_worker_creates_typed_worker_spec(tmp_path: Path) -> None:
    # Given
    source = tmp_path / "source.png"
    Image.new("RGB", (4, 3)).save(source)

    # When
    selection = select_parallel_save(
        _document(("metadata", "no"), ("resolution", "72")),
        _preflight(source, tmp_path / "output.png"),
        _settings(max_workers=1),
    )

    # Then
    assert isinstance(selection, SaveJobSpec)


def test_no_save_uses_legacy_serial_path(tmp_path: Path) -> None:
    # Given
    source = tmp_path / "source.png"
    Image.new("RGB", (4, 3)).save(source)
    settings = ParallelSaveSettings(
        max_workers=2,
        overwrite_existing=True,
        resume=False,
        no_save=True,
        repeat=1,
    )

    # When
    selection = select_parallel_save(
        _document(("metadata", "no"), ("resolution", "72")),
        _preflight(source, tmp_path / "output.png"),
        settings,
    )

    # Then
    assert isinstance(selection, ParallelSaveUnsupported)
    assert "--no-save" in selection.reason


def test_keep_and_resume_each_use_legacy_serial_path(tmp_path: Path) -> None:
    # Given
    source = tmp_path / "source.png"
    Image.new("RGB", (4, 3)).save(source)
    document = _document(("metadata", "no"), ("resolution", "72"))
    preflight = _preflight(source, tmp_path / "output.png")

    # When
    keep = select_parallel_save(
        document, preflight, _settings(overwrite_existing=False)
    )
    resume = select_parallel_save(document, preflight, _settings(resume=True))

    # Then
    assert isinstance(keep, ParallelSaveUnsupported)
    assert isinstance(resume, ParallelSaveUnsupported)
    assert "--keep" in keep.reason
    assert "--resume" in resume.reason


def test_jpeg_target_size_uses_legacy_serial_path(tmp_path: Path) -> None:
    # Given
    source = tmp_path / "source.png"
    Image.new("RGB", (4, 3)).save(source)

    # When
    selection = select_parallel_save(
        _document(
            ("metadata", "no"),
            ("resolution", "72"),
            ("jpeg_size_maximum", "100 kb"),
        ),
        _preflight(source, tmp_path / "output.jpg"),
        _settings(),
    )

    # Then
    assert isinstance(selection, ParallelSaveUnsupported)
    assert "JPEG Size Maximum" in selection.reason


def test_explicit_supported_fields_create_typed_worker_spec(tmp_path: Path) -> None:
    # Given
    source = tmp_path / "animated.gif"
    first = Image.new("RGB", (5, 4), "red")
    second = Image.new("RGB", (5, 4), "blue")
    first.save(source, save_all=True, append_images=[second], duration=[30, 40])
    preflight = _preflight(source, tmp_path / "output.gif")

    # When
    selection = select_parallel_save(
        _document(
            ("metadata", "no"),
            ("resolution", "144"),
            ("jpeg_quality", "91"),
            ("png_optimize", "yes"),
            ("jpeg_size_maximum", "0 kb"),
        ),
        preflight,
        _settings(),
    )

    # Then
    assert isinstance(selection, SaveJobSpec)
    assert selection.resolution == 144
    assert selection.preserve_metadata is False
    jobs = build_image_jobs(selection, preflight)
    assert jobs[0].frame_count == 2
    assert jobs[0].retains_animation is True


def test_dynamic_resolution_uses_legacy_serial_path(tmp_path: Path) -> None:
    # Given
    source = tmp_path / "source.png"
    Image.new("RGB", (4, 3)).save(source, dpi=(96, 96))

    # When
    selection = select_parallel_save(
        _document(("metadata", "no"), ("resolution", "<dpi>")),
        _preflight(source, tmp_path / "output.png"),
        _settings(),
    )

    # Then
    assert isinstance(selection, ParallelSaveUnsupported)
    assert "dpi" in selection.reason
