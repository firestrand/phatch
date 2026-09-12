from __future__ import annotations

import zipfile
from pathlib import Path


def write_metadata_wheel(path: Path, requirements: tuple[str, ...] = ()) -> Path:
    requires_dist = "".join(
        f"Requires-Dist: {requirement}\n" for requirement in requirements
    )
    metadata_text = (
        "Metadata-Version: 2.4\n"
        "Name: Phatch\n"
        "Version: 0.3.0\n"
        "License-Expression: GPL-3.0-or-later\n"
        f"{requires_dist}\n"
    )
    with zipfile.ZipFile(path, "w") as wheel:
        wheel.writestr("phatch-0.3.0.dist-info/METADATA", metadata_text)
    return path
