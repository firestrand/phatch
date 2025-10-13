#!/usr/bin/env python
"""Simulate exact GUI save/load workflow."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import builtins
if '_' not in dir(builtins):
    builtins._ = str

from phatch.core import config, api
from phatch.services.action_list import ActionListService
import tempfile

config.init_config_paths()
api.init()

print("=" * 70)
print("EXACT GUI WORKFLOW SIMULATION")
print("=" * 70)

# Step 1: Create an action (like in GUI)
print("\n1. Creating Border action...")
border = api.ACTIONS['Border']()
save_action = api.ACTIONS['Save']()

# Step 2: Save through service (like GUI does)
service = ActionListService()
test_file = tempfile.mktemp(suffix='.phatch')

print(f"2. Saving through ActionListService to: {test_file}")
try:
    payload = service.save(test_file, "Test from GUI workflow", [border, save_action])
    print(f"   ✓ Saved successfully")
    print(f"   Payload keys: {list(payload.keys())}")
except Exception as e:
    print(f"   ❌ Save failed: {e}")
    sys.exit(1)

# Step 3: Check what was written
print("\n3. Checking saved file...")
with open(test_file, 'r') as f:
    content = f.read()
print(f"   File size: {len(content)} bytes")
print(f"   First 300 chars:\n{content[:300]}")

# Step 4: Try to load it back (like GUI does)
print("\n4. Loading through ActionListService (safe mode OFF)...")
service = ActionListService(safe_mode_checker=lambda: False)
try:
    result = service.load(test_file)
    print(f"   ✓ Loaded successfully!")
    print(f"   Description: {result.description}")
    print(f"   Actions: {len(result.actions)}")
    print(f"   Format version: {result.data.get('format_version')}")
except Exception as e:
    print(f"   ❌ Load failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Step 5: Try with safe mode ON (like GUI might)
print("\n5. Loading through ActionListService (safe mode ON)...")
service_safe = ActionListService(safe_mode_checker=lambda: True)
try:
    result = service_safe.load(test_file)
    print(f"   ✓ Loaded successfully!")
except Exception as e:
    print(f"   ❌ Load failed: {type(e).__name__}: {e}")

os.remove(test_file)
print("\n" + "=" * 70)
print("If this all passed, the code is working correctly.")
print("The issue might be:")
print("  1. An old .phatch file from before the migration")
print("  2. GUI needs to be fully restarted") 
print("  3. A system-wide phatch installation is being used")
print("=" * 70)
