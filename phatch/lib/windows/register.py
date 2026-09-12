from __future__ import annotations

import hashlib
import importlib
import ntpath
import subprocess
from contextlib import suppress
from dataclasses import dataclass
from types import ModuleType
from typing import Final, Protocol

OWNER_VALUE: Final = "Phatch.Owner"
OWNER_MARKER: Final = "Phatch.WindowsExplorerVerb.v1"
REG_SZ: Final = 1
RegistryData = str | int | bytes | list[str] | None


@dataclass(frozen=True, slots=True)
class RegistryValue:
    data: RegistryData
    value_type: int = REG_SZ


@dataclass(frozen=True, slots=True)
class KeySnapshot:
    values: dict[str | None, RegistryValue]
    command_values: dict[str | None, RegistryValue] | None


class RegistryStore(Protocol):
    def snapshot(self, path: str) -> KeySnapshot | None: ...

    def set_value(self, path: str, name: str | None, value: RegistryValue) -> None: ...

    def delete_tree(self, path: str) -> None: ...

    def restore(self, path: str, snapshot: KeySnapshot) -> None: ...


@dataclass(frozen=True, slots=True)
class ExplorerVerb:
    identity: str
    display_label: str
    argv: tuple[str, ...]
    extensions: tuple[str, ...]
    include_folder: bool = False
    action_list: str | None = None


@dataclass(frozen=True, slots=True)
class VerbTarget:
    label: str
    path: str


@dataclass(frozen=True, slots=True)
class ExplorerVerbResult:
    targets: tuple[str, ...]


class ExplorerVerbError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ExplorerVerbConflictError(ExplorerVerbError):
    path: str

    def __str__(self) -> str:
        return f"Explorer verb is occupied by another owner: {self.path}"


@dataclass(frozen=True, slots=True)
class ExplorerVerbWriteError(ExplorerVerbError):
    path: str
    reason: str

    def __str__(self) -> str:
        return f"Explorer verb write failed at {self.path}: {self.reason}"


@dataclass(frozen=True, slots=True)
class ExplorerVerbRollbackError(ExplorerVerbError):
    primary: ExplorerVerbError
    rollback_reason: str

    def __str__(self) -> str:
        return f"{self.primary}; rollback failed: {self.rollback_reason}"


def verb_id(verb: ExplorerVerb) -> str:
    action_list = ""
    if verb.action_list is not None:
        action_list = ntpath.normcase(ntpath.normpath(verb.action_list))
    payload = f"{verb.identity}\0{action_list}".encode()
    return "Phatch." + hashlib.sha256(payload).hexdigest()[:20]


def _extensions(values: tuple[str, ...]) -> tuple[str, ...]:
    normalized = {
        "." + value.lower().lstrip(".") for value in values if value.strip(".")
    }
    return tuple(sorted(normalized))


def target_paths(verb: ExplorerVerb) -> tuple[VerbTarget, ...]:
    identifier = verb_id(verb)
    targets = [
        VerbTarget(
            extension,
            rf"Software\Classes\SystemFileAssociations\{extension}\shell\{identifier}",
        )
        for extension in _extensions(verb.extensions)
    ]
    if verb.include_folder:
        targets.insert(
            0,
            VerbTarget("folder", rf"Software\Classes\Folder\shell\{identifier}"),
        )
    return tuple(targets)


def serialize_command(argv: tuple[str, ...]) -> str:
    return subprocess.list2cmdline(argv) + ' "%1"'


@dataclass(frozen=True, slots=True)
class ExplorerVerbRegistry:
    store: RegistryStore

    def register(self, verb: ExplorerVerb) -> ExplorerVerbResult:
        targets = target_paths(verb)
        snapshots = self._snapshots(targets)
        for target, snapshot in snapshots:
            if snapshot is None:
                continue
            owner = snapshot.values.get(OWNER_VALUE)
            if owner is None or owner.data != OWNER_MARKER:
                raise ExplorerVerbConflictError(target.path)
        touched: list[tuple[VerbTarget, KeySnapshot | None]] = []
        try:
            for target, snapshot in snapshots:
                touched.append((target, snapshot))
                self.store.set_value(
                    target.path, None, RegistryValue(verb.display_label)
                )
                self.store.set_value(
                    target.path, OWNER_VALUE, RegistryValue(OWNER_MARKER)
                )
                self.store.set_value(
                    target.path + r"\command",
                    None,
                    RegistryValue(serialize_command(verb.argv)),
                )
        except (OSError, PermissionError) as error:
            primary = ExplorerVerbWriteError(touched[-1][0].path, str(error))
            self._rollback(touched, primary)
            raise primary from error
        return ExplorerVerbResult(tuple(target.label for target in targets))

    def _snapshots(
        self, targets: tuple[VerbTarget, ...]
    ) -> tuple[tuple[VerbTarget, KeySnapshot | None], ...]:
        snapshots: list[tuple[VerbTarget, KeySnapshot | None]] = []
        for target in targets:
            try:
                snapshot = self.store.snapshot(target.path)
            except OSError as error:
                raise ExplorerVerbWriteError(target.path, str(error)) from error
            snapshots.append((target, snapshot))
        return tuple(snapshots)

    def _rollback(
        self,
        touched: list[tuple[VerbTarget, KeySnapshot | None]],
        primary: ExplorerVerbError,
    ) -> None:
        rollback_error: OSError | None = None
        for target, snapshot in reversed(touched):
            try:
                if snapshot is None:
                    self.store.delete_tree(target.path)
                else:
                    self.store.restore(target.path, snapshot)
            except OSError as error:
                if rollback_error is None:
                    rollback_error = error
        if rollback_error is not None:
            raise ExplorerVerbRollbackError(
                primary, str(rollback_error)
            ) from rollback_error

    def remove(self, verb: ExplorerVerb) -> ExplorerVerbResult:
        snapshots = self._snapshots(target_paths(verb))
        removed: list[str] = []
        owned: list[tuple[VerbTarget, KeySnapshot]] = []
        for target, snapshot in snapshots:
            if snapshot is None:
                continue
            owner = snapshot.values.get(OWNER_VALUE)
            if owner is None or owner.data != OWNER_MARKER:
                continue
            owned.append((target, snapshot))
        touched: list[tuple[VerbTarget, KeySnapshot | None]] = []
        try:
            for target, snapshot in owned:
                touched.append((target, snapshot))
                self.store.delete_tree(target.path)
                removed.append(target.label)
        except OSError as error:
            primary = ExplorerVerbWriteError(touched[-1][0].path, str(error))
            self._rollback(touched, primary)
            raise primary from error
        return ExplorerVerbResult(tuple(removed))


@dataclass(frozen=True, slots=True)
class NativeRegistryStore:
    module: ModuleType

    @classmethod
    def create(cls) -> NativeRegistryStore:
        try:
            return cls(importlib.import_module("winreg"))
        except ModuleNotFoundError as error:
            raise ExplorerVerbWriteError(
                "winreg", "Windows registry unavailable"
            ) from error

    def _read_values(self, path: str) -> dict[str | None, RegistryValue] | None:
        try:
            with self.module.OpenKey(
                self.module.HKEY_CURRENT_USER, path, 0, self.module.KEY_READ
            ) as key:
                count = self.module.QueryInfoKey(key)[1]
                values: dict[str | None, RegistryValue] = {}
                for index in range(count):
                    name, data, value_type = self.module.EnumValue(key, index)
                    values[name or None] = RegistryValue(data, value_type)
                return values
        except FileNotFoundError:
            return None

    def snapshot(self, path: str) -> KeySnapshot | None:
        values = self._read_values(path)
        command = self._read_values(path + r"\command")
        if values is None and command is None:
            return None
        return KeySnapshot(values or {}, command)

    def set_value(self, path: str, name: str | None, value: RegistryValue) -> None:
        with self.module.CreateKeyEx(
            self.module.HKEY_CURRENT_USER, path, 0, self.module.KEY_WRITE
        ) as key:
            self.module.SetValueEx(key, name or "", 0, value.value_type, value.data)

    def delete_tree(self, path: str) -> None:
        with suppress(FileNotFoundError):
            self.module.DeleteKey(self.module.HKEY_CURRENT_USER, path + r"\command")
        with suppress(FileNotFoundError):
            self.module.DeleteKey(self.module.HKEY_CURRENT_USER, path)

    def restore(self, path: str, snapshot: KeySnapshot) -> None:
        self.delete_tree(path)
        for name, value in snapshot.values.items():
            self.set_value(path, name, value)
        if snapshot.command_values is not None:
            for name, value in snapshot.command_values.items():
                self.set_value(path + r"\command", name, value)


def register_extensions(
    label: str,
    argv: tuple[str, ...],
    extensions: tuple[str, ...],
    folder: bool = False,
    *,
    identity: str = "legacy",
    action_list: str | None = None,
) -> tuple[str, ...]:
    verb = ExplorerVerb(identity, label, argv, extensions, folder, action_list)
    return ExplorerVerbRegistry(NativeRegistryStore.create()).register(verb).targets


def deregister_extensions(
    identity: str,
    extensions: tuple[str, ...],
    folder: bool = True,
    *,
    action_list: str | None = None,
) -> tuple[str, ...]:
    verb = ExplorerVerb(identity, "", (), extensions, folder, action_list)
    return ExplorerVerbRegistry(NativeRegistryStore.create()).remove(verb).targets
