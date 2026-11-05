"""
Visualization Subpackage: Publication Figures and Diagnostic Plots
===================================================================
"""

from .publication_figures import generate_mesa_summary_4panel
from .diagnostic_plots import (
    generate_hr_diagram_grid,
    generate_rho_tc_phase_space,
    generate_abundance_profiles_comparison,
    generate_all_diagnostic_figures,
)

__all__ = [
    "generate_mesa_summary_4panel",
    "generate_hr_diagram_grid",
    "generate_rho_tc_phase_space",
    "generate_abundance_profiles_comparison",
    "generate_all_diagnostic_figures",
]
