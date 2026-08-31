import sys
import os
import unittest

# Ensure backend directory is in python module search path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def run_all_tests():
    print("=" * 50)
    print("        ASSETVAULT TEST SUITE EXECUTION           ")
    print("=" * 50)
    
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=current_dir, pattern="test_*.py")
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\nTest Summary:")
    print(f"  Total Run : {result.testsRun}")
    print(f"  Failures  : {len(result.failures)}")
    print(f"  Errors    : {len(result.errors)}")
    
    if not result.wasSuccessful():
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()
