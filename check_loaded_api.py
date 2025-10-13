#!/usr/bin/env python
"""Check which api.py module is actually loaded."""
import sys
import os

# Replicate bin/phatch setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import builtins
if '_' not in dir(builtins):
    builtins._ = str

# Now import
from phatch.core import api

print("=" * 60)
print("CHECKING LOADED API MODULE")
print("=" * 60)
print(f"\napi module file: {api.__file__}")
print(f"ACTIONS_LIST_FORMAT_VERSION: {api.ACTIONS_LIST_FORMAT_VERSION}")

# Check if it has our new code
import inspect
source = inspect.getsource(api.open_actionlist)
has_json_code = 'json.loads' in source
has_new_version_check = "('1.0', '2.0')" in source

print(f"\nHas json.loads in open_actionlist: {has_json_code}")
print(f"Has new version check ('1.0', '2.0'): {has_new_version_check}")

if has_json_code and has_new_version_check:
    print("\n✅ Correct version of api.py is loaded!")
else:
    print("\n❌ OLD version of api.py is loaded!")
    print("\nFirst 500 chars of open_actionlist:")
    print(source[:500])
