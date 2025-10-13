"""Advises on action list adjustments such as ensuring a save action."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from phatch.core import ct

try:  # pragma: no cover - provided by gettext in runtime
    _  # type: ignore[name-defined]
except NameError:  # pragma: no cover - fallback for tests
    import builtins

    if '_' not in builtins.__dict__:
        builtins.__dict__['_'] = lambda value: value
    _ = builtins.__dict__['_']


@dataclass(frozen=True)
class SaveAdvice:
    message: str
    action_label: str


class ActionListAdvisor:
    """Provides recommendations for augmenting action lists."""

    @staticmethod
    def recommend_save_action(actions: Iterable[object]) -> SaveAdvice:
        actions = list(actions)
        only_metadata = _only_actions_with_tag(actions, 'metadata') if actions else False
        message = ct.SAVE_ACTION_NEEDED + " " + _(
            "Phatch will add one for you, please check its settings."
        )
        if only_metadata:
            message += ' \n\n%s%s' % (
                _('The action list only processes metadata.'),
                _('Phatch chooses the lossless "Save Tags" action.'),
            )
            label = 'Save Tags'
        else:
            label = 'Save'
        return SaveAdvice(message=message, action_label=label)


def _only_actions_with_tag(actions: Iterable[object], tag: str) -> bool:
    for action in actions:
        if not hasattr(action, 'tags') or tag not in action.tags:
            return False
    return True
