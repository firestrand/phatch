"""Console batch safety warnings and interactive decisions use existing presentation."""

import pytest

from phatch.console import batch_console
from phatch.core import api
from phatch.core.batch import BatchResult
from phatch.core.settings import DEFAULT_SETTINGS
from phatch.lib import formField, safe


@pytest.mark.parametrize("safe_mode", [True, False])
def test_batch_console_respects_loader_safety_warning(monkeypatch, safe_mode):
    monkeypatch.setattr(
        api,
        "open_batch_actionlist",
        lambda path: ({"actions": []}, "unsafe expression"),
    )
    monkeypatch.setattr(formField, "get_safe", lambda: safe_mode)
    monkeypatch.setattr(
        api, "apply_batch_actions_to_photos", lambda *args, **kwargs: BatchResult()
    )
    settings = dict(DEFAULT_SETTINGS, verbose=False, interactive=False)
    if safe_mode:
        with pytest.raises(safe.UnsafeError, match="unsafe expression"):
            batch_console.Frame("recipe.phatch", [], settings)
    else:
        frame = batch_console.Frame("recipe.phatch", [], settings)
        try:
            assert isinstance(frame.result, BatchResult)
        finally:
            frame.unsubscribe_all()


def test_batch_console_interactive_error_choice(monkeypatch):
    frame = batch_console.Frame.receiver(dict(DEFAULT_SETTINGS, interactive=True))
    monkeypatch.setattr(batch_console, "ask", lambda *args: "ignore")
    response = {}
    try:
        frame.show_progress_error(response, "processing failed")
        assert response == {"answer": "ignore", "stop_for_errors": True}
        frame.append_save_action([])
    finally:
        frame.unsubscribe_all()
