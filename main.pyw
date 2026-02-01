import os
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui.app import run_gui

if __name__ == "__main__":
    run_gui()