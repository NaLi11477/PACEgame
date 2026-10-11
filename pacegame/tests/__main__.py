"""Run every shipped regression: python -m pacegame.tests."""
import sys
import unittest
from . import load_suite


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=1).run(load_suite())
    sys.exit(0 if result.wasSuccessful() else 1)
