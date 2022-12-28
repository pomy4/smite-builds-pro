import sys
import unittest

modules = ["be", "upd", "shared"]
# unittest prefers when directories contain __init__.py, but this code also works.
# Using TestLoader() instead of defaultTestLoader since defaultTestLoader
# throws 'ImportError: Start directory is not importable' on the second module.
test_suites = [unittest.TestLoader().discover(x) for x in modules]
result = unittest.TextTestRunner().run(unittest.TestSuite(test_suites))
sys.exit(0 if result.wasSuccessful() else 1)
