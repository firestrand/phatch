from __future__ import annotations

import io
import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from phatch.core.action_registry import RegisteredAction, RegistryField
from phatch.core.execution_types import (
    ExecutionIssue,
    ExecutionOutcome,
    ExecutionResult,
    IssueSeverity,
    IssueStage,
)
from phatch.lib.capabilities import (
    Capability,
    CapabilityId,
    CapabilityReasonCode,
    CapabilityStatus,
)
from phatch.services import automation_cli
from phatch.services.action_schema import ActionDocument, RegistrySchemaCatalog
from phatch.services.preflight import (
    PreflightRequest,
    PreflightService,
    PreflightValidationError,
)
from phatch.services.structured_report import ExitCode, execution_report


class _Field:
    def __init__(self, invalid: str | None = None) -> None:
        self.invalid = invalid

    def get_as_string(self) -> str:
        return ""

    def set_as_string(self, value: str) -> None:
        return None

    def get(self, info, label: str, value: str, test: bool = False) -> str:
        if self.invalid == value:
            raise ValueError(value)
        return value


class _CollisionRegistry:
    def __init__(
        self, *, reverse: bool = False, invalid_transformation: str | None = None
    ) -> None:
        self.reverse = reverse
        self.invalid_transformation = invalid_transformation

    @property
    def fields(self) -> Mapping[str, Mapping[str, RegistryField]]:
        field = _Field()
        items = [
            ("Transformation", _Field(self.invalid_transformation)),
            ("Transformation ", field),
            ("Angle", field),
            ("Angle ", field),
            ("Direction", field),
            ("Direction ", field),
        ]
        if self.reverse:
            items.reverse()
        return {"Lossless JPEG": dict(items)}

    def labels(self) -> tuple[str, ...]:
        return ("Lossless JPEG",)

    def instantiate(self, label: str) -> RegisteredAction:
        raise AssertionError(label)


def test_catalog_assigns_collision_safe_field_ids() -> None:
    catalog = RegistrySchemaCatalog(_CollisionRegistry())

    assert catalog.field_id("lossless_jpeg", "Transformation") == "transformation"
    assert catalog.field_id("lossless_jpeg", "Transformation ") == "transformation_2"
    assert catalog.field_label("lossless_jpeg", "angle_2") == "Angle "
    assert catalog.field_label("lossless_jpeg", "direction_2") == "Direction "


def test_catalog_collision_ids_are_independent_of_registry_order() -> None:
    forward = RegistrySchemaCatalog(_CollisionRegistry())
    reverse = RegistrySchemaCatalog(_CollisionRegistry(reverse=True))

    for label in (
        "Transformation",
        "Transformation ",
        "Angle",
        "Angle ",
        "Direction",
        "Direction ",
    ):
        assert forward.field_id("lossless_jpeg", label) == reverse.field_id(
            "lossless_jpeg", label
        )


def test_preflight_uses_filtered_discovery_and_preserves_duplicates(
    tmp_path: Path,
) -> None:
    image = tmp_path / "image.PNG"
    ignored = tmp_path / "notes.txt"
    image.write_bytes(b"image")
    ignored.write_text("not an image", encoding="utf-8")

    result = PreflightService().build(
        PreflightRequest(
            ActionDocument.from_values("", ()),
            (tmp_path, image),
            (),
        )
    )

    assert result.inputs == (image.resolve(), image.resolve())


def test_preflight_rejects_invalid_path(tmp_path: Path) -> None:
    with pytest.raises(PreflightValidationError, match="not a valid path"):
        PreflightService().build(
            PreflightRequest(
                ActionDocument.from_values("", ()),
                (tmp_path / "missing",),
                (),
            )
        )


def test_preflight_rejects_empty_directory(tmp_path: Path) -> None:
    with pytest.raises(PreflightValidationError, match="No input images"):
        PreflightService().build(
            PreflightRequest(ActionDocument.from_values("", ()), (tmp_path,), ())
        )


def test_preflight_reports_invalid_field_values_without_constructing(
    tmp_path: Path,
) -> None:
    image = tmp_path / "input.png"
    image.write_bytes(b"image")
    registry = _CollisionRegistry(invalid_transformation="<open>")
    catalog = RegistrySchemaCatalog(registry)
    document = ActionDocument.from_values(
        "", (("lossless_jpeg", (("transformation", "<open>"),)),)
    )

    result = PreflightService().build(
        PreflightRequest(document, (image,), (), catalog=catalog)
    )

    assert result.invalid_fields == ("lossless_jpeg.transformation",)


def test_preflight_ignores_disabled_actions_and_uses_selected_utility(
    tmp_path: Path,
) -> None:
    source = tmp_path / "image.jpg"
    source.write_bytes(b"image")
    destination = tmp_path / "output"
    document = ActionDocument.from_values(
        "",
        (
            (
                "save",
                (
                    ("enabled", "no"),
                    ("in", str(destination)),
                    ("file_name", "disabled"),
                    ("as", "png"),
                ),
            ),
            (
                "lossless_jpeg",
                (
                    ("utility", "Jpegtran (without exif support)"),
                    ("in", str(destination)),
                    ("file_name", "<filename>"),
                ),
            ),
        ),
    )
    exiftran = Capability(
        CapabilityId("exiftran"),
        CapabilityStatus.UNAVAILABLE,
        CapabilityReasonCode.MISSING_EXECUTABLE,
        "missing",
    )
    jpegtran = Capability(
        CapabilityId("jpegtran"),
        CapabilityStatus.AVAILABLE,
        CapabilityReasonCode.AVAILABLE,
        "available",
    )

    result = PreflightService().build(
        PreflightRequest(document, (source,), (exiftran, jpegtran))
    )

    assert result.outputs == ((destination / "image.jpg").resolve(),)
    assert result.unavailable_capabilities == ()
    assert result.estimated_work == 1


@pytest.mark.parametrize(
    "argument",
    ("--report-format=json", "--resume=journal.jsonl"),
)
def test_automation_detection_accepts_equals_form(argument: str) -> None:
    assert automation_cli.is_automation_request((argument,)) is True


def test_parser_failure_emits_json_when_equals_form_requested() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    result = automation_cli.run_automation_cli(
        ("--dry-run", "--report-format=json", "--unknown"), stdout, stderr
    )

    assert result == ExitCode.VALIDATION_FAILURE
    assert json.loads(stdout.getvalue())["outcome"] == "validation_failure"
    assert "unrecognized arguments" in stderr.getvalue()


def test_execution_report_normalizes_action_label_to_stable_id() -> None:
    result = ExecutionResult(
        ExecutionOutcome.FAILED,
        (),
        (
            ExecutionIssue(
                IssueStage.ACTION_EXECUTION,
                IssueSeverity.ERROR,
                "failed",
                action_label="Scale",
            ),
        ),
        0.0,
    )

    assert execution_report(result)["issues"][0]["action_id"] == "scale"
