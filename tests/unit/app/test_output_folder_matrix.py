from __future__ import annotations

from pathlib import Path

import pytest

from phatch.core.execution_types import (
    ExecutionOutcome,
    ExecutionResult,
    FileOutcome,
    FileResult,
    OutputRecord,
    ReportFile,
)
from phatch.lib import system
from phatch.pyWx.execution_results import output_folders


def _result(source: Path, *outputs: Path) -> ExecutionResult:
    return ExecutionResult(
        ExecutionOutcome.COMPLETED,
        (source,),
        (
            FileResult(
                source,
                FileOutcome.PROCESSED,
                outputs=tuple(
                    OutputRecord(ReportFile(source, output)) for output in outputs
                ),
            ),
        ),
    )


def test_output_folder_zero_one_and_sorted_many_matrix(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    alpha = tmp_path / "Alpha folder"
    middle = tmp_path / "middle"
    zulu = tmp_path / "zulu"
    for folder in (alpha, middle, zulu):
        folder.mkdir()

    assert output_folders(_result(source)) == ()
    assert output_folders(_result(source, middle / "one.png")) == (middle.resolve(),)
    assert output_folders(
        _result(
            source,
            zulu / "z.png",
            alpha / "a.png",
            middle / "m.png",
        )
    ) == (alpha.resolve(), middle.resolve(), zulu.resolve())


def test_output_folder_deduplicates_parent_symlink_and_case_variants(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.png"
    canonical = tmp_path / "Case Parent"
    case_variant = tmp_path / "case parent"
    alias = tmp_path / "alias"
    canonical.mkdir()
    alias.symlink_to(canonical, target_is_directory=True)

    folders = output_folders(
        _result(
            source,
            canonical / "first.png",
            canonical / "duplicate.png",
            alias / "symlink.png",
            case_variant / "variant.png",
        )
    )

    assert folders == (canonical.resolve(),)


@pytest.mark.parametrize("platform", ["darwin", "win32", "linux"])
def test_open_directory_keeps_spaces_and_metacharacters_in_one_argv_without_shell(
    tmp_path: Path,
    platform: str,
) -> None:
    folder = tmp_path / "output folder; $(touch nope) [x] 'quoted'"
    folder.mkdir()

    command = system.open_directory_command(folder, platform)

    assert len(command.argv) == 2
    assert command.argv[1] == str(folder.resolve())
    assert not hasattr(command, "shell")


def test_open_directory_public_route_passes_command_object_to_runner(
    tmp_path: Path,
) -> None:
    folder = tmp_path / "owned output"
    folder.mkdir()

    class Runner:
        def __init__(self) -> None:
            self.commands = []

        def run(self, command):
            self.commands.append(command)

    runner = Runner()

    system.open_directory(folder, runner)

    assert runner.commands[0].argv[1] == str(folder.resolve())


def test_open_directory_rejects_missing_folder_and_existing_file(
    tmp_path: Path,
) -> None:
    existing_file = tmp_path / "not-a-folder"
    existing_file.touch()

    with pytest.raises(FileNotFoundError):
        system.open_directory_command(tmp_path / "missing")
    with pytest.raises(NotADirectoryError):
        system.open_directory_command(existing_file)
