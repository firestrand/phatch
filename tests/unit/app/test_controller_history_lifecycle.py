from phatch.pyWx.controller import ActionListController
from phatch.services.action_schema_types import ActionField
from tests.unit.app.controller_history_test_support import (
    FakeAction,
    HistoryTree,
    action_ids,
)


def test_failed_open_transition_restores_document_history_and_state() -> None:
    tree = HistoryTree([FakeAction("resize")])
    controller = ActionListController(tree)
    controller.add_action_by_label("Crop")
    before = (
        controller.current_document,
        controller.checkpoint,
        controller.state,
        controller.can_undo,
        controller.can_redo,
    )
    controller.begin_open()
    controller.new_actionlist()

    controller.finish_open(success=False)

    assert action_ids(controller) == ("resize", "crop")
    assert [action.action_id for action in tree.actions] == ["resize", "crop"]
    assert (
        controller.current_document,
        controller.checkpoint,
        controller.state,
        controller.can_undo,
        controller.can_redo,
    ) == before


def test_successful_open_replaces_document_and_clears_history() -> None:
    controller = ActionListController(HistoryTree([FakeAction("resize")]))
    controller.add_action_by_label("Crop")
    controller.begin_open()
    controller.new_actionlist()
    controller.apply_loaded_data("opened.phatch", [FakeAction("scale")], "Opened")

    controller.finish_open(success=True)

    assert action_ids(controller) == ("scale",)
    assert controller.checkpoint == controller.current_document
    assert controller.can_undo is False
    assert controller.state.dirty is False


def test_failed_save_transition_restores_filename_and_checkpoint() -> None:
    controller = ActionListController(HistoryTree([FakeAction("resize")]))
    controller.add_action_by_label("Crop")
    before = (controller.state, controller.checkpoint, controller.can_undo)
    controller.begin_save()
    controller.state.filename = "failed.phatch"
    controller.mark_clean("Failed")

    controller.finish_save(success=False)

    assert (controller.state, controller.checkpoint, controller.can_undo) == before
    assert controller.current_document.description != "Failed"


def test_successful_save_keeps_history_and_moves_checkpoint() -> None:
    controller = ActionListController(HistoryTree([FakeAction("resize")]))
    controller.add_action_by_label("Crop")
    controller.begin_save()
    controller.state.filename = "saved.phatch"
    controller.mark_clean("Saved")

    controller.finish_save(success=True)

    assert controller.state.filename == "saved.phatch"
    assert controller.current_document.description == "Saved"
    assert controller.checkpoint == controller.current_document
    assert controller.can_undo is True
    assert controller.state.dirty is False


def test_initial_snapshot_does_not_share_mutable_action_fields() -> None:
    action = FakeAction("resize", {"width": "100"})
    controller = ActionListController(HistoryTree([action]))

    action.fields["width"] = "999"

    assert controller.current_document.actions[0].fields == (
        ActionField("width", "100"),
    )


def test_history_listener_registration_is_idempotent_and_removable() -> None:
    controller = ActionListController(HistoryTree())
    notifications: list[None] = []

    def listener() -> None:
        notifications.append(None)

    controller.add_history_listener(listener)
    controller.add_history_listener(listener)
    controller.update_description("first")
    controller.remove_history_listener(listener)
    controller.remove_history_listener(listener)
    controller.update_description("second")

    assert notifications == [None]


def test_inactive_lifecycle_failures_leave_state_unchanged() -> None:
    controller = ActionListController(HistoryTree([FakeAction("resize")]))
    before = controller.state

    controller.finish_open(success=False)
    controller.finish_save(success=False)

    assert controller.state is before
