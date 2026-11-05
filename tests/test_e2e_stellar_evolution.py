#!/usr/bin/env python3
"""
Comprehensive End-to-End (E2E) Test Suite for Stellar Evolution Project
========================================================================
Covers all four testing tiers specified in TEST_INFRA.md and PROJECT.md:
  - Tier 1: Feature Coverage (F1 through F22, CLI entrypoints, parser, HTML outputs)
  - Tier 2: Boundary & Corner Cases (mass extremes 0.3 & 25 M_sun, Z extremes 0.0001 & 0.03,
            Fortran float parsing, empty/malformed logs, physical conservation laws)
  - Tier 3: Cross-Feature Integration Pipelines (MESA log -> StellarModel -> Figures -> HTML)
  - Tier 4: Real-World Astrophysics Application Scenarios (Solar lifecycle, 25 M_sun CCSN
            onion-skin, 8 M_sun metallicity fate bifurcation)
"""

import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Add PROJECT_ROOT to sys.path so modules can be imported directly
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Attempt imports of project modules (with graceful fallbacks for progressive testability)
try:
    import stellar_grid_engine as sge
except ImportError:
    sge = None

try:
    import memory_watchdog
except ImportError:
    memory_watchdog = None

from stellar_evolution.mesa.native_parser import parse_fortran_float, remove_backups
from stellar_evolution.core.exceptions import MesaParseError

try:
    from stellar_evolution.mesa import NativeMesaParser, MesaBridge
except ImportError:
    NativeMesaParser = None
    MesaBridge = None


# ==============================================================================
# Tier 1: Feature Coverage (Features F1 through F22)
# ==============================================================================

class TestTier1FeatureCoverage(unittest.TestCase):
    """
    Tier 1 tests cover the primary functional behavior and entrypoints of all
    features F1 through F22 defined in PROJECT.md.
    """

    @classmethod
    def setUpClass(cls):
        cls.data_file = PROJECT_ROOT / "stellar_grid_data.json"
        if cls.data_file.exists():
            cls.grid_data = json.loads(cls.data_file.read_text(encoding="utf-8"))
        else:
            cls.grid_data = None

    def test_f1_workspace_and_d_drive_structure(self):
        """Feature F1: Verify project root directories and D: drive structure."""
        # Project root essentials
        self.assertTrue((PROJECT_ROOT / "PROJECT.md").exists(), "PROJECT.md must exist at root")
        self.assertTrue((PROJECT_ROOT / "README.md").exists(), "README.md must exist at root")
        self.assertTrue((PROJECT_ROOT / "mesa_configs").is_dir(), "mesa_configs/ directory must exist")
        self.assertTrue((PROJECT_ROOT / "tests").is_dir(), "tests/ directory must exist")

        # Check D: drive workspace structure if running in Windows environment with D: available
        d_drive = Path("D:/")
        if d_drive.exists():
            d_work = Path("D:/天体物理导论")
            self.assertTrue(
                d_work.exists(),
                "D:/天体物理导论 workspace directory must exist when D: drive is mounted"
            )

    def test_f2_f4_mesa_configs_and_inlists(self):
        """Features F2 & F4: Verify MESA inlist templates and column definitions."""
        cfg_dir = PROJECT_ROOT / "mesa_configs"
        hist_cols = cfg_dir / "history_columns.list"
        prof_cols = cfg_dir / "profile_columns.list"
        inlist_low = cfg_dir / "inlist_template_low_intermediate"
        inlist_mass = cfg_dir / "inlist_template_massive"

        self.assertTrue(hist_cols.exists(), "history_columns.list must exist")
        self.assertTrue(prof_cols.exists(), "profile_columns.list must exist")
        self.assertTrue(inlist_low.exists(), "inlist_template_low_intermediate must exist")
        self.assertTrue(inlist_mass.exists(), "inlist_template_massive must exist")

        # Validate column list contents
        hist_text = hist_cols.read_text(encoding="utf-8")
        for col in ["model_number", "star_age", "log_L", "log_Teff", "log_R", "log_center_T", "log_center_Rho"]:
            self.assertIn(col, hist_text, f"history_columns.list must include standard column {col}")

        prof_text = prof_cols.read_text(encoding="utf-8")
        for col in ["zone", "mass", "q", "logT", "logRho", "h1", "he4", "c12", "o16", "fe56"]:
            self.assertIn(col, prof_text, f"profile_columns.list must include standard column {col}")

        # Validate template parameter placeholders
        low_text = inlist_low.read_text(encoding="utf-8")
        self.assertIn("{INITIAL_MASS}", low_text)
        self.assertIn("{INITIAL_Z}", low_text)

    def test_f3_memory_safety_guard(self):
        """Feature F3: Verify memory watchdog configuration and safety thresholds (<85% RAM)."""
        watchdog_path = PROJECT_ROOT / "memory_watchdog.py"
        self.assertTrue(watchdog_path.exists(), "memory_watchdog.py must exist at project root")

        import memory_watchdog as mw
        # Threshold invariants
        self.assertEqual(mw.WARNING_THRESHOLD_PERCENT, 80.0)
        self.assertEqual(mw.EMERGENCY_CEILING_PERCENT, 84.0)
        self.assertEqual(mw.ABSOLUTE_MAX_PERCENT, 85.0)

        # Host memory inspection
        wd = mw.MemoryWatchdog(emergency_threshold=100.0)
        status = wd.get_status()
        self.assertIn("percent", status)
        self.assertIn("safe", status)
        self.assertIn("total_bytes", status)
        self.assertIn("used_bytes", status)

        # Test threshold enforcement: must raise MemoryCeilingExceeded when threshold exceeded
        wd_emergency = mw.MemoryWatchdog(emergency_threshold=status["percent"] - 1.0)
        with self.assertRaises(mw.MemoryCeilingExceeded):
            wd_emergency.check_memory(auto_pause=False)

        # Normal operation below threshold must not raise
        wd_safe = mw.MemoryWatchdog(emergency_threshold=100.0)
        pct = wd_safe.check_memory()
        self.assertIsInstance(pct, float)

    def test_f6_native_mesa_parser_contract(self):
        """Feature F6: Verify NativeMesaParser contract using synthetic MESA logs."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            logs_dir = Path(tmp_dir) / "LOGS"
            logs_dir.mkdir()

            # Create synthetic history.data with Fortran D-notation, header info, and rollbacks
            hist_path = logs_dir / "history.data"
            hist_content = (
                "       1     2     3\n"
                " version_number initial_mass initial_z\n"
                "          26410  1.0000000000000000D+00  1.4000000000000000D-02\n"
                "\n"
                " model_number star_age log_L log_Teff log_R log_center_T log_center_Rho\n"
                "            1  1.0000000000000000D+05 -1.5500000000000000D-01  3.7613000000000000D+00 -5.1000000000000000D-02  7.1300000000000000D+00  1.9200000000000000D+00\n"
                "            2  2.0000000000000000D+05 -1.5400000000000000D-01  3.7614000000000000D+00 -5.0000000000000000D-02  7.1320000000000000D+00  1.9250000000000000D+00\n"
                "            3  3.0000000000000000D+05 -1.5300000000000000D-01  3.7615000000000000D+00 -4.9000000000000000D-02  7.1340000000000000D+00  1.9300000000000000D+00\n"
                "            2  2.1000000000000000D+05 -1.5400000000000000D-01  3.7614000000000000D+00 -5.0000000000000000D-02  7.1320000000000000D+00  1.9250000000000000D+00\n"
                "            3  3.1000000000000000D+05 -1.5300000000000000D-01  3.7615000000000000D+00 -4.9000000000000000D-02  7.1340000000000000D+00  1.9300000000000000D+00\n"
                "            4  4.0000000000000000D+05 -1.5200000000000000D-01  3.7616000000000000D+00 -4.8000000000000000D-02  7.1360000000000000D+00  1.9350000000000000D+00\n"
            )
            hist_path.write_text(hist_content, encoding="utf-8")

            # Create profiles.index
            idx_path = logs_dir / "profiles.index"
            idx_content = (
                " model_number priority profile_number\n"
                "            1        1              1\n"
                "            4        1              2\n"
            )
            idx_path.write_text(idx_content, encoding="utf-8")

            # Create profile1.data
            prof1_path = logs_dir / "profile1.data"
            prof1_content = (
                "       1     2     3\n"
                " model_number star_age star_mass\n"
                "            1  1.0000000000000000D+05  1.0000000000000000D+00\n"
                "\n"
                " zone mass q logR logT logRho h1 he4 c12 o16 ne20 si28 fe56\n"
                "    1  1.000000D+00  1.000000D+00 -5.100000D-02  3.761300D+00  1.000000D-07  7.000000D-01  2.800000D-01  3.000000D-03  9.000000D-03  2.000000D-03  7.000000D-04  1.300000D-03\n"
                "    2  5.000000D-01  5.000000D-01 -2.500000D-01  6.500000D+00  1.000000D+00  7.000000D-01  2.800000D-01  3.000000D-03  9.000000D-03  2.000000D-03  7.000000D-04  1.300000D-03\n"
                "    3  1.000000D-02  1.000000D-02 -9.000000D-01  7.130000D+00  1.920000D+00  7.000000D-01  2.800000D-01  3.000000D-03  9.000000D-03  2.000000D-03  7.000000D-04  1.300000D-03\n"
            )
            prof1_path.write_text(prof1_content, encoding="utf-8")

            # Test using NativeMesaParser if available, or reference parser verification
            if NativeMesaParser is not None:
                hist = NativeMesaParser.read_history(hist_path, remove_backups=True)
                self.assertIn("model_number", hist)
                self.assertIn("log_L", hist)
                self.assertEqual(len(hist["model_number"]), 4, "remove_backups must retain 4 monotonic models")
                self.assertEqual(list(hist["model_number"]), [1, 2, 3, 4])

                idx = NativeMesaParser.read_index(idx_path)
                self.assertEqual(len(idx), 2)

                prof = NativeMesaParser.read_profile(prof1_path)
                self.assertIn("h1", prof)
                self.assertEqual(len(prof["zone"]), 3)
            else:
                # Direct validation of the parsing contract
                lines = hist_path.read_text(encoding="utf-8").splitlines()
                cols = lines[4].split()
                self.assertIn("model_number", cols)
                self.assertIn("log_L", cols)
                raw_models = [int(line.split()[0]) for line in lines[5:] if line.strip()]
                cleaned_models = remove_mesa_backups(raw_models)
                self.assertEqual(cleaned_models, [1, 2, 3, 4])

    def test_f7_f8_unified_data_model_and_grid_engine(self):
        """Features F7 & F8: Verify the 28-model grid and unified StellarModel data structure."""
        self.assertIsNotNone(self.grid_data, "stellar_grid_data.json must exist")
        models = self.grid_data["models"]

        # Validate 4 metallicities and 7 masses = 28 models
        metallicities = list(models.keys())
        self.assertEqual(sorted(metallicities), ["0.0001", "0.001", "0.014", "0.03"])
        for z_k, z_models in models.items():
            masses = list(z_models.keys())
            self.assertEqual(
                sorted([float(m) for m in masses]),
                [0.3, 1.0, 3.0, 5.0, 8.0, 15.0, 25.0]
            )
            for m_k, mod in z_models.items():
                self.assertIn("zams", mod)
                self.assertIn("track", mod)
                self.assertIn("kippenhahn", mod)
                self.assertIn("profiles", mod)
                self.assertIn("pathway", mod)

                # Stages structure (supports both StellarModel 'stages' list and grid 'stage_names')
                if "stages" in mod:
                    self.assertEqual(len(mod["stages"]), 6, "Must define 6 evolutionary stage anchors")
                else:
                    self.assertIn("stage_names", mod)
                    self.assertEqual(len(mod["stage_names"]), 6, "Must define 6 evolutionary stage anchors")

                # Track arrays non-empty
                age_key = "age_yr" if "age_yr" in mod["track"] else "star_age"
                self.assertGreater(len(mod["track"][age_key]), 50)
                self.assertEqual(len(mod["track"][age_key]), len(mod["track"]["log_L"]))
                self.assertEqual(len(mod["track"][age_key]), len(mod["track"]["log_Teff"]))

    def test_f9_scientific_plotting_pipeline(self):
        """Feature F9: Verify scientific figure generation pipeline and outputs in figures/."""
        fig_dir = PROJECT_ROOT / "figures"
        fig_dir.mkdir(exist_ok=True)

        # Run generate_figures.py if figures are missing or to verify fresh generation
        f1 = fig_dir / "hr_diagram_grid.png"
        f2 = fig_dir / "rho_tc_phase_space.png"
        f3 = fig_dir / "abundance_profiles_comparison.png"

        if not (f1.exists() and f2.exists() and f3.exists()):
            proc = subprocess.run(
                [sys.executable, str(PROJECT_ROOT / "generate_figures.py")],
                capture_output=True,
                text=True,
                cwd=str(PROJECT_ROOT),
            )
            self.assertEqual(proc.returncode, 0, f"generate_figures.py failed: {proc.stderr}")

        for fig_path in [f1, f2, f3]:
            self.assertTrue(fig_path.exists(), f"Figure {fig_path.name} must exist")
            # Must be valid non-empty PNG
            size = fig_path.stat().st_size
            self.assertGreater(size, 10000, f"Figure {fig_path.name} size ({size}B) too small")
            with open(fig_path, "rb") as fp:
                header = fp.read(8)
                self.assertEqual(header, b"\x89PNG\r\n\x1a\n", f"Invalid PNG magic in {fig_path.name}")

    def test_f11_f12_f13_web_ui_dashboard(self):
        """Features F11, F12, F13: Verify web explorer dashboard and responsive layout."""
        index_html = PROJECT_ROOT / "index.html"
        explorer_html = PROJECT_ROOT / "stellar_explorer.html"

        self.assertTrue(index_html.exists(), "index.html must exist for GitHub Pages")
        self.assertTrue(explorer_html.exists(), "stellar_explorer.html must exist")

        content = index_html.read_text(encoding="utf-8")
        # Visual hierarchy & Material Dark theme
        self.assertIn('class="dark"', content)
        self.assertIn("three.min.js", content)

        # Canvas containers
        self.assertIn('id="hrCanvas"', content)
        self.assertIn('id="rhoTCanvas"', content)
        self.assertIn('id="onionCanvas"', content)
        self.assertIn('id="profCanvas"', content)

        # Telemetry HUD elements
        self.assertIn('id="mMassVal"', content)
        self.assertIn('id="mAgeVal"', content)
        self.assertIn('id="mTeffVal"', content)
        self.assertIn('id="mLumVal"', content)
        self.assertIn('id="mTcVal"', content)
        self.assertIn('id="mRhocVal"', content)
        self.assertIn('id="mBurningSub"', content)
        self.assertIn('id="mRemnantVal"', content)

    def test_f14_to_f19_onion_skin_visualizer(self):
        """Features F14-F19: Verify onion skin visualizer structure and interactive features."""
        content = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")

        # Species representation
        for sp in ["H1", "He4", "C12", "O16", "Ne20", "Si28", "Fe56"]:
            self.assertIn(sp, content, f"Onion skin visualizer must reference isotopic species {sp}")

        # Interactive controls & presentation modes
        self.assertIn("btnToggleCutaway", content, "Must include 3D cutaway toggle button")
        self.assertIn("onionContainer", content, "Must include onion container element")
        self.assertIn("onionHudInfo", content, "Must include onion HUD overlay element")

    def test_f21_f22_git_and_github_pages_deployment(self):
        """Features F21 & F22: Verify repository integrity and GitHub Pages workflow."""
        workflow_file = PROJECT_ROOT / ".github" / "workflows" / "pages.yml"
        self.assertTrue(workflow_file.exists(), ".github/workflows/pages.yml must exist")
        workflow_text = workflow_file.read_text(encoding="utf-8")
        self.assertIn("actions/deploy-pages", workflow_text)
        self.assertTrue((PROJECT_ROOT / "index.html").exists(), "index.html must be at root for Pages")


# ==============================================================================
# Tier 2: Boundary & Corner Cases
# ==============================================================================

class TestTier2BoundaryAndCornerCases(unittest.TestCase):
    """
    Tier 2 tests verify boundary conditions, extreme mass/metallicity values,
    malformed inputs, Fortran float edge cases, and strict physical conservation laws.
    """

    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((PROJECT_ROOT / "stellar_grid_data.json").read_text(encoding="utf-8"))

    def test_extreme_low_mass_03_msun_fully_convective(self):
        """Boundary: 0.3 M_sun star must be fully convective with ultra-long MS lifetime."""
        m03 = self.data["models"]["0.014"]["0.3"]

        # Lifetime > 500 Gyr
        self.assertGreater(m03["zams"]["t_ms"], 5.0e11)

        # Core temperature remains below helium burning threshold (log_Tc < 8.0)
        self.assertLess(max(m03["track"]["log_Tc"]), 8.0)

        # Uniform flat composition at TAMS due to convective mixing across entire star
        prof_tams = m03["profiles"]["1"]
        h1_vals = prof_tams["H1"]
        delta_h1 = max(h1_vals) - min(h1_vals)
        self.assertLess(delta_h1, 0.005, "0.3 M_sun TAMS must have flat radial abundance")

        # Endpoint is a Helium White Dwarf without supernova
        self.assertEqual(m03["pathway"]["remnant_code"], "He_WD")

    def test_extreme_high_mass_25_msun_massive_star(self):
        """Boundary: 25.0 M_sun star must have high luminosity, short lifetime, and iron core."""
        m25 = self.data["models"]["0.014"]["25.0"]

        # High luminosity at ZAMS
        self.assertGreater(m25["zams"]["log_L"], 4.70)

        # Rapid evolution: lifetime < 10 Myr
        self.assertLess(m25["zams"]["t_ms"], 1.0e7)

        # Advanced stage profile must have iron group synthesis in central core
        prof_late = m25["profiles"]["5"]
        # Innermost radial zone is q[0]
        fe_central = prof_late["Fe56"][0]
        self.assertGreater(fe_central, 0.50, "25 M_sun pre-CCSN must have dominant central Fe core")

        # Endpoint is core-collapse supernova yielding BH or NS
        self.assertIn(m25["pathway"]["remnant_code"], ["CCSN", "BH", "NS"])

    def test_extreme_metallicity_subsolar_vs_supersolar(self):
        """Boundary: Sub-solar (Z=0.0001) vs Super-solar (Z=0.03) opacity-driven divergence."""
        for m_str in ["0.3", "1.0", "3.0", "8.0", "25.0"]:
            mod_low = self.data["models"]["0.0001"][m_str]
            mod_high = self.data["models"]["0.03"][m_str]

            # Lower opacity at Z=0.0001 causes star to be hotter and more luminous at ZAMS
            self.assertGreater(
                mod_low["zams"]["log_L"],
                mod_high["zams"]["log_L"],
                f"Z=0.0001 must have higher log_L than Z=0.03 for M={m_str}"
            )
            self.assertGreater(
                mod_low["zams"]["log_Teff"],
                mod_high["zams"]["log_Teff"],
                f"Z=0.0001 must have higher log_Teff than Z=0.03 for M={m_str}"
            )
            self.assertLess(
                mod_low["zams"]["log_R"],
                mod_high["zams"]["log_R"],
                f"Z=0.0001 must be more compact (smaller log_R) than Z=0.03 for M={m_str}"
            )

    def test_fortran_float_parsing_corner_cases(self):
        """Corner Case: Parsing complex Fortran numeric notations with production parser."""
        # Standard Fortran D notation
        self.assertAlmostEqual(parse_fortran_float("1.23456789D+02"), 123.456789)
        self.assertAlmostEqual(parse_fortran_float("9.87654321D-05"), 0.0000987654321)
        self.assertAlmostEqual(parse_fortran_float("3.14159265d+00"), 3.14159265)

        # Missing E/D letter (compact exponent format e.g. '1.50000000-004')
        self.assertAlmostEqual(parse_fortran_float("1.50000000-004"), 0.00015)
        self.assertAlmostEqual(parse_fortran_float("-2.50000000+003"), -2500.0)

        # IEEE Special Values
        self.assertTrue(math.isnan(parse_fortran_float("NaN")))
        self.assertTrue(math.isinf(parse_fortran_float("+Infinity")))
        self.assertTrue(math.isinf(parse_fortran_float("-Inf")))

        # Empty and whitespace tokens return default 0.0 in production parser
        self.assertEqual(parse_fortran_float(""), 0.0)
        self.assertEqual(parse_fortran_float("   "), 0.0)

        # Malformed tokens raise MesaParseError
        with self.assertRaises(MesaParseError):
            parse_fortran_float("not_a_number")
        with self.assertRaises(MesaParseError):
            parse_fortran_float("1.2.3.4")

    def test_parser_rollback_and_empty_file_handling(self):
        """Corner Case: remove_backups algorithm and empty input handling."""
        # Rollback deduplication
        raw_models = [1, 2, 3, 4, 3, 4, 5, 4, 5, 6, 7]
        cleaned = remove_backups(raw_models)
        self.assertEqual(cleaned, [1, 2, 3, 4, 5, 6, 7])

        # Monotonic list unchanged
        self.assertEqual(remove_backups([10, 20, 30]), [10, 20, 30])

        # Severe rollback
        self.assertEqual(remove_backups([1, 2, 3, 1, 2]), [1, 2])

    def test_physical_conservation_and_stefan_boltzmann(self):
        """Physical Invariance: Strict mass fraction normalization and Stefan-Boltzmann law."""
        species = self.data["metadata"]["species"]
        sigma_sb_const = 3.7613  # log10(Teff) zero point for solar units

        for z_k, z_dict in self.data["models"].items():
            for m_k, mod in z_dict.items():
                # 1. Stefan-Boltzmann law consistency on ZAMS:
                # log_Teff == 3.7613 + 0.25 * log_L - 0.50 * log_R
                zams = mod["zams"]
                expected_teff = sigma_sb_const + 0.25 * zams["log_L"] - 0.50 * zams["log_R"]
                self.assertAlmostEqual(
                    zams["log_Teff"],
                    expected_teff,
                    places=3,
                    msg=f"Stefan-Boltzmann violated for M={m_k}, Z={z_k}"
                )

                # 2. Strict chemical abundance normalization: sum(X_i) == 1.0
                for st_k, prof in mod["profiles"].items():
                    for i in range(len(prof["q"])):
                        total_abundance = sum(prof[sp][i] for sp in species)
                        self.assertAlmostEqual(
                            total_abundance,
                            1.0,
                            places=2,
                            msg=f"Abundance not normalized to 1.0 at q[{i}] in M={m_k}, Z={z_k}, stage={st_k}"
                        )
                        # All abundances must be non-negative
                        for sp in species:
                            self.assertGreaterEqual(
                                prof[sp][i],
                                -1e-6,
                                f"Negative abundance {sp}={prof[sp][i]} in M={m_k}, Z={z_k}"
                            )

    def test_lifetime_monotonicity_with_mass(self):
        """Physical Invariance: Main sequence lifetime must strictly decrease with mass."""
        mass_order = [0.3, 1.0, 3.0, 5.0, 8.0, 15.0, 25.0]
        for z_k, z_dict in self.data["models"].items():
            lifetimes = [z_dict[str(m)]["zams"]["t_ms"] for m in mass_order]
            for i in range(len(lifetimes) - 1):
                self.assertGreater(
                    lifetimes[i],
                    lifetimes[i + 1],
                    f"Lifetime not monotonically decreasing between {mass_order[i]} and {mass_order[i+1]} M_sun at Z={z_k}"
                )


# ==============================================================================
# Tier 3: Cross-Feature Integration Pipelines
# ==============================================================================

class TestTier3CrossFeatureIntegration(unittest.TestCase):
    """
    Tier 3 tests verify full cross-feature workflows from data generation
    to diagnostic plotting and web explorer HTML compilation.
    """

    def test_end_to_end_data_to_visualization_pipeline(self):
        """Pipeline: stellar_grid_engine -> generate_figures -> build_explorer_html."""
        # 1. Run grid engine
        p_engine = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "stellar_grid_engine.py")],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        self.assertEqual(p_engine.returncode, 0, f"stellar_grid_engine failed: {p_engine.stderr}")
        grid_json = PROJECT_ROOT / "stellar_grid_data.json"
        self.assertTrue(grid_json.exists())

        # 2. Run figure generator
        p_figs = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "generate_figures.py")],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        self.assertEqual(p_figs.returncode, 0, f"generate_figures failed: {p_figs.stderr}")

        # 3. Run build HTML generator
        p_html = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "build_explorer_html.py")],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        self.assertEqual(p_html.returncode, 0, f"build_explorer_html failed: {p_html.stderr}")

        # Verify generated output files exist and are populated
        idx_path = PROJECT_ROOT / "index.html"
        exp_path = PROJECT_ROOT / "stellar_explorer.html"
        self.assertTrue(idx_path.exists())
        self.assertTrue(exp_path.exists())
        self.assertGreater(idx_path.stat().st_size, 100000)

    def test_html_artifact_parity(self):
        """Pipeline: index.html and stellar_explorer.html must be 100% byte-identical."""
        idx_bytes = (PROJECT_ROOT / "index.html").read_bytes()
        exp_bytes = (PROJECT_ROOT / "stellar_explorer.html").read_bytes()
        self.assertEqual(
            idx_bytes,
            exp_bytes,
            "index.html and stellar_explorer.html must be identical standalone builds"
        )

    def test_memory_safe_execution_watchdog(self):
        """Pipeline: Watchdog monitors host memory while running tasks, ensuring telemetry & guardrails."""
        import memory_watchdog as mw
        wd = mw.MemoryWatchdog(emergency_threshold=100.0)
        status_before = wd.get_status()
        self.assertIn("percent", status_before)
        self.assertIn("total_bytes", status_before)

        # Verify peak tracking and check_memory telemetry
        pct = wd.check_memory()
        self.assertIsInstance(pct, float)
        status_after = wd.get_status()
        self.assertIn("peak_percent", status_after)
        self.assertGreaterEqual(status_after["peak_percent"], status_before["percent"])


# ==============================================================================
# Tier 4: Real-World Astrophysics Application Scenarios
# ==============================================================================

class TestTier4RealWorldScenarios(unittest.TestCase):
    """
    Tier 4 tests validate real-world astrophysics scenarios:
      - Scenario 1: Solar Lifecycle (1.0 M_sun, Z=0.014) from ZAMS to White Dwarf
      - Scenario 2: Massive Star Supernova Progenitor (25.0 M_sun, Z=0.014) Onion Skin
      - Scenario 3: Metallicity-Induced Fate Bifurcation at 8.0 M_sun (ONe WD vs NS)
    """

    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((PROJECT_ROOT / "stellar_grid_data.json").read_text(encoding="utf-8"))

    def test_scenario_solar_full_lifecycle(self):
        """Scenario 1: Detailed physical audit of 1.0 M_sun solar benchmark evolution."""
        sun = self.data["models"]["0.014"]["1.0"]

        # 1. ZAMS Properties
        # Sun at zero age is fainter (~0.70 L_sun -> log_L = -0.155) and smaller (~0.89 R_sun -> log_R = -0.051)
        self.assertAlmostEqual(sun["zams"]["log_L"], -0.155, places=3)
        self.assertAlmostEqual(sun["zams"]["log_R"], -0.051, places=3)
        # Teff around 5600 K (log_Teff = 3.75)
        self.assertTrue(3.74 <= sun["zams"]["log_Teff"] <= 3.76)

        # 2. Main Sequence Lifetime
        # Calibrated to 10.0 Gyr (standard solar lifetime)
        self.assertTrue(9.5e9 <= sun["zams"]["t_ms"] <= 1.05e10)

        # 3. Evolution stages
        if "stages" in sun:
            stage_names = [st["name"] for st in sun["stages"]]
        else:
            stage_names = sun["stage_names"]
        self.assertIn("ZAMS", stage_names[0])
        self.assertIn("TAMS", stage_names[1])
        self.assertIn("RGB", stage_names[2])
        self.assertIn("CHeB", stage_names[3])
        self.assertIn("AGB", stage_names[4])

        # 4. RGB & Core Contraction
        # Central density increases from ZAMS to RGB by > 1.5 dex (degenerate He core contracts)
        zams_rhoc = sun["track"]["log_Rhoc"][0]
        rgb_step_idx = sun.get("stage_step_indices", [0, 40, 80, 119, 159, 199])[2]
        rgb_rhoc = sun["track"]["log_Rhoc"][rgb_step_idx]
        self.assertGreater(rgb_rhoc - zams_rhoc, 1.5)

        # 5. Remnant
        # Carbon-Oxygen White Dwarf with core mass around 0.55 - 0.65 M_sun
        self.assertEqual(sun["pathway"]["remnant_code"], "CO_WD")
        self.assertTrue(0.50 <= sun["pathway"]["remnant_mass"] <= 0.70)

    def test_scenario_massive_star_onion_skin(self):
        """Scenario 2: Detailed physical audit of 25.0 M_sun core-collapse onion skin."""
        star25 = self.data["models"]["0.014"]["25.0"]

        # 1. High energy output and short life
        self.assertGreater(star25["zams"]["log_L"], 4.70)
        self.assertLess(star25["zams"]["t_ms"], 8.0e6)

        # 2. Advanced Onion-Skin radial profile at stage 5 (Pre-supernova)
        prof = star25["profiles"]["5"]
        q_coords = prof["q"]
        n_pts = len(q_coords)

        # Innermost core (q ~ 0): Iron group dominant
        fe_core = prof["Fe56"][0]
        self.assertGreater(fe_core, 0.60, "Innermost core of 25 M_sun must be Fe-rich")

        # Intermediate zones: Si28 peak, O16 peak, C12 peak, He4 peak
        max_si = max(prof["Si28"])
        max_o = max(prof["O16"])
        max_c = max(prof["C12"])
        max_he = max(prof["He4"])
        max_h = max(prof["H1"])

        self.assertGreater(max_si, 0.40, "Silicon shell must be present")
        self.assertGreater(max_o, 0.50, "Oxygen shell must be present")
        self.assertGreater(max_c, 0.20, "Carbon shell must be present")
        self.assertGreater(max_he, 0.50, "Helium mantle must be present")
        self.assertGreater(max_h, 0.60, "Hydrogen envelope must be present")

        # Radial ordering check: Fe core is innermost, H envelope is outermost
        fe_idx = prof["Fe56"].index(max_fe := max(prof["Fe56"]))
        h_idx = prof["H1"].index(max_h)
        self.assertLess(q_coords[fe_idx], q_coords[h_idx], "Fe core must be inside H envelope")

        # 3. Supernova endpoint
        self.assertIn(star25["pathway"]["remnant_code"], ["CCSN", "BH", "NS"])

    def test_scenario_8msun_metallicity_fate_bifurcation(self):
        """Scenario 3: 8.0 M_sun bifurcation between ONe White Dwarf and Neutron Star."""
        m8_solar = self.data["models"]["0.014"]["8.0"]
        m8_lowz = self.data["models"]["0.0001"]["8.0"]

        # Solar metallicity: Stronger mass loss peels envelope -> ONe White Dwarf
        self.assertEqual(
            m8_solar["pathway"]["remnant_code"],
            "ONe_WD",
            "8.0 M_sun at solar Z must end as ONe White Dwarf"
        )

        # Low metallicity: Weaker mass loss retains core -> Core Collapse Supernova / Neutron Star
        self.assertEqual(
            m8_lowz["pathway"]["remnant_code"],
            "NS",
            "8.0 M_sun at low Z (0.0001) must end as Neutron Star"
        )


if __name__ == "__main__":
    unittest.main()
