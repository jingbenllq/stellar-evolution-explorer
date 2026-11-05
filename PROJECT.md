# Project: Stellar Evolution Simulation & Interactive Web Explorer

## Architecture
The system consists of three interconnected layers:
1. **Simulation & Data Ingestion Layer (`D:\天体物理导论` & `stellar_evolution.mesa`)**:
   - Host WSL2 Ubuntu 26.04 simulation workspace in `D:\天体物理导论` with memory-safe watchdog (<85% RAM).
   - High-fidelity MESA 26.4.1 environment and simulation pipeline (1 $M_\odot$ ZAMS and grid runs).
   - Zero-dependency `NativeMesaParser` and `MesaBridge` reading standard MESA `LOGS/history.data`, `profiles.index`, and `profile*.data` (Fortran floats, `remove_backups`, profile interpolation).
2. **Analytical Physics & Grid Engine (`stellar_evolution.physics` / `stellar_grid_engine.py`)**:
   - Calibrated 28-model stellar evolution grid ($0.3 - 25.0\,M_\odot$, $Z = 0.0001 - 0.03$).
   - Stefan-Boltzmann, mass-luminosity scaling, Kippenhahn convective/radiative boundaries, nucleosynthetic burning rates, and normalized composition profiles.
   - Unified `StellarModel` data representation bridging analytical grid and MESA outputs.
3. **Interactive Visual Dashboard & Onion-Skin Engine (`build_explorer_html.py` -> `index.html` & `stellar_explorer.html`)**:
   - Single-source generator producing zero-server standalone HTML with embedded Three.js WebGL and 2D canvas engines.
   - Modernized UI presentation: floating control dock, high-contrast telemetry HUD, responsive 2x2 scientific plots with theater-mode expansion.
   - Overhauled Stellar Interior Onion-Skin Diagram (洋葱图): concentric nuclear burning shells ($\text{H} \to \text{He} \to \text{C} \to \text{Ne} \to \text{O} \to \text{Si} \to \text{Fe}$), pulsating burning ring glows, convective vs radiative visual styling, tri-coordinate mapping ($q$, $r/R_\star$, $\log r$), 3D Raycaster hover diagnostics, and 2D publication cross-section.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | D-Drive Directory Setup | Structure and initialize `D:\天体物理导论` with safe permissions and symlink | M1 | ORIGINAL_REQUEST §R1 |
| F2 | MESA 26.4.1 & SDK Environment | Download/configure MESA and MESA SDK in WSL2 with Townsend 26.6.1 | M1 | ORIGINAL_REQUEST §R1, Survey 1 |
| F3 | Memory Safety Guard (<85% RAM) | Enforce .wslconfig, OMP_NUM_THREADS, streaming I/O, and real-time psutil watchdog | M1 | ORIGINAL_REQUEST §R1, Survey 1 |
| F4 | MESA 1 $M_\odot$ Simulation Pipeline | Run 1 $M_\odot$ simulation producing verified `LOGS/history.data` and profiles | M1 | ORIGINAL_REQUEST §R1, Reference Docs |
| F5 | Workspace Synchronization | Bidirectional sync of code, figures, data, and docs between D: drive and repo | M1 | ORIGINAL_REQUEST §R1 |
| F6 | Native MESA Parser (`NativeMesaParser`) | Parse `history.data`, `profiles.index`, `profile*.data` with Fortran `D+` support | M2 | ORIGINAL_REQUEST §R2, Survey 2 |
| F7 | Unified Data Model (`StellarModel`) | Bridge MESA simulation outputs and calibrated 28-model analytical grid | M2 | ORIGINAL_REQUEST §R2, Survey 2 |
| F8 | Physics Engine Modularity | Modularize `stellar_grid_engine.py` into clean architecture with backward compatibility | M2 | ORIGINAL_REQUEST §R2, Survey 2 |
| F9 | Scientific Plotting Pipeline | Publication-grade 4-panel figure generator following `py_mesa_reader` tutorial | M2 | ORIGINAL_REQUEST §R2, Reference Docs |
| F10 | Comprehensive Unit Test Suite | Expand unit tests to 40+ tests across physics, parsing, normalization, and grid | M2 | ORIGINAL_REQUEST §R2, Survey 2 |
| F11 | Web UI Aesthetic Redesign | Modern spectator-friendly dark UI, compact floating control dock, refined typography | M3 | ORIGINAL_REQUEST §R3, Survey 3 |
| F12 | Responsive Layout & Theater Mode | Prevent 1100px collapse, add canvas theater/fullscreen zoom mode, high-DPI scaling | M3 | ORIGINAL_REQUEST §R3, Survey 3 |
| F13 | Telemetry HUD Optimization | High-contrast cards, comparison mode stability, clean metric badges | M3 | ORIGINAL_REQUEST §R3, Survey 3 |
| F14 | Concentric Nuclear Burning Shells | Accurately render 7 burning layers ($\text{H} \to \text{Fe}$) based on mass & stage | M4 | ORIGINAL_REQUEST §R4, Survey 3 |
| F15 | Active Nuclear Burning Ring Glows | Pulsating volumetric energy release rings ($\epsilon_{\text{nuc}}$ interfaces) | M4 | ORIGINAL_REQUEST §R4, Survey 3 |
| F16 | Convective vs Radiative Zoning | Visual differentiation between convective mixing churn and radiative stratification | M4 | ORIGINAL_REQUEST §R4, Survey 3 |
| F17 | Tri-Coordinate Radius/Mass Toggle | Switch between normalized mass $q$, true radius $r/R_\star$, and log radius $\log r$ | M4 | ORIGINAL_REQUEST §R4, Survey 3 |
| F18 | 3D Raycaster Hover Layer Inspection | Interactive mouse hover diagnostic tooltip displaying $T, \rho, P, q, X_i$, reactions | M4 | ORIGINAL_REQUEST §R4, Survey 3 |
| F19 | 2D/3D Dual View Presentation | Switch between 3D rotatable cutaway sphere and 2D publication cross-section | M4 | ORIGINAL_REQUEST §R4, Survey 3 |
| F20 | End-to-End Test Suite Execution | 100% pass of unit and multi-tier E2E tests | M5 | ORIGINAL_REQUEST §R5 |
| F21 | Git Sync & GitHub Push | Commit and push all refactored code and assets to `main` branch | M5 | ORIGINAL_REQUEST §R5 |
| F22 | GitHub Pages Deployment Verification | Verify live status and functional rendering on GitHub Pages | M5 | ORIGINAL_REQUEST §R5 |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | MESA Environment, Memory Guard (<85%) & D-Drive Setup | F1, F2, F3, F4, F5 | none | DONE |
| M2 | Python Engine & Native MESA Reader Pipeline Refactoring | F6, F7, F8, F9, F10 | none | DONE |
| M3 | Web Explorer UI Aesthetic Redesign & Presentation Deck | F11, F12, F13 | none | DONE |
| M4 | Stellar Interior Onion-Skin Diagram (洋葱图) Complete Overhaul | F14, F15, F16, F17, F18, F19 | M3 | DONE |
| M5 | Full Verification, Git Sync & GitHub Pages Live Deployment | F20, F21, F22 | M1, M2, M4 | DONE |

---

## Interface Contracts

### 1. `NativeMesaParser` ↔ Simulation Logs
- **Input**: Path to MESA directory or `LOGS/` folder.
- **Methods**:
  - `read_history(path)` -> `HistoryData`: dictionary of column arrays (e.g. `model_number`, `star_age`, `log_L`, `log_Teff`, `log_R`, `log_center_T`, `log_center_Rho`, etc.) with `remove_backups=True` deduplication.
  - `read_profile(path)` -> `ProfileData`: dictionary of radial arrays (`mass`, `radius`, `temperature`, `density`, `pressure`, `x`, `y`, `z`, isotopic abundances `h1`, `he4`, `c12`, `o16`, `ne20`, `si28`, `fe56`).
  - `read_index(path)` -> `list[ProfileInfo]` mapping `model_number` to profile number.

### 2. `StellarModel` ↔ Frontend Generator (`build_explorer_html.py`)
- **Schema**:
  ```python
  {
      "mass": float,
      "metallicity": float,
      "stages": [
          {
              "name": str,  # "ZAMS", "TAMS", "RGB", "CHeB", "AGB", "Remnant"
              "age_yr": float,
              "log_L": float,
              "log_Teff": float,
              "radius_Rsun": float,
              "onion_shells": [
                  {
                      "name": str,  # "H_env", "He_core", "C_O_core", etc.
                      "dominant_element": str,
                      "q_inner": float,
                      "q_outer": float,
                      "r_inner_norm": float,
                      "r_outer_norm": float,
                      "is_convective": bool,
                      "burning_active": bool,
                      "burning_reaction": str,
                      "temperature_K": float,
                      "density_cgs": float,
                      "abundances": dict[str, float]
                  }
              ]
          }
      ]
  }
  ```

### 3. Build Script ↔ Output Assets
- `build_explorer_html.py` generates `index.html` and `stellar_explorer.html` (100% byte-identical, zero external local server dependencies, self-contained Three.js / Canvas rendering).

---

## Code Layout
```
stellar_evolution_project/
├── .agents/teamwork/             # Agent metadata only (never put code here)
├── .github/workflows/pages.yml   # GitHub Pages deployment action
├── index.html                    # Live entrypoint for GitHub Pages
├── stellar_explorer.html         # Interactive standalone web explorer
├── build_explorer_html.py        # Single-source HTML & visualizer generator
├── stellar_grid_engine.py        # Backward-compatible grid engine entrypoint
├── generate_figures.py           # Publication figure generator
├── memory_watchdog.py            # Real-time host memory safety daemon (<85% RAM)
├── mesa_configs/                 # MESA inlist templates and grid run configs
├── stellar_evolution/            # Modular Python package
│   ├── __init__.py
│   ├── core/                     # Constants, schemas, exceptions
│   ├── physics/                  # ZAMS, tracks, kippenhahn, burning rates
│   ├── mesa/                     # NativeMesaParser, MesaBridge, log utils
│   └── viz/                      # Figure generation, publication plots
├── tests/                        # Comprehensive unit & regression test suite
│   ├── test_stellar_grid.py
│   ├── test_mesa_parser.py
│   ├── test_physics_consistency.py
│   └── test_build_html.py
└── D:\天体物理导论/               # MESA workspace, downloads, SDK, simulations
    ├── mesa-26.4.1/
    ├── mesasdk/
    ├── mesa_work/
    ├── LOGS/
    └── memory_watchdog.py
```
