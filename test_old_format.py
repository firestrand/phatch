#!/usr/bin/env python
"""Test what happens with old pprint format files."""
import sys
sys.path.insert(0, '.')

import builtins
if '_' not in dir(builtins):
    builtins._ = str

from phatch.core import config, api
from phatch.services.action_list import ActionListService
import tempfile
import os

config.init_config_paths()
api.init()

service = ActionListService(safe_mode_checker=lambda: False)

print("=" * 60)
print("TESTING OLD PPRINT FORMAT (v1.0)")
print("=" * 60)

# Create a file in the OLD pprint format (what the old code would have saved)
# This is missing format_version but has version
old_content_v1 = """{'actions': [{'fields': {'Border Width': '1px',
                         'Bottom': '0px',
                         'Color': '#FFFFFF',
                         'Left': '0px',
                         'Method': 'Equal for all sides',
                         'Opacity': '100',
                         'Right': '0px',
                         'Top': '0px',
                         '__enabled__': 'yes'},
              'label': 'Border'}],
 'description': 'Old format',
 'version': '0.3.0'}"""

test_file = tempfile.mktemp(suffix='.phatch')
with open(test_file, 'w') as f:
    f.write(old_content_v1)

print("\n1. Created old format file (version 0.3.0, NO format_version)")
print("   First 200 chars:", old_content_v1[:200])

print("\n2. Testing API load...")
try:
    result = api.open_actionlist(test_file)
    if result is None:
        print("   ❌ API returned None (incompatible)")
    else:
        data, warning = result
        print(f"   ✓ API loaded: {len(data.get('actions', []))} actions")
        print(f"     format_version: {data.get('format_version')}")
        print(f"     version: {data.get('version')}")
except Exception as e:
    print(f"   ❌ Exception: {e}")

print("\n3. Testing Service load...")
try:
    result = service.load(test_file)
    print(f"   ✓ Service loaded: {len(result.actions)} actions")
except Exception as e:
    print(f"   ❌ Exception: {type(e).__name__}: {e}")

os.remove(test_file)

# Now test with format_version 1.0 explicitly set
print("\n" + "=" * 60)
print("TESTING OLD FORMAT WITH format_version: '1.0'")
print("=" * 60)

old_content_v1_explicit = """{'actions': [{'fields': {'Border Width': '1px',
                         '__enabled__': 'yes'},
              'label': 'Border'}],
 'description': 'Old with format_version',
 'format_version': '1.0',
 'version': '0.3.0'}"""

test_file2 = tempfile.mktemp(suffix='.phatch')
with open(test_file2, 'w') as f:
    f.write(old_content_v1_explicit)

print("\n4. Testing API load...")
try:
    result = api.open_actionlist(test_file2)
    if result is None:
        print("   ❌ API returned None (incompatible)")
    else:
        data, warning = result
        print(f"   ✓ API loaded: {len(data.get('actions', []))} actions")
except Exception as e:
    print(f"   ❌ Exception: {e}")

print("\n5. Testing Service load...")
try:
    result = service.load(test_file2)
    print(f"   ✓ Service loaded: {len(result.actions)} actions")
except Exception as e:
    print(f"   ❌ Exception: {type(e).__name__}: {e}")

os.remove(test_file2)
