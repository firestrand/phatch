# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run with an installed GUI environment from outside the checkout."""

import builtins
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import time


def check_editor_collision_policies(
    frame, source: Path, scratch: Path
) -> None:
    """Exercise edited Save fields through the installed GUI service adapter."""
    from PIL import Image
    from phatch.core import api
    from phatch.core.settings import DEFAULT_SETTINGS

    class Notifications:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    original_sender = api.send
    api.send = Notifications()  # Keep progress/error notifications non-modal.
    try:
        for policy in ('skip', 'fail', 'replace', 'rename'):
            folder = scratch / 'collision-policies' / policy
            folder.mkdir(parents=True)
            target = folder / source.name
            with Image.new('RGB', (64, 32), 'blue') as image:
                image.save(target)
            original = target.read_bytes()
            save = api.ACTIONS['Save']()
            save.set_field_as_string('In', str(folder))
            save.set_field_as_string('As', 'png')
            save.set_field_as_string('Collision Policy', policy)
            frame.controller.apply_loaded_data(
                str(scratch / (policy + '.phatch')),
                [api.ACTIONS['Invert'](), save],
                '',
            )
            edited = list(frame.controller.export_actions())
            assert edited[-1].get_field_string('Collision Policy') == policy
            settings = dict(
                DEFAULT_SETTINGS,
                check_images_first=False,
                always_show_status_dialog=False,
                stop_for_errors=False,
            )
            result = frame.action_service.execute(
                edited, settings, paths=[str(source)]
            )
            assert result is not None
            if policy == 'fail':
                assert result.status == 'invalid_setup'
            else:
                assert result.status == 'success', result.to_dict(
                    include_details=True
                )
            if policy in {'skip', 'fail', 'rename'}:
                assert target.read_bytes() == original
            if policy in {'replace', 'rename'}:
                assert len(result.files[0].outputs) == 1
                output = result.files[0].outputs[0]
                assert (output == target) == (policy == 'replace')
                with Image.open(output) as image:
                    image.load()
                    assert image.size == (64, 32)
                    assert image.getpixel((0, 0)) == (0, 255, 255)
            else:
                assert not result.files[0].outputs
    finally:
        api.send = original_sender


def main() -> None:
    scratch = Path(sys.argv[1]).resolve()
    for key in ('XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME'):
        os.environ[key] = str(scratch / key)
    builtins._ = str
    import phatch
    import wx
    from PIL import Image
    from phatch.core import api, ct
    from phatch.core.settings import DEFAULT_SETTINGS

    paths = phatch.init_config_paths()
    assert '/site-packages/' in phatch.__file__
    api.init()
    from phatch.pyWx import gui
    from phatch.pyWx.workflow_preview import WorkflowPreviewFrame
    from phatch.services import ActionListService

    app = wx.App(False)
    app.settings = deepcopy(DEFAULT_SETTINGS)
    app.report = []
    frame = gui.Frame('', None, -1, ct.TITLE)
    frame.Show()
    preset_path = (
        Path(paths['PHATCH_ACTIONLISTS_PATH']) / 'web_variants.phatch'
    )
    preset = ActionListService().load(str(preset_path))
    frame.controller.apply_loaded_data(
        str(preset_path), preset.actions, preset.description
    )
    assert len(list(frame.controller.export_actions())) == 1
    assert frame.menu_tools.FindItem('Workflow &preview…') != wx.NOT_FOUND
    source = scratch / 'input.png'
    source.parent.mkdir(parents=True, exist_ok=True)
    with Image.new('RGB', (64, 32), 'red') as image:
        image.save(source)
    save = api.ACTIONS['Save']()
    save.set_field_as_string('In', str(scratch / 'outputs'))
    window = WorkflowPreviewFrame(
        frame, source, lambda: [api.ACTIONS['Invert'](), save], lambda: {}
    )
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and window._result is None:
            app.Yield()
            time.sleep(0.01)
        assert window._result is not None
        assert window._result.status == 'success', window._result.failure
        assert window.steps.GetCount() == 2
        assert not (scratch / 'outputs').exists()
        check_editor_collision_policies(frame, source, scratch)
        print(
            json.dumps(
                {
                    'wx': wx.version(),
                    'installed': phatch.__file__,
                    'main_frame': True,
                    'preset': True,
                    'preview': True,
                    'collision_policies': [
                        'skip',
                        'fail',
                        'replace',
                        'rename',
                    ],
                }
            )
        )
    finally:
        window.Close()
        frame.Destroy()
        app.Yield()
        app.Destroy()


if __name__ == '__main__':
    main()
