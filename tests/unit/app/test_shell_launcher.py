import builtins

if '_' not in builtins.__dict__:
    builtins.__dict__['_'] = lambda value: value

from phatch.core import ct
from phatch.services.shell_launcher import ShellLauncher


class FakeShell:
    def __init__(self, parent, **kwargs):
        self.parent = parent
        self.kwargs = kwargs
        self.visible = []

    def Show(self, checked):
        self.visible.append(checked)


def test_toggle_creates_shell_only_once():
    created = []

    def factory(parent, **kwargs):
        shell = FakeShell(parent, **kwargs)
        created.append(shell)
        return shell

    launcher = ShellLauncher(
        shell_factory=factory,
        icon_provider=lambda: "icon",
        app_provider=lambda: "app",
    )

    class Controller:
        def export_actions(self):
            return []

    controller = Controller()

    launcher.toggle(parent="frame", controller=controller, checked=True)
    launcher.toggle(parent="frame", controller=controller, checked=True)

    assert len(created) == 1
    assert created[0].kwargs['icon'] == "icon"
    assert created[0].kwargs['intro'].strip().endswith(ct.INFO['name'])
    assert created[0].visible == [True, True]


def test_toggle_off_hides_shell():
    shell = FakeShell("frame")

    def factory(*args, **kwargs):
        return shell

    launcher = ShellLauncher(
        shell_factory=factory,
        icon_provider=lambda: "icon",
        app_provider=lambda: "app",
    )

    launcher.toggle(parent="frame", controller=type('C', (), {'export_actions': lambda self: []})(), checked=True)
    launcher.toggle(parent="frame", controller=None, checked=False)

    assert shell.visible == [True, False]
