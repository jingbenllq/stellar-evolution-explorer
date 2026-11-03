#!/usr/bin/env python3
"""
Publication-Grade Stellar Evolution Parameter Space Figure Generator
====================================================================
Generates 5 high-resolution vector SVG and PNG figures in `/workspace/figures/`
using standard ApJ / MESA pgstar typography (DejaVu Sans):
  1. fig1_hr_diagram_grid.{svg,png}          - Multi-Mass & Metallicity H-R Diagram
  2. fig2_central_rho_T_phase.{svg,png}      - Central Density-Temperature Phase Diagram
  3. fig3_kippenhahn_comparison.{svg,png}    - Kippenhahn Diagrams (1 M_sun vs 15 M_sun)
  4. fig4_internal_profiles_stages.{svg,png} - Radial Chemical Abundance & Onion-Skin Profiles
  5. fig5_parameter_space_scaling.{svg,png}  - ZAMS Scaling Laws & Stage Lifetimes
"""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

MASS_COLORS = {
    0.3: "#ff595e",
    1.0: "#ffca3a",
    3.0: "#8ac926",
    5.0: "#00b4d8",
    8.0: "#4361ee",
    15.0: "#b5179e",
    25.0: "#f72585",
}


def svg_header(width: int, height: int) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" style="background:#0b1021;font-family:\'DejaVu Sans\',sans-serif;">\n'
        '<defs>\n'
        '  <linearGradient id="bgGrad" x1="0" y1="0" x2="0" y2="1">\n'
        '    <stop offset="0%" stop-color="#0b1021"/>\n'
        '    <stop offset="100%" stop-color="#111936"/>\n'
        '  </linearGradient>\n'
        '  <pattern id="convHatch" width="8" height="8" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">\n'
        '    <line x1="0" y1="0" x2="0" y2="8" stroke="#38bdf8" stroke-width="2" stroke-opacity="0.45"/>\n'
        '  </pattern>\n'
        '  <pattern id="envHatch" width="8" height="8" patternTransform="rotate(-45 0 0)" patternUnits="userSpaceOnUse">\n'
        '    <line x1="0" y1="0" x2="0" y2="8" stroke="#f59e0b" stroke-width="2" stroke-opacity="0.40"/>\n'
        '  </pattern>\n'
        '</defs>\n'
        f'<rect width="{width}" height="{height}" fill="url(#bgGrad)"/>\n'
    )


def build_fig1_hr_diagram(data: dict) -> str:
    w, h = 1120, 760
    pad_l, pad_r, pad_t, pad_b = 95, 265, 75, 80
    pw = w - pad_l - pad_r
    ph = h - pad_t - pad_b

    x_min, x_max = 3.35, 5.15
    y_min, y_max = -3.0, 6.0

    def tx(log_teff: float) -> float:
        return pad_l + (x_max - log_teff) / (x_max - x_min) * pw

    def ty(log_l: float) -> float:
        return pad_t + (y_max - log_l) / (y_max - y_min) * ph

    out = [svg_header(w, h)]
    out.append(f'<text x="{pad_l + pw/2:.1f}" y="38" fill="#f8fafc" font-size="20" font-weight="bold" text-anchor="middle">Stellar Evolution Parameter Space: Hertzsprung-Russell Diagram</text>')
    out.append(f'<text x="{pad_l + pw/2:.1f}" y="60" fill="#94a3b8" font-size="13" text-anchor="middle">Solid: Solar Metallicity (Z = 0.014) | Dashed: Metal-Poor Pop II (Z = 0.0001) | Dots: Evolutionary Stages (ZAMS to End)</text>')

    out.append(f'<rect x="{pad_l}" y="{pad_t}" width="{pw}" height="{ph}" fill="#0f172a" stroke="#334155" stroke-width="1.5"/>')

    for xv in [3.4, 3.6, 3.8, 4.0, 4.2, 4.4, 4.6, 4.8, 5.0]:
        px = tx(xv)
        out.append(f'<line x1="{px:.1f}" y1="{pad_t}" x2="{px:.1f}" y2="{pad_t+ph}" stroke="#1e293b" stroke-width="1"/>')
        out.append(f'<text x="{px:.1f}" y="{pad_t+ph+24}" fill="#cbd5e1" font-size="12" text-anchor="middle">{xv:.1f}</text>')
    for yv in range(-3, 7):
        py = ty(yv)
        out.append(f'<line x1="{pad_l}" y1="{py:.1f}" x2="{pad_l+pw}" y2="{py:.1f}" stroke="#1e293b" stroke-width="1"/>')
        out.append(f'<text x="{pad_l-12}" y="{py+4:.1f}" fill="#cbd5e1" font-size="12" text-anchor="end">{yv}</text>')

    # Constant-radius lines
    for r_val, r_lbl in [(0.01, "0.01 R_sun (WD)"), (0.1, "0.1 R_sun"), (1.0, "1 R_sun"), (10.0, "10 R_sun"), (100.0, "100 R_sun"), (1000.0, "1000 R_sun (RSG)")]:
        pts = []
        for xv in [x_min + i * 0.02 for i in range(int((x_max - x_min) / 0.02) + 1)]:
            yv = 2.0 * math.log10(r_val) + 4.0 * (xv - 3.7613)
            if y_min <= yv <= y_max:
                pts.append((tx(xv), ty(yv)))
        if len(pts) >= 2:
            d_str = " ".join(f"{'M' if i==0 else 'L'}{p[0]:.1f},{p[1]:.1f}" for i, p in enumerate(pts))
            out.append(f'<path d="{d_str}" fill="none" stroke="#475569" stroke-width="1" stroke-dasharray="4,4"/>')
            mid = pts[len(pts) // 2]
            out.append(f'<text x="{mid[0]:.1f}" y="{mid[1]-6:.1f}" fill="#64748b" font-size="10">{r_lbl}</text>')

    # ZAMS locus line for Z=0.014
    zams_pts = []
    for m_obj in data["models"]:
        if abs(m_obj["initial_z"] - 0.014) < 1e-6:
            zams_pts.append((tx(m_obj["history"]["log_Teff"][0]), ty(m_obj["history"]["log_L"][0])))
    if zams_pts:
        d_zams = " ".join(f"{'M' if i==0 else 'L'}{p[0]:.1f},{p[1]:.1f}" for i, p in enumerate(zams_pts))
        out.append(f'<path d="{d_zams}" fill="none" stroke="#94a3b8" stroke-width="2.5" stroke-opacity="0.55"/>')

    # Plot tracks for Z=0.0001 (dashed) and Z=0.014 (solid)
    for m_obj in data["models"]:
        z = m_obj["initial_z"]
        if z not in (0.014, 0.0001):
            continue
        mass = m_obj["initial_mass"]
        col = MASS_COLORS[mass]
        teffs = m_obj["history"]["log_Teff"]
        lums = m_obj["history"]["log_L"]

        pts = []
        for t_v, l_v in zip(teffs, lums):
            cx = min(pad_l + pw, max(pad_l, tx(t_v)))
            cy = min(pad_t + ph, max(pad_t, ty(l_v)))
            pts.append((cx, cy))
        d_str = " ".join(f"{'M' if i==0 else 'L'}{p[0]:.1f},{p[1]:.1f}" for i, p in enumerate(pts))

        if abs(z - 0.0001) < 1e-6:
            out.append(f'<path d="{d_str}" fill="none" stroke="{col}" stroke-width="1.6" stroke-dasharray="5,4" stroke-opacity="0.75"/>')
        else:
            out.append(f'<path d="{d_str}" fill="none" stroke="{col}" stroke-width="2.5"/>')
            for p_prof in m_obj["profiles"]:
                px = min(pad_l + pw, max(pad_l, tx(p_prof["log_Teff"])))
                py = min(pad_t + ph, max(pad_t, ty(p_prof["log_L"])))
                r_dot = 5.5 if p_prof["stage_index"] in (1, 6) else 3.8
                out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r_dot}" fill="{col}" stroke="#0f172a" stroke-width="1.2"/>')
            p0 = pts[0]
            out.append(f'<text x="{p0[0]-8:.1f}" y="{p0[1]+4:.1f}" fill="{col}" font-size="12" font-weight="bold" text-anchor="end">{mass:g} M_sun</text>')

    # Annotations
    out.append(f'<text x="{tx(3.52)+6:.1f}" y="{ty(3.35):.1f}" fill="#fde047" font-size="11" font-weight="bold">He Flash (1 M_sun)</text>')
    out.append(f'<text x="{tx(3.85):.1f}" y="{ty(2.85)-10:.1f}" fill="#38bdf8" font-size="11" font-weight="bold">Blue Loop (Core He Burn)</text>')
    out.append(f'<text x="{tx(4.32):.1f}" y="{ty(-1.85):.1f}" fill="#cbd5e1" font-size="12" font-weight="bold">White Dwarf Cooling Sequence</text>')
    out.append(f'<text x="{tx(3.57)-10:.1f}" y="{ty(5.2):.1f}" fill="#f472b6" font-size="11" font-weight="bold" text-anchor="end">Red Supergiants / Pre-CCSN →</text>')

    out.append(f'<text x="{pad_l + pw/2:.1f}" y="{h-22}" fill="#f8fafc" font-size="15" font-weight="bold" text-anchor="middle">Effective Temperature log10(T_eff / K)  [Hotter to the Left]</text>')
    out.append(f'<text x="28" y="{pad_t + ph/2:.1f}" fill="#f8fafc" font-size="15" font-weight="bold" text-anchor="middle" transform="rotate(-90, 28, {pad_t + ph/2:.1f})">Luminosity log10(L / L_sun)</text>')

    # Legend panel
    lx, ly = pad_l + pw + 18, pad_t + 10
    out.append(f'<rect x="{lx}" y="{ly}" width="232" height="400" rx="8" fill="#1e293b" stroke="#334155"/>')
    out.append(f'<text x="{lx+14}" y="{ly+28}" fill="#f8fafc" font-size="14" font-weight="bold">Initial Mass (M_init)</text>')
    for idx, (m_val, col) in enumerate(MASS_COLORS.items()):
        yy = ly + 55 + idx * 30
        out.append(f'<line x1="{lx+14}" y1="{yy-4}" x2="{lx+46}" y2="{yy-4}" stroke="{col}" stroke-width="3"/>')
        out.append(f'<circle cx="{lx+30}" cy="{yy-4}" r="4" fill="{col}"/>')
        rem = "He WD" if m_val < 0.5 else ("CO WD" if m_val < 7 else ("ONe WD" if m_val < 10 else ("NS (CCSN)" if m_val < 20 else "NS / BH")))
        out.append(f'<text x="{lx+54}" y="{yy}" fill="#e2e8f0" font-size="12">{m_val:g} M_sun → {rem}</text>')

    out.append(f'<text x="{lx+14}" y="{ly+285}" fill="#f8fafc" font-size="14" font-weight="bold">Metallicity Grid (Z_init)</text>')
    out.append(f'<line x1="{lx+14}" y1="{ly+310}" x2="{lx+48}" y2="{ly+310}" stroke="#38bdf8" stroke-width="2.5"/>')
    out.append(f'<text x="{lx+56}" y="{ly+314}" fill="#cbd5e1" font-size="12">Z = 0.014 (Solar)</text>')
    out.append(f'<line x1="{lx+14}" y1="{ly+338}" x2="{lx+48}" y2="{ly+338}" stroke="#38bdf8" stroke-width="2" stroke-dasharray="5,4"/>')
    out.append(f'<text x="{lx+56}" y="{ly+342}" fill="#cbd5e1" font-size="12">Z = 0.0001 (Pop II)</text>')
    out.append(f'<text x="{lx+14}" y="{ly+372}" fill="#94a3b8" font-size="11">* Lower Z → lower opacity</text>')
    out.append(f'<text x="{lx+14}" y="{ly+388}" fill="#94a3b8" font-size="11">  → hotter &amp; more luminous</text>')

    out.append("</svg>")
    return "\n".join(out)


def build_fig2_rho_T_phase(data: dict) -> str:
    w, h = 1120, 740
    pad_l, pad_r, pad_t, pad_b = 95, 265, 75, 80
    pw = w - pad_l - pad_r
    ph = h - pad_t - pad_b

    x_min, x_max = 0.0, 10.0
    y_min, y_max = 6.5, 9.8

    def tx(log_rho: float) -> float:
        return pad_l + (log_rho - x_min) / (x_max - x_min) * pw

    def ty(log_t: float) -> float:
        return pad_t + (y_max - log_t) / (y_max - y_min) * ph

    out = [svg_header(w, h)]
    out.append(f'<text x="{pad_l + pw/2:.1f}" y="38" fill="#f8fafc" font-size="20" font-weight="bold" text-anchor="middle">Central Evolutionary Phase Diagram (log rho_c vs. log T_c)</text>')
    out.append(f'<text x="{pad_l + pw/2:.1f}" y="60" fill="#94a3b8" font-size="13" text-anchor="middle">Contraction Scaling (T_c ~ rho_c^1/3), Electron Degeneracy Boundary (eta &gt; 0), and Nuclear Ignition Thresholds</text>')

    out.append(f'<rect x="{pad_l}" y="{pad_t}" width="{pw}" height="{ph}" fill="#0f172a" stroke="#334155" stroke-width="1.5"/>')

    for xv in range(0, 11, 1):
        px = tx(xv)
        out.append(f'<line x1="{px:.1f}" y1="{pad_t}" x2="{px:.1f}" y2="{pad_t+ph}" stroke="#1e293b" stroke-width="1"/>')
        out.append(f'<text x="{px:.1f}" y="{pad_t+ph+24}" fill="#cbd5e1" font-size="12" text-anchor="middle">{xv}</text>')
    for yv_10 in range(65, 100, 5):
        yv = yv_10 / 10.0
        py = ty(yv)
        out.append(f'<line x1="{pad_l}" y1="{py:.1f}" x2="{pad_l+pw}" y2="{py:.1f}" stroke="#1e293b" stroke-width="1"/>')
        out.append(f'<text x="{pad_l-12}" y="{py+4:.1f}" fill="#cbd5e1" font-size="12" text-anchor="end">{yv:.1f}</text>')

    # Electron degeneracy boundary
    deg_pts = []
    for r_v in [0.5 + i * 0.2 for i in range(46)]:
        t_v = 5.25 + 0.667 * min(r_v, 6.2) + 0.333 * max(0.0, r_v - 6.2)
        if y_min <= t_v <= y_max:
            deg_pts.append((tx(r_v), ty(t_v)))
    if deg_pts:
        poly_pts = [(deg_pts[0][0], ty(y_min))] + deg_pts + [(deg_pts[-1][0], ty(y_min))]
        p_str = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in poly_pts)
        out.append(f'<polygon points="{p_str}" fill="#3b82f6" fill-opacity="0.10"/>')
        d_deg = " ".join(f"{'M' if i==0 else 'L'}{p[0]:.1f},{p[1]:.1f}" for i, p in enumerate(deg_pts))
        out.append(f'<path d="{d_deg}" fill="none" stroke="#60a5fa" stroke-width="2" stroke-dasharray="6,4"/>')
        out.append(f'<text x="{tx(5.6):.1f}" y="{ty(7.05):.1f}" fill="#60a5fa" font-size="12" font-weight="bold">Electron Degenerate Regime (eta &gt; 0)</text>')
        out.append(f'<text x="{tx(1.8):.1f}" y="{ty(8.85):.1f}" fill="#94a3b8" font-size="12" font-weight="bold">Non-Degenerate Ideal Gas (T_c ~ rho_c^1/3)</text>')

    ign_thresholds = [
        (7.05, "#4ade80", "H Burning Ignition (p-p / CNO, T ~ 1.2e7 K)"),
        (8.02, "#facc15", "He Burning Ignition (3-alpha, T ~ 1.0e8 K)"),
        (8.72, "#fb923c", "Carbon Burning Ignition (12C + 12C, T ~ 5.2e8 K)"),
        (9.18, "#f87171", "Neon / Oxygen Burning Ignition (T ~ 1.5e9 K)"),
        (9.50, "#c084fc", "Silicon Burning &amp; Fe Core Collapse (T ~ 3.2e9 K)"),
    ]
    for t_ign, col, lbl in ign_thresholds:
        py = ty(t_ign)
        out.append(f'<line x1="{pad_l}" y1="{py:.1f}" x2="{pad_l+pw}" y2="{py:.1f}" stroke="{col}" stroke-width="1.3" stroke-dasharray="3,3" stroke-opacity="0.75"/>')
        out.append(f'<text x="{pad_l+10}" y="{py-6:.1f}" fill="{col}" font-size="11">{lbl}</text>')

    for m_obj in data["models"]:
        if abs(m_obj["initial_z"] - 0.014) > 1e-6:
            continue
        mass = m_obj["initial_mass"]
        col = MASS_COLORS[mass]
        rhos = m_obj["history"]["log_center_Rho"]
        ts = m_obj["history"]["log_center_T"]
        pts = [(tx(r), ty(t)) for r, t in zip(rhos, ts)]
        d_str = " ".join(f"{'M' if i==0 else 'L'}{p[0]:.1f},{p[1]:.1f}" for i, p in enumerate(pts))
        out.append(f'<path d="{d_str}" fill="none" stroke="{col}" stroke-width="2.6"/>')
        for p_prof in m_obj["profiles"]:
            px, py = tx(p_prof["log_center_Rho"]), ty(p_prof["log_center_T"])
            out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="{col}" stroke="#0f172a" stroke-width="1.2"/>')
        out.append(f'<text x="{pts[0][0]-6:.1f}" y="{pts[0][1]+4:.1f}" fill="{col}" font-size="11" font-weight="bold" text-anchor="end">{mass:g}M</text>')

    out.append(f'<text x="{pad_l + pw/2:.1f}" y="{h-22}" fill="#f8fafc" font-size="15" font-weight="bold" text-anchor="middle">Central Density log10(rho_c / g cm^-3)</text>')
    out.append(f'<text x="28" y="{pad_t + ph/2:.1f}" fill="#f8fafc" font-size="15" font-weight="bold" text-anchor="middle" transform="rotate(-90, 28, {pad_t + ph/2:.1f})">Central Temperature log10(T_c / K)</text>')

    lx, ly = pad_l + pw + 18, pad_t + 10
    out.append(f'<rect x="{lx}" y="{ly}" width="232" height="430" rx="8" fill="#1e293b" stroke="#334155"/>')
    out.append(f'<text x="{lx+14}" y="{ly+28}" fill="#f8fafc" font-size="14" font-weight="bold">Core Regimes by Mass</text>')
    notes = [
        ("0.3 M_sun (Very Low Mass)", "#ff595e", "Enters degeneracy after H burn;"),
        ("", "#94a3b8", "never ignites He → He WD"),
        ("1.0 M_sun (Solar-Type)", "#ffca3a", "Ignites He in degenerate core"),
        ("", "#94a3b8", "(He Flash) → cools as CO WD"),
        ("3–5 M_sun (Intermediate)", "#8ac926", "Non-degenerate He burn;"),
        ("", "#94a3b8", "degenerate CO core → CO WD"),
        ("8.0 M_sun (Critical Mass)", "#4361ee", "Off-center C ignition →"),
        ("", "#94a3b8", "forms ONe White Dwarf"),
        ("15–25 M_sun (Massive)", "#f72585", "Non-degenerate throughout;"),
        ("", "#94a3b8", "ignites H→He→C→Ne→O→Si"),
        ("", "#94a3b8", "→ Fe Core Collapse (CCSN)"),
    ]
    for i, (title, col, desc) in enumerate(notes):
        yy = ly + 58 + i * 31
        if title:
            out.append(f'<text x="{lx+14}" y="{yy}" fill="{col}" font-size="12" font-weight="bold">{title}</text>')
            out.append(f'<text x="{lx+14}" y="{yy+15}" fill="#cbd5e1" font-size="11">{desc}</text>')
        else:
            out.append(f'<text x="{lx+14}" y="{yy+6}" fill="{col}" font-size="11">{desc}</text>')

    out.append("</svg>")
    return "\n".join(out)


def build_fig3_kippenhahn(data: dict) -> str:
    w, h = 1150, 680
    out = [svg_header(w, h)]
    out.append(f'<text x="{w/2:.1f}" y="36" fill="#f8fafc" font-size="20" font-weight="bold" text-anchor="middle">Kippenhahn Structural Evolution Diagrams: 1.0 M_sun vs. 15.0 M_sun (Z = 0.014)</text>')
    out.append(f'<text x="{w/2:.1f}" y="58" fill="#94a3b8" font-size="13" text-anchor="middle">Comparing Convective vs. Radiative Zones, Core Boundaries (He, CO, Fe), Dredge-Up, and Stellar Wind Mass Loss</text>')

    models_by_m = {m["initial_mass"]: m for m in data["models"] if abs(m["initial_z"] - 0.014) < 1e-6}
    panels = [
        (1.0, 75, 460, "1.0 M_sun Solar-Type Star (Final Remnant: 0.53 M_sun CO WD)", 1.05),
        (15.0, 625, 460, "15.0 M_sun Massive Star (Final Remnant: 1.45 M_sun Fe-Core NS)", 15.5),
    ]
    pad_t, ph = 95, 470

    for mass, px0, pw, title, ymax in panels:
        m_obj = models_by_m[mass]
        hist = m_obj["history"]
        n = len(hist["model_number"])

        def tx(idx: int) -> float:
            return px0 + (idx / (n - 1)) * pw

        def ty(m_val: float) -> float:
            return pad_t + (1.0 - m_val / ymax) * ph

        out.append(f'<text x="{px0 + pw/2:.1f}" y="{pad_t - 12}" fill="#f8fafc" font-size="13" font-weight="bold" text-anchor="middle">{title}</text>')
        out.append(f'<rect x="{px0}" y="{pad_t}" width="{pw}" height="{ph}" fill="#0f172a" stroke="#334155" stroke-width="1.5"/>')

        step_y = 0.2 if ymax < 2.0 else 3.0
        yv = 0.0
        while yv <= ymax + 1e-5:
            py = ty(yv)
            out.append(f'<line x1="{px0}" y1="{py:.1f}" x2="{px0+pw}" y2="{py:.1f}" stroke="#1e293b" stroke-width="1"/>')
            out.append(f'<text x="{px0-8}" y="{py+4:.1f}" fill="#cbd5e1" font-size="11" text-anchor="end">{yv:.1f}</text>')
            yv += step_y

        stage_names_short = ["ZAMS", "TAMS", "RGB/HeIgn", "Core He", "AGB/C-Burn", "End"]
        for s_idx, step_i in enumerate(m_obj["stage_indices"]):
            sx = tx(step_i)
            out.append(f'<line x1="{sx:.1f}" y1="{pad_t}" x2="{sx:.1f}" y2="{pad_t+ph}" stroke="#475569" stroke-width="1" stroke-dasharray="3,3"/>')
            out.append(f'<text x="{sx:.1f}" y="{pad_t+ph+20}" fill="#cbd5e1" font-size="11" text-anchor="middle">{stage_names_short[s_idx]}</text>')

        cc_pts = [(tx(0), ty(0.0))] + [(tx(i), ty(hist["conv_core_top"][i])) for i in range(n)] + [(tx(n - 1), ty(0.0))]
        out.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in cc_pts)}" fill="url(#convHatch)" stroke="#38bdf8" stroke-width="1.2"/>')

        ce_top = [(tx(i), ty(hist["star_mass"][i])) for i in range(n)]
        ce_bot = [(tx(i), ty(hist["conv_env_bot"][i])) for i in reversed(range(n))]
        out.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in (ce_top + ce_bot))}" fill="url(#envHatch)" stroke="#f59e0b" stroke-width="1.2"/>')

        m_curve = " ".join(f"{'M' if i==0 else 'L'}{tx(i):.1f},{ty(hist['star_mass'][i]):.1f}" for i in range(n))
        out.append(f'<path d="{m_curve}" fill="none" stroke="#f8fafc" stroke-width="2.5"/>')

        he_curve = " ".join(f"{'M' if i==0 else 'L'}{tx(i):.1f},{ty(hist['he_core_mass'][i]):.1f}" for i in range(n))
        out.append(f'<path d="{he_curve}" fill="none" stroke="#facc15" stroke-width="2" stroke-dasharray="5,3"/>')

        co_curve = " ".join(f"{'M' if i==0 else 'L'}{tx(i):.1f},{ty(hist['co_core_mass'][i]):.1f}" for i in range(n))
        out.append(f'<path d="{co_curve}" fill="none" stroke="#fb923c" stroke-width="2" stroke-dasharray="3,3"/>')

        if mass >= 10.0:
            fe_curve = " ".join(f"{'M' if i==0 else 'L'}{tx(i):.1f},{ty(hist['fe_core_mass'][i]):.1f}" for i in range(n))
            out.append(f'<path d="{fe_curve}" fill="none" stroke="#f43f5e" stroke-width="2.2"/>')

        out.append(f'<text x="{px0 + pw/2:.1f}" y="{pad_t+ph+44}" fill="#f8fafc" font-size="13" font-weight="bold" text-anchor="middle">Normalized Evolutionary Stage Coordinate</text>')
        out.append(f'<text x="{px0 - 45}" y="{pad_t + ph/2:.1f}" fill="#f8fafc" font-size="13" font-weight="bold" text-anchor="middle" transform="rotate(-90, {px0 - 45}, {pad_t + ph/2:.1f})">Enclosed Mass Coordinate m / M_sun</text>')

    ly = h - 45
    items = [
        ("#f8fafc", "Total Mass M_star(t)"),
        ("#38bdf8", "Convective Core"),
        ("#f59e0b", "Convective Envelope"),
        ("#facc15", "He Core Boundary"),
        ("#fb923c", "CO Core Boundary"),
        ("#f43f5e", "Fe Core Boundary"),
    ]
    for i, (col, lbl) in enumerate(items):
        lx = 65 + i * 178
        out.append(f'<line x1="{lx}" y1="{ly}" x2="{lx+26}" y2="{ly}" stroke="{col}" stroke-width="3"/>')
        out.append(f'<text x="{lx+32}" y="{ly+4}" fill="#e2e8f0" font-size="12">{lbl}</text>')

    out.append("</svg>")
    return "\n".join(out)


def build_fig4_internal_profiles(data: dict) -> str:
    w, h = 1150, 740
    out = [svg_header(w, h)]
    out.append(f'<text x="{w/2:.1f}" y="36" fill="#f8fafc" font-size="20" font-weight="bold" text-anchor="middle">Radial Chemical Composition Profiles Across Evolutionary Stages (MESA profile*.data)</text>')
    out.append(f'<text x="{w/2:.1f}" y="58" fill="#94a3b8" font-size="13" text-anchor="middle">Comparing Core H Depletion (TAMS), CO White Dwarf Stratification, and 15 M_sun Pre-Supernova "Onion-Skin" Structure</text>')

    models_by_m = {m["initial_mass"]: m for m in data["models"] if abs(m["initial_z"] - 0.014) < 1e-6}
    m1 = models_by_m[1.0]
    m15 = models_by_m[15.0]

    panel_specs = [
        (m1["profiles"][1], 75, 95, 460, 245, "1.0 M_sun at TAMS (Central H Exhaustion → He Core)"),
        (m1["profiles"][5], 615, 95, 460, 245, "1.0 M_sun Final State (CO White Dwarf: C/O Core + He/H Envelope)"),
        (m15["profiles"][3], 75, 415, 460, 245, "15.0 M_sun Core He Burning (RSG: Growing C/O Core + He/H Shells)"),
        (m15["profiles"][5], 615, 415, 460, 245, "15.0 M_sun Pre-CCSN Final State (Classic Onion-Skin Layering)"),
    ]

    elem_colors = [
        ("h1", "1H (Hydrogen)", "#38bdf8"),
        ("he4", "4He (Helium)", "#facc15"),
        ("c12", "12C (Carbon)", "#fb923c"),
        ("o16", "16O (Oxygen)", "#4ade80"),
        ("ne20", "20Ne (Neon)", "#a78bfa"),
        ("si28", "28Si (Silicon)", "#f472b6"),
        ("fe56", "56Fe (Iron Core)", "#f43f5e"),
    ]

    for prof, px0, py0, pw, ph, title in panel_specs:
        out.append(f'<text x="{px0 + pw/2:.1f}" y="{py0 - 10}" fill="#f8fafc" font-size="13" font-weight="bold" text-anchor="middle">{title}</text>')
        out.append(f'<rect x="{px0}" y="{py0}" width="{pw}" height="{ph}" fill="#0f172a" stroke="#334155" stroke-width="1.5"/>')

        def tx(q_val: float) -> float:
            return px0 + q_val * pw

        def ty(x_val: float) -> float:
            return py0 + (1.0 - x_val) * ph

        for qv in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
            gx = tx(qv)
            out.append(f'<line x1="{gx:.1f}" y1="{py0}" x2="{gx:.1f}" y2="{py0+ph}" stroke="#1e293b" stroke-width="1"/>')
            out.append(f'<text x="{gx:.1f}" y="{py0+ph+18}" fill="#cbd5e1" font-size="11" text-anchor="middle">{qv:.1f}</text>')
        for xv in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
            gy = ty(xv)
            out.append(f'<line x1="{px0}" y1="{gy:.1f}" x2="{px0+pw}" y2="{gy:.1f}" stroke="#1e293b" stroke-width="1"/>')
            out.append(f'<text x="{px0-8}" y="{gy+4:.1f}" fill="#cbd5e1" font-size="11" text-anchor="end">{xv:.1f}</text>')

        qs = prof["q"]
        for key, _, col in elem_colors:
            vals = prof[key]
            if max(vals) < 0.01:
                continue
            d_str = " ".join(f"{'M' if i==0 else 'L'}{tx(q):.1f},{ty(v):.1f}" for i, (q, v) in enumerate(zip(qs, vals)))
            out.append(f'<path d="{d_str}" fill="none" stroke="{col}" stroke-width="2.4"/>')

        out.append(f'<text x="{px0 + pw/2:.1f}" y="{py0+ph+36}" fill="#cbd5e1" font-size="12" text-anchor="middle">Fractional Mass Coordinate q = m / M_star (0 = Center, 1 = Surface)</text>')
        out.append(f'<text x="{px0 - 38}" y="{py0 + ph/2:.1f}" fill="#cbd5e1" font-size="12" text-anchor="middle" transform="rotate(-90, {px0 - 38}, {py0 + ph/2:.1f})">Mass Fraction X_i</text>')

    ly = h - 28
    for i, (_, lbl, col) in enumerate(elem_colors):
        lx = 65 + i * 150
        out.append(f'<line x1="{lx}" y1="{ly-4}" x2="{lx+26}" y2="{ly-4}" stroke="{col}" stroke-width="3.2"/>')
        out.append(f'<text x="{lx+32}" y="{ly}" fill="#f8fafc" font-size="12" font-weight="bold">{lbl}</text>')

    out.append("</svg>")
    return "\n".join(out)


def build_fig5_scaling_laws(data: dict) -> str:
    w, h = 1150, 640
    out = [svg_header(w, h)]
    out.append(f'<text x="{w/2:.1f}" y="36" fill="#f8fafc" font-size="20" font-weight="bold" text-anchor="middle">Parameter Space Scaling Relations: ZAMS Luminosity L(M, Z) &amp; Main-Sequence Lifetime tau_MS(M, Z)</text>')
    out.append(f'<text x="{w/2:.1f}" y="58" fill="#94a3b8" font-size="13" text-anchor="middle">Steep Mass-Luminosity Scaling (L ~ M^3.5) Shortens Massive Star Lifetimes by Over 4 Orders of Magnitude</text>')

    z_styles = [
        (0.0001, "#38bdf8", "Z = 0.0001 (Extreme Pop II)"),
        (0.001, "#4ade80", "Z = 0.001 (Metal-Poor)"),
        (0.014, "#facc15", "Z = 0.014 (Solar)"),
        (0.03, "#f43f5e", "Z = 0.030 (Metal-Rich)"),
    ]

    px1, py1, pw, ph = 85, 95, 450, 440
    out.append(f'<text x="{px1+pw/2:.1f}" y="{py1-12}" fill="#f8fafc" font-size="14" font-weight="bold" text-anchor="middle">ZAMS Mass–Luminosity Relation L_ZAMS(M, Z)</text>')
    out.append(f'<rect x="{px1}" y="{py1}" width="{pw}" height="{ph}" fill="#0f172a" stroke="#334155" stroke-width="1.5"/>')

    px2, py2 = 635, 95
    out.append(f'<text x="{px2+pw/2:.1f}" y="{py2-12}" fill="#f8fafc" font-size="14" font-weight="bold" text-anchor="middle">Main-Sequence Lifetime tau_MS(M, Z)</text>')
    out.append(f'<rect x="{px2}" y="{py2}" width="{pw}" height="{ph}" fill="#0f172a" stroke="#334155" stroke-width="1.5"/>')

    xm_min, xm_max = -0.6, 1.5
    yl_min, yl_max = -2.0, 6.0
    yt_min, yt_max = 6.5, 11.5

    def tx1(log_m: float) -> float:
        return px1 + (log_m - xm_min) / (xm_max - xm_min) * pw

    def ty1(log_l: float) -> float:
        return py1 + (yl_max - log_l) / (yl_max - yl_min) * ph

    def tx2(log_m: float) -> float:
        return px2 + (log_m - xm_min) / (xm_max - xm_min) * pw

    def ty2(log_t: float) -> float:
        return py2 + (yt_max - log_t) / (yt_max - yt_min) * ph

    for m_tick in [0.3, 1.0, 3.0, 5.0, 8.0, 15.0, 25.0]:
        lm = math.log10(m_tick)
        for tx_fn in (tx1, tx2):
            gx = tx_fn(lm)
            out.append(f'<line x1="{gx:.1f}" y1="{py1}" x2="{gx:.1f}" y2="{py1+ph}" stroke="#1e293b" stroke-width="1"/>')
            out.append(f'<text x="{gx:.1f}" y="{py1+ph+20}" fill="#cbd5e1" font-size="11" text-anchor="middle">{m_tick:g}</text>')

    for lv in range(-2, 7):
        gy = ty1(lv)
        out.append(f'<line x1="{px1}" y1="{gy:.1f}" x2="{px1+pw}" y2="{gy:.1f}" stroke="#1e293b" stroke-width="1"/>')
        out.append(f'<text x="{px1-10}" y="{gy+4:.1f}" fill="#cbd5e1" font-size="11" text-anchor="end">{lv}</text>')

    for tv in range(7, 12):
        gy = ty2(tv)
        out.append(f'<line x1="{px2}" y1="{gy:.1f}" x2="{px2+pw}" y2="{gy:.1f}" stroke="#1e293b" stroke-width="1"/>')
        out.append(f'<text x="{px2-10}" y="{gy+4:.1f}" fill="#cbd5e1" font-size="11" text-anchor="end">10^{tv}</text>')

    hy = ty2(10.14)
    out.append(f'<line x1="{px2}" y1="{hy:.1f}" x2="{px2+pw}" y2="{hy:.1f}" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="5,4"/>')
    out.append(f'<text x="{px2+pw-10}" y="{hy-6:.1f}" fill="#cbd5e1" font-size="11" text-anchor="end">Age of Universe (Hubble Time ~ 13.8 Gyr)</text>')

    for z_val, col, _ in z_styles:
        sub = [m for m in data["models"] if abs(m["initial_z"] - z_val) < 1e-6]
        sub.sort(key=lambda x: x["initial_mass"])
        pts1 = [(tx1(math.log10(m["initial_mass"])), ty1(m["zams_summary"]["log_L"])) for m in sub]
        pts2 = [(tx2(math.log10(m["initial_mass"])), ty2(math.log10(m["zams_summary"]["t_ms"]))) for m in sub]

        d1 = " ".join(f"{'M' if i==0 else 'L'}{p[0]:.1f},{p[1]:.1f}" for i, p in enumerate(pts1))
        d2 = " ".join(f"{'M' if i==0 else 'L'}{p[0]:.1f},{p[1]:.1f}" for i, p in enumerate(pts2))
        out.append(f'<path d="{d1}" fill="none" stroke="{col}" stroke-width="2.4"/>')
        out.append(f'<path d="{d2}" fill="none" stroke="{col}" stroke-width="2.4"/>')
        for p1, p2 in zip(pts1, pts2):
            out.append(f'<circle cx="{p1[0]:.1f}" cy="{p1[1]:.1f}" r="4" fill="{col}"/>')
            out.append(f'<circle cx="{p2[0]:.1f}" cy="{p2[1]:.1f}" r="4" fill="{col}"/>')

    out.append(f'<text x="{px1+pw/2:.1f}" y="{py1+ph+44}" fill="#f8fafc" font-size="13" font-weight="bold" text-anchor="middle">Initial Mass M_init / M_sun (log scale)</text>')
    out.append(f'<text x="{px2+pw/2:.1f}" y="{py2+ph+44}" fill="#f8fafc" font-size="13" font-weight="bold" text-anchor="middle">Initial Mass M_init / M_sun (log scale)</text>')
    out.append(f'<text x="32" y="{py1+ph/2:.1f}" fill="#f8fafc" font-size="13" font-weight="bold" text-anchor="middle" transform="rotate(-90, 32, {py1+ph/2:.1f})">ZAMS Luminosity log10(L / L_sun)</text>')
    out.append(f'<text x="580" y="{py2+ph/2:.1f}" fill="#f8fafc" font-size="13" font-weight="bold" text-anchor="middle" transform="rotate(-90, 580, {py2+ph/2:.1f})">Main-Sequence Lifetime tau_MS (yr)</text>')

    ly = h - 32
    for i, (_, col, lbl) in enumerate(z_styles):
        lx = 115 + i * 245
        out.append(f'<line x1="{lx}" y1="{ly-4}" x2="{lx+30}" y2="{ly-4}" stroke="{col}" stroke-width="3"/>')
        out.append(f'<circle cx="{lx+15}" cy="{ly-4}" r="4" fill="{col}"/>')
        out.append(f'<text x="{lx+38}" y="{ly}" fill="#f8fafc" font-size="12" font-weight="bold">{lbl}</text>')

    out.append("</svg>")
    return "\n".join(out)


def convert_svg_to_png(svg_path: Path, png_path: Path, width: int, height: int) -> None:
    cmd = [
        "/usr/bin/google-chrome",
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        f"--window-size={width},{height}",
        f"--screenshot={png_path}",
        f"file://{svg_path.resolve()}",
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> None:
    workspace = Path("/workspace")
    fig_dir = workspace / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads((workspace / "stellar_grid_data.json").read_text(encoding="utf-8"))

    specs = [
        ("fig1_hr_diagram_grid", build_fig1_hr_diagram(data), 1120, 760),
        ("fig2_central_rho_T_phase", build_fig2_rho_T_phase(data), 1120, 740),
        ("fig3_kippenhahn_comparison", build_fig3_kippenhahn(data), 1150, 680),
        ("fig4_internal_profiles_stages", build_fig4_internal_profiles(data), 1150, 740),
        ("fig5_parameter_space_scaling", build_fig5_scaling_laws(data), 1150, 640),
    ]

    for name, svg_content, w, h in specs:
        svg_path = fig_dir / f"{name}.svg"
        png_path = fig_dir / f"{name}.png"
        svg_path.write_text(svg_content, encoding="utf-8")
        convert_svg_to_png(svg_path, png_path, w, h)
        print(f"[Generated] {svg_path.name} & {png_path.name}")


if __name__ == "__main__":
    main()
