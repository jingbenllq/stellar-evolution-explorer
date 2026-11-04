#!/usr/bin/env python3
"""
Generate High-Resolution Static Diagnostic Figures (v2.0 Physics Audited)
=========================================================================
Outputs publication-grade PNG figures into `figures/`:
  1. figures/hr_diagram_grid.png
  2. figures/rho_tc_phase_space.png
  3. figures/abundance_profiles_comparison.png
"""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["axes.facecolor"] = "#0b101d"
plt.rcParams["figure.facecolor"] = "#090d16"
plt.rcParams["text.color"] = "#e2e8f0"
plt.rcParams["axes.labelcolor"] = "#cbd5e1"
plt.rcParams["xtick.color"] = "#94a3b8"
plt.rcParams["ytick.color"] = "#94a3b8"
plt.rcParams["axes.edgecolor"] = "#334155"
plt.rcParams["grid.color"] = "#1e293b"

def main():
    base = Path(__file__).parent
    data = json.loads((base / "stellar_grid_data.json").read_text(encoding="utf-8"))
    fig_dir = base / "figures"
    fig_dir.mkdir(exist_ok=True)

    colors = {
        "0.3": "#f87171",
        "1.0": "#facc15",
        "3.0": "#4ade80",
        "5.0": "#2dd4bf",
        "8.0": "#38bdf8",
        "15.0": "#818cf8",
        "25.0": "#c084fc",
    }

    # 1. HR Diagram at Z = 0.014 vs Z = 0.0001
    fig, ax = plt.subplots(figsize=(9, 6.5), dpi=180)
    for m_key, col in colors.items():
        mod_sol = data["models"]["0.014"][m_key]
        mod_low = data["models"]["0.0001"][m_key]
        ax.plot(mod_sol["track"]["log_Teff"], mod_sol["track"]["log_L"], color=col, lw=2.0, label=f"{m_key} M_sun (Z=0.014)")
        ax.plot(mod_low["track"]["log_Teff"], mod_low["track"]["log_L"], color=col, lw=1.2, ls="--", alpha=0.65)
    ax.scatter([3.7613], [0.0], color="#fde047", s=70, zorder=10, edgecolor="white", label="Present-day Sun (4.57 Gyr)")
    ax.set_xlim(4.90, 3.40)
    ax.set_ylim(-3.0, 5.6)
    ax.set_xlabel("log10(T_eff / K)")
    ax.set_ylabel("log10(L / L_sun)")
    ax.set_title("Hertzsprung-Russell Diagram Parameter Space (Solid: Z=0.014, Dashed: Z=0.0001)")
    ax.grid(True, ls=":", alpha=0.5)
    ax.legend(loc="lower left", fontsize=8.5, facecolor="#111827", edgecolor="#334155")
    fig.tight_layout()
    fig.savefig(fig_dir / "hr_diagram_grid.png")
    plt.close(fig)

    # 2. Central Rho_c - T_c Phase Space
    fig, ax = plt.subplots(figsize=(9, 6.5), dpi=180)
    for m_key, col in colors.items():
        mod = data["models"]["0.014"][m_key]
        ax.plot(mod["track"]["log_Rhoc"], mod["track"]["log_Tc"], color=col, lw=2.0, label=f"{m_key} M_sun")
    # Degeneracy boundary (slope 2/3 -> 1/3 at logRho = 6.3)
    r_nr = np.linspace(-0.5, 6.3, 50)
    r_ur = np.linspace(6.3, 10.0, 50)
    ax.plot(r_nr, (2.0/3.0)*r_nr + 4.38, "--", color="#fde047", lw=1.5, label="Electron Degeneracy (NR 2/3 -> UR 1/3)")
    ax.plot(r_ur, (1.0/3.0)*r_ur + 6.48, "--", color="#fde047", lw=1.5)
    ax.set_xlim(-0.5, 10.0)
    ax.set_ylim(6.4, 9.75)
    ax.set_xlabel("log10(rho_c / g cm^-3)")
    ax.set_ylabel("log10(T_c / K)")
    ax.set_title("Central Temperature-Density Phase Space (Z = 0.014)")
    ax.grid(True, ls=":", alpha=0.5)
    ax.legend(loc="upper left", fontsize=8.5, facecolor="#111827", edgecolor="#334155")
    fig.tight_layout()
    fig.savefig(fig_dir / "rho_tc_phase_space.png")
    plt.close(fig)

    # 3. Radial Abundance Profiles Comparison (0.3 M_sun Flat vs 1.0 M_sun Step vs 15 M_sun Onion-Skin)
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.2), dpi=180, sharey=True)
    configs = [
        ("0.3", "1", "0.3 M_sun TAMS (Fully Convective Flat)"),
        ("1.0", "1", "1.0 M_sun TAMS (Radiative Core Step)"),
        ("15.0", "5", "15.0 M_sun Pre-CCSN (Onion-Skin)"),
    ]
    sp_cols = {"H1": "#f97316", "He4": "#facc15", "C12": "#22c55e", "O16": "#38bdf8", "Ne20": "#06b6d4", "Si28": "#a855f7", "Fe56": "#e2e8f0"}
    for ax_i, (m_k, st_k, title) in zip(axes, configs):
        prof = data["models"]["0.014"][m_k]["profiles"][st_k]
        for sp, col in sp_cols.items():
            if max(prof[sp]) > 0.005:
                ax_i.plot(prof["q"], prof[sp], label=sp, color=col, lw=2.0)
        ax_i.set_title(title, fontsize=10)
        ax_i.set_xlabel("Normalized Mass Coordinate q = m/M*")
        ax_i.set_xlim(0, 1)
        ax_i.set_ylim(0, 1.02)
        ax_i.grid(True, ls=":", alpha=0.5)
        ax_i.legend(loc="center right", fontsize=8, facecolor="#111827", edgecolor="#334155")
    axes[0].set_ylabel("Mass Fraction X_i(q)")
    fig.tight_layout()
    fig.savefig(fig_dir / "abundance_profiles_comparison.png")
    plt.close(fig)
    print("Generated static figures in", fig_dir)

if __name__ == "__main__":
    main()
