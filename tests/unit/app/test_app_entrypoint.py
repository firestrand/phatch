from types import SimpleNamespace

import builtins

from phatch import app


if not hasattr(builtins, '_'):
    builtins._ = lambda x: x


def test_main_supports_direct_invocation(monkeypatch, tmp_path):
    options = SimpleNamespace(
        console=True,
        interactive=False,
        init_fonts=False,
        image_inspector=False,
        droplet=False,
        verbose=False,
    )

    monkeypatch.setattr(app, 'parse_options', lambda: (options, []))
    monkeypatch.setattr(app.config, 'load_locale', lambda *args, **kwargs: None)
    monkeypatch.setattr(app.config, 'check_fonts', lambda *args, **kwargs: None)

    captured = {}

    def fake_console(paths, settings):
        captured['paths'] = list(paths)
        captured['console_flag'] = settings['console']

    monkeypatch.setattr(app, '_console', fake_console)
    monkeypatch.setattr(app, '_gui', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('GUI should not run')))
    monkeypatch.setattr(app, '_droplet', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('Droplet should not run')))
    monkeypatch.setattr(app, '_inspect', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('Inspector should not run')))
    monkeypatch.setattr(app, '_init_fonts', lambda *args, **kwargs: None)

    app.main(config_paths={'PHATCH_LOCALE_PATH': str(tmp_path)}, app_file=str(tmp_path / 'app.py'), force_console=True)

    assert captured['paths'] == []
    assert captured['console_flag'] is True
