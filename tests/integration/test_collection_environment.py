from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

SANDBOX_ENVIRONMENT_KEYS = (
    "HOME",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "XDG_DATA_HOME",
    "XDG_CONFIG_HOME",
    "XDG_CACHE_HOME",
    "XDG_RUNTIME_DIR",
    "TMPDIR",
    "TEMP",
    "TMP",
    "PHATCH_PORTABLE_ROOT",
)


def test_thumbnail_import_does_not_create_cache_directories(
    isolated_runtime,
) -> None:
    # Given: a sentinel home with an existing freedesktop normal cache
    normal = isolated_runtime.home / ".thumbnails" / "normal"
    normal.mkdir(parents=True)
    before = sorted(isolated_runtime.root.rglob("*"))

    # When: thumbnail is imported in a fresh process
    result = subprocess.run(
        [sys.executable, "-c", "import phatch.lib.thumbnail"],
        cwd=isolated_runtime.cwd,
        env=isolated_runtime.env,
        capture_output=True,
        text=True,
        check=False,
    )

    # Then: import succeeds without creating any filesystem entry
    assert result.returncode == 0, result.stderr
    assert sorted(isolated_runtime.root.rglob("*")) == before


def test_collection_environment_is_sandboxed_and_restored(
    isolated_runtime, project_root: Path, tmp_path: Path
) -> None:
    # Given: a test module that captures process paths during collection
    driver = tmp_path / "test_collection_driver.py"
    driver.write_text(
        "\n".join(
            [
                "import os",
                "from pathlib import Path",
                f"KEYS = {SANDBOX_ENVIRONMENT_KEYS!r}",
                "ROOT = Path(os.environ['PHATCH_TEST_ROOT'])",
                "COLLECTED = {key: Path(os.environ[key]) for key in KEYS}",
                "",
                "def test_paths_are_inside_collection_sandbox():",
                "    assert all(",
                "        path.is_relative_to(ROOT) for path in COLLECTED.values()",
                "    )",
                "    assert all(path.exists() for path in COLLECTED.values())",
            ]
        ),
        encoding="utf-8",
    )
    parent_environment = {
        key: isolated_runtime.env.get(key) for key in SANDBOX_ENVIRONMENT_KEYS
    }
    wrapper = "\n".join(
        [
            "import os",
            "import pytest",
            f"keys = {SANDBOX_ENVIRONMENT_KEYS!r}",
            "before = {key: os.environ.get(key) for key in keys}",
            "status = pytest.main([",
            "    '-q',",
            "    '-p',",
            "    'tests.conftest',",
            f"    '--rootdir={project_root}',",
            f"    {str(driver)!r},",
            "])",
            "after = {key: os.environ.get(key) for key in keys}",
            "assert status == pytest.ExitCode.OK, status",
            "assert after == before, (before, after)",
        ]
    )

    # When: pytest loads the root plugin and collects the driver
    result = subprocess.run(
        [sys.executable, "-c", wrapper],
        cwd=project_root,
        env=isolated_runtime.env,
        capture_output=True,
        text=True,
        check=False,
    )

    # Then: collection passes and the parent environment remains unchanged
    assert result.returncode == 0, result.stdout + result.stderr
    assert {
        key: isolated_runtime.env.get(key) for key in SANDBOX_ENVIRONMENT_KEYS
    } == parent_environment


def test_collection_environment_is_restored_after_session_finish_error(
    isolated_runtime, project_root: Path, tmp_path: Path
) -> None:
    # Given: a collection plugin that raises after observing the sandbox
    driver = tmp_path / "test_session_finish_driver.py"
    driver.write_text("def test_collected():\n    assert True\n", encoding="utf-8")
    plugin = tmp_path / "raising_session_plugin.py"
    plugin.write_text(
        "\n".join(
            [
                "import os",
                "",
                "def pytest_sessionfinish(session, exitstatus):",
                "    assert 'PHATCH_TEST_ROOT' in os.environ",
                "    raise RuntimeError('session finish sentinel')",
            ]
        ),
        encoding="utf-8",
    )
    environment = isolated_runtime.env.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(tmp_path), str(project_root)]
    )
    wrapper = "\n".join(
        [
            "import os",
            "import pytest",
            f"keys = {SANDBOX_ENVIRONMENT_KEYS!r}",
            "before = {key: os.environ.get(key) for key in keys}",
            "error = None",
            "try:",
            "    pytest.main([",
            "        '-q',",
            "        '-p',",
            "        'tests.conftest',",
            "        '-p',",
            "        'raising_session_plugin',",
            f"        '--rootdir={project_root}',",
            f"        {str(driver)!r},",
            "    ])",
            "except RuntimeError as caught:",
            "    error = str(caught)",
            "after = {key: os.environ.get(key) for key in keys}",
            "assert error == 'session finish sentinel', error",
            "assert after == before, (before, after)",
        ]
    )

    # When: session finish raises after test execution
    result = subprocess.run(
        [sys.executable, "-c", wrapper],
        cwd=project_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    # Then: pytest unconfigure still restores the complete environment snapshot
    assert result.returncode == 0, result.stdout + result.stderr


def test_isolated_runtime_environment_remains_per_test(isolated_runtime) -> None:
    # Given: the existing per-test runtime environment mapping
    environment_paths = [
        Path(isolated_runtime.env[key]) for key in SANDBOX_ENVIRONMENT_KEYS
    ]

    # When: its configured locations are resolved
    resolved = [path.resolve() for path in environment_paths]

    # Then: every location remains owned by this test's temporary root
    assert all(path.is_relative_to(isolated_runtime.root) for path in resolved)


def test_thumbnail_cache_directories_are_created_only_when_saving(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Given: cache destinations that do not exist after module import
    from phatch.lib import thumbnail

    source = tmp_path / "source.png"
    Image.new("RGB", (4, 4), "red").save(source)
    cache_paths = {
        "normal": tmp_path / "cache" / "normal",
        "large": tmp_path / "cache" / "large",
    }
    monkeypatch.setattr(thumbnail, "FREEDESKTOP_PATH", cache_paths)

    # When: cache persistence is explicitly requested
    with Image.open(source) as image:
        thumbnail.save_to_cache(str(source), image=image)

    # Then: both cache buckets are initialized at the write boundary
    assert all(path.is_dir() for path in cache_paths.values())
