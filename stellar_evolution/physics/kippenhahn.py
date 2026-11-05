"""
Kippenhahn Interior Mixing and Shell Burning Boundaries
======================================================
Calculates radial convective core boundary (conv_core), convective envelope base
(conv_env), hydrogen burning shell (h_shell), and helium burning shell (he_shell)
as a function of stellar mass, metallicity, and evolutionary stage parameter s in [0, 5].
"""

import math
from typing import Dict, List, Optional, Any
import numpy as np


def compute_kippenhahn_series(mass: float, z: float, s_grid: np.ndarray) -> Dict[str, List[Optional[float]]]:
    """
    Compute compact Kippenhahn zone boundary arrays over continuous stage parameter s_grid.

    Parameters:
        mass: Stellar mass (M_sun)
        z: Stellar metallicity
        s_grid: 1D numpy array of stage parameter values in [0.0, 5.0]

    Returns:
        dict containing:
            "conv_core": list of convective core top boundaries (q = m/M*)
            "conv_env": list of convective envelope bottom boundaries (q = m/M*)
            "h_shell": list of hydrogen burning shell coordinates (or None)
            "he_shell": list of helium burning shell coordinates (or None)
    """
    conv_core: List[float] = []
    conv_env: List[float] = []
    h_shell: List[Optional[float]] = []
    he_shell: List[Optional[float]] = []

    for s_val in s_grid:
        s_val = float(s_val)
        if mass < 0.5:
            # 0.3 M_sun: Fully convective -> He enrichment -> Blue dwarf -> He WD
            if s_val < 1.8:
                cc, ce, hs, hes = 0.0, 0.0, None, None
            elif s_val < 3.0:
                frac = (s_val - 1.8) / 1.2
                cc, ce, hs, hes = 0.0, min(0.98, 0.25 + 0.73 * frac), 0.85, None
            else:
                cc, ce, hs, hes = 0.0, 0.99, None, None
        elif mass < 2.2:
            # Low-mass solar type: radiative core on MS, deep convective envelope on RGB
            if s_val <= 1.0:
                cc, ce, hs, hes = 0.0, 0.975 - 0.04 * s_val, None, None
            elif s_val <= 2.0:
                u = s_val - 1.0
                cc, ce, hs, hes = 0.0, 0.935 - 0.65 * math.sin(u * math.pi * 0.85), 0.14 + 0.30 * u, None
            elif s_val <= 3.5:
                u = (s_val - 2.0) / 1.5
                cc, ce, hs, hes = 0.16 * (1.0 - 0.2 * u), 0.72 - 0.22 * u, 0.52 + 0.06 * u, None
            elif s_val <= 4.3:
                u = (s_val - 3.5) / 0.8
                cc, ce, hs, hes = 0.0, 0.58 + 0.35 * u, 0.56 + 0.22 * u, 0.50 + 0.24 * u
            else:
                cc, ce, hs, hes = 0.0, 0.995, None, None
        else:
            # Intermediate and massive stars: convective core on MS
            q_cc0 = min(0.52, 0.21 * (mass ** 0.28))
            if s_val <= 1.0:
                cc, ce, hs, hes = q_cc0 * (1.0 - 0.38 * s_val), 0.992, None, None
            elif s_val <= 2.0:
                u = s_val - 1.0
                cc, ce, hs, hes = 0.04 * (1.0 - u), 0.99 - 0.58 * (u ** 1.4), q_cc0 * 0.65 + 0.06 * u, None
            elif s_val <= 3.5:
                u = (s_val - 2.0) / 1.5
                cc = q_cc0 * (0.48 + 0.12 * u)
                ce = 0.65 + 0.25 * math.sin(u * math.pi) if mass < 10 else 0.48 - 0.10 * u
                hs, hes = q_cc0 * 0.78 + 0.08 * u, None
            else:
                u = min(1.0, (s_val - 3.5) / 1.5)
                cc = (q_cc0 * 0.28 * (1.0 - 0.5 * u)) if mass >= 10 else 0.0
                ce = 0.38 + 0.12 * u if mass >= 10 else min(0.99, 0.45 + 0.54 * u)
                hs = min(0.92, q_cc0 * 0.88 + 0.15 * u) if (mass >= 10 or u < 0.6) else None
                hes = min(0.84, q_cc0 * 0.65 + 0.12 * u) if (mass >= 10 or u < 0.6) else None

        conv_core.append(round(cc, 3))
        conv_env.append(round(ce, 3))
        h_shell.append(round(hs, 3) if hs is not None else None)
        he_shell.append(round(hes, 3) if hes is not None else None)

    return {
        "conv_core": conv_core,
        "conv_env": conv_env,
        "h_shell": h_shell,
        "he_shell": he_shell,
    }


def get_convective_boundaries_at_stage(mass: float, z: float, stage_idx: int) -> Dict[str, Any]:
    """Retrieve convective and shell boundaries at an integer stage index (0 to 5)."""
    s_arr = np.array([float(stage_idx)])
    res = compute_kippenhahn_series(mass, z, s_arr)
    return {
        "conv_core": res["conv_core"][0],
        "conv_env": res["conv_env"][0],
        "h_shell": res["h_shell"][0],
        "he_shell": res["he_shell"][0],
    }
