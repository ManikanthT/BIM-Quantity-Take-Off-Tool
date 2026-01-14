"""
Standalone entry point for the BIM QTO tool.
Allows running the tool directly: python main.py <ifc_file> <output_file>
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import src
sys.path.insert(0, str(Path(__file__).parent))

from src.main import main

if __name__ == '__main__':
    main()
