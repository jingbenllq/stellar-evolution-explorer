"""
Zero-Age Main Sequence (ZAMS) Scaling and Calibration
=====================================================
Implements MESA/MIST-calibrated global and central properties across the
stellar mass grid (0.3 - 25.0 M_sun) and metallicity range (0.0001 - 0.03):
  - Piecewise mass-luminosity relation with CNO transition and radiation pressure flattening
  - Mass-radius scaling and Stefan-Boltzmann consistency
  - Metallicity-dependent opacity corrections (zeta = log10(Z / 0.014))
  - Exact solar calibration at ZAMS: log_L = -0.155 (0.70 L_sun), R = 0.89 R_sun, Teff = 5600 K
"""

import math
from typing import Dict, Any, List

MASS_GRID: List[float] = [0.3, 1.0, 3.0, 5.0, 8.0, 15.0, 25.0]
METALLICITY_GRID: List[float] = [0.0001, 0.001, 0.014, 0.03]

STAGE_NAMES: List[str] = [
    "ZAMS 零龄主序",
    "TAMS 主序拐点",
    "RGB/HG 壳层氢燃烧与氦点火",
    "CHeB 中心氦燃烧 (HB/蓝环/RSG)",
    "AGB/晚期碳氧燃烧",
    "演化终点 (WD冷却 / 铁核坍缩前夕)",
]

SPECIES: List[str] = ["H1", "He4", "C12", "O16", "Ne20", "Si28", "Fe56"]


def zams_properties(mass: float, z: float) -> Dict[str, Any]:
    """
    Compute MESA/MIST-calibrated ZAMS global and central properties.

    Parameters:
        mass: Initial stellar mass in solar masses (M_sun), 0.3 <= mass <= 25.0
        z: Initial metallicity, e.g. 0.0001 <= z <= 0.03

    Returns:
        dict containing log_L, log_R, log_Teff, log_Tc, log_Rhoc, t_ms, f_core, zeta
    """
    zeta = math.log10(z / 0.014)

    # Opacity-driven metallicity shift: lower Z -> lower bound-free/free-free opacity
    # -> more compact, hotter, and more luminous at ZAMS
    z_lum = -0.095 * zeta if mass < 10.0 else -0.040 * zeta
    z_rad = 0.046 * zeta if mass < 10.0 else 0.024 * zeta

    # Mass-Luminosity relation with solar ZAMS calibration (-0.155 at 1 M_sun, L = 0.70 L_sun),
    # CNO transition steepening (1-2 M_sun), Kramers regime (2-10 M_sun),
    # and radiation-pressure / electron-scattering flattening (M >= 10 M_sun)
    if mass < 0.43:
        log_L = math.log10(0.19 * (mass ** 2.35)) + z_lum
    elif mass < 1.0:
        log_L = -0.155 + 4.10 * math.log10(mass) + z_lum
    elif mass < 2.0:
        log_L = -0.155 + 4.50 * math.log10(mass) + z_lum
    elif mass < 10.0:
        log_L2 = -0.155 + 4.50 * math.log10(2.0)  # 1.200 at 2 M_sun
        log_L = log_L2 + 3.65 * math.log10(mass / 2.0) + z_lum
    else:
        log_L10 = -0.155 + 4.50 * math.log10(2.0) + 3.65 * math.log10(10.0 / 2.0)  # 3.751 at 10 M_sun
        log_L = log_L10 + 2.75 * math.log10(mass / 10.0) + z_lum

    # Mass-Radius relation with solar ZAMS calibration (-0.051 at 1 M_sun, R = 0.89 R_sun)
    if mass < 1.0:
        log_R = -0.051 + 0.86 * math.log10(mass) + z_rad
    elif mass < 1.5:
        log_R = -0.051 + 0.92 * math.log10(mass) + z_rad
    else:
        log_R15 = -0.051 + 0.92 * math.log10(1.5)
        log_R = log_R15 + 0.57 * math.log10(mass / 1.5) + z_rad

    # Stefan-Boltzmann law: L / L_sun = (R / R_sun)^2 * (Teff / 5772 K)^4
    # log10(Teff) = log10(5772) + 0.25 * log_L - 0.50 * log_R = 3.7613 + 0.25 * log_L - 0.50 * log_R
    log_Teff = 3.7613 + 0.25 * log_L - 0.50 * log_R

    # Central Temperature log10(Tc / K) at ZAMS
    if mass < 0.5:
        log_Tc = 6.91 + 0.42 * math.log10(mass / 0.3) - 0.015 * zeta
    elif mass < 1.3:
        log_Tc = 7.130 + 0.48 * math.log10(mass) - 0.020 * zeta
    else:
        log_Tc13 = 7.130 + 0.48 * math.log10(1.3)
        log_Tc = log_Tc13 + 0.22 * math.log10(mass / 1.3) - 0.028 * zeta

    # Central Density log10(rhoc / g cm^-3) at ZAMS
    if mass < 0.5:
        log_Rhoc = 1.96 - 0.35 * math.log10(mass / 0.3) - 0.04 * zeta
    elif mass < 1.3:
        log_Rhoc = 1.92 - 0.65 * math.log10(mass) - 0.05 * zeta
    else:
        log_Rhoc13 = 1.92 - 0.65 * math.log10(1.3)
        log_Rhoc = log_Rhoc13 - 1.12 * math.log10(mass / 1.3) - 0.05 * zeta

    # Effective core fuel fraction f_core & Main Sequence Lifetime (years)
    # M <= 0.4 M_sun is fully convective -> f_core ~ 0.85 -> t_MS ~ 680-780 Gyr
    if mass <= 0.4:
        f_core = 0.85
        mean_L_factor = 2.75  # Homogeneous He enrichment raises L over MS
    elif mass < 1.25:
        f_core = 0.105
        mean_L_factor = 1.42  # Mean MS L is ~1.42 * L_ZAMS -> t_MS(1 M_sun) = 10.0 Gyr
    elif mass < 10.0:
        f_core = min(0.24, 0.118 * (mass ** 0.22))
        mean_L_factor = 1.55
    else:
        # Massive stars with convective core + overshooting
        f_core = min(0.30, 0.125 * (mass ** 0.25))
        mean_L_factor = 1.72

    L_mean = (10.0 ** log_L) * mean_L_factor
    t_ms = 1.0e10 * (f_core / 0.105) * (mass / L_mean)

    return {
        "log_L": log_L,
        "log_R": log_R,
        "log_Teff": log_Teff,
        "log_Tc": log_Tc,
        "log_Rhoc": log_Rhoc,
        "t_ms": t_ms,
        "f_core": f_core,
        "zeta": zeta,
    }
