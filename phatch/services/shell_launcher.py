"""Encapsulates creation and toggling of the embedded Python shell."""

from __future__ import annotations

from typing import Any, Callable, Optional

from phatch.core import ct

try:  # pragma: no cover - provided by gettext at runtime
    _  # type: ignore[name-defined]
except NameError:  # pragma: no cover - fallback for tests
    import builtins

    if '_' not in builtins.__dict__:
        builtins.__dict__['_'] = lambda value: value
    _ = builtins.__dict__['_']


class ShellLauncher:
    """Creates and toggles the interactive shell window."""

    def __init__(
        self,
        shell_factory: Callable[..., Any],
        icon_provider: Callable[[], Any],
        app_provider: Callable[[], Any],
    ) -> None:
        self._shell_factory = shell_factory
        self._icon_provider = icon_provider
        self._app_provider = app_provider
        self._shell: Optional[Any] = None

    def toggle(self, parent: Any, controller: Any, checked: bool) -> None:
        if self._shell is None and checked:
            self._shell = self._create_shell(parent, controller)
        if self._shell is not None:
            self._shell.Show(checked)

    # --- internal helpers -----------------------------------------
    def _create_shell(self, parent: Any, controller: Any) -> Any:
        title_key = ct.TITLE.lower()
        app = self._app_provider()
        values = {
            f"{title_key}_{_('application')}": app,
            f"{title_key}_{_('frame')}": parent,
            f"{title_key}_{_('actions')}": controller.export_actions,
        }
        return self._shell_factory(
            parent,
            title=_('%(name)s Shell') % ct.INFO,
            intro='%(name)s ' % ct.INFO,
            values=values,
            icon=self._icon_provider(),
        )
