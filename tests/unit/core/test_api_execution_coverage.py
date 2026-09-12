from io import StringIO

from phatch.core import api


class ActionFake:
    label = "Action"
    metadata = ()

    def __init__(self, *, error=False):
        self.error = error
        self.fields = {}

    def dump(self):
        return {"label": self.label}

    def _get_fields(self):
        return self.fields

    def apply(self, photo, settings, cache):
        if self.error:
            raise ValueError("apply")
        return photo


class ImageFake:
    def copy(self):
        return self


class LayerFake:
    def __init__(self):
        self.image = ImageFake()


class PhotoFake:
    def __init__(self):
        self.closed = False
        self.report_files = [{"path": "out.png"}]
        self.layer = LayerFake()
        self.info = InfoFake()

    def close(self):
        self.closed = True

    def get_layer(self):
        return self.layer

    def get_log(self) -> str:
        return ""

    def clear_log(self):
        return None


class InfoFake:
    def __init__(self):
        self.values = {"path": "in.png", "index": 0}

    def __getitem__(self, key):
        return self.values[key]

    def set(self, key, value):
        self.values[key] = value


def test_log_error_and_unsafe_action(monkeypatch):
    monkeypatch.setattr(api, "ERROR_LOG_FILE", StringIO(), raising=False)
    monkeypatch.setattr(api, "ERROR_LOG_COUNTER", 0, raising=False)
    monkeypatch.setattr(api.traceback, "print_exc", lambda file: file.write("trace"))
    details = api.log_error("bad", "in.png", ActionFake())
    assert "Action" in details
    assert api.ERROR_LOG_COUNTER == 1

    class UnsafeField:
        def assert_safe(self, label, info):
            raise ValueError("unsafe")

    action = ActionFake()
    action.label = "Geek"
    action.fields = {"Expression": UnsafeField(), "_hidden": object()}
    assert "unsafe" in api.assert_safe([action])


def test_verify_images_dialog_paths(monkeypatch):
    infos = [{"path": "good.png"}, {"path": "bad.png"}]
    monkeypatch.setattr(api.send, "frame_show_progress", lambda **kwargs: None)
    monkeypatch.setattr(api.send, "progress_close", lambda: None)
    monkeypatch.setattr(
        api.send,
        "progress_update_filename",
        lambda result, *args: result.update(keepgoing=True),
    )

    def verify(info, valid, invalid):
        (valid if info["path"] == "good.png" else invalid).append(info)

    monkeypatch.setattr(api.openImage, "verify_image", verify)
    monkeypatch.setattr(
        api.send,
        "frame_show_files_message",
        lambda result, **kwargs: result.update(cancel=False),
    )
    monkeypatch.setattr(
        api.send,
        "frame_show_image_tree",
        lambda result, *args, **kwargs: result.update(answer=True),
    )
    assert api.verify_images(infos, 2) == [infos[0]]
    assert infos[0]["index"] == 0

    monkeypatch.setattr(
        api.send,
        "progress_update_filename",
        lambda result, *args: result.update(keepgoing=False),
    )
    assert api.verify_images(infos, 1) is None

    monkeypatch.setattr(
        api.send,
        "progress_update_filename",
        lambda result, *args: result.update(keepgoing=True),
    )
    monkeypatch.setattr(
        api.openImage, "verify_image", lambda info, valid, invalid: invalid.append(info)
    )
    monkeypatch.setattr(
        api.send,
        "frame_show_files_message",
        lambda result, **kwargs: result.update(cancel=True),
    )
    assert api.verify_images(infos, 1) is None

    monkeypatch.setattr(
        api.send,
        "frame_show_files_message",
        lambda result, **kwargs: result.update(cancel=False),
    )
    monkeypatch.setattr(api.send, "frame_show_error", lambda message: None)
    assert api.verify_images(infos, 1) is None


def test_path_dialog_boundaries(monkeypatch):
    errors = []
    monkeypatch.setattr(api.send, "frame_show_error", errors.append)
    monkeypatch.setattr(
        api.send,
        "frame_show_execute_dialog",
        lambda result, settings, paths: result.update(cancel=True),
    )
    assert api.get_paths_and_settings(None, {"paths": []}) is None

    monkeypatch.setattr(
        api.send,
        "frame_show_execute_dialog",
        lambda result, settings, paths: result.update(cancel=False),
    )
    assert api.get_paths_and_settings(None, {"paths": []}) is None
    assert errors
    assert api.get_paths_and_settings(["a"], {}) == ["a"]


def test_action_list_file_boundaries(monkeypatch, tmp_path):
    action_list = tmp_path / "actions"
    previous = tmp_path / "actions.phatch~"
    current = tmp_path / "actions.phatch"
    previous.write_text("old backup", encoding="utf-8")
    current.write_text("old", encoding="utf-8")
    api.save_actionlist(str(action_list), {"actions": [ActionFake()]})
    assert current.is_file()
    assert previous.read_text(encoding="utf-8") == "old"

    invalid = tmp_path / "invalid.phatch"
    invalid.write_text("not valid json or a literal", encoding="utf-8")
    errors = []
    monkeypatch.setattr(api.send, "frame_show_error", errors.append)
    assert api.open_actionlist(str(invalid)) is None
    assert errors

    schema_without_registry = tmp_path / "schema-without-registry.phatch"
    schema_without_registry.write_text(
        '{"schema_version": 3, "description": "empty", "actions": []}',
        encoding="utf-8",
    )
    monkeypatch.setattr(api, "ACTIONS", {})
    assert api.open_actionlist(str(schema_without_registry)) is None
    assert len(errors) == 2


def test_remaining_dialog_and_resume_branches(monkeypatch):
    info = {"path": "good.png"}
    monkeypatch.setattr(api.send, "frame_show_progress", lambda **kwargs: None)
    monkeypatch.setattr(api.send, "progress_close", lambda: None)
    monkeypatch.setattr(
        api.send,
        "progress_update_filename",
        lambda result, *args: result.update(keepgoing=True),
    )
    monkeypatch.setattr(
        api.openImage,
        "verify_image",
        lambda value, valid, invalid: valid.append(value),
    )
    monkeypatch.setattr(
        api.send,
        "frame_show_image_tree",
        lambda result, *args, **kwargs: result.update(answer=False),
    )
    assert api.verify_images([info], 1) is None

    values = {"paths": ["selected.png"]}
    monkeypatch.setattr(
        api.send,
        "frame_show_execute_dialog",
        lambda result, settings, paths: result.update(cancel=False),
    )
    assert api.get_paths_and_settings(None, values) == ["selected.png"]


def test_remaining_log_and_actionlist_branches(monkeypatch, tmp_path):
    logged = []
    monkeypatch.setattr(api, "log_error", lambda *args, **kwargs: logged.append(args))

    class LoggedPhoto(PhotoFake):
        def get_log(self) -> str:
            return "warning"

        def clear_log(self):
            logged.append("cleared")

    api.flush_log(LoggedPhoto(), "in.png")
    assert logged

    errors = []
    monkeypatch.setattr(api.send, "frame_show_error", errors.append)
    cases = [
        '{"format_version": "9.0", "actions": []}',
        '{"version": "1.0", "actions": []}',
        '{"format_version": "2.0", "actions": []}',
    ]
    for index, source in enumerate(cases):
        filename = tmp_path / f"case-{index}.phatch"
        filename.write_text(source, encoding="utf-8")
        monkeypatch.setattr(api, "ACTIONS", None if index == 2 else {})
        assert api.open_actionlist(str(filename)) is None
    assert len(errors) == 3


def test_process_error_reuses_previous_skip(monkeypatch):
    monkeypatch.setattr(api, "log_error", lambda *args: None)
    result = {"stop_for_errors": False, "last_answer": "skip"}
    _, updated = api.process_error(None, "bad", "in.png", None, result, False)
    assert updated["skip"] is True
