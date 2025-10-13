import builtins
from types import SimpleNamespace

from phatch.pyWx.dialog_service import DialogDependencies, DialogService

if "_" not in builtins.__dict__:
    builtins.__dict__["_"] = lambda value: value


class MessageDialogStub:
    instances = []
    result = 101

    def __init__(self, parent, message, title, style):
        self.parent = parent
        self.message = message
        self.title = title
        self.style = style
        self.destroyed = False
        MessageDialogStub.instances.append(self)

    def ShowModal(self):
        return self.result

    def Destroy(self):
        self.destroyed = True


class ScrolledMessageDialogStub:
    def __init__(self, *args, **kwargs):
        self.destroyed = False

    def ShowModal(self):
        return None

    def Destroy(self):
        self.destroyed = True


class WxAppStub:
    def __init__(self):
        self.settings = {}
        self.report = None
        self.active = False

    def IsActive(self):
        return self.active


class WxStub:
    OK = 1
    ICON_ERROR = 2
    ICON_EXCLAMATION = 4
    ICON_INFORMATION = 8
    ICON_QUESTION = 16
    YES_NO = 32
    CANCEL = 64
    DEFAULT_DIALOG_STYLE = 128
    MAXIMIZE_BOX = 256
    RESIZE_BORDER = 512
    ID_CANCEL = -1
    ID_ABORT = -2
    ID_FORWARD = -3
    ID_NO = -4
    ID_YES = -5
    ID_OK = -6
    MessageDialog = MessageDialogStub

    def __init__(self):
        self.app = WxAppStub()
        self.call_after_invocations = []

    def GetApp(self):
        return self.app

    def CallAfter(self, func, *args, **kwargs):
        self.call_after_invocations.append((func, args, kwargs))
        func(*args, **kwargs)


class WxLibDialogsStub:
    ScrolledMessageDialog = ScrolledMessageDialogStub


class NotifyStub:
    def __init__(self):
        self.calls = []

    def send(self, **payload):
        self.calls.append(payload)


class GraphicsStub:
    def __init__(self):
        self.requests = []

    def bitmap(self, value):
        self.requests.append(value)
        return f"bitmap:{value}"


class SystemStub:
    def __init__(self):
        self.calls = []

    def filename_to_title(self, value):
        self.calls.append(value)
        return f"title:{value}"


class StubFrame:
    def __init__(self):
        self._shown = True
        self._active = False
        self.filename = "/tmp/example.phatch"
        self.attention_requested = False

    def IsShown(self):
        return self._shown

    def set_shown(self, shown: bool):
        self._shown = shown

    def GetSize(self):
        return (320, 240)

    def IsActive(self):
        return self._active

    def set_active(self, active: bool):
        self._active = active

    def RequestUserAttention(self):
        self.attention_requested = True

    def get_icon_filename(self):
        return "/tmp/icon.png"


def build_service():
    wx_stub = WxStub()
    notify_stub = NotifyStub()
    graphics_stub = GraphicsStub()
    system_stub = SystemStub()
    deps = DialogDependencies(
        wx=wx_stub,
        wx_lib_dialogs=WxLibDialogsStub(),
        dialogs=SimpleNamespace(),
        list_data=SimpleNamespace(files_data_dict=lambda x: x, DataDict=object()),
        notify=notify_stub,
        graphics=graphics_stub,
        images=SimpleNamespace(ICON_PHATCH_64="ICON"),
        system=system_stub,
        api=SimpleNamespace(SEE_LOG="See log"),
    )
    frame = StubFrame()
    service = DialogService(frame, dependencies=deps)
    return service, frame, wx_stub, notify_stub, graphics_stub, system_stub


def test_show_message_uses_frame_as_parent_when_visible():
    MessageDialogStub.instances.clear()
    service, frame, wx_stub, *_ = build_service()

    result = service.show_message("Hello", "World")

    assert result == MessageDialogStub.result
    assert MessageDialogStub.instances[-1].parent is frame
    assert MessageDialogStub.instances[-1].message == "Hello"
    assert MessageDialogStub.instances[-1].title.endswith("World")


def test_show_notification_sends_when_inactive_and_updates_report():
    MessageDialogStub.instances.clear()
    service, frame, wx_stub, notify_stub, graphics_stub, system_stub = build_service()
    frame.set_active(False)
    wx_stub.app.active = False

    service.show_notification("Process finished", report=["entry"])

    assert wx_stub.app.report == ["entry"]
    assert len(notify_stub.calls) == 1
    payload = notify_stub.calls[0]
    assert payload["message"] == "Process finished"
    assert payload["icon"] == frame.get_icon_filename()
    assert payload["wxicon"] == "bitmap:ICON"
    assert system_stub.calls == [frame.filename]
    assert frame.attention_requested is True


def test_get_and_set_setting_delegate_to_app():
    service, _, wx_stub, *_ = build_service()

    service.set_setting("key", "value")

    assert wx_stub.app.settings["key"] == "value"
    assert service.get_setting("key") == "value"
