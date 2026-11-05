"""
Stellar Evolution Simulation & Parameter Space Package
======================================================
Modular toolkit providing:
  - core: physical constants, schemas, error types
  - physics: ZAMS scaling, evolutionary tracks, Kippenhahn boundaries, nucleosynthesis
  - mesa: pure-Python NativeMesaParser, MesaLogDir, MesaBridge
  - viz: publication-grade 4-panel and diagnostic figures
"""

from .core.constants import (
    G,
    M_sun,
    L_sun,
    R_sun,
    sigma_SB,
    yr_s,
    T_EFF_SUN,
    G_CGS,
    G_SI,
    M_SUN_CGS,
    M_SUN_SI,
    L_SUN_CGS,
    L_SUN_SI,
    R_SUN_CGS,
    R_SUN_SI,
    SIGMA_SB_CGS,
    SIGMA_SB_SI,
    stefan_boltzmann_luminosity,
    stefan_boltzmann_radius,
    stefan_boltzmann_teff,
)
from .core.schemas import (
    StellarModel,
    StageModel,
    OnionShellModel,
    HistoryData,
    ProfileData,
    ProfileInfo,
)
from .core.exceptions import (
    StellarEvolutionError,
    MesaParseError,
    MesaFormatError,
    PhysicsConsistencyError,
    ValidationError,
)
from .physics.zams import (
    MASS_GRID,
    METALLICITY_GRID,
    STAGE_NAMES,
    SPECIES,
    zams_properties,
)
from .physics.evolution import (
    classify_pathway,
    compute_stage_anchors,
    generate_track,
    build_full_grid,
)
from .physics.kippenhahn import (
    compute_kippenhahn_series,
    get_convective_boundaries_at_stage,
)
from .physics.abundance import (
    compute_abundance_profile,
    normalize_abundance_stack,
)
from .physics.nucleosynthesis import (
    calc_pp_rate,
    calc_cno_rate,
    calc_triple_alpha_rate,
    calc_carbon_burning_rate,
    calc_oxygen_burning_rate,
    calc_silicon_burning_rate,
    generate_onion_shells,
)
from .mesa.native_parser import (
    parse_fortran_float,
    NativeMesaParser,
    MesaLogDir,
)
from .mesa.bridge import (
    MesaBridge,
    STAGE_NAME_MAP,
)
from .viz.publication_figures import generate_mesa_summary_4panel
from .viz.diagnostic_plots import (
    generate_hr_diagram_grid,
    generate_rho_tc_phase_space,
    generate_abundance_profiles_comparison,
    generate_all_diagnostic_figures,
)

__version__ = "2.1.0"

__all__ = [
    # Constants
    "G",
    "M_sun",
    "L_sun",
    "R_sun",
    "sigma_SB",
    "yr_s",
    "T_EFF_SUN",
    "G_CGS",
    "G_SI",
    "M_SUN_CGS",
    "M_SUN_SI",
    "L_SUN_CGS",
    "L_SUN_SI",
    "R_SUN_CGS",
    "R_SUN_SI",
    "SIGMA_SB_CGS",
    "SIGMA_SB_SI",
    "stefan_boltzmann_luminosity",
    "stefan_boltzmann_radius",
    "stefan_boltzmann_teff",
    # Schemas & Exceptions
    "StellarModel",
    "StageModel",
    "OnionShellModel",
    "HistoryData",
    "ProfileData",
    "ProfileInfo",
    "StellarEvolutionError",
    "MesaParseError",
    "MesaFormatError",
    "PhysicsConsistencyError",
    "ValidationError",
    # Physics
    "MASS_GRID",
    "METALLICITY_GRID",
    "STAGE_NAMES",
    "SPECIES",
    "zams_properties",
    "classify_pathway",
    "compute_stage_anchors",
    "generate_track",
    "build_full_grid",
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
    "generate_onion_shells",
    # MESA
    "parse_fortran_float",
    "NativeMesaParser",
    "MesaLogDir",
    "MesaBridge",
    "STAGE_NAME_MAP",
    # Viz
    "generate_mesa_summary_4panel",
    "generate_hr_diagram_grid",
    "generate_rho_tc_phase_space",
    "generate_abundance_profiles_comparison",
    "generate_all_diagnostic_figures",
]
