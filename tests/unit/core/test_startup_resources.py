import locale
import sys
from types import SimpleNamespace

import pytest

from phatch.core import config
from phatch.core.user_paths import HostPlatform, PathResolution, resolve_user_paths
from phatch.lib import fonts


@pytest.fixture
def startup_paths(tmp_path, monkeypatch):
    resources = tmp_path / "resources"
    resources.mkdir()
    user_paths = resolve_user_paths(
        PathResolution({}, HostPlatform.LINUX, tmp_path / "portable")
    )
    config._set_user_paths(user_paths)
    monkeypatch.setattr(config, "PHATCH_DATA_PATH", str(resources))
    return resources, user_paths.geek


def test_explicit_startup_copies_valid_geek_resource(startup_paths):
    resources, user_geek = startup_paths
    (resources / "geek.txt").write_text("convert input output\n", encoding="utf-8")

    config.verify_app_user_paths()

    assert user_geek.read_text(encoding="utf-8") == "convert input output\n"


def test_explicit_startup_reports_missing_geek_resource(startup_paths):
    _, user_geek = startup_paths

    with pytest.raises(config.StartupResourceError, match="geek.txt"):
        config.verify_app_user_paths()

    assert not user_geek.exists()


def test_explicit_startup_reports_malformed_geek_resource(startup_paths):
    resources, user_geek = startup_paths
    (resources / "geek.txt").mkdir()

    with pytest.raises(config.StartupResourceError, match="geek.txt"):
        config.verify_app_user_paths()

    assert not user_geek.exists()


def test_explicit_startup_reports_atomic_geek_write_failure(startup_paths, monkeypatch):
    resources, user_geek = startup_paths
    (resources / "geek.txt").write_text("command\n", encoding="utf-8")

    def fail_atomic_write(destination, data):
        raise OSError("copy interrupted")

    monkeypatch.setattr(config, "atomic_write_bytes", fail_atomic_write)

    with pytest.raises(config.StartupResourceError) as caught:
        config.verify_app_user_paths()

    assert caught.value.destination == user_geek
    assert not user_geek.exists()


def test_installed_windows_paths_report_unsupported_platform(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")

    with pytest.raises(SystemExit):
        config.check_config_paths({})


def test_locale_detection_handles_unavailable_environment(monkeypatch):
    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(
        config.locale,
        "getlocale",
        lambda category=None: (_ for _ in ()).throw(ValueError()),
    )

    assert config._detect_default_locale() is None


def test_load_locale_handles_locale_error_and_base_language(monkeypatch):
    installed = []
    translation = SimpleNamespace(install=lambda: installed.append(True))
    monkeypatch.setattr(
        config.locale,
        "setlocale",
        lambda *args: (_ for _ in ()).throw(locale.Error()),
    )
    monkeypatch.setattr(
        config.gettext, "translation", lambda *args, **kwargs: translation
    )
    monkeypatch.setattr(config.glob, "glob", lambda pattern: [])

    config.load_locale("phatch", "", canonical="fr")

    assert installed == [True]


def test_init_config_paths_does_not_load_obsolete_pil_compatibility(monkeypatch):
    calls = []
    paths = {"PHATCH_PYTHON_PATH": "/phatch"}
    monkeypatch.setitem(
        sys.modules,
        "Image",
        SimpleNamespace(VERSION="1.1.6"),
    )
    monkeypatch.setattr(config, "check_config_paths", lambda value: paths)
    monkeypatch.setattr(config, "add_user_paths", lambda value: None)
    monkeypatch.setattr(
        config,
        "fix_python_path",
        lambda path=None: calls.append(path) or "/phatch",
    )
    monkeypatch.setattr(fonts, "set_font_cache", lambda *args: None)

    assert config.init_config_paths({}) is paths
    assert calls == ["/phatch", config.USER_ACTIONS_PATH]
