from __future__ import annotations

from pathlib import Path

import pytest

from phatch.lib.windows import shortcut


class FakeShortcut:
    def __init__(self, staged: Path, *, save_error: OSError | None = None) -> None:
        self.staged = staged
        self.save_error = save_error
        self.TargetPath = ""
        self.Arguments = ""
        self.WorkingDirectory = ""
        self.Description = ""
        self.IconLocation = ""
        self.saves = 0

    def Save(self) -> None:
        self.saves += 1
        if self.save_error is not None:
            raise self.save_error
        self.staged.write_text("new shortcut", encoding="utf-8")


class FakeShell:
    def __init__(
        self, *, create_error: OSError | None = None, save_error: OSError | None = None
    ) -> None:
        self.create_error = create_error
        self.save_error = save_error
        self.created: list[FakeShortcut] = []

    def CreateShortcut(self, path: str) -> FakeShortcut:
        if self.create_error is not None:
            raise self.create_error
        item = FakeShortcut(Path(path), save_error=self.save_error)
        self.created.append(item)
        return item


class FakeClient:
    def __init__(
        self, shell: FakeShell, *, dispatch_error: OSError | None = None
    ) -> None:
        self.shell = shell
        self.dispatch_error = dispatch_error

    def Dispatch(self, name: str) -> FakeShell:
        assert name == "WScript.Shell"
        if self.dispatch_error is not None:
            raise self.dispatch_error
        return self.shell


def spec(destination: Path, icon_index: int = 0) -> shortcut.ShortcutSpec:
    return shortcut.ShortcutSpec(
        destination,
        Path(r"C:\Phatch\phatch-gui.exe"),
        ("-d", "recent item"),
        Path(r"C:\Phatch"),
        "Recent",
        Path(r"C:\Phatch\phatch.ico"),
        icon_index,
    )


@pytest.mark.parametrize("icon_index", [0, 4])
def test_shortcut_sets_all_fields_and_atomically_replaces(
    icon_index: int, tmp_path: Path
) -> None:
    destination = tmp_path / "Recent.lnk"
    shell = FakeShell()
    writer = shortcut.ShortcutWriter(
        lambda _: FakeClient(shell), staging_token=lambda: "token"
    )

    result = writer.create(spec(destination, icon_index))

    created = shell.created[0]
    assert result.path == destination
    assert created.TargetPath == r"C:\Phatch\phatch-gui.exe"
    assert created.Arguments == '-d "recent item"'
    assert created.WorkingDirectory == r"C:\Phatch"
    assert created.Description == "Recent"
    assert created.IconLocation == rf"C:\Phatch\phatch.ico,{icon_index}"
    assert created.saves == 1
    assert destination.read_text(encoding="utf-8") == "new shortcut"


def test_shortcut_reports_missing_pywin32(tmp_path: Path) -> None:
    def missing(_: str):
        raise ModuleNotFoundError("win32com")

    with pytest.raises(shortcut.ShortcutUnavailableError):
        shortcut.ShortcutWriter(missing).create(spec(tmp_path / "x.lnk"))


def test_shortcut_reports_broken_pywin32(tmp_path: Path) -> None:
    def broken(_: str):
        raise ImportError("broken")

    with pytest.raises(shortcut.ShortcutBrokenImportError):
        shortcut.ShortcutWriter(broken).create(spec(tmp_path / "x.lnk"))


@pytest.mark.parametrize(
    "where", ["dispatch", "create", "save", "replace", "missing-stage"]
)
def test_shortcut_preserves_existing_file_on_failures(
    where: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "old.lnk"
    destination.write_text("old", encoding="utf-8")
    shell = FakeShell(
        create_error=OSError("create") if where == "create" else None,
        save_error=OSError("save") if where == "save" else None,
    )
    client = FakeClient(
        shell, dispatch_error=OSError("dispatch") if where == "dispatch" else None
    )
    writer = shortcut.ShortcutWriter(lambda _: client, staging_token=lambda: "token")
    if where == "replace":
        monkeypatch.setattr(
            shortcut.os,
            "replace",
            lambda source, target: (_ for _ in ()).throw(OSError("replace")),
        )
    if where == "missing-stage":
        monkeypatch.setattr(FakeShortcut, "Save", lambda self: None)

    with pytest.raises(shortcut.ShortcutError):
        writer.create(spec(destination))

    assert destination.read_text(encoding="utf-8") == "old"
    assert not (tmp_path / ".old.token.lnk").exists()


def test_shortcut_supports_empty_optional_fields_and_compatibility_create(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    shell = FakeShell()
    writer = shortcut.ShortcutWriter(
        lambda _: FakeClient(shell), staging_token=lambda: "token"
    )
    destination = tmp_path / "plain.lnk"
    result = writer.create(shortcut.ShortcutSpec(destination, Path("gui.exe")))
    assert result.path == destination
    assert shell.created[0].WorkingDirectory == ""
    assert shell.created[0].IconLocation == ""

    calls: list[shortcut.ShortcutSpec] = []
    monkeypatch.setattr(
        shortcut.ShortcutWriter,
        "create",
        lambda self, value: (
            calls.append(value) or shortcut.ShortcutResult(value.destination)
        ),
    )
    shortcut.create(
        str(destination),
        "gui.exe",
        ("-n",),
        description="Inspect",
        icon_path="icon.ico",
        icon_index=2,
    )
    assert calls[0].arguments == ("-n",)


def test_native_client_boundary_and_error_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shell = FakeShell()
    monkeypatch.setattr(
        shortcut.importlib,
        "import_module",
        lambda name: FakeClient(shell),
    )
    assert shortcut._import_client("win32com.client").Dispatch("WScript.Shell") is shell
    monkeypatch.setattr(
        shortcut.importlib,
        "import_module",
        lambda name: object(),
    )
    with pytest.raises(shortcut.ShortcutUnavailableError):
        shortcut._import_client("win32com.client")
    errors = (
        shortcut.ShortcutUnavailableError("missing"),
        shortcut.ShortcutBrokenImportError("broken"),
        shortcut.ShortcutDispatchError("dispatch"),
        shortcut.ShortcutCreateError("create"),
        shortcut.ShortcutSaveError("save"),
        shortcut.ShortcutReplaceError("replace"),
    )
    assert all(str(error) for error in errors)
