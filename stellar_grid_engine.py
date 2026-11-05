#!/usr/bin/env python3
"""
Stellar Evolution Parameter Space Engine (v2.1 — Modular & MESA Audited)
========================================================================
Backward-compatible root entrypoint forwarding to the modular
`stellar_evolution.physics` subpackage.

Maintains exact public API and CLI entrypoint:
  - MASS_GRID, METALLICITY_GRID, STAGE_NAMES, SPECIES
  - zams_properties(mass, z)
  - classify_pathway(mass, z)
  - compute_stage_anchors(mass, z, zams, pathway)
  - compute_kippenhahn_series(mass, z, s_grid)
  - compute_abundance_profile(mass, z, stage_idx, pathway)
  - generate_track(mass, z, n_steps=200)
  - build_full_grid(out_dir)
"""

from pathlib import Path
from stellar_evolution.physics import (
    MASS_GRID,
    METALLICITY_GRID,
    STAGE_NAMES,
    SPECIES,
    zams_properties,
    classify_pathway,
    compute_stage_anchors,
    compute_kippenhahn_series,
    compute_abundance_profile,
    generate_track,
    build_full_grid,
)

__all__ = [
    "MASS_GRID",
    "METALLICITY_GRID",
    "STAGE_NAMES",
    "SPECIES",
    "zams_properties",
    "classify_pathway",
    "compute_stage_anchors",
    "compute_kippenhahn_series",
    "compute_abundance_profile",
    "generate_track",
    "build_full_grid",
]


if __name__ == "__main__":
    build_full_grid(Path(__file__).parent)
