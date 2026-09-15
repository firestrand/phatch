#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = []
# ///

# How to run: uv run scripts/runtime_inventory.py [--json]

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from phatch.release_inventory import RuntimeInventoryError, collect_runtime_inventory


def main(arguments: tuple[str, ...] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    options = parser.parse_args(arguments)
    try:
        inventory = collect_runtime_inventory()
    except (RuntimeInventoryError, OSError) as error:
        print(error, file=sys.stderr)
        return 1
    payload = {
        "modules": sorted(inventory.modules),
        "resources": [asdict(resource) for resource in inventory.resources],
        "resource_counts": dict(inventory.resource_counts),
    }
    if options.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(
            f"runtime inventory: {len(inventory.modules)} modules, "
            f"{len(inventory.resources)} required resources"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
