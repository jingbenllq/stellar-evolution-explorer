"""
Fundamental Physical and Astronomical Constants
==============================================
Provides standard IAU/CODATA physical constants in both CGS and SI units,
calibrated to ensure exact Stefan-Boltzmann and solar thermodynamic consistency.
"""

import math

# Gravitational Constant
G_CGS = 6.67430e-8      # cm^3 g^-1 s^-2
G_SI = 6.67430e-11      # m^3 kg^-1 s^-2
G = G_CGS

# Solar Mass
M_SUN_CGS = 1.98847e33  # g
M_SUN_SI = 1.98847e30   # kg
M_sun = M_SUN_CGS

# Solar Luminosity (nominal IAU 2015 resolution B3)
L_SUN_CGS = 3.828e33    # erg s^-1
L_SUN_SI = 3.828e26     # W
L_sun = L_SUN_CGS

# Solar Radius (nominal IAU 2015 resolution B3)
R_SUN_CGS = 6.957e10    # cm
R_SUN_SI = 6.957e8      # m
R_sun = R_SUN_CGS

# Stefan-Boltzmann Constant (CODATA 2018 exact relation)
SIGMA_SB_CGS = 5.670374419e-5  # erg cm^-2 s^-1 K^-4
SIGMA_SB_SI = 5.670374419e-8   # W m^-2 K^-4
sigma_SB = SIGMA_SB_CGS

# Solar Effective Temperature (nominal)
T_EFF_SUN = 5772.0      # K

# Seconds per Julian year
YR_S = 31557600.0       # 365.25 days in seconds
yr_s = YR_S

# Additional useful constants
C_LIGHT_CGS = 2.99792458e10    # cm s^-1
K_BOLTZMANN_CGS = 1.380649e-16 # erg K^-1
M_PROTON_CGS = 1.67262192e-24  # g
M_HYDROGEN_CGS = 1.6735575e-24 # g
A_RAD_CGS = 4.0 * SIGMA_SB_CGS / C_LIGHT_CGS  # radiation constant 7.5657e-15 erg cm^-3 K^-4


def stefan_boltzmann_luminosity(radius_cm: float, teff_k: float) -> float:
    """Calculate bolometric luminosity in erg/s from radius in cm and Teff in K."""
    return 4.0 * math.pi * (radius_cm ** 2) * SIGMA_SB_CGS * (teff_k ** 4)


def stefan_boltzmann_radius(luminosity_erg_s: float, teff_k: float) -> float:
    """Calculate stellar radius in cm from luminosity in erg/s and Teff in K."""
    return math.sqrt(luminosity_erg_s / (4.0 * math.pi * SIGMA_SB_CGS * (teff_k ** 4)))


def stefan_boltzmann_teff(luminosity_erg_s: float, radius_cm: float) -> float:
    """Calculate effective temperature in K from luminosity in erg/s and radius in cm."""
    return (luminosity_erg_s / (4.0 * math.pi * (radius_cm ** 2) * SIGMA_SB_CGS)) ** 0.25
