#!/usr/bin/env python3
"""
Unit Test Suite for Native MESA ASCII Parser & Bridge
=====================================================
Tests Fortran scientific notation parsing, history.data and profile*.data ingestion,
remove_backups() deduplication, MesaLogDir operations, and MesaBridge schema mapping.
"""

import tempfile
import unittest
from pathlib import Path
import numpy as np

from stellar_evolution.core.constants import L_sun, R_sun
from stellar_evolution.core.schemas import StellarModel, StageModel, OnionShellModel, ProfileInfo
from stellar_evolution.core.exceptions import MesaParseError, ValidationError
from stellar_evolution.mesa.native_parser import parse_fortran_float, NativeMesaParser, MesaLogDir
from stellar_evolution.mesa.bridge import MesaBridge
from stellar_evolution.physics.evolution import generate_track


class TestNativeMesaParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.logs_dir = Path(cls.temp_dir.name)

        # 1. Write sample history.data with Fortran D-notation and backup steps
        # Steps: 1, 2, 3, then backup to 2, 3, 4
        cls.hist_path = cls.logs_dir / "history.data"
        hist_text = (
            "                  1                   2                   3\n"
            "        version_number            compiler               build\n"
            '              "24.03.1"          "gfortran"           "native"\n'
            "\n"
            "                   1                    2                    3                    4                    5                    6\n"
            "        model_number             star_age            star_mass                log_L             log_Teff                log_R\n"
            "                   1         1.000000D+05         1.000000D+00        -1.550000D-01         3.761300D+00        -5.100000D-02\n"
            "                   2         2.000000D+05         9.999000D-01        -1.540000D-01         3.761400D+00        -5.000000D-02\n"
            "                   3         3.000000D+05         9.998000D-01        -1.530000D-01         3.761500D+00        -4.900000D-02\n"
            "                   2         2.100000D+05         9.999000D-01        -1.540000D-01         3.761400D+00        -5.000000D-02\n"
            "                   3         3.100000D+05         9.998000D-01        -1.530000D-01         3.761500D+00        -4.900000D-02\n"
            "                   4         4.000000D+05         9.997000D-01        -1.520000D-01         3.761600D+00        -4.800000D-02\n"
        )
        cls.hist_path.write_text(hist_text, encoding="utf-8")

        # 2. Write sample profiles.index
        cls.idx_path = cls.logs_dir / "profiles.index"
        idx_text = (
            " index file for profiles\n"
            "        model_number              priority        profile_number\n"
            "                   1                     1                     1\n"
            "                   4                     1                     2\n"
        )
        cls.idx_path.write_text(idx_text, encoding="utf-8")

        # 3. Write sample profile1.data
        cls.prof1_path = cls.logs_dir / "profile1.data"
        prof1_text = (
            "                  1                   2                   3\n"
            "       model_number            star_age           star_mass\n"
            "                  1        1.000000D+05        1.000000D+00\n"
            "\n"
            "               1                2                3                4                5                6                7\n"
            "            zone             mass                q             logR             logT           logRho               h1\n"
            "               1      1.00000D+00      1.00000D+00     -5.10000D-02      3.76130D+00     -6.50000D+00      7.00000D-01\n"
            "               2      5.00000D-01      5.00000D-01     -2.50000D-01      6.50000D+00      1.00000D+00      7.00000D-01\n"
            "               3      1.00000D-02      1.00000D-02     -9.00000D-01      7.13000D+00      1.92000D+00      7.00000D-01\n"
        )
        cls.prof1_path.write_text(prof1_text, encoding="utf-8")

        # 4. Write sample profile2.data
        cls.prof2_path = cls.logs_dir / "profile2.data"
        prof2_text = (
            "                  1                   2                   3\n"
            "       model_number            star_age           star_mass\n"
            "                  4        4.000000D+05        9.997000D-01\n"
            "\n"
            "               1                2                3                4                5                6                7\n"
            "            zone             mass                q             logR             logT           logRho               h1\n"
            "               1      9.99700D-01      1.00000D+00     -4.80000D-02      3.76160D+00     -6.40000D+00      6.99000D-01\n"
            "               2      5.00000D-01      5.00150D-01     -2.40000D-01      6.52000D+00      1.05000D+00      6.95000D-01\n"
            "               3      1.00000D-02      1.00030D-02     -8.90000D-01      7.13600D+00      1.93500D+00      6.80000D-01\n"
        )
        cls.prof2_path.write_text(prof2_text, encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_fortran_float_parsing_standard_notation(self):
        """Test standard Fortran D and E exponent notation parsing."""
        self.assertAlmostEqual(parse_fortran_float("1.234567D+02"), 123.4567)
        self.assertAlmostEqual(parse_fortran_float("1.234567d-02"), 0.01234567)
        self.assertAlmostEqual(parse_fortran_float("3.14159E+00"), 3.14159)
        self.assertAlmostEqual(parse_fortran_float("-2.50000e-01"), -0.25)

    def test_fortran_float_parsing_missing_exponent_letter(self):
        """Test Fortran missing-E compact notation e.g. 1.2345-05."""
        self.assertAlmostEqual(parse_fortran_float("1.2345-05"), 1.2345e-5)
        self.assertAlmostEqual(parse_fortran_float("-1.2345+03"), -1234.5)

    def test_fortran_float_parsing_edge_cases(self):
        """Test parsing quoted numbers, zero, integers, and whitespace."""
        self.assertEqual(parse_fortran_float(' "42" '), 42.0)
        self.assertEqual(parse_fortran_float("0.000000e+00"), 0.0)
        self.assertEqual(parse_fortran_float(""), 0.0)

    def test_parse_history_data(self):
        """Test reading history.data columns and header metadata."""
        hist = NativeMesaParser.read_history(self.hist_path, remove_backups=False)
        self.assertEqual(hist.header("version_number"), "24.03.1")
        self.assertEqual(hist.header("compiler"), "gfortran")
        self.assertIn("model_number", hist)
        self.assertIn("log_L", hist)
        self.assertEqual(len(hist["log_L"]), 6)

    def test_remove_backups_algorithm_deduplication(self):
        """Test remove_backups eliminates retry steps so model_number is strictly increasing."""
        hist = NativeMesaParser.read_history(self.hist_path, remove_backups=True)
        self.assertEqual(list(hist["model_number"]), [1, 2, 3, 4])
        self.assertEqual(len(hist["log_L"]), 4)
        # Verify step 2 and 3 kept were the retried ones with age 2.1e5 and 3.1e5
        self.assertAlmostEqual(hist["star_age"][1], 2.1e5)
        self.assertAlmostEqual(hist["star_age"][2], 3.1e5)

    def test_history_column_attribute_access(self):
        """Test attribute-style column access on HistoryData."""
        hist = NativeMesaParser.read_history(self.hist_path, remove_backups=True)
        self.assertEqual(len(hist.star_age), 4)
        self.assertAlmostEqual(hist.star_age[0], 1.0e5)
        self.assertAlmostEqual(hist.log_L[0], -0.155)

    def test_history_derived_properties(self):
        """Test automatic conversion of log quantities to linear: L = 10^log_L, Teff = 10^log_Teff."""
        hist = NativeMesaParser.read_history(self.hist_path, remove_backups=True)
        self.assertTrue(np.allclose(hist.L, 10.0 ** hist.log_L))
        self.assertTrue(np.allclose(hist.Teff, 10.0 ** hist.log_Teff))
        self.assertTrue(np.allclose(hist.R, 10.0 ** hist.log_R))

    def test_history_in_data_and_contains(self):
        """Test column existence checking via in_data() and 'in' operator."""
        hist = NativeMesaParser.read_history(self.hist_path)
        self.assertTrue(hist.in_data("star_mass"))
        self.assertIn("star_mass", hist)
        self.assertFalse(hist.in_data("non_existent_column"))
        self.assertNotIn("non_existent_column", hist)

    def test_history_data_at_model_number(self):
        """Test querying history column value at a specific model number."""
        hist = NativeMesaParser.read_history(self.hist_path, remove_backups=True)
        age_at_4 = hist.data_at_model_number("star_age", 4)
        self.assertAlmostEqual(age_at_4, 4.0e5)

    def test_parse_profiles_index(self):
        """Test parsing profiles.index into ProfileInfo dataclasses."""
        idx = NativeMesaParser.read_index(self.idx_path)
        self.assertEqual(len(idx), 2)
        self.assertEqual(idx[0].model_number, 1)
        self.assertEqual(idx[0].profile_number, 1)
        self.assertEqual(idx[1].model_number, 4)
        self.assertEqual(idx[1].profile_number, 2)

    def test_parse_profile_data(self):
        """Test parsing radial zones and isotopes from profile1.data."""
        prof = NativeMesaParser.read_profile(self.prof1_path)
        self.assertEqual(prof.header("model_number"), 1.0)
        self.assertEqual(len(prof["zone"]), 3)
        self.assertEqual(len(prof["mass"]), 3)
        self.assertAlmostEqual(prof["h1"][0], 0.70)

    def test_profile_derived_properties(self):
        """Test automatic linear properties for profiles: T = 10^logT, Rho = 10^logRho."""
        prof = NativeMesaParser.read_profile(self.prof1_path)
        self.assertTrue(np.allclose(prof.T, 10.0 ** prof.logT))
        self.assertTrue(np.allclose(prof.Rho, 10.0 ** prof.logRho))

    def test_mesa_parser_instance_api(self):
        """Test using NativeMesaParser as an instantiated object with logs_dir."""
        parser = NativeMesaParser(self.logs_dir)
        hist = parser.read_history(remove_backups=True)
        self.assertEqual(len(hist["model_number"]), 4)
        idx = parser.read_index()
        self.assertEqual(len(idx), 2)
        prof1 = parser.read_profile(1)
        self.assertEqual(len(prof1["zone"]), 3)

    def test_mesa_log_dir_high_level_interface(self):
        """Test MesaLogDir directory manager, caching, and model lookup."""
        logs = MesaLogDir(self.logs_dir)
        self.assertEqual(len(logs.history.star_age), 6)
        self.assertEqual(list(logs.model_numbers), [1, 4])
        self.assertEqual(list(logs.profile_numbers), [1, 2])
        prof_last = logs.profile_data()
        self.assertEqual(prof_last.header("model_number"), 4.0)

    def test_mesa_log_dir_select_models(self):
        """Test MesaLogDir.select_models with conditional predicate."""
        logs = MesaLogDir(self.logs_dir)
        filtered = logs.select_models(lambda age: age > 2.0e5, "star_age")
        self.assertEqual(list(filtered), [4])

    def test_mesa_bridge_from_grid_model(self):
        """Test converting analytical grid track to unified StellarModel schema."""
        raw_model = generate_track(1.0, 0.014)
        stellar_model = MesaBridge.grid_model_to_stellar_model(raw_model)
        self.assertEqual(stellar_model.mass, 1.0)
        self.assertEqual(stellar_model.metallicity, 0.014)
        self.assertEqual(len(stellar_model.stages), 6)
        self.assertTrue(MesaBridge.validate_stellar_model(stellar_model))

    def test_mesa_bridge_from_logs(self):
        """Test converting parsed MESA simulation directory to StellarModel schema."""
        logs = MesaLogDir(self.logs_dir)
        stellar_model = MesaBridge.mesa_logs_to_stellar_model(logs, mass=1.0, metallicity=0.014)
        self.assertEqual(stellar_model.mass, 1.0)
        self.assertEqual(len(stellar_model.stages), 2)
        self.assertTrue(MesaBridge.validate_stellar_model(stellar_model))

    def test_mesa_parse_error_handling(self):
        """Test raising MesaParseError on nonexistent files."""
        with self.assertRaises(MesaParseError):
            NativeMesaParser.read_history(self.logs_dir / "non_existent.data")

    def test_publication_4panel_figure_generation(self):
        """Test generation of 4-panel publication PDF and PNG figures following py_mesa_reader guide."""
        from stellar_evolution.viz.publication_figures import generate_mesa_summary_4panel
        fig_out_dir = self.logs_dir / "test_figures"
        png_path = generate_mesa_summary_4panel(
            logs_or_dir=self.logs_dir,
            output_dir=fig_out_dir,
            file_prefix="test_mesa_4panel",
        )
        self.assertTrue(png_path.is_file(), "PNG figure must be created")
        pdf_path = fig_out_dir / "test_mesa_4panel.pdf"
        self.assertTrue(pdf_path.is_file(), "Vector PDF figure must be created")
        self.assertGreater(png_path.stat().st_size, 5000, "PNG figure must be non-empty")
        self.assertGreater(pdf_path.stat().st_size, 5000, "PDF figure must be non-empty")


if __name__ == "__main__":
    unittest.main()
