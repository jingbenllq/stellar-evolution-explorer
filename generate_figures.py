#!/usr/bin/env python3
"""
Generate High-Resolution Static Diagnostic Figures (v2.1 Physics Audited)
=========================================================================
Backward-compatible root entrypoint forwarding to `stellar_evolution.viz`.
Outputs publication-grade PNG figures into `figures/`:
  1. figures/hr_diagram_grid.png
  2. figures/rho_tc_phase_space.png
  3. figures/abundance_profiles_comparison.png
"""

from pathlib import Path
from stellar_evolution.viz import (
    generate_all_diagnostic_figures,
    generate_hr_diagram_grid,
    generate_rho_tc_phase_space,
    generate_abundance_profiles_comparison,
)


def main():
    base = Path(__file__).parent
    generate_all_diagnostic_figures(base)


if __name__ == "__main__":
    main()
