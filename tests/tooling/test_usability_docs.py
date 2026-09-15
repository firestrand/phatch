from __future__ import annotations

import configparser
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]
USABILITY_GUIDE = PROJECT_ROOT / "docs" / "usability_050.md"
RECIPE_ROOT = PROJECT_ROOT / "phatch_assets" / "data" / "actionlists"


def _table_rows(markdown: str, heading: str) -> list[list[str]]:
    section = markdown.split(f"## {heading}", 1)[1].split("\n## ", 1)[0]
    rows = []
    for line in section.splitlines():
        if not line.startswith("|") or re.fullmatch(r"[| :\-]+", line):
            continue
        rows.append([cell.strip().strip("`") for cell in line.strip("|").split("|")])
    return rows[1:]


def test_readme_links_to_the_complete_candidate_guide() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "docs/usability_050.md" in readme
    assert USABILITY_GUIDE.is_file()


def test_six_workflows_reference_real_packaged_resources() -> None:
    guide = USABILITY_GUIDE.read_text(encoding="utf-8")
    rows = _table_rows(guide, "Starter workflows")

    assert [row[0] for row in rows] == [
        "resize-export",
        "crop-scale",
        "watermark",
        "metadata-preserving-export",
        "web-size-export",
        "droplet-resize",
    ]
    assert [row[1] for row in rows] == [
        "resize.phatch",
        "crop_scale.phatch",
        "watermark.phatch",
        "metadata_preserving_export.phatch",
        "web_size_export.phatch",
        "resize.phatch",
    ]
    assert all((RECIPE_ROOT / row[1]).is_file() for row in rows)
    assert (RECIPE_ROOT / "watermark.png").is_file()


def test_shortcut_table_matches_native_accelerators() -> None:
    guide = USABILITY_GUIDE.read_text(encoding="utf-8")
    rows = _table_rows(guide, "Keyboard shortcuts")

    assert rows == [
        ["Undo action-list edit", "Command-Z", "Ctrl-Z"],
        ["Redo action-list edit", "Command-Shift-Z", "Ctrl-Shift-Z or Ctrl-Y"],
    ]


def test_report_migration_documents_the_machine_contract() -> None:
    guide = USABILITY_GUIDE.read_text(encoding="utf-8")
    schema = (PROJECT_ROOT / "docs" / "action_list_schema.md").read_text(
        encoding="utf-8"
    )

    for token in (
        "--report-version 2",
        "--report-version 1",
        "report_version",
        "processed",
        "skipped",
        "failed",
        "cancelled",
        "survived",
        "<input>",
        "<output>",
        "<home>",
        "<temp>",
        "<redacted>",
    ):
        assert token in guide
    assert "schema version 3" in schema
    assert "report_version: 2" in schema


def test_ubuntu_commands_are_user_local_space_safe_and_reversible() -> None:
    guide = USABILITY_GUIDE.read_text(encoding="utf-8")

    for token in (
        'INSTALL_ROOT="$HOME/.local/Phatch 0.5"',
        '"$INSTALL_ROOT/bin/phatch-gui"',
        'XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"',
        '"$XDG_DATA_HOME/applications/phatch.desktop"',
        '"$XDG_DATA_HOME/icons/hicolor/scalable/apps/phatch.svg"',
        "desktop-file-install",
        "gtk-launch phatch",
        'rm -rf "$INSTALL_ROOT"',
        'rm -f "$XDG_DATA_HOME/applications/phatch.desktop"',
        'rm -f "$XDG_DATA_HOME/icons/hicolor/scalable/apps/phatch.svg"',
    ):
        assert token in guide


def test_desktop_entry_uses_the_gui_entry_point() -> None:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(PROJECT_ROOT / "linux" / "phatch.desktop", encoding="utf-8")

    assert parser["Desktop Entry"]["Exec"] == "phatch-gui %U"
    assert parser["Desktop Entry"]["Icon"] == "phatch"
    assert (PROJECT_ROOT / "phatch_assets/images/icons/scalable/phatch.svg").is_file()


def test_support_matrix_does_not_overstate_candidate_artifacts() -> None:
    guide = USABILITY_GUIDE.read_text(encoding="utf-8")
    rows = _table_rows(guide, "Platform status")

    assert rows == [
        ["Ubuntu 24.04", "Source or local candidate wheel", "Task 20 verified"],
        ["macOS 14+ Apple silicon", "Published 0.4.0 ZIP", "Ad-hoc signed"],
        ["Windows", "Source only", "Native 0.5 verification deferred"],
    ]
    assert "releases/tag/v0.5" not in guide
