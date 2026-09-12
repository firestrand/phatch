from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from phatch.core.execution_types import ExecutionResult, RecoveryConfiguration
from phatch.services.legacy_types import (
    LegacyActionObject,
    LegacyPaths,
    LegacySettings,
    UpdateCallback,
)
from phatch.services.recovery import RecoveryJournal, RecoverySession
from phatch.services.recovery_fingerprint import execution_fingerprint


def execute_with_recovery(
    actions: Sequence[LegacyActionObject],
    settings: LegacySettings,
    recovery: RecoveryConfiguration,
    paths: LegacyPaths | None = None,
    drop: bool = False,
    update: UpdateCallback | None = None,
) -> ExecutionResult:
    from phatch.services.legacy_execution import _execute_actions_to_photos

    session = RecoverySession(
        RecoveryJournal(recovery.journal_path),
        execution_fingerprint(
            tuple(action.dump() for action in actions),
            settings,
            tuple(Path(path) for path in paths) if paths is not None else None,
            drop,
        ),
    )
    return _execute_actions_to_photos(actions, settings, paths, drop, update, session)
