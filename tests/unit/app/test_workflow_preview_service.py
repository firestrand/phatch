# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Race checks use explicit events and actual owned background workers."""

from queue import Queue
import threading
import weakref

import pytest

from phatch.core.workflow_preview import PreviewResult
from phatch.services.workflow_preview import WorkflowPreviewService


def test_ui_queued_stale_result_cannot_overwrite_new_request():
    deliveries = Queue()
    results = []

    class Renderer:
        def render(self, source, *args, **kwargs):
            return PreviewResult('success', cache_key=str(source))

    with WorkflowPreviewService(
        deliveries.put, renderer=Renderer()
    ) as service:
        service.submit('old', [], results.append)
        old_delivery = deliveries.get(timeout=3)
        service.submit('new', [], results.append)
        new_delivery = deliveries.get(timeout=3)
        old_delivery()
        new_delivery()
    assert [result.cache_key for result in results] == ['new']


def test_superseded_running_work_is_cancelled_and_latest_request_delivered():
    deliveries = Queue()
    entered = threading.Event()
    release = threading.Event()
    calls = []

    class Renderer:
        def render(self, source, *args, cancel, **kwargs):
            calls.append(source)
            if source == 'old':
                entered.set()
                assert release.wait(3)
                assert cancel()
            return PreviewResult('success', cache_key=str(source))

    results = []
    with WorkflowPreviewService(
        deliveries.put, renderer=Renderer()
    ) as service:
        service.submit('old', [], results.append)
        assert entered.wait(3)
        service.submit('discarded', [], results.append)
        service.submit('latest', [], results.append)
        release.set()
        deliveries.get(timeout=3)()
    assert calls == ['old', 'latest']
    assert [result.cache_key for result in results] == ['latest']


def test_parameter_invalidation_suppresses_already_queued_delivery():
    deliveries = Queue()
    results = []

    class Renderer:
        def render(self, *args, **kwargs):
            return PreviewResult('success')

    with WorkflowPreviewService(
        deliveries.put, renderer=Renderer()
    ) as service:
        service.submit('source', [], results.append)
        delivery = deliveries.get(timeout=3)
        service.invalidate()
        delivery()
    assert not results


def test_close_suppresses_ui_delivery_and_rejects_new_jobs():
    deliveries = Queue()
    results = []

    class Renderer:
        def render(self, *args, **kwargs):
            return PreviewResult('success')

    service = WorkflowPreviewService(deliveries.put, renderer=Renderer())
    service.submit('source', [], results.append)
    delivery = deliveries.get(timeout=3)
    service.close()
    delivery()
    assert not results
    with pytest.raises(RuntimeError, match='closed'):
        service.submit('source', [], results.append)


def test_worker_failure_is_delivered_as_visible_result():
    deliveries = Queue()
    results = []

    class Renderer:
        def render(self, *args, **kwargs):
            raise ValueError('test worker failure')

    with WorkflowPreviewService(
        deliveries.put, renderer=Renderer()
    ) as service:
        service.submit('source', [], results.append)
        deliveries.get(timeout=3)()
    assert results[0].status == 'failed'
    assert results[0].failure.kind == 'ValueError'


def test_invalid_snapshot_supersedes_old_queued_result():
    deliveries = Queue()
    results = []

    class Renderer:
        def render(self, *args, **kwargs):
            return PreviewResult('success')

    class InvalidAction:
        def is_enabled(self):
            raise ValueError('test snapshot failure')

    with WorkflowPreviewService(
        deliveries.put, renderer=Renderer()
    ) as service:
        service.submit('old', [], results.append)
        old = deliveries.get(timeout=3)
        service.submit('new', [InvalidAction()], results.append)
        new = deliveries.get(timeout=3)
        old()
        new()
    assert len(results) == 1
    assert results[0].status == 'failed'
    assert results[0].failure.action == 'Preview setup'


def test_rapid_edits_retain_only_current_and_latest_snapshots():
    deliveries = Queue()
    entered = threading.Event()
    release = threading.Event()
    instances = weakref.WeakSet()

    class Action:
        preview_safe = True
        label = 'Pure test action'

        def __init__(self):
            instances.add(self)

        def is_enabled(self):
            return True

        def dump(self):
            return {'fields': {}}

        def load(self, fields):
            return []

        def _get_fields(self):
            return {}

    class Renderer:
        def render(self, source, *args, **kwargs):
            if source == 'old':
                entered.set()
                assert release.wait(3)
            return PreviewResult('success', cache_key=source)

    original = Action()
    results = []
    with WorkflowPreviewService(
        deliveries.put, renderer=Renderer()
    ) as service:
        service.submit('old', [original], results.append)
        assert entered.wait(3)
        try:
            for index in range(100):
                service.submit(str(index), [original], results.append)
            # One caller-owned original, one running snapshot, one pending.
            assert len(instances) <= 3
        finally:
            release.set()
        deliveries.get(timeout=3)()
    assert [result.cache_key for result in results] == ['99']


def test_cancelled_queued_future_never_runs_renderer(monkeypatch):
    from concurrent.futures import Future
    from phatch.services import workflow_preview

    attempted = threading.Event()
    delivered = []

    class CancelledFuture(Future):
        def __init__(self):
            super().__init__()
            self.cancel()

        def set_running_or_notify_cancel(self):
            result = super().set_running_or_notify_cancel()
            attempted.set()
            return result

    class Renderer:
        def render(self, *args, **kwargs):
            pytest.fail('Cancelled queued job must not render')

    monkeypatch.setattr(workflow_preview, 'Future', CancelledFuture)
    with WorkflowPreviewService(lambda callback: callback(), renderer=Renderer()) as service:
        service.submit('source', [], delivered.append)
        assert attempted.wait(3)
    assert not delivered
