from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Final, TypeVar

_ActionValue = TypeVar("_ActionValue")
_SettingValue = TypeVar("_SettingValue")
_EXECUTION_SETTING_KEYS: Final = frozenset(
    {
        "extensions",
        "recursive",
        "stop_for_errors",
        "overwrite_existing_images",
        "overwrite_existing_images_forced",
        "no_save",
        "check_images_first",
        "safe",
        "repeat",
    }
)


def execution_fingerprint(
    actions: tuple[Mapping[str, _ActionValue], ...],
    settings: Mapping[str, _SettingValue],
    paths: tuple[Path, ...] | None,
    drop: bool,
) -> str:
    payload = json.dumps(
        {
            "actions": actions,
            "settings": {
                key: value
                for key, value in settings.items()
                if key in _EXECUTION_SETTING_KEYS
            },
            "paths": (
                tuple(str(path.resolve()) for path in paths)
                if paths is not None
                else None
            ),
            "drop": drop,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode()
    return hashlib.sha256(payload).hexdigest()
