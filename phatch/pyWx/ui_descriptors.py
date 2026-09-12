"""Reusable descriptors for building wx menus and toolbars."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Sequence, Tuple

try:  # pragma: no cover - exercised in runtime, not tests
    import wx
except ImportError:  # pragma: no cover - used in headless test environments
    class _WxStub:  # minimal shim for unit tests without wxPython
        ITEM_NORMAL = 0
        ITEM_CHECK = 1

        class Menu:  # type: ignore[dead-code]
            pass

        class ToolBar:  # type: ignore[dead-code]
            def AddSeparator(self) -> None:
                raise NotImplementedError("wxPython required for GUI execution")

    wx = _WxStub()  # type: ignore

try:  # pragma: no cover - installed via gettext at runtime
    _  # type: ignore[name-defined]
except NameError:  # pragma: no cover - fallback for tests
    import builtins

    if '_' not in builtins.__dict__:
        builtins.__dict__['_'] = lambda value: value
    _ = builtins.__dict__['_']


@dataclass(frozen=True)
class MenuGroupDescriptor:
    """Defines menu items that toggle with the action-panel state."""

    menu_attr: str
    item_attrs: Tuple[str, ...]


@dataclass(frozen=True)
class ToolbarDescriptor:
    """Specifies a toolbar button to materialise."""

    bitmap: str
    label: str
    tooltip: str
    handler: str
    checkable: bool = False
    toggles_actions: bool = False
    attr_name: str | None = None


@dataclass(frozen=True)
class ToolbarSeparator:
    """Marker that a separator should be inserted."""


def build_menu_groups(frame: object, descriptors: Sequence[MenuGroupDescriptor]) -> List[Tuple[Any, List[int]]]:
    """Return a list of menu/id collections used for enable toggling."""

    groups: List[Tuple[wx.Menu, List[int]]] = []
    for descriptor in descriptors:
        menu = getattr(frame, descriptor.menu_attr)
        ids = [getattr(frame, item_attr).GetId() for item_attr in descriptor.item_attrs]
        groups.append((menu, ids))
    return groups


def build_toolbar(frame: object, toolbar: wx.ToolBar, descriptors: Iterable[object]) -> Tuple[List[int], List[int]]:
    """Create toolbar items from descriptors.

    Returns two lists: (action_toggle_ids, all_tool_ids).
    """

    toggle_ids: List[int] = []
    all_ids: List[int] = []
    for descriptor in descriptors:
        if isinstance(descriptor, ToolbarSeparator):
            toolbar.AddSeparator()
            continue
        if not isinstance(descriptor, ToolbarDescriptor):  # pragma: no cover - defensive
            raise TypeError(f"Unsupported toolbar descriptor: {descriptor!r}")
        item_kind = wx.ITEM_CHECK if descriptor.checkable else wx.ITEM_NORMAL
        tool = frame.add_tool(
            descriptor.bitmap,
            descriptor.label,
            descriptor.tooltip,
            getattr(frame, descriptor.handler),
            item=item_kind,
        )
        tool_id = tool.GetId()
        if descriptor.attr_name:
            setattr(frame, descriptor.attr_name, tool)
        all_ids.append(tool_id)
        if descriptor.toggles_actions:
            toggle_ids.append(tool_id)
    return toggle_ids, all_ids


MENU_ENABLE_GROUPS: Tuple[MenuGroupDescriptor, ...] = (
    MenuGroupDescriptor(
        menu_attr="menu_file",
        item_attrs=("menu_file_new", "menu_file_save", "menu_file_save_as"),
    ),
    MenuGroupDescriptor(
        menu_attr="menu_edit",
        item_attrs=(
            "menu_edit_remove",
            "menu_edit_up",
            "menu_edit_down",
            "menu_edit_enable",
            "menu_edit_disable",
        ),
    ),
    MenuGroupDescriptor(
        menu_attr="menu_view",
        item_attrs=(
            "menu_view_droplet",
            "menu_view_description",
            "menu_view_expand_all",
            "menu_view_collapse_all",
            "menu_view_collapse_automatic",
        ),
    ),
    MenuGroupDescriptor(
        menu_attr="menu_tools",
        item_attrs=("menu_tools_execute", "menu_tools_show_report", "menu_tools_show_log"),
    ),
    MenuGroupDescriptor(
        menu_attr="menu_file_export",
        item_attrs=("menu_file_export_actionlist_to_clipboard",),
    ),
)


TOOLBAR_SPEC: Tuple[object, ...] = (
    ToolbarDescriptor(
        bitmap="ART_FILE_OPEN",
        label=_("Open"),
        tooltip=_("Open a saved list of image-processing steps."),
        handler="on_menu_file_open",
        toggles_actions=False,
    ),
    ToolbarDescriptor(
        bitmap="ART_EXECUTABLE_FILE",
        label=_("Execute"),
        tooltip=_("Choose photos and run all enabled actions in this list."),
        handler="on_menu_tools_execute",
        toggles_actions=True,
    ),
    ToolbarSeparator(),
    ToolbarDescriptor(
        bitmap="ART_ADD_BOOKMARK",
        label=_("Add"),
        tooltip=_("Add an image-processing step, such as resize or rotate."),
        handler="on_menu_edit_add",
        toggles_actions=False,
    ),
    ToolbarDescriptor(
        bitmap="ART_DEL_BOOKMARK",
        label=_("Remove"),
        tooltip=_("Remove the selected action from the list, not your photos."),
        handler="on_menu_edit_remove",
        toggles_actions=True,
    ),
    ToolbarDescriptor(
        bitmap="ART_GO_UP",
        label=_("Up"),
        tooltip=_("Move the selected action earlier in the processing order."),
        handler="on_menu_edit_up",
        toggles_actions=True,
    ),
    ToolbarDescriptor(
        bitmap="ART_GO_DOWN",
        label=_("Down"),
        tooltip=_("Move the selected action later in the processing order."),
        handler="on_menu_edit_down",
        toggles_actions=True,
    ),
    ToolbarSeparator(),
    ToolbarDescriptor(
        bitmap="ART_FIND",
        label=_("Image Inspector"),
        tooltip=_("View photo details and camera metadata (EXIF and IPTC)."),
        handler="on_menu_tools_image_inspector",
        toggles_actions=False,
    ),
    ToolbarSeparator(),
    ToolbarDescriptor(
        bitmap="ART_TIP",
        label=_("Description"),
        tooltip=_("Show or hide notes describing what this action list does."),
        handler="on_menu_view_description",
        toggles_actions=True,
        checkable=True,
        attr_name="toolbar_description",
    ),
)


HELP_LINKS = {
    "website": "https://github.com/firestrand/phatch",
    "documentation": "https://github.com/firestrand/phatch/wiki",
    "forum": "https://github.com/firestrand/phatch/discussions",
    "translate": "https://github.com/firestrand/phatch/wiki",
    "bug": "https://github.com/firestrand/phatch/issues",
}
