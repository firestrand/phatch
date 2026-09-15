from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from phatch.core.action_registry import (
    ActionRegistryBuildFailure,
    ActionRegistryBuildSuccess,
    ImmutableActionRegistry,
)
from phatch.core.execution_types import ExecutionIssue, IssueSeverity, IssueStage
from phatch.services import preview_actions
from phatch.services.preview_types import (
    PreviewActionSpec,
    PreviewAdmissionError,
    PreviewErrorCode,
)


class FakeField:
    def get_as_string(self) -> str:
        return "value"

    def set_as_string(self, value: str) -> None:
        return None


class FakeAction:
    def __init__(self, invalid: list[str] | None = None) -> None:
        self.invalid = invalid or []

    def load(self, fields):
        return self.invalid

    def init(self):
        return None

    def values(self, info):
        return {}

    def get_field(self, label, info):
        return None

    def get_field_size(self, label, info, reference, dpi):
        return 0

    def apply(self, photo, settings, cache):
        return photo


def _construct(
    monkeypatch: pytest.MonkeyPatch,
    action: object,
    fields: tuple[dict[str, str], ...] = ({"field": "value"},),
    *,
    known: bool = True,
):
    registry = MagicMock(spec=ImmutableActionRegistry)
    registry.labels.return_value = ("Known",) if known else ()
    registry.fields = {"Known": {"Field": FakeField()}} if known else {}
    registry.instantiate.return_value = action

    def build(_sources):
        return ActionRegistryBuildSuccess(registry)

    monkeypatch.setattr("phatch.services.preview_actions.build_action_registry", build)
    return preview_actions.construct_preview_actions(
        (PreviewActionSpec("known", tuple(fields[0].items())),),
        fields,
    )


def test_construct_rejects_registry_build_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "phatch.services.preview_actions.build_action_registry",
        lambda _sources: ActionRegistryBuildFailure(
            (
                ExecutionIssue(
                    IssueStage.ACTION_INITIALIZATION,
                    IssueSeverity.ERROR,
                    "broken registry",
                ),
            )
        ),
    )

    with pytest.raises(PreviewAdmissionError) as captured:
        preview_actions.construct_preview_actions((), ())

    assert captured.value.code is PreviewErrorCode.WORKER_FAILED


def test_construct_rejects_unknown_action(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(PreviewAdmissionError) as captured:
        _construct(monkeypatch, FakeAction(), ({},), known=False)

    assert captured.value.code is PreviewErrorCode.UNKNOWN_ACTION


def test_construct_rejects_unknown_field(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(PreviewAdmissionError) as captured:
        _construct(monkeypatch, FakeAction(), ({"missing": "x"},))

    assert captured.value.code is PreviewErrorCode.INVALID_FIELD


def test_construct_rejects_incomplete_action_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(PreviewAdmissionError) as captured:
        _construct(monkeypatch, lambda: None)

    assert captured.value.code is PreviewErrorCode.WORKER_FAILED


def test_construct_rejects_action_field_load_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(PreviewAdmissionError) as captured:
        _construct(monkeypatch, FakeAction(["Field"]))

    assert captured.value.code is PreviewErrorCode.INVALID_FIELD


def test_construct_accepts_action_without_relevance_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _construct(monkeypatch, FakeAction())

    assert len(result) == 1
