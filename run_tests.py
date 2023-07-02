import sys
import unittest

test_suite = unittest.defaultTestLoader.discover("backend")
result = unittest.TextTestRunner().run(test_suite)
sys.exit(0 if result.wasSuccessful() else 1)
