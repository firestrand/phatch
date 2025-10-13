import builtins

if '_' not in builtins.__dict__:
    builtins.__dict__['_'] = lambda value: value

from types import SimpleNamespace

from phatch.services.action_advisor import ActionListAdvisor


def test_recommend_save_action_for_metadata_only():
    actions = [SimpleNamespace(tags={'metadata'}), SimpleNamespace(tags={'metadata'})]

    advice = ActionListAdvisor.recommend_save_action(actions)

    assert 'lossless "Save Tags"' in advice.message
    assert advice.action_label == 'Save Tags'


def test_recommend_save_action_for_general_actions():
    actions = [SimpleNamespace(tags={'metadata'}), SimpleNamespace(tags={'image'})]

    advice = ActionListAdvisor.recommend_save_action(actions)

    assert advice.action_label == 'Save'
    assert 'Save Tags' not in advice.action_label
