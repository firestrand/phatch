#!/usr/bin/env python
# Test script for Phatch console mode

import os
import sys
from PIL import Image

# Add the current directory to the path so we can import phatch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_console():
    """Test the console mode of Phatch."""
    try:
        # Import necessary modules
        from phatch.console import console
        
        # Create a test image
        test_image = Image.new('RGB', (200, 200), color='red')
        test_dir = 'test_images'
        
        # Create test directory if it doesn't exist
        if not os.path.exists(test_dir):
            os.makedirs(test_dir)
        
        # Save test image
        test_image_path = os.path.join(test_dir, 'test_image.jpg')
        test_image.save(test_image_path)
        print(f"Created test image: {test_image_path}")
        
        # Print available actions
        print("Available actions:")
        for action in console.get_actions():
            print(f"  {action}")
        
        print("\nTest completed successfully!")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        try:
            if os.path.exists(test_image_path):
                os.remove(test_image_path)
                print(f"Removed: {test_image_path}")
            if os.path.exists(test_dir):
                os.rmdir(test_dir)
                print(f"Removed directory: {test_dir}")
        except:
            pass

if __name__ == "__main__":
    success = test_console()
    sys.exit(0 if success else 1) 