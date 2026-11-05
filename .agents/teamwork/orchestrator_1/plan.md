# Plan: MESA Setup, Architecture Refactoring, Web UI & Onion-Skin Overhaul

## Overview
Comprehensive delivery of all requirements specified in ORIGINAL_REQUEST.md:
1. Environment & MESA setup in `D:\天体物理导论` with memory watchdog (<85% RAM).
2. Architectural optimization of local simulation/grid engines and MESA log parsers.
3. Modern, aesthetic web UI redesign.
4. Complete scientific and visual overhaul of the Onion-Skin interior cross-section diagram (洋葱图).
5. Comprehensive testing, Git commit/push to `main`, and live GitHub Pages validation.

## Execution Phases
- **Phase 0: Survey**:
  - Spawn 3 Explorers in parallel to inspect (1) MESA guides/WSL/D-drive environment, (2) Python engine & test code layout, (3) Frontend assets, UI structure, and onion-skin rendering logic.
- **Phase 1: Project Plan & Contracts**:
  - Synthesize Explorer reports into `PROJECT.md` with full feature inventory, interface contracts, and milestone breakdown.
- **Phase 2: Milestone Execution**:
  - M1: D-drive MESA setup, pipeline scripts, memory watchdog (<85% RAM), simulation run & data generation.
  - M2: Python codebase refactoring (`stellar_grid_engine.py`, `build_explorer_html.py`, `generate_figures.py`, parsers, tests).
  - M3: Web UI complete visual & aesthetic redesign (`stellar_explorer.html` & `index.html`).
  - M4: Onion-skin diagram (洋葱图) deep overhaul (shell structures, burning rings, convective zones, interactive inspectability, true physical mapping).
  - M5: Parallel E2E testing suite, verification, Git commit & push, and GitHub Pages deployment check.
