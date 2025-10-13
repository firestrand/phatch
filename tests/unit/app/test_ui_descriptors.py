import builtins

if '_' not in builtins.__dict__:
    builtins.__dict__['_'] = lambda value: value

from phatch.pyWx.ui_descriptors import (
    MenuGroupDescriptor,
    ToolbarDescriptor,
    ToolbarSeparator,
    build_menu_groups,
    build_toolbar,
)


class DummyMenu:
    pass


class DummyMenuItem:
    def __init__(self, value):
        self._value = value

    def GetId(self):
        return self._value


class DummyTool:
    def __init__(self, value):
        self._value = value

    def GetId(self):
        return self._value


class DummyToolbar:
    def __init__(self):
        self.separators = 0

    def AddSeparator(self):
        self.separators += 1


class DummyFrame:
    def __init__(self):
        self.menu_file = DummyMenu()
        self.menu_edit = DummyMenu()
        self.menu_file_new = DummyMenuItem(10)
        self.menu_file_save = DummyMenuItem(11)
        self.menu_file_save_as = DummyMenuItem(12)
        self.menu_edit_remove = DummyMenuItem(20)
        self.menu_edit_up = DummyMenuItem(21)
        self.menu_edit_down = DummyMenuItem(22)
        self.menu_edit_enable = DummyMenuItem(23)
        self.menu_edit_disable = DummyMenuItem(24)
        self.generated = []
        self._tool_id = 30

    def add_tool(self, bitmap, label, tooltip, handler, item):
        self.generated.append((bitmap, label, tooltip, handler.__name__, item))
        tool = DummyTool(self._tool_id)
        self._tool_id += 1
        return tool

    # Handlers referenced by descriptors
    def on_menu_file_open(self):  # pragma: no cover - not executed
        raise NotImplementedError

    def on_menu_tools_execute(self):  # pragma: no cover - not executed
        raise NotImplementedError

    def on_menu_edit_add(self):  # pragma: no cover - not executed
        raise NotImplementedError

    def on_menu_edit_remove(self):  # pragma: no cover - not executed
        raise NotImplementedError

    def on_menu_edit_up(self):  # pragma: no cover - not executed
        raise NotImplementedError

    def on_menu_edit_down(self):  # pragma: no cover - not executed
        raise NotImplementedError

    def on_menu_tools_image_inspector(self):  # pragma: no cover - not executed
        raise NotImplementedError

    def on_menu_view_description(self):  # pragma: no cover - not executed
        raise NotImplementedError


def test_build_menu_groups_collects_ids():
    frame = DummyFrame()
    descriptors = [
        MenuGroupDescriptor("menu_file", ("menu_file_new", "menu_file_save")),
        MenuGroupDescriptor("menu_edit", ("menu_edit_remove",)),
    ]

    groups = build_menu_groups(frame, descriptors)

    assert groups == [
        (frame.menu_file, [10, 11]),
        (frame.menu_edit, [20]),
    ]


def test_build_toolbar_creates_tools_and_tracks_ids():
    frame = DummyFrame()
    toolbar = DummyToolbar()
    descriptors = [
        ToolbarDescriptor(
            bitmap="ART_FILE_OPEN",
            label="Open",
            tooltip="Open an action list",
            handler="on_menu_file_open",
            toggles_actions=False,
        ),
        ToolbarSeparator(),
        ToolbarDescriptor(
            bitmap="ART_EXECUTABLE_FILE",
            label="Execute",
            tooltip="Execute the action",
            handler="on_menu_tools_execute",
            toggles_actions=True,
            checkable=True,
            attr_name="toolbar_execute",
        ),
    ]

    toggle_ids, all_ids = build_toolbar(frame, toolbar, descriptors)

    assert all_ids == [30, 31]
    assert toggle_ids == [31]
    assert toolbar.separators == 1
    assert frame.toolbar_execute.GetId() == 31
    assert frame.generated[0][0] == "ART_FILE_OPEN"
