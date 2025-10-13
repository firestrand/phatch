#!/bin/bash
# Diagnostic script to identify the issue

echo "============================================================"
echo "PHATCH ACTION LIST DIAGNOSTIC"
echo "============================================================"

echo ""
echo "1. Checking code version..."
grep "ACTIONS_LIST_FORMAT_VERSION = " phatch/core/api.py

echo ""
echo "2. Verifying JSON migration is present..."
if grep -q "json.loads" phatch/core/api.py; then
    echo "   ✓ JSON code is present"
else
    echo "   ❌ JSON code is MISSING!"
fi

echo ""
echo "3. Checking for bytecode cache..."
if find . -name "*.pyc" -o -type d -name "__pycache__" 2>/dev/null | grep -q .; then
    echo "   ⚠️  Python cache found - clearing..."
    find . -name "*.pyc" -delete 2>/dev/null
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
    echo "   ✓ Cache cleared"
else
    echo "   ✓ No cache found"
fi

echo ""
echo "4. Testing API..."
python3 -c "
import sys; sys.path.insert(0, '.')
import builtins; builtins._ = str
from phatch.core import api
print(f'   ACTIONS_LIST_FORMAT_VERSION: {api.ACTIONS_LIST_FORMAT_VERSION}')
print(f'   Has JSON support: {\"json.loads\" in open(\"phatch/core/api.py\").read()}')
"

echo ""
echo "5. Running comprehensive test..."
python3 test_gui_workflow.py 2>&1 | tail -5

echo ""
echo "============================================================"
echo "RECOMMENDED ACTIONS:"
echo "============================================================"
echo ""
echo "If all tests pass but GUI still fails:"
echo ""
echo "  1. DELETE any .phatch files you saved BEFORE the migration"
echo "     (they may be corrupted)"
echo ""
echo "  2. Create a NEW action list in the GUI:"
echo "     - Add a simple action (like Border)"
echo "     - Save it with a new name"
echo "     - Try to open it"
echo ""
echo "  3. Check which .phatch file is causing the error:"
read -p "     Enter the FULL PATH to the .phatch file that fails: " PHATCH_FILE
if [ -n "$PHATCH_FILE" ] && [ -f "$PHATCH_FILE" ]; then
    echo ""
    echo "  Analyzing $PHATCH_FILE:"
    echo "  ----------------------------------------"
    head -20 "$PHATCH_FILE"
    echo "  ----------------------------------------"
    echo ""
    python3 -c "
import sys; sys.path.insert(0, '.')
import builtins; builtins._ = str
from phatch.core import api, config
config.init_config_paths()
api.init()
try:
    result = api.open_actionlist('$PHATCH_FILE')
    if result:
        print('✓ This file loads correctly!')
    else:
        print('❌ This file returns None (incompatible)')
except Exception as e:
    print(f'❌ Exception: {e}')
    "
fi

echo ""
echo "============================================================"
