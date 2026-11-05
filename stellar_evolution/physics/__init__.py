"""
Physics Subpackage: Analytical Scaling, Tracks, Kippenhahn, Abundances, and Nucleosynthesis
==========================================================================================
"""

from .zams import (
    MASS_GRID,
    METALLICITY_GRID,
    STAGE_NAMES,
    SPECIES,
    zams_properties,
)
from .kippenhahn import (
    compute_kippenhahn_series,
    get_convective_boundaries_at_stage,
)
from .abundance import (
    compute_abundance_profile,
    normalize_abundance_stack,
)
from .nucleosynthesis import (
    calc_pp_rate,
    calc_cno_rate,
    calc_triple_alpha_rate,
    calc_carbon_burning_rate,
    calc_oxygen_burning_rate,
    calc_silicon_burning_rate,
    identify_dominant_element,
    generate_onion_shells,
)
from .evolution import (
    classify_pathway,
    compute_stage_anchors,
    generate_track,
    build_full_grid,
)

__all__ = [
    "MASS_GRID",
    "METALLICITY_GRID",
    "STAGE_NAMES",
    "SPECIES",
    "zams_properties",
    "compute_kippenhahn_series",
    "get_convective_boundaries_at_stage",
    "compute_abundance_profile",
    "normalize_abundance_stack",
    "calc_pp_rate",
    "calc_cno_rate",
    "calc_triple_alpha_rate",
    "calc_carbon_burning_rate",
    "calc_oxygen_burning_rate",
    "calc_silicon_burning_rate",
    "identify_dominant_element",
    "generate_onion_shells",
    "classify_pathway",
    "compute_stage_anchors",
    "generate_track",
    "build_full_grid",
]
