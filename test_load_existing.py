#!/usr/bin/env python
"""Test loading existing action lists."""
import sys
sys.path.insert(0, '.')

import builtins
if '_' not in dir(builtins):
    builtins._ = str

from phatch.core import config, api

config.init_config_paths()
api.init()

# Test loading an existing action list
test_files = [
    'data/actionlists/badge.phatch',
    'data/actionlists/button.phatch',
]

print("Testing existing action lists:\n")

for filepath in test_files:
    print(f"📂 Loading: {filepath}")
    try:
        result = api.open_actionlist(filepath)
        if result is None:
            print(f"   ❌ FAILED: Returned None (incompatible version)")
        else:
            data, warning = result
            print(f"   ✅ Success: {len(data.get('actions', []))} actions")
            if data.get('format_version'):
                print(f"      format_version: {data.get('format_version')}")
            if data.get('version'):
                print(f"      version: {data.get('version')}")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
    print()
