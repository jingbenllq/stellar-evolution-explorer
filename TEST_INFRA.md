# Test Infrastructure (TEST_INFRA.md)

## 1. Overview & Architecture
The Stellar Evolution Explorer project features an automated, headless End-to-End (E2E) testing framework designed for rigorous verification on Windows and cross-platform environments. It tests both static HTML/DOM/CSS asset structures and dynamic JavaScript/Canvas/WebGL runtime logic without requiring external browser installations.

- **Primary Runner**: `tests/run_e2e_tests.py` (Python 3.11+ standard library).
- **Runtime Simulation**: Dual-engine validation combining Python AST/DOM parsing with Node.js headless mock runtime for deep dynamic JavaScript evaluation.
- **Data Source**: Embedded `stellar_grid_data.json` containing 28 stellar models across 7 initial masses and 4 metallicities.
- **Zero External PIP Dependencies**: The entire suite executes out-of-the-box using standard library Python (`json`, `re`, `subprocess`, `math`, `pathlib`, `sys`).

---

## 2. Directory Layout & Test Suite Hierarchy

```
tests/
├── run_e2e_tests.py           # Master automated test runner and CLI orchestrator
├── test_harness.py            # Headless browser mock environment & Node.js execution engine
├── test_tier1_features.py     # Tier 1: Core Feature Coverage (>=5 tests per feature, 30 tests)
├── test_tier2_boundaries.py   # Tier 2: Boundary & Corner Cases (>=5 tests per area, 30 tests)
├── test_tier3_interactions.py # Tier 3: Cross-Feature Interactions (6 tests)
└── test_tier4_scenarios.py    # Tier 4: Real-World Astrophysics Scenarios (6 tests)
```

---

## 3. Four-Tier Testing Methodology

| Tier | Category | Scope | Cases | Description |
|:---|:---|:---|:---:|:---|
| **Tier 1** | **Feature Coverage** | 6 Features | 30 | Verifies baseline functional presence and specifications for: 3D cutaway onion-skin, high-DPI canvas handling, interactive hover tooltips, multi-speed playback, timeline stage markers, and one-click export. |
| **Tier 2** | **Boundary & Corner Cases** | 6 Boundary Areas | 30 | Evaluates extreme values, numerical guards, and stress conditions: limits 0 and 199, boundary speeds 0.5x and 5.0x, extreme stellar masses 0.3 and 25.0 $M_\odot$, metallicities $Z = 0.0001$ and $0.03$, rapid UI toggling, and zero-division guards. |
| **Tier 3** | **Cross-Feature Interactions** | Concurrency & State Sync | 6 | Tests concurrent operations: speed change during stage seek, data export during animation playback, high-DPI resize during 3D camera rotation, comparative track overlays with tooltips, and raycast hit detection during dynamic pulsation. |
| **Tier 4** | **Real-World Scenarios** | Astrophysics & Visual Workflows | 6 | Validates end-to-end scientific and visual scenarios: $25\ M_\odot$ supernova precursor onion-skin structure, $1\ M_\odot$ degenerate helium flash signature, full CSV track exports with UTF-8 BOM, 80-zone radial profiles, composite 4-panel dashboard layout, and convective red dwarf limits. |

**Total Test Cases**: **72 Test Cases**

---

## 4. Execution Commands

### 4.1 Complete Test Suite Execution
```powershell
# From project root:
py -3 tests/run_e2e_tests.py
```

### 4.2 Milestone-Filtered Execution
```powershell
# Run only Milestone M1 features (Web UI & Export):
py -3 tests/run_e2e_tests.py --milestone M1

# Run Milestone M2 features (3D Cutaway Onion-Skin):
py -3 tests/run_e2e_tests.py --milestone M2
```

### 4.3 Tier-Specific Execution
```powershell
# Run Tier 1 only (Feature Coverage):
py -3 tests/run_e2e_tests.py --tier 1

# Run Tier 2 only (Boundary & Corner Cases):
py -3 tests/run_e2e_tests.py --tier 2

# Run Tier 3 only (Cross-Feature Interactions):
py -3 tests/run_e2e_tests.py --tier 3

# Run Tier 4 only (Real-World Scenarios):
py -3 tests/run_e2e_tests.py --tier 4
```

### 4.4 Structured JSON Report Output
```powershell
py -3 tests/run_e2e_tests.py --json test_report.json
```

---

## 5. Verification Invariants & Exit Codes
- **Exit Code 0**: All executed test cases pass and `build_explorer_html.py` compiles cleanly without errors.
- **Exit Code 1**: One or more executed test cases fail, or `build_explorer_html.py` raises an unhandled exception or non-zero return code.
- **Headless Execution**: All tests execute non-interactively without opening GUI windows, suitable for CI/CD pipelines and headless build environments.
