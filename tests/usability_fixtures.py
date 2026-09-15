from __future__ import annotations

import shutil
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Final, TypeAlias

from PIL import Image, UnidentifiedImageError

from tests.fixtures.usability.process import ChildProcessProbe as ChildProcessProbe
from tests.fixtures.usability.process import ProcessCleanup as ProcessCleanup
from tests.fixtures.usability.process import (
    TerminationBehavior as TerminationBehavior,
)
from tests.fixtures.usability.process import child_process_probe as child_process_probe
from tests.fixtures.usability.process import (
    cleanup_child_process as cleanup_child_process,
)
from tests.fixtures.usability.process import pid_exists as pid_exists
from tests.fixtures.usability.process import spawn_child_process as spawn_child_process

_ORIENTATION_TAG: Final = 274
_ASSET_ROOT: Final = Path(__file__).parent / "fixtures" / "usability"


@dataclass(frozen=True, slots=True)
class ImageFixture:
    name: str
    path: Path
    size: tuple[int, int] | None
    mode: str | None
    orientation: int | None
    sha256: str


@dataclass(frozen=True, slots=True)
class _FixtureSource:
    name: str
    filename: str
    size: tuple[int, int] | None
    mode: str | None
    orientation: int | None
    sha256: str


_FIXTURE_SOURCES: Final = (
    _FixtureSource(
        "rgb",
        "rgb.png",
        (3, 2),
        "RGB",
        None,
        "59eb093a0909bb0e649564a0eb69950a7b05131876d890cfe4ec83112222978f",
    ),
    _FixtureSource(
        "rgba",
        "rgba.png",
        (2, 2),
        "RGBA",
        None,
        "0fe5711b92aef9d6e8de2afeb834351c1bee9e72b3411f244a583722306ebb98",
    ),
    _FixtureSource(
        "oriented",
        "oriented.png",
        (3, 2),
        "RGB",
        6,
        "a60c16c4a1fefefbd8372e0ed7637ca6a213d2f25084f7e3a429fbfaad5c768c",
    ),
    _FixtureSource(
        "corrupt",
        "corrupt.img",
        None,
        None,
        None,
        "7bef35b4a16d471bd8b55dec08dcf9a67a7a5ea275dd9a4353615e41c3c216e4",
    ),
)


@dataclass(frozen=True, slots=True)
class FixtureVerified:
    fixture: ImageFixture


@dataclass(frozen=True, slots=True)
class FixtureMismatch:
    fixture: ImageFixture
    field: str
    expected: str
    actual: str


FixtureVerification: TypeAlias = FixtureVerified | FixtureMismatch


@dataclass(frozen=True, slots=True)
class SensitiveValues:
    roots: tuple[Path, Path, Path, Path]
    credentials: tuple[str, str, str]
    free_text: str


@dataclass(frozen=True, slots=True)
class OutputLayout:
    source: Path
    outputs: tuple[Path, Path]
    preexisting_outputs: tuple[Path, Path]
    staged_outputs: tuple[Path, Path]
    backup_outputs: tuple[Path, Path]
    rollback_survivors: tuple[Path, Path]
    rollback_removed: tuple[Path, Path, Path, Path]


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def build_small_fixtures(root: Path) -> tuple[ImageFixture, ...]:
    root.mkdir(parents=True, exist_ok=True)
    fixtures: list[ImageFixture] = []
    for source in _FIXTURE_SOURCES:
        path = root / source.filename
        shutil.copyfile(_ASSET_ROOT / source.filename, path)
        fixtures.append(
            ImageFixture(
                source.name,
                path,
                source.size,
                source.mode,
                source.orientation,
                source.sha256,
            )
        )
    return tuple(fixtures)


def build_pixel_boundary_fixtures(
    root: Path,
) -> tuple[ImageFixture, ImageFixture]:
    root.mkdir(parents=True, exist_ok=True)
    fixtures: list[ImageFixture] = []
    for name, size in (
        ("exact-8000000", (4000, 2000)),
        ("over-8002000", (4001, 2000)),
    ):
        path = root / f"{name}.png"
        with Image.new("RGB", size, (17, 31, 47)) as image:
            image.save(path, format="PNG")
        fixtures.append(ImageFixture(name, path, size, "RGB", None, file_sha256(path)))
    return fixtures[0], fixtures[1]


def seed_sensitive_values(root: Path) -> SensitiveValues:
    roots = (
        root / "home-private",
        root / "input-private",
        root / "output-private",
        root / "temp-private",
    )
    for path in roots:
        path.mkdir(parents=True, exist_ok=True)
    credentials = (
        "token=fixture-token-not-a-secret",
        "password=fixture-password-not-a-secret",
        "api_key=fixture-key-not-a-secret",
    )
    return SensitiveValues(
        roots,
        credentials,
        " | ".join((*map(str, roots), *credentials)),
    )


def build_output_layout(root: Path) -> OutputLayout:
    source_root = root / "source"
    output_roots = (root / "output-a", root / "output-b")
    rollback_roots = (root / "rollback-a", root / "rollback-b")
    for path in (source_root, *output_roots, *rollback_roots):
        path.mkdir(parents=True, exist_ok=True)
    source = source_root / "original.png"
    shutil.copyfile(_ASSET_ROOT / "rgb.png", source)
    outputs = (output_roots[0] / "result.png", output_roots[1] / "result.png")
    staged = (
        rollback_roots[0] / "result.staged",
        rollback_roots[1] / "result.staged",
    )
    backups = (
        rollback_roots[0] / "result.backup",
        rollback_roots[1] / "result.backup",
    )
    previous = (b"previous-output-a", b"previous-output-b")
    for path, contents in zip(outputs, previous, strict=True):
        path.write_bytes(contents)
    for path, contents in zip(staged, (b"new-output-a", b"new-output-b"), strict=True):
        path.write_bytes(contents)
    for path, contents in zip(backups, previous, strict=True):
        path.write_bytes(contents)
    return OutputLayout(
        source,
        outputs,
        outputs,
        staged,
        backups,
        outputs,
        (*staged, *backups),
    )


def verify_fixture(fixture: ImageFixture) -> FixtureVerification:
    actual_hash = file_sha256(fixture.path)
    if actual_hash != fixture.sha256:
        return FixtureMismatch(fixture, "sha256", fixture.sha256, actual_hash)
    if fixture.size is None:
        try:
            with Image.open(fixture.path):
                return FixtureMismatch(fixture, "corruption", "unreadable", "readable")
        except (UnidentifiedImageError, OSError):
            return FixtureVerified(fixture)
    with Image.open(fixture.path) as image:
        if image.size != fixture.size:
            expected = f"{fixture.size[0]}x{fixture.size[1]}"
            actual = f"{image.size[0]}x{image.size[1]}"
            return FixtureMismatch(fixture, "size", expected, actual)
        if image.mode != fixture.mode:
            return FixtureMismatch(fixture, "mode", str(fixture.mode), image.mode)
        orientation = image.getexif().get(_ORIENTATION_TAG)
        if orientation != fixture.orientation:
            return FixtureMismatch(
                fixture,
                "orientation",
                str(fixture.orientation),
                str(orientation),
            )
    return FixtureVerified(fixture)
