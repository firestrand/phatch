#!/usr/bin/env python

import os
import sys

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath('.'))

# Import necessary modules
from phatch.core import config
from phatch.core import api
from phatch.core import pil

def main():
    # Initialize configuration paths
    from phatch.phatch_main import init_config_paths
    config_paths = init_config_paths()
    
    # Initialize API
    api.init()
    
    # Print welcome message
    print("Phatch Console Mode")
    print("------------------")
    print("Available actions:")
    
    # List available actions
    for action_name in sorted(api.ACTIONS.keys()):
        print(f"- {action_name}")
    
    print("\nTo use Phatch in console mode, you need to create an action list first.")
    print("Then you can run: python -m phatch.console.phatch <actionlist> <folder>")

if __name__ == '__main__':
    main() 