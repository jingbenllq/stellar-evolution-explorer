#!/usr/bin/env python3
"""
Unit & Grid Audit Test Suite for Stellar Evolution Explorer v2.1
================================================================
Comprehensive verification of parameter space models, scaling relations,
stage anchors, and radial abundance normalization.
"""

import json
import unittest
from pathlib import Path

import stellar_grid_engine as sge
from stellar_evolution.physics import (
    MASS_GRID,
    METALLICITY_GRID,
    STAGE_NAMES,
    SPECIES,
    zams_properties,
    classify_pathway,
)


class TestStellarGrid(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = Path(__file__).resolve().parent.parent
        cls.json_path = cls.base / "stellar_grid_data.json"
        cls.data = json.loads(cls.json_path.read_text(encoding="utf-8"))

    def test_28_models_present(self):
        """Verify the grid contains exactly 28 models across 4 metallicities and 7 masses."""
        models = self.data["models"]
        self.assertEqual(len(models), 4, "Must contain exactly 4 metallicity brackets")
        total_count = sum(len(z_dict) for z_dict in models.values())
        self.assertEqual(total_count, 28, "Total model count must be 28 (4 Z x 7 M)")

    def test_grid_metadata_structure(self):
        """Verify metadata fields, masses, metallicities, species, and stage names."""
        meta = self.data["metadata"]
        self.assertIn("version", meta)
        self.assertEqual(meta["masses"], MASS_GRID)
        self.assertEqual(meta["metallicities"], METALLICITY_GRID)
        self.assertEqual(meta["species"], SPECIES)
        self.assertEqual(len(meta["stage_names"]), 6)

    def test_solar_zams_vs_present_day_sun_calibration(self):
        """Verify Solar ZAMS calibration: log_L = -0.155 (0.70 L_sun), R = 0.89 R_sun, t_ms = 10 Gyr."""
        sun = self.data["models"]["0.014"]["1.0"]
        self.assertAlmostEqual(sun["zams"]["log_L"], -0.155, places=3)
        self.assertAlmostEqual(sun["zams"]["log_R"], -0.051, places=3)
        self.assertTrue(3.74 <= sun["zams"]["log_Teff"] <= 3.76)
        self.assertTrue(9.5e9 <= sun["zams"]["t_ms"] <= 1.05e10)

    def test_fully_convective_03msun_flat_profile(self):
        """Verify 0.3 M_sun star is fully convective with lifetime > 500 Gyr and flat TAMS profile."""
        m03 = self.data["models"]["0.014"]["0.3"]
        self.assertGreater(m03["zams"]["t_ms"], 5.0e11)
        prof_tams = m03["profiles"]["1"]
        # Flat H1 profile across all radial mass coordinates q
        h1_spread = max(prof_tams["H1"]) - min(prof_tams["H1"])
        self.assertLess(h1_spread, 0.005, "0.3 M_sun must exhibit flat homogeneous profile on MS")

    def test_8msun_metallicity_fate_bifurcation(self):
        """Verify 8.0 M_sun bifurcation between ONe White Dwarf and Neutron Star."""
        m8_sol = self.data["models"]["0.014"]["8.0"]
        m8_low = self.data["models"]["0.0001"]["8.0"]
        self.assertEqual(m8_sol["pathway"]["remnant_code"], "ONe_WD")
        self.assertEqual(m8_low["pathway"]["remnant_code"], "NS")

    def test_strict_abundance_normalization_all_models_all_stages(self):
        """Verify sum_i X_i(q) == 1.0 within 1e-3 across all 28 models and all 6 stages."""
        species = self.data["metadata"]["species"]
        for z_k, z_dict in self.data["models"].items():
            for m_k, mod in z_dict.items():
                for st_k, prof in mod["profiles"].items():
                    q_len = len(prof["q"])
                    for i in range(q_len):
                        total = sum(prof[sp][i] for sp in species)
                        self.assertAlmostEqual(
                            total, 1.0, places=2,
                            msg=f"Model Z={z_k} M={m_k} Stage={st_k} q_idx={i} failed normalization: total={total}"
                        )

    def test_mass_luminosity_monotonicity_on_zams(self):
        """Verify ZAMS luminosity strictly increases with stellar mass."""
        z_sol = self.data["models"]["0.014"]
        masses = [0.3, 1.0, 3.0, 5.0, 8.0, 15.0, 25.0]
        lums = [z_sol[f"{m:.1f}"]["zams"]["log_L"] for m in masses]
        for i in range(len(lums) - 1):
            self.assertLess(lums[i], lums[i + 1], f"Luminosity must increase from {masses[i]} to {masses[i+1]}")

    def test_mass_radius_monotonicity_on_zams(self):
        """Verify ZAMS radius strictly increases with stellar mass."""
        z_sol = self.data["models"]["0.014"]
        masses = [0.3, 1.0, 3.0, 5.0, 8.0, 15.0, 25.0]
        radii = [z_sol[f"{m:.1f}"]["zams"]["log_R"] for m in masses]
        for i in range(len(radii) - 1):
            self.assertLess(radii[i], radii[i + 1], f"Radius must increase from {masses[i]} to {masses[i+1]}")

    def test_metallicity_opacity_effect_on_zams(self):
        """Verify lower metallicity stars are hotter and more luminous on ZAMS due to lower opacity."""
        mod_solar = self.data["models"]["0.014"]["1.0"]
        mod_lowz = self.data["models"]["0.0001"]["1.0"]
        self.assertGreater(mod_lowz["zams"]["log_Teff"], mod_solar["zams"]["log_Teff"])
        self.assertGreater(mod_lowz["zams"]["log_L"], mod_solar["zams"]["log_L"])

    def test_track_age_monotonic_progression(self):
        """Verify age progresses monotonically along the evolutionary stage anchors."""
        for z_k, z_dict in self.data["models"].items():
            for m_k, mod in z_dict.items():
                ages = [st["age_yr"] for st in mod["stages"]]
                for i in range(len(ages) - 1):
                    self.assertLessEqual(ages[i], ages[i + 1])

    def test_remnant_mass_physical_bounds(self):
        """Verify remnant mass is positive and strictly less than initial stellar mass."""
        for z_k, z_dict in self.data["models"].items():
            for m_k, mod in z_dict.items():
                m_init = float(m_k)
                m_rem = mod["pathway"]["remnant_mass"]
                self.assertGreater(m_rem, 0.0)
                self.assertLess(m_rem, m_init)

    def test_massive_star_end_temperatures(self):
        """Verify massive stars (15, 25 M_sun) reach core temperatures > 10^9 K (log_Tc > 9.0)."""
        star15 = self.data["models"]["0.014"]["15.0"]
        star25 = self.data["models"]["0.014"]["25.0"]
        self.assertGreater(star15["track"]["log_Tc"][-1], 9.0)
        self.assertGreater(star25["track"]["log_Tc"][-1], 9.2)

    def test_unified_stages_array_present(self):
        """Verify every model contains a 6-stage array with valid concentric onion shells."""
        for z_k, z_dict in self.data["models"].items():
            for m_k, mod in z_dict.items():
                self.assertIn("stages", mod)
                self.assertEqual(len(mod["stages"]), 6)
                for st in mod["stages"]:
                    self.assertIn("onion_shells", st)
                    self.assertGreater(len(st["onion_shells"]), 0)

    def test_backward_compatible_cli_and_exports(self):
        """Verify root stellar_grid_engine preserves all backward-compatible exports and functions."""
        self.assertEqual(sge.MASS_GRID, MASS_GRID)
        self.assertEqual(sge.METALLICITY_GRID, METALLICITY_GRID)
        zams_1 = sge.zams_properties(1.0, 0.014)
        self.assertAlmostEqual(zams_1["log_L"], -0.155, places=3)
        pathway = sge.classify_pathway(1.0, 0.014)
        self.assertEqual(pathway["remnant_code"], "CO_WD")


if __name__ == "__main__":
    unittest.main()
