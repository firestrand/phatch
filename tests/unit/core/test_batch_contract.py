# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Public batch and planning behavior on the repository's sample image."""

import json

import pytest
from PIL import Image

from phatch.core import api
from phatch.core.batch import plan_batch, run_batch


@pytest.fixture
def workflow(tmp_path):
    api.import_actions()
    save = api.ACTIONS['Save']()
    save.set_field_as_string('In', str(tmp_path / 'outputs'))
    save.set_field_as_string('As', 'png')
    return [api.ACTIONS['Invert'](), save]


def test_engine_returns_verified_output(workflow, test_input_dir):
    result = run_batch(workflow, [test_input_dir / 'frog.gif'])
    assert result.status == 'success'
    assert result.exit_code == 0
    assert result.succeeded == 1
    assert result.files[0].status == 'success'
    with Image.open(result.files[0].outputs[0]) as output:
        output.load()
        assert output.size == (128, 128)


def test_report_hides_paths_and_metadata_by_default(workflow, test_input_dir):
    result = run_batch(workflow, [test_input_dir / 'frog.gif'])
    report = json.dumps(result.to_dict())
    assert str(test_input_dir) not in report
    assert 'frog.gif' in report
    assert 'exif' not in report.lower()


def test_preflight_creates_no_outputs(workflow, test_input_dir, tmp_path):
    result = plan_batch(workflow, [test_input_dir / 'frog.gif'])
    assert result.valid
    assert result.files[0].destinations[0].path == (
        tmp_path / 'outputs/frog.png'
    )
    assert not (tmp_path / 'outputs').exists()


def test_duplicate_destinations_are_detected(
    workflow, test_input_dir, tmp_path
):
    duplicate = tmp_path / 'frog.gif'
    duplicate.write_bytes((test_input_dir / 'frog.gif').read_bytes())
    result = plan_batch(workflow, [test_input_dir / 'frog.gif', duplicate])
    assert not result.valid
    assert any(issue.code == 'collision' for issue in result.issues)


def test_preflight_identifies_overlap(workflow, test_input_dir):
    workflow[-1].set_field_as_string('In', '<folder>')
    workflow[-1].set_field_as_string('As', '<type>')
    result = plan_batch(workflow, [test_input_dir / 'frog.gif'])
    assert any(issue.code == 'source_overlap' for issue in result.issues)


def test_unresolved_preflight_does_not_execute_custom_action(
    workflow, test_input_dir
):
    class Custom:
        label = 'Custom'

        def is_enabled(self):
            return True

        def dump(self):
            return {'label': self.label, 'fields': {}}

        def init(self):
            raise AssertionError('preflight initialized an action')

        def apply(self, *args):
            raise AssertionError('preflight executed an action')

    workflow[-1].set_field_as_string('File Name', '<width>')
    result = plan_batch([Custom(), *workflow], [test_input_dir / 'frog.gif'])
    assert result.files[0].unresolved


def test_cancelled_batch_is_distinguishable(workflow, test_input_dir):
    result = run_batch(
        workflow, [test_input_dir / 'frog.gif'], cancel=lambda: True
    )
    assert result.status == 'cancelled'
    assert result.exit_code == 130
    assert result.files[0].outputs == []


def test_invalid_input_is_a_structured_failure(workflow, tmp_path):
    result = run_batch(workflow, [tmp_path / 'missing.png'])
    assert result.status == 'invalid_setup'
    assert result.exit_code == 2
    assert result.issues


def test_action_failure_isolated_to_input(workflow, test_input_dir, tmp_path):
    class Failure(type(workflow[0])):
        label = 'Failure'

        def apply(self, photo, setting, cache):
            raise ValueError('action rejected input')

    result = run_batch(
        [Failure(), workflow[-1]],
        [test_input_dir / 'frog.gif'],
        settings={'stop_for_errors': False},
    )
    assert result.failed == 1
    assert result.files[0].failures[0].action == 'Failure'
    assert not (tmp_path / 'outputs').exists()


def test_repeat_indices_have_distinct_planned_outputs(
    workflow, test_input_dir
):
    workflow[-1].set_field_as_string('File Name', '<filename>-<index>')
    plan = plan_batch(workflow, [test_input_dir / 'frog.gif'], {'repeat': 2})
    assert [d.path.name for d in plan.files[0].destinations] == [
        'frog-0.png',
        'frog-1.png',
    ]
    result = run_batch(workflow, [test_input_dir / 'frog.gif'], {'repeat': 2})
    assert [p.name for p in result.files[0].outputs] == [
        'frog-0.png',
        'frog-1.png',
    ]


def test_recursive_subfolders_are_preserved(
    workflow, test_input_dir, tmp_path
):
    root = tmp_path / 'inputs'
    nested = root / 'nested'
    nested.mkdir(parents=True)
    (nested / 'frog.gif').write_bytes(
        (test_input_dir / 'frog.gif').read_bytes()
    )
    workflow[-1].set_field_as_string(
        'In', str(tmp_path / 'outputs') + '/<subfolder>'
    )
    result = run_batch(workflow, [root], {'recursive': True})
    assert result.status == 'success'
    assert result.files[0].outputs == [tmp_path / 'outputs/nested/frog.png']


def test_report_path_cannot_overwrite_a_source(workflow, test_input_dir):
    source = test_input_dir / 'frog.gif'
    result = run_batch(workflow, [source], {'report_path': str(source)})
    assert result.status == 'invalid_setup'
    assert any(issue.code == 'artifact_collision' for issue in result.issues)


def test_invalid_repeat_is_setup_error(workflow, test_input_dir):
    result = run_batch(workflow, [test_input_dir / 'frog.gif'], {'repeat': 0})
    assert result.status == 'invalid_setup'


def test_progress_cancellation_prevents_action(workflow, test_input_dir):
    cancelled = False

    def progress(event):
        nonlocal cancelled
        cancelled = True

    result = run_batch(
        workflow,
        [test_input_dir / 'frog.gif'],
        progress=progress,
        cancel=lambda: cancelled,
    )
    assert result.status == 'cancelled'
    assert result.files[0].outputs == []


def test_error_skip_decision_continues_with_next_input(
    workflow, test_input_dir, tmp_path
):
    class Failure(type(workflow[0])):
        label = 'Failure'

        def apply(self, photo, setting, cache):
            raise ValueError('action rejected input')

    second = tmp_path / 'second.gif'
    second.write_bytes((test_input_dir / 'frog.gif').read_bytes())
    result = run_batch(
        [Failure(), workflow[-1]],
        [test_input_dir / 'frog.gif', second],
        on_error=lambda failure, source: 'skip',
    )
    assert result.failed == 2
    assert all(item.status == 'failed' for item in result.files)


def test_service_returns_engine_result(workflow, test_input_dir):
    from phatch.services.action_list import ActionListService
    from phatch.core.settings import DEFAULT_SETTINGS

    settings = dict(DEFAULT_SETTINGS, check_images_first=False)
    result = ActionListService().execute(
        workflow, settings, paths=[str(test_input_dir / 'frog.gif')]
    )
    assert result.status == 'success'


@pytest.mark.parametrize('available_suffix', [9999, None])
def test_rename_preflight_has_same_finite_candidates_as_commit(
    workflow, test_input_dir, tmp_path, monkeypatch, available_suffix
):
    from pathlib import Path

    workflow[-1].set_field_as_string('Collision Policy', 'rename')
    output_folder = tmp_path / 'outputs'
    original_exists = Path.exists
    checked = []

    def occupied(path):
        if path.parent == output_folder:
            checked.append(path.name)
            return path.name != f'frog-{available_suffix}.png'
        return original_exists(path)

    monkeypatch.setattr(Path, 'exists', occupied)
    plan = plan_batch(workflow, [test_input_dir / 'frog.gif'])
    assert len(checked) == 10000
    assert checked[-1] == 'frog-9999.png'
    if available_suffix is None:
        assert not plan.valid
        assert any(
            issue.code == 'collision' and 'limit exceeded' in issue.message
            for issue in plan.issues
        )
        assert not plan.files[0].destinations
    else:
        assert plan.valid, plan.issues
        assert plan.files[0].destinations[0].path.name == 'frog-9999.png'
    assert not output_folder.is_dir()


@pytest.mark.parametrize('workers', [1, 2])
@pytest.mark.parametrize('path_kind', ['direct', 'expression', 'alias'])
@pytest.mark.parametrize(
    'destination_kind', ['journal', 'report', 'image', 'artifact']
)
def test_preflight_protects_read_resources(
    tmp_path, workers, path_kind, destination_kind, monkeypatch
):
    from phatch.core import resources
    from phatch.core.variants import Variant, variant_action

    api.import_actions()
    source = tmp_path / 'source.png'
    mark = tmp_path / (
        'source-variants.json'
        if destination_kind == 'artifact'
        else 'mark.png'
    )
    for path, size, color in [
        (source, (40, 20), 'red'),
        (mark, (8, 8), 'blue'),
    ]:
        with Image.new('RGB', size, color) as image:
            image.save(path, format='PNG')
    before = mark.read_bytes()
    watermark = api.ACTIONS['Watermark']()
    if destination_kind == 'artifact':
        # This fixture permits PNG content at the JSON association path.
        watermark._get_fields()['Mark'].extensions = ['json']
    value = str(mark)
    if path_kind == 'expression':
        value = '<folder>/' + mark.name
    elif path_kind == 'alias':
        watermark._get_fields()['Mark'].dictionary = {'fixture': str(mark)}
        value = 'fixture'
    watermark.set_field_as_string('Mark', value)
    save = api.ACTIONS['Save']()
    save.set_field_as_string('In', str(tmp_path / 'outputs'))
    save.set_field_as_string('As', 'png')
    workflow = [watermark, save]
    settings = {'workers': workers}
    if destination_kind in {'journal', 'report'}:
        settings[
            'manifest_path' if destination_kind == 'journal' else 'report_path'
        ] = mark
    elif destination_kind == 'image':
        save.set_field_as_string('In', str(tmp_path))
        save.set_field_as_string('File Name', 'mark')
    else:
        workflow[-1] = variant_action(
            [Variant('tiny', 10, 10, 'png')], tmp_path
        )
    with monkeypatch.context() as patch:

        def forbidden_hash(*args, **kwargs):
            raise AssertionError('Preflight hashed resource contents')

        patch.setattr(resources, 'file_fingerprint', forbidden_hash)
        plan = plan_batch(workflow, [source], settings)
    assert not plan.valid
    assert mark in plan.resource_paths
    assert any(issue.code == 'resource_overlap' for issue in plan.issues)
    result = run_batch(workflow, [source], settings)
    assert result.status == 'invalid_setup', result.to_dict(
        include_details=True
    )
    assert mark.read_bytes() == before
    assert not (tmp_path / 'outputs').exists()
    with pytest.raises(ValueError, match='overlaps'):
        result.write_report(mark)
    assert mark.read_bytes() == before


@pytest.mark.parametrize('workers', [1, 2])
def test_custom_repeat_frame_resources_are_protected(tmp_path, workers):
    from tests.fixtures.resource_action import Action

    api.import_actions()
    source = tmp_path / 'sequence.gif'
    frames = [Image.new('RGB', (40, 20), color) for color in ('red', 'blue')]
    try:
        frames[0].save(source, save_all=True, append_images=frames[1:])
    finally:
        for frame in frames:
            frame.close()
    resources = []
    for repeat in range(2):
        for frame in range(2):
            path = tmp_path / f'color-{repeat}-{frame}.txt'
            path.write_text('red')
            resources.append(path)
    custom = Action()
    custom.set_field_as_string(
        'Color File', '<folder>/color-<repeatindex>-<frameindex>.txt'
    )
    save = api.ACTIONS['Save']()
    save.set_field_as_string('In', str(tmp_path / 'outputs'))
    save.set_field_as_string('As', 'png')
    settings = {
        'workers': workers,
        'repeat': 2,
        'animation_policy': 'extract',
        'manifest_path': resources[-1],
    }
    plan = plan_batch([custom, save], [source], settings)
    assert set(plan.resource_paths) == set(resources)
    assert any(issue.code == 'resource_overlap' for issue in plan.issues)
    result = run_batch([custom, save], [source], settings)
    assert result.status == 'invalid_setup'
    assert all(path.read_text() == 'red' for path in resources)
    assert not (tmp_path / 'outputs').exists()


def test_plan_protects_one_inputs_resource_from_another_inputs_output(
    tmp_path,
):
    from tests.fixtures.resource_action import Action

    api.import_actions()
    sources = []
    for folder, name in [('left', 'left'), ('right', 'right')]:
        directory = tmp_path / folder
        directory.mkdir()
        source = directory / f'{name}.png'
        with Image.new('RGB', (40, 20), 'red') as image:
            image.save(source)
        (directory / 'color.png').write_text('red')
        sources.append(source)
    custom = Action()
    custom.set_field_as_string('Color File', '<folder>/color.png')
    save = api.ACTIONS['Save']()
    save.set_field_as_string('In', str(tmp_path / 'right'))
    save.set_field_as_string('File Name', 'color')
    save.set_field_as_string('As', 'png')
    settings = {'collision_policy': 'skip'}
    result = run_batch([custom, save], sources, settings)
    assert result.status == 'invalid_setup'
    assert any(issue.code == 'resource_overlap' for issue in result.issues)
    assert (tmp_path / 'right/color.png').read_text() == 'red'
