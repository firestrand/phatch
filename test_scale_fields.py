#!/usr/bin/env python
# Simple test script for Phatch scale action fields

import os
import sys

# Add the current directory to the path so we can import phatch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_scale_fields():
    """Test the scale action fields."""
    try:
        # Import necessary modules
        from phatch.core import api
        from phatch.actions import scale
        
        # Initialize API
        api.init()
        
        # Create scale action
        scale_action = scale.Action()
        
        # Print fields
        print("Scale action fields:")
        for field_name, field in scale_action._fields.items():
            print(f"  {field_name}: {field.__class__.__name__}")
            if hasattr(field, 'label'):
                print(f"    Label: {field.label}")
            if hasattr(field, 'default'):
                print(f"    Default: {field.default}")
        
        # Print action info
        print("\nScale action info:")
        print(f"  Label: {scale_action.label}")
        print(f"  Author: {scale_action.author}")
        print(f"  Version: {scale_action.version}")
        print(f"  Tags: {scale_action.tags}")
        
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_scale_fields()
    sys.exit(0 if success else 1) 