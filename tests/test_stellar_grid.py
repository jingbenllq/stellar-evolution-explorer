#!/usr/bin/env python3
"""Unit & Physics Audit Test Suite for Stellar Evolution Explorer v2.0."""
import json
import unittest
from pathlib import Path
import stellar_grid_engine as sge

class TestStellarPhysicsAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = Path(__file__).resolve().parent.parent
        cls.data = json.loads((cls.base / "stellar_grid_data.json").read_text(encoding="utf-8"))

    def test_28_models_present(self):
        count = sum(len(z_dict) for z_dict in self.data["models"].values())
        self.assertEqual(count, 28)

    def test_solar_zams_vs_present_day_sun_calibration(self):
        sun = self.data["models"]["0.014"]["1.0"]
        # ZAMS should be ~0.70 L_sun (log_L = -0.155), not 1.0 L_sun
        self.assertAlmostEqual(sun["zams"]["log_L"], -0.155, places=3)
        # Main sequence lifetime should be ~10.0 Gyr
        self.assertTrue(9.5e9 <= sun["zams"]["t_ms"] <= 1.05e10)

    def test_fully_convective_03msun_flat_profile(self):
        m03 = self.data["models"]["0.014"]["0.3"]
        self.assertGreater(m03["zams"]["t_ms"], 5.0e11)
        prof_tams = m03["profiles"]["1"]
        # Flat H1 profile across all radial zones q
        self.assertLess(max(prof_tams["H1"]) - min(prof_tams["H1"]), 0.005)

    def test_8msun_metallicity_fate_bifurcation(self):
        m8_sol = self.data["models"]["0.014"]["8.0"]
        m8_low = self.data["models"]["0.0001"]["8.0"]
        self.assertEqual(m8_sol["pathway"]["remnant_code"], "ONe_WD")
        self.assertEqual(m8_low["pathway"]["remnant_code"], "NS")

    def test_strict_abundance_normalization(self):
        species = self.data["metadata"]["species"]
        for z_k, z_dict in self.data["models"].items():
            for m_k, mod in z_dict.items():
                for st_k, prof in mod["profiles"].items():
                    for i in range(len(prof["q"])):
                        total = sum(prof[sp][i] for sp in species)
                        self.assertAlmostEqual(total, 1.0, places=2)

if __name__ == "__main__":
    unittest.main()
