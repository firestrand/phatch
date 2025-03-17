#!/usr/bin/env python
# Simple test script for Phatch imports

import os
import sys

# Add the current directory to the path so we can import phatch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test if we can import the necessary modules."""
    try:
        print("Importing phatch...")
        import phatch
        print("Importing phatch.core.api...")
        from phatch.core import api
        print("Initializing API...")
        api.init()
        print("Importing phatch.actions...")
        from phatch.actions import scale
        print("Creating scale action...")
        scale_action = scale.Action()
        print("All imports successful!")
        return True
    except Exception as e:
        print(f"Import ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1) 