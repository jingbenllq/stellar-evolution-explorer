"""
Stellar Evolutionary Tracks, Pathways, and Grid Generation
==========================================================
Computes 6-stage evolutionary anchor nodes, continuous 200-step tracks,
internal Kippenhahn zones, radial abundance profiles, and concentric
onion shells across the 28-model parameter space:
  - M_init in [0.3, 1.0, 3.0, 5.0, 8.0, 15.0, 25.0] M_sun
  - Z_init in [0.0001, 0.001, 0.014, 0.03]
"""

import csv
import json
import math
from pathlib import Path
from typing import Dict, List, Any, Tuple
import numpy as np

from .zams import MASS_GRID, METALLICITY_GRID, STAGE_NAMES, SPECIES, zams_properties
from .kippenhahn import compute_kippenhahn_series
from .abundance import compute_abundance_profile
from .nucleosynthesis import generate_onion_shells


def classify_pathway(mass: float, z: float) -> Dict[str, Any]:
    """
    Determine evolutionary regime, core burning limits, supernova type,
    and final remnant properties across the mass-metallicity grid.
    """
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


def compute_stage_anchors(mass: float, z: float, zams: Dict[str, Any], pathway: Dict[str, Any]) -> List[Tuple[float, ...]]:
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


def generate_track(mass: float, z: float, n_steps: int = 200) -> Dict[str, Any]:
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

    # Build stage models conforming to PROJECT.md interface contracts
    canonical_stage_names = ["ZAMS", "TAMS", "RGB", "CHeB", "AGB", "Remnant"]
    stages_list = []
    for s_i in range(6):
        step_idx = stage_indices[s_i]
        tp = {
            "log_L": float(log_L[step_idx]),
            "log_Teff": float(log_Teff[step_idx]),
            "log_R": float(log_R[step_idx]),
            "log_Tc": float(log_Tc[step_idx]),
            "log_Rhoc": float(log_Rhoc[step_idx]),
        }
        shells = generate_onion_shells(mass, z, s_i, tp, profiles[str(s_i)])
        stages_list.append({
            "name": canonical_stage_names[s_i],
            "age_yr": round(float(age_yr[step_idx]), 2),
            "log_L": round(float(log_L[step_idx]), 4),
            "log_Teff": round(float(log_Teff[step_idx]), 4),
            "radius_Rsun": round(float(10.0 ** log_R[step_idx]), 4),
            "onion_shells": [s.to_dict() for s in shells],
        })

    age_rounded = [round(float(x), 2) for x in age_yr]
    mass_rounded = [round(float(x), 4) for x in star_mass]

    return {
        "mass_init": mass,
        "z_init": z,
        "zams": {k: round(v, 4) for k, v in zams.items()},
        "pathway": pathway,
        "stage_names": STAGE_NAMES,
        "stage_step_indices": stage_indices,
        "stages": stages_list,
        "track": {
            "s": [round(float(x), 4) for x in s_grid],
            "age_yr": age_rounded,
            "star_age": age_rounded,  # Alias for MESA & E2E compatibility
            "mass": mass_rounded,
            "star_mass": mass_rounded,  # Alias for MESA & E2E compatibility
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
    """Generate the full 28-model parameter space grid and summary tables."""
    grid_data = {
        "metadata": {
            "version": "2.1.0",
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
    return grid_data
