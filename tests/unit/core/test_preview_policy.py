from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from re import findall
from types import SimpleNamespace

import pytest

from phatch.services import preview_policy
from phatch.services.preview_policy import (
    PREVIEW_POLICIES,
    AdapterKind,
    PolicyKind,
    PreviewAction,
    PreviewPolicyViolation,
    ReadKind,
    admit_preview_actions,
    policy_for,
)
from scripts.audit_preview_policy import (
    ActionAuditError,
    audit_action_sources,
    discover_action_sources,
    main,
)

ELIGIBLE_IDS = frozenset(
    findall(
        r"[a-z_]+",
        "auto_contrast background border brightness canvas color_to_alpha "
        "colorize common contour contrast convert_mode crop desaturate effect "
        "equalize fit grid highlight invert mask maximum median minimum mirror "
        "offset perspective posterize rank reflection rotate round saturation "
        "scale shadow sketch solarize text transpose warm_up watermark",
    )
)

BLOCKED_REASONS = {
    "blender": "external process/temp output",
    "copy": "file write",
    "delete_tags": "metadata mutation",
    "geek": "arbitrary process",
    "geotag": "metadata/report I/O",
    "imagemagick": "external process",
    "lossless_jpeg": "file mutation",
    "rename": "source rename",
    "rename_tag": "metadata mutation",
    "save_tags": "metadata file output",
    "tamogen": "folder/content-dependent reads",
    "time_shift": "metadata/file-date mutation",
    "write_tag": "metadata mutation",
}


def test_manifest_has_exact_policy_partition() -> None:
    eligible = {
        action_id
        for action_id, policy in PREVIEW_POLICIES.items()
        if policy.kind is PolicyKind.ELIGIBLE
    }
    blocked = {
        action_id
        for action_id, policy in PREVIEW_POLICIES.items()
        if policy.kind is PolicyKind.BLOCKED
    }
    terminal = {
        action_id
        for action_id, policy in PREVIEW_POLICIES.items()
        if policy.kind is PolicyKind.TERMINAL_SAVE
    }

    assert eligible == ELIGIBLE_IDS
    assert blocked == set(BLOCKED_REASONS)
    assert terminal == {"save"}
    assert len(PREVIEW_POLICIES) == 54


@pytest.mark.parametrize(("action_id", "reason"), BLOCKED_REASONS.items())
def test_blocked_policy_declares_exact_reason(action_id: str, reason: str) -> None:
    policy_reason = policy_for(action_id).reason

    assert policy_reason is not None
    assert policy_reason.message == reason
    assert str(policy_reason) == reason


def test_manifest_declares_conditional_reads_and_prebinding_adapters() -> None:
    background = policy_for("background")

    assert background.reads[0].field_id == "mark"
    assert background.reads[0].kind is ReadKind.PACKAGED_OR_SELECTED_FILE
    assert background.reads[0].condition is not None
    assert background.reads[0].condition.field_id == "fill"
    assert background.reads[0].condition.equals == "Image"
    assert background.adapters[0].field_id == "mark"
    assert background.adapters[0].kind is AdapterKind.FILE_REFERENCE

    expected_reads = {
        "highlight": "highlight",
        "mask": "mask",
        "text": "font",
        "watermark": "mark",
    }
    assert {
        action_id: policy_for(action_id).reads[0].field_id
        for action_id in expected_reads
    } == expected_reads
    assert policy_for("perspective").reads == ()
    assert policy_for("perspective").adapters[0].field_id == "projection"
    assert policy_for("perspective").adapters[0].kind is AdapterKind.PACKAGED_CATALOG


def test_policy_records_and_manifest_are_immutable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(TypeError):
        monkeypatch.setitem(PREVIEW_POLICIES, "new", policy_for("scale"))
    monkeypatch._setitem.pop()
    policy = policy_for("scale")
    with pytest.raises(FrozenInstanceError):
        policy.__setattr__("reason", None)


def test_unknown_id_is_rejected_even_when_disabled() -> None:
    with pytest.raises(PreviewPolicyViolation, match="unknown action ID: custom"):
        admit_preview_actions((PreviewAction("custom", enabled=False),))


def test_disabled_blocked_action_is_ignored_after_id_validation() -> None:
    result = admit_preview_actions(
        (PreviewAction("copy", enabled=False), PreviewAction("scale"))
    )

    assert result.action_ids == ("scale",)
    assert result.omitted_terminal_save is False


@pytest.mark.parametrize(
    ("actions", "message"),
    [
        ((PreviewAction("copy"),), "copy: file write"),
        (
            (PreviewAction("save"), PreviewAction("scale")),
            "save must be the final enabled action",
        ),
        (
            (PreviewAction("save"), PreviewAction("save")),
            "preview accepts at most one enabled save",
        ),
    ],
)
def test_sequence_admission_rejects_blocked_and_invalid_save_rules(
    actions: tuple[PreviewAction, ...], message: str
) -> None:
    with pytest.raises(PreviewPolicyViolation, match=message):
        admit_preview_actions(actions)


def test_blocked_policy_without_reason_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        preview_policy,
        "policy_for",
        lambda action_id: SimpleNamespace(
            action_id=action_id,
            enabled=True,
            kind=PolicyKind.BLOCKED,
            reason=None,
        ),
    )

    with pytest.raises(PreviewPolicyViolation, match="blocked from preview"):
        admit_preview_actions((PreviewAction("scale"),))


def test_terminal_save_is_omitted_from_admitted_action_ids() -> None:
    result = admit_preview_actions((PreviewAction("scale"), PreviewAction("save")))

    assert result.action_ids == ("scale",)
    assert result.omitted_terminal_save is True


def test_ast_audit_covers_current_primary_action_sources(project_root: Path) -> None:
    result = audit_action_sources(project_root / "phatch" / "actions")

    assert result.covered == 54
    assert result.total == 54
    assert result.missing_policy_ids == frozenset()
    assert result.stale_policy_ids == frozenset()
    assert {source.action_id for source in result.sources} == set(PREVIEW_POLICIES)


def test_ast_discovery_reads_alias_wrappers_without_executing_source(
    tmp_path: Path,
) -> None:
    source = tmp_path / "wrapped.py"
    source.write_text(
        "from nowhere import translate as alias\n"
        "raise RuntimeError('must not execute')\n"
        "class Other:\n"
        "    label = alias('Hidden')\n"
        "class Action(Wrapper):\n"
        "    init = staticmethod(init)\n"
        "    label = alias('Fixture Action')\n",
        encoding="utf-8",
    )

    discovered = discover_action_sources(tmp_path)

    assert tuple(item.action_id for item in discovered) == ("fixture_action",)
    assert discovered[0].source == source


def test_ast_audit_reports_dynamic_missing_id(tmp_path: Path) -> None:
    (tmp_path / "fixture.py").write_text(
        "class Action:\n    label = translate('Fixture Action')\n",
        encoding="utf-8",
    )

    result = audit_action_sources(tmp_path, expected_ids=frozenset({"known"}))

    assert result.missing_policy_ids == frozenset({"fixture_action"})
    assert result.stale_policy_ids == frozenset({"known"})


@pytest.mark.parametrize(
    "source_text",
    [
        "class Action:\n    label = make_label()\n",
        "class Action:\n    label = 'First'\nclass Action:\n    label = 'Second'\n",
        "class Action:\n    label = 'broken'\n    this is not valid Python\n",
    ],
)
def test_ast_discovery_rejects_ambiguous_or_invalid_sources(
    tmp_path: Path, source_text: str
) -> None:
    (tmp_path / "invalid.py").write_text(source_text, encoding="utf-8")

    with pytest.raises(ActionAuditError):
        discover_action_sources(tmp_path)


def test_ast_discovery_supports_annotated_literal_and_rejects_duplicates(
    tmp_path: Path,
) -> None:
    (tmp_path / "first.py").write_text(
        "class Action:\n    label: str = 'Same'\n", encoding="utf-8"
    )
    assert discover_action_sources(tmp_path)[0].action_id == "same"
    (tmp_path / "second.py").write_text(
        "class Action:\n    label = 'Same'\n", encoding="utf-8"
    )

    with pytest.raises(ActionAuditError, match="duplicate action ID"):
        discover_action_sources(tmp_path)


def test_ast_discovery_ignores_utility_sources(tmp_path: Path) -> None:
    (tmp_path / "utility.py").write_text(
        "class Helper:\n    label = 'Not an action'\n", encoding="utf-8"
    )

    assert discover_action_sources(tmp_path) == ()


def test_audit_cli_reports_success_and_complete_inventory(
    project_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(("--actions-root", str(project_root / "phatch" / "actions")))

    output = capsys.readouterr()
    assert exit_code == 0
    assert "auto_contrast: autocontrast.py" in output.out
    assert output.out.endswith("54/54 covered\n")
    assert output.err == ""


def test_audit_cli_reports_missing_and_extra_ids(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "fixture.py").write_text(
        "class Action:\n    label = translate('Fixture Action')\n",
        encoding="utf-8",
    )

    exit_code = main(("--actions-root", str(tmp_path)))

    output = capsys.readouterr()
    assert exit_code == 1
    assert "missing policy IDs: fixture_action" in output.err
    assert "extra policy IDs:" in output.err
    assert output.out.endswith("0/1 covered\n")


def test_audit_cli_rejects_missing_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "missing"

    exit_code = main(("--actions-root", str(missing)))

    output = capsys.readouterr()
    assert exit_code == 2
    assert str(missing) in output.err
