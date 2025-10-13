# Debug Instructions for Action List Error

I've added comprehensive debug output to identify exactly where the incompatibility error is coming from.

## Steps to Debug

1. **Clear all Python cache:**
   ```bash
   find . -name "*.pyc" -delete 2>/dev/null
   find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
   ```

2. **Run Phatch from the terminal** (so you can see debug output):
   ```bash
   ./bin/phatch 2>&1 | tee debug.log
   ```

3. **Try to open your action list** (`~/phatch/actionlists/blue-border-1.phatch`)

4. **Check the terminal output** - you should see DEBUG messages like:
   ```
   DEBUG: Rejecting format_version: ...
   DEBUG: Rejecting version: ...
   DEBUG: open_actionlist returned None for ...
   DEBUG: Exception in service.load: ...
   ```

5. **Share the debug output** with me - copy/paste the DEBUG lines

## What the Debug Output Tells Us

- **"DEBUG: Failed to parse file as JSON"** - File is corrupted or not valid JSON
- **"DEBUG: Rejecting format_version: X"** - Version mismatch (expecting 1.0 or 2.0)
- **"DEBUG: Rejecting version: X"** - Old file with wrong version
- **"DEBUG: open_actionlist returned None"** - One of the above checks failed

## Quick Test

Before running the GUI, test the specific file:

```bash
python3 << 'EOF'
import sys; sys.path.insert(0, '.')
import builtins; builtins._ = str
from phatch.core import config, api

config.init_config_paths()
api.init()

filepath = '/Users/firestrand/phatch/actionlists/blue-border-1.phatch'
print(f"Testing: {filepath}")

result = api.open_actionlist(filepath)
if result:
    print("✓ File loads successfully")
else:
    print("✗ File returns None (see DEBUG output above)")
EOF
```

This should show any DEBUG messages immediately.

## Expected Behavior

If everything is working correctly, you should see **NO** DEBUG messages and the file should load fine.

If you see DEBUG messages, they'll tell us exactly what's wrong with the file format.
