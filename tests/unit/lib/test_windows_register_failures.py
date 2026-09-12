from __future__ import annotations

from copy import deepcopy

import pytest

from phatch.lib.windows import register


class ProgrammerFailure(RuntimeError):
    pass


class TransactionStore:
    def __init__(self) -> None:
        self.keys: dict[str, dict[str | None, register.RegistryValue]] = {}
        self.snapshot_calls = 0
        self.snapshot_failure: tuple[int, Exception] | None = None
        self.delete_calls = 0
        self.delete_failure_at: int | None = None
        self.restore_calls: list[str] = []
        self.restore_failure_at: int | None = None

    def snapshot(self, path: str) -> register.KeySnapshot | None:
        self.snapshot_calls += 1
        if (
            self.snapshot_failure is not None
            and self.snapshot_calls == self.snapshot_failure[0]
        ):
            raise self.snapshot_failure[1]
        values = self.keys.get(path)
        command = self.keys.get(path + r"\command")
        if values is None and command is None:
            return None
        return register.KeySnapshot(deepcopy(values or {}), deepcopy(command))

    def set_value(
        self, path: str, name: str | None, value: register.RegistryValue
    ) -> None:
        self.keys.setdefault(path, {})[name] = value

    def delete_tree(self, path: str) -> None:
        self.delete_calls += 1
        self.keys.pop(path + r"\command", None)
        self.keys.pop(path, None)
        if self.delete_calls == self.delete_failure_at:
            raise PermissionError(f"delete denied: {path}")

    def restore(self, path: str, snapshot: register.KeySnapshot) -> None:
        self.restore_calls.append(path)
        if len(self.restore_calls) == self.restore_failure_at:
            raise PermissionError(f"restore denied: {path}")
        self.keys.pop(path + r"\command", None)
        self.keys[path] = deepcopy(snapshot.values)
        if snapshot.command_values is not None:
            self.keys[path + r"\command"] = deepcopy(snapshot.command_values)


def operation() -> register.ExplorerVerb:
    return register.ExplorerVerb(
        "recent",
        "Recent",
        ("gui.exe", "-d", "recent"),
        ("JPG", ".jpg", "png"),
        True,
    )


def seed_owned(store: TransactionStore) -> tuple[register.VerbTarget, ...]:
    targets = register.target_paths(operation())
    for index, target in enumerate(targets, start=1):
        store.keys[target.path] = {
            None: register.RegistryValue(f"label-{index}", 10 + index),
            register.OWNER_VALUE: register.RegistryValue(register.OWNER_MARKER, 20),
            "binary": register.RegistryValue(bytes([index]), 30 + index),
        }
        store.keys[target.path + r"\command"] = {
            None: register.RegistryValue(f"command-{index}", 40 + index),
            "count": register.RegistryValue(index, 50 + index),
        }
    return targets


@pytest.mark.parametrize("method", ["register", "remove"])
@pytest.mark.parametrize("backend_error", [PermissionError("denied"), OSError("io")])
def test_snapshot_backend_failure_is_typed(
    method: str,
    backend_error: OSError,
) -> None:
    store = TransactionStore()
    targets = seed_owned(store)
    before = deepcopy(store.keys)
    store.snapshot_failure = (2, backend_error)

    with pytest.raises(register.ExplorerVerbWriteError) as raised:
        getattr(register.ExplorerVerbRegistry(store), method)(operation())

    assert raised.value.path == targets[1].path
    assert raised.value.reason == str(backend_error)
    assert store.keys == before


def test_snapshot_programmer_failure_propagates() -> None:
    store = TransactionStore()
    seed_owned(store)
    store.snapshot_failure = (1, ProgrammerFailure("bug"))

    with pytest.raises(ProgrammerFailure, match="bug"):
        register.ExplorerVerbRegistry(store).remove(operation())


@pytest.mark.parametrize("failure_at", [1, 2, 3])
def test_remove_restores_every_target_after_each_delete_failure(
    failure_at: int,
) -> None:
    store = TransactionStore()
    targets = seed_owned(store)
    before = deepcopy(store.keys)
    store.delete_failure_at = failure_at

    with pytest.raises(register.ExplorerVerbWriteError) as raised:
        register.ExplorerVerbRegistry(store).remove(operation())

    assert raised.value.path == targets[failure_at - 1].path
    assert store.keys == before
    assert store.restore_calls == [
        target.path for target in reversed(targets[:failure_at])
    ]


def test_remove_rollback_failure_keeps_primary_and_attempts_all_restores() -> None:
    store = TransactionStore()
    targets = seed_owned(store)
    store.delete_failure_at = 3
    store.restore_failure_at = 1

    with pytest.raises(register.ExplorerVerbRollbackError) as raised:
        register.ExplorerVerbRegistry(store).remove(operation())

    assert isinstance(raised.value.primary, register.ExplorerVerbWriteError)
    assert raised.value.primary.path == targets[2].path
    assert "restore denied" in raised.value.rollback_reason
    assert store.restore_calls == [target.path for target in reversed(targets)]


def test_remove_preserves_missing_and_foreign_targets() -> None:
    store = TransactionStore()
    targets = register.target_paths(operation())
    store.keys[targets[1].path] = {
        register.OWNER_VALUE: register.RegistryValue("foreign", 9)
    }
    store.keys[targets[2].path] = {
        register.OWNER_VALUE: register.RegistryValue(register.OWNER_MARKER, 1)
    }

    result = register.ExplorerVerbRegistry(store).remove(operation())

    assert result.targets == (".png",)
    assert targets[1].path in store.keys
    assert targets[2].path not in store.keys
