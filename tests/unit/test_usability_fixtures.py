from __future__ import annotations

import os
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from PIL import Image, UnidentifiedImageError

from tests.usability_fixtures import (
    FixtureMismatch,
    FixtureVerified,
    build_output_layout,
    build_pixel_boundary_fixtures,
    build_small_fixtures,
    child_process_probe,
    pid_exists,
    seed_sensitive_values,
    verify_fixture,
)

_FIXTURE_HASHES = (
    "59eb093a0909bb0e649564a0eb69950a7b05131876d890cfe4ec83112222978f",
    "0fe5711b92aef9d6e8de2afeb834351c1bee9e72b3411f244a583722306ebb98",
    "a60c16c4a1fefefbd8372e0ed7637ca6a213d2f25084f7e3a429fbfaad5c768c",
    "7bef35b4a16d471bd8b55dec08dcf9a67a7a5ea275dd9a4353615e41c3c216e4",
)


def test_small_images_are_deterministic_between_generated_roots(tmp_path: Path) -> None:
    # Given
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"

    # When
    first = build_small_fixtures(first_root)
    second = build_small_fixtures(second_root)

    # Then
    assert tuple(item.sha256 for item in first) == _FIXTURE_HASHES
    assert tuple(item.sha256 for item in second) == _FIXTURE_HASHES
    assert tuple(item.name for item in first) == (
        "rgb",
        "rgba",
        "oriented",
        "corrupt",
    )


def test_small_images_have_expected_modes_dimensions_and_orientation(
    tmp_path: Path,
) -> None:
    # Given
    fixtures = {item.name: item for item in build_small_fixtures(tmp_path)}

    # When
    with Image.open(fixtures["rgb"].path) as rgb_image:
        rgb_properties = (rgb_image.mode, rgb_image.size)
    with Image.open(fixtures["rgba"].path) as rgba_image:
        rgba_properties = (rgba_image.mode, rgba_image.size)
    with Image.open(fixtures["oriented"].path) as oriented_image:
        oriented_properties = (
            oriented_image.mode,
            oriented_image.size,
            oriented_image.getexif()[274],
        )

    # Then
    assert rgb_properties == ("RGB", (3, 2))
    assert rgba_properties == ("RGBA", (2, 2))
    assert oriented_properties == ("RGB", (3, 2), 6)


def test_corrupt_fixture_is_rejected_by_pillow(tmp_path: Path) -> None:
    # Given
    corrupt = build_small_fixtures(tmp_path)[3]

    # When / Then
    with pytest.raises(UnidentifiedImageError):
        Image.open(corrupt.path)
    assert isinstance(verify_fixture(corrupt), FixtureVerified)


def test_pixel_boundary_images_have_exact_dimensions_and_are_temporary() -> None:
    # Given
    with TemporaryDirectory() as directory:
        root = Path(directory) / "generated"

        # When
        exact, over = build_pixel_boundary_fixtures(root)
        with Image.open(exact.path) as exact_image:
            exact_properties = (exact_image.mode, exact_image.size)
        with Image.open(over.path) as over_image:
            over_properties = (over_image.mode, over_image.size)

        # Then
        assert exact_properties == ("RGB", (4000, 2000))
        assert over_properties == ("RGB", (4001, 2000))
        assert exact.size == (4000, 2000)
        assert over.size == (4001, 2000)
        assert exact_properties[1][0] * exact_properties[1][1] == 8_000_000
        assert over_properties[1][0] * over_properties[1][1] == 8_002_000
        assert exact.path.parent == root
        assert over.path.parent == root
    assert not root.exists()


def test_sensitive_values_cover_known_roots_credentials_and_free_text(
    tmp_path: Path,
) -> None:
    # Given / When
    sensitive = seed_sensitive_values(tmp_path)

    # Then
    assert sensitive.roots == (
        tmp_path / "home-private",
        tmp_path / "input-private",
        tmp_path / "output-private",
        tmp_path / "temp-private",
    )
    assert len(sensitive.credentials) == 3
    for value in (*map(str, sensitive.roots), *sensitive.credentials):
        assert value in sensitive.free_text


def test_output_layout_spans_multiple_destinations_and_rollback_paths(
    tmp_path: Path,
) -> None:
    # Given / When
    layout = build_output_layout(tmp_path)

    # Then
    assert len({path.parent for path in layout.outputs}) == 2
    assert len({path.parent for path in layout.staged_outputs}) == 2
    assert all(path.parent.is_dir() for path in layout.outputs)
    assert all(path.parent.is_dir() for path in layout.staged_outputs)
    assert not set(layout.outputs) & set(layout.staged_outputs)


def test_verifier_returns_typed_sha_mismatch_when_seeded_byte_changes(
    tmp_path: Path,
) -> None:
    # Given
    fixture = build_small_fixtures(tmp_path)[0]
    fixture.path.write_bytes(fixture.path.read_bytes() + b"altered")

    # When
    result = verify_fixture(fixture)

    # Then
    assert isinstance(result, FixtureMismatch)
    assert result.field == "sha256"
    assert result.expected == fixture.sha256
    assert result.actual == sha256(fixture.path.read_bytes()).hexdigest()


def test_verifier_returns_typed_dimension_mismatch(tmp_path: Path) -> None:
    # Given
    fixture = build_small_fixtures(tmp_path)[0]
    with Image.new("RGB", (4, 2), "black") as image:
        image.save(fixture.path)
    changed = replace(
        fixture,
        sha256=sha256(fixture.path.read_bytes()).hexdigest(),
    )

    # When
    result = verify_fixture(changed)

    # Then
    assert isinstance(result, FixtureMismatch)
    assert result.field == "size"
    assert result.expected == "3x2"
    assert result.actual == "4x2"


@pytest.mark.parametrize(
    ("fixture_index", "replacement", "field"),
    [
        (0, {"mode": "RGBA"}, "mode"),
        (2, {"orientation": 3}, "orientation"),
        (0, {"size": None}, "corruption"),
    ],
)
def test_verifier_identifies_non_hash_contract_mismatches(
    tmp_path: Path,
    fixture_index: int,
    replacement: dict[str, str | int | None],
    field: str,
) -> None:
    # Given
    fixture = build_small_fixtures(tmp_path)[fixture_index]
    changed = replace(fixture, **replacement)

    # When
    result = verify_fixture(changed)

    # Then
    assert isinstance(result, FixtureMismatch)
    assert result.field == field


def test_child_process_probe_detects_and_reaps_real_child() -> None:
    # Given / When
    child_pid = 0
    try:
        with child_process_probe() as child:
            child_pid = child.pid

            # Then
            assert child_pid != os.getpid()
            assert pid_exists(child_pid)
    finally:
        assert not pid_exists(child_pid)
    assert not pid_exists(0)
