"""
Stellar Radial Abundance Profiles and Normalization
===================================================
Calculates 60-point normalized radial chemical mass fractions X_i(q) over
relative mass coordinate q = m/M* in [0.01, 1.0] across 7 principal isotopes:
  H1, He4, C12, O16, Ne20, Si28, Fe56
Enforces strict mass conservation: sum_i X_i(q) == 1.0 at every radial zone.
"""

import math
from typing import Dict, List, Any
import numpy as np


def normalize_abundance_stack(stack: np.ndarray) -> np.ndarray:
    """Ensure non-negative abundances and strict sum_i X_i = 1.0 across all radial points."""
    stack = np.maximum(0.0, stack)
    totals = np.sum(stack, axis=0)
    # Avoid zero division
    totals = np.where(totals <= 0.0, 1.0, totals)
    return stack / totals


def compute_abundance_profile(mass: float, z: float, stage_idx: int, pathway: Dict[str, Any]) -> Dict[str, List[float]]:
    """
    Compute 60-point radial abundance profile X_i(q) over relative mass coordinate q in [0.01, 1.0]
    for stage_idx in [0, 1, 2, 3, 4, 5], strictly normalized so sum_i X_i(q) = 1.0.

    Parameters:
        mass: Initial stellar mass in M_sun
        z: Initial metallicity
        stage_idx: Stage integer index (0: ZAMS, 1: TAMS, 2: RGB, 3: CHeB, 4: AGB, 5: Remnant)
        pathway: Evolutionary pathway classification dict

    Returns:
        dict with keys "q", "H1", "He4", "C12", "O16", "Ne20", "Si28", "Fe56"
    """
    q_arr = np.linspace(0.01, 1.0, 60)
    zeta = math.log10(z / 0.014)

    X_init = max(0.68, 0.745 - 2.2 * z)
    Y_init = max(0.24, 1.0 - X_init - z)
    c_init = 0.24 * z
    o_init = 0.50 * z
    ne_init = 0.12 * z
    si_init = 0.07 * z
    fe_init = 1.0 - (X_init + Y_init + c_init + o_init + ne_init + si_init)

    H1 = np.full_like(q_arr, X_init)
    He4 = np.full_like(q_arr, Y_init)
    C12 = np.full_like(q_arr, c_init)
    O16 = np.full_like(q_arr, o_init)
    Ne20 = np.full_like(q_arr, ne_init)
    Si28 = np.full_like(q_arr, si_init)
    Fe56 = np.full_like(q_arr, fe_init)

    def sig(q, q0, width=0.03):
        return 0.5 * (1.0 + np.tanh((q - q0) / width))

    if stage_idx == 0:
        pass
    elif mass < 0.5:
        # Fully convective red dwarf: homogeneous burning -> blue dwarf -> He WD
        if stage_idx == 1:
            H1[:] = 0.18
            He4[:] = 1.0 - z - 0.18
        elif stage_idx == 2:
            w = sig(q_arr, 0.75, 0.08)
            H1 = 0.015 * (1.0 - w) + 0.08 * w
            He4 = 1.0 - z - H1
        else:
            w = sig(q_arr, 0.94, 0.02)
            H1 = 0.001 * (1.0 - w) + X_init * w
            He4 = (1.0 - z - 0.001) * (1.0 - w) + Y_init * w
    else:
        q_core_ms = 0.14 if mass < 1.3 else min(0.44, 0.19 * (mass ** 0.27))

        if stage_idx == 1:
            w = sig(q_arr, q_core_ms, 0.04)
            H1 = X_init * w
            He4 = (1.0 - z) * (1.0 - w) + Y_init * w
        elif stage_idx == 2:
            q_he = q_core_ms * 1.12
            w = sig(q_arr, q_he, 0.025)
            H1 = (X_init - 0.02) * w
            He4 = (1.0 - z) * (1.0 - w) + (Y_init + 0.02) * w
        elif stage_idx == 3:
            q_co = q_core_ms * 0.65
            q_he = q_core_ms * 1.25
            w_co = sig(q_arr, q_co, 0.03)
            w_he = sig(q_arr, q_he, 0.03)
            in_co = 1.0 - w_co
            in_he_shell = w_co * (1.0 - w_he)
            in_env = w_he

            H1 = (X_init - 0.025) * in_env
            He4 = 0.32 * in_co + (1.0 - z) * in_he_shell + (Y_init + 0.025) * in_env
            C12 = 0.40 * in_co + c_init * (in_he_shell + in_env)
            O16 = (0.28 - z) * in_co + o_init * (in_he_shell + in_env)
        elif stage_idx == 4:
            if mass < 7.0:
                q_co = min(0.75, 0.48 + 0.05 * mass)
                q_he = min(0.84, q_co + 0.08)
                w_co = sig(q_arr, q_co, 0.02)
                w_he = sig(q_arr, q_he, 0.02)
                in_co = 1.0 - w_co
                in_he = w_co * (1.0 - w_he)
                in_env = w_he

                H1 = (X_init - 0.03) * in_env
                He4 = (1.0 - z) * in_he + (Y_init + 0.03) * in_env
                C12 = 0.38 * in_co + c_init * (in_he + in_env)
                O16 = (0.62 - z) * in_co + o_init * (in_he + in_env)
            elif mass < 10.0:
                q_one = 0.58
                q_co = 0.68
                q_he = 0.78
                w1 = sig(q_arr, q_one, 0.02)
                w2 = sig(q_arr, q_co, 0.02)
                w3 = sig(q_arr, q_he, 0.02)
                in_one = 1.0 - w1
                in_co = w1 * (1.0 - w2)
                in_he = w2 * (1.0 - w3)
                in_env = w3

                H1 = (X_init - 0.04) * in_env
                He4 = (1.0 - z) * in_he + (Y_init + 0.04) * in_env
                C12 = 0.04 * in_one + 0.36 * in_co + c_init * (in_he + in_env)
                O16 = 0.60 * in_one + (0.64 - z) * in_co + o_init * (in_he + in_env)
                Ne20 = (0.36 - z) * in_one + ne_init * (in_co + in_he + in_env)
            else:
                q_on = 0.24 + 0.004 * (mass - 15.0)
                q_co = 0.38 + 0.006 * (mass - 15.0)
                q_he = 0.55 + 0.008 * (mass - 15.0) - 0.03 * zeta
                w1 = sig(q_arr, q_on, 0.02)
                w2 = sig(q_arr, q_co, 0.02)
                w3 = sig(q_arr, q_he, 0.02)
                in_on = 1.0 - w1
                in_co = w1 * (1.0 - w2)
                in_he = w2 * (1.0 - w3)
                in_env = w3

                H1 = (X_init - 0.05) * in_env
                He4 = (1.0 - z) * in_he + (Y_init + 0.05) * in_env
                C12 = 0.05 * in_on + 0.35 * in_co + c_init * (in_he + in_env)
                O16 = 0.66 * in_on + (0.65 - z) * in_co + o_init * (in_he + in_env)
                Ne20 = 0.24 * in_on + ne_init * (in_co + in_he + in_env)
                Si28 = (0.05 - z) * in_on + si_init * (in_co + in_he + in_env)
        elif stage_idx == 5:
            if mass < 7.0:
                w_co = sig(q_arr, 0.92, 0.015)
                w_he = sig(q_arr, 0.98, 0.01)
                in_co = 1.0 - w_co
                in_he = w_co * (1.0 - w_he)
                in_h = w_he
                H1 = X_init * in_h
                He4 = (1.0 - z) * in_he + Y_init * in_h
                C12 = 0.38 * in_co + c_init * (in_he + in_h)
                O16 = (0.62 - z) * in_co + o_init * (in_he + in_h)
            elif mass < 10.0:
                w_one = sig(q_arr, 0.88, 0.015)
                w_co = sig(q_arr, 0.96, 0.015)
                in_one = 1.0 - w_one
                in_co = w_one * (1.0 - w_co)
                in_he = w_co
                H1[:] = 0.0
                He4 = (1.0 - z) * in_he
                C12 = 0.03 * in_one + 0.36 * in_co + c_init * in_he
                O16 = 0.60 * in_one + (0.64 - z) * in_co + o_init * in_he
                Ne20 = (0.37 - z) * in_one + ne_init * (in_co + in_he)
            else:
                wind_factor = (z / 0.014) ** 0.65
                m_final = max(6.0, mass * (1.0 - (0.285 * ((mass / 15.0) ** 1.38) * wind_factor)))
                m_fe = 1.44 + 0.012 * (mass - 15.0)
                q_fe = min(0.18, max(0.08, m_fe / m_final))
                q_si = q_fe + 0.075 + 0.002 * (mass - 15.0)
                q_o = q_si + 0.080 + 0.002 * (mass - 15.0)
                q_ne = q_o + 0.080 + 0.002 * (mass - 15.0)
                q_c = q_ne + 0.080 + 0.002 * (mass - 15.0)
                q_he = min(0.85, q_c + 0.16 + 0.003 * (mass - 15.0) + 0.035 * (-zeta))

                w_fe = sig(q_arr, q_fe, 0.010)
                w_si = sig(q_arr, q_si, 0.010)
                w_o = sig(q_arr, q_o, 0.010)
                w_ne = sig(q_arr, q_ne, 0.010)
                w_c = sig(q_arr, q_c, 0.010)
                w_he = sig(q_arr, q_he, 0.015)

                s_fe = 1.0 - w_fe
                s_si = w_fe * (1.0 - w_si)
                s_o = w_si * (1.0 - w_o)
                s_ne = w_o * (1.0 - w_ne)
                s_c = w_ne * (1.0 - w_c)
                s_he = w_c * (1.0 - w_he)
                s_env = w_he

                H1 = (X_init - 0.06) * s_env
                He4 = (1.0 - z) * s_he + (Y_init + 0.06) * s_env
                C12 = 0.04 * s_o + 0.06 * s_ne + 0.56 * s_c + c_init * (s_he + s_env)
                O16 = 0.14 * s_si + 0.72 * s_o + 0.32 * s_ne + 0.32 * s_c + o_init * (s_he + s_env)
                Ne20 = 0.16 * s_o + 0.56 * s_ne + 0.06 * s_c + ne_init * (s_he + s_env)
                Si28 = 0.08 * s_fe + 0.78 * s_si + 0.08 * s_o + 0.06 * s_ne + si_init * (s_c + s_he + s_env)
                Fe56 = 0.92 * s_fe + 0.08 * s_si + fe_init * (s_o + s_ne + s_c + s_he + s_env)

    raw_stack = np.vstack([H1, He4, C12, O16, Ne20, Si28, Fe56])
    stack = normalize_abundance_stack(raw_stack)

    return {
        "q": [round(float(x), 4) for x in q_arr],
        "H1": [round(float(x), 4) for x in stack[0]],
        "He4": [round(float(x), 4) for x in stack[1]],
        "C12": [round(float(x), 4) for x in stack[2]],
        "O16": [round(float(x), 4) for x in stack[3]],
        "Ne20": [round(float(x), 4) for x in stack[4]],
        "Si28": [round(float(x), 4) for x in stack[5]],
        "Fe56": [round(float(x), 4) for x in stack[6]],
    }
