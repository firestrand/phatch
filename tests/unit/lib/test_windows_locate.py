from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from phatch.lib.windows import locate


class FakeKey:
    def __init__(self, value: locate.RegistryValue) -> None:
        self.value = value
        self.closed = False

    def query_value(self, name: str | None) -> locate.RegistryValue:
        del name
        return self.value

    def __enter__(self) -> FakeKey:
        return self

    def __exit__(self, *args: object) -> None:
        self.closed = True


class FakeRegistry:
    REG_SZ = 1
    REG_EXPAND_SZ = 2

    def __init__(self) -> None:
        self.values: dict[
            tuple[locate.RegistryHive, str, locate.RegistryView],
            locate.RegistryValue | BaseException,
        ] = {}
        self.opens: list[tuple[locate.RegistryHive, str, locate.RegistryView]] = []
        self.keys: list[FakeKey] = []

    @contextmanager
    def open_key(
        self,
        hive: locate.RegistryHive,
        path: str,
        view: locate.RegistryView,
    ):
        identity = (hive, path, view)
        self.opens.append(identity)
        value = self.values.get(identity, FileNotFoundError(path))
        if isinstance(value, BaseException):
            raise value
        key = FakeKey(value)
        self.keys.append(key)
        with key:
            yield key

    def expand_environment(self, value: str) -> str:
        return value.replace("%TOOLS%", r"C:\Tools")


def executable_file(tmp_path: Path, name: str = "tool.exe") -> Path:
    target = tmp_path / name
    target.write_text("binary", encoding="utf-8")
    target.chmod(0o755)
    return target


def test_lookup_prefers_user_registration_and_closes_handle(tmp_path: Path) -> None:
    user = executable_file(tmp_path, "user.exe")
    machine = executable_file(tmp_path, "machine.exe")
    registry = FakeRegistry()
    registry.values[
        (
            locate.RegistryHive.CURRENT_USER,
            r"Software\Classes\blendfile\DefaultIcon",
            locate.RegistryView.WOW64_64,
        )
    ] = locate.RegistryValue(f'"{user}",0', 1)
    registry.values[
        (
            locate.RegistryHive.LOCAL_MACHINE,
            r"Software\Classes\blendfile\DefaultIcon",
            locate.RegistryView.WOW64_64,
        )
    ] = locate.RegistryValue(f'"{machine}",0', 1)

    result = locate.RegistryExecutableLocator(registry).resolve("blender")

    assert result.path == user
    assert result.hive is locate.RegistryHive.CURRENT_USER
    assert registry.keys[0].closed


def test_lookup_checks_64_then_32_bit_views(tmp_path: Path) -> None:
    target = executable_file(tmp_path)
    registry = FakeRegistry()
    path = r"Software\Classes\svgfile\shell\edit\command"
    registry.values[
        (locate.RegistryHive.CURRENT_USER, path, locate.RegistryView.WOW64_32)
    ] = locate.RegistryValue(f'"{target}" "%1"', 1)

    result = locate.RegistryExecutableLocator(registry).resolve("inkscape")

    assert result.view is locate.RegistryView.WOW64_32
    assert [item[2] for item in registry.opens[:2]] == [
        locate.RegistryView.WOW64_64,
        locate.RegistryView.WOW64_32,
    ]


@pytest.mark.parametrize(
    "registered",
    [
        r'C:\Program Files\Inkscape\inkscape.exe "%1"',
        r'"C:\Program Files\Inkscape\inkscape.exe',
        "",
    ],
)
def test_lookup_rejects_ambiguous_or_malformed_commands(registered: str) -> None:
    registry = FakeRegistry()
    path = r"Software\Classes\svgfile\shell\edit\command"
    registry.values[
        (locate.RegistryHive.CURRENT_USER, path, locate.RegistryView.WOW64_64)
    ] = locate.RegistryValue(registered, 1)

    with pytest.raises(locate.MalformedRegistrationError):
        locate.RegistryExecutableLocator(
            registry, is_executable=lambda _: True
        ).resolve("inkscape")


def test_lookup_expands_only_expand_string_values() -> None:
    path = r"Software\Classes\blendfile\DefaultIcon"
    registry = FakeRegistry()
    identity = (locate.RegistryHive.CURRENT_USER, path, locate.RegistryView.WOW64_64)
    registry.values[identity] = locate.RegistryValue(r"%TOOLS%\blender.exe,0", 2)
    result = locate.RegistryExecutableLocator(
        registry, is_executable=lambda _: True
    ).resolve("blender")
    assert str(result.path) == r"C:\Tools\blender.exe"

    registry.values[identity] = locate.RegistryValue(r"%TOOLS%\blender.exe,0", 1)
    with pytest.raises(locate.MalformedRegistrationError):
        locate.RegistryExecutableLocator(
            registry, is_executable=lambda path: "%" not in str(path)
        ).resolve("blender")


def test_lookup_preserves_denial_and_find_exe_fails_closed() -> None:
    registry = FakeRegistry()
    path = r"Software\Classes\blendfile\DefaultIcon"
    registry.values[
        (locate.RegistryHive.CURRENT_USER, path, locate.RegistryView.WOW64_64)
    ] = PermissionError(path)
    resolver = locate.RegistryExecutableLocator(registry)

    with pytest.raises(locate.RegistryAccessDeniedError):
        resolver.resolve("blender")
    assert locate.find_exe("unknown") is None


def test_lookup_rejects_unsupported_app_and_value_type() -> None:
    with pytest.raises(locate.UnsupportedApplicationError):
        locate.RegistryExecutableLocator(FakeRegistry()).resolve("imagemagick")
    registry = FakeRegistry()
    path = r"Software\Classes\blendfile\DefaultIcon"
    registry.values[
        (locate.RegistryHive.CURRENT_USER, path, locate.RegistryView.WOW64_64)
    ] = locate.RegistryValue(r"C:\Tools\blender.exe", 99)
    with pytest.raises(locate.MalformedRegistrationError):
        locate.RegistryExecutableLocator(registry).resolve("blender")


def test_native_registry_uses_read_only_view_and_closes_handle() -> None:
    calls: list[tuple] = []

    class Handle:
        pass

    handle = Handle()
    module = ModuleType("fake_winreg")
    attributes = {
        "REG_SZ": 1,
        "REG_EXPAND_SZ": 2,
        "HKEY_CURRENT_USER": "user",
        "HKEY_LOCAL_MACHINE": "machine",
        "HKEY_CLASSES_ROOT": "classes",
        "KEY_READ": 4,
        "KEY_WOW64_64KEY": 8,
        "KEY_WOW64_32KEY": 16,
        "OpenKey": lambda *args: calls.append(args) or handle,
        "QueryValueEx": lambda key, name: (r"C:\Tools\tool.exe", 1),
        "CloseKey": lambda key: calls.append(("close", key)),
        "ExpandEnvironmentStrings": lambda value: value.replace("%A%", "expanded"),
    }
    for name, item in attributes.items():
        setattr(module, name, item)
    registry = locate.NativeRegistry(module)

    with registry.open_key(
        locate.RegistryHive.LOCAL_MACHINE,
        "Software\\Classes\\tool",
        locate.RegistryView.WOW64_32,
    ) as key:
        value = key.query_value(None)

    assert value.data.endswith("tool.exe")
    assert calls[0][-1] == 20
    assert calls[-1] == ("close", handle)
    assert registry.expand_environment("%A%") == "expanded"


def test_native_key_rejects_non_string_value() -> None:
    class InvalidValueModule(ModuleType):
        def QueryValueEx(self, handle, name):
            return 4, 1

    module = InvalidValueModule("fake_winreg")
    with pytest.raises(locate.MalformedRegistrationError):
        locate._NativeKey(module, "handle").query_value(None)


def test_find_exe_is_lazy_and_does_not_swallow_programming_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imported: list[str] = []
    monkeypatch.setattr(
        locate.importlib,
        "import_module",
        lambda name: imported.append(name) or SimpleNamespace(),
    )
    resolution = locate.ExecutableResolution(
        "blender",
        Path(r"C:\Tools\blender.exe"),
        locate.RegistryHive.CURRENT_USER,
        locate.RegistryView.WOW64_64,
    )
    monkeypatch.setattr(
        locate.RegistryExecutableLocator, "resolve", lambda self, app: resolution
    )
    assert locate.find_exe("blender") == r"C:\Tools\blender.exe"
    assert imported == ["winreg"]
    monkeypatch.setattr(
        locate.RegistryExecutableLocator,
        "resolve",
        lambda self, app: (_ for _ in ()).throw(RuntimeError("bug")),
    )
    with pytest.raises(RuntimeError, match="bug"):
        locate.find_exe("blender")


def test_parsers_accept_conservative_quoted_and_unquoted_forms() -> None:
    assert (
        locate.parse_icon_executable(r'"C:\Program Files\Blender\blender.exe",-2')
        == r"C:\Program Files\Blender\blender.exe"
    )
    assert (
        locate.parse_command_executable(r"C:\Inkscape\inkscape.exe %1")
        == r"C:\Inkscape\inkscape.exe"
    )
    with pytest.raises(locate.MalformedRegistrationError):
        locate.parse_icon_executable("not an icon registration")


def test_lookup_reports_all_candidates_missing() -> None:
    with pytest.raises(locate.RegistryEntryNotFoundError):
        locate.RegistryExecutableLocator(FakeRegistry()).resolve("blender")


def test_find_exe_fails_closed_when_winreg_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        locate.importlib,
        "import_module",
        lambda name: (_ for _ in ()).throw(ModuleNotFoundError(name)),
    )
    assert locate.find_exe("blender") is None


def test_lookup_error_messages_are_nonempty(tmp_path: Path) -> None:
    errors = (
        locate.UnsupportedApplicationError("app"),
        locate.RegistryBackendUnavailableError("missing"),
        locate.RegistryEntryNotFoundError("app"),
        locate.RegistryAccessDeniedError("key"),
        locate.MalformedRegistrationError("value"),
        locate.NonExecutableRegistrationError(tmp_path),
    )
    assert all(str(error) for error in errors)
