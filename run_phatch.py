#!/usr/bin/env python

import os
import sys

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath('.'))

# Import and run the main function
from phatch.phatch_main import main

if __name__ == '__main__':
    main() 