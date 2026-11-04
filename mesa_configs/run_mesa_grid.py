#!/usr/bin/env python3
"""
Automate MESA r24.03.1 Grid Setup Across (M_init, Z_init) Parameter Space
=========================================================================
Generates working directories and populated `inlist_project` files for all
28 models in MASS_GRID x METALLICITY_GRID.
"""
from pathlib import Path

MASS_GRID = [0.3, 1.0, 3.0, 5.0, 8.0, 15.0, 25.0]
METALLICITY_GRID = [0.0001, 0.001, 0.014, 0.03]

def prepare_grid_dirs(base_dir: Path):
    cfg_dir = base_dir / "mesa_configs"
    tpl_low = (cfg_dir / "inlist_template_low_intermediate").read_text(encoding="utf-8")
    tpl_high = (cfg_dir / "inlist_template_massive").read_text(encoding="utf-8")
    runs_dir = base_dir / "mesa_grid_runs"
    runs_dir.mkdir(exist_ok=True)

    for z in METALLICITY_GRID:
        for m in MASS_GRID:
            run_name = f"M{m:.1f}_Z{z}"
            target = runs_dir / run_name
            target.mkdir(exist_ok=True)
            tpl = tpl_high if m >= 10.0 else tpl_low
            inlist_content = tpl.replace("{INITIAL_MASS}", f"{m:.2f}d0").replace("{INITIAL_Z}", f"{z}d0")
            (target / "inlist_project").write_text(inlist_content, encoding="utf-8")
    print(f"Prepared 28 MESA run directories in {runs_dir}")

if __name__ == "__main__":
    prepare_grid_dirs(Path(__file__).resolve().parent.parent)
