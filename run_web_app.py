#!/usr/bin/env python3
"""
Run the BBVAnalyzer web application directly.
This script is a convenience wrapper to start the web application.
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import and run the tray app
from src import tray_app

if __name__ == "__main__":
    print("Starting BBVAnalyzer web application...")
    print("The application will open in your default web browser.")
    print("You can also access it at http://localhost:5000")
    print("Press Ctrl+C to stop the server.")
    tray_app.main() 