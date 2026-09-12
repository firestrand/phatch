import pytest

from phatch.core import api


@pytest.mark.parametrize(
    ("answer", "expected_skip", "expected_abort"),
    [("abort", False, True), ("skip", True, False), ("ignore", False, False)],
)
def test_error_decisions_log_before_prompt(
    monkeypatch, answer, expected_skip, expected_abort
):
    events = []
    result = {"stop_for_errors": True, "last_answer": None}
    monkeypatch.setattr(api, "log_error", lambda *args: events.append("log"))

    def prompt(prompt_result, message, ignore):
        events.append("prompt")
        prompt_result["answer"] = answer

    monkeypatch.setattr(api.send, "frame_show_progress_error", prompt)

    _, updated = api.process_error(None, "problem", "photo.jpg", None, result, True)

    assert events == ["log", "prompt"]
    assert updated["skip"] is expected_skip
    assert updated["abort"] is expected_abort
    if answer != "abort":
        assert updated["last_answer"] == answer


def test_previous_skip_decision_propagates_when_prompts_are_disabled(monkeypatch):
    result = {"stop_for_errors": False, "last_answer": "skip"}
    monkeypatch.setattr(api, "log_error", lambda *args: None)

    _, updated = api.process_error(None, "problem", "photo.jpg", None, result, True)

    assert updated["skip"] is True
    assert updated["abort"] is False
