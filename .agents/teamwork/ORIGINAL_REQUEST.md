# Original User Request

## Initial Request — 2026-11-04T23:23:03Z

Download and configure MESA in `D:\天体物理导论`, run the MESA stellar evolution simulation pipeline while strictly keeping system memory usage below 85%, comprehensively refactor the architecture of both the local Python programs and the web explorer, completely redesign the web UI for a cleaner and more aesthetic presentation, overhaul the stellar interior onion-skin diagram (洋葱图), and deploy the updated project to GitHub and GitHub Pages.

Working directory: C:/Users/廖敬本/.gemini/antigravity/scratch/stellar_evolution_project
Target D-drive directory: D:/天体物理导论
Integrity mode: development

## Context & Reference Materials
- Local repository path: `C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project`
- Target D-drive workspace: `D:\天体物理导论`
- Remote GitHub repository: `https://github.com/jingbenllq/stellar-evolution-explorer` (`main` branch)
- Live GitHub Pages URL: `https://jingbenllq.github.io/stellar-evolution-explorer/`
- Reference guides on disk:
  - `d:\QQ\MESA_26.4.1_中文安装与1太阳质量测试.md`
  - `d:\QQ\MESA模拟数据科研绘图教程_py_mesa_reader.md`
  - MESA SDK URL: `https://madstar.richtownsend.dev/static.php?ref=mesasdk`
  - MESA 26.4.1 Zenodo URL: `https://zenodo.org/records/19722306`

## Requirements

### R1. D:\天体物理导论 Workspace Setup, MESA Download & Memory-Safe Execution (< 85% RAM)
- Create and structure `D:\天体物理导论` on the D: drive.
- Download MESA / MESA SDK resources and set up the MESA environment and project files inside `D:\天体物理导论` following `d:\QQ\MESA_26.4.1_中文安装与1太阳质量测试.md` and `d:\QQ\MESA模拟数据科研绘图教程_py_mesa_reader.md` (using WSL2 Ubuntu if available and functional on this Windows host, or providing the full downloaded/configured MESA workspace, `LOGS/` data, and `py_mesa_reader` compatible simulation pipeline in `D:\天体物理导论`).
- Enforce a strict memory guard so system RAM usage never exceeds 85% during downloads, compilation, or simulation runs (`OMP_NUM_THREADS` / process memory monitoring).
- Synchronize the refactored code, generated data, figures, and documentation to both `D:\天体物理导论` and `C:\Users\廖敬本\.gemini\antigravity\scratch\stellar_evolution_project`.

### R2. Architectural Optimization of Local Programs & Data Pipeline
- Refactor the codebase (`stellar_grid_engine.py`, `build_explorer_html.py`, `generate_figures.py`, `mesa_configs/run_mesa_grid.py`, `py_mesa_reader` analysis scripts, and `tests/test_stellar_grid.py`) for clean modularity, maintainability, and strict physical accuracy.
- Support seamless ingestion of standard MESA `LOGS/history.data`, `LOGS/profiles.index`, and `LOGS/profile*.data` via `mesa_reader` / native parsers alongside the calibrated 28-model grid engine.

### R3. Complete Web UI Redesign (Aesthetic, Clean, Spectator-Friendly)
- Redesign the web dashboard (`stellar_explorer.html` and `index.html`) so that it looks modern, clean, uncluttered, and visually refined for an audience/spectator presentation.
- Improve visual hierarchy, spacing, typography, card layouts, color palette, responsive high-DPI canvas rendering, and interactive controls so the interface feels cohesive and effortless to read at a glance.

### R4. Overhaul of the Stellar Interior Onion-Skin Diagram (洋葱图重构)
- Completely redesign the stellar interior "Onion-Skin" visualization (洋葱图).
- Provide a clear, aesthetically refined, scientifically accurate cutaway/cross-section visual of the concentric nuclear burning shells ($\text{H} \to \text{He} \to \text{C} \to \text{Ne} \to \text{O} \to \text{Si} \to \text{Fe}$) and internal zones (convective vs. radiative regions, active nuclear burning ring glows, proportional visual clarity + true mass/radius coordinate mapping, chemical abundance callouts, and interactive hover/click layer inspection) across all stellar masses and evolutionary stages.

### R5. Verification, Git Sync & GitHub Pages Deployment
- Run and pass all unit and verification tests.
- Commit and push all updates to `https://github.com/jingbenllq/stellar-evolution-explorer` (`main` branch) and verify the live deployment at `https://jingbenllq.github.io/stellar-evolution-explorer/`.
