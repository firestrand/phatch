"""Batch service callbacks, cancellation and validation retain their outcomes."""

import pytest
from PIL import Image

from phatch.core import api
from phatch.core.settings import DEFAULT_SETTINGS
from phatch.services.action_list import ActionListService


@pytest.fixture
def batch_workflow(initialized_runtime, tmp_path):
    save = api.ACTIONS["Save"]()
    save.set_field_as_string("In", str(tmp_path / "outputs"))
    save.set_field_as_string("As", "png")
    return [api.ACTIONS["Invert"](), save]


def test_batch_service_forwards_callback_and_verifies_selected_images(
    batch_workflow, test_input_dir
):
    updates = []
    result = ActionListService().execute_batch(
        iter(batch_workflow),
        dict(DEFAULT_SETTINGS, check_images_first=True),
        update_callback=lambda: updates.append(True),
        paths=[str(test_input_dir / "frog.gif")],
    )
    assert result.status == "success", result.to_dict(include_details=True)
    assert updates
    with Image.open(result.files[0].outputs[0]) as image:
        assert image.size == (128, 128)


@pytest.mark.parametrize("answer", ["abort", "skip", "ignore", "stop"])
def test_batch_service_error_decisions_preserve_failure_details(
    batch_workflow, test_input_dir, monkeypatch, answer
):
    from tests.fixtures.worker_action import Action

    action = Action()
    action.set_field_as_string("Mode", "fail")

    def decide(response, *args, **kwargs):
        response["answer"] = answer

    monkeypatch.setattr(api.send, "frame_show_progress_error", decide)
    result = ActionListService().execute_batch(
        [action, *batch_workflow],
        dict(DEFAULT_SETTINGS, check_images_first=False, stop_for_errors=True),
        paths=[str(test_input_dir / "frog.gif")],
    )
    expected = {
        "abort": "cancelled",
        "ignore": "partial_failure",
        "skip": "failed",
        "stop": "failed",
    }
    assert result.status == expected[answer]
    assert result.files[0].failures


def test_batch_service_empty_discovery_and_cancelled_selection(
    batch_workflow, test_input_dir, monkeypatch
):
    settings = dict(DEFAULT_SETTINGS, check_images_first=True)
    assert (
        api.apply_batch_actions_to_photos(batch_workflow, settings, paths=[]).status
        == "cancelled"
    )
    monkeypatch.setattr(api, "get_image_infos", lambda *args: [])
    result = api.apply_batch_actions_to_photos(
        batch_workflow, settings, paths=[str(test_input_dir / "frog.gif")]
    )
    assert result.status == "invalid_setup"
    assert result.issues[0].code == "empty_input"


@pytest.mark.parametrize("cancelled", [False, True])
def test_batch_service_verification_outcome(batch_workflow, monkeypatch, cancelled):
    monkeypatch.setattr(api, "get_image_infos", lambda *args: [{"path": "source.png"}])

    def verification(infos, repeat, state):
        state["cancelled"] = cancelled

    monkeypatch.setattr(api, "verify_images", verification)
    result = api.apply_batch_actions_to_photos(
        batch_workflow,
        dict(DEFAULT_SETTINGS, check_images_first=True),
        paths=["source.png"],
    )
    assert result.status == ("cancelled" if cancelled else "invalid_setup")
