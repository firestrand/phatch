#!/usr/bin/env python
# Simple test script for Phatch image processing

import os
import sys
from PIL import Image

# Add the current directory to the path so we can import phatch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from phatch.core import api, models
from phatch.lib import metadata

def test_scale():
    """Test the scale action on a sample image."""
    try:
        # Initialize the API
        api.init()
        
        # Create a test image
        test_image = Image.new('RGB', (200, 200), color='red')
        test_image_path = 'test_image.jpg'
        test_image.save(test_image_path)
        
        print(f"Created test image: {test_image_path}")
        
        # Get the scale action
        from phatch.actions import scale
        scale_action = scale.Action()
        
        # Create a settings dictionary
        settings = {
            'Canvas Width': '100px',
            'Canvas Height': '100px',
            'Resolution': '72',
            'Constrain Proportions': True,
            'Resample Image': 'BICUBIC',
            'Scale Down Only': False
        }
        
        # Create an info object
        info = metadata.InfoExtract()
        info.set(filename=test_image_path)
        info.image = test_image
        info.size = test_image.size
        
        # Create a photo object
        photo = models.Photo(info)
        
        # Apply the action
        result_photo = scale_action.apply(photo, settings, {})
        result = result_photo.image
        
        # Save the result
        result_path = 'test_image_scaled.jpg'
        result.save(result_path)
        
        print(f"Created scaled image: {result_path}")
        print(f"Original size: {test_image.size}")
        print(f"Scaled size: {result.size}")
        
        # Verify the result
        if result.size == (100, 100):
            print("Test PASSED: Image was correctly scaled")
            return True
        else:
            print(f"Test FAILED: Image size is {result.size}, expected (100, 100)")
            return False
    except Exception as e:
        print(f"Test ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        for path in [test_image_path, result_path]:
            if os.path.exists(path):
                os.remove(path)
                print(f"Removed: {path}")

if __name__ == "__main__":
    success = test_scale()
    sys.exit(0 if success else 1) 