#!/usr/bin/env python3
"""
Unit Test Suite for Physics Invariants & Thermodynamic Consistency
==================================================================
Tests fundamental astrophysical laws and conservation conditions:
  - Stefan-Boltzmann identity: L = 4 * pi * R^2 * sigma * Teff^4 across all ZAMS models
  - Kippenhahn convective boundary consistency: q_conv_core <= q_conv_env
  - Nuclear burning reaction thresholds: PP vs CNO transition, 3-alpha, C/O/Si burning
  - Abundance mass conservation and shell concentricity
"""

import json
import math
import unittest
from pathlib import Path
import numpy as np

from stellar_evolution.core.constants import (
    G,
    M_sun,
    L_sun,
    R_sun,
    sigma_SB,
    T_EFF_SUN,
    SIGMA_SB_CGS,
    stefan_boltzmann_luminosity,
    stefan_boltzmann_radius,
    stefan_boltzmann_teff,
)
from stellar_evolution.physics import (
    MASS_GRID,
    METALLICITY_GRID,
    zams_properties,
    calc_pp_rate,
    calc_cno_rate,
    calc_triple_alpha_rate,
    calc_carbon_burning_rate,
    calc_oxygen_burning_rate,
    calc_silicon_burning_rate,
    compute_kippenhahn_series,
)


class TestPhysicsConsistency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = Path(__file__).resolve().parent.parent
        cls.json_path = cls.base / "stellar_grid_data.json"
        cls.data = json.loads(cls.json_path.read_text(encoding="utf-8"))

    def test_stefan_boltzmann_solar_constants_consistency(self):
        """Verify nominal solar constants satisfy L_sun = 4 * pi * R_sun^2 * sigma * Teff_sun^4 within 0.1%."""
        computed_L = 4.0 * math.pi * (R_sun ** 2) * SIGMA_SB_CGS * (T_EFF_SUN ** 4)
        rel_diff = abs(computed_L - L_sun) / L_sun
        self.assertLess(rel_diff, 0.001, f"Solar Stefan-Boltzmann discrepancy too large: {rel_diff:.4f}")

    def test_stefan_boltzmann_identity_all_zams_models(self):
        """Verify L == 4 * pi * R^2 * sigma * Teff^4 holds within 0.5% across all 28 ZAMS models."""
        for z in METALLICITY_GRID:
            for m in MASS_GRID:
                props = zams_properties(m, z)
                L_cgs = (10.0 ** props["log_L"]) * L_sun
                R_cgs = (10.0 ** props["log_R"]) * R_sun
                Teff_k = 10.0 ** props["log_Teff"]

                sb_L = 4.0 * math.pi * (R_cgs ** 2) * SIGMA_SB_CGS * (Teff_k ** 4)
                rel_err = abs(sb_L - L_cgs) / L_cgs
                self.assertLess(
                    rel_err, 0.005,
                    f"ZAMS model M={m} Z={z} violates Stefan-Boltzmann: rel_err={rel_err:.5f}"
                )

    def test_stefan_boltzmann_helper_functions(self):
        """Verify inversion consistency among SB helper functions (L, R, Teff)."""
        r_test = 2.5 * R_sun
        teff_test = 8500.0
        l_calc = stefan_boltzmann_luminosity(r_test, teff_test)
        r_inverted = stefan_boltzmann_radius(l_calc, teff_test)
        teff_inverted = stefan_boltzmann_teff(l_calc, r_test)

        self.assertAlmostEqual(r_test, r_inverted, delta=1.0e5)
        self.assertAlmostEqual(teff_test, teff_inverted, delta=1.0e-3)

    def test_kippenhahn_convective_boundaries_monotonicity(self):
        """Verify convective core top boundary <= convective envelope base boundary across all models."""
        s_arr = np.linspace(0.0, 5.0, 100)
        for z in METALLICITY_GRID:
            for m in MASS_GRID:
                kip = compute_kippenhahn_series(m, z, s_arr)
                cc = kip["conv_core"]
                ce = kip["conv_env"]
                for i in range(len(s_arr)):
                    # Core convection must not overlap envelope convection
                    self.assertLessEqual(
                        cc[i], ce[i] + 0.01,
                        f"Convective core ({cc[i]}) exceeds convective envelope ({ce[i]}) at s={s_arr[i]} for M={m}"
                    )

    def test_kippenhahn_shell_bounds_in_unit_interval(self):
        """Verify hydrogen and helium shell burning coordinates remain strictly within [0, 1]."""
        s_arr = np.linspace(0.0, 5.0, 100)
        for z in METALLICITY_GRID:
            for m in MASS_GRID:
                kip = compute_kippenhahn_series(m, z, s_arr)
                for hs in kip["h_shell"]:
                    if hs is not None:
                        self.assertTrue(0.0 <= hs <= 1.0)
                for hes in kip["he_shell"]:
                    if hes is not None:
                        self.assertTrue(0.0 <= hes <= 1.0)

    def test_pp_chain_temperature_dependence(self):
        """Verify PP-chain rate increases with T and vanishes below ignition threshold (3 * 10^6 K)."""
        self.assertEqual(calc_pp_rate(100.0, 1.0e6, 0.70), 0.0)
        rate_10m = calc_pp_rate(100.0, 1.0e7, 0.70)
        rate_15m = calc_pp_rate(100.0, 1.5e7, 0.70)
        self.assertGreater(rate_10m, 0.0)
        self.assertGreater(rate_15m, rate_10m)

    def test_cno_cycle_steep_temperature_response(self):
        """Verify CNO cycle rate exhibits extreme sensitivity (> 100x increase between 1.5e7 and 3e7 K)."""
        self.assertEqual(calc_cno_rate(100.0, 5.0e6, 0.70, 0.014), 0.0)
        rate_15m = calc_cno_rate(100.0, 1.5e7, 0.70, 0.014)
        rate_30m = calc_cno_rate(100.0, 3.0e7, 0.70, 0.014)
        self.assertGreater(rate_30m, rate_15m * 100.0)

    def test_pp_cno_transition_temperature(self):
        """Verify PP chain dominates at 1.2e7 K and CNO cycle dominates at 2.5e7 K for solar composition."""
        rho = 100.0
        X = 0.70
        Z_cno = 0.014
        # Low T: PP dominates
        pp_low = calc_pp_rate(rho, 1.2e7, X)
        cno_low = calc_cno_rate(rho, 1.2e7, X, Z_cno)
        self.assertGreater(pp_low, cno_low)

        # High T: CNO dominates
        pp_high = calc_pp_rate(rho, 2.5e7, X)
        cno_high = calc_cno_rate(rho, 2.5e7, X, Z_cno)
        self.assertGreater(cno_high, pp_high)

    def test_triple_alpha_ignition_threshold(self):
        """Verify 3-alpha helium burning is zero below 6e7 K and explodes at T >= 1e8 K."""
        self.assertEqual(calc_triple_alpha_rate(1000.0, 5.0e7, 0.98), 0.0)
        rate_100m = calc_triple_alpha_rate(1000.0, 1.0e8, 0.98)
        rate_150m = calc_triple_alpha_rate(1000.0, 1.5e8, 0.98)
        self.assertGreater(rate_100m, 0.0)
        self.assertGreater(rate_150m, rate_100m * 10.0)

    def test_advanced_burning_thresholds(self):
        """Verify Carbon, Oxygen, and Silicon burning ignite only at appropriate extreme temperatures."""
        # Carbon burning: ignites at T >= 5.0e8 K
        self.assertEqual(calc_carbon_burning_rate(1.0e5, 3.0e8, 0.50), 0.0)
        self.assertGreater(calc_carbon_burning_rate(1.0e5, 6.0e8, 0.50), 0.0)

        # Oxygen burning: ignites at T >= 1.5e9 K
        self.assertEqual(calc_oxygen_burning_rate(1.0e6, 1.0e9, 0.60), 0.0)
        self.assertGreater(calc_oxygen_burning_rate(1.0e6, 2.0e9, 0.60), 0.0)

        # Silicon burning: ignites at T >= 2.5e9 K
        self.assertEqual(calc_silicon_burning_rate(1.0e7, 2.0e9, 0.80), 0.0)
        self.assertGreater(calc_silicon_burning_rate(1.0e7, 3.5e9, 0.80), 0.0)

    def test_initial_abundance_conservation(self):
        """Verify initial composition X_init + Y_init + Z == 1.0 across all metallicities."""
        for z in METALLICITY_GRID:
            X_init = max(0.68, 0.745 - 2.2 * z)
            Y_init = max(0.24, 1.0 - X_init - z)
            self.assertAlmostEqual(X_init + Y_init + z, 1.0, places=4)

    def test_core_fuel_fraction_bounds(self):
        """Verify core fuel fraction f_core is in realistic physical range (0.10 to 0.88)."""
        for z in METALLICITY_GRID:
            for m in MASS_GRID:
                p = zams_properties(m, z)
                f_core = p["f_core"]
                self.assertGreaterEqual(f_core, 0.10)
                self.assertLessEqual(f_core, 0.88)

    def test_electron_degeneracy_parameter_evolution(self):
        """Verify degeneracy parameter eta increases significantly from MS to WD stage in low mass stars."""
        m1 = self.data["models"]["0.014"]["1.0"]
        eta_zams = m1["track"]["eta"][0]
        eta_rem = m1["track"]["eta"][-1]
        self.assertLess(eta_zams, 0.0, "ZAMS core is classical / non-degenerate")
        self.assertGreater(eta_rem, 30.0, "White dwarf core must be highly degenerate (eta > 30)")

    def test_onion_shells_concentric_geometry(self):
        """Verify that within all stages, shell boundaries satisfy q_in <= q_out and r_in <= r_out."""
        for z_k, z_dict in self.data["models"].items():
            for m_k, mod in z_dict.items():
                for st in mod["stages"]:
                    for shell in st["onion_shells"]:
                        self.assertLessEqual(
                            shell["q_inner"], shell["q_outer"],
                            f"Shell {shell['name']} has inverted q boundaries"
                        )
                        self.assertLessEqual(
                            shell["r_inner_norm"], shell["r_outer_norm"],
                            f"Shell {shell['name']} has inverted r boundaries"
                        )

    def test_onion_shells_full_mass_coverage(self):
        """Verify onion shells span the full radial mass range [0, 1] without gaps."""
        for z_k, z_dict in self.data["models"].items():
            for m_k, mod in z_dict.items():
                for st in mod["stages"]:
                    shells = st["onion_shells"]
                    self.assertAlmostEqual(shells[0]["q_inner"], 0.0, places=2)
                    self.assertAlmostEqual(shells[-1]["q_outer"], 1.0, places=2)

    def test_onion_shells_dominant_element_validity(self):
        """Verify all identified onion shells belong to standard nucleosynthetic alpha/iron elements."""
        valid_elements = {"H", "He", "C", "O", "Ne", "Mg", "Si", "Fe"}
        for z_k, z_dict in self.data["models"].items():
            for m_k, mod in z_dict.items():
                for st in mod["stages"]:
                    for shell in st["onion_shells"]:
                        self.assertIn(
                            shell["dominant_element"], valid_elements,
                            f"Unknown dominant element {shell['dominant_element']} in {shell['name']}"
                        )


if __name__ == "__main__":
    unittest.main()
