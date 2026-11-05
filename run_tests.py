#!/usr/bin/env python3
"""
Dedicated Test Runner for Stellar Evolution Explorer Project
============================================================
Executes unit and multi-tier end-to-end tests with structured reporting.

Usage:
    py -3 run_tests.py                 # Run all test suites
    py -3 run_tests.py --tier 1        # Run Tier 1: Feature Coverage
    py -3 run_tests.py --tier 2        # Run Tier 2: Boundary & Corner Cases
    py -3 run_tests.py --tier 3        # Run Tier 3: Cross-Feature Integration
    py -3 run_tests.py --tier 4        # Run Tier 4: Real-World Scenarios
    py -3 run_tests.py --verbose       # Verbose test discovery
"""

import argparse
import sys
import time
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


TIER_MAPPING = {
    1: "tests.test_e2e_stellar_evolution.TestTier1FeatureCoverage",
    2: "tests.test_e2e_stellar_evolution.TestTier2BoundaryAndCornerCases",
    3: "tests.test_e2e_stellar_evolution.TestTier3CrossFeatureIntegration",
    4: "tests.test_e2e_stellar_evolution.TestTier4RealWorldScenarios",
}


def build_suite(tier: int = None) -> unittest.TestSuite:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    if tier in TIER_MAPPING:
        # Load specific tier class
        test_class_path = TIER_MAPPING[tier]
        loaded = loader.loadTestsFromName(test_class_path)
        suite.addTest(loaded)
    else:
        # Discover all tests in tests/
        tests_dir = PROJECT_ROOT / "tests"
        discovered = loader.discover(
            start_dir=str(tests_dir),
            pattern="test_*.py",
            top_level_dir=str(PROJECT_ROOT),
        )
        suite.addTest(discovered)

    return suite


def main():
    parser = argparse.ArgumentParser(description="Stellar Evolution Test Runner")
    parser.add_argument(
        "--tier",
        type=int,
        choices=[1, 2, 3, 4],
        help="Run tests for a specific tier (1, 2, 3, or 4)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    args = parser.parse_args()

    suite = build_suite(args.tier)
    verbosity = 2 if args.verbose else 1

    print("=" * 70)
    print("Stellar Evolution Simulation & Interactive Web Explorer Test Suite")
    if args.tier:
        print(f"Target: Tier {args.tier} ({TIER_MAPPING[args.tier]})")
    else:
        print("Target: All Tiers & Discoverable Tests")
    print(f"Directory: {PROJECT_ROOT}")
    print("=" * 70)

    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    elapsed = time.time() - start_time

    print("\n" + "=" * 70)
    print(f"Ran {result.testsRun} tests in {elapsed:.3f}s")
    if result.wasSuccessful():
        print("RESULT: ALL TESTS PASSED [OK]")
        sys.exit(0)
    else:
        print(f"RESULT: FAILED (failures={len(result.failures)}, errors={len(result.errors)})")
        sys.exit(1)


if __name__ == "__main__":
    main()
