#!/usr/bin/env python3
"""
Automated MESA Parameter Space Grid Builder & Runner
====================================================
Generates ready-to-run MESA directories (inlist_project, history_columns.list,
profile_columns.list) across the full (M_init, Z_init) stellar parameter space.
If MESA ($MESA_DIR) is installed on the host machine, passing `--execute` will
automatically compile and run `./rn` for each grid point.
"""

import argparse
import os
import shutil
import subprocess
from pathlib import Path

# Core Parameter Space Grid
MASS_GRID = [0.3, 1.0, 3.0, 5.0, 8.0, 15.0, 25.0]  # M_sun
METALLICITY_GRID = [0.0001, 0.001, 0.014, 0.03]    # Z mass fraction


def compute_helium_abundance(z: float) -> float:
    """Primordial He (Y_p = 0.247) + galactic chemical enrichment (dY/dZ = 1.54)."""
    return round(0.247 + 1.54 * z, 5)


def build_grid_directories(base_dir: Path, execute_mesa: bool = False) -> list[Path]:
    config_dir = Path(__file__).resolve().parent
    low_tpl = (config_dir / "inlist_template_low_intermediate").read_text(encoding="utf-8")
    high_tpl = (config_dir / "inlist_template_massive").read_text(encoding="utf-8")
    hist_cols = config_dir / "history_columns.list"
    prof_cols = config_dir / "profile_columns.list"

    runs_root = base_dir / "mesa_grid_runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    created_dirs = []

    for mass in MASS_GRID:
        for z in METALLICITY_GRID:
            # Generate full metallicity sweep for key masses (1.0, 3.0, 15.0 M_sun)
            # and solar metallicity (Z=0.014) + low-Z (Z=0.001) across all masses
            if z not in (0.014, 0.001) and mass not in (1.0, 3.0, 15.0):
                continue

            y = compute_helium_abundance(z)
            overshoot_f = 0.016 if mass >= 1.2 else 0.0
            tpl = high_tpl if mass >= 12.0 else low_tpl

            run_name = f"M{mass:04.1f}_Z{z:.4f}"
            run_dir = runs_root / run_name
            run_dir.mkdir(parents=True, exist_ok=True)

            inlist_content = tpl.format(
                INITIAL_MASS=f"{mass:.2f}d0",
                INITIAL_Z=f"{z:.5f}d0",
                INITIAL_Y=f"{y:.5f}d0",
                OVERSHOOT_F=f"{overshoot_f:.4f}d0",
            )
            (run_dir / "inlist_project").write_text(inlist_content, encoding="utf-8")
            shutil.copy2(hist_cols, run_dir / "history_columns.list")
            shutil.copy2(prof_cols, run_dir / "profile_columns.list")
            created_dirs.append(run_dir)

            if execute_mesa:
                mesa_dir = os.environ.get("MESA_DIR")
                if not mesa_dir:
                    raise RuntimeError("$MESA_DIR environment variable is not set.")
                print(f"[MESA] Running grid point {run_name}...")
                subprocess.run(["./rn"], cwd=run_dir, check=True)

    return created_dirs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build and optionally execute MESA parameter space grid.")
    parser.add_argument("--out-dir", type=Path, default=Path("/workspace"), help="Output root directory")
    parser.add_argument("--execute", action="store_true", help="Execute ./rn if MESA is installed")
    args = parser.parse_args()

    dirs = build_grid_directories(args.out_dir, execute_mesa=args.execute)
    print(f"Successfully generated {len(dirs)} MESA work directories under {args.out_dir / 'mesa_grid_runs'}")
