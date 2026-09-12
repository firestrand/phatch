from __future__ import annotations

import os
from pathlib import Path

import pytest

from phatch.lib.windows import shortcut


class ComFailure(RuntimeError):
    pass


class StageShortcut:
    staged: Path
    failure_stage: str | None
    TargetPath: str
    Arguments: str
    WorkingDirectory: str
    Description: str
    IconLocation: str

    def __init__(self, staged: Path, failure_stage: str | None) -> None:
        self.__dict__["staged"] = staged
        self.__dict__["failure_stage"] = failure_stage
        self.__dict__["TargetPath"] = ""
        self.__dict__["Arguments"] = ""
        self.__dict__["WorkingDirectory"] = ""
        self.__dict__["Description"] = ""
        self.__dict__["IconLocation"] = ""

    def __setattr__(self, name: str, value: str) -> None:
        if name == "TargetPath" and self.failure_stage == "assignment":
            raise ComFailure("assignment")
        self.__dict__[name] = value

    def Save(self) -> None:
        if self.failure_stage == "save":
            raise ComFailure("save")
        self.staged.write_text("new", encoding="utf-8")


class StageShell:
    def __init__(self, failure_stage: str | None) -> None:
        self.failure_stage = failure_stage

    def CreateShortcut(self, path: str) -> shortcut.ComShortcut:
        if self.failure_stage == "create":
            raise ComFailure("create")
        return StageShortcut(Path(path), self.failure_stage)


class StageClient:
    def __init__(self, failure_stage: str | None) -> None:
        self.failure_stage = failure_stage

    def Dispatch(self, name: str) -> shortcut.ComShell:
        assert name == "WScript.Shell"
        if self.failure_stage == "dispatch":
            raise ComFailure("dispatch")
        return StageShell(self.failure_stage)


def spec(destination: Path) -> shortcut.ShortcutSpec:
    return shortcut.ShortcutSpec(destination, Path("gui.exe"))


@pytest.mark.parametrize(
    ("failure_stage", "expected"),
    [
        ("import", shortcut.ShortcutBrokenImportError),
        ("dispatch", shortcut.ShortcutDispatchError),
        ("create", shortcut.ShortcutCreateError),
        ("assignment", shortcut.ShortcutCreateError),
        ("save", shortcut.ShortcutSaveError),
        ("replace", shortcut.ShortcutReplaceError),
    ],
)
def test_non_oserror_boundary_failures_are_mapped(
    failure_stage: str,
    expected: type[shortcut.ShortcutError],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    staged = tmp_path / ".item.token.lnk"
    staged.write_text("residue", encoding="utf-8")

    def importer(_: str) -> StageClient:
        if failure_stage == "import":
            raise ComFailure("import")
        return StageClient(failure_stage)

    monkeypatch.setattr(
        Path,
        "unlink",
        lambda path, missing_ok=False: (_ for _ in ()).throw(
            PermissionError("path cleanup")
        ),
    )
    monkeypatch.setattr(
        shortcut.os,
        "unlink",
        lambda path: (_ for _ in ()).throw(PermissionError("os cleanup")),
    )
    if failure_stage == "replace":
        monkeypatch.setattr(
            shortcut.os,
            "replace",
            lambda source, target: (_ for _ in ()).throw(ComFailure("replace")),
        )

    with pytest.raises(expected, match=failure_stage):
        shortcut.ShortcutWriter(importer, lambda: "token").create(
            spec(tmp_path / "item.lnk")
        )

    assert staged.exists()


@pytest.mark.parametrize("interrupt", [KeyboardInterrupt("stop"), SystemExit("stop")])
def test_system_exceptions_propagate_from_com_boundary(
    interrupt: KeyboardInterrupt | SystemExit,
    tmp_path: Path,
) -> None:
    def importer(_: str) -> StageClient:
        raise interrupt

    with pytest.raises(type(interrupt), match="stop"):
        shortcut.ShortcutWriter(importer, lambda: "token").create(
            spec(tmp_path / "item.lnk")
        )


def test_primary_error_survives_path_cleanup_failure_with_os_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "item.lnk"
    staged = tmp_path / ".item.token.lnk"
    real_unlink = os.unlink

    def fail_path_unlink(path: Path, *, missing_ok: bool = False) -> None:
        del path, missing_ok
        raise PermissionError("path cleanup")

    monkeypatch.setattr(Path, "unlink", fail_path_unlink)
    monkeypatch.setattr(
        shortcut.os,
        "replace",
        lambda source, target: (_ for _ in ()).throw(ComFailure("replace")),
    )
    monkeypatch.setattr(shortcut.os, "unlink", real_unlink)

    with pytest.raises(shortcut.ShortcutReplaceError, match="replace"):
        shortcut.ShortcutWriter(lambda _: StageClient(None), lambda: "token").create(
            spec(destination)
        )

    assert not staged.exists()


def test_cleanup_only_failure_is_typed_and_residue_reflects_physical_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "item.lnk"
    staged = tmp_path / ".item.token.lnk"
    monkeypatch.setattr(shortcut.os, "replace", lambda source, target: None)
    monkeypatch.setattr(
        Path,
        "unlink",
        lambda path, missing_ok=False: (_ for _ in ()).throw(
            PermissionError("path cleanup")
        ),
    )
    monkeypatch.setattr(
        shortcut.os,
        "unlink",
        lambda path: (_ for _ in ()).throw(PermissionError("os cleanup")),
    )

    with pytest.raises(shortcut.ShortcutSaveError, match="os cleanup"):
        shortcut.ShortcutWriter(lambda _: StageClient(None), lambda: "token").create(
            spec(destination)
        )

    assert staged.exists()


def test_missing_staging_parent_is_not_created(tmp_path: Path) -> None:
    parent = tmp_path / "missing"

    with pytest.raises(shortcut.ShortcutSaveError):
        shortcut.ShortcutWriter(lambda _: StageClient(None), lambda: "token").create(
            spec(parent / "item.lnk")
        )

    assert not parent.exists()
