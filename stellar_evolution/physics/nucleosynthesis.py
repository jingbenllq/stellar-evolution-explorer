"""
Stellar Nucleosynthesis Burning Rates and Interior Shell Structure
==================================================================
Implements semi-analytical nuclear energy generation rates (erg g^-1 s^-1)
and physical burning regime diagnostics:
  - Proton-Proton (PP) chain: eps_pp ~ rho * X^2 * T_6^(-2/3) * exp(-33.80 / T_6^(1/3))
  - CNO cycle: eps_cno ~ rho * X * Z_cno * T_6^(-2/3) * exp(-152.28 / T_6^(1/3))
  - Triple-alpha (3a) helium burning: eps_3a ~ rho^2 * Y^3 * T_8^(-3) * exp(-44.027 / T_8)
  - Advanced burning: Carbon, Neon, Oxygen, and Silicon burning
Provides onion-skin shell boundary identification conforming to PROJECT.md interface contracts.
"""

import math
from typing import Dict, List, Any, Optional
import numpy as np

from ..core.schemas import OnionShellModel


def calc_pp_rate(rho: float, T: float, X: float = 0.70) -> float:
    """
    Compute PP-chain energy generation rate eps_pp in erg g^-1 s^-1.
    Dominates at T ~ (1.0 - 1.8) * 10^7 K.
    """
    if T < 3.0e6 or rho <= 0.0 or X <= 0.0:
        return 0.0
    T6 = T / 1.0e6
    # Standard Kippenhahn & Weigert / Hansen-Kawaler parameterization
    # eps_pp ~ 2.4e4 * rho * X^2 * T6^(-2/3) * exp(-33.80 / T6^(1/3))
    try:
        val = 2.38e4 * rho * (X ** 2) * (T6 ** (-2.0 / 3.0)) * math.exp(-33.80 / (T6 ** (1.0 / 3.0)))
        return float(val)
    except OverflowError:
        return 0.0


def calc_cno_rate(rho: float, T: float, X: float = 0.70, Z_cno: float = 0.014) -> float:
    """
    Compute CNO-cycle energy generation rate eps_cno in erg g^-1 s^-1.
    Surpasses PP-chain above T ~ 1.8 * 10^7 K with steep ~T^16 - T^20 temperature dependence.
    """
    if T < 1.0e7 or rho <= 0.0 or X <= 0.0 or Z_cno <= 0.0:
        return 0.0
    T6 = T / 1.0e6
    try:
        val = 8.67e27 * rho * X * (Z_cno * 0.5) * (T6 ** (-2.0 / 3.0)) * math.exp(-152.28 / (T6 ** (1.0 / 3.0)))
        return float(val)
    except OverflowError:
        return 0.0


def calc_triple_alpha_rate(rho: float, T: float, Y: float = 0.98) -> float:
    """
    Compute Triple-alpha helium burning rate eps_3a in erg g^-1 s^-1.
    Ignites at T >= 1.0 * 10^8 K (T8 >= 1.0) with extreme ~T^40 sensitivity.
    """
    if T < 6.0e7 or rho <= 0.0 or Y <= 0.0:
        return 0.0
    T8 = T / 1.0e8
    try:
        val = 5.09e8 * (rho ** 2) * (Y ** 3) * (T8 ** -3.0) * math.exp(-44.027 / T8)
        return float(val)
    except OverflowError:
        return 0.0


def calc_carbon_burning_rate(rho: float, T: float, X_C: float = 0.50) -> float:
    """
    Compute 12C + 12C fusion energy generation rate in erg g^-1 s^-1.
    Ignites at T >= 5.0 * 10^8 K (T9 >= 0.5).
    """
    if T < 4.0e8 or rho <= 0.0 or X_C <= 0.0:
        return 0.0
    T9 = T / 1.0e9
    try:
        val = 1.0e16 * rho * (X_C ** 2) * (T9 ** -0.667) * math.exp(-84.165 / (T9 ** (1.0 / 3.0)))
        return float(val)
    except OverflowError:
        return 0.0


def calc_oxygen_burning_rate(rho: float, T: float, X_O: float = 0.60) -> float:
    """Compute 16O + 16O fusion rate in erg g^-1 s^-1, igniting at T >= 1.8 * 10^9 K."""
    if T < 1.4e9 or rho <= 0.0 or X_O <= 0.0:
        return 0.0
    T9 = T / 1.0e9
    try:
        val = 2.0e28 * rho * (X_O ** 2) * (T9 ** -0.667) * math.exp(-135.93 / (T9 ** (1.0 / 3.0)))
        return float(val)
    except OverflowError:
        return 0.0


def calc_silicon_burning_rate(rho: float, T: float, X_Si: float = 0.80) -> float:
    """Compute Silicon photodisintegration and alpha-capture rate, active at T >= 3.0 * 10^9 K."""
    if T < 2.5e9 or rho <= 0.0 or X_Si <= 0.0:
        return 0.0
    T9 = T / 1.0e9
    try:
        val = 1.0e29 * rho * X_Si * math.exp(-150.0 / T9)
        return float(val)
    except OverflowError:
        return 0.0


def identify_dominant_element(abundances: Dict[str, float]) -> str:
    """Find the most abundant element abbreviation."""
    if not abundances:
        return "H"
    best_elem = "H"
    best_frac = -1.0
    for elem, frac in abundances.items():
        if frac > best_frac:
            best_frac = frac
            best_elem = elem
    # Strip mass number (e.g. H1 -> H, He4 -> He, C12 -> C, Fe56 -> Fe)
    clean_name = "".join([c for c in best_elem if not c.isdigit()])
    return clean_name or "H"


def generate_onion_shells(
    mass: float,
    z: float,
    stage_idx: int,
    track_point: Dict[str, Any],
    profile: Dict[str, List[float]],
) -> List[OnionShellModel]:
    """
    Construct concentric OnionShellModel objects for a specific stage from the
    radial composition profile and physical track state.

    Conforms strictly to PROJECT.md § Interface Contracts:
      - dominant_element: "H", "He", "C", "O", "Ne", "Si", "Fe"
      - q_inner, q_outer: mass coordinates in [0, 1]
      - r_inner_norm, r_outer_norm: radial coordinates in [0, 1]
      - is_convective: whether zone is convective
      - burning_active: whether nuclear burning is currently active
      - burning_reaction: burning reaction name ("pp-chain", "CNO-cycle", "3-alpha", etc.)
      - temperature_K, density_cgs: characteristic layer T and rho
      - abundances: dict of isotopic mass fractions
    """
    q_arr = np.array(profile["q"])
    species = ["H1", "He4", "C12", "O16", "Ne20", "Si28", "Fe56"]
    n_pts = len(q_arr)

    # Central conditions
    log_Tc = track_point.get("log_Tc", 7.15)
    log_Rhoc = track_point.get("log_Rhoc", 1.95)
    log_Teff = track_point.get("log_Teff", 3.76)
    Tc = 10.0 ** log_Tc
    Rhoc = 10.0 ** log_Rhoc
    Teff = 10.0 ** log_Teff

    # Identify shell boundaries by finding zones where dominant element changes
    dom_arr = []
    for i in range(n_pts):
        local_abund = {sp: profile[sp][i] for sp in species}
        dom_arr.append(identify_dominant_element(local_abund))

    # Segment into contiguous shells
    segments: List[Dict[str, Any]] = []
    cur_dom = dom_arr[0]
    start_idx = 0

    for i in range(1, n_pts):
        if dom_arr[i] != cur_dom:
            segments.append({
                "dom": cur_dom,
                "start": start_idx,
                "end": i,
            })
            cur_dom = dom_arr[i]
            start_idx = i

    segments.append({
        "dom": cur_dom,
        "start": start_idx,
        "end": n_pts,
    })

    shells: List[OnionShellModel] = []
    n_segs = len(segments)

    # Compute strictly contiguous boundaries B_0, B_1, ..., B_n
    # Ensure q_in^(k+1) == q_out^(k) across all interfaces
    boundaries = [0.0]
    for seg_idx in range(1, n_segs):
        i_s = segments[seg_idx]["start"]
        b_val = 0.5 * (float(q_arr[i_s - 1]) + float(q_arr[i_s]))
        boundaries.append(round(b_val, 4))
    boundaries.append(1.0)

    for seg_idx, seg in enumerate(segments):
        i_s = seg["start"]
        i_e = seg["end"] - 1
        elem = seg["dom"]

        q_in = boundaries[seg_idx]
        q_out = boundaries[seg_idx + 1]

        # Radius coordinate mapping: r ~ q^0.45 in realistic stellar polytropes
        r_in = 0.0 if seg_idx == 0 else round(float(q_in ** 0.45), 4)
        r_out = 1.0 if seg_idx == n_segs - 1 else round(float(q_out ** 0.45), 4)

        # Midpoint conditions
        mid_idx = (i_s + i_e) // 2
        q_mid = 0.5 * (q_in + q_out)
        t_factor = max(0.01, 1.0 - (q_mid ** 0.5))
        rho_factor = max(1.0e-7, (1.0 - (q_mid ** 0.35)) ** 3.0)

        layer_T = max(Teff, Tc * t_factor)
        layer_rho = max(1.0e-8, Rhoc * rho_factor)

        abund_dict = {sp: float(profile[sp][mid_idx]) for sp in species}

        # Convective status
        is_conv = False
        if mass <= 0.4:
            is_conv = True
        elif mass < 1.3:
            # Solar type: convective envelope (outer ~30% mass)
            if q_mid >= 0.70:
                is_conv = True
        else:
            # Intermediate/massive: convective core on MS / helium core
            if q_mid <= 0.25 and stage_idx <= 3:
                is_conv = True
            elif q_mid >= 0.65 and stage_idx >= 2:
                is_conv = True

        # Nuclear burning activity
        burning_active = False
        reaction = "None"

        if elem == "H" and stage_idx <= 4:
            if layer_T >= 8.0e6 and abund_dict.get("H1", 0.0) > 0.05:
                burning_active = True
                reaction = "pp-chain" if mass < 1.3 else "CNO-cycle"
        elif elem == "He" and stage_idx in [2, 3, 4, 5]:
            if layer_T >= 8.0e7 and abund_dict.get("He4", 0.0) > 0.10:
                burning_active = True
                reaction = "3-alpha"
        elif elem == "C" and stage_idx in [4, 5] and mass >= 7.0:
            if layer_T >= 5.0e8:
                burning_active = True
                reaction = "C-burning"
        elif elem == "O" and stage_idx in [4, 5] and mass >= 7.0:
            if layer_T >= 1.5e9:
                burning_active = True
                reaction = "O-burning"
        elif elem in ["Ne", "Mg"] and stage_idx == 5 and mass >= 10.0:
            if layer_T >= 1.2e9:
                burning_active = True
                reaction = "Ne-burning"
        elif elem == "Si" and stage_idx == 5 and mass >= 10.0:
            if layer_T >= 2.5e9:
                burning_active = True
                reaction = "Si-burning"

        shell_name = f"{elem}_core" if q_in == 0.0 else (f"{elem}_envelope" if q_out >= 0.999 else f"{elem}_shell")

        shell = OnionShellModel(
            name=shell_name,
            dominant_element=elem,
            q_inner=round(q_in, 4),
            q_outer=round(q_out, 4),
            r_inner_norm=round(r_in, 4),
            r_outer_norm=round(r_out, 4),
            is_convective=is_conv,
            burning_active=burning_active,
            burning_reaction=reaction,
            temperature_K=round(layer_T, 1),
            density_cgs=round(layer_rho, 4),
            abundances=abund_dict,
        )
        shells.append(shell)

    return shells
