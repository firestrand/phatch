# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual spawned workers preserve deterministic results and parent contracts."""

import json
import multiprocessing
import threading

import pytest
from PIL import Image

from phatch.core import api
from phatch.core.batch import plan_batch, run_batch


@pytest.fixture
def images(tmp_path):
    result = []
    for index, color in enumerate(['red', 'blue', 'green', 'yellow']):
        path = tmp_path / f'input-{index}.png'
        with Image.new('RGB', (80, 40), color) as image:
            image.save(path)
        result.append(path)
    return result


def workflow(output, name='<filename>-<index>'):
    api.import_actions()
    save = api.ACTIONS['Save']()
    save.set_field_as_string('In', str(output))
    save.set_field_as_string('As', 'png')
    save.set_field_as_string('File Name', name)
    return [api.ACTIONS['Invert'](), save]


def test_worker_pixels_names_order_and_bounds(tmp_path, images):
    serial = run_batch(workflow(tmp_path / 'serial'), images, {'repeat': 2})
    parallel = run_batch(
        workflow(tmp_path / 'parallel'),
        images,
        {'repeat': 2, 'workers': 2},
        mp_context=multiprocessing.get_context('spawn'),
    )
    assert parallel.status == 'success', parallel.to_dict(include_details=True)
    assert [item.source for item in parallel.files] == images
    assert parallel.execution['effective_workers'] == 2
    assert parallel.execution['max_in_flight'] <= 2
    for left, right in zip(serial.files, parallel.files):
        assert [p.name for p in left.outputs] == [
            p.name for p in right.outputs
        ]
        for a, b in zip(left.outputs, right.outputs):
            with Image.open(a) as expected, Image.open(b) as actual:
                assert actual.tobytes() == expected.tobytes()


def test_worker_rename_reservations_are_deterministic(tmp_path, images):
    first = tmp_path / 'a' / 'same.png'
    second = tmp_path / 'b' / 'same.png'
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_bytes(images[0].read_bytes())
    second.write_bytes(images[1].read_bytes())
    actions = workflow(tmp_path / 'outputs', '<filename>')
    settings = {'workers': 2, 'collision_policy': 'rename'}
    plan = plan_batch(actions, [first, second], settings)
    assert plan.valid
    result = run_batch(actions, [first, second], settings)
    assert result.status == 'success', result.to_dict(include_details=True)
    assert [item.outputs[0] for item in result.files] == [
        file.destinations[0].path for file in plan.files
    ]
    with (
        Image.open(result.files[0].outputs[0]) as first_output,
        Image.open(result.files[1].outputs[0]) as second_output,
    ):
        assert first_output.getpixel((0, 0)) == (0, 255, 255)
        assert second_output.getpixel((0, 0)) == (255, 255, 0)


def test_progress_and_cancel_run_on_calling_thread(tmp_path, images):
    owner = threading.get_ident()
    cancelled = False
    events = []

    def progress(event):
        nonlocal cancelled
        assert threading.get_ident() == owner
        events.append(event)
        cancelled = True

    result = run_batch(
        workflow(tmp_path / 'outputs'),
        images,
        {'workers': 2},
        progress=progress,
        cancel=lambda: cancelled,
    )
    assert result.status == 'cancelled', result.to_dict(include_details=True)
    assert events
    assert not any(item.outputs for item in result.files)
    assert all(event.input_count == 4 for event in events)
    assert any(item.status == 'not_started' for item in result.files)


def test_parent_journal_resumes_all_jobs(tmp_path, images):
    actions = workflow(tmp_path / 'outputs')
    settings = {'workers': 2, 'manifest_path': tmp_path / 'journal.json'}
    initial = run_batch(actions, images, settings)
    assert initial.status == 'success', initial.to_dict(include_details=True)
    journal = json.loads(settings['manifest_path'].read_text())
    assert len(journal['records']) == 4
    assert all(
        record['status'] == 'complete'
        for record in journal['records'].values()
    )
    resumed = run_batch(actions, images, {**settings, 'resume': True})
    assert resumed.skipped == 4
    assert all(item.resumed for item in resumed.files)
    initial.files[-1].outputs[0].unlink()
    refreshed = run_batch(actions, images, {**settings, 'resume': True})
    assert refreshed.status == 'success'
    assert refreshed.skipped == 3
    assert refreshed.files[-1].status == 'success'


def test_invalid_worker_counts(tmp_path, images):
    for count in [0, -1, 65, 'two', True]:
        result = run_batch(
            workflow(tmp_path / 'outputs'), images, {'workers': count}
        )
        assert result.status == 'invalid_setup'
    assert not (tmp_path / 'outputs').exists()


def test_memory_budget_rejects_oversized_input_before_writes(tmp_path, images):
    result = run_batch(
        workflow(tmp_path / 'outputs'),
        images,
        {'workers': 2, 'memory_budget_mb': 1},
    )
    assert result.status == 'invalid_setup'
    assert any(issue.code == 'invalid_workers' for issue in result.issues)
    assert not (tmp_path / 'outputs').exists()


def test_unresolved_worker_outputs_rejected(tmp_path, images):
    result = run_batch(
        workflow(tmp_path / 'outputs', '<width>'), images, {'workers': 2}
    )
    assert result.status == 'invalid_setup'
    assert not (tmp_path / 'outputs').exists()


def test_callback_exception_shuts_down_workers(tmp_path, images):
    before = {child.pid for child in multiprocessing.active_children()}

    def broken(event):
        raise ValueError('callback failed')

    with pytest.raises(ValueError, match='callback failed'):
        run_batch(
            workflow(tmp_path / 'outputs'),
            images,
            {'workers': 2},
            progress=broken,
        )
    assert {child.pid for child in multiprocessing.active_children()} == before


def test_one_worker_failure_does_not_corrupt_other_outputs(tmp_path, images):
    from tests.fixtures.worker_action import Action

    actions = [Action(), *workflow(tmp_path / 'outputs')]
    result = run_batch(
        actions, images, {'workers': 2, 'stop_for_errors': False}
    )
    assert result.status == 'partial_failure', result.to_dict(
        include_details=True
    )
    assert result.failed == 1
    assert result.succeeded == 3
    assert result.files[0].failures[0].kind == 'ValueError'
    for item in result.files[1:]:
        with Image.open(item.outputs[0]) as image:
            image.verify()


def test_error_decisions_are_on_parent_and_skip_continues(tmp_path, images):
    from tests.fixtures.worker_action import Action

    owner = threading.get_ident()
    failures = []

    def decide(failure, source):
        assert threading.get_ident() == owner
        failures.append((failure, source))
        return 'skip'

    result = run_batch(
        [Action(), *workflow(tmp_path / 'outputs')],
        images,
        {'workers': 2},
        on_error=decide,
    )
    assert result.succeeded == 3, result.to_dict(include_details=True)
    assert failures[0][1] == images[0]


def test_address_space_limit_is_enforced_and_other_jobs_survive(
    tmp_path, images
):
    from tests.fixtures.worker_action import Action

    action = Action()
    action.set_field_as_string('Mode', 'allocate')
    result = run_batch(
        [action, *workflow(tmp_path / 'outputs')],
        images,
        {'workers': 2, 'memory_budget_mb': 256, 'stop_for_errors': False},
    )
    assert result.status == 'partial_failure', result.to_dict(
        include_details=True
    )
    assert result.files[0].failures[0].kind == 'MemoryError'
    assert result.succeeded == 3
    assert (
        result.execution['per_worker_address_space_limit_bytes']
        == 128 * 1024 * 1024
    )


def test_worker_variants_and_sequences_keep_reserved_outputs(tmp_path, images):
    from phatch.core.variants import Variant, variant_action

    animation = tmp_path / 'animation.gif'
    first = Image.new('RGB', (16, 10), 'red')
    second = Image.new('RGB', (16, 10), 'blue')
    first.save(
        animation, save_all=True, append_images=[second], duration=[40, 80]
    )
    first.close()
    second.close()
    api.import_actions()
    actions = [
        variant_action([Variant('small', 8, 8, 'png')], tmp_path / 'outputs')
    ]
    settings = {'workers': 2, 'animation_policy': 'extract'}
    plan = plan_batch(actions, [animation, images[0]], settings)
    result = run_batch(actions, [animation, images[0]], settings)
    assert result.status == 'success', result.to_dict(include_details=True)
    for item, planned in zip(result.files, plan.files):
        assert set(item.outputs + item.artifacts) == {
            dest.path for dest in planned.destinations
        }


def test_abrupt_worker_exit_is_reported_without_relaunch(tmp_path, images):
    from tests.fixtures.worker_action import Action

    action = Action()
    action.set_field_as_string('Mode', 'crash')
    result = run_batch(
        [action, *workflow(tmp_path / 'outputs')],
        images,
        {'workers': 2, 'stop_for_errors': False},
    )
    assert result.status in {'failed', 'partial_failure'}
    assert any(
        failure.kind == 'BrokenProcessPool'
        for item in result.files
        for failure in item.failures
    )
    assert result.execution['max_in_flight'] <= 2
    assert any(item.status == 'not_started' for item in result.files)


@pytest.mark.parametrize('mode', ['crash_encode', 'crash_committed'])
@pytest.mark.parametrize('policy', ['replace', 'rename'])
def test_crash_during_output_recovers_only_owned_files(
    tmp_path, images, mode, policy
):
    from tests.fixtures.worker_action import Action

    output = tmp_path / 'outputs'
    output.mkdir()
    target = output / 'input-0-0.png'
    target.write_bytes(images[1].read_bytes())
    original = target.read_bytes()
    foreign = output / '.input-0-0-foreign.png'
    foreign.write_bytes(b'another writer owns this file')
    action = Action()
    action.set_field_as_string('Mode', mode)
    actions = [action, workflow(output)[-1]]
    settings = {
        'workers': 2,
        'stop_for_errors': False,
        'collision_policy': policy,
        'manifest_path': tmp_path / 'journal.json',
    }
    planned = plan_batch(actions, images, settings)
    committed = planned.files[0].destinations[0].path
    result = run_batch(
        actions,
        images,
        settings,
    )
    assert result.files[0].status == 'failed'
    assert list(output.glob('.input-0-0-*')) == [foreign]
    assert foreign.read_bytes() == b'another writer owns this file'
    if mode == 'crash_encode':
        assert target.read_bytes() == original
        assert result.files[0].outputs == []
    else:
        assert result.status == 'partial_failure'
        assert result.files[0].outputs == [committed]
        if policy == 'rename':
            assert target.read_bytes() == original
        with Image.open(committed) as image:
            assert image.getpixel((0, 0)) == (255, 0, 0)
    journal = json.loads((tmp_path / 'journal.json').read_text())
    record = journal['records'][str(images[0])]
    assert record['status'] == 'incomplete'


def test_crash_after_variant_manifest_reports_images_and_artifact(
    tmp_path, images
):
    from tests.fixtures.worker_action import Action
    from phatch.core.variants import Variant, variant_action

    action = Action()
    action.set_field_as_string('Mode', 'crash_artifact')
    actions = [
        action,
        variant_action(
            [Variant('small', 20, 20, 'png')], tmp_path / 'outputs'
        ),
    ]
    # Isolate the registered transaction being crashed. Other workers killed
    # by the broken pool can stop before their registration handshake.
    sources = images[:1]
    planned = plan_batch(actions, sources, {'workers': 2})
    result = run_batch(
        actions, sources, {'workers': 2, 'stop_for_errors': False}
    )
    assert result.files[0].status == 'failed'
    assert set(result.files[0].outputs + result.files[0].artifacts) == {
        dest.path for dest in planned.files[0].destinations
    }
    assert len(result.files[0].artifacts) == 1
    assert json.loads(result.files[0].artifacts[0].read_text())
    assert not list((tmp_path / 'outputs').glob('.*'))


def test_crash_cleanup_preserves_replacement_at_registered_temp(
    tmp_path, images
):
    from tests.fixtures.worker_action import Action

    action = Action()
    action.set_field_as_string('Mode', 'crash_encode_foreign')
    output = tmp_path / 'outputs'
    result = run_batch(
        [action, workflow(output)[-1]],
        images,
        {'workers': 2, 'stop_for_errors': False},
    )
    assert result.files[0].status == 'failed'
    (replacement,) = output.glob('.input-0-0-*')
    assert replacement.read_bytes() == b'partial encoding'
    assert not (output / 'input-0-0.png').exists()


def test_crash_during_pipe_message_recovers_committed_output(tmp_path, images):
    from tests.fixtures.worker_action import Action

    action = Action()
    action.set_field_as_string('Mode', 'crash_transport')
    output = tmp_path / 'outputs'
    result = run_batch(
        [action, workflow(output)[-1]], images[:1], {'workers': 2}
    )
    assert result.status == 'partial_failure'
    assert result.files[0].status == 'failed'
    assert result.files[0].outputs == [output / 'input-0-0.png']
    with Image.open(result.files[0].outputs[0]) as image:
        assert image.getpixel((0, 0)) == (255, 0, 0)
    assert not list(output.glob('.*'))


def test_crash_while_checking_cancel_does_not_strand_parent(tmp_path, images):
    from tests.fixtures.worker_action import Action

    action = Action()
    action.set_field_as_string('Mode', 'crash_cancel')
    output = tmp_path / 'outputs'
    result = run_batch(
        [action, workflow(output)[-1]], images[:1], {'workers': 2}
    )
    assert result.status == 'failed'
    assert result.files[0].status == 'failed'
    assert not result.files[0].outputs


def test_cancel_notification_is_visible_to_every_reader_until_closed():
    from phatch.core.workers import _Cancellation, _CancellationView

    cancellation = _Cancellation(multiprocessing.get_context('spawn'))
    readers = [_CancellationView(cancellation.reader) for _ in range(3)]
    try:
        assert not any(reader.is_set() for reader in readers)
        cancellation.set()
        cancellation.set()
        assert cancellation.is_set()
        for _ in range(3):
            assert all(reader.is_set() for reader in readers)
    finally:
        cancellation.close()
    assert cancellation.reader.closed and cancellation.writer.closed
