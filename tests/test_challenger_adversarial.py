#!/usr/bin/env python3
"""
Adversarial Challenge & Empirical Verification Test Suite
=========================================================
Target:
1. NativeMesaParser & MesaBridge:
   - Fortran float parsing fuzzing (extreme numbers, compact missing E, NaNs, Infs, malformed strings)
   - Malformed Fortran logs fuzzing (missing headers, truncated rows, jagged columns, empty files, NaNs)
   - remove_backups() stress testing under complex backtrack patterns (interleaved rollbacks, sawteeth, complete rewinds)
   - Large-scale array parser performance and memory consumption benchmark
   - MesaBridge handling of degraded/minimal profile data and schema validation
2. Physics Grid Engine:
   - 28 models continuity and monotonicity across initial mass and metallicity
   - Stefan-Boltzmann law universality across all 28 models, all 6 stages, and all 5,600 track steps
   - Radial chemical abundance conservation: sum(X_i) == 1.000 +/- 0.005 across all 10,080 radial sample points
"""

import io
import json
import math
import tempfile
import time
import unittest
from pathlib import Path
import numpy as np

from stellar_evolution.core.constants import L_sun, R_sun, SIGMA_SB_CGS, T_EFF_SUN
from stellar_evolution.core.schemas import HistoryData, ProfileData, ProfileInfo, StellarModel, StageModel, OnionShellModel
from stellar_evolution.core.exceptions import MesaParseError, MesaFormatError, ValidationError
from stellar_evolution.mesa.native_parser import parse_fortran_float, NativeMesaParser, MesaLogDir
from stellar_evolution.mesa.bridge import MesaBridge
from stellar_evolution.physics import (
    MASS_GRID,
    METALLICITY_GRID,
    STAGE_NAMES,
    SPECIES,
    zams_properties,
    classify_pathway,
    compute_stage_anchors,
    compute_kippenhahn_series,
    compute_abundance_profile,
    generate_track,
)


class TestFortranFloatAdversarial(unittest.TestCase):
    """Fuzzing and adversarial testing of parse_fortran_float()."""

    def test_extreme_numbers(self):
        """Test parsing of very large and very small Fortran floats."""
        # Near double-precision limits
        self.assertAlmostEqual(parse_fortran_float("1.000000D+300"), 1.0e300)
        self.assertAlmostEqual(parse_fortran_float("1.000000D-300"), 1.0e-300)
        self.assertAlmostEqual(parse_fortran_float("-1.000000D+300"), -1.0e300)
        self.assertAlmostEqual(parse_fortran_float("-1.000000D-300"), -1.0e-300)

        # Zero representations
        self.assertEqual(parse_fortran_float("0.000000D+00"), 0.0)
        self.assertEqual(parse_fortran_float("-0.000000D+00"), 0.0)
        self.assertEqual(parse_fortran_float("0.0D-99"), 0.0)

    def test_missing_exponent_letter_variations(self):
        """Test compact Fortran notation without 'E' or 'D'."""
        self.assertAlmostEqual(parse_fortran_float("1.234567-05"), 1.234567e-5)
        self.assertAlmostEqual(parse_fortran_float("9.876543+12"), 9.876543e12)
        self.assertAlmostEqual(parse_fortran_float("-3.141592-02"), -3.141592e-2)
        self.assertAlmostEqual(parse_fortran_float("-2.718281+03"), -2.718281e3)

    def test_special_floats_nan_inf(self):
        """Test parsing of NaN and Inf representations."""
        self.assertTrue(math.isnan(parse_fortran_float("NaN")))
        self.assertTrue(math.isnan(parse_fortran_float("nan")))
        self.assertTrue(math.isnan(parse_fortran_float("-NAN")))
        self.assertTrue(math.isinf(parse_fortran_float("Inf")))
        self.assertTrue(math.isinf(parse_fortran_float("-inf")))
        self.assertTrue(math.isinf(parse_fortran_float("Infinity")))
        self.assertTrue(math.isinf(parse_fortran_float("-Infinity")))

    def test_whitespace_and_quotes(self):
        """Test string sanitization with spaces and surrounding quotes."""
        self.assertEqual(parse_fortran_float(""), 0.0)
        self.assertEqual(parse_fortran_float("   "), 0.0)
        self.assertAlmostEqual(parse_fortran_float('  "1.2345D+02"  '), 123.45)
        self.assertAlmostEqual(parse_fortran_float("  '-9.876D-01'  "), -0.9876)

    def test_malformed_inputs_raise_mesa_parse_error(self):
        """Verify that truly invalid strings raise MesaParseError."""
        invalid_tokens = [
            "1.2.3",
            "12D34E56",
            "abc",
            "1.0D+abc",
            "++1.0",
            "--2.5",
            "1.0 D+02",
        ]
        for token in invalid_tokens:
            with self.assertRaises(MesaParseError, msg=f"Failed to raise MesaParseError on token '{token}'"):
                parse_fortran_float(token)


class TestNativeMesaParserFuzzing(unittest.TestCase):
    """Stress testing NativeMesaParser with malformed, partial, and noisy Fortran files."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_missing_header_block_bulk_only(self):
        """Parser should handle files with only one block (bulk data, no header)."""
        bulk_only_path = self.dir_path / "bulk_only.data"
        content = (
            "                   1                    2                    3\n"
            "        model_number             star_age                log_L\n"
            "                   1         1.000000D+05        -1.550000D-01\n"
            "                   2         2.000000D+05        -1.540000D-01\n"
        )
        bulk_only_path.write_text(content, encoding="utf-8")
        headers, data = NativeMesaParser._parse_mesa_ascii_table(bulk_only_path)
        self.assertEqual(len(headers), 0)
        self.assertIn("model_number", data)
        self.assertEqual(len(data["model_number"]), 2)
        self.assertEqual(data["model_number"][0], 1)
        self.assertEqual(data["model_number"][1], 2)

    def test_completely_empty_and_comment_only_files(self):
        """Parser returns empty headers and data on empty or comments-only files."""
        empty_path = self.dir_path / "empty.data"
        empty_path.write_text("", encoding="utf-8")
        headers, data = NativeMesaParser._parse_mesa_ascii_table(empty_path)
        self.assertEqual(headers, {})
        self.assertEqual(data, {})

        comments_path = self.dir_path / "comments.data"
        comments_path.write_text("! line 1\n! line 2\n! line 3\n", encoding="utf-8")
        headers_c, data_c = NativeMesaParser._parse_mesa_ascii_table(comments_path)
        self.assertEqual(headers_c, {})
        self.assertEqual(data_c, {})

    def test_jagged_and_truncated_rows_resilience(self):
        """Parser should skip rows that have fewer columns than header and truncate excess."""
        jagged_path = self.dir_path / "jagged.data"
        content = (
            "                  1                   2\n"
            "            version            compiler\n"
            "           24.03.11            gfortran\n"
            "\n"
            "                   1                    2                    3\n"
            "        model_number             star_age                log_L\n"
            "                   1         1.000000D+05        -1.550000D-01\n"
            "                   2         2.000000D+05\n"  # Truncated row: only 2 tokens -> should skip
            "                   3         3.000000D+05        -1.530000D-01        9.999999D+99\n"  # Excess tokens: 4 tokens -> should take first 3
            "                   4         4.000000D+05        -1.520000D-01\n"
        )
        jagged_path.write_text(content, encoding="utf-8")
        headers, data = NativeMesaParser._parse_mesa_ascii_table(jagged_path)
        self.assertEqual(headers["version"], "24.03.11")
        self.assertIn("model_number", data)
        # Should have kept rows 1, 3, 4 (skipping row 2)
        self.assertEqual(list(data["model_number"]), [1, 3, 4])
        self.assertEqual(len(data["star_age"]), 3)
        self.assertAlmostEqual(data["log_L"][1], -0.153)

    def test_embedded_nan_and_inf_in_history_bulk(self):
        """Parser must correctly ingest NaN and Inf tokens without raising exceptions."""
        nan_path = self.dir_path / "nan_history.data"
        content = (
            "                  1\n"
            "            version\n"
            "           24.03.11\n"
            "\n"
            "                   1                    2                    3\n"
            "        model_number                log_L             log_Teff\n"
            "                   1                  NaN                  Inf\n"
            "                   2        -1.550000D-01        3.761300D+00\n"
            "                   3                 -Inf                 -NaN\n"
        )
        nan_path.write_text(content, encoding="utf-8")
        hist = NativeMesaParser.read_history(nan_path, remove_backups=False)
        self.assertTrue(math.isnan(hist.data("log_L")[0]))
        self.assertTrue(math.isinf(hist.data("log_Teff")[0]))
        self.assertAlmostEqual(hist.data("log_L")[1], -0.155)
        self.assertTrue(math.isinf(hist.data("log_L")[2]))
        self.assertTrue(math.isnan(hist.data("log_Teff")[2]))

    def test_malformed_profiles_index_handling(self):
        """profiles.index with irregular spaces, extra comments, and non-numeric rows."""
        idx_path = self.dir_path / "profiles.index"
        content = (
            "! header comment\n"
            "  random unformatted text line\n"
            "        model_number              priority        profile_number\n"
            "                   1                     1                     1\n"
            "             corrupted                   1                     2\n"  # corrupt model_number
            "                   5                     1             corrupted\n"  # corrupt profile_number
            "                  10                     2                     3\n"
        )
        idx_path.write_text(content, encoding="utf-8")
        profiles = NativeMesaParser.read_index(idx_path)
        self.assertEqual(len(profiles), 2)
        self.assertEqual(profiles[0].model_number, 1)
        self.assertEqual(profiles[0].profile_number, 1)
        self.assertEqual(profiles[1].model_number, 10)
        self.assertEqual(profiles[1].profile_number, 3)


class TestRemoveBackupsStress(unittest.TestCase):
    """Exhaustive testing of remove_backups() backward-scan deduplication under hostile rollback scenarios."""

    def _make_hist(self, model_numbers: list) -> HistoryData:
        n = len(model_numbers)
        data = {
            "model_number": np.array(model_numbers, dtype=int),
            "step_id": np.arange(n, dtype=int),
            "star_age": np.linspace(1e5, 1e6, n),
        }
        return HistoryData(headers={}, data=data)

    def test_strictly_monotonic_unaltered(self):
        """Clean trajectory without any retries must remain untouched."""
        mn = [1, 2, 3, 4, 5, 6, 7]
        hist = self._make_hist(mn).remove_backups()
        self.assertEqual(list(hist["model_number"]), mn)
        self.assertEqual(list(hist["step_id"]), list(range(len(mn))))

    def test_single_backtrack(self):
        """Standard MESA retry: 1, 2, 3, 4, retry back to 3, 4, 5."""
        mn = [1, 2, 3, 4, 3, 4, 5]
        hist = self._make_hist(mn).remove_backups()
        # Should keep 1, 2 from first leg, and 3, 4, 5 from second leg
        self.assertEqual(list(hist["model_number"]), [1, 2, 3, 4, 5])
        self.assertEqual(list(hist["step_id"]), [0, 1, 4, 5, 6])

    def test_interleaved_sawtooth_rollbacks(self):
        """Repeated numerical convergence failures producing sawtooth backtracks."""
        # Timeline:
        # [1, 2, 3, 2, 3, 4, 3, 4, 5, 4, 5, 6]
        mn = [1, 2, 3, 2, 3, 4, 3, 4, 5, 4, 5, 6]
        hist = self._make_hist(mn).remove_backups()
        res = list(hist["model_number"])
        # Must be strictly monotonically increasing:
        for a, b in zip(res[:-1], res[1:]):
            self.assertLess(a, b, f"remove_backups produced non-monotonic sequence: {res}")
        self.assertEqual(res, [1, 2, 3, 4, 5, 6])
        # Verify step_id reflects the latest iterations:
        self.assertEqual(list(hist["step_id"]), [0, 3, 6, 9, 10, 11])

    def test_severe_catastrophic_rewind(self):
        """Simulation rewound all the way back to step 1 from step 10."""
        mn = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5]
        hist = self._make_hist(mn).remove_backups()
        # The later run rewound to 1..5, so the entire previous run 1..10 must be discarded
        self.assertEqual(list(hist["model_number"]), [1, 2, 3, 4, 5])
        self.assertEqual(list(hist["step_id"]), [10, 11, 12, 13, 14])

    def test_consecutive_duplicates(self):
        """Same model number repeated multiple times during zero-timestep backup."""
        mn = [1, 2, 2, 2, 3, 3, 4]
        hist = self._make_hist(mn).remove_backups()
        self.assertEqual(list(hist["model_number"]), [1, 2, 3, 4])
        # Must retain the LAST instance of 2 (index 3) and 3 (index 5)
        self.assertEqual(list(hist["step_id"]), [0, 3, 5, 6])

    def test_all_identical_steps(self):
        """All models identical: should collapse to exactly 1 point (the last)."""
        mn = [42, 42, 42, 42]
        hist = self._make_hist(mn).remove_backups()
        self.assertEqual(list(hist["model_number"]), [42])
        self.assertEqual(list(hist["step_id"]), [3])

    def test_inverted_descending_steps(self):
        """Pathological descending model numbers: should collapse to only the last element."""
        mn = [10, 9, 8, 7, 6, 5]
        hist = self._make_hist(mn).remove_backups()
        self.assertEqual(list(hist["model_number"]), [5])
        self.assertEqual(list(hist["step_id"]), [5])

    def test_empty_and_single_element(self):
        """Boundary cases: 0 elements and 1 element."""
        empty_hist = self._make_hist([]).remove_backups()
        self.assertEqual(len(empty_hist["model_number"]), 0)

        single_hist = self._make_hist([99]).remove_backups()
        self.assertEqual(list(single_hist["model_number"]), [99])

    def test_data_at_model_number_behavior(self):
        """Verify data_at_model_number correctly resolves values and raises ValueError for missing steps."""
        hist = self._make_hist([1, 2, 3, 2, 3, 4]).remove_backups()
        # Should resolve existing steps
        age_4 = hist.data_at_model_number("star_age", 4)
        self.assertGreater(age_4, 0.0)

        # Missing step should raise ValueError
        with self.assertRaises(ValueError):
            hist.data_at_model_number("star_age", 999)

        # Missing column should raise KeyError
        with self.assertRaises(KeyError):
            hist.data_at_model_number("nonexistent_column", 4)

    def test_corrupted_model_number_backups(self):
        """Verify behavior when model_number contains negative or extreme integer tokens."""
        # Extreme negative step at end
        mn_neg = [1, 2, 3, -100]
        hist_neg = self._make_hist(mn_neg).remove_backups()
        # Because -100 is smaller than all preceding, it keeps ONLY -100
        self.assertEqual(list(hist_neg["model_number"]), [-100])


class TestParserScaleAndPerformance(unittest.TestCase):
    """Stress testing parser speed and memory scaling under large simulated datasets."""

    def test_large_array_history_parsing_and_backups(self):
        """Test parsing and backup removal on a 30,000-step synthetic log (~15 MB)."""
        temp_dir = tempfile.TemporaryDirectory()
        try:
            log_path = Path(temp_dir.name) / "big_history.data"
            n_rows = 30000
            n_cols = 10

            col_names = ["model_number", "star_age", "star_mass", "log_L", "log_Teff",
                         "log_R", "log_center_T", "log_center_Rho", "he4", "c12"]

            # Generate synthetic data with periodic rollbacks every 500 steps
            model_nums = []
            cur_m = 1
            for i in range(n_rows):
                if i > 0 and i % 500 == 0:
                    cur_m = max(1, cur_m - 30)  # Rollback 30 steps
                model_nums.append(cur_m)
                cur_m += 1

            lines = [
                " 1 2 3",
                " version compiler build",
                ' "24.03" "gfortran" "native"',
                "",
                " ".join([f"{i+1}" for i in range(n_cols)]),
                " ".join(col_names),
            ]

            for i in range(n_rows):
                mn = model_nums[i]
                age = 1e5 + i * 1e3
                line = f"{mn} {age:.6E} 1.000000E+00 -1.550000E-01 3.761300E+00 -5.100000E-02 7.150000E+00 1.950000E+00 2.800000E-01 2.000000E-02"
                lines.append(line)

            t0 = time.perf_counter()
            log_path.write_text("\n".join(lines), encoding="utf-8")
            t_write = time.perf_counter() - t0

            # Measure parser time
            t1 = time.perf_counter()
            hist = NativeMesaParser.read_history(log_path, remove_backups=True)
            t_parse = time.perf_counter() - t1

            # Performance assertions
            self.assertLess(t_parse, 4.0, f"Parser too slow on 30,000 rows: took {t_parse:.3f}s")
            self.assertGreater(len(hist["model_number"]), 0)
            self.assertLess(len(hist["model_number"]), n_rows)  # Backups removed

            # Monotonicity check
            mn_arr = hist["model_number"]
            diffs = np.diff(mn_arr)
            self.assertTrue(np.all(diffs > 0), "Backups were not completely removed in large dataset")

        finally:
            temp_dir.cleanup()


class TestMesaBridgeAdversarial(unittest.TestCase):
    """Adversarial testing of MesaBridge schema transformation and model validation."""

    def test_minimal_profile_without_isotopes(self):
        """Bridge should handle profile lacking detailed isotope columns."""
        headers = {"model_number": 1, "star_age": 1e5, "log_L": 0.0, "log_Teff": 3.76}
        # Only mass, radius, temperature, density
        data = {
            "q": np.array([1.0, 0.5, 0.0]),
            "logT": np.array([3.8, 6.5, 7.1]),
            "logRho": np.array([-6.0, 1.0, 2.0]),
        }
        prof = ProfileData(headers=headers, data=data)
        shells = MesaBridge._build_shells_from_profile(prof)
        self.assertGreaterEqual(len(shells), 1)
        self.assertEqual(shells[0].q_inner, 0.0)
        self.assertEqual(shells[-1].q_outer, 1.0)

    def test_reversed_radial_coordinate_profile(self):
        """Profile with q from surface (1.0) to center (0.0) must be automatically sorted."""
        headers = {"model_number": 1}
        data = {
            "q": np.array([1.0, 0.75, 0.5, 0.25, 0.0]),
            "h1": np.array([0.7, 0.7, 0.7, 0.1, 0.0]),
            "he4": np.array([0.28, 0.28, 0.28, 0.88, 0.98]),
            "logT": np.array([3.7, 5.0, 6.0, 7.0, 7.5]),
            "logRho": np.array([-5.0, -2.0, 0.5, 1.5, 2.5]),
        }
        prof = ProfileData(headers=headers, data=data)
        shells = MesaBridge._build_shells_from_profile(prof)
        # Verify concentric ordering from center (0) to surface (1)
        for s in shells:
            self.assertLessEqual(s.q_inner, s.q_outer)
        self.assertEqual(shells[0].q_inner, 0.0)
        self.assertEqual(shells[-1].q_outer, 1.0)

    def test_validate_stellar_model_failures(self):
        """Verify that invalid models trigger ValidationError."""
        # 1. Non-positive mass
        m_bad = StellarModel(mass=-1.0, metallicity=0.014, stages=[StageModel("ZAMS", 0.0, 0.0, 3.76, 1.0)])
        with self.assertRaises(ValidationError):
            MesaBridge.validate_stellar_model(m_bad)

        # 2. Out-of-bounds metallicity
        m_bad_z = StellarModel(mass=1.0, metallicity=0.25, stages=[StageModel("ZAMS", 0.0, 0.0, 3.76, 1.0)])
        with self.assertRaises(ValidationError):
            MesaBridge.validate_stellar_model(m_bad_z)

        # 3. Empty stages
        m_empty = StellarModel(mass=1.0, metallicity=0.014, stages=[])
        with self.assertRaises(ValidationError):
            MesaBridge.validate_stellar_model(m_empty)

        # 4. Inverted shell coordinates (q_inner > q_outer)
        bad_shell = OnionShellModel("core", "He", q_inner=0.8, q_outer=0.2, r_inner_norm=0.8, r_outer_norm=0.2,
                                    is_convective=False, burning_active=False, burning_reaction="None",
                                    temperature_K=1e7, density_cgs=1.0)
        stage_bad_shell = StageModel("ZAMS", 0.0, 0.0, 3.76, 1.0, onion_shells=[bad_shell])
        m_bad_shell = StellarModel(mass=1.0, metallicity=0.014, stages=[stage_bad_shell])
        with self.assertRaises(ValidationError):
            MesaBridge.validate_stellar_model(m_bad_shell)


class TestPhysicsGridEngine28Models(unittest.TestCase):
    """Exhaustive empirical validation of all 28 parameter space models."""

    @classmethod
    def setUpClass(cls):
        cls.models = {}
        for z in METALLICITY_GRID:
            for m in MASS_GRID:
                cls.models[(m, z)] = generate_track(m, z, n_steps=200)

    def test_all_28_models_exist_and_conform(self):
        """Verify exactly 28 models are generated with full data tracks."""
        self.assertEqual(len(self.models), 28)
        for (m, z), model in self.models.items():
            self.assertEqual(model["mass_init"], m)
            self.assertEqual(model["z_init"], z)
            self.assertIn("track", model)
            self.assertIn("stages", model)
            self.assertEqual(len(model["stages"]), 6)
            self.assertEqual(len(model["track"]["s"]), 200)

    def test_zams_mass_monotonicity_all_metallicities(self):
        """At any metallicity, ZAMS Luminosity and Radius must be strictly monotonically increasing with Mass."""
        for z in METALLICITY_GRID:
            lums = []
            radii = []
            t_cores = []
            lifetimes = []
            for m in MASS_GRID:
                props = zams_properties(m, z)
                lums.append(props["log_L"])
                radii.append(props["log_R"])
                t_cores.append(props["log_Tc"])
                lifetimes.append(props["t_ms"])

            # Luminosity strictly increasing
            for i in range(len(lums) - 1):
                self.assertLess(
                    lums[i], lums[i + 1],
                    f"Z={z}: L_ZAMS non-monotonic between M={MASS_GRID[i]} and M={MASS_GRID[i+1]}"
                )

            # Radius strictly increasing
            for i in range(len(radii) - 1):
                self.assertLess(
                    radii[i], radii[i + 1],
                    f"Z={z}: R_ZAMS non-monotonic between M={MASS_GRID[i]} and M={MASS_GRID[i+1]}"
                )

            # Central Temperature strictly increasing
            for i in range(len(t_cores) - 1):
                self.assertLess(
                    t_cores[i], t_cores[i + 1],
                    f"Z={z}: Tc_ZAMS non-monotonic between M={MASS_GRID[i]} and M={MASS_GRID[i+1]}"
                )

            # Main Sequence Lifetime strictly decreasing
            for i in range(len(lifetimes) - 1):
                self.assertGreater(
                    lifetimes[i], lifetimes[i + 1],
                    f"Z={z}: t_ms non-decreasing between M={MASS_GRID[i]} and M={MASS_GRID[i+1]}"
                )

    def test_zams_metallicity_monotonicity_all_masses(self):
        """At fixed mass, lower metallicity (lower opacity) must yield higher ZAMS Luminosity."""
        for m in MASS_GRID:
            prev_lum = float("inf")
            for z in METALLICITY_GRID:
                props = zams_properties(m, z)
                curr_lum = props["log_L"]
                # Higher Z -> higher opacity -> lower L
                self.assertLess(
                    curr_lum, prev_lum,
                    f"M={m}: L_ZAMS did not decrease with increasing Z (Z={z})"
                )
                prev_lum = curr_lum

    def test_track_age_monotonicity_all_28_models(self):
        """Stellar age must be monotonically non-decreasing along all 200 track points for all 28 models."""
        for (m, z), model in self.models.items():
            ages = model["track"]["age_yr"]
            for i in range(len(ages) - 1):
                self.assertGreaterEqual(
                    ages[i + 1], ages[i] - 1e-6,
                    f"Model M={m} Z={z} violates age monotonicity at step {i}: {ages[i]} > {ages[i+1]}"
                )


class TestStefanBoltzmannUniversality(unittest.TestCase):
    """Rigorous empirical validation of Stefan-Boltzmann law across the entire parameter space."""

    def test_stefan_boltzmann_all_28_models_at_zams(self):
        """Verify SB law holds to within 0.05% across all 28 ZAMS models."""
        for z in METALLICITY_GRID:
            for m in MASS_GRID:
                props = zams_properties(m, z)
                log_L = props["log_L"]
                log_R = props["log_R"]
                log_Teff = props["log_Teff"]

                # Stefan-Boltzmann in solar logarithmic units:
                # log_Teff = log10(5772) + 0.25 * log_L - 0.50 * log_R
                expected_log_Teff = 3.761326 + 0.25 * log_L - 0.50 * log_R
                diff = abs(log_Teff - expected_log_Teff)
                self.assertLess(
                    diff, 0.0005,
                    f"ZAMS model M={m} Z={z} violates Stefan-Boltzmann: diff={diff:.6f} dex"
                )

    def test_stefan_boltzmann_all_168_stages(self):
        """Verify SB law across all 6 stages of all 28 models (168 evolutionary stages)."""
        for z in METALLICITY_GRID:
            for m in MASS_GRID:
                model = generate_track(m, z, n_steps=200)
                for stage in model["stages"]:
                    log_L = stage["log_L"]
                    log_Teff = stage["log_Teff"]
                    radius_Rsun = stage["radius_Rsun"]
                    log_R = math.log10(radius_Rsun)

                    expected_log_Teff = 3.761326 + 0.25 * log_L - 0.50 * log_R
                    diff = abs(log_Teff - expected_log_Teff)
                    self.assertLess(
                        diff, 0.001,
                        f"Stage {stage['name']} in model M={m} Z={z} violates SB: diff={diff:.6f} dex"
                    )

    def test_stefan_boltzmann_all_5600_track_steps(self):
        """Verify SB consistency across every individual track step (28 models x 200 steps = 5,600 points)."""
        for z in METALLICITY_GRID:
            for m in MASS_GRID:
                model = generate_track(m, z, n_steps=200)
                track = model["track"]
                log_L_arr = np.array(track["log_L"])
                log_Teff_arr = np.array(track["log_Teff"])
                log_R_arr = np.array(track["log_R"])

                expected_log_Teff = 3.761326 + 0.25 * log_L_arr - 0.50 * log_R_arr
                max_dev = np.max(np.abs(log_Teff_arr - expected_log_Teff))
                self.assertLess(
                    max_dev, 0.001,
                    f"Model M={m} Z={z} track maximum SB deviation {max_dev:.6f} dex exceeds 0.001 dex"
                )


class TestRadialAbundanceConservation(unittest.TestCase):
    """Rigorous empirical validation of chemical abundance mass conservation."""

    def test_abundance_mass_conservation_all_10080_points(self):
        """Verify sum(X_i) == 1.0 +/- 0.005 for all 28 models x 6 stages x 60 radial points."""
        total_points_tested = 0
        max_dev = 0.0

        for z in METALLICITY_GRID:
            for m in MASS_GRID:
                pathway = classify_pathway(m, z)
                for stage_idx in range(6):
                    prof = compute_abundance_profile(m, z, stage_idx, pathway)
                    q_len = len(prof["q"])
                    self.assertEqual(q_len, 60)

                    # Sum abundances across all 7 species
                    stack = np.zeros(q_len, dtype=float)
                    for sp in SPECIES:
                        arr = np.array(prof[sp])
                        # Check non-negativity
                        self.assertTrue(
                            np.all(arr >= -1e-7),
                            f"Negative abundance found in M={m} Z={z} stage={stage_idx} sp={sp}: min={np.min(arr)}"
                        )
                        stack += arr

                    devs = np.abs(stack - 1.0)
                    local_max = np.max(devs)
                    if local_max > max_dev:
                        max_dev = local_max

                    self.assertLess(
                        local_max, 0.005,
                        f"Abundance sum deviates from 1.0 in M={m} Z={z} stage={stage_idx}: max_dev={local_max:.6f}"
                    )
                    total_points_tested += q_len

        self.assertEqual(total_points_tested, 28 * 6 * 60)  # 10,080 points
        self.assertLess(max_dev, 0.001)

    def test_stage_physical_burning_nucleosynthesis_signatures(self):
        """Verify expected astrophysical nucleosynthesis signatures across stages."""
        # Solar model (1.0 M_sun, Z=0.014)
        pathway = classify_pathway(1.0, 0.014)

        # 1. ZAMS: Pristine envelope
        zams_prof = compute_abundance_profile(1.0, 0.014, 0, pathway)
        self.assertGreater(zams_prof["H1"][0], 0.65)
        self.assertGreater(zams_prof["H1"][-1], 0.65)

        # 2. TAMS: Exhausted core hydrogen
        tams_prof = compute_abundance_profile(1.0, 0.014, 1, pathway)
        self.assertLess(tams_prof["H1"][0], 0.02, "Core hydrogen not exhausted at TAMS")
        self.assertGreater(tams_prof["He4"][0], 0.95, "Core helium not enriched at TAMS")

        # 3. Massive star (25 M_sun, Z=0.014) pre-CCSN endpoint
        mass_pathway = classify_pathway(25.0, 0.014)
        ccsn_prof = compute_abundance_profile(25.0, 0.014, 5, mass_pathway)
        # Central core must be dominated by Iron-56
        self.assertGreater(ccsn_prof["Fe56"][0], 0.60, "Pre-CCSN core not dominated by Fe56")
        # Middle shell must contain Silicon & Oxygen
        self.assertGreater(max(ccsn_prof["Si28"]), 0.50, "Pre-CCSN star lacks rich Silicon shell")
        self.assertGreater(max(ccsn_prof["O16"]), 0.50, "Pre-CCSN star lacks rich Oxygen shell")


if __name__ == "__main__":
    unittest.main()
