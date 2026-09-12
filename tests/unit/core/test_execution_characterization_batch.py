import inspect
from types import SimpleNamespace

import pytest
from PIL import Image

from phatch.core import api
from phatch.services.action_list import ActionListService
from phatch.services.execution import ExecutionService


class InfoFileFake:
    @staticmethod
    def split_vars(variables):
        return (), ()

    def __init__(self, vars):
        self.vars = vars


def configure_batch(monkeypatch, events, *, statement=None):
    report = {"source": "photo.jpg", "path": "report.jpg"}

    def is_done(photo):
        events.append("is_done")
        return False

    def apply(photo, settings, cache):
        photo.report_files.append(report)
        return photo

    action = SimpleNamespace(
        label="action",
        init=lambda: None,
        is_done=is_done,
        apply=apply,
    )
    layer = SimpleNamespace(image=Image.new("RGB", (1, 1)))
    photo = SimpleNamespace(
        info=SimpleNamespace(set=lambda *args: None),
        report_files=[],
        get_layer=lambda: layer,
        close=lambda: None,
    )
    monkeypatch.setattr(api, "init_error_log_file", lambda: events.append("log:init"))
    monkeypatch.setattr(api, "check_actionlist", lambda actions, settings: actions)
    monkeypatch.setattr(
        api, "get_paths_and_settings", lambda paths, settings, drop: paths
    )
    monkeypatch.setattr(api, "get_vars", lambda actions: ())
    monkeypatch.setattr(api.metadata, "InfoFile", InfoFileFake)
    monkeypatch.setattr(api.metadata, "InfoExtract", lambda vars: vars)
    monkeypatch.setattr(api, "get_image_infos", lambda *args: [{"path": "photo.jpg"}])
    monkeypatch.setattr(api.pil, "Photo", lambda *args: photo)
    monkeypatch.setattr(api, "flush_log", lambda *args: None)
    monkeypatch.setattr(
        api.pil, "split_vars_static_dynamic", lambda variables: ((), ())
    )
    monkeypatch.setattr(
        api.send,
        "frame_show_progress",
        lambda **kwargs: events.append(
            ("progress:start", kwargs["parent_max"], kwargs["child_max"])
        ),
    )
    monkeypatch.setattr(
        api.send, "progress_close", lambda: events.append("progress:close")
    )
    monkeypatch.setattr(
        api.send,
        "frame_show_notification",
        lambda message, report: events.append(("notification", tuple(report))),
    )
    monkeypatch.setattr(
        api.send, "frame_show_status", lambda *args, **kwargs: events.append("status")
    )

    monkeypatch.setattr(
        api.send,
        "progress_update_filename",
        lambda result, *args: None,
    )
    monkeypatch.setattr(
        api.send,
        "progress_update_index",
        lambda result, *args: result.update(keepgoing=statement != "return"),
    )
    monkeypatch.setattr(api, "ERROR_LOG_COUNTER", 0, raising=False)
    return [action]


def batch_settings(*, overwrite=False, forced=False, no_save=False):
    return {
        "check_images_first": False,
        "extensions": ["jpg"],
        "recursive": False,
        "repeat": 1,
        "overwrite_existing_images": overwrite,
        "overwrite_existing_images_forced": forced,
        "no_save": no_save,
        "stop_for_errors": True,
        "always_show_status_dialog": False,
    }


@pytest.mark.parametrize(
    ("overwrite", "forced", "no_save", "expected_skip"),
    [
        (False, False, False, True),
        (True, False, False, False),
        (False, True, False, False),
        (False, False, True, False),
    ],
)
def test_overwrite_and_no_save_matrix(
    monkeypatch, overwrite, forced, no_save, expected_skip
):
    events = []
    actions = configure_batch(monkeypatch, events)

    api.apply_actions_to_photos(
        actions,
        batch_settings(overwrite=overwrite, forced=forced, no_save=no_save),
        paths=["photo.jpg"],
    )

    assert ("is_done" in events) is expected_skip


def test_cancellation_suppresses_updates_and_completion_messages(monkeypatch):
    events = []
    actions = configure_batch(monkeypatch, events, statement="return")

    result = api.apply_actions_to_photos(
        actions,
        batch_settings(),
        paths=["photo.jpg"],
        update=lambda: events.append("update"),
    )

    assert result is None
    assert events == [
        "log:init",
        ("progress:start", 1, 2),
        "is_done",
        "progress:close",
    ]


def test_legacy_call_returns_none_and_reports_after_file_loop(monkeypatch):
    events = []
    actions = configure_batch(monkeypatch, events)

    result = api.apply_actions_to_photos(
        actions,
        batch_settings(),
        ["photo.jpg"],
        False,
        lambda: events.append("update"),
    )

    assert result is None
    assert events == [
        "log:init",
        ("progress:start", 1, 2),
        "is_done",
        "update",
        "progress:close",
        "update",
        ("notification", ({"source": "photo.jpg", "path": "report.jpg"},)),
    ]


def test_legacy_entrypoint_traverses_typed_execution_service(monkeypatch):
    events = []
    actions = configure_batch(monkeypatch, events)
    calls = []
    execute = ExecutionService.execute

    def observed_execute(service, request):
        calls.append(request)
        return execute(service, request)

    monkeypatch.setattr(ExecutionService, "execute", observed_execute)

    api.apply_actions_to_photos(actions, batch_settings(), ["photo.jpg"])

    assert len(calls) == 1


def test_legacy_entrypoint_processes_a_real_image(monkeypatch, tmp_path):
    source = tmp_path / "source.png"
    output = tmp_path / "output.png"
    Image.new("RGB", (4, 3), "red").save(source)

    class RealImageAction:
        label = "Real image test"
        tags = ("file",)
        metadata = ()
        valid_last = False

        @staticmethod
        def _get_fields():
            return {}

        @staticmethod
        def is_enabled():
            return True

        @staticmethod
        def is_overwrite_existing_images_forced():
            return False

        @staticmethod
        def init():
            return None

        @staticmethod
        def is_done(photo):
            return False

        @staticmethod
        def apply(photo, settings, cache):
            photo.get_layer().image.transpose(Image.Transpose.ROTATE_90).save(output)
            return photo

    monkeypatch.setattr(api, "init_error_log_file", lambda: None)
    monkeypatch.setattr(api, "ERROR_LOG_COUNTER", 0, raising=False)

    api.apply_actions_to_photos(
        [RealImageAction()],
        batch_settings(no_save=True),
        [str(source)],
    )

    with Image.open(output) as processed:
        assert processed.size == (3, 4)


def test_legacy_signature_remains_positional_and_optional():
    signature = inspect.signature(api.apply_actions_to_photos)

    assert list(signature.parameters) == [
        "actions",
        "settings",
        "paths",
        "drop",
        "update",
    ]
    assert signature.parameters["paths"].default is None
    assert signature.parameters["drop"].default is False
    assert signature.parameters["update"].default is None


def test_explicit_update_takes_precedence_over_update_callback():
    captured = []

    def callback():
        return None

    def explicit():
        return None

    service = ActionListService(
        apply_actions_to_photos=lambda *args, **kwargs: captured.append(kwargs)
    )

    result = service.execute([], {}, update_callback=callback, update=explicit)

    assert result is None
    assert captured == [{"update": explicit}]
