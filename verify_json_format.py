#!/usr/bin/env python
"""Verify the JSON format migration is working."""
import sys
sys.path.insert(0, '.')

import builtins
if '_' not in dir(builtins):
    builtins._ = str

from phatch.core import config, api

config.init_config_paths()
api.init()

print("=" * 60)
print("VERIFYING JSON FORMAT MIGRATION")
print("=" * 60)
print(f"\n✓ ACTIONS_LIST_FORMAT_VERSION: {api.ACTIONS_LIST_FORMAT_VERSION}")
print(f"✓ VERSION: {api.VERSION}")

# Test save
import tempfile
import os
import json

border = api.ACTIONS['Border']()
test_file = tempfile.mktemp(suffix='.phatch')

print(f"\n📝 Saving test action list to: {test_file}")
data = {'description': 'Verification test', 'actions': [border]}
api.save_actionlist(test_file, data)

# Verify it's JSON
with open(test_file, 'r') as f:
    content = f.read()

print("\n📄 File content (first 300 chars):")
print(content[:300])

try:
    parsed = json.loads(content)
    print("\n✅ File is valid JSON!")
    print(f"   format_version: {parsed.get('format_version')}")
    print(f"   version: {parsed.get('version')}")
except:
    print("\n❌ File is NOT valid JSON!")
    sys.exit(1)

# Test load
print("\n📖 Loading the action list back...")
result = api.open_actionlist(test_file)

if result is None:
    print("❌ FAILED: open_actionlist returned None (incompatible version)")
    sys.exit(1)
else:
    loaded_data, warning = result
    print(f"✅ Successfully loaded {len(loaded_data.get('actions', []))} actions")

os.remove(test_file)
print("\n" + "=" * 60)
print("✅ ALL CHECKS PASSED - JSON format is working!")
print("=" * 60)
