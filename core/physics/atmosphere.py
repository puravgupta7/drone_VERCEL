"""
High-Altitude Atmospheric Physics Module (ISA 1976 + Arctic/Highland Extensions).
Computes exact thermodynamic and aerodynamic properties of air as a function of altitude,
including barometric pressure, temperature, density, speed of sound, dynamic viscosity,
and convective heat dissipation derating.
"""

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class AtmosphericState:
    altitude_m: float
    temperature_k: float
    temperature_c: float
    pressure_pa: float
    pressure_hpa: float
    density_kg_m3: float
    density_ratio: float  # rho / rho_0
    speed_of_sound_ms: float
    dynamic_viscosity_pa_s: float
    convective_cooling_factor: float  # Cooling efficiency relative to sea level (1.0 = 100%)
    relative_humidity: float
    air_thermal_conductivity_w_mk: float


class AtmosphereModel:
    # Standard Sea-Level Constants (ISA 1976)
    T0_SEA_LEVEL = 288.15      # Kelvin (15.0 °C)
    P0_SEA_LEVEL = 101325.0    # Pascals (1013.25 hPa)
    RHO0_SEA_LEVEL = 1.225     # kg/m^3
    G0 = 9.80665               # m/s^2 (Standard gravitational acceleration)
    R_SPECIFIC = 287.05287     # J / (kg * K) (Specific gas constant for dry air)
    GAMMA = 1.40               # Ratio of specific heats
    LAPSE_RATE = -0.0065       # K / m (Troposphere temperature lapse rate)
    
    # Sutherland's Viscosity Law Constants
    MU_0 = 1.716e-5            # Pa * s (at T_ref = 273.15 K)
    T_REF_SUTHERLAND = 273.15  # K
    S_SUTHERLAND = 110.4       # K (Sutherland's empirical temperature constant)

    @classmethod
    def compute(cls, altitude_m: float, delta_t_c: float = 0.0, relative_humidity: float = 0.40) -> AtmosphericState:
        """
        Calculates atmospheric properties at a given geopotential altitude.
        
        Args:
            altitude_m: Altitude above sea level in meters (0 to 11,000 m).
            delta_t_c: Temperature offset in °C from standard ISA (e.g. -25°C for Siachen/Himalayan winter).
            relative_humidity: Fractional relative humidity (0.0 to 1.0).
            
        Returns:
            AtmosphericState object containing all environmental parameters.
        """
        alt = max(0.0, min(11000.0, float(altitude_m)))
        
        # Standard ISA Troposphere Temperature
        t_isa = cls.T0_SEA_LEVEL + cls.LAPSE_RATE * alt
        # Apply temperature offset (harsh winter or high plateau solar heating)
        t_kelvin = max(180.0, t_isa + delta_t_c)
        t_celsius = t_kelvin - 273.15
        
        # Barometric Pressure via Barometric Formula
        # P = P0 * (1 + (L * h) / T0) ^ (-g0 / (R * L))
        exponent = -cls.G0 / (cls.R_SPECIFIC * cls.LAPSE_RATE)
        pressure_pa = cls.P0_SEA_LEVEL * math.pow(1.0 + (cls.LAPSE_RATE * alt) / cls.T0_SEA_LEVEL, exponent)
        
        # In actual cold atmosphere, pressure follows ideal gas state
        density = pressure_pa / (cls.R_SPECIFIC * t_kelvin)
        density_ratio = density / cls.RHO0_SEA_LEVEL
        
        # Speed of Sound: c = sqrt(gamma * R * T)
        speed_of_sound = math.sqrt(cls.GAMMA * cls.R_SPECIFIC * t_kelvin)
        
        # Dynamic Viscosity via Sutherland's Equation
        viscosity = cls.MU_0 * math.pow(t_kelvin / cls.T_REF_SUTHERLAND, 1.5) * (
            (cls.T_REF_SUTHERLAND + cls.S_SUTHERLAND) / (t_kelvin + cls.S_SUTHERLAND)
        )
        
        # Air Thermal Conductivity: k ~ 2.646e-3 * T^1.5 / (T + 245.4 * 10^(-12/T))
        k_air = (2.646e-3 * math.pow(t_kelvin, 1.5)) / (t_kelvin + 245.4 * math.pow(10.0, -12.0 / t_kelvin))
        
        # Convective Cooling Derating Factor:
        # Heat transfer coefficient h_c for forced convection scales approximately as:
        # h_c ~ (rho * v)^0.6 * (k / mu^0.6)
        # In thin air, reduced density drastically cuts convective cooling.
        cooling_factor = math.pow(density_ratio, 0.6) * math.pow(cls.T0_SEA_LEVEL / t_kelvin, 0.18)
        
        return AtmosphericState(
            altitude_m=alt,
            temperature_k=round(t_kelvin, 2),
            temperature_c=round(t_celsius, 2),
            pressure_pa=round(pressure_pa, 1),
            pressure_hpa=round(pressure_pa / 100.0, 2),
            density_kg_m3=round(density, 4),
            density_ratio=round(density_ratio, 4),
            speed_of_sound_ms=round(speed_of_sound, 2),
            dynamic_viscosity_pa_s=viscosity,
            convective_cooling_factor=round(cooling_factor, 4),
            relative_humidity=relative_humidity,
            air_thermal_conductivity_w_mk=round(k_air, 4)
        )
