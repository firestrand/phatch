from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import pytest

from phatch.lib import system


def test_text_and_path_helpers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    local_file = tmp_path / "holiday-photo.JPG"
    local_file.write_text("photo", encoding="utf-8")

    assert system.wrap("one two three", fill=4) == "one two three"
    assert system.title("hello_world-test") == "Hello World Test"
    assert system.is_www_file("http://example.com/photo.jpg")
    assert system.is_www_file("ftp://example.com/photo.jpg")
    assert not system.is_www_file("photo.jpg")
    assert system.is_file(local_file)
    assert system.is_file("http://example.com/photo.jpg")
    assert not system.is_file(str(tmp_path / "missing.jpg"))
    assert system.file_extension(local_file) == "jpg"
    assert system.filename_to_title(local_file) == "Holiday Photo"

    nested = tmp_path / "parent" / "child"
    system._ensure_path(nested)
    assert nested.is_dir()
    monkeypatch.setattr(system.os.path, "exists", lambda path: False)
    with pytest.raises(OSError, match="not valid"):
        system._ensure_path("relative")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("blender", "blender"),
        (b"my program", '"my program"'),
        ("my program", '"my program"'),
        ('my "program" path', "'my \"program\" path'"),
        ('my "program\'s" path', '"my \\"program\'s\\" path"'),
    ],
)
def test_fix_quotes(value: str | bytes, expected: str) -> None:
    assert system.fix_quotes(value) == expected


def test_binary_path_registry_and_search(tmp_path: Path) -> None:
    executable = tmp_path / "tool"
    executable.write_text("", encoding="utf-8")

    system.set_bin_paths([str(tmp_path)])

    assert [str(tmp_path)] == system.BIN
    assert system.find_in("tool", system.BIN) == str(executable)
    assert system.find_in("missing", system.BIN) is None


def test_find_exe_finds_quotes_without_caching_binary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binary_dir = tmp_path / "program files"
    binary_dir.mkdir()
    binary = binary_dir / "tool"
    binary.write_text("", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.setattr(system, "BIN", [str(binary_dir)])
    first = system.find_exe("tool", use_which=False)
    binary.unlink()
    second = system.find_exe("tool", use_which=False)

    assert first == f'"{binary}"'
    assert second is None


def test_find_exe_uses_which_then_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binary = tmp_path / "tool"
    binary.write_text("", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.setattr(system, "BIN", [])
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr(
        system.shutil,
        "which",
        lambda executable, path=None: str(binary) if path == str(tmp_path) else None,
    )

    assert system.find_exe("tool", quote=False) == str(binary)


def test_find_exe_supports_windows_locator_and_required_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(system, "WINDOWS", True)
    monkeypatch.setattr(system, "_EXE", ".exe")
    monkeypatch.setattr(system, "BIN", [])
    monkeypatch.setattr(system, "find_in", lambda executable, paths: None)
    binary = tmp_path / "tool.exe"
    binary.write_text("", encoding="utf-8")
    binary.chmod(0o755)
    windows_locator = SimpleNamespace(find_exe=lambda executable: str(binary))
    monkeypatch.setattr(system, "windows_locate", windows_locator)
    assert system.find_exe("tool", use_which=False, quote=False) == str(binary)

    monkeypatch.setattr(windows_locator, "find_exe", lambda executable: None)
    with pytest.raises(OSError, match="No such program"):
        system.find_exe("missing", use_which=False, raise_exception=True)


def test_command_parsing() -> None:
    assert system.find_command('"/my apps/tool" image.jpg') == '"/my apps/tool"'
    assert system.find_command("") is None
    assert system.split_command('"/my apps/tool" image.jpg') == [
        '"/my apps/tool"',
        "image.jpg",
    ]


def test_temp_file_close_removes_moves_and_guards_state(tmp_path: Path) -> None:
    temporary = system.TempFile(".tmp")
    generated_path = Path(temporary.path)
    assert generated_path.exists()
    temporary.close()
    assert not generated_path.exists()
    with pytest.raises(OSError, match="already closed"):
        temporary.close()

    source = tmp_path / "source.tmp"
    destination = tmp_path / "destination.tmp"
    source.write_text("content", encoding="utf-8")
    supplied = system.TempFile(path=str(source))
    supplied.close(dest=str(destination))
    assert destination.read_text(encoding="utf-8") == "content"

    missing = system.TempFile(path=str(tmp_path / "missing.tmp"))
    missing.close(force_remove=False)


def test_shell_and_returncode_delegate_to_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pipe = SimpleNamespace(stdout=io.BytesIO(b"out"), stderr=io.BytesIO(b"err"))
    popen_calls: list[tuple] = []
    call_options: list[dict] = []
    monkeypatch.setattr(
        system.subprocess,
        "Popen",
        lambda *args, **options: popen_calls.append((args, options)) or pipe,
    )
    monkeypatch.setattr(
        system.subprocess,
        "call",
        lambda *args, **options: call_options.append(options) or 7,
    )

    assert system.shell(["tool"]) == (b"out", b"err")
    assert system.shell_returncode(["tool"]) == 7
    assert popen_calls[0][1]["stdout"] is system.subprocess.PIPE
    assert call_options[0]["stderr"] is system.subprocess.PIPE


class _MemoryFile:
    def __init__(self, source: bytes = b"") -> None:
        self.source = source
        self.written: str | bytes | None = None

    def read(self) -> bytes:
        return self.source

    def write(self, value: str | bytes) -> None:
        self.written = value

    def close(self) -> None:
        return None


def test_shell_cache_writes_missing_result(monkeypatch: pytest.MonkeyPatch) -> None:
    output = _MemoryFile()
    monkeypatch.setattr(system.os.path, "isfile", lambda path: False)
    monkeypatch.setattr(system, "shell", lambda args, **options: (b"out", b"err"))
    monkeypatch.setattr(system, "ensure_path", lambda path: None)
    monkeypatch.setattr("builtins.open", lambda path, mode: output)

    result = system.shell_cache(["tool"], cache="/cache/results", validate=3)

    assert result == (b"out", b"err")
    assert output.written is not None


@pytest.mark.parametrize("validate", [None, 3])
def test_shell_cache_reads_valid_cached_result(
    validate: int | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cached = {
        ("tool",): {
            system.sys.platform: {
                "validate": 3,
                "stdout": b"cached",
                "stderr": b"",
            }
        }
    }
    monkeypatch.setattr(system.os.path, "isfile", lambda path: True)
    monkeypatch.setattr("builtins.open", lambda path, mode: _MemoryFile(b"cache"))
    monkeypatch.setattr(system.safe, "eval_safe", lambda source: cached)
    monkeypatch.setattr(
        system,
        "shell",
        lambda args, **options: pytest.fail("cached command should not run"),
    )

    assert system.shell_cache(["tool"], cache="cache", validate=validate) == (
        b"cached",
        b"",
    )


def test_shell_cache_recovers_from_invalid_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _MemoryFile()
    monkeypatch.setattr(system.os.path, "isfile", lambda path: True)
    monkeypatch.setattr("builtins.open", lambda path, mode: output)
    monkeypatch.setattr(
        system.safe, "eval_safe", lambda source: (_ for _ in ()).throw(SyntaxError)
    )
    monkeypatch.setattr(system, "shell", lambda args, **options: (b"fresh", b""))
    monkeypatch.setattr(system, "ensure_path", lambda path: None)

    assert system.shell_cache(["tool"], cache="cache", key="key") == (b"fresh", b"")


def test_call_configures_shell_splitting_and_verbose_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[object, dict]] = []
    monkeypatch.setattr(
        system.subprocess, "call", lambda args, **values: calls.append((args, values))
    )
    monkeypatch.setattr(system, "WINDOWS", False)
    monkeypatch.setattr(system, "VERBOSE", False)

    system.call("tool first\\\n second", shell=False, verbose=True)
    system.call(["tool"], verbose=False)

    assert calls[0] == (["tool", "first", "second"], {"shell": False})
    assert calls[1] == (["tool"], {"shell": True})
    assert "tool" in capsys.readouterr().out


def test_start_uses_platform_launcher(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []
    monkeypatch.setattr(
        system.os, "startfile", lambda path: calls.append(path), raising=False
    )
    system.start("photo.jpg")
    assert calls == ["photo.jpg"]

    monkeypatch.delattr(system.os, "startfile")
    monkeypatch.setattr(
        system.subprocess, "call", lambda command, shell: calls.append(command)
    )
    monkeypatch.setattr(system.sys, "platform", "darwin")
    system.start("photo.jpg")
    monkeypatch.setattr(system.sys, "platform", "linux")
    system.start("photo.jpg")
    assert calls[-2:] == ['open "photo.jpg"', 'xdg-open "photo.jpg"']


def test_method_register_tracks_and_unregisters_relationships() -> None:
    register = system.MethodRegister()

    register.register(["jpg", "png"], abs)
    register.register(["png"], str)
    register.register(["gif"], None)
    assert register.does_process("photo.JPG")
    assert register.get_methods("png") == [abs, str]
    assert register.get_methods("gif") == []

    register.unregister_method(abs)
    assert register.get_methods("jpg") == []
    assert register.get_methods("png") == [str]
    register.unregister_extension("png")
    assert register.extensions == []
    register.unregister_extension("missing")
