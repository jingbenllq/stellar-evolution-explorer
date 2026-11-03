#!/usr/bin/env python3
"""
Stellar Evolution Parameter Space Physics Engine & MESA LOGS Reader/Writer
==========================================================================
1. Builds full MESA-format `LOGS/history.data` and `LOGS/profile*.data` files
   across the (M_init, Z_init) parameter space using analytical & semi-empirical
   stellar evolution physics (Tout et al. 1996; Hurley, Pols & Tout 2000;
   Kippenhahn, Weigert & Weiss 2012).
2. Includes a standard `MESALogsReader` capable of parsing real MESA ASCII output
   files (`history.data`, `profiles.index`, `profile*.data`) seamlessly.
3. Exports `parameter_space_summary.csv` and `stellar_grid_data.json` for
   publication-grade static visualizations and the interactive Web Explorer.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import numpy as np

from mesa_configs.run_mesa_grid import build_grid_directories, compute_helium_abundance

# Full Parameter Space Grid (7 Masses x 4 Metallicities = 28 models)
MASS_GRID = [0.3, 1.0, 3.0, 5.0, 8.0, 15.0, 25.0]
METALLICITY_GRID = [0.0001, 0.001, 0.014, 0.03]

STAGE_NAMES = [
    ("ZAMS", "零龄主序 (ZAMS)"),
    ("TAMS", "主序拐点 (TAMS)"),
    ("RGB_HeIgn", "红巨星顶 / 氦点燃 (RGB Tip / He Ignition)"),
    ("HB_CoreHe", "中心氦燃烧 / 水平支或蓝环 (Core He Burn)"),
    ("AGB_AdvBurn", "渐近巨星支 / 晚期碳氧硅燃烧 (AGB / C-O-Si Burn)"),
    ("EndState", "演化终点：白矮星冷却 / 铁核坍缩前夕 (Final State)"),
]


def stage_names_for(mass: float) -> list[tuple[str, str]]:
    """Return stage codes and labels tailored to the stellar mass regime."""
    if mass >= 12.0:
        s3 = ("HG_HeIgn", "赫氏间隙 / 核心氦点燃")
        s5 = ("AdvBurn_COSi", "晚期碳氧硅燃烧")
    elif mass >= 8.0:
        s3 = ("HG_HeIgn", "赫氏间隙 / 核心氦点燃")
        s5 = ("SuperAGB_CO", "晚期碳/氧燃烧（Super-AGB）")
    elif mass >= 0.5:
        s3 = ("RGB_HeIgn", "红巨星顶 / 氦点燃")
        s5 = ("AGB", "AGB")
    else:
        s3 = ("Subgiant_HeCore", "亚巨星收缩 / 简并氦核")
        s5 = ("HeCore_HShell", "氦核收缩 / 氢壳层")

    return [
        ("ZAMS", "零龄主序 (ZAMS)"),
        ("TAMS", "主序拐点 (TAMS)"),
        s3,
        ("HB_CoreHe", "中心氦燃烧 / 水平支或蓝环 (Core He Burn)"),
        s5,
        ("EndState", "演化终点：白矮星冷却 / 铁核坍缩前夕 (Final State)"),
    ]


def zams_properties(mass: float, z: float) -> dict[str, float]:
    """
    Compute ZAMS luminosity (L/L_sun), radius (R/R_sun), Teff (K), central T_c (K),
    central density rho_c (g/cm^3), and main-sequence lifetime t_MS (yr)
    incorporating metallicity scaling (Tout et al. 1996 / Kippenhahn & Weigert).
    """
    zeta = math.log10(z / 0.014)  # log10(Z / Z_sun)

    # Piecewise physical Mass-Luminosity scaling on ZAMS + metallicity shift
    # Lower Z -> lower opacity -> higher L and higher Teff
    z_lum_shift = -0.11 * zeta if mass < 10.0 else -0.04 * zeta
    if mass < 0.43:
        log_L = math.log10(0.23 * (mass ** 2.3)) + z_lum_shift
    elif mass < 2.0:
        log_L = 4.0 * math.log10(mass) + z_lum_shift
    elif mass < 20.0:
        log_L = math.log10(1.4 * (mass ** 3.5)) + z_lum_shift
    else:
        log_L = math.log10(1.4 * (mass ** 3.5)) + z_lum_shift

    # ZAMS Radius scaling with metallicity dependence
    z_rad_shift = 0.05 * zeta
    if mass < 1.0:
        log_R = 0.85 * math.log10(mass) + z_rad_shift
    elif mass < 1.5:
        log_R = 0.92 * math.log10(mass) + z_rad_shift
    else:
        log_R = 0.57 * math.log10(mass) + z_rad_shift

    # Stefan-Boltzmann law: L / L_sun = (R / R_sun)^2 * (Teff / 5772)^4
    log_Teff = 3.7613 + 0.25 * log_L - 0.5 * log_R

    # Central temperature T_c ~ M / R (virial theorem with mean molecular weight mu)
    if mass < 1.2:
        # p-p chain dominated
        log_Tc = 7.18 + 0.55 * math.log10(mass) - 0.02 * zeta
    else:
        # CNO cycle dominated (steeper T sensitivity -> weak Tc variation)
        log_Tc = 7.28 + 0.22 * math.log10(mass) - 0.03 * zeta

    # Central density rho_c ~ M / R^3 (with polytropic concentration factor)
    if mass < 1.0:
        log_Rhoc = 1.90 - 0.50 * math.log10(mass) - 0.06 * zeta
    else:
        log_Rhoc = 1.90 - 1.15 * math.log10(mass) - 0.06 * zeta

    # Main sequence lifetime t_MS (years): proportional to f_core * M / L
    f_core = 0.10 if mass < 1.2 else min(0.32, 0.14 * (mass ** 0.25))
    t_ms = 1.0e10 * (f_core / 0.10) * (mass / (10.0 ** log_L))

    return {
        "log_L": log_L,
        "log_R": log_R,
        "log_Teff": log_Teff,
        "log_Tc": log_Tc,
        "log_Rhoc": log_Rhoc,
        "t_ms": t_ms,
    }


def determine_remnant_and_pathway(mass: float, z: float) -> dict[str, str | float]:
    """Classify evolutionary pathway, core burning stages, and final remnant."""
    zeta = math.log10(z / 0.014)
    if mass < 0.5:
        return {
            "regime": "极低质量恒星 (Fully Convective Low-Mass)",
            "ms_core": "全星对流 + p-p 链氢聚变",
            "he_ignition": "不点燃氦 (质量不足，中心简并冷却)",
            "advanced_burning": "无",
            "remnant_type": "氦白矮星 (He WD)",
            "remnant_mass": round(0.26 * (mass / 0.3), 3),
        }
    elif mass < 2.2:
        return {
            "regime": "低质量类太阳恒星 (Low-Mass Solar-Type)",
            "ms_core": "辐射核 + 对流包层 (p-p 链主导)",
            "he_ignition": "简并氦核 -> 红巨星支顶氦闪 (Helium Flash)",
            "advanced_burning": "止步于简并碳氧核 (AGB 热脉冲 + 行星状星云抛射)",
            "remnant_type": "碳氧白矮星 (CO WD)",
            "remnant_mass": round(0.53 + 0.08 * (mass - 1.0) - 0.015 * zeta, 3),
        }
    elif mass < 7.0:
        return {
            "regime": "中等质量恒星 (Intermediate-Mass)",
            "ms_core": "对流核 + 辐射包层 (CNO 循环主导)",
            "he_ignition": "非简并平稳点燃氦 -> 赫罗图蓝环 (Blue Loop)",
            "advanced_burning": "止步于简并碳氧核 (强 AGB 星风抛射)",
            "remnant_type": "碳氧白矮星 (CO WD)",
            "remnant_mass": round(0.68 + 0.07 * (mass - 3.0) - 0.02 * zeta, 3),
        }
    elif mass < 10.0:
        return {
            "regime": "大质量过渡区恒星 (Super-AGB / Critical Mass)",
            "ms_core": "对流核 + 辐射包层 (CNO 循环主导)",
            "he_ignition": "非简并氦燃烧 (蓝环)",
            "advanced_burning": "偏心碳点燃 (Off-center C burning) -> 氧氖镁核",
            "remnant_type": "氧氖镁白矮星 (ONe WD) / 电子俘获超新星",
            "remnant_mass": round(1.18 - 0.03 * zeta, 3),
        }
    elif mass < 20.0:
        return {
            "regime": "大质量恒星 (Massive Star - Red Supergiant Progenitor)",
            "ms_core": "大对流核 + 辐射包层 (强 CNO 循环)",
            "he_ignition": "非简并核心氦燃烧 (红/蓝超巨星)",
            "advanced_burning": "全套核聚变 H->He->C->Ne->O->Si->Fe (洋葱皮结构)",
            "remnant_type": "铁核坍缩超新星 (IIP型 CCSN) -> 中子星 (NS)",
            "remnant_mass": round(1.45 + 0.03 * (mass - 15.0) - 0.04 * zeta, 3),
        }
    else:
        return {
            "regime": "超大质量恒星 (Very Massive Star)",
            "ms_core": "极大对流核 + 辐射包层 + 强辐射压星风",
            "he_ignition": "核心快速氦燃烧 (超巨星)",
            "advanced_burning": "全套核聚变 H->He->C->Ne->O->Si->Fe (大质量铁核)",
            "remnant_type": "核坍缩超新星 / 坍缩星 -> 中子星或恒星级黑洞 (BH)",
            "remnant_mass": round(2.10 + 0.15 * (mass - 20.0) - 0.15 * zeta, 3),
        }


def simulate_model_track(mass: float, z: float, n_steps: int = 240) -> dict:
    """
    Generate a continuous evolutionary track (n_steps) and 6 detailed radial
    profiles across key evolutionary phases for a star of initial (mass, z).
    """
    zams = zams_properties(mass, z)
    zeta = math.log10(z / 0.014)
    y_init = compute_helium_abundance(z)
    x_init = round(1.0 - y_init - z, 5)
    pathway = determine_remnant_and_pathway(mass, z)

    log_L0 = zams["log_L"]
    log_Teff0 = zams["log_Teff"]
    log_Tc0 = zams["log_Tc"]
    log_Rhoc0 = zams["log_Rhoc"]
    t_ms = zams["t_ms"]

    # Define normalized evolutionary coordinate s in [0, 5] mapping the 6 anchor stages:
    # s=0: ZAMS
    # s=1: TAMS
    # s=2: RGB Tip / He Ignition
    # s=3: Core He Burning (HB / Blue Loop / RSG)
    # s=4: AGB Tip / C-O-Si Burning
    # s=5: Final State (WD Cooling Track or Pre-SN Fe Core Collapse)

    # Anchor points in (log_Teff, log_L, log_Tc, log_Rhoc, age_yr, star_mass, center_degeneracy)
    if mass < 0.5:
        # 0.3 M_sun: Fully convective, evolves slowly blueward/upward then cools as He WD
        anchors = [
            # s=0 ZAMS
            (log_Teff0, log_L0, log_Tc0, log_Rhoc0, 0.0, mass, -1.2),
            # s=1 TAMS
            (log_Teff0 + 0.05, log_L0 + 0.35, log_Tc0 + 0.12, log_Rhoc0 + 0.85, t_ms, mass * 0.99, 1.5),
            # s=2 Subgiant / He-core contraction
            (log_Teff0 + 0.02, log_L0 + 0.85, log_Tc0 + 0.25, log_Rhoc0 + 1.80, t_ms * 1.06, mass * 0.96, 5.2),
            # s=3 Pre-WD turnoff
            (log_Teff0 + 0.35, log_L0 + 0.60, log_Tc0 + 0.28, log_Rhoc0 + 2.65, t_ms * 1.08, pathway["remnant_mass"], 12.0),
            # s=4 Early He WD cooling
            (4.15 - 0.02 * zeta, -0.60, 7.15, 5.15, t_ms * 1.10, pathway["remnant_mass"], 22.0),
            # s=5 Cool He WD
            (3.85 - 0.02 * zeta, -2.40, 6.60, 5.25, t_ms * 1.15, pathway["remnant_mass"], 45.0),
        ]
    elif mass < 2.2:
        # 1.0 M_sun: MS -> Subgiant -> RGB Tip (He Flash!) -> HB Clump -> AGB -> Planetary Nebula -> CO WD
        log_Teff_rgb = 3.52 - 0.04 * zeta
        log_L_rgb = 3.35 - 0.08 * zeta
        log_Teff_hb = 3.69 - 0.06 * zeta
        log_L_hb = 1.72 - 0.04 * zeta
        log_Teff_agb = 3.49 - 0.04 * zeta
        log_L_agb = 3.68 - 0.05 * zeta
        anchors = [
            # s=0 ZAMS
            (log_Teff0, log_L0, log_Tc0, log_Rhoc0, 0.0, mass, -1.5),
            # s=1 TAMS
            (log_Teff0 - 0.03, log_L0 + 0.32, log_Tc0 + 0.14, log_Rhoc0 + 0.95, t_ms, mass * 0.995, 0.2),
            # s=2 RGB Tip (Helium Flash at log_Tc ~ 7.95, log_Rhoc ~ 5.8)
            (log_Teff_rgb, log_L_rgb, 7.96, 5.75, t_ms * 1.12, mass * 0.85, 18.5),
            # s=3 Horizontal Branch / Red Clump (Non-degenerate Core He burning after flash)
            (log_Teff_hb, log_L_hb, 8.08, 4.15, t_ms * 1.132, mass * 0.82, 1.8),
            # s=4 AGB Tip (Degenerate CO core + He/H shell thermal pulses)
            (log_Teff_agb, log_L_agb, 8.28, 6.15, t_ms * 1.135, mass * 0.65, 24.0),
            # s=5 CO White Dwarf Cooling Track
            (4.35, -1.50, 7.25, 6.38, t_ms * 1.15, pathway["remnant_mass"], 48.0),
        ]
    elif mass < 10.0:
        # 3.0, 5.0, 8.0 M_sun: Convective MS -> HG -> RGB -> Blue Loop (Core He) -> AGB -> WD
        is_super_agb = mass >= 7.0
        log_Teff_rgb = 3.58 - 0.03 * zeta + 0.01 * math.log10(mass)
        log_L_rgb = log_L0 + 0.45
        log_Teff_loop = log_Teff0 - 0.14 - 0.08 * zeta  # Blue loop excursion
        log_L_loop = log_L0 + 0.55
        log_Teff_agb = 3.51 - 0.04 * zeta
        log_L_agb = min(4.65, log_L0 + 1.15)
        tc_agb = 8.82 if is_super_agb else 8.42
        rhoc_agb = 6.55 if is_super_agb else 6.25
        anchors = [
            # s=0 ZAMS
            (log_Teff0, log_L0, log_Tc0, log_Rhoc0, 0.0, mass, -2.5),
            # s=1 TAMS
            (log_Teff0 - 0.07, log_L0 + 0.28, log_Tc0 + 0.12, log_Rhoc0 + 0.55, t_ms, mass * 0.995, -1.8),
            # s=2 Base of RGB / Smooth He Ignition
            (log_Teff_rgb, log_L_rgb, 8.06, 4.25 - 0.4 * math.log10(mass / 3.0), t_ms * 1.02, mass * 0.98, -0.2),
            # s=3 Core He Burning (Blue Loop)
            (log_Teff_loop, log_L_loop, 8.18, 3.85 - 0.35 * math.log10(mass / 3.0), t_ms * 1.18, mass * 0.95, -0.5),
            # s=4 TP-AGB / Super-AGB (Off-center C ignition for 8 M_sun)
            (log_Teff_agb, log_L_agb, tc_agb, rhoc_agb, t_ms * 1.20, mass * 0.72, 16.5),
            # s=5 High-mass CO / ONe White Dwarf
            (4.48, -1.10, 7.38, 6.85 if is_super_agb else 6.55, t_ms * 1.22, pathway["remnant_mass"], 52.0),
        ]
    else:
        # 15.0, 25.0 M_sun: Massive Star -> MS -> BSG/RSG He Burning -> C -> Ne/O -> Si -> Fe Core Collapse
        # Higher Z -> stronger line-driven stellar wind mass loss
        wind_factor = (z / 0.014) ** 0.5
        dm_ms = 0.04 * (mass / 15.0) ** 1.6 * wind_factor
        dm_he = 0.22 * (mass / 15.0) ** 1.5 * wind_factor
        m_tams = max(mass * 0.75, mass - dm_ms * mass)
        m_end = max(pathway["remnant_mass"] * 2.5, mass - (dm_ms + dm_he) * mass)

        log_Teff_he_ign = 3.85 - 0.08 * zeta
        log_Teff_rsg = 3.57 - 0.03 * zeta
        anchors = [
            # s=0 ZAMS
            (log_Teff0, log_L0, log_Tc0, log_Rhoc0, 0.0, mass, -3.5),
            # s=1 TAMS
            (log_Teff0 - 0.12, log_L0 + 0.26, log_Tc0 + 0.14, log_Rhoc0 + 0.50, t_ms, m_tams, -2.8),
            # s=2 Core He Ignition (crossing Hertzsprung gap)
            (log_Teff_he_ign, log_L0 + 0.34, 8.22, 3.15 - 0.2 * math.log10(mass / 15.0), t_ms * 1.008, m_tams * 0.97, -1.9),
            # s=3 Core He Burning (Red/Yellow Supergiant)
            (log_Teff_rsg + 0.04, log_L0 + 0.38, 8.32, 3.35 - 0.2 * math.log10(mass / 15.0), t_ms * 1.09, (m_tams + m_end) * 0.5, -1.5),
            # s=4 Core Carbon & Oxygen Burning (RSG)
            (log_Teff_rsg, log_L0 + 0.44, 8.95, 5.65, t_ms * 1.100, m_end * 1.01, 0.8),
            # s=5 Core Silicon Burning -> Pre-CCSN Fe Core Infall (T_c ~ 3.5e9 K, rho_c ~ 3e9 g/cm^3)
            (log_Teff_rsg - 0.01, log_L0 + 0.46, 9.55, 9.45, t_ms * 1.1001, m_end, 4.2),
        ]

    # Interpolate evolutionary track across s in [0, 5]
    s_grid = np.linspace(0.0, 5.0, n_steps)
    s_nodes = np.arange(6, dtype=float)

    a_arr = np.array(anchors)
    log_Teff_arr = np.interp(s_grid, s_nodes, a_arr[:, 0])
    log_L_arr = np.interp(s_grid, s_nodes, a_arr[:, 1])
    log_Tc_arr = np.interp(s_grid, s_nodes, a_arr[:, 2])
    log_Rhoc_arr = np.interp(s_grid, s_nodes, a_arr[:, 3])
    age_arr = np.interp(s_grid, s_nodes, a_arr[:, 4])
    mass_arr = np.interp(s_grid, s_nodes, a_arr[:, 5])
    eta_arr = np.interp(s_grid, s_nodes, a_arr[:, 6])

    # Add realistic HR morphology nuances (e.g., Planetary Nebula horizontal crossing for 1-8 M_sun)
    if 0.5 <= mass < 10.0:
        for idx, s_val in enumerate(s_grid):
            if 4.0 < s_val < 5.0:
                u = s_val - 4.0  # u in (0, 1): 0->0.45 is constant-L PN central star heating, 0.45->1.0 is WD cooling
                if u < 0.45:
                    frac = u / 0.45
                    log_L_arr[idx] = a_arr[4, 1] - 0.15 * frac
                    log_Teff_arr[idx] = a_arr[4, 0] + (5.05 - a_arr[4, 0]) * frac
                else:
                    frac = (u - 0.45) / 0.55
                    log_L_arr[idx] = (a_arr[4, 1] - 0.15) * (1.0 - frac) + a_arr[5, 1] * frac
                    log_Teff_arr[idx] = 5.05 * (1.0 - frac) + a_arr[5, 0] * frac

    # Stefan-Boltzmann radius: log_R = 0.5 * log_L - 2.0 * (log_Teff - 3.7613)
    log_R_arr = 0.5 * log_L_arr - 2.0 * (log_Teff_arr - 3.7613)

    # Central chemical abundances & core masses along s_grid
    c_h1 = np.zeros(n_steps)
    c_he4 = np.zeros(n_steps)
    c_c12 = np.zeros(n_steps)
    c_o16 = np.zeros(n_steps)
    c_ne20 = np.zeros(n_steps)
    c_si28 = np.zeros(n_steps)
    c_fe56 = np.zeros(n_steps)
    he_core_m = np.zeros(n_steps)
    co_core_m = np.zeros(n_steps)
    fe_core_m = np.zeros(n_steps)
    log_LH = np.zeros(n_steps)
    log_LHe = np.zeros(n_steps)
    log_LZ = np.zeros(n_steps)

    # Kippenhahn convective & burning boundaries (in mass coordinate m / M_sun)
    conv_core_top = np.zeros(n_steps)
    conv_env_bot = np.zeros(n_steps)

    for i, s_val in enumerate(s_grid):
        m_curr = mass_arr[i]
        # Central abundances
        if s_val <= 1.0:
            # Main Sequence: H burns into He
            u = s_val
            c_h1[i] = max(0.0, x_init * (1.0 - u))
            c_he4[i] = y_init + x_init * u
            c_c12[i] = z * 0.18
            c_o16[i] = z * 0.45
        elif s_val <= 3.0:
            # Post-MS inert He core contraction / RGB / He ignition
            c_h1[i] = 0.0
            c_he4[i] = 1.0 - z
            c_c12[i] = z * 0.18
            c_o16[i] = z * 0.45
        elif s_val <= 3.5:
            # Core He burning (if mass >= 0.5)
            if mass < 0.5:
                c_he4[i] = 1.0 - z
                c_c12[i] = z * 0.18
                c_o16[i] = z * 0.45
            else:
                u = (s_val - 3.0) / 0.5
                c_he4[i] = max(0.0, (1.0 - z) * (1.0 - u))
                c_c12[i] = 0.32 * u
                c_o16[i] = 0.68 * (1.0 - z) * u
        else:
            # Advanced stages (s > 3.5)
            if mass < 0.5:
                c_he4[i] = 1.0 - z
            elif mass < 7.0:
                c_c12[i] = 0.32
                c_o16[i] = 0.66
                c_ne20[i] = 0.02
            elif mass < 10.0:
                # 8 M_sun converts C into O/Ne/Mg
                u = min(1.0, (s_val - 3.5) / 1.0)
                c_c12[i] = 0.32 * (1.0 - u)
                c_o16[i] = 0.58
                c_ne20[i] = 0.10 + 0.30 * u
            else:
                # Massive star: C -> Ne/O -> Si -> Fe
                if s_val <= 4.2:
                    u = (s_val - 3.5) / 0.7
                    c_c12[i] = max(0.0, 0.32 * (1.0 - u))
                    c_o16[i] = 0.65
                    c_ne20[i] = 0.30 * u
                elif s_val <= 4.7:
                    u = (s_val - 4.2) / 0.5
                    c_o16[i] = max(0.0, 0.65 * (1.0 - u))
                    c_ne20[i] = max(0.0, 0.30 * (1.0 - u))
                    c_si28[i] = 0.85 * u
                else:
                    u = (s_val - 4.7) / 0.3
                    c_si28[i] = max(0.0, 0.85 * (1.0 - u))
                    c_fe56[i] = 0.92 * u

        # Core masses
        he_frac_max = 0.88 if mass < 0.5 else (0.53 / mass if mass < 2.2 else 0.28)
        if s_val > 0.8:
            he_core_m[i] = min(m_curr, mass * he_frac_max * min(1.0, (s_val - 0.8) / 1.5))
        if s_val > 2.5 and mass >= 0.5:
            co_core_m[i] = min(he_core_m[i] * 0.88, he_core_m[i] * min(1.0, (s_val - 2.5) / 1.3))
        if s_val > 4.6 and mass >= 10.0:
            fe_core_m[i] = min(co_core_m[i] * 0.45, pathway["remnant_mass"] * min(1.0, (s_val - 4.6) / 0.4))

        # Nuclear luminosities
        log_LH[i] = log_L_arr[i] if s_val < 4.3 else -3.0
        log_LHe[i] = (log_L_arr[i] - 0.3) if (2.0 <= s_val <= 4.5 and mass >= 0.5) else -5.0
        log_LZ[i] = (log_L_arr[i] + 0.8 * (s_val - 3.8)) if (s_val >= 3.8 and mass >= 7.5) else -8.0

        # Convection zones for Kippenhahn diagram
        if mass < 0.5:
            conv_core_top[i] = m_curr if s_val < 3.0 else 0.0
            conv_env_bot[i] = 0.0 if s_val < 3.0 else m_curr
        elif mass < 1.3:
            # Radiative core on MS, deep convective envelope on RGB/AGB, convective He core on HB
            conv_core_top[i] = 0.15 * mass if (2.05 <= s_val <= 3.3) else 0.0
            if s_val <= 1.2:
                conv_env_bot[i] = 0.975 * m_curr
            elif s_val <= 2.0:
                # First Dredge-Up on RGB
                u = (s_val - 1.2) / 0.8
                conv_env_bot[i] = m_curr * (0.975 - 0.68 * u)
            elif s_val <= 3.4:
                conv_env_bot[i] = m_curr * 0.75
            elif s_val <= 4.1:
                conv_env_bot[i] = max(co_core_m[i] * 1.05, m_curr * 0.55)
            else:
                conv_env_bot[i] = m_curr
        else:
            # Massive / Intermediate star: receding convective core on MS, convective He core, deep RSG/AGB envelope
            if s_val <= 1.0:
                f_cc0 = min(0.55, 0.18 * (mass ** 0.3))
                conv_core_top[i] = mass * f_cc0 * (1.0 - 0.35 * s_val)
                conv_env_bot[i] = m_curr * 0.998
            elif s_val <= 2.0:
                conv_core_top[i] = 0.0
                conv_env_bot[i] = m_curr * (0.998 - 0.45 * (s_val - 1.0))
            elif s_val <= 3.5:
                conv_core_top[i] = he_core_m[i] * 0.65
                conv_env_bot[i] = m_curr * 0.45 if log_Teff_arr[i] < 3.68 else m_curr * 0.98
            else:
                conv_core_top[i] = co_core_m[i] * 0.35 if mass >= 10.0 else 0.0
                conv_env_bot[i] = max(he_core_m[i] * 1.05, m_curr * 0.38) if s_val < 4.5 else m_curr

    # Build radial profiles at the 6 key stages (s = 0, 1, 2, 3, 4, 5)
    stage_indices = [int(round(k * (n_steps - 1) / 5.0)) for k in range(6)]
    profiles = []
    q_grid = np.linspace(0.005, 1.0, 80)  # 80 radial zones from center to surface

    for stage_idx, (stage_code, stage_label) in enumerate(stage_names_for(mass)):
        idx = stage_indices[stage_idx]
        m_star = float(mass_arr[idx])
        r_star_log = float(log_R_arr[idx])
        tc_log = float(log_Tc_arr[idx])
        tsurf_log = float(log_Teff_arr[idx])
        rhoc_log = float(log_Rhoc_arr[idx])

        m_zones = q_grid * m_star
        logT_prof = tc_log - (tc_log - tsurf_log) * (q_grid ** 0.65)
        logRho_prof = rhoc_log - (rhoc_log + 6.5) * (q_grid ** 0.55)
        logR_prof = r_star_log + np.log10(q_grid ** 0.45)

        h1_p = np.zeros_like(q_grid)
        he4_p = np.zeros_like(q_grid)
        c12_p = np.zeros_like(q_grid)
        o16_p = np.zeros_like(q_grid)
        ne20_p = np.zeros_like(q_grid)
        si28_p = np.zeros_like(q_grid)
        fe56_p = np.zeros_like(q_grid)
        eps_nuc_p = np.zeros_like(q_grid)
        mixing_p = np.zeros_like(q_grid, dtype=int)

        for j, q in enumerate(q_grid):
            m_q = q * m_star
            if m_q <= conv_core_top[idx] or m_q >= conv_env_bot[idx]:
                mixing_p[j] = 1  # Convective

            if stage_idx == 0:  # ZAMS: homogeneous
                h1_p[j] = x_init
                he4_p[j] = y_init
                c12_p[j] = z * 0.18
                o16_p[j] = z * 0.45
                eps_nuc_p[j] = (10.0 ** log_L_arr[idx]) * math.exp(-((q / 0.15) ** 2))
            elif stage_idx == 1:  # TAMS: He-enriched core
                core_q = 0.15 if mass < 1.2 else min(0.38, 0.18 * (mass ** 0.25))
                w = 0.5 * (1.0 + math.tanh((q - core_q) / 0.04))
                h1_p[j] = x_init * w
                he4_p[j] = (1.0 - z) * (1.0 - w) + y_init * w
                c12_p[j] = z * 0.18
                o16_p[j] = z * 0.45
                eps_nuc_p[j] = (10.0 ** log_L_arr[idx]) * math.exp(-(((q - core_q) / 0.05) ** 2))
            elif stage_idx in (2, 3):  # RGB / Core He Burning
                q_he = max(0.18, he_core_m[idx] / m_star)
                q_co = 0.0
                if q < q_co:
                    c12_p[j] = 0.32
                    o16_p[j] = 0.66
                    he4_p[j] = 0.02
                elif q < q_he:
                    he4_p[j] = 0.98 - z
                    c12_p[j] = z * 0.3
                    o16_p[j] = z * 0.5
                else:
                    h1_p[j] = x_init
                    he4_p[j] = y_init
                    c12_p[j] = z * 0.18
                    o16_p[j] = z * 0.45
                eps_nuc_p[j] = (10.0 ** log_L_arr[idx]) * (
                    math.exp(-(((q - q_he) / 0.03) ** 2)) + (0.4 * math.exp(-((q / 0.10) ** 2)) if stage_idx == 3 else 0.0)
                )
            else:  # stage_idx 4 or 5: Advanced Burning / Final Onion-Skin or White Dwarf
                if mass < 0.5:
                    if stage_idx == 5:
                        he4_p[j] = 0.99 - z if q < 0.96 else x_init
                        h1_p[j] = 1.0 - he4_p[j] - z
                    else:
                        he4_p[j] = 0.98 - z if q < 0.85 else y_init
                        h1_p[j] = 1.0 - he4_p[j] - z
                elif mass < 10.0:
                    # CO or ONe White Dwarf / AGB core-envelope structure
                    q_co = 0.95 if stage_idx == 5 else max(0.25, co_core_m[idx] / m_star)
                    q_he = 0.99 if stage_idx == 5 else min(0.95, q_co + 0.06)
                    if q < q_co:
                        if mass >= 7.0:
                            o16_p[j] = 0.58
                            ne20_p[j] = 0.35
                            c12_p[j] = 0.05
                        else:
                            c12_p[j] = 0.35
                            o16_p[j] = 0.63
                            ne20_p[j] = 0.02
                    elif q < q_he:
                        he4_p[j] = 0.96
                        c12_p[j] = 0.03
                    else:
                        h1_p[j] = x_init
                        he4_p[j] = y_init
                        c12_p[j] = z * 0.2
                        o16_p[j] = z * 0.5
                else:
                    # Massive Star Onion-Skin Structure: Fe -> Si -> O/Ne -> C/O -> He -> H
                    if stage_idx == 4:
                        # Carbon/Oxygen burning stage
                        if q < 0.12:
                            o16_p[j] = 0.62
                            ne20_p[j] = 0.32
                            c12_p[j] = 0.06
                        elif q < 0.26:
                            c12_p[j] = 0.32
                            o16_p[j] = 0.66
                        elif q < 0.42:
                            he4_p[j] = 0.98 - z
                        else:
                            h1_p[j] = x_init
                            he4_p[j] = y_init
                    else:
                        # Stage 5: Classic Pre-Supernova Onion-Skin Profile
                        if q < 0.11:
                            fe56_p[j] = 0.92
                            si28_p[j] = 0.08
                        elif q < 0.18:
                            si28_p[j] = 0.78
                            o16_p[j] = 0.16
                            fe56_p[j] = 0.06
                        elif q < 0.30:
                            o16_p[j] = 0.68
                            ne20_p[j] = 0.24
                            c12_p[j] = 0.08
                        elif q < 0.38:
                            c12_p[j] = 0.34
                            o16_p[j] = 0.60
                            he4_p[j] = 0.06
                        elif q < 0.52:
                            he4_p[j] = 0.96 - z
                            c12_p[j] = 0.02
                        else:
                            h1_p[j] = x_init
                            he4_p[j] = y_init
                            c12_p[j] = z * 0.18
                            o16_p[j] = z * 0.45

        profiles.append({
            "stage_index": stage_idx + 1,
            "stage_code": stage_code,
            "stage_label": stage_label,
            "model_number": int((idx + 1) * 10),
            "star_age": float(age_arr[idx]),
            "star_mass": m_star,
            "log_L": float(log_L_arr[idx]),
            "log_Teff": float(log_Teff_arr[idx]),
            "log_R": r_star_log,
            "log_center_T": tc_log,
            "log_center_Rho": rhoc_log,
            "q": [round(float(x), 4) for x in q_grid],
            "mass": [round(float(x), 4) for x in m_zones],
            "logR": [round(float(x), 4) for x in logR_prof],
            "logT": [round(float(x), 4) for x in logT_prof],
            "logRho": [round(float(x), 4) for x in logRho_prof],
            "mixing_type": [int(x) for x in mixing_p],
            "eps_nuc": [round(float(x), 3) for x in eps_nuc_p],
            "h1": [round(float(x), 4) for x in h1_p],
            "he4": [round(float(x), 4) for x in he4_p],
            "c12": [round(float(x), 4) for x in c12_p],
            "o16": [round(float(x), 4) for x in o16_p],
            "ne20": [round(float(x), 4) for x in ne20_p],
            "si28": [round(float(x), 4) for x in si28_p],
            "fe56": [round(float(x), 4) for x in fe56_p],
        })

    return {
        "model_id": f"M{mass:04.1f}_Z{z:.4f}",
        "initial_mass": mass,
        "initial_z": z,
        "initial_y": y_init,
        "initial_x": x_init,
        "pathway": pathway,
        "zams_summary": zams,
        "stage_indices": stage_indices,
        "history": {
            "model_number": [int((i + 1) * 10) for i in range(n_steps)],
            "star_age": [float(x) for x in age_arr],
            "star_mass": [round(float(x), 4) for x in mass_arr],
            "log_L": [round(float(x), 4) for x in log_L_arr],
            "log_Teff": [round(float(x), 4) for x in log_Teff_arr],
            "log_R": [round(float(x), 4) for x in log_R_arr],
            "log_center_T": [round(float(x), 4) for x in log_Tc_arr],
            "log_center_Rho": [round(float(x), 4) for x in log_Rhoc_arr],
            "center_degeneracy": [round(float(x), 3) for x in eta_arr],
            "log_LH": [round(float(x), 3) for x in log_LH],
            "log_LHe": [round(float(x), 3) for x in log_LHe],
            "log_LZ": [round(float(x), 3) for x in log_LZ],
            "center_h1": [round(float(x), 4) for x in c_h1],
            "center_he4": [round(float(x), 4) for x in c_he4],
            "center_c12": [round(float(x), 4) for x in c_c12],
            "center_o16": [round(float(x), 4) for x in c_o16],
            "center_ne20": [round(float(x), 4) for x in c_ne20],
            "center_si28": [round(float(x), 4) for x in c_si28],
            "center_fe56": [round(float(x), 4) for x in c_fe56],
            "he_core_mass": [round(float(x), 4) for x in he_core_m],
            "co_core_mass": [round(float(x), 4) for x in co_core_m],
            "fe_core_mass": [round(float(x), 4) for x in fe_core_m],
            "conv_core_top": [round(float(x), 4) for x in conv_core_top],
            "conv_env_bot": [round(float(x), 4) for x in conv_env_bot],
        },
        "profiles": profiles,
    }


def write_mesa_ascii_logs(model_data: dict, logs_dir: Path) -> None:
    """
    Write standard MESA ASCII format `history.data`, `profiles.index`, and
    `profile1.data`..`profile6.data` so any standard MESA tool (`mesa_reader`,
    `py_mesa_reader`) can load them directly.
    """
    logs_dir.mkdir(parents=True, exist_ok=True)
    h = model_data["history"]
    cols = list(h.keys())
    n_rows = len(h["model_number"])

    # 1. Write history.data
    hist_lines = [
        "                  1                   2                   3",
        "        version_number            compiler               build",
        '       "synthetic-1.0"            "python" "stellar_grid_engine"',
        "",
        " ".join(f"{i+1:>20d}" for i in range(len(cols))),
        " ".join(f"{c:>20s}" for c in cols),
    ]
    for r in range(n_rows):
        row_str = " ".join(
            f"{h[c][r]:20d}" if isinstance(h[c][r], int) else f"{h[c][r]:20.6e}"
            for c in cols
        )
        hist_lines.append(row_str)
    (logs_dir / "history.data").write_text("\n".join(hist_lines) + "\n", encoding="utf-8")

    # 2. Write profiles.index and profileN.data
    idx_lines = [
        "index file for profiles",
        "          model_number              priority        profile_number",
    ]
    for p in model_data["profiles"]:
        p_num = p["stage_index"]
        idx_lines.append(f"{p['model_number']:22d}{1:22d}{p_num:22d}")
        p_cols = ["q", "mass", "logR", "logT", "logRho", "mixing_type", "eps_nuc",
                  "h1", "he4", "c12", "o16", "ne20", "si28", "fe56"]
        n_zones = len(p["q"])
        p_lines = [
            "                  1                   2                   3                   4",
            "       model_number            star_age           star_mass               log_L",
            f"{p['model_number']:20d}{p['star_age']:20.6e}{p['star_mass']:20.6e}{p['log_L']:20.6e}",
            "",
            " ".join(f"{i+1:>16d}" for i in range(len(p_cols))),
            " ".join(f"{c:>16s}" for c in p_cols),
        ]
        for z_idx in range(n_zones):
            # MESA profiles order zones from surface (zone 1) to center (zone N)
            rev_idx = n_zones - 1 - z_idx
            row_str = " ".join(
                f"{p[c][rev_idx]:16d}" if isinstance(p[c][rev_idx], int) else f"{p[c][rev_idx]:16.5e}"
                for c in p_cols
            )
            p_lines.append(row_str)
        (logs_dir / f"profile{p_num}.data").write_text("\n".join(p_lines) + "\n", encoding="utf-8")

    (logs_dir / "profiles.index").write_text("\n".join(idx_lines) + "\n", encoding="utf-8")


class MESALogsReader:
    """Standard reader for MESA `history.data` and `profile*.data` ASCII files."""

    @staticmethod
    def read_mesa_table(filepath: Path) -> dict[str, list[float]]:
        lines = [line.strip() for line in filepath.read_text(encoding="utf-8").splitlines() if line.strip()]
        # Standard MESA format: line index 4 (0-based) is column names after header block
        col_names = lines[4].split()
        data = {c: [] for c in col_names}
        for row_line in lines[5:]:
            parts = row_line.split()
            for c, val_str in zip(col_names, parts):
                data[c].append(float(val_str))
        return data


def main() -> None:
    workspace = Path(__file__).resolve().parent
    build_grid_directories(workspace, execute_mesa=False)

    all_models = []
    summary_rows = []

    for mass in MASS_GRID:
        for z in METALLICITY_GRID:
            model = simulate_model_track(mass, z, n_steps=200)
            all_models.append(model)

            # Write MESA ASCII LOGS into mesa_grid_runs/M*_Z*/LOGS for all 28 models
            run_dir = workspace / "mesa_grid_runs" / model["model_id"]
            run_dir.mkdir(parents=True, exist_ok=True)
            write_mesa_ascii_logs(model, run_dir / "LOGS")

            # Extract stage summary rows for CSV export
            for p in model["profiles"]:
                summary_rows.append({
                    "model_id": model["model_id"],
                    "initial_mass_Msun": mass,
                    "initial_Z": z,
                    "regime": model["pathway"]["regime"],
                    "remnant_type": model["pathway"]["remnant_type"],
                    "remnant_mass_Msun": model["pathway"]["remnant_mass"],
                    "stage_index": p["stage_index"],
                    "stage_code": p["stage_code"],
                    "stage_label": p["stage_label"],
                    "age_yr": round(p["star_age"], 2),
                    "current_mass_Msun": round(p["star_mass"], 4),
                    "log_L_Lsun": round(p["log_L"], 4),
                    "log_Teff_K": round(p["log_Teff"], 4),
                    "log_R_Rsun": round(p["log_R"], 4),
                    "log_Tc_K": round(p["log_center_T"], 4),
                    "log_Rhoc_gcm3": round(p["log_center_Rho"], 4),
                    "center_H1": p["h1"][0],
                    "center_He4": p["he4"][0],
                    "center_C12": p["c12"][0],
                    "center_O16": p["o16"][0],
                    "center_Fe56": p["fe56"][0],
                })

    # Verify MESA ASCII reader on one of the generated LOGS
    sample_hist = MESALogsReader.read_mesa_table(
        workspace / "mesa_grid_runs" / "M01.0_Z0.0140" / "LOGS" / "history.data"
    )
    print(f"[Verified MESA Reader] Loaded M01.0_Z0.0140/LOGS/history.data with {len(sample_hist['model_number'])} steps.")

    # Save parameter_space_summary.csv
    csv_path = workspace / "parameter_space_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    # Save full JSON dataset for figures & interactive explorer
    json_path = workspace / "stellar_grid_data.json"
    json_path.write_text(
        json.dumps(
            {
                "masses": MASS_GRID,
                "metallicities": METALLICITY_GRID,
                "stages": [{"code": c, "label": lbl} for c, lbl in STAGE_NAMES],
                "models": all_models,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"Exported {len(all_models)} parameter-space models ({len(summary_rows)} stage snapshots) to {csv_path.name} and {json_path.name}.")


if __name__ == "__main__":
    main()
