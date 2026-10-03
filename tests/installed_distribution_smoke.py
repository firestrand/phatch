# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run with an installed environment's Python from outside the checkout."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('scratch', type=Path)
    arguments = parser.parse_args()
    scratch = arguments.scratch.resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    for key, folder in (
        ('XDG_CONFIG_HOME', 'config'),
        ('XDG_CACHE_HOME', 'cache'),
        ('XDG_DATA_HOME', 'data'),
    ):
        os.environ[key] = str(scratch / folder)

    import phatch
    from PIL import Image, __version__ as pillow_version
    from phatch.core import api
    from phatch.core.batch import run_batch
    from phatch.core.workflow_preview import PreviewRenderer
    from phatch.services import ActionListService

    checkout = Path(__file__).resolve().parents[1]
    assert not Path(phatch.__file__).resolve().is_relative_to(checkout)
    assert importlib.util.find_spec('wx') is None, 'Use a headless environment'
    paths = phatch.init_config_paths()
    api.import_actions()
    resources = Path(paths['PHATCH_ACTIONLISTS_PATH'])
    assert (resources / 'resize.phatch').is_file()
    assert (Path(paths['PHATCH_FONTS_PATH']) / 'FreeSans.ttf').is_file()
    preset = ActionListService().load(str(resources / 'web_variants.phatch'))
    variants = preset.actions
    variants[0].set_field_as_string('In', str(scratch / 'variants'))
    variants[0].set_field_as_string('Format Fallback', 'png')
    sources = []
    for index, color in enumerate(['red', 'blue']):
        source = scratch / f'input-{index}.png'
        with Image.new('RGB', (64, 32), color) as image:
            image.save(source)
        sources.append(source)
    variant_result = run_batch(variants, sources)
    assert variant_result.status == 'success', variant_result.to_dict(
        include_details=True
    )
    assert all(
        len(item.outputs) == 6 and len(item.artifacts) == 1
        for item in variant_result.files
    )

    text = api.ACTIONS['Text']()
    text.set_field_as_string('Font', 'Free Sans')
    text.set_field_as_string('Size', '12px')
    save = api.ACTIONS['Save']()
    save.set_field_as_string('In', str(scratch / 'saved'))
    save.set_field_as_string('As', 'png')
    actions = [text, save]
    recipe = scratch / 'recipe.phatch'
    ActionListService().save(str(recipe), 'Installed wheel smoke', actions)
    preview = PreviewRenderer().render(sources[0], actions)
    assert preview.status == 'success', preview.failure
    assert not (scratch / 'saved').exists()
    executable = Path(sys.executable).parent / 'phatch'

    def launch(*options: str | Path) -> dict[str, object]:
        result = subprocess.run(
            [str(executable), '--console', *map(str, options)],
            cwd=scratch,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads(result.stdout) if '--capabilities' in options else {}

    capabilities = launch('--capabilities')
    launch('--dry-run', '--report', scratch / 'plan.json', recipe, *sources)
    assert json.loads((scratch / 'plan.json').read_text())['valid']
    assert not (scratch / 'saved').exists()
    shared = ['--workers', '2', '--manifest', scratch / 'journal.json']
    launch(*shared, '--report', scratch / 'first.json', recipe, *sources)
    first = json.loads((scratch / 'first.json').read_text())
    assert first['status'] == 'success' and first['succeeded'] == 2
    assert first['execution']['backend'] == 'process'
    launch(
        *shared,
        '--resume',
        '--report',
        scratch / 'resumed.json',
        recipe,
        *sources,
    )
    resumed = json.loads((scratch / 'resumed.json').read_text())
    assert resumed['skipped'] == 2 and all(
        item['resumed'] for item in resumed['files']
    )
    for source in sources:
        with Image.open(scratch / 'saved' / source.name) as image:
            assert image.size == (64, 32)
            image.verify()
    print(
        json.dumps(
            {
                'python': platform.python_version(),
                'pillow': pillow_version,
                'installed_module': str(Path(phatch.__file__).resolve()),
                'variants': sum(
                    len(item.outputs) for item in variant_result.files
                ),
                'resumed': resumed['skipped'],
                'capabilities': capabilities,
            },
            sort_keys=True,
        )
    )


if __name__ == '__main__':
    main()
