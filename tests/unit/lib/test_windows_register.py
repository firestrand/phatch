from __future__ import annotations

from copy import deepcopy
from types import ModuleType

import pytest

from phatch.lib.windows import register


class FakeStore:
    def __init__(self) -> None:
        self.keys: dict[str, dict[str | None, register.RegistryValue]] = {}
        self.mutations = 0
        self.fail_at: int | None = None
        self.rollback_fails = False

    def snapshot(self, path: str) -> register.KeySnapshot | None:
        values = self.keys.get(path)
        command = self.keys.get(path + r"\command")
        if values is None and command is None:
            return None
        return register.KeySnapshot(deepcopy(values or {}), deepcopy(command))

    def set_value(
        self, path: str, name: str | None, value: register.RegistryValue
    ) -> None:
        self.mutations += 1
        if self.fail_at == self.mutations:
            raise PermissionError(path)
        self.keys.setdefault(path, {})[name] = value

    def delete_tree(self, path: str) -> None:
        if self.rollback_fails:
            raise PermissionError(path)
        self.keys.pop(path + r"\command", None)
        self.keys.pop(path, None)

    def restore(self, path: str, snapshot: register.KeySnapshot) -> None:
        if self.rollback_fails:
            raise PermissionError(path)
        self.delete_tree(path)
        self.keys[path] = deepcopy(snapshot.values)
        if snapshot.command_values is not None:
            self.keys[path + r"\command"] = deepcopy(snapshot.command_values)


def operation(*extensions: str, folder: bool = False) -> register.ExplorerVerb:
    return register.ExplorerVerb(
        identity="recent",
        display_label="Phatch Recent...",
        argv=(r"C:\Phatch\phatch-gui.exe", "-d", "recent"),
        extensions=extensions,
        include_folder=folder,
    )


def test_register_writes_owned_hkcu_paths_and_normalizes_duplicates() -> None:
    store = FakeStore()

    result = register.ExplorerVerbRegistry(store).register(
        operation("JPG", ".jpg", "png", folder=True)
    )

    assert result.targets == ("folder", ".jpg", ".png")
    assert all(path.startswith("Software\\Classes\\") for path in store.keys)
    assert not any("HKEY_CLASSES_ROOT" in path for path in store.keys)
    roots = [path for path in store.keys if not path.endswith(r"\command")]
    assert all(
        store.keys[path][register.OWNER_VALUE].data == register.OWNER_MARKER
        for path in roots
    )
    commands = [store.keys[path + r"\command"][None].data for path in roots]
    assert all(
        isinstance(command, str) and command.endswith(' "%1"') for command in commands
    )


def test_register_coexists_with_foreign_label_and_rejects_owned_id_collision() -> None:
    store = FakeStore()
    foreign = r"Software\Classes\SystemFileAssociations\.jpg\shell\Foreign"
    store.keys[foreign] = {None: register.RegistryValue("Phatch Recent...", 1)}
    verb = operation("jpg")
    owned_path = register.target_paths(verb)[0].path
    store.keys[owned_path] = {
        register.OWNER_VALUE: register.RegistryValue("SomeoneElse", 1)
    }

    with pytest.raises(register.ExplorerVerbConflictError):
        register.ExplorerVerbRegistry(store).register(verb)
    assert store.keys[foreign][None].data == "Phatch Recent..."


@pytest.mark.parametrize("failure", [1, 2, 3, 4, 5, 6])
def test_register_rolls_back_after_each_mutation(failure: int) -> None:
    store = FakeStore()
    before = deepcopy(store.keys)
    store.fail_at = failure

    with pytest.raises(register.ExplorerVerbWriteError):
        register.ExplorerVerbRegistry(store).register(operation("jpg", "png"))

    assert store.keys == before


def test_register_surfaces_primary_and_rollback_failures() -> None:
    store = FakeStore()
    store.fail_at = 2
    store.rollback_fails = True

    with pytest.raises(register.ExplorerVerbRollbackError) as error:
        register.ExplorerVerbRegistry(store).register(operation("jpg"))

    assert isinstance(error.value.primary, register.ExplorerVerbWriteError)


def test_remove_is_idempotent_and_preserves_foreign_state() -> None:
    store = FakeStore()
    verb = operation("jpg")
    registry = register.ExplorerVerbRegistry(store)
    registry.register(verb)
    foreign = r"Software\Classes\SystemFileAssociations\.png\shell\Foreign"
    store.keys[foreign] = {None: register.RegistryValue("Other", 1)}

    assert registry.remove(verb).targets == (".jpg",)
    assert registry.remove(verb).targets == ()
    assert foreign in store.keys


def test_stable_id_uses_identity_and_canonical_action_list() -> None:
    first = register.ExplorerVerb(
        "action-list",
        "Label",
        ("gui.exe",),
        ("jpg",),
        action_list=r"C:\Lists\..\Lists\Edit.phatch",
    )
    second = register.ExplorerVerb(
        "action-list",
        "Translated",
        ("gui.exe",),
        ("jpg",),
        action_list=r"c:\lists\edit.phatch",
    )
    assert register.verb_id(first) == register.verb_id(second)
    assert register.verb_id(first).startswith("Phatch.")


def test_register_updates_owned_state_and_skips_empty_extensions() -> None:
    store = FakeStore()
    verb = operation("", ".")
    assert register.ExplorerVerbRegistry(store).register(verb).targets == ()

    owned = operation("jpg")
    path = register.target_paths(owned)[0].path
    store.keys[path] = {
        None: register.RegistryValue("Old", 1),
        register.OWNER_VALUE: register.RegistryValue(register.OWNER_MARKER, 1),
    }
    register.ExplorerVerbRegistry(store).register(owned)
    assert store.keys[path][None].data == "Phatch Recent..."


def test_remove_surfaces_denial() -> None:
    store = FakeStore()
    verb = operation("jpg")
    registry = register.ExplorerVerbRegistry(store)
    registry.register(verb)
    store.rollback_fails = True
    with pytest.raises(register.ExplorerVerbRollbackError):
        registry.remove(verb)


def test_native_registry_store_snapshots_restores_and_deletes() -> None:
    values: dict[str, dict[str, tuple[register.RegistryData, int]]] = {
        "verb": {"": ("Label", 1), "number": (42, 4)},
        r"verb\command": {"": ('gui.exe "%1"', 1)},
    }

    class Key:
        def __init__(self, path: str) -> None:
            self.path = path

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def open_key(root, path, reserved, access):
        del root, reserved, access
        if path not in values:
            raise FileNotFoundError(path)
        return Key(path)

    def create_key(root, path, reserved, access):
        del root, reserved, access
        values.setdefault(path, {})
        return Key(path)

    def enum_value(key, index):
        name, value = tuple(values[key.path].items())[index]
        return name, value[0], value[1]

    def set_value(key, name, reserved, value_type, data):
        del reserved
        values[key.path][name] = (data, value_type)

    def delete_key(root, path):
        del root
        if path not in values:
            raise FileNotFoundError(path)
        del values[path]

    module = ModuleType("fake_winreg")
    attributes = {
        "HKEY_CURRENT_USER": "HKCU",
        "KEY_READ": 1,
        "KEY_WRITE": 2,
        "OpenKey": open_key,
        "CreateKeyEx": create_key,
        "QueryInfoKey": lambda key: (0, len(values[key.path]), 0),
        "EnumValue": enum_value,
        "SetValueEx": set_value,
        "DeleteKey": delete_key,
    }
    for name, value in attributes.items():
        setattr(module, name, value)
    store = register.NativeRegistryStore(module)
    snapshot = store.snapshot("verb")
    assert snapshot is not None
    store.set_value("verb", None, register.RegistryValue("Changed"))
    store.restore("verb", snapshot)
    assert values["verb"][""][0] == "Label"
    store.delete_tree("verb")
    store.delete_tree("verb")
    assert store.snapshot("verb") is None


def test_compatibility_functions_construct_native_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FakeStore()
    monkeypatch.setattr(
        register.NativeRegistryStore, "create", classmethod(lambda cls: store)
    )
    added = register.register_extensions(
        "Recent", ("gui.exe", "-d", "recent"), ("jpg",), identity="recent"
    )
    removed = register.deregister_extensions("recent", ("jpg",), folder=False)
    assert added == removed == (".jpg",)


def test_native_store_reports_missing_winreg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        register.importlib,
        "import_module",
        lambda name: (_ for _ in ()).throw(ModuleNotFoundError(name)),
    )
    with pytest.raises(register.ExplorerVerbWriteError):
        register.NativeRegistryStore.create()


def test_remove_preserves_foreign_exact_id() -> None:
    store = FakeStore()
    verb = operation("jpg")
    path = register.target_paths(verb)[0].path
    store.keys[path] = {register.OWNER_VALUE: register.RegistryValue("foreign", 1)}
    assert register.ExplorerVerbRegistry(store).remove(verb).targets == ()
    assert path in store.keys


def test_rollback_restores_prior_owned_snapshot() -> None:
    store = FakeStore()
    verb = operation("jpg", "png")
    path = register.target_paths(verb)[0].path
    store.keys[path] = {
        None: register.RegistryValue("Old", 1),
        register.OWNER_VALUE: register.RegistryValue(register.OWNER_MARKER, 1),
    }
    before = deepcopy(store.keys)
    store.fail_at = 4
    with pytest.raises(register.ExplorerVerbWriteError):
        register.ExplorerVerbRegistry(store).register(verb)
    assert store.keys == before


def test_registry_error_messages_are_nonempty() -> None:
    primary = register.ExplorerVerbWriteError("key", "denied")
    errors = (
        register.ExplorerVerbConflictError("key"),
        primary,
        register.ExplorerVerbRollbackError(primary, "rollback denied"),
    )
    assert all(str(error) for error in errors)
