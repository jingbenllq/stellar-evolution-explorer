## 2026-11-04T23:35:33Z

You are test_writer_e2e, a teamwork_test_writer subagent.
Your Working Directory: C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project\.agents\teamwork\test_writer_e2e
Original Request Path: C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project\.agents\teamwork\ORIGINAL_REQUEST.md
Project Scope Document: C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project\PROJECT.md

MANDATORY FIRST STEP: Read ORIGINAL_REQUEST.md and PROJECT.md.

Task:
Design and build the comprehensive End-to-End (E2E) testing track:
1. Read the Feature Inventory in PROJECT.md (Features F1 through F22).
2. Create `TEST_INFRA.md` at the project root `C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project\TEST_INFRA.md` following the required template in the Project Pattern:
   - Test philosophy (opaque-box, requirement-driven, derived from user requirements).
   - Feature inventory mapping to tiers.
   - Test architecture and runner command (`py -3 -m unittest discover tests` or dedicated runner).
   - Real-world application scenarios.
   - Coverage thresholds.
3. Implement the E2E test suite in `tests/test_e2e_stellar_evolution.py` (or tiered test files in `tests/`):
   - Tier 1: Feature coverage (test each feature's entrypoints, CLI, parser, and HTML outputs).
   - Tier 2: Boundary & corner cases (extreme stellar masses like 0.3 and 25 M_sun, extreme metallicities 0.0001 and 0.03, empty logs, malformed Fortran floats, negative values).
   - Tier 3: Cross-feature combinations (MESA parser -> unified StellarModel -> figure generation -> HTML builder).
   - Tier 4: Real-world application scenarios (simulating Sun 1.0 M_sun from ZAMS to WD, massive star 25 M_sun core-collapse onion skin).
4. Run the test suite and verify test runner execution.
5. Publish `TEST_READY.md` at project root `C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project\TEST_READY.md` with:
   - Test runner command
   - Coverage summary table (Tiers 1-4)
   - Feature checklist
6. Write your handoff report to `handoff.md` in your working directory and notify the orchestrator via send_message.
