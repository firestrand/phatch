# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise JSON reporting and exit statuses through the actual launcher."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from phatch.core import api


ROOT = Path(__file__).resolve().parents[2]


def test_fresh_profile_registry_and_spawn_import(tmp_path):
    environment = dict(os.environ)
    for variable in ('XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME'):
        environment[variable] = str(tmp_path / variable)
    program = """
import multiprocessing
import phatch
from phatch.core import api, config
from core import config as legacy_config
from phatch.lib import fonts
from lib import fonts as legacy_fonts

def child():
    from phatch.phatch import main
    assert callable(main)

if __name__ == '__main__':
    paths = phatch.init_config_paths()
    api.import_actions()
    assert config is legacy_config
    assert 'Geek' in api.ACTIONS
    assert fonts.ROOT_FONTS_PATH == legacy_fonts.ROOT_FONTS_PATH
    process = multiprocessing.get_context('spawn').Process(target=child)
    process.start()
    process.join(10)
    assert process.exitcode == 0
"""
    script = tmp_path / 'startup.py'
    script.write_text(program)
    environment['PYTHONPATH'] = str(ROOT)
    result = subprocess.run(
        [sys.executable, str(script)],
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not list(tmp_path.rglob('geek.txt'))


def launch(*arguments):
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / 'bin/phatch'),
            '--console',
            *map(str, arguments),
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )


def recipe(tmp_path):
    api.import_actions()
    action = api.ACTIONS['Save']()
    action.set_field_as_string('In', str(tmp_path / 'outputs'))
    action.set_field_as_string('As', 'png')
    source = tmp_path / 'recipe.phatch'
    api.save_actionlist(str(source), {'actions': [action]})
    return source


def test_cli_dry_run_reports_without_outputs(tmp_path):
    report = tmp_path / 'plan.json'
    result = launch(
        '--dry-run',
        '--report',
        report,
        recipe(tmp_path),
        ROOT / 'tests/input/frog.gif',
    )
    assert result.returncode == 0, result.stderr
    plan = json.loads(report.read_text())
    assert plan['valid']
    assert plan['files'][0]['destinations'][0]['path'] == 'frog.png'
    assert not (tmp_path / 'outputs').exists()


def test_cli_success_report_matches_exit_code(tmp_path):
    report = tmp_path / 'report.json'
    result = launch(
        '--report', report, recipe(tmp_path), ROOT / 'tests/input/frog.gif'
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(report.read_text())
    assert payload['exit_code'] == result.returncode
    assert payload['status'] == 'success'
    assert (tmp_path / 'outputs/frog.png').is_file()


def test_cli_invalid_recipe_has_report_and_nonzero_status(tmp_path):
    source = tmp_path / 'invalid.phatch'
    source.write_text('{"actions": "invalid"}')
    report = tmp_path / 'report.json'
    result = launch('--report', report, source, ROOT / 'tests/input/frog.gif')
    assert result.returncode == 2
    payload = json.loads(report.read_text())
    assert payload['status'] == 'invalid_setup'
    assert payload['exit_code'] == 2


def test_cli_rejects_report_overwriting_source(tmp_path):
    image = tmp_path / 'frog.gif'
    original = (ROOT / 'tests/input/frog.gif').read_bytes()
    image.write_bytes(original)
    result = launch('--report', image, recipe(tmp_path), image)
    assert result.returncode == 2
    assert image.read_bytes() == original


def test_cli_capabilities_needs_no_recipe_or_gui():
    result = launch('--capabilities')
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report['encoders']['PNG']
    assert 'WEBP' in report['encoders']
    assert report['pillow_version']
    assert 'tiffcp' in report['external_tools']


def test_cli_manifest_resume_reports_verified_skip(tmp_path):
    journal = tmp_path / 'manifest.json'
    report = tmp_path / 'report.json'
    source = recipe(tmp_path)
    initial = launch(
        '--manifest', journal, source, ROOT / 'tests/input/frog.gif'
    )
    assert initial.returncode == 0, initial.stderr
    resumed = launch(
        '--manifest',
        journal,
        '--resume',
        '--report',
        report,
        source,
        ROOT / 'tests/input/frog.gif',
    )
    assert resumed.returncode == 0, resumed.stderr
    payload = json.loads(report.read_text())
    assert payload['skipped'] == 1
    assert payload['files'][0]['resumed']


def test_cli_report_cannot_replace_manifest(tmp_path):
    journal = tmp_path / 'manifest.json'
    journal.write_text('previous manifest')
    result = launch(
        '--manifest',
        journal,
        '--report',
        journal,
        recipe(tmp_path),
        ROOT / 'tests/input/frog.gif',
    )
    assert result.returncode == 2
    assert journal.read_text() == 'previous manifest'


def test_cli_variants_reports_images_and_artifact(tmp_path):
    from phatch.core.variants import Variant, variant_action

    api.import_actions()
    action = variant_action(
        [Variant('small', 64, 64, 'png')], tmp_path / 'outputs'
    )
    source = tmp_path / 'variants.phatch'
    api.save_actionlist(str(source), {'actions': [action]})
    report = tmp_path / 'report.json'
    result = launch('--report', report, source, ROOT / 'tests/input/frog.gif')
    assert result.returncode == 0, result.stderr
    payload = json.loads(report.read_text())
    assert payload['files'][0]['outputs'] == ['frog-small.png']
    assert payload['files'][0]['artifacts'] == ['frog-variants.json']
    assert (
        json.loads((tmp_path / 'outputs/frog-variants.json').read_text())[
            'source'
        ]['name']
        == 'frog.gif'
    )


def test_cli_animation_policy_is_explicit(tmp_path):
    from PIL import Image

    source = tmp_path / 'animation.gif'
    first = Image.new('RGB', (16, 10), 'red')
    second = Image.new('RGB', (16, 10), 'blue')
    first.save(
        source,
        save_all=True,
        append_images=[second],
        duration=[40, 80],
        loop=2,
    )
    first.close()
    second.close()
    actions = recipe(tmp_path)
    rejected = launch(actions, source)
    assert rejected.returncode == 2
    assert not (tmp_path / 'outputs').exists()
    result = launch('--animation-policy', 'preserve', actions, source)
    assert result.returncode == 0, result.stderr
    with Image.open(tmp_path / 'outputs/animation.png') as image:
        assert image.n_frames == 2
        assert image.info['loop'] == 2


@pytest.mark.parametrize('backend', ['namespace', 'modern'])
def test_headless_metadata_ignores_incompatible_backend(tmp_path, backend):
    from PIL import Image

    # A neighboring checkout can be importable as a namespace while exposing
    # none of the legacy adapter API. Native Pillow metadata must still work.
    (tmp_path / 'pyexiv2').mkdir()
    if backend == 'modern':
        (tmp_path / 'pyexiv2/__init__.py').write_text(
            'class Image:\n'
            '    def __init__(self, *args):\n'
            '        raise AssertionError("Incompatible backend was used")\n'
            '    def read_exif(self):\n'
            '        return {}\n'
        )
    image_path = tmp_path / 'source.jpg'
    exif = Image.Exif()
    exif[315] = 'Synthetic artist'
    with Image.new('RGB', (24, 12), 'red') as image:
        image.save(image_path, exif=exif)
    environment = dict(os.environ)
    environment['PYTHONPATH'] = str(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / 'bin/phatch'),
            '--console',
            str(recipe(tmp_path)),
            str(image_path),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        env=environment,
    )
    assert result.returncode == 0, result.stderr
    with Image.open(tmp_path / 'outputs/source.png') as output:
        assert output.size == (24, 12)
        assert output.getexif()[315] == 'Synthetic artist'


def test_cli_process_workers_emit_execution_bounds(tmp_path):
    report = tmp_path / 'report.json'
    result = launch(
        '--workers',
        '2',
        '--report',
        report,
        recipe(tmp_path),
        ROOT / 'tests/input/frog.gif',
    )
    assert result.returncode == 0, result.stderr
    execution = json.loads(report.read_text())['execution']
    assert execution['backend'] == 'process'
    assert execution['requested_workers'] == 2
    assert execution['max_in_flight'] == 1


@pytest.mark.parametrize('destination', ['journal', 'report', 'image'])
@pytest.mark.parametrize('workers', [1, 2])
def test_cli_preserves_resource_overlapping_destination(
    tmp_path, destination, workers
):
    from PIL import Image

    api.import_actions()
    source = tmp_path / 'source.png'
    mark = tmp_path / 'mark.png'
    for path, size, color in [
        (source, (40, 20), 'red'),
        (mark, (8, 8), 'blue'),
    ]:
        with Image.new('RGB', size, color) as image:
            image.save(path)
    original = mark.read_bytes()
    watermark = api.ACTIONS['Watermark']()
    watermark.set_field_as_string('Mark', '<folder>/mark.png')
    save = api.ACTIONS['Save']()
    save.set_field_as_string(
        'In', str(tmp_path if destination == 'image' else tmp_path / 'outputs')
    )
    save.set_field_as_string('As', 'png')
    if destination == 'image':
        save.set_field_as_string('File Name', 'mark')
    recipe_path = tmp_path / 'workflow.phatch'
    api.save_actionlist(str(recipe_path), {'actions': [watermark, save]})
    options = ['--workers', workers]
    if destination != 'image':
        options.extend(
            ['--manifest' if destination == 'journal' else '--report', mark]
        )
    result = launch(*options, recipe_path, source)
    assert result.returncode == 2, result.stdout + result.stderr
    assert mark.read_bytes() == original
    assert not (tmp_path / 'outputs').exists()
    if destination == 'report':
        dry_run = launch('--dry-run', '--report', mark, recipe_path, source)
        assert dry_run.returncode == 2, dry_run.stdout + dry_run.stderr
        assert mark.read_bytes() == original


@pytest.mark.parametrize('workers', [1, 2])
@pytest.mark.parametrize('abort', [False, True])
def test_cli_processing_failure_and_abort_reports_agree_with_exit(
    tmp_path, workers, abort
):
    api.import_actions()
    watermark = api.ACTIONS['Watermark']()
    watermark.set_field_as_string('Mark', str(tmp_path / 'missing.png'))
    save = api.ACTIONS['Save']()
    save.set_field_as_string('In', str(tmp_path / 'outputs'))
    save.set_field_as_string('As', 'png')
    recipe_path = tmp_path / 'workflow.phatch'
    api.save_actionlist(str(recipe_path), {'actions': [watermark, save]})
    report_path = tmp_path / 'report.json'
    arguments = [
        sys.executable,
        str(ROOT / 'bin/phatch'),
        '--console',
        '--workers',
        str(workers),
        '--report',
        str(report_path),
    ]
    if abort:
        arguments.append('--interactive')
    arguments.extend([str(recipe_path), str(ROOT / 'tests/input/frog.gif')])
    completed = subprocess.run(
        arguments,
        input='abort\n' if abort else '',
        capture_output=True,
        text=True,
        timeout=20,
    )
    expected = 130 if abort else 1
    assert completed.returncode == expected, (
        completed.stdout + completed.stderr
    )
    report = json.loads(report_path.read_text())
    assert report['exit_code'] == expected
    assert report['status'] == ('cancelled' if abort else 'failed')
    assert report['failed'] == 1
    assert not report['files'][0]['outputs']
    assert not (tmp_path / 'outputs').exists()
