import builtins

if '_' not in builtins.__dict__:
    builtins.__dict__['_'] = lambda value: value

from phatch.pyWx.controller import ActionListController, ActionListState


class FakeTree:
    def __init__(self):
        self.deleted = 0
        self.appended = []
        self._has_forms = False
        self._exported = []
        self.removed_calls = 0
        self.moved_up = 0
        self.moved_down = 0
        self.enabled_flags = []
        self.selected = False
        self.expanded = False
        self.collapsed = False
        self.collapse_auto = False
        self.popup_closed = 0
        self.popup_resized = 0
        self.popup_menu_invoked = []

    def delete_all_forms(self):
        self.deleted += 1
        self._has_forms = False
        self.appended.clear()

    def append_forms(self, actions):
        self.appended.append(tuple(actions))
        self._has_forms = bool(actions)
        self._exported = list(actions)
        return self._has_forms

    def has_forms(self):
        return self._has_forms

    def export_forms(self):
        return list(self._exported)

    def append_form_by_label_to_selected(self, label):
        self.append_forms([label])

    def append_form_by_label_to_last(self, label):
        self.append_forms([label])

    def remove_selected_form(self):
        if not self._has_forms:
            return False
        self.removed_calls += 1
        self._has_forms = False
        self._exported = []
        return True

    def move_form_selected_up(self):
        self.moved_up += 1

    def move_form_selected_down(self):
        self.moved_down += 1

    def enable_selected_form(self, enabled):
        self.enabled_flags.append(enabled)

    def is_form_selected(self):
        return self.selected

    def expand_forms(self):
        self.expanded = True

    def collapse_forms(self):
        self.collapsed = True

    def enable_collapse_automatic(self, checked):
        self.collapse_auto = checked

    def close_popup(self):
        self.popup_closed += 1

    def resize_popup(self):
        self.popup_resized += 1

    def popup_menu(self, menu):
        self.popup_menu_invoked.append(menu)


def test_new_actionlist_resets_tree_and_state():
    tree = FakeTree()
    controller = ActionListController(tree)

    state = controller.new_actionlist()

    assert tree.deleted == 1
    assert state == ActionListState()


def test_apply_loaded_data_sets_filename_description_and_actions():
    tree = FakeTree()
    controller = ActionListController(tree)

    state = controller.apply_loaded_data("path/to/file.phatch", [1, 2], "Description")

    assert tree.deleted == 1
    assert tree.appended == [(1, 2)]
    assert state.filename == "path/to/file.phatch"
    assert state.description == "Description"
    assert not state.dirty
    assert state.has_actions is True


def test_apply_loaded_data_falls_back_to_default_description():
    tree = FakeTree()
    controller = ActionListController(tree)

    state = controller.apply_loaded_data("file", [1], "")

    assert state.description != ""
    assert state.description == state.saved_description


def test_mark_dirty_and_clean_toggle_state():
    tree = FakeTree()
    controller = ActionListController(tree)

    controller.mark_dirty()
    assert controller.state.dirty is True

    controller.mark_clean("Saved")
    assert controller.state.dirty is False
    assert controller.state.description == "Saved"
    assert controller.state.saved_description == "Saved"


def test_update_description_marks_dirty_when_changed():
    tree = FakeTree()
    controller = ActionListController(tree)

    controller.mark_clean("Initial")
    controller.update_description("Modified")

    assert controller.state.description == "Modified"
    assert controller.state.dirty is True

    controller.update_description("Initial")
    assert controller.state.dirty is False


def test_export_actions_returns_tree_data():
    tree = FakeTree()
    controller = ActionListController(tree)
    controller.apply_loaded_data("file", ["resize"], "")

    assert list(controller.export_actions()) == ["resize"]


def test_refresh_has_actions_queries_tree():
    tree = FakeTree()
    controller = ActionListController(tree)

    controller.apply_loaded_data("file", ["resize"], "")
    assert controller.refresh_has_actions() is True

    tree.delete_all_forms()
    assert controller.refresh_has_actions() is False


def test_add_action_by_label_updates_state_and_marks_dirty():
    tree = FakeTree()
    controller = ActionListController(tree)

    controller.add_action_by_label("Resize")

    assert controller.state.has_actions is True
    assert controller.state.dirty is True
    assert tree.appended[-1] == ("Resize",)


def test_remove_selected_action_marks_clean_when_no_actions_remain():
    tree = FakeTree()
    controller = ActionListController(tree)
    controller.apply_loaded_data("file", ["resize"], "")

    removed = controller.remove_selected_action()

    assert removed is True
    assert controller.state.has_actions is False
    assert controller.state.dirty is False


def test_remove_selected_action_marks_dirty_when_actions_remain():
    tree = FakeTree()
    controller = ActionListController(tree)
    controller.apply_loaded_data("file", ["resize", "crop"], "")
    tree._has_forms = True  # ensure after removal still considered populated

    # Simulate removal without clearing stored export list entirely
    def fake_remove():
        tree._exported = ["crop"]
        return True

    tree.remove_selected_form = fake_remove
    tree.has_forms = lambda: True  # noqa: E731

    removed = controller.remove_selected_action()

    assert removed is True
    assert controller.state.has_actions is True
    assert controller.state.dirty is True


def test_move_selected_actions_mark_dirty():
    tree = FakeTree()
    controller = ActionListController(tree)

    controller.move_selected_action_up()
    controller.move_selected_action_down()

    assert controller.state.dirty is True
    assert tree.moved_up == 1
    assert tree.moved_down == 1


def test_enable_selected_action_tracks_dirty_state():
    tree = FakeTree()
    controller = ActionListController(tree)

    controller.enable_selected_action(True)
    controller.enable_selected_action(False)

    assert controller.state.dirty is True
    assert tree.enabled_flags == [True, False]


def test_has_selected_action_forwarded_to_tree():
    tree = FakeTree()
    controller = ActionListController(tree)
    tree.selected = True

    assert controller.has_selected_action() is True


def test_expand_and_collapse_all_forward_to_tree():
    tree = FakeTree()
    controller = ActionListController(tree)

    controller.expand_all()
    controller.collapse_all()

    assert getattr(tree, "expanded", False) is True
    assert getattr(tree, "collapsed", False) is True


def test_add_action_by_label_to_last_marks_dirty():
    tree = FakeTree()
    controller = ActionListController(tree)

    controller.add_action_by_label_to_last("Save")

    assert controller.state.dirty is True
    assert controller.state.has_actions is True
    assert tree.appended[-1] == ("Save",)


def test_enable_collapse_automatic_forwarded():
    tree = FakeTree()
    controller = ActionListController(tree)

    controller.enable_collapse_automatic(True)

    assert getattr(tree, "collapse_auto", None) is True


def test_has_forms_uses_tree_state():
    tree = FakeTree()
    controller = ActionListController(tree)
    tree._has_forms = True

    assert controller.has_forms() is True


def test_close_context_popup_delegates_to_tree():
    tree = FakeTree()
    controller = ActionListController(tree)

    controller.close_context_popup()

    assert tree.popup_closed == 1


def test_resize_popup_delegates_to_tree():
    tree = FakeTree()
    controller = ActionListController(tree)

    controller.resize_popup()

    assert tree.popup_resized == 1


def test_show_context_menu_delegates_to_tree():
    tree = FakeTree()
    controller = ActionListController(tree)
    menu = object()

    controller.show_context_menu(menu)

    assert tree.popup_menu_invoked == [menu]
