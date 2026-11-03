#!/usr/bin/env python3
"""
Master E2E Automated Test Runner for Stellar Evolution Explorer.
Orchestrates Tiers 1-4 test execution, static and dynamic analysis,
and reports results for both development milestones and final audit.

Usage:
    py -3 tests/run_e2e_tests.py
    py -3 tests/run_e2e_tests.py --tier 1
    py -3 tests/run_e2e_tests.py --milestone M1
    py -3 tests/run_e2e_tests.py --json report.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.test_harness import StellarExplorerHarness, TestResult
from tests.test_tier1_features import run_tier1_tests
from tests.test_tier2_boundaries import run_tier2_tests
from tests.test_tier3_interactions import run_tier3_tests
from tests.test_tier4_scenarios import run_tier4_tests

BUILD_SCRIPT = PROJECT_ROOT / "build_explorer_html.py"


def verify_build_pipeline() -> Tuple[bool, str]:
    """Tests executing build_explorer_html.py directly."""
    try:
        res = subprocess.run(
            [sys.executable, str(BUILD_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=30.0,
            cwd=str(PROJECT_ROOT),
        )
        if res.returncode == 0:
            return True, "Build script executed cleanly with exit code 0."
        else:
            err = res.stderr.strip() or res.stdout.strip()
            return False, f"Build script failed (exit code {res.returncode}): {err}"
    except Exception as e:
        return False, f"Build script execution threw exception: {str(e)}"


def format_status(passed: bool, milestone: str, current_milestone: str) -> str:
    if passed:
        return "\033[92m[PASS]\033[0m"
    if current_milestone and milestone != current_milestone and milestone > current_milestone:
        return "\033[93m[PENDING]\033[0m"
    return "\033[91m[FAIL]\033[0m"


def main() -> int:
    parser = argparse.ArgumentParser(description="Stellar Evolution Explorer E2E Test Runner")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4], help="Run a specific tier only")
    parser.add_argument("--milestone", type=str, choices=["M1", "M2", "M3"], help="Target milestone")
    parser.add_argument("--json", type=str, help="Export results as JSON file")
    parser.add_argument("--skip-build-check", action="store_true", help="Skip initial build_explorer_html.py execution")
    args = parser.parse_args()

    print("=" * 80)
    print(" STELLAR EVOLUTION EXPLORER — E2E TEST SUITE RUNNER")
    print(f" Python: {sys.version.split()[0]} | Working Directory: {PROJECT_ROOT}")
    print("=" * 80)

    # 1. Build Pipeline Verification
    build_ok = True
    build_msg = ""
    if not args.skip_build_check:
        print("\n[*] Step 1: Checking Build Pipeline (build_explorer_html.py)...")
        build_ok, build_msg = verify_build_pipeline()
        if build_ok:
            print(f"    \033[92m[PASS]\033[0m {build_msg}")
        else:
            print(f"    \033[91m[FAIL]\033[0m {build_msg}")

    # 2. Initialize Harness
    harness = StellarExplorerHarness()
    try:
        harness.load_grid_data()
        html_content = harness.get_html_content()
        print(f"[*] Step 2: Loaded HTML target ({len(html_content) / 1024:.1f} KB) & Grid Dataset (28 models)")
    except Exception as e:
        print(f"[-] Fatal error initializing test harness: {e}")
        return 1

    # 3. Collect Test Results
    all_results: List[TestResult] = []
    tiers_to_run = [args.tier] if args.tier else [1, 2, 3, 4]

    if 1 in tiers_to_run:
        all_results.extend(run_tier1_tests(harness))
    if 2 in tiers_to_run:
        all_results.extend(run_tier2_tests(harness))
    if 3 in tiers_to_run:
        all_results.extend(run_tier3_tests(harness))
    if 4 in tiers_to_run:
        all_results.extend(run_tier4_tests(harness))

    # Filter by milestone if specified
    if args.milestone:
        filtered_results = [r for r in all_results if r.milestone == args.milestone]
    else:
        filtered_results = all_results

    # 4. Print Results by Tier
    tier_names = {
        1: "Tier 1: Feature Coverage (Core Requirements)",
        2: "Tier 2: Boundary & Corner Cases",
        3: "Tier 3: Cross-Feature Interactions",
        4: "Tier 4: Real-World Scenarios",
    }

    print("\n[*] Step 3: Executing Test Cases...")
    for t in tiers_to_run:
        tier_cases = [r for r in filtered_results if r.tier == t]
        if not tier_cases:
            continue
        print(f"\n--- {tier_names.get(t, f'Tier {t}')} ({len(tier_cases)} cases) ---")
        for r in tier_cases:
            status = format_status(r.passed, r.milestone, args.milestone or "")
            print(f" {status} [{r.test_id}] {r.name:<60} ({r.duration_ms:.1f}ms)")
            if not r.passed:
                print(f"        \033[90m↳ Reason: {r.message}\033[0m")

    # 5. Summary Statistics
    total_count = len(filtered_results)
    passed_count = sum(1 for r in filtered_results if r.passed)
    failed_count = total_count - passed_count
    pass_rate = (passed_count / total_count * 100.0) if total_count > 0 else 0.0

    print("\n" + "=" * 80)
    print(" TEST SUITE SUMMARY")
    print("=" * 80)
    print(f" Total Test Cases Run : {total_count}")
    print(f" Passed               : \033[92m{passed_count}\033[0m")
    print(f" Failed / Pending     : \033[91m{failed_count}\033[0m")
    print(f" Pass Rate            : {pass_rate:.1f}%")
    print(f" Build Pipeline Clean : {'YES' if build_ok else 'NO (Escalate build bug)'}")

    # Breakdown by Tier
    print("\n Breakdown by Tier:")
    for t in tiers_to_run:
        t_cases = [r for r in filtered_results if r.tier == t]
        t_pass = sum(1 for r in t_cases if r.passed)
        t_total = len(t_cases)
        pct = (t_pass / t_total * 100.0) if t_total > 0 else 0.0
        print(f"   Tier {t}: {t_pass}/{t_total} ({pct:.1f}%)")

    # Breakdown by Milestone
    m1_cases = [r for r in filtered_results if r.milestone == "M1"]
    m2_cases = [r for r in filtered_results if r.milestone == "M2"]
    print("\n Breakdown by Implementation Milestone:")
    print(f"   Milestone M1 (Web UI & Export) : {sum(1 for r in m1_cases if r.passed)}/{len(m1_cases)} passed")
    print(f"   Milestone M2 (3D Cutaway)      : {sum(1 for r in m2_cases if r.passed)}/{len(m2_cases)} passed")

    # Discovered Defects to Escalate
    discovered_bugs = []
    if not build_ok:
        discovered_bugs.append(f"Build Pipeline: {build_msg}")
    for r in filtered_results:
        if not r.passed and r.milestone == "M1":
            discovered_bugs.append(f"[{r.test_id}] {r.name}: {r.message}")

    if discovered_bugs:
        print("\n \033[93mDiscovered Implementation Gaps / Defects to Escalate:\033[0m")
        for b in discovered_bugs[:10]:
            print(f"   - {b}")
        if len(discovered_bugs) > 10:
            print(f"   ... and {len(discovered_bugs) - 10} more.")

    # 6. JSON Export
    if args.json:
        report_data = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "build_ok": build_ok,
            "build_message": build_msg,
            "total": total_count,
            "passed": passed_count,
            "failed": failed_count,
            "pass_rate": pass_rate,
            "results": [
                {
                    "test_id": r.test_id,
                    "name": r.name,
                    "tier": r.tier,
                    "feature": r.feature,
                    "milestone": r.milestone,
                    "passed": r.passed,
                    "message": r.message,
                    "duration_ms": r.duration_ms,
                }
                for r in filtered_results
            ],
        }
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        print(f"\n JSON report exported to: {args.json}")

    print("=" * 80)
    # Exit with code 0 if all tests pass and build is ok; otherwise 1
    return 0 if (failed_count == 0 and build_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
