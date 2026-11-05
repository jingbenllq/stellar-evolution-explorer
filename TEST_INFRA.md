# TEST_INFRA — Stellar Evolution Simulation & Interactive Web Explorer

This document specifies the end-to-end testing architecture, philosophy, tier taxonomy, execution guidelines, and quality thresholds for the Stellar Evolution Project.

---

## 1. Test Philosophy

1. **Opaque-Box & Requirement-Driven**:
   - Tests are derived strictly from the authoritative specifications in `ORIGINAL_REQUEST.md` (R1–R5) and the interface contracts in `PROJECT.md` (§ Interface Contracts).
   - Tests evaluate system behavior against external contracts, APIs, CLI entrypoints, output artifacts, and physical invariances rather than transient private implementation details.
2. **Astrophysical Ground Truth & Mathematical Rigor**:
   - Expected outputs are based on verified astrophysics principles:
     - Stefan-Boltzmann law: $L = 4\pi R^2 \sigma T_{\text{eff}}^4 \iff \log_{10}(T_{\text{eff}}) = 3.7613 + 0.25\log_{10}(L) - 0.50\log_{10}(R)$.
     - Solar ZAMS calibration: $L_{\text{ZAMS}} \approx 0.70\,L_\odot$ ($\log L \approx -0.155$), $R_{\text{ZAMS}} \approx 0.89\,R_\odot$, $t_{\text{MS}} \approx 10\,\text{Gyr}$.
     - Fully convective low-mass stars ($M \le 0.35\,M_\odot$): homogeneous mixing, flat radial chemical abundances, lifetimes $>500\,\text{Gyr}$.
     - Massive star onion-skin structure ($M \ge 15\,M_\odot$): 7 concentric burning shells ($\text{H} \to \text{He} \to \text{C} \to \text{Ne} \to \text{O} \to \text{Si} \to \text{Fe}$) with core collapse endpoint.
     - Strict abundance conservation: $\sum_{i} X_i(q) = 1.0 \pm 0.01$ across all radial mass coordinates $q \in [0, 1]$.
3. **Anti-Cheat & Genuine Execution**:
   - Facade tests, dummy passes, or assertions tailored to circumvent real computation are strictly prohibited.
   - All tests inspect actual data files (`stellar_grid_data.json`), generated figures in `figures/`, compiled HTML/JS files (`index.html`, `stellar_explorer.html`), and parse authentic Fortran MESA outputs.
4. **Progressive Testability**:
   - The test suite is designed to execute cleanly at every milestone:
     - Directly verifies standalone entrypoints (`stellar_grid_engine.py`, `build_explorer_html.py`, `generate_figures.py`, `memory_watchdog.py`).
     - Dynamically leverages modular imports (`stellar_evolution.physics`, `stellar_evolution.mesa`, `stellar_evolution.viz`, `stellar_evolution.core`) when available.
     - Provides synthetic standard MESA log fixtures to rigorously verify `NativeMesaParser` even before WSL/MESA live runs conclude.

---

## 2. Feature Inventory Mapping to Test Tiers

All 22 features defined in `PROJECT.md` are systematically assigned across four testing tiers:

| Feature ID | Feature Name | Milestone | Test Tier | Primary Test Class / Target |
|------------|--------------|-----------|-----------|-----------------------------|
| **F1** | D-Drive Directory Setup | M1 | Tier 1 | `TestTier1Features.test_d_drive_structure` |
| **F2** | MESA 26.4.1 & SDK Environment | M1 | Tier 1 | `TestTier1Features.test_mesa_configs_and_inlists` |
| **F3** | Memory Safety Guard (<85% RAM) | M1 | Tier 1 | `TestTier1Features.test_memory_watchdog_guard` |
| **F4** | MESA 1 $M_\odot$ Simulation Pipeline | M1 | Tier 1, 4 | `TestTier4RealWorldScenarios.test_scenario_solar_full_lifecycle` |
| **F5** | Workspace Synchronization | M1 | Tier 1 | `TestTier1Features.test_workspace_synchronization_structure` |
| **F6** | Native MESA Parser (`NativeMesaParser`) | M2 | Tier 1, 2 | `TestTier1Features.test_native_mesa_parser_history_and_profile` |
| **F7** | Unified Data Model (`StellarModel`) | M2 | Tier 1, 3 | `TestTier1Features.test_unified_stellar_model_contract` |
| **F8** | Physics Engine Modularity | M2 | Tier 1 | `TestTier1Features.test_physics_engine_modularity` |
| **F9** | Scientific Plotting Pipeline | M2 | Tier 1, 3 | `TestTier1Features.test_scientific_plotting_pipeline` |
| **F10** | Comprehensive Unit Test Suite | M2 | Tier 1 | All Unit & E2E Suites |
| **F11** | Web UI Aesthetic Redesign | M3 | Tier 1 | `TestTier1Features.test_web_ui_structure_and_assets` |
| **F12** | Responsive Layout & Theater Mode | M3 | Tier 1 | `TestTier1Features.test_responsive_layout_and_canvas` |
| **F13** | Telemetry HUD Optimization | M3 | Tier 1 | `TestTier1Features.test_telemetry_hud_elements` |
| **F14** | Concentric Nuclear Burning Shells | M4 | Tier 1, 4 | `TestTier1Features.test_concentric_burning_shells` |
| **F15** | Active Nuclear Burning Ring Glows | M4 | Tier 1 | `TestTier1Features.test_burning_ring_glow_elements` |
| **F16** | Convective vs Radiative Zoning | M4 | Tier 1 | `TestTier1Features.test_convective_vs_radiative_zoning` |
| **F17** | Tri-Coordinate Radius/Mass Toggle | M4 | Tier 1 | `TestTier1Features.test_tri_coordinate_toggle_in_frontend` |
| **F18** | 3D Raycaster Hover Layer Inspection | M4 | Tier 1 | `TestTier1Features.test_raycaster_hover_inspection_logic` |
| **F19** | 2D/3D Dual View Presentation | M4 | Tier 1 | `TestTier1Features.test_dual_view_presentation_modes` |
| **F20** | End-to-End Test Suite Execution | M5 | Tiers 1–4 | `test_e2e_stellar_evolution.py` Execution |
| **F21** | Git Sync & GitHub Push | M5 | Tier 1 | `TestTier1Features.test_git_clean_and_repo_integrity` |
| **F22** | GitHub Pages Deployment Verification | M5 | Tier 1, 3 | `TestTier1Features.test_github_pages_entrypoint_parity` |

---

## 3. Tier Architecture & Test Descriptions

### Tier 1: Functional & Feature Unit Coverage
Verifies that each individual component adheres to its defined public API and operational contracts:
- **CLI & Scripts Execution**: Ensures `stellar_grid_engine.py`, `build_explorer_html.py`, `generate_figures.py`, and `memory_watchdog.py` execute cleanly without unhandled exceptions.
- **Native MESA Parser**: Validates ASCII reading of MESA `LOGS/history.data`, `LOGS/profiles.index`, and `LOGS/profile*.data`, handling Fortran `D+`/`D-` exponents and deduplication of backup steps (`remove_backups`).
- **Data Model Integrity**: Validates the unified `StellarModel` JSON schema containing mass, metallicity, evolutionary stage anchors, Kippenhahn boundaries, and normalized isotopic abundances ($X_{\text{H1}}, X_{\text{He4}}, \dots, X_{\text{Fe56}}$).
- **Web UI & Onion-Skin Elements**: Asserts that `index.html` and `stellar_explorer.html` contain all required DOM structures, high-DPI canvas containers, Three.js shaders/cutaway meshes, coordinate toggle controls ($q$, $r/R_\star$, $\log r$), and interactive diagnostic HUD cards.

### Tier 2: Boundary & Corner Cases
Stress tests numerical limits, extreme parameter configurations, and malformed inputs:
- **Mass Extremes**:
  - $M = 0.3\,M_\odot$ (lowest boundary): Fully convective interior, $t_{\text{MS}} > 500\,\text{Gyr}$, flat radial abundance gradient ($\Delta X_{\text{H1}} < 0.005$), ends as helium white dwarf without helium flash.
  - $M = 25.0\,M_\odot$ (highest boundary): Intense radiation pressure, $t_{\text{MS}} \approx 6.5\,\text{Myr}$, full 7-stage advanced burning onion-skin interior with central Fe56 core prior to core collapse.
- **Metallicity Extremes**:
  - $Z = 0.0001$ (extreme sub-solar): Drastically reduced bound-free/free-free opacity $\kappa$, hotter and more compact ZAMS, higher luminosity ($\Delta \log L > 0$), reduced mass loss.
  - $Z = 0.03$ (super-solar): Elevated opacity, expanded convective envelopes, lower effective temperature, enhanced mass loss.
- **MESA Parser Robustness**:
  - Handling malformed Fortran numbers (e.g. `1.23456-004` without `E` or `D`, `NaN`, `Infinity`).
  - Graceful handling of empty log files, comment-only files, or missing column headers.
  - History files with non-monotonic model numbers or backtracked steps (`remove_backups` validation).
- **Physical Invariances**:
  - Abundance conservation: $\sum_{i=1}^7 X_i(q) = 1.0 \pm 0.01$ at every radial point $q \in [0, 1]$.
  - Stefan-Boltzmann consistency: $|\log L - (2\log R + 4\log(T_{\text{eff}}/5772\,\text{K}))| < 0.02$.
  - Lifetime monotonicity with stellar mass: $t_{\text{MS}}(0.3) > t_{\text{MS}}(1.0) > t_{\text{MS}}(3.0) > t_{\text{MS}}(8.0) > t_{\text{MS}}(25.0)$.

### Tier 3: Cross-Feature Integration Pipelines
Exercises complete end-to-end multi-module pipelines:
1. **Simulation-to-Web Pipeline**:
   - `NativeMesaParser` parses raw MESA simulation logs $\to$ Converts to `StellarModel` $\to$ `generate_figures.py` renders publication diagnostics $\to$ `build_explorer_html.py` embeds data into standalone `index.html` and `stellar_explorer.html`.
2. **Memory Watchdog Guard Pipeline**:
   - Verifies that `memory_watchdog.py` monitors real-time system memory and alerts or throttles when exceeding defined thresholds (Warning: 80%, Emergency: 84%, Hard limit: 85%).
3. **Artifact Parity Pipeline**:
   - Validates that `index.html` and `stellar_explorer.html` are generated consistently from `build_explorer_html.py` and are 100% byte-identical.

### Tier 4: Real-World Astrophysics Application Scenarios
Simulates authentic astrophysical research investigations:
1. **Scenario 1 — Solar Lifecycle ($1.0\,M_\odot, Z = 0.014$)**:
   - Verifies transition from ZAMS ($L = 0.70\,L_\odot, R = 0.89\,R_\odot, T_c \approx 1.35\times 10^7\,\text{K}$) through Main Sequence (age $\approx 10\,\text{Gyr}$), Subgiant, Red Giant Branch (isothermal degenerate He core, shell H burning), Core Helium Flash, Horizontal Branch / CHeB, Asymptotic Giant Branch, thermal pulses, planetary nebula ejection, to a final Carbon-Oxygen White Dwarf ($M_{\text{WD}} \approx 0.6\,M_\odot$).
2. **Scenario 2 — Massive Star Supernova Progenitor ($25.0\,M_\odot, Z = 0.014$)**:
   - Verifies complete progression of nuclear burning stages:
     $\text{H} \to \text{He} \to \text{C} \to \text{Ne} \to \text{O} \to \text{Si} \to \text{Fe core collapse}$.
   - Verifies spatial stratifications in the Onion-Skin diagram:
     - Outermost: Hydrogen envelope ($X_{\text{H1}} > 0.60$)
     - He shell / mantle
     - C-O mantle
     - O-Ne-Mg layer
     - Si-S layer
     - Innermost: Fe56 core ($X_{\text{Fe56}} > 0.70$)
   - Endpoint: Core mass exceeds Chandrasekhar mass ($M_c > 1.4\,M_\odot$), triggering core-collapse supernova yielding a Neutron Star or Black Hole remnant.
3. **Scenario 3 — Metallicity-Induced Fate Bifurcation ($8.0\,M_\odot$)**:
   - Compares $8.0\,M_\odot$ at solar metallicity ($Z = 0.014$, forming an Oxygen-Neon White Dwarf via stellar wind mass loss) versus low metallicity ($Z = 0.0001$, undergoing core-collapse to form a Neutron Star due to lower mass loss and higher core mass).

---

## 4. Test Architecture & Runner Command

### Standard Test Runner
To run all unit and end-to-end tests across the entire project:

```powershell
cd C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project
py -3 -m unittest discover tests
```

Or using explicit pattern and directory specification:
```powershell
py -3 -m unittest discover -s tests -p "test_*.py" -v
```

### Dedicated Runner Script (`run_tests.py`)
A dedicated test runner script is provided at the project root for formatted reporting and tiered test filtering:

```powershell
# Run all tests
py -3 run_tests.py

# Run specific tier
py -3 run_tests.py --tier 1
py -3 run_tests.py --tier 2
py -3 run_tests.py --tier 3
py -3 run_tests.py --tier 4
```

---

## 5. Coverage Thresholds & Quality Gates

| Metric | Target Threshold | Enforcement Mechanism |
|--------|------------------|-----------------------|
| **Test Pass Rate** | **100%** (0 failures, 0 errors) | Automated test runner in CI / pre-commit |
| **Grid Parameter Coverage** | **28 / 28 models (100%)** | `TestStellarPhysicsAudit.test_28_models_present` |
| **Mass Range Coverage** | $0.3, 1.0, 3.0, 5.0, 8.0, 15.0, 25.0\,M_\odot$ | Tier 1 & 2 test assertions |
| **Metallicity Range Coverage** | $Z \in [0.0001, 0.001, 0.014, 0.03]$ | Tier 1 & 2 test assertions |
| **Chemical Abundance Conservation** | $|\sum X_i(q) - 1.0| \le 0.01$ | `test_strict_abundance_normalization` |
| **Memory Ceiling** | Peak RAM utilization $< 85\%$ | `memory_watchdog.py` threshold test |
| **Asset Identity** | `index.html` $\equiv$ `stellar_explorer.html` | Tier 1 & 3 hash / byte comparison |
| **Figure Generation Output** | 3 publication figures in `figures/` | Tier 1 & 3 file verification |

---

*Authored by `test_writer_e2e` for the Stellar Evolution Project verification pipeline.*
