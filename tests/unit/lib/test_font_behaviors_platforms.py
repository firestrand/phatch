from __future__ import annotations

import importlib
import importlib.util
import io
import subprocess
import sys
from types import ModuleType

import pytest

from phatch.lib import fonts

findsystem = importlib.import_module("other.findsystem")


def load_fonts_for_platform(
    monkeypatch: pytest.MonkeyPatch, platform: str
) -> ModuleType:
    monkeypatch.setattr(sys, "platform", platform)
    module_name = f"phatch.lib._fonts_{platform}_test"
    spec = importlib.util.spec_from_file_location(module_name, fonts.__file__)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_macos_collection_uses_only_configured_directory_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: deterministic results for the current macOS collector
    observed: list[list[str]] = []

    def collect(directories: list[str]) -> list[str]:
        observed.append(directories)
        return ["/fonts/FreeSans.ttf"]

    monkeypatch.setattr(fonts, "collect_fonts_from_dirs", collect)

    # When: platform font discovery runs
    discovered = fonts.collect_fonts()

    # Then: only the declared macOS roots are passed to recursive discovery
    assert discovered == ["/fonts/FreeSans.ttf"]
    assert observed == [fonts.MACOS_FONT_DIRS]


def test_linux_collection_prefers_known_directories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a Linux-loaded module with a font in a known directory
    module = load_fonts_for_platform(monkeypatch, "linux")
    monkeypatch.setattr(
        module,
        "collect_fonts_from_dirs",
        lambda directories: ["/fonts/Known.ttf"],
    )

    # When: Linux font discovery runs
    discovered = module.collect_fonts()

    # Then: subprocess fallback is unnecessary
    assert discovered == ["/fonts/Known.ttf"]


def test_linux_collection_filters_subprocess_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: no directory fonts and mixed locate output
    module = load_fonts_for_platform(monkeypatch, "linux")
    monkeypatch.setattr(module, "collect_fonts_from_dirs", lambda directories: [])
    monkeypatch.setattr(
        module,
        "locate_files",
        lambda command: [b"/fonts/A.TTF", b"/tmp/readme.txt"],
    )
    monkeypatch.setattr(module.system, "find_exe", lambda executable: True)

    # When: subprocess fallback discovery runs
    discovered = module.collect_fonts()

    # Then: only supported font extensions are returned
    assert discovered == [b"/fonts/A.TTF"]


def test_linux_collection_uses_final_platform_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: no known-directory fonts and no locate executable
    module = load_fonts_for_platform(monkeypatch, "linux")
    monkeypatch.setattr(module, "collect_fonts_from_dirs", lambda directories: [])
    monkeypatch.setattr(module.system, "find_exe", lambda executable: False)
    monkeypatch.setattr(findsystem, "findFonts", lambda: ["/fallback/Font.ttf"])

    # When: all primary discovery routes are exhausted
    discovered = module.collect_fonts()

    # Then: the legacy platform provider supplies the result
    assert discovered == ["/fallback/Font.ttf"]


def test_locate_files_reads_subprocess_stdout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a Linux-loaded module and a subprocess with byte output
    module = load_fonts_for_platform(monkeypatch, "linux")

    class Process:
        stdout = io.BytesIO(b"/fonts/A.ttf\n/fonts/B.otf\n")

    monkeypatch.setattr(subprocess, "Popen", lambda command, stdout: Process())

    # When: the locate adapter reads process output
    discovered = module.locate_files(["locate", ".ttf"])

    # Then: subprocess lines remain discrete paths for later decoding
    assert discovered == [b"/fonts/A.ttf", b"/fonts/B.otf"]


def test_windows_collection_delegates_to_findsystem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a Windows-loaded module with deterministic system discovery
    monkeypatch.setattr(findsystem, "findFonts", lambda: ["C:/Fonts/Arial.ttf"])
    module = load_fonts_for_platform(monkeypatch, "win32")

    # When: Windows font discovery runs
    discovered = module.collect_fonts()

    # Then: the platform provider result is returned unchanged
    assert discovered == ["C:/Fonts/Arial.ttf"]


def test_linux_collection_continues_after_failed_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: one failing command followed by a successful font locator
    module = load_fonts_for_platform(monkeypatch, "linux")
    monkeypatch.setattr(module, "collect_fonts_from_dirs", lambda directories: [])
    monkeypatch.setattr(module.system, "find_exe", lambda executable: True)
    outputs = iter((OSError("failed"), [b"/fonts/Recovered.otf"]))

    def locate(command: list[str]) -> list[bytes]:
        result = next(outputs)
        if isinstance(result, OSError):
            raise result
        return result

    monkeypatch.setattr(module, "locate_files", locate)

    # When: Linux discovery tries each configured command
    discovered = module.collect_fonts()

    # Then: a failure does not prevent the next command from succeeding
    assert discovered == [b"/fonts/Recovered.otf"]


def test_font_dictionary_filters_non_display_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a filename normalizer producing a lowercase internal name
    monkeypatch.setattr(fonts, "name", lambda value: "internal")

    # When: the display dictionary is built
    discovered = fonts._font_dictionary(["hidden.ttf"])

    # Then: names not beginning with an uppercase display character are omitted
    assert discovered == {}
