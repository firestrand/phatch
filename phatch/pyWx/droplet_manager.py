"""Encapsulates droplet frame lifecycle and validation."""

from __future__ import annotations

from typing import Callable, Iterable, Optional, Protocol, Sequence


class DropletFrame(Protocol):
    def show(self, visible: bool) -> None: ...


class DropletManager:
    """Coordinates creation and visibility of the droplet helper window."""

    def __init__(
        self,
        export_actions: Callable[[], Sequence[object]],
        settings_provider: Callable[[], dict],
        check_actionlist: Callable[[Iterable[object], dict], bool],
        create_frame: Callable[[], DropletFrame],
        schedule_hide: Callable[[], None],
        state_callback: Callable[[bool], None],
    ) -> None:
        self._export_actions = export_actions
        self._settings_provider = settings_provider
        self._check_actionlist = check_actionlist
        self._create_frame = create_frame
        self._schedule_hide = schedule_hide
        self._state_callback = state_callback
        self._frame: Optional[DropletFrame] = None

    def toggle(self, checked: bool) -> None:
        if checked:
            actions = list(self._export_actions())
            settings = self._settings_provider()
            if self._check_actionlist(actions, settings):
                if self._frame is None:
                    self._frame = self._create_frame()
                self._frame.show(True)
                self._state_callback(True)
            else:
                self._schedule_hide()
        else:
            if self._frame is not None:
                self._frame.show(False)
            self._state_callback(False)

    def handle_show_event(self, visible: bool) -> None:
        if not visible:
            self._frame = None
        self._state_callback(visible)
