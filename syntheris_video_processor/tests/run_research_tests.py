#!/usr/bin/env python3
"""
Research Tests Runner
Runs all research validation tests in sequence with proper reporting.
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def run_research_tests():
    """Run all research validation tests."""
    
    print("[TEST] Running Research Implementation Tests")
    print("=" * 60)
    
    # Discover and load test modules
    loader = unittest.TestLoader()
    
    # Test modules to run
    test_modules = [
        'test_duration_preservation',
        'test_rife_v426_integration', 
        'test_pts_handling'
    ]
    
    # Create test suite
    suite = unittest.TestSuite()
    failed_imports = []
    
    for module_name in test_modules:
        try:
            module = __import__(f'syntheris_video_processor.tests.{module_name}', 
                              fromlist=[module_name])
            tests = loader.loadTestsFromModule(module)
            suite.addTests(tests)
            print(f"SUCCESS: Loaded tests from {module_name}")
        except ImportError as e:
            failed_imports.append(module_name)
            print(f"WARNING: Failed to load {module_name}: {e}")
        except Exception as e:
            failed_imports.append(module_name)
            print(f"FAIL: Error loading {module_name}: {e}")
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        buffer=True,
        failfast=False
    )
    
    print(f"\n[DEPLOY] Running {suite.countTestCases()} research validation tests...\n")
    
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("[DATA] TEST SUMMARY")
    print("=" * 60)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
    passed = total_tests - failures - errors - skipped
    
    print(f"Total Tests:  {total_tests}")
    print(f"Passed:       {passed}")
    print(f"Failed:       {failures}")
    print(f"Errors:       {errors}")
    print(f"Skipped:      {skipped}")
    
    if result.wasSuccessful() and not failed_imports and total_tests > 0:
        print("\n🎉 ALL RESEARCH TESTS PASSED!")
        success = True
    else:
        print("\nWARNING: SOME TESTS FAILED - See details above")
        success = False
        
        # Print failure details
        if result.failures:
            print("\nFAILURES:")
            for test, traceback in result.failures:
                print(f"  {test}: {traceback}")
        
        if result.errors:
            print("\nERRORS:")
            for test, traceback in result.errors:
                print(f"  {test}: {traceback}")
    
    return success


if __name__ == "__main__":
    success = run_research_tests()
    sys.exit(0 if success else 1)