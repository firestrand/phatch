#!/usr/bin/env python
"""Debug what happens when GUI loads an action list."""
import sys
sys.path.insert(0, '.')

import builtins
if '_' not in dir(builtins):
    builtins._ = str

from phatch.core import config, api
from phatch.services.action_list import ActionListService

config.init_config_paths()
api.init()

# Simulate what the GUI does
service = ActionListService()

# Create a test file with the new format
import tempfile
border = api.ACTIONS['Border']()
test_file = tempfile.mktemp(suffix='.phatch')

print("=" * 60)
print("SIMULATING GUI LOAD")
print("=" * 60)

# Save with new format
print("\n1. Saving action list...")
api.save_actionlist(test_file, {'description': 'GUI test', 'actions': [border]})

# Check what's in the file
with open(test_file, 'r') as f:
    content = f.read()
print("\n2. File content (first 200 chars):")
print(content[:200])

import json
data = json.loads(content)
print(f"\n3. Parsed format_version: {data.get('format_version')!r} (type: {type(data.get('format_version'))})")
print(f"   ACTIONS_LIST_FORMAT_VERSION: {api.ACTIONS_LIST_FORMAT_VERSION!r}")
print(f"   Comparison: str({data.get('format_version')!r}) in ('1.0', '2.0') = {str(data.get('format_version')) in ('1.0', '2.0')}")

# Try loading directly with API
print("\n4. Loading with api.open_actionlist()...")
try:
    result = api.open_actionlist(test_file)
    if result is None:
        print("   ❌ API returned None!")
    else:
        print("   ✓ API returned data")
except Exception as e:
    print(f"   ❌ API raised exception: {e}")

# Try loading through service (like GUI does)
print("\n5. Loading through ActionListService (like GUI)...")
try:
    result = service.load(test_file)
    print(f"   ✓ Service loaded: {len(result.actions)} actions")
except Exception as e:
    print(f"   ❌ Service raised: {type(e).__name__}: {e}")

import os
os.remove(test_file)

print("\n" + "=" * 60)
