from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

from phatch.services.field_presentation import FieldPresentationError
from phatch.services.field_presentation_audit import audit_builtin_presentations
from scripts import audit_field_presentation

EXPECTED_CONDITIONAL_SOURCES = frozenset(
    {
        "_blender_action.py",
        "_imagemagick_action.py",
        "_lossless_jpeg_options.py",
        "background.py",
        "border.py",
        "color_to_alpha.py",
        "delete_tags.py",
        "geek.py",
        "grid.py",
        "lossless_jpeg.py",
        "perspective.py",
        "reflection.py",
        "round.py",
        "save.py",
        "tamogen.py",
        "text.py",
        "time_shift.py",
    }
)


def test_source_inventory_discovers_all_conditional_implementations(
    project_root: Path,
) -> None:
    audit = audit_builtin_presentations(project_root / "phatch" / "actions")

    assert audit.conditional_sources == EXPECTED_CONDITIONAL_SOURCES
    assert audit.conditional_source_count == len(audit.conditional_sources)


def test_reachable_runtime_branch_inventory_exposes_every_conditional_field(
    project_root: Path,
) -> None:
    audit = audit_builtin_presentations(project_root / "phatch" / "actions")

    assert audit.conditional_action_count > audit.conditional_source_count
    assert audit.branch_count > audit.conditional_action_count
    assert audit.uncovered_conditional_fields == ()
    assert audit.unvisited_controller_values == ()


def test_dynamic_choice_families_are_exercised_without_running_actions(
    project_root: Path,
) -> None:
    audit = audit_builtin_presentations(project_root / "phatch" / "actions")

    assert audit.visited_values[("blender", "object")] == frozenset(
        {"Book", "Box", "Can", "Cd", "Lcd", "Sphere"}
    )
    assert audit.visited_values[("imagemagick", "action")] == frozenset(
        {
            "3D Edge",
            "Blur",
            "Bullet",
            "Charcoal",
            "Motion Blur",
            "Paint",
            "Pencil Sketch",
            "Polaroid",
            "Shadow",
            "Sharpen",
            "Sigmoidal Contrast",
            "Unsharp",
            "Wave",
        }
    )
    assert audit.visited_values[("lossless_jpeg", "utility")] == frozenset(
        {"Exiftran (with exif support)", "Jpegtran (without exif support)"}
    )
    assert "User" in audit.visited_values[("perspective", "projection")]


def test_crop_branch_inventory_preserves_all_auto_and_custom_sets(
    project_root: Path,
) -> None:
    audit = audit_builtin_presentations(project_root / "phatch" / "actions")

    assert audit.relevant_sets["crop"] == frozenset(
        {
            ("mode", "all"),
            ("mode",),
            ("mode", "top", "left", "bottom", "right"),
        }
    )


def test_inventory_cli_reports_runtime_counts(
    project_root: Path,
    capsys,
) -> None:
    exit_code = audit_field_presentation.main(
        ("--actions-root", str(project_root / "phatch" / "actions"))
    )

    output = capsys.readouterr()
    assert exit_code == 0
    assert (
        "crop.all: pixel; preset=editable; units=px,%,cm,mm,inch; basis=average"
        in output.out
    )
    assert output.out.endswith(
        "54 actions, 290 fields, 17 conditional sources, "
        "294 runtime branches; exhaustive\n"
    )
    assert output.err == ""


def test_inventory_cli_rejects_unknown_action_fixture(
    tmp_path: Path,
    capsys,
) -> None:
    (tmp_path / "unknown.py").write_text(
        "class Action:\n    label = 'Unknown'\n",
        encoding="utf-8",
    )

    exit_code = audit_field_presentation.main(("--actions-root", str(tmp_path)))

    output = capsys.readouterr()
    assert exit_code == 2
    assert "unknown.*" in output.err


def test_inventory_cli_reports_descriptor_errors(monkeypatch, capsys) -> None:
    def fail(_actions_root: Path):
        raise FieldPresentationError("sample", "field", "unsupported descriptor")

    monkeypatch.setattr(audit_field_presentation, "audit_builtin_presentations", fail)

    assert audit_field_presentation.main(()) == 2
    assert "unsupported descriptor" in capsys.readouterr().err


def test_inventory_cli_script_exits_through_main(monkeypatch) -> None:
    script = Path(audit_field_presentation.__file__)
    monkeypatch.setattr(sys, "argv", [str(script), "--help"])

    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(str(script), run_name="__main__")

    assert exit_info.value.code == 0
