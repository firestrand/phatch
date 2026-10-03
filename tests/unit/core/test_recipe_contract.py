# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Recipe boundary and compatibility checks."""

import json
from pathlib import Path

import pytest

from phatch.core import api
from phatch.core.recipes import RecipeValidationError, parse_recipe


def test_all_bundled_recipes_are_literal_compatible():
    for source in Path('phatch_assets/data/actionlists').glob('*.phatch'):
        result = parse_recipe(source.read_text(encoding='utf-8'))
        assert isinstance(result['actions'], list)


@pytest.mark.parametrize(
    'data,location',
    [
        ([], '$'),
        ({'actions': 'bad'}, 'actions'),
        ({'actions': [{}]}, 'actions[0].label'),
        ({'actions': [{'label': 'Save', 'fields': []}]}, 'actions[0].fields'),
        (
            {'actions': [{'label': 'Save', 'fields': {'In': 3}}]},
            'actions[0].fields.In',
        ),
        ({'actions': [], 'format_version': '999'}, 'format_version'),
    ],
)
def test_invalid_shape_has_field_location(data, location):
    with pytest.raises(RecipeValidationError) as error:
        parse_recipe(json.dumps(data))
    assert error.value.location == location


def test_recipe_limits_size_and_nesting():
    with pytest.raises(RecipeValidationError, match='size'):
        parse_recipe(' ' * (1024 * 1024 + 1))
    with pytest.raises(RecipeValidationError, match='nesting'):
        parse_recipe('[' * 70 + '0' + ']' * 70)


def test_legacy_recipe_does_not_evaluate_expressions():
    with pytest.raises(RecipeValidationError):
        parse_recipe("{'actions': [], 'description': str(1)}")


def test_plugin_id_survives_display_label_change(tmp_path, monkeypatch):
    api.import_actions()
    action = api.ACTIONS['Border']()
    target = tmp_path / 'recipe.phatch'
    api.save_actionlist(str(target), {'actions': [action]})
    document = json.loads(target.read_text())
    assert document['actions'][0]['id'] == 'border'
    # Labels may change without changing a persisted plugin identity.
    monkeypatch.setattr(api, 'ACTIONS', {'New border label': type(action)})
    monkeypatch.setattr(api, 'ACTION_FIELDS', {'New border label': action._fields})
    target.write_text(json.dumps(document))
    result, _ = api.open_actionlist(str(target))
    assert isinstance(result['actions'][0], type(action))


def test_duplicate_plugin_identity_is_rejected(monkeypatch):
    from types import SimpleNamespace

    from phatch.core.models import Action

    class First(Action):
        label = 'One'
        plugin_id = 'example.duplicate'

    class Second(Action):
        label = 'Two'
        plugin_id = 'example.duplicate'

    monkeypatch.setattr(api.ct, "USER_ACTIONS_PATH", "/tmp/phatch-user-actions")
    modules = iter(
        [SimpleNamespace(Action=First), SimpleNamespace(Action=Second)]
    )
    monkeypatch.setattr(
        api.glob,
        'glob',
        lambda path: (
            []
            if path.startswith(api.ct.USER_ACTIONS_PATH)
            else ['one.py', 'two.py']
        ),
    )
    monkeypatch.setattr(api, 'import_module', lambda *args: next(modules))
    with pytest.raises(ValueError, match='Duplicate plugin'):
        api.import_actions()


def test_all_bundled_recipes_load_and_round_trip(tmp_path, initialized_runtime):
    api.import_actions()
    sources = list(Path('phatch_assets/data/actionlists').glob('*.phatch'))
    assert sources
    for index, source in enumerate(sources):
        loaded, _ = api.open_actionlist(str(source))
        assert loaded is not None, source
        target = tmp_path / f'roundtrip-{index}.phatch'
        api.save_actionlist(str(target), loaded)
        reopened, _ = api.open_actionlist(str(target))
        assert reopened['description'] == loaded.get('description', '')
        assert [action.dump() for action in reopened['actions']] == [
            action.dump() for action in loaded['actions']
        ], source
        document = json.loads(target.read_text())
        assert all(action['id'] for action in document['actions'])


def test_missing_plugin_id_does_not_fall_back_to_display_label(tmp_path):
    from phatch.services.action_list import (
        ActionListService,
        MissingRequiredActionError,
    )

    api.import_actions()
    path = tmp_path / 'missing.phatch'
    path.write_text(
        json.dumps(
            {
                'format_version': '2.0',
                'actions': [
                    {
                        'label': 'Save',
                        'plugin_id': 'example.unavailable',
                        'fields': {},
                    }
                ],
            }
        )
    )
    with pytest.raises(
        MissingRequiredActionError, match='example.unavailable'
    ):
        ActionListService().load(str(path))
