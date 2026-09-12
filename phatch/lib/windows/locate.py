from __future__ import annotations

import importlib
import ntpath
import os
import re
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import ModuleType
from typing import Final, Protocol


class RegistryHive(StrEnum):
    CURRENT_USER = "HKCU"
    LOCAL_MACHINE = "HKLM"
    CLASSES_ROOT = "HKCR"


class RegistryView(StrEnum):
    WOW64_64 = "64"
    WOW64_32 = "32"


@dataclass(frozen=True, slots=True)
class RegistryValue:
    data: str
    value_type: int


class RegistryKey(Protocol):
    def query_value(self, name: str | None) -> RegistryValue: ...


class RegistryBackend(Protocol):
    @property
    def REG_SZ(self) -> int: ...

    @property
    def REG_EXPAND_SZ(self) -> int: ...

    def open_key(
        self, hive: RegistryHive, path: str, view: RegistryView
    ) -> AbstractContextManager[RegistryKey]: ...

    def expand_environment(self, value: str) -> str: ...


class WindowsLookupError(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class UnsupportedApplicationError(WindowsLookupError):
    app_name: str

    def __str__(self) -> str:
        return f"unsupported registry application: {self.app_name}"


@dataclass(frozen=True, slots=True)
class RegistryBackendUnavailableError(WindowsLookupError):
    reason: str

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class RegistryEntryNotFoundError(WindowsLookupError):
    app_name: str

    def __str__(self) -> str:
        return f"no registry registration found for {self.app_name}"


@dataclass(frozen=True, slots=True)
class RegistryAccessDeniedError(WindowsLookupError):
    path: str

    def __str__(self) -> str:
        return f"registry access denied: {self.path}"


@dataclass(frozen=True, slots=True)
class MalformedRegistrationError(WindowsLookupError):
    value: str

    def __str__(self) -> str:
        return f"malformed executable registration: {self.value!r}"


@dataclass(frozen=True, slots=True)
class NonExecutableRegistrationError(WindowsLookupError):
    path: Path

    def __str__(self) -> str:
        return f"registered target is not executable: {self.path}"


@dataclass(frozen=True, slots=True)
class ExecutableResolution:
    app_name: str
    path: Path
    hive: RegistryHive
    view: RegistryView


@dataclass(frozen=True, slots=True)
class _Recipe:
    path: str
    parser: Callable[[str], str]


_QUOTED_EXECUTABLE: Final = re.compile(r'^\s*"([^"\r\n]+)"(?:\s|$)')
_UNQUOTED_EXECUTABLE: Final = re.compile(r"^\s*([^\s\"']+\.exe)(?:\s|$)", re.I)
_QUOTED_ICON: Final = re.compile(r'^\s*"([^"\r\n]+)"\s*(?:,\s*[+-]?\d+)?\s*$')
_UNQUOTED_ICON: Final = re.compile(r"^\s*([^\s,]+)(?:\s*,\s*[+-]?\d+)?\s*$")


def _absolute_windows_path(value: str) -> str:
    if not ntpath.isabs(value) or ntpath.splitext(value)[1].lower() != ".exe":
        raise MalformedRegistrationError(value)
    return value


def parse_command_executable(value: str) -> str:
    quoted = _QUOTED_EXECUTABLE.match(value)
    if quoted is not None:
        return _absolute_windows_path(quoted.group(1))
    unquoted = _UNQUOTED_EXECUTABLE.match(value)
    if unquoted is None:
        raise MalformedRegistrationError(value)
    return _absolute_windows_path(unquoted.group(1))


def parse_icon_executable(value: str) -> str:
    quoted = _QUOTED_ICON.match(value)
    if quoted is not None:
        return _absolute_windows_path(quoted.group(1))
    unquoted = _UNQUOTED_ICON.match(value)
    if unquoted is None:
        raise MalformedRegistrationError(value)
    return _absolute_windows_path(unquoted.group(1))


_RECIPES: Final = {
    "blender": _Recipe(r"blendfile\DefaultIcon", parse_icon_executable),
    "inkscape": _Recipe(r"svgfile\shell\edit\command", parse_command_executable),
}
_VIEWS: Final = (RegistryView.WOW64_64, RegistryView.WOW64_32)
_LOCATIONS: Final = (
    (RegistryHive.CURRENT_USER, r"Software\Classes"),
    (RegistryHive.LOCAL_MACHINE, r"Software\Classes"),
    (RegistryHive.CLASSES_ROOT, ""),
)


@dataclass(frozen=True, slots=True)
class RegistryExecutableLocator:
    registry: RegistryBackend
    is_executable: Callable[[Path], bool] = lambda path: (
        path.is_file() and os.access(path, os.X_OK)
    )

    def resolve(self, app_name: str) -> ExecutableResolution:
        recipe = _RECIPES.get(app_name.lower())
        if recipe is None:
            raise UnsupportedApplicationError(app_name)
        failure: WindowsLookupError | None = None
        for hive, prefix in _LOCATIONS:
            path = "\\".join(part for part in (prefix, recipe.path) if part)
            for view in _VIEWS:
                try:
                    with self.registry.open_key(hive, path, view) as key:
                        registered = key.query_value(None)
                except FileNotFoundError:
                    continue
                except PermissionError:
                    failure = failure or RegistryAccessDeniedError(path)
                    continue
                if registered.value_type not in {
                    self.registry.REG_SZ,
                    self.registry.REG_EXPAND_SZ,
                }:
                    failure = failure or MalformedRegistrationError(registered.data)
                    continue
                value = registered.data
                if registered.value_type == self.registry.REG_EXPAND_SZ:
                    value = self.registry.expand_environment(value)
                try:
                    executable = Path(recipe.parser(value))
                except MalformedRegistrationError as error:
                    failure = failure or error
                    continue
                if not self.is_executable(executable):
                    failure = failure or NonExecutableRegistrationError(executable)
                    continue
                return ExecutableResolution(app_name, executable, hive, view)
        if failure is not None:
            raise failure
        raise RegistryEntryNotFoundError(app_name)


class _NativeKey:
    def __init__(self, module: ModuleType, handle: object) -> None:
        self._module = module
        self._handle = handle

    def query_value(self, name: str | None) -> RegistryValue:
        data, value_type = self._module.QueryValueEx(self._handle, name)
        if not isinstance(data, str) or not isinstance(value_type, int):
            raise MalformedRegistrationError(repr(data))
        return RegistryValue(data, value_type)


@dataclass(frozen=True, slots=True)
class NativeRegistry:
    module: ModuleType

    @property
    def REG_SZ(self) -> int:
        return self.module.REG_SZ

    @property
    def REG_EXPAND_SZ(self) -> int:
        return self.module.REG_EXPAND_SZ

    def open_key(self, hive: RegistryHive, path: str, view: RegistryView):
        root = {
            RegistryHive.CURRENT_USER: self.module.HKEY_CURRENT_USER,
            RegistryHive.LOCAL_MACHINE: self.module.HKEY_LOCAL_MACHINE,
            RegistryHive.CLASSES_ROOT: self.module.HKEY_CLASSES_ROOT,
        }[hive]
        flag = (
            self.module.KEY_WOW64_64KEY
            if view is RegistryView.WOW64_64
            else self.module.KEY_WOW64_32KEY
        )
        handle = self.module.OpenKey(root, path, 0, self.module.KEY_READ | flag)
        return _NativeContext(self.module, handle)

    def expand_environment(self, value: str) -> str:
        return self.module.ExpandEnvironmentStrings(value)


class _NativeContext:
    def __init__(self, module: ModuleType, handle: object) -> None:
        self._module = module
        self._handle = handle

    def __enter__(self) -> _NativeKey:
        return _NativeKey(self._module, self._handle)

    def __exit__(self, *args: object) -> None:
        self._module.CloseKey(self._handle)


def find_exe(app_name: str) -> str | None:
    try:
        module = importlib.import_module("winreg")
    except ModuleNotFoundError:
        return None
    try:
        return str(
            RegistryExecutableLocator(NativeRegistry(module)).resolve(app_name).path
        )
    except WindowsLookupError:
        return None
