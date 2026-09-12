from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from phatch import app
from phatch.lib import system


def test_importing_config_resolves_paths_without_creating_them(tmp_path: Path) -> None:
    # Given
    home = tmp_path / "home"
    home.mkdir()
    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(home),
            "XDG_CACHE_HOME": str(tmp_path / "cache"),
            "XDG_CONFIG_HOME": str(tmp_path / "config"),
            "XDG_DATA_HOME": str(tmp_path / "data"),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    script = (
        "import json; from phatch.core import config; "
        "print(json.dumps([config.USER_CONFIG_PATH, config.USER_DATA_PATH, "
        "config.USER_CACHE_PATH]))"
    )

    # When
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )

    # Then
    resolved = tuple(json.loads(completed.stdout))
    assert resolved == ("", "", "")
    assert tuple(tmp_path.iterdir()) == (home,)


def test_fix_path_preserves_ordinary_paths_and_decodes_simple_file_uri() -> None:
    # Given
    ordinary = "photos/holiday image.jpg"
    file_uri = "file:///tmp/holiday%20image.jpg"

    # When
    ordinary_result = app.fix_path(ordinary)
    uri_result = app.fix_path(file_uri)

    # Then
    assert ordinary_result == ordinary
    assert uri_result == "/tmp/holiday image.jpg"


def test_ensure_path_creates_nested_directory(tmp_path: Path) -> None:
    # Given
    destination = tmp_path / "one/two"

    # When
    system.ensure_path(destination)

    # Then
    assert destination.is_dir()


def test_rename_replaces_destination_on_host(tmp_path: Path) -> None:
    # Given
    source = tmp_path / "source.txt"
    destination = tmp_path / "destination.txt"
    source.write_text("new", encoding="utf-8")
    destination.write_text("old", encoding="utf-8")

    # When
    system.rename(source, destination)

    # Then
    assert destination.read_text(encoding="utf-8") == "new"
    assert not source.exists()
