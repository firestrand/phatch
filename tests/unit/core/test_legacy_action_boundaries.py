import builtins
from pathlib import Path

import pytest

from phatch.core.execution_types import DiscoveredFile, ExecutionOptions
from phatch.services.legacy_actions import LegacyActionAdapter, LegacyActionDependencies
from phatch.services.legacy_types import translate
from tests.unit.core.execution_fakes import ActionFake, PhotoFake
from tests.unit.core.test_legacy_execution_adapters import (
    ActionFake as LegacyActionFake,
)
from tests.unit.core.test_legacy_execution_adapters import InteractionFake


def test_legacy_action_run_rejects_nonlegacy_action() -> None:
    raw_action = LegacyActionFake()
    run = LegacyActionDependencies({}, InteractionFake(), (raw_action,)).begin_run(
        ExecutionOptions(())
    )

    with pytest.raises(TypeError, match="requires LegacyActionAdapter"):
        run.is_done(ActionFake(), PhotoFake(DiscoveredFile(Path("source.png"))))


def test_legacy_action_run_rejects_nonlegacy_photo() -> None:
    raw_action = LegacyActionFake()
    run = LegacyActionDependencies({}, InteractionFake(), (raw_action,)).begin_run(
        ExecutionOptions(())
    )

    with pytest.raises(TypeError, match="requires LegacyPhotoAdapter"):
        run.is_done(
            LegacyActionAdapter(raw_action),
            PhotoFake(DiscoveredFile(Path("source.png"))),
        )


def test_translate_uses_installed_gettext_callable(monkeypatch) -> None:
    monkeypatch.setattr(builtins, "_", lambda value: f"translated:{value}")

    assert translate("message") == "translated:message"


def test_translate_returns_value_without_gettext_callable(monkeypatch) -> None:
    monkeypatch.setattr(builtins, "_", None)

    assert translate("message") == "message"
