# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Commit to parent-reserved paths when processing independent worker jobs."""

from pathlib import Path
from typing import Any

from phatch.lib.atomic import CollisionPolicy


def planned_destination(
    photo: Any, filename: Path | str, policy: CollisionPolicy
) -> tuple[Path, CollisionPolicy]:
    path = Path(filename)
    planned = getattr(photo, 'planned_destinations', None)
    if planned is None:
        return path, policy
    candidates = planned.get(str(path.expanduser().resolve()))
    if not candidates:
        raise ValueError(
            'Worker produced an output that was not reserved by preflight'
        )
    # A racing external writer must not redirect a worker into another job's
    # reservation. Planned rename commits therefore use no-overwrite fail.
    return Path(candidates.popleft()), 'fail' if policy == 'rename' else policy
