# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Resume verifies content and configuration, including interrupted jobs."""

import json
import os

import pytest
from PIL import Image

from phatch.core import api, manifests
from phatch.core.batch import run_batch


@pytest.mark.parametrize('workers', [1, 2])
def test_expression_resource_change_invalidates_only_affected_input(
    job, tmp_path, workers
):
    actions, source, settings = job
    other = tmp_path / 'second.png'
    other.write_bytes(source.read_bytes())
    marks = tmp_path / 'marks'
    marks.mkdir()
    for path in [source, other]:
        with Image.new('RGBA', (24, 12), 'red') as image:
            image.save(marks / f'{path.stem}.png')
    watermark = api.ACTIONS['Watermark']()
    watermark.set_field_as_string('Mark', '<folder>/marks/<filename>.png')
    actions.insert(0, watermark)
    settings['workers'] = workers
    initial = run_batch(actions, [source, other], settings)
    assert initial.status == 'success', initial.to_dict(include_details=True)
    matching = run_batch(
        actions, [source, other], {**settings, 'resume': True}
    )
    assert matching.skipped == 2
    original = initial.files[0].outputs[0].read_bytes()
    with Image.new('RGBA', (24, 12), 'blue') as image:
        image.save(marks / f'{source.stem}.png')
    refreshed = run_batch(
        actions, [source, other], {**settings, 'resume': True}
    )
    assert refreshed.status == 'success', refreshed.to_dict(
        include_details=True
    )
    assert not refreshed.files[0].resumed
    assert refreshed.files[1].resumed
    assert refreshed.files[0].outputs[0].read_bytes() != original


@pytest.mark.parametrize('workers', [1, 2])
def test_resource_change_during_processing_prevents_completion(
    job, tmp_path, workers
):
    actions, source, settings = job
    mark = tmp_path / 'mark.png'
    with Image.new('RGBA', (24, 12), 'red') as image:
        image.save(mark)
    watermark = api.ACTIONS['Watermark']()
    watermark.set_field_as_string('Mark', str(mark))
    actions.insert(0, watermark)
    settings['workers'] = workers
    changed = False

    def mutate(event):
        nonlocal changed
        if not changed:
            changed = True
            with Image.new('RGBA', (24, 12), 'blue') as image:
                image.save(mark)

    result = run_batch(actions, [source], settings, progress=mutate)
    assert result.status == 'partial_failure', result.to_dict(
        include_details=True
    )
    assert result.files[0].outputs
    record = json.loads(settings['manifest_path'].read_text())['records'][
        str(source)
    ]
    assert record['status'] != 'complete'
    assert not record['outputs']
    retry = run_batch(actions, [source], {**settings, 'resume': True})
    assert retry.status == 'success'
    assert not retry.files[0].resumed


@pytest.mark.parametrize(
    'value, status',
    [
        ('<width>.png', 'failed'),
        ('<unknown>.png', 'invalid_setup'),
        ('missing.png', 'failed'),
    ],
)
def test_unresolved_or_missing_resource_is_not_journaled(job, value, status):
    actions, source, settings = job
    watermark = api.ACTIONS['Watermark']()
    watermark.set_field_as_string('Mark', value)
    actions.insert(0, watermark)
    result = run_batch(actions, [source], settings)
    assert result.status == status, result.to_dict(include_details=True)
    if status == 'failed':
        assert result.files[0].failures[0].action == 'Manifest'
    else:
        assert result.issues
    assert not settings['manifest_path'].exists()
    assert not result.files[0].outputs


@pytest.mark.parametrize('workers', [1, 2])
def test_font_alias_content_change_invalidates_resume_without_cache_write(
    job, tmp_path, test_input_dir, monkeypatch, workers
):
    from lib import fonts

    actions, source, settings = job
    settings['workers'] = workers
    font = tmp_path / 'font.ttf'
    font.write_bytes(
        (test_input_dir.parents[1] / 'data/fonts/FreeSans.ttf').read_bytes()
    )
    cache = tmp_path / 'font-cache'
    monkeypatch.setattr(fonts, '_FONT_DICTIONARY', None)
    monkeypatch.setattr(
        fonts, '_font_dictionary', lambda: {'Review Font': str(font)}
    )
    monkeypatch.setattr(
        fonts, 'USER_FONTS_CACHE_PATH', str(tmp_path / 'missing-user-cache')
    )
    monkeypatch.setattr(
        fonts, 'ROOT_FONTS_CACHE_PATH', str(tmp_path / 'missing-root-cache')
    )
    monkeypatch.setattr(fonts, 'WRITABLE_FONTS_CACHE_PATH', str(cache))
    text = api.ACTIONS['Text']()
    text.set_field_as_string('Font', 'Review Font')
    actions.insert(0, text)
    assert run_batch(actions, [source], settings).status == 'success'
    assert (
        run_batch(actions, [source], {**settings, 'resume': True})
        .files[0]
        .resumed
    )
    with font.open('ab') as stream:
        stream.write(b'\0')
    result = run_batch(actions, [source], {**settings, 'resume': True})
    assert result.status == 'success', result.to_dict(include_details=True)
    assert not result.files[0].resumed
    assert not cache.exists()


@pytest.mark.parametrize('workers', [1, 2])
@pytest.mark.parametrize('policy', ['extract', 'preserve'])
def test_custom_declared_resource_tracks_repeat_and_frame_context(
    job, tmp_path, workers, policy
):
    from tests.fixtures.resource_action import Action

    actions, _, settings = job
    source = tmp_path / 'sequence.png'
    with (
        Image.new('RGB', (20, 10), 'white') as first,
        Image.new('RGB', (20, 10), 'black') as second,
    ):
        first.save(
            source,
            save_all=True,
            append_images=[second],
            duration=[40, 80],
            loop=0,
        )
    for repeat_index in range(2):
        for frame_index in range(2):
            (tmp_path / f'color-{repeat_index}-{frame_index}.txt').write_text(
                'red' if frame_index == 0 else 'green'
            )
    custom = Action()
    custom.set_field_as_string(
        'Color File', '<folder>/color-<repeatindex>-<frameindex>.txt'
    )
    actions.insert(0, custom)
    actions[-1].set_field_as_string('File Name', '<filename>-<repeatindex>')
    settings.update(workers=workers, repeat=2, animation_policy=policy)
    initial = run_batch(actions, [source], settings)
    assert initial.status == 'success', initial.to_dict(include_details=True)
    assert len(initial.files[0].outputs) == (4 if policy == 'extract' else 2)
    matching = run_batch(actions, [source], {**settings, 'resume': True})
    assert matching.files[0].resumed
    (tmp_path / 'color-1-1.txt').write_text('blue')
    refreshed = run_batch(actions, [source], {**settings, 'resume': True})
    assert refreshed.status == 'success', refreshed.to_dict(
        include_details=True
    )
    assert not refreshed.files[0].resumed
    assert len(refreshed.files[0].outputs) == (4 if policy == 'extract' else 2)
    with Image.open(refreshed.files[0].outputs[-1]) as image:
        if policy == 'preserve':
            image.seek(1)
        assert image.getpixel((0, 0))[:3] == (0, 0, 255)


def test_invalid_custom_resource_declaration_is_actionable(job):
    from tests.fixtures.resource_action import Action

    actions, source, settings = job
    custom = Action()
    custom.resource_fields = ('Unknown Field',)
    actions.insert(0, custom)
    result = run_batch(actions, [source], settings)
    assert result.status == 'failed'
    assert 'unknown resource field' in result.files[0].failures[0].message
    assert not settings['manifest_path'].exists()


def test_resumable_contract_requires_boolean_true(job):
    from tests.fixtures.resource_action import Action

    actions, source, settings = job
    custom = Action()
    custom.resumable = 'true'
    actions.insert(0, custom)
    result = run_batch(actions, [source], settings)
    assert result.status == 'invalid_setup'
    assert result.issues[0].code == 'invalid_manifest'
    assert not settings['manifest_path'].exists()


@pytest.fixture
def job(tmp_path, test_input_dir):
    api.import_actions()
    action = api.ACTIONS['Save']()
    action.set_field_as_string('In', str(tmp_path / 'outputs'))
    action.set_field_as_string('As', 'png')
    source = tmp_path / 'source.png'
    with Image.open(test_input_dir / 'frog.gif') as image:
        image.convert('RGB').save(source)
    settings = {'manifest_path': tmp_path / 'job.json'}
    return [action], source, settings


def test_matching_resume_verifies_outputs_without_processing(job):
    actions, source, settings = job
    initial = run_batch(actions, [source], settings)
    assert initial.status == 'success'
    output = initial.files[0].outputs[0]
    modified = output.stat().st_mtime_ns
    events = []
    resumed = run_batch(
        actions, [source], {**settings, 'resume': True}, progress=events.append
    )
    assert resumed.status == 'success'
    assert resumed.skipped == 1
    assert resumed.files[0].resumed
    assert resumed.files[0].outputs == [output]
    assert resumed.to_dict()['files'][0]['resumed'] is True
    assert not events
    assert output.stat().st_mtime_ns == modified


@pytest.mark.parametrize(
    'change', ['source', 'recipe', 'settings', 'plugin', 'output', 'missing']
)
def test_resume_invalidates_changed_work(job, change, monkeypatch):
    actions, source, settings = job
    initial = run_batch(actions, [source], settings)
    output = initial.files[0].outputs[0]
    if change == 'source':
        with Image.open(source) as image:
            image.crop((0, 0, 70, 50)).save(source)
    elif change == 'recipe':
        actions[0].set_field_as_string('Metadata Policy', 'strip')
    elif change == 'settings':
        settings['collision_policy'] = 'replace'
    elif change == 'plugin':
        monkeypatch.setattr(type(actions[0]), 'version', 'test-new-version')
    elif change == 'output':
        output.write_bytes(b'corrupt image')
    elif change == 'missing':
        output.unlink()
    events = []
    result = run_batch(
        actions, [source], {**settings, 'resume': True}, progress=events.append
    )
    assert result.status == 'success', result.to_dict(include_details=True)
    assert not result.files[0].resumed
    assert events
    with Image.open(result.files[0].outputs[0]) as image:
        image.verify()


def test_cancelled_file_is_incomplete_and_resumes(job):
    actions, source, settings = job
    cancelled = False

    def progress(event):
        nonlocal cancelled
        cancelled = True

    result = run_batch(
        actions,
        [source],
        settings,
        progress=progress,
        cancel=lambda: cancelled,
    )
    assert result.status == 'cancelled'
    journal = json.loads(settings['manifest_path'].read_text())
    assert journal['records'][str(source)]['status'] == 'incomplete'
    assert not journal['records'][str(source)]['outputs']
    result = run_batch(actions, [source], {**settings, 'resume': True})
    assert result.status == 'success'
    assert not result.files[0].resumed


def test_completed_inputs_survive_interruption_between_files(job, tmp_path):
    actions, source, settings = job
    other = tmp_path / 'second.png'
    other.write_bytes(source.read_bytes())
    first = run_batch(actions, [source], settings)
    assert first.status == 'success'
    resumed = run_batch(actions, [source, other], {**settings, 'resume': True})
    assert resumed.status == 'success'
    assert resumed.files[0].resumed
    assert not resumed.files[1].resumed


@pytest.mark.parametrize(
    'content',
    [
        '{broken',
        '[]',
        '{"schema_version": 42}',
        '{"schema_version": 1, "records": []}',
    ],
)
def test_corrupt_manifests_fail_before_writing_outputs(job, content):
    actions, source, settings = job
    settings['manifest_path'].write_text(content)
    result = run_batch(actions, [source], {**settings, 'resume': True})
    assert result.status == 'invalid_setup'
    assert any(issue.code == 'invalid_manifest' for issue in result.issues)
    assert not (source.parent / 'outputs').exists()
    assert settings['manifest_path'].read_text() == content


def test_manifest_cannot_overwrite_input_or_output(job):
    actions, source, settings = job
    original = source.read_bytes()
    result = run_batch(actions, [source], {'manifest_path': source})
    assert result.status == 'invalid_setup'
    assert source.read_bytes() == original
    target = source.parent / 'outputs/source.png'
    result = run_batch(actions, [source], {'manifest_path': target})
    assert result.status == 'invalid_setup'
    assert not target.exists()


def test_resume_requires_explicit_manifest(job):
    actions, source, settings = job
    assert (
        run_batch(actions, [source], {'resume': True}).status
        == 'invalid_setup'
    )


def test_resume_preserves_collision_fail_for_changed_work(job):
    actions, source, settings = job
    actions[0].set_field_as_string('Collision Policy', 'fail')
    initial = run_batch(actions, [source], settings)
    assert initial.status == 'success'
    matching = run_batch(actions, [source], {**settings, 'resume': True})
    assert matching.files[0].resumed
    actions[0].set_field_as_string('Metadata Policy', 'strip')
    changed = run_batch(actions, [source], {**settings, 'resume': True})
    assert changed.status == 'failed'
    assert not changed.files[0].resumed


def test_running_record_is_never_accepted_as_complete(job):
    actions, source, settings = job
    run_batch(actions, [source], settings)
    journal = json.loads(settings['manifest_path'].read_text())
    journal['records'][str(source)]['status'] = 'running'
    settings['manifest_path'].write_text(json.dumps(journal))
    result = run_batch(actions, [source], {**settings, 'resume': True})
    assert result.status == 'success'
    assert not result.files[0].resumed


def test_manifest_write_failure_does_not_replace_old_journal(job, monkeypatch):
    actions, source, settings = job
    run_batch(actions, [source], settings)
    original = settings['manifest_path'].read_bytes()

    def fail_commit(self):
        raise OSError('test failure')

    monkeypatch.setattr(manifests.AtomicOutput, '_commit', fail_commit)
    result = run_batch(actions, [source], settings)
    assert result.status == 'failed'
    assert settings['manifest_path'].read_bytes() == original


def test_source_timestamp_change_invalidates_date_dependent_work(job):
    actions, source, settings = job
    run_batch(actions, [source], settings)
    previous = source.stat()
    os.utime(source, ns=(previous.st_atime_ns, previous.st_mtime_ns + 10**9))
    result = run_batch(actions, [source], {**settings, 'resume': True})
    assert result.status == 'success'
    assert not result.files[0].resumed


def test_source_change_during_execution_is_not_recorded_complete(job):
    actions, source, settings = job

    def mutate(event):
        previous = source.stat()
        os.utime(
            source, ns=(previous.st_atime_ns, previous.st_mtime_ns + 10**9)
        )

    result = run_batch(actions, [source], settings, progress=mutate)
    assert result.status == 'partial_failure'
    record = json.loads(settings['manifest_path'].read_text())['records'][
        str(source)
    ]
    assert record['status'] == 'running'
    assert not record['outputs']


def test_side_effecting_actions_are_rejected_for_manifest_jobs(job):
    actions, source, settings = job
    actions.insert(0, api.ACTIONS['Copy']())
    result = run_batch(actions, [source], settings)
    assert result.status == 'invalid_setup'
    assert not settings['manifest_path'].exists()
