import pytest

from phatch.services.action_list import (
    ActionListService,
    IncompatibleActionListError,
    MissingRequiredActionError,
    UnsafeActionListError,
)


def test_load_returns_data_and_metadata_when_safe_mode_allows():
    data = {
        "description": "example",
        "actions": ["resize"],
        "invalid labels": ["Foo"],
    }

    def fake_open(path):
        assert path == "sample.phatch"
        return data, ""

    service = ActionListService(
        open_actionlist=fake_open,
        safe_mode_checker=lambda: False,
    )

    result = service.load("sample.phatch")

    assert result.data is data
    assert result.warning == ""
    assert result.invalid_labels == ("Foo",)
    assert result.description == "example"
    assert list(result.actions) == ["resize"]


def test_load_raises_missing_required_action():
    def fake_open(_):
        raise KeyError("MissingAction")

    service = ActionListService(open_actionlist=fake_open)

    with pytest.raises(MissingRequiredActionError) as exc:
        service.load("missing.phatch")

    assert "MissingAction" in str(exc.value)


def test_load_raises_incompatible_action_list_for_other_errors():
    def fake_open(_):
        raise ValueError("broken")

    service = ActionListService(open_actionlist=fake_open)

    with pytest.raises(IncompatibleActionListError) as exc:
        service.load("broken.phatch")

    assert "broken.phatch" in str(exc.value)


def test_load_raises_unsafe_action_list_when_safe_mode_enabled():
    data = {
        "description": "example",
        "actions": [],
        "invalid labels": [],
    }

    def fake_open(_):
        return data, "unsafe warning"

    service = ActionListService(
        open_actionlist=fake_open,
        safe_mode_checker=lambda: True,
    )

    with pytest.raises(UnsafeActionListError) as exc:
        service.load("unsafe.phatch")

    assert exc.value.warning == "unsafe warning"


def test_save_persists_payload():
    saved = {}

    def fake_save(path, payload):
        saved["path"] = path
        saved["payload"] = payload

    service = ActionListService(save_actionlist=fake_save)

    payload = service.save("actionlist.phatch", "desc", ["resize"])

    assert saved["path"] == "actionlist.phatch"
    assert saved["payload"] == {"description": "desc", "actions": ["resize"]}
    assert payload is saved["payload"]


def test_save_writes_bytes_to_file(tmp_path):
    file_path = tmp_path / "action.phatch"

    service = ActionListService()

    payload = service.save(str(file_path), "desc", [])

    with open(file_path, "rb") as handle:
        content = handle.read()

    # Verify JSON format (not old pprint format)
    assert b'"description": "desc"' in content
    assert payload["description"] == "desc"


def test_round_trip_save_and_load(tmp_path):
    # Initialize API to populate ACTIONS registry
    import builtins
    if '_' not in builtins.__dict__:
        builtins.__dict__['_'] = lambda value: value

    from phatch.core import config, api
    config.init_config_paths()
    api.init()

    file_path = tmp_path / "action.phatch"

    service = ActionListService(safe_mode_checker=lambda: False)

    service.save(str(file_path), "desc", [])

    result = service.load(str(file_path))

    assert result.description == 'desc'
    assert result.data.get('format_version') == '2.0'  # New JSON format


def test_load_legacy_version_still_allowed(monkeypatch):
    legacy = {
        'version': '0.2.7',
        'actions': [],
        'description': 'legacy desc',
    }

    def fake_open(_):
        return legacy, ''

    service = ActionListService(open_actionlist=fake_open, safe_mode_checker=lambda: False)

    result = service.load('legacy.phatch')

    assert result.description == 'legacy desc'


def test_save_and_load_real_actions(tmp_path, monkeypatch):
    # ensure translation helper is available for ct import
    import builtins

    if '_' not in builtins.__dict__:
        builtins.__dict__['_'] = lambda value: value

    from phatch.core import config, api

    config.init_config_paths()
    api.init()

    border = api.ACTIONS['Border']()
    save_action = api.ACTIONS['Save']()

    path = tmp_path / 'real.phatch'

    service = ActionListService()
    service.save(str(path), 'real desc', [border, save_action])

    result = service.load(str(path))

    assert result.description == 'real desc'
    assert len(result.actions) == 2


def test_execute_passes_update_callback_when_missing_from_kwargs():
    captured = {}

    def fake_apply(actions, settings, **kwargs):
        captured["actions"] = actions
        captured["settings"] = settings
        captured["kwargs"] = kwargs

    callback = object()
    service = ActionListService(apply_actions_to_photos=fake_apply)

    service.execute(["resize"], {"quality": 90}, update_callback=callback, extra="value")

    assert captured["actions"] == ["resize"]
    assert captured["settings"] == {"quality": 90}
    assert captured["kwargs"]["update"] is callback
    assert captured["kwargs"]["extra"] == "value"


def test_execute_respects_explicit_update_kwarg():
    captured = {}

    def fake_apply(actions, settings, **kwargs):
        captured["kwargs"] = kwargs

    service = ActionListService(apply_actions_to_photos=fake_apply)

    service.execute([], {}, update_callback=lambda: None, update="custom")

    assert captured["kwargs"]["update"] == "custom"


def test_saves_as_json_format(tmp_path):
    """Verify that action lists are saved in JSON format."""
    import json
    import builtins

    if '_' not in builtins.__dict__:
        builtins.__dict__['_'] = lambda value: value

    from phatch.core import config, api

    config.init_config_paths()
    api.init()

    border = api.ACTIONS['Border']()
    path = tmp_path / 'json_test.phatch'

    service = ActionListService()
    service.save(str(path), 'JSON format test', [border])

    # Verify it's valid JSON
    with open(path, 'r') as f:
        content = f.read()
        data = json.loads(content)  # Should not raise

    assert data['format_version'] == '2.0'
    assert data['description'] == 'JSON format test'


def test_loads_legacy_pprint_format(tmp_path):
    """Verify backward compatibility with old pprint format."""
    import builtins

    if '_' not in builtins.__dict__:
        builtins.__dict__['_'] = lambda value: value

    from phatch.core import config, api

    config.init_config_paths()
    api.init()

    # Create a file in the old pprint format (version 1.0)
    legacy_content = """{'actions': [{'fields': {'Border Width': '1px',
                         'Bottom': '0px',
                         'Color': '#FFFFFF',
                         'Left': '0px',
                         'Method': 'Equal for all sides',
                         'Opacity': '100',
                         'Right': '0px',
                         'Top': '0px',
                         '__enabled__': 'yes'},
              'label': 'Border'}],
 'description': 'Legacy format',
 'format_version': '1.0',
 'version': '0.3.0'}"""

    path = tmp_path / 'legacy.phatch'
    with open(path, 'w') as f:
        f.write(legacy_content)

    service = ActionListService(safe_mode_checker=lambda: False)
    result = service.load(str(path))

    assert result.description == 'Legacy format'
    assert len(result.actions) == 1
