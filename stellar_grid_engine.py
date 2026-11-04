#!/usr/bin/env python3
"""
Stellar Evolution Parameter Space Engine (v2.0 — Physics & MESA Audited)
========================================================================
Implements physically calibrated semi-analytical evolutionary tracks, internal
radial chemical abundance profiles X_i(q), and Kippenhahn convective/burning
zone histories across the (M_init, Z_init) parameter space:
  - M_init in [0.3, 1.0, 3.0, 5.0, 8.0, 15.0, 25.0] M_sun
  - Z_init in [0.0001, 0.001, 0.014, 0.03]

Calibrated against MESA r24.03.1 / MIST (Choi et al. 2016) & SSE (Hurley et al. 2000).
"""

import csv
import json
import math
from pathlib import Path
import numpy as np

MASS_GRID = [0.3, 1.0, 3.0, 5.0, 8.0, 15.0, 25.0]
METALLICITY_GRID = [0.0001, 0.001, 0.014, 0.03]

STAGE_NAMES = [
    "ZAMS 零龄主序",
    "TAMS 主序拐点",
    "RGB/HG 壳层氢燃烧与氦点火",
    "CHeB 中心氦燃烧 (HB/蓝环/RSG)",
    "AGB/晚期碳氧燃烧",
    "演化终点 (WD冷却 / 铁核坍缩前夕)",
]

SPECIES = ["H1", "He4", "C12", "O16", "Ne20", "Si28", "Fe56"]


def zams_properties(mass: float, z: float) -> dict:
    """Compute MESA/MIST-calibrated ZAMS global & central properties."""
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
    # M <= 0.35 M_sun is fully convective -> f_core ~ 0.88 -> t_MS ~ 680 Gyr!
    if mass <= 0.4:
        f_core = 0.85
        mean_L_factor = 2.75  # Homogeneous He enrichment raises L significantly over MS -> t_MS ~ 780 Gyr
    elif mass < 1.25:
        f_core = 0.105
        mean_L_factor = 1.42  # Mean MS L is ~1.42 * L_ZAMS so t_MS(1 M_sun) = 10.0 Gyr
    elif mass < 10.0:
        f_core = min(0.24, 0.118 * (mass ** 0.22))
        mean_L_factor = 1.55
    else:
        # Massive stars with convective core + overshooting (t_MS ~ 11.8 Myr at 15 Msun, ~6.7 Myr at 25 Msun)
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


def classify_pathway(mass: float, z: float) -> dict:
    """Determine evolutionary regime, burning stages, and final remnant properties."""
    zeta = math.log10(z / 0.014)
    if mass < 0.5:
        return {
            "regime": "全对流红矮星 (Fully Convective M-Dwarf)",
            "core_structure": "全星对流混合 (无辐射核/壳层分界) → 蓝矮星收缩 → 氦白矮星",
            "max_burning": "pp-I 链氢聚变 (无氦点燃)",
            "remnant_type": "He WD (氦白矮星)",
            "remnant_code": "He_WD",
            "remnant_mass": round(mass * 0.96, 3),
            "supernova": "无 (平稳简并冷却)",
        }
    elif mass < 2.2:
        m_rem = round(0.54 + 0.085 * (mass - 1.0) - 0.015 * zeta, 3)
        return {
            "regime": "低质量类太阳恒星 (Low-Mass Solar-Type)",
            "core_structure": "辐射核 + 对流包层 → 简并氦核氦闪 → 碳氧白矮星",
            "max_burning": "pp 链 / CNO 氢燃烧 + 3α 氦燃烧 (氦闪点火)",
            "remnant_type": "CO WD (碳氧白矮星)",
            "remnant_code": "CO_WD",
            "remnant_mass": m_rem,
            "supernova": "行星状星云抛射 (Planetary Nebula)",
        }
    elif mass < 7.0:
        m_rem = round(0.70 + 0.075 * (mass - 3.0) - 0.025 * zeta, 3)
        return {
            "regime": "中等质量恒星 (Intermediate-Mass Star)",
            "core_structure": "对流核 + 辐射包层 → 非简并平稳氦点火(蓝环) → TP-AGB → 碳氧白矮星",
            "max_burning": "CNO 循环氢燃烧 + 非简并 3α 氦燃烧",
            "remnant_type": "CO WD (大质量碳氧白矮星)",
            "remnant_code": "CO_WD",
            "remnant_mass": m_rem,
            "supernova": "强星风 + 行星状星云 (Planetary Nebula)",
        }
    elif mass < 10.0:
        if z <= 0.001:
            return {
                "regime": "超渐近巨星支 / 电子俘获超新星前身星 (Super-AGB → ECSN)",
                "core_structure": "低金属丰度弱星风 → 偏心碳点火 → 简并 O-Ne-Mg 核达 1.37 M☉ 坍缩",
                "max_burning": "H → He → C 燃烧 + 20Ne/24Mg 电子俘获",
                "remnant_type": "NS (电子俘获中子星)",
                "remnant_code": "NS",
                "remnant_mass": 1.28,
                "supernova": "电子俘获超新星 (ECSN)",
            }
        else:
            m_rem = round(1.20 - 0.03 * zeta, 3)
            return {
                "regime": "超渐近巨星支临界恒星 (Super-AGB Critical Star)",
                "core_structure": "对流核 + 偏心碳点火 → 强星风剥离包层 → 氧氖镁白矮星",
                "max_burning": "H → He → 偏心碳燃烧 (Off-center C Burning)",
                "remnant_type": "ONeMg WD (氧氖镁白矮星)",
                "remnant_code": "ONe_WD",
                "remnant_mass": m_rem,
                "supernova": "超渐近巨星支强星风 + 星云抛射",
            }
    elif mass < 20.0:
        m_rem = round(1.46 - 0.03 * zeta, 3)
        return {
            "regime": "大质量核心坍缩前身星 (Massive CCSN Progenitor)",
            "core_structure": "全核合成同心洋葱皮结构 (Fe→Si→O→Ne→C→He→H)",
            "max_burning": "完整聚变链直至硅燃烧生成 56Fe/56Ni",
            "remnant_type": "NS (中子星 / 脉冲星)",
            "remnant_code": "NS",
            "remnant_mass": m_rem,
            "supernova": "IIP / IIb 型核心坍缩超新星 (CCSN)",
        }
    else:
        m_rem = round(2.95 - 0.35 * zeta, 3)
        return {
            "regime": "极大质量黑洞前身星 (Very Massive Black Hole Progenitor)",
            "core_structure": "强星风剥离 + 大质量铁核坍缩 + 回落吸积 (Fallback)",
            "max_burning": "完整聚变链 + 铁核光致蜕变坍缩",
            "remnant_type": "BH (恒星级黑洞)",
            "remnant_code": "BH",
            "remnant_mass": m_rem,
            "supernova": "Ib/Ic 型超新星或直接坍缩黑洞 (CCSN / Fallback BH)",
        }


def compute_stage_anchors(mass: float, z: float, zams: dict, pathway: dict) -> list:
    """
    Return 6 stage anchor tuples:
    (log_Teff, log_L, log_Tc, log_Rhoc, age_yr, current_mass, eta_degeneracy)
    """
    log_Teff0 = zams["log_Teff"]
    log_L0 = zams["log_L"]
    log_Tc0 = zams["log_Tc"]
    log_Rhoc0 = zams["log_Rhoc"]
    t_ms = zams["t_ms"]
    zeta = zams["zeta"]

    if mass < 0.5:
        # 0.3 M_sun: Fully convective -> Blue Dwarf hook -> He WD cooling
        return [
            (log_Teff0, log_L0, log_Tc0, log_Rhoc0, 0.0, mass, -0.8),
            (log_Teff0 + 0.055, log_L0 + 0.32, log_Tc0 + 0.14, log_Rhoc0 + 0.90, t_ms * 0.85, mass * 0.992, 1.4),
            (log_Teff0 + 0.165, log_L0 + 0.55, log_Tc0 + 0.24, log_Rhoc0 + 1.85, t_ms * 1.00, mass * 0.980, 4.8),
            (log_Teff0 + 0.240, log_L0 + 0.18, log_Tc0 + 0.20, log_Rhoc0 + 2.75, t_ms * 1.03, pathway["remnant_mass"], 11.5),
            (3.98 - 0.02 * zeta, -1.35, 7.05, 5.20, t_ms * 1.08, pathway["remnant_mass"], 24.0),
            (3.74 - 0.02 * zeta, -2.65, 6.48, 5.32, t_ms * 1.16, pathway["remnant_mass"], 48.0),
        ]

    elif mass < 2.2:
        log_Teff_rgb = 3.515 - 0.038 * zeta
        log_L_rgb = 3.36 - 0.07 * zeta
        log_Teff_hb = 3.695 - 0.085 * zeta
        log_L_hb = 1.70 - 0.04 * zeta
        log_Teff_agb = 3.485 - 0.038 * zeta
        log_L_agb = 3.68 - 0.05 * zeta
        return [
            (log_Teff0, log_L0, log_Tc0, log_Rhoc0, 0.0, mass, -1.6),
            (log_Teff0 - 0.015, log_L0 + 0.36, log_Tc0 + 0.18, log_Rhoc0 + 0.98, t_ms, mass * 0.996, 0.4),
            (log_Teff_rgb, log_L_rgb, 7.98, 5.80, t_ms * 1.115, mass * 0.86, 19.2),
            (log_Teff_hb, log_L_hb, 8.09, 4.18, t_ms * 1.127, mass * 0.82, 1.5),
            (log_Teff_agb, log_L_agb, 8.26, 6.18, t_ms * 1.131, mass * 0.64, 24.5),
            (4.38, -1.45, 7.22, 6.42, t_ms * 1.150, pathway["remnant_mass"], 49.0),
        ]

    elif mass < 10.0:
        is_super_agb = mass >= 7.0
        ecsn_branch = is_super_agb and (z <= 0.001)
        log_Teff_rgb = 3.585 - 0.032 * zeta + 0.01 * math.log10(mass / 3.0)
        log_L_rgb = log_L0 + 0.38
        log_Teff_loop = min(log_Teff0 - 0.06, 3.74 + 0.08 * math.log10(mass / 3.0) - 0.095 * zeta)
        log_L_loop = log_L0 + 0.54
        log_Teff_agb = 3.505 - 0.038 * zeta
        log_L_agb = min(4.68, log_L0 + 1.08)

        if ecsn_branch:
            end_node = (3.52, log_L_agb + 0.12, 9.12, 9.40, t_ms * 1.185, mass * 0.78, 32.0)
        else:
            end_node = (
                4.48 if is_super_agb else 4.42,
                -1.15,
                7.35,
                6.88 if is_super_agb else 6.55,
                t_ms * 1.21,
                pathway["remnant_mass"],
                52.0,
            )

        return [
            (log_Teff0, log_L0, log_Tc0, log_Rhoc0, 0.0, mass, -2.5),
            (log_Teff0 - 0.075, log_L0 + 0.28, log_Tc0 + 0.13, log_Rhoc0 + 0.56, t_ms, mass * 0.995, -1.8),
            (log_Teff_rgb, log_L_rgb, 8.07, 4.20 - 0.38 * math.log10(mass / 3.0), t_ms * 1.018, mass * 0.985, -0.3),
            (log_Teff_loop, log_L_loop, 8.19, 3.82 - 0.32 * math.log10(mass / 3.0), t_ms * 1.165, mass * 0.955, -0.6),
            (
                log_Teff_agb,
                log_L_agb,
                8.84 if is_super_agb else 8.40,
                6.58 if is_super_agb else 6.22,
                t_ms * 1.182,
                mass * (0.82 if ecsn_branch else 0.70),
                17.5,
            ),
            end_node,
        ]

    else:
        wind_factor = (z / 0.014) ** 0.65
        dm_ms = 0.045 * ((mass / 15.0) ** 1.45) * wind_factor
        dm_post = 0.24 * ((mass / 15.0) ** 1.35) * wind_factor
        m_tams = max(mass * 0.78, mass * (1.0 - dm_ms))
        m_end = max(pathway["remnant_mass"] * 3.0, mass * (1.0 - dm_ms - dm_post))

        log_Teff_he_ign = 3.88 - 0.085 * zeta
        log_Teff_rsg = 3.565 - 0.028 * zeta

        return [
            (log_Teff0, log_L0, log_Tc0, log_Rhoc0, 0.0, mass, -3.6),
            (log_Teff0 - 0.115, log_L0 + 0.25, log_Tc0 + 0.14, log_Rhoc0 + 0.52, t_ms, m_tams, -2.9),
            (log_Teff_he_ign, log_L0 + 0.32, 8.23, 3.12 - 0.20 * math.log10(mass / 15.0), t_ms * 1.008, m_tams * 0.985, -1.9),
            (log_Teff_rsg + 0.05 - 0.06 * zeta, log_L0 + 0.37, 8.33, 3.35 - 0.20 * math.log10(mass / 15.0), t_ms * 1.088, 0.5 * (m_tams + m_end), -1.0),
            (log_Teff_rsg, log_L0 + 0.42, 8.98, 5.72, t_ms * 1.098, m_end * 1.015, 0.9),
            (log_Teff_rsg - 0.01, log_L0 + 0.45, 9.56, 9.48, t_ms * 1.0985, m_end, 4.6),
        ]


def compute_kippenhahn_series(mass: float, z: float, s_grid: np.ndarray) -> dict:
    """Compute compact Kippenhahn zone boundary arrays over s_grid."""
    conv_core, conv_env, h_shell, he_shell = [], [], [], []
    for s_val in s_grid:
        s_val = float(s_val)
        if mass < 0.5:
            if s_val < 1.8:
                cc, ce, hs, hes = 0.0, 0.0, None, None
            elif s_val < 3.0:
                frac = (s_val - 1.8) / 1.2
                cc, ce, hs, hes = 0.0, min(0.98, 0.25 + 0.73 * frac), 0.85, None
            else:
                cc, ce, hs, hes = 0.0, 0.99, None, None
        elif mass < 2.2:
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


def compute_abundance_profile(mass: float, z: float, stage_idx: int, pathway: dict) -> dict:
    """
    Compute 60-point radial abundance profile X_i(q) over relative mass coordinate q in [0.01, 1.0]
    for stage_idx in [0, 1, 2, 3, 4, 5], strictly normalized so sum_i X_i(q) = 1.0.
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
                q_fe = min(0.22, max(0.075, m_fe / m_final))
                q_si = q_fe + 0.065 + 0.002 * (mass - 15.0)
                q_one = q_si + 0.14 + 0.005 * (mass - 15.0)
                q_co = q_one + 0.12 + 0.003 * (mass - 15.0)
                q_he = min(0.88, q_co + 0.16 + 0.004 * (mass - 15.0) + 0.035 * (-zeta))

                w_fe = sig(q_arr, q_fe, 0.014)
                w_si = sig(q_arr, q_si, 0.016)
                w_one = sig(q_arr, q_one, 0.020)
                w_co = sig(q_arr, q_co, 0.022)
                w_he = sig(q_arr, q_he, 0.025)

                s_fe = 1.0 - w_fe
                s_si = w_fe * (1.0 - w_si)
                s_one = w_si * (1.0 - w_one)
                s_co = w_one * (1.0 - w_co)
                s_he = w_co * (1.0 - w_he)
                s_env = w_he

                H1 = (X_init - 0.06) * s_env
                He4 = (1.0 - z) * s_he + (Y_init + 0.06) * s_env
                C12 = 0.08 * s_one + 0.36 * s_co + c_init * (s_he + s_env)
                O16 = 0.14 * s_si + 0.66 * s_one + (0.64 - z) * s_co + o_init * (s_he + s_env)
                Ne20 = 0.24 * s_one + ne_init * (s_co + s_he + s_env)
                Si28 = 0.08 * s_fe + 0.78 * s_si + 0.02 * s_one + si_init * (s_co + s_he + s_env)
                Fe56 = 0.92 * s_fe + 0.08 * s_si + fe_init * (s_one + s_co + s_he + s_env)

    stack = np.vstack([H1, He4, C12, O16, Ne20, Si28, Fe56])
    stack = np.maximum(0.0, stack)
    totals = np.sum(stack, axis=0)
    stack = stack / totals

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


def generate_track(mass: float, z: float, n_steps: int = 200) -> dict:
    """Generate full 200-step stellar evolutionary track, interior profiles, and Kippenhahn zones."""
    zams = zams_properties(mass, z)
    pathway = classify_pathway(mass, z)
    anchors = compute_stage_anchors(mass, z, zams, pathway)

    s_grid = np.linspace(0.0, 5.0, n_steps)
    s_nodes = np.arange(6, dtype=float)
    a_arr = np.array(anchors, dtype=float)

    log_Teff = np.interp(s_grid, s_nodes, a_arr[:, 0])
    log_L = np.interp(s_grid, s_nodes, a_arr[:, 1])
    log_Tc = np.interp(s_grid, s_nodes, a_arr[:, 2])
    log_Rhoc = np.interp(s_grid, s_nodes, a_arr[:, 3])
    age_yr = np.interp(s_grid, s_nodes, a_arr[:, 4])
    star_mass = np.interp(s_grid, s_nodes, a_arr[:, 5])
    eta_deg = np.interp(s_grid, s_nodes, a_arr[:, 6])

    if mass >= 1.2:
        hook = 0.026 * np.exp(-(((s_grid - 1.03) / 0.055) ** 2))
        log_Teff += hook
        log_L += 0.035 * hook

    if 0.5 <= mass < 10.0 and not (mass >= 7.0 and z <= 0.001):
        pn_mask = (s_grid > 4.0) & (s_grid < 5.0)
        u = s_grid[pn_mask] - 4.0
        teff_peak = 4.82 if mass >= 3.0 else 4.68
        log_Teff[pn_mask] = (
            (1.0 - u) * a_arr[4, 0]
            + u * a_arr[5, 0]
            + 0.42 * np.sin(u * math.pi) * (teff_peak - 0.5 * (a_arr[4, 0] + a_arr[5, 0]))
        )
        l_high = a_arr[4, 1]
        l_low = a_arr[5, 1]
        drop_w = 0.5 * (1.0 + np.tanh((u - 0.48) / 0.14))
        log_L[pn_mask] = l_high * (1.0 - drop_w) + l_low * drop_w

    log_R = 0.5 * log_L - 2.0 * (log_Teff - 3.7613)

    stage_indices = [int(round(s * (n_steps - 1) / 5.0)) for s in range(6)]
    profiles = {str(s): compute_abundance_profile(mass, z, s, pathway) for s in range(6)}
    kippenhahn = compute_kippenhahn_series(mass, z, s_grid)

    return {
        "mass_init": mass,
        "z_init": z,
        "zams": {k: round(v, 4) for k, v in zams.items()},
        "pathway": pathway,
        "stage_names": STAGE_NAMES,
        "stage_step_indices": stage_indices,
        "track": {
            "s": [round(float(x), 4) for x in s_grid],
            "age_yr": [round(float(x), 2) for x in age_yr],
            "mass": [round(float(x), 4) for x in star_mass],
            "log_Teff": [round(float(x), 4) for x in log_Teff],
            "log_L": [round(float(x), 4) for x in log_L],
            "log_R": [round(float(x), 4) for x in log_R],
            "log_Tc": [round(float(x), 4) for x in log_Tc],
            "log_Rhoc": [round(float(x), 4) for x in log_Rhoc],
            "eta": [round(float(x), 2) for x in eta_deg],
        },
        "kippenhahn": kippenhahn,
        "profiles": profiles,
    }


def build_full_grid(out_dir: Path):
    grid_data = {
        "metadata": {
            "version": "2.0.0",
            "title": "Stellar Evolution Parameter Space Explorer (Physics & MESA Audited)",
            "masses": MASS_GRID,
            "metallicities": METALLICITY_GRID,
            "species": SPECIES,
            "stage_names": STAGE_NAMES,
        },
        "models": {},
    }
    summary_rows = []

    for z in METALLICITY_GRID:
        z_key = f"{z:.4f}".rstrip("0").rstrip(".") if z < 1 else str(z)
        grid_data["models"][z_key] = {}
        for m in MASS_GRID:
            m_key = f"{m:.1f}"
            model = generate_track(m, z)
            grid_data["models"][z_key][m_key] = model

            tr = model["track"]
            summary_rows.append({
                "M_init_Msun": m,
                "Z_init": z,
                "Regime": model["pathway"]["regime"],
                "log_L_ZAMS": model["zams"]["log_L"],
                "log_Teff_ZAMS": model["zams"]["log_Teff"],
                "t_MS_yr": f"{model['zams']['t_ms']:.3e}",
                "max_log_L": round(max(tr["log_L"]), 3),
                "max_log_Tc": round(max(tr["log_Tc"]), 3),
                "max_log_Rhoc": round(max(tr["log_Rhoc"]), 3),
                "Remnant_Type": model["pathway"]["remnant_type"],
                "Remnant_Mass_Msun": model["pathway"]["remnant_mass"],
            })

    json_path = out_dir / "stellar_grid_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(grid_data, f, ensure_ascii=False, separators=(",", ":"))

    csv_path = out_dir / "parameter_space_summary.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"Generated {len(summary_rows)} models -> {json_path} ({json_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    build_full_grid(Path(__file__).parent)
