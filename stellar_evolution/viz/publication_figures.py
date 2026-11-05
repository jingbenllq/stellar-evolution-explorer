"""
Publication-Grade 4-Panel Figure Pipeline for Stellar Simulation Data
=====================================================================
Generates publication-quality 4-panel scientific figures following the official
tutorial in `d:\\QQ\\MESA模拟数据科研绘图教程_py_mesa_reader.md`:
  Panel 1: Hertzsprung-Russell Diagram (log_Teff vs log_L, inverted x-axis)
  Panel 2: Central Hydrogen Depletion History (center_h1 vs star_age)
  Panel 3: Internal Density-Temperature Structure (loglog Rho vs T)
  Panel 4: Radial Chemical Abundance Distribution (mass coordinate q vs H, He, Z / isotopes)
Outputs both publication-ready vector PDF and high-resolution 300 DPI PNG figures.
"""

from pathlib import Path
from typing import Optional, Union
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ..mesa.native_parser import MesaLogDir


def generate_mesa_summary_4panel(
    logs_or_dir: Union[str, Path, MesaLogDir],
    output_dir: Optional[Union[str, Path]] = None,
    file_prefix: str = "mesa_summary",
    title_suffix: str = "",
) -> Path:
    """
    Generate 4-panel publication figure following py_mesa_reader scientific standards.

    Parameters:
        logs_or_dir: MesaLogDir instance or path to MESA LOGS directory
        output_dir: Target output folder (defaults to 'figures' next to log_dir)
        file_prefix: Prefix for saved figure filenames (e.g. mesa_summary)
        title_suffix: Optional label to append to figure titles

    Returns:
        Path to generated PNG figure
    """
    if isinstance(logs_or_dir, (str, Path)):
        logs = MesaLogDir(str(logs_or_dir))
    else:
        logs = logs_or_dir

    if output_dir is None:
        out_dir = Path(logs.log_dir).parent / "figures"
    else:
        out_dir = Path(output_dir)

    out_dir.mkdir(parents=True, exist_ok=True)

    h = logs.history
    h.remove_backups()

    fig, axs = plt.subplots(
        2, 2,
        figsize=(10.0, 8.0),
        constrained_layout=True,
    )

    # 1. HR Diagram
    ax = axs[0, 0]
    valid_hr = np.isfinite(h.log_Teff) & np.isfinite(h.log_L)
    ax.plot(
        h.log_Teff[valid_hr],
        h.log_L[valid_hr],
        color="#2563eb",
        lw=2.0,
        label="Evolution Track",
    )
    ax.invert_xaxis()
    ax.set_xlabel(r"$\log_{10}(T_{\rm eff}/{\rm K})$", fontsize=12)
    ax.set_ylabel(r"$\log_{10}(L/L_\odot)$", fontsize=12)
    ax.set_title(f"Hertzsprung-Russell Diagram {title_suffix}".strip(), fontsize=13)

    # 2. Central Hydrogen Evolution
    ax = axs[0, 1]
    age_yr = h.star_age
    max_age = float(np.nanmax(age_yr)) if len(age_yr) > 0 else 1.0
    if max_age > 1.0e8:
        age_plot = age_yr / 1.0e9
        age_unit = "Gyr"
    else:
        age_plot = age_yr / 1.0e6
        age_unit = "Myr"

    if "center_h1" in h:
        valid_ch = np.isfinite(h.center_h1)
        ax.plot(
            age_plot[valid_ch],
            h.center_h1[valid_ch],
            color="#d97706",
            lw=2.0,
            label=r"Central $X_{\rm H}$",
        )
        ax.set_ylabel(r"Central $X_{\rm H}$", fontsize=12)
        ax.set_ylim(-0.02, 1.02)
    elif "log_center_T" in h:
        ax.plot(
            age_plot,
            h.log_center_T,
            color="#d97706",
            lw=2.0,
            label=r"$\log_{10}(T_{\rm c})$",
        )
        ax.set_ylabel(r"$\log_{10}(T_{\rm c}/{\rm K})$", fontsize=12)
    else:
        ax.plot(
            age_plot,
            h.log_L,
            color="#d97706",
            lw=2.0,
            label=r"$\log_{10}(L)$",
        )
        ax.set_ylabel(r"$\log_{10}(L/L_\odot)$", fontsize=12)

    ax.set_xlabel(f"Age ({age_unit})", fontsize=12)
    ax.set_title(f"Core Evolution ({age_unit}) {title_suffix}".strip(), fontsize=13)

    # 3 & 4. Last Profile
    try:
        p = logs.profile_data()
        has_prof = True
    except Exception:
        has_prof = False
        p = None

    if has_prof and p is not None:
        # Panel 3: Temperature - Density Profile
        ax = axs[1, 0]
        if "Rho" in dir(p) and "T" in dir(p):
            ax.loglog(p.Rho, p.T, color="#0f766e", lw=1.8)
            ax.set_xlabel(r"Density (g cm$^{-3}$)", fontsize=12)
            ax.set_ylabel("Temperature (K)", fontsize=12)
        elif "logRho" in p and "logT" in p:
            ax.plot(p["logRho"], p["logT"], color="#0f766e", lw=1.8)
            ax.set_xlabel(r"$\log_{10}(\rho / {\rm g\,cm^{-3}})$", fontsize=12)
            ax.set_ylabel(r"$\log_{10}(T / {\rm K})$", fontsize=12)
        ax.set_title("Internal Temperature-Density Structure", fontsize=13)

        # Panel 4: Composition Profile
        ax = axs[1, 1]
        if "q" in p:
            q_arr = p["q"]
        elif "mass" in p and len(p["mass"]) > 0:
            m_0 = max(p["mass"])
            q_arr = p["mass"] / (m_0 if m_0 > 0 else 1.0)
        else:
            q_arr = np.linspace(1.0, 0.0, len(p.data(p.bulk_names[0])))

        order = np.argsort(q_arr)
        q_sorted = q_arr[order]

        plotted_any = False
        if "x_mass_fraction_H" in p:
            ax.plot(q_sorted, p.data("x_mass_fraction_H")[order], label="H", color="#2563eb", lw=1.8)
            plotted_any = True
        elif "h1" in p:
            ax.plot(q_sorted, p.data("h1")[order], label="H1", color="#2563eb", lw=1.8)
            plotted_any = True

        if "y_mass_fraction_He" in p:
            ax.plot(q_sorted, p.data("y_mass_fraction_He")[order], label="He", color="#d97706", lw=1.8)
            plotted_any = True
        elif "he4" in p:
            ax.plot(q_sorted, p.data("he4")[order], label="He4", color="#d97706", lw=1.8)
            plotted_any = True

        if "z_mass_fraction_metals" in p:
            ax.plot(q_sorted, p.data("z_mass_fraction_metals")[order], label="Z", color="#7c3aed", lw=1.8)
            plotted_any = True
        elif "c12" in p:
            ax.plot(q_sorted, p.data("c12")[order], label="C12", color="#22c55e", lw=1.8)
            if "o16" in p:
                ax.plot(q_sorted, p.data("o16")[order], label="O16", color="#38bdf8", lw=1.8)
            plotted_any = True

        if not plotted_any:
            ax.text(0.5, 0.5, "No composition columns in profile", ha="center", va="center")

        ax.set_xlabel(r"Mass coordinate $M_r/M_\star$", fontsize=12)
        ax.set_ylabel("Mass fraction", fontsize=12)
        ax.set_ylim(-0.02, 1.02)
        ax.set_title("Radial Chemical Profile", fontsize=13)
        ax.legend(frameon=False, fontsize=9.5)
    else:
        # Placeholder for profile subplots
        axs[1, 0].text(0.5, 0.5, "Profile data not available", ha="center", va="center")
        axs[1, 1].text(0.5, 0.5, "Profile data not available", ha="center", va="center")

    for a in axs.flat:
        a.tick_params(direction="in", top=True, right=True, labelsize=10)
        a.grid(alpha=0.25, lw=0.6, ls=":")

    png_path = out_dir / f"{file_prefix}.png"
    pdf_path = out_dir / f"{file_prefix}.pdf"

    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    return png_path
