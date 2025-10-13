import builtins

if '_' not in builtins.__dict__:
    builtins.__dict__['_'] = lambda value: value

from phatch.services.file_dialogs import DialogSelection, FileDialogService, wx


class FakeDialog:
    def __init__(self, parent, **options):
        self.parent = parent
        self.options = options
        self.result_queue = []
        self.paths = []
        self.filter_index = 0

    def enqueue(self, result, path, filter_index=None):
        self.result_queue.append(result)
        self.paths.append(path)
        if filter_index is not None:
            self.filter_index = filter_index

    def ShowModal(self):
        return self.result_queue.pop(0)

    def GetPath(self):
        return self.paths.pop(0)

    def GetFilterIndex(self):
        return self.filter_index

    def Destroy(self):
        self.destroyed = True


def test_open_actionlist_returns_selection_when_ok(monkeypatch):
    dialog = FakeDialog(None)
    dialog.enqueue(wx.ID_OK, "/tmp/list.phatch")

    def factory(parent, **options):
        # Reuse the same dialog instance to inspect options
        dialog.options = options
        return dialog

    service = FileDialogService(factory)

    selection = service.open_actionlist(
        parent=None,
        message="Choose",
        default_dir="/tmp",
        wildcard="*.phatch",
        style=1,
    )

    assert selection == DialogSelection(path="/tmp/list.phatch", filter_index=0)
    assert dialog.options['message'] == "Choose"
    assert dialog.options['defaultDir'] == "/tmp"
    assert dialog.options['wildcard'] == "*.phatch"
    assert dialog.options['style'] == 1


def test_save_actionlist_applies_overwrite_flag(monkeypatch):
    dialog = FakeDialog(None)
    dialog.enqueue(wx.ID_OK, "/tmp/list.phatch", filter_index=2)

    def factory(parent, **options):
        dialog.options = options
        return dialog

    service = FileDialogService(factory)

    selection = service.save_actionlist(
        parent=None,
        message="Save",
        default_dir="/tmp",
        wildcard="*.phatch",
        style=4,
        default_filename="list",
    )

    assert selection == DialogSelection(path="/tmp/list.phatch", filter_index=2)
    assert dialog.options['defaultFile'] == "list"
    assert dialog.options['style'] & 4


def test_dialog_cancel_returns_none():
    dialog = FakeDialog(None)
    dialog.enqueue(False, "/does/not/matter")

    service = FileDialogService(lambda *a, **k: dialog)

    selection = service.open_actionlist(parent=None, message="", default_dir="", wildcard="", style=0)

    assert selection is None
