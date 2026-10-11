"""One discovery entry point for both checkout and installed-wheel tests."""
from pathlib import Path
import unittest


def load_suite():
    folder = Path(__file__).resolve().parent
    return unittest.defaultTestLoader.discover(
        str(folder), pattern="test*.py", top_level_dir=str(folder.parent.parent))
