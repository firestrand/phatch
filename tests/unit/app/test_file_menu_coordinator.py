import builtins
from types import SimpleNamespace

if "_" not in builtins.__dict__:
    builtins.__dict__["_"] = lambda value: value

from phatch.core import ct
from phatch.pyWx.file_menu import ClipboardMessages, FileMenuCoordinator, wx as file_wx
from phatch.services.file_dialogs import DialogSelection


class DescriptionField:
    def __init__(self):
        self.value = None

    def SetValue(self, value):
        self.value = value


class StubController:
    def __init__(self):
        self.state = SimpleNamespace(
            filename=ct.UNKNOWN,
            description=ct.ACTION_LIST_DESCRIPTION,
            saved_description=ct.ACTION_LIST_DESCRIPTION,
            dirty=False,
            has_actions=False,
        )

    def new_actionlist(self):
        self.state = SimpleNamespace(
            filename=ct.UNKNOWN,
            description=ct.ACTION_LIST_DESCRIPTION,
            saved_description=ct.ACTION_LIST_DESCRIPTION,
            dirty=False,
            has_actions=False,
        )
        return self.state


class StubFileHistory:
    def __init__(self):
        self.entries: list[str] = []

    def UseMenu(self, menu):
        pass

    def AddFileToHistory(self, filename):
        self.entries.append(filename)

    def GetCount(self):
        return len(self.entries)

    def GetHistoryFile(self, index):
        return self.entries[index]


class StubFileDialogs:
    def __init__(self):
        self.open_selection = None
        self.save_selection = None
        self.open_kwargs = None
        self.save_kwargs = None

    def open_actionlist(self, **kwargs):
        self.open_kwargs = kwargs
        return self.open_selection

    def save_actionlist(self, **kwargs):
        self.save_kwargs = kwargs
        return self.save_selection


class StubFrame:
    def __init__(self):
        self.controller = StubController()
        self.filename = ct.UNKNOWN
        self.description = DescriptionField()
        self.show_description_state = None
        self.enable_actions_state = None
        self.saved_paths: list[str | None] = []
        self.opened_paths: list[str] = []
        self.last_question = None
        self.question_response = file_wx.ID_YES
        self.last_message = None
        self.message_response = file_wx.ID_NO
        self.info_messages: list[str] = []

    def _set_filename(self, filename):
        self.filename = filename

    def _save(self, filename=None):
        self.saved_paths.append(filename if filename is not None else self.filename)

    def _open(self, path):
        self.opened_paths.append(path)

    def show_description(self, value):
        self.show_description_state = value

    def enable_actions(self, value):
        self.enable_actions_state = value

    def show_message(self, message, style=None):
        self.last_message = (message, style)
        return self.message_response

    def show_question(self, message):
        self.last_question = message
        return self.question_response

    def show_info(self, message, title=""):
        self.info_messages.append(message)

    def is_protected_actionlist(self, filename):
        return False


def build_coordinator(frame, file_history=None, file_dialogs=None, copy_log=None):
    if file_history is None:
        file_history = StubFileHistory()
    if file_dialogs is None:
        file_dialogs = StubFileDialogs()
    if copy_log is None:
        copy_log = []

    def copy_text(value):
        copy_log.append(value)

    clipboard = ClipboardMessages(
        paste_hint="paste",
        actionlist="actionlist",
        recent="recent",
        inspector="inspector",
    )
    coordinator = FileMenuCoordinator(
        frame=frame,
        file_history=file_history,
        file_dialogs=file_dialogs,
        clipboard_messages=clipboard,
        ensure_suffix=lambda value: value if value.endswith(ct.EXTENSION) else f"{value}{ct.EXTENSION}",
        copy_text=copy_text,
    )
    return coordinator, file_history, file_dialogs, copy_log


def test_confirm_proceed_allows_when_not_dirty():
    frame = StubFrame()
    coordinator, *_ = build_coordinator(frame)

    assert coordinator.confirm_proceed() is True
    assert frame.last_message is None


def test_confirm_proceed_returns_false_when_user_cancels():
    frame = StubFrame()
    frame.controller.state.dirty = True
    frame.filename = "example.phatch"
    frame.message_response = file_wx.ID_CANCEL
    coordinator, *_ = build_coordinator(frame)

    assert coordinator.confirm_proceed() is False
    assert frame.saved_paths == []


def test_confirm_proceed_saves_when_user_accepts(tmp_path):
    frame = StubFrame()
    frame.controller.state.dirty = True
    frame.message_response = file_wx.ID_YES
    selection_path = tmp_path / "saved.phatch"
    file_dialogs = StubFileDialogs()
    file_dialogs.save_selection = DialogSelection(str(selection_path))
    coordinator, *_ = build_coordinator(frame, file_dialogs=file_dialogs)

    assert coordinator.confirm_proceed() is True
    assert frame.saved_paths == [str(selection_path)]


def test_new_actionlist_resets_frame_state():
    frame = StubFrame()
    coordinator, *_ = build_coordinator(frame)

    coordinator.new_actionlist()

    assert frame.filename == ct.UNKNOWN
    assert frame.description.value == ct.ACTION_LIST_DESCRIPTION
    assert frame.show_description_state is False
    assert frame.enable_actions_state is False


def test_open_actionlist_loads_selected_path():
    frame = StubFrame()
    file_dialogs = StubFileDialogs()
    file_dialogs.open_selection = DialogSelection("path/to/file.phatch")
    coordinator, *_ = build_coordinator(frame, file_dialogs=file_dialogs)

    coordinator.open_actionlist()

    assert frame.opened_paths == ["path/to/file.phatch"]


def test_save_as_honours_overwrite_rejection(tmp_path):
    existing = tmp_path / "existing.phatch"
    existing.write_text("data")
    frame = StubFrame()
    frame.filename = str(existing)
    frame.question_response = file_wx.ID_NO
    file_dialogs = StubFileDialogs()
    file_dialogs.save_selection = DialogSelection(str(existing))
    coordinator, *_ = build_coordinator(frame, file_dialogs=file_dialogs)

    assert coordinator.save_as() is False
    assert frame.saved_paths == []


def test_file_history_roundtrip(tmp_path):
    first = tmp_path / "first.phatch"
    second = tmp_path / "second.phatch"
    first.write_text("1")
    second.write_text("2")
    frame = StubFrame()
    file_history = StubFileHistory()
    coordinator, file_history, *_ = build_coordinator(frame, file_history=file_history)

    coordinator.load_file_history([str(first), str(second)])

    assert file_history.entries == [str(second), str(first)]
    assert coordinator.get_file_history() == [str(second), str(first)]


def test_export_actionlist_to_clipboard(tmp_path):
    frame = StubFrame()
    frame.filename = str(tmp_path / "workflow.phatch")
    frame.controller.state.dirty = False
    coordinator, _, _, copy_log = build_coordinator(frame)

    coordinator.export_actionlist_to_clipboard()

    assert copy_log == [ct.COMMAND["DROP"] % frame.filename]
    assert frame.info_messages == [" ".join(["actionlist", "paste"])]
