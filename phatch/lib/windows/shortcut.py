from __future__ import annotations

import importlib
import os
import subprocess
import sys
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Protocol


class ComShortcut(Protocol):
    TargetPath: str
    Arguments: str
    WorkingDirectory: str
    Description: str
    IconLocation: str

    def Save(self) -> None: ...


class ComShell(Protocol):
    def CreateShortcut(self, path: str) -> ComShortcut: ...


class ComClient(Protocol):
    def Dispatch(self, name: str) -> ComShell: ...


ModuleImporter = Callable[[str], ComClient]


class ShortcutError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ShortcutUnavailableError(ShortcutError):
    reason: str

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class ShortcutBrokenImportError(ShortcutError):
    reason: str

    def __str__(self) -> str:
        return f"pywin32 import failed: {self.reason}"


@dataclass(frozen=True, slots=True)
class ShortcutDispatchError(ShortcutError):
    reason: str

    def __str__(self) -> str:
        return f"COM dispatch failed: {self.reason}"


@dataclass(frozen=True, slots=True)
class ShortcutCreateError(ShortcutError):
    reason: str

    def __str__(self) -> str:
        return f"shortcut creation failed: {self.reason}"


@dataclass(frozen=True, slots=True)
class ShortcutSaveError(ShortcutError):
    reason: str

    def __str__(self) -> str:
        return f"shortcut save failed: {self.reason}"


@dataclass(frozen=True, slots=True)
class ShortcutReplaceError(ShortcutError):
    reason: str

    def __str__(self) -> str:
        return f"shortcut replacement failed: {self.reason}"


@dataclass(frozen=True, slots=True)
class ShortcutSpec:
    destination: Path
    target: Path
    arguments: tuple[str, ...] = ()
    working_directory: Path | None = None
    description: str = ""
    icon_path: Path | None = None
    icon_index: int = 0


@dataclass(frozen=True, slots=True)
class ShortcutResult:
    path: Path


def _import_client(name: str) -> ComClient:
    module = importlib.import_module(name)
    dispatch = getattr(module, "Dispatch", None)
    if not callable(dispatch):
        raise ShortcutUnavailableError("win32com.client has no callable Dispatch")
    return _NativeComClient(module)


def _cleanup_staged(path: Path) -> OSError | None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        try:
            os.unlink(path)
        except FileNotFoundError:
            return None
        except OSError as error:
            return error
    return None


@dataclass(frozen=True, slots=True)
class _NativeComClient:
    module: ModuleType

    def Dispatch(self, name: str) -> ComShell:
        return self.module.Dispatch(name)


@dataclass(frozen=True, slots=True)
class ShortcutWriter:
    importer: ModuleImporter = _import_client
    staging_token: Callable[[], str] = lambda: uuid.uuid4().hex

    def create(self, spec: ShortcutSpec) -> ShortcutResult:
        staged = spec.destination.with_name(
            f".{spec.destination.stem}.{self.staging_token()}{spec.destination.suffix}"
        )
        try:
            try:
                client = self.importer("win32com.client")
            except ShortcutError:
                raise
            except ModuleNotFoundError as error:
                raise ShortcutUnavailableError(str(error)) from error
            except Exception as error:
                raise ShortcutBrokenImportError(str(error)) from error
            try:
                shell = client.Dispatch("WScript.Shell")
            except Exception as error:
                raise ShortcutDispatchError(str(error)) from error
            try:
                item = shell.CreateShortcut(str(staged))
            except Exception as error:
                raise ShortcutCreateError(str(error)) from error
            try:
                item.TargetPath = str(spec.target)
                item.Arguments = subprocess.list2cmdline(spec.arguments)
                item.WorkingDirectory = (
                    ""
                    if spec.working_directory is None
                    else str(spec.working_directory)
                )
                item.Description = spec.description
                if spec.icon_path is not None:
                    item.IconLocation = f"{spec.icon_path},{spec.icon_index}"
            except Exception as error:
                raise ShortcutCreateError(str(error)) from error
            try:
                item.Save()
            except Exception as error:
                raise ShortcutSaveError(str(error)) from error
            finally:
                del item
                del shell
                del client
            if not staged.is_file():
                raise ShortcutSaveError("COM did not create the staged shortcut")
            try:
                os.replace(staged, spec.destination)
            except Exception as error:
                raise ShortcutReplaceError(str(error)) from error
            return ShortcutResult(spec.destination)
        finally:
            active_error = sys.exception()
            cleanup_error = _cleanup_staged(staged)
            if active_error is None and cleanup_error is not None:
                raise ShortcutSaveError(str(cleanup_error)) from cleanup_error


def create(
    save_as: str,
    path: str,
    arguments: tuple[str, ...] = (),
    working_dir: str = "",
    description: str = "",
    icon_path: str | None = None,
    icon_index: int = 0,
) -> ShortcutResult:
    return ShortcutWriter().create(
        ShortcutSpec(
            Path(save_as),
            Path(path),
            arguments,
            Path(working_dir) if working_dir else None,
            description,
            Path(icon_path) if icon_path else None,
            icon_index,
        )
    )
