"""
Static Diagnostic Visualizations for Stellar Evolution Parameter Space
======================================================================
Produces high-resolution static diagnostic figures for publication and documentation:
  1. HR Diagram parameter space (Z = 0.014 vs Z = 0.0001)
  2. Central Density - Temperature (Rho_c - T_c) phase space with degeneracy thresholds
  3. Multi-mass internal radial abundance profiles comparison
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

GRID_COLORS = {
    "0.3": "#f87171",
    "1.0": "#facc15",
    "3.0": "#4ade80",
    "5.0": "#2dd4bf",
    "8.0": "#38bdf8",
    "15.0": "#818cf8",
    "25.0": "#c084fc",
}

SPECIES_COLORS = {
    "H1": "#f97316",
    "He4": "#facc15",
    "C12": "#22c55e",
    "O16": "#38bdf8",
    "Ne20": "#06b6d4",
    "Si28": "#a855f7",
    "Fe56": "#e2e8f0",
}


def apply_dark_theme():
    """Apply dark astrophysical scientific aesthetic."""
    plt.rcParams["axes.facecolor"] = "#0b101d"
    plt.rcParams["figure.facecolor"] = "#090d16"
    plt.rcParams["text.color"] = "#e2e8f0"
    plt.rcParams["axes.labelcolor"] = "#cbd5e1"
    plt.rcParams["xtick.color"] = "#94a3b8"
    plt.rcParams["ytick.color"] = "#94a3b8"
    plt.rcParams["axes.edgecolor"] = "#334155"
    plt.rcParams["grid.color"] = "#1e293b"


def generate_hr_diagram_grid(data: Dict[str, Any], out_path: Path):
    """Plot full HR diagram grid comparing solar and low metallicity tracks."""
    apply_dark_theme()
    fig, ax = plt.subplots(figsize=(9, 6.5), dpi=180)
    for m_key, col in GRID_COLORS.items():
        mod_sol = data["models"]["0.014"][m_key]
        mod_low = data["models"]["0.0001"][m_key]
        ax.plot(
            mod_sol["track"]["log_Teff"],
            mod_sol["track"]["log_L"],
            color=col,
            lw=2.0,
            label=f"{m_key} M_sun (Z=0.014)",
        )
        ax.plot(
            mod_low["track"]["log_Teff"],
            mod_low["track"]["log_L"],
            color=col,
            lw=1.2,
            ls="--",
            alpha=0.65,
        )

    # Present-day Sun reference
    ax.scatter([3.7613], [0.0], color="#fde047", s=70, zorder=10, edgecolor="white", label="Present-day Sun (4.57 Gyr)")
    ax.set_xlim(4.90, 3.40)
    ax.set_ylim(-3.0, 5.6)
    ax.set_xlabel(r"$\log_{10}(T_{\rm eff} / {\rm K})$", fontsize=12)
    ax.set_ylabel(r"$\log_{10}(L / L_\odot)$", fontsize=12)
    ax.set_title("Hertzsprung-Russell Diagram Parameter Space (Solid: Z=0.014, Dashed: Z=0.0001)", fontsize=13)
    ax.grid(True, ls=":", alpha=0.5)
    ax.legend(loc="lower left", fontsize=8.5, facecolor="#111827", edgecolor="#334155")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def generate_rho_tc_phase_space(data: Dict[str, Any], out_path: Path):
    """Plot central density-temperature phase space with degeneracy boundaries."""
    apply_dark_theme()
    fig, ax = plt.subplots(figsize=(9, 6.5), dpi=180)
    for m_key, col in GRID_COLORS.items():
        mod = data["models"]["0.014"][m_key]
        ax.plot(mod["track"]["log_Rhoc"], mod["track"]["log_Tc"], color=col, lw=2.0, label=f"{m_key} M_sun")

    # Degeneracy boundary (slope 2/3 -> 1/3 at logRho = 6.3)
    r_nr = np.linspace(-0.5, 6.3, 50)
    r_ur = np.linspace(6.3, 10.0, 50)
    ax.plot(r_nr, (2.0 / 3.0) * r_nr + 4.38, "--", color="#fde047", lw=1.5, label="Electron Degeneracy (NR 2/3 -> UR 1/3)")
    ax.plot(r_ur, (1.0 / 3.0) * r_ur + 6.48, "--", color="#fde047", lw=1.5)

    ax.set_xlim(-0.5, 10.0)
    ax.set_ylim(6.4, 9.75)
    ax.set_xlabel(r"$\log_{10}(\rho_{\rm c} / {\rm g\,cm^{-3}})$", fontsize=12)
    ax.set_ylabel(r"$\log_{10}(T_{\rm c} / {\rm K})$", fontsize=12)
    ax.set_title("Central Temperature-Density Phase Space (Z = 0.014)", fontsize=13)
    ax.grid(True, ls=":", alpha=0.5)
    ax.legend(loc="upper left", fontsize=8.5, facecolor="#111827", edgecolor="#334155")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def generate_abundance_profiles_comparison(data: Dict[str, Any], out_path: Path):
    """Plot 3-panel comparison of radial chemical abundance profiles."""
    apply_dark_theme()
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.2), dpi=180, sharey=True)
    configs = [
        ("0.3", "1", "0.3 M_sun TAMS (Fully Convective Flat)"),
        ("1.0", "1", "1.0 M_sun TAMS (Radiative Core Step)"),
        ("15.0", "5", "15.0 M_sun Pre-CCSN (Onion-Skin)"),
    ]
    for ax_i, (m_k, st_k, title) in zip(axes, configs):
        prof = data["models"]["0.014"][m_k]["profiles"][st_k]
        for sp, col in SPECIES_COLORS.items():
            if max(prof[sp]) > 0.005:
                ax_i.plot(prof["q"], prof[sp], label=sp, color=col, lw=2.0)
        ax_i.set_title(title, fontsize=10)
        ax_i.set_xlabel(r"Normalized Mass Coordinate $q = m / M_\star$", fontsize=10)
        ax_i.set_xlim(0, 1)
        ax_i.set_ylim(0, 1.02)
        ax_i.grid(True, ls=":", alpha=0.5)
        ax_i.legend(loc="center right", fontsize=8, facecolor="#111827", edgecolor="#334155")

    axes[0].set_ylabel(r"Mass Fraction $X_i(q)$", fontsize=10)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def generate_all_diagnostic_figures(base_dir: Optional[Path] = None):
    """Generate all standard diagnostic figures from stellar_grid_data.json."""
    if base_dir is None:
        base = Path(__file__).resolve().parent.parent.parent
    else:
        base = Path(base_dir)

    json_path = base / "stellar_grid_data.json"
    if not json_path.is_file():
        from ..physics.evolution import build_full_grid
        build_full_grid(base)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    fig_dir = base / "figures"
    fig_dir.mkdir(exist_ok=True)

    generate_hr_diagram_grid(data, fig_dir / "hr_diagram_grid.png")
    generate_rho_tc_phase_space(data, fig_dir / "rho_tc_phase_space.png")
    generate_abundance_profiles_comparison(data, fig_dir / "abundance_profiles_comparison.png")
    print(f"Generated static diagnostic figures in {fig_dir}")
