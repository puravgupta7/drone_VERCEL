"""
Automated Unit Tests for High-Altitude Physics Models.
Verifies ISA 1976 atmosphere, Paschen's law dielectric breakdown,
cable harness cryogenic hysteresis, and thin-air drone aerodynamics.
"""

import pytest
import math
import numpy as np

from core.physics.atmosphere import AtmosphereModel
from core.physics.paschen import PaschenModel
from core.physics.cable_dynamics import CableHysteresisModel, CABLE_MATERIALS
from core.physics.target_dynamics import HighAltitudeTargetDrone


def test_atmosphere_sea_level():
    atmo = AtmosphereModel.compute(altitude_m=0.0, delta_t_c=0.0)
    assert pytest.approx(atmo.pressure_pa, rel=1e-2) == 101325.0
    assert pytest.approx(atmo.density_kg_m3, rel=1e-2) == 1.225
    assert pytest.approx(atmo.temperature_c, abs=0.5) == 15.0
    assert atmo.density_ratio == 1.0
    assert atmo.convective_cooling_factor == 1.0


def test_atmosphere_high_altitude_siachen():
    # Siachen glacier altitude (~5,400m)
    atmo = AtmosphereModel.compute(altitude_m=5400.0, delta_t_c=-20.0)
    # Air pressure at 5400m should be ~500 hPa (half of sea level)
    assert 480.0 <= atmo.pressure_hpa <= 540.0
    # Density should be ~40-50% lower than sea level
    assert 0.55 <= atmo.density_ratio <= 0.78
    # Convective cooling efficiency is significantly derated
    assert atmo.convective_cooling_factor < 0.85
    # Ambient temperature with -20 offset should be ~ -35 to -40 C
    assert atmo.temperature_c < -25.0


def test_paschen_dielectric_breakdown():
    # Sea level breakdown across 1mm gap (~3,000V peak)
    p_sl = 101325.0
    res_sl = PaschenModel.calculate_breakdown(pressure_pa=p_sl, gap_distance_mm=1.0)
    assert res_sl.breakdown_voltage_v_peak > 2500.0
    assert res_sl.dielectric_derating_factor == 1.0
    assert res_sl.corona_risk_level == "SAFE"
    
    # High altitude breakdown (5400m, ~500 hPa)
    p_alt = 50000.0
    res_alt = PaschenModel.calculate_breakdown(pressure_pa=p_alt, gap_distance_mm=1.0, altitude_m=5400.0)
    # Breakdown voltage must be lower
    assert res_alt.breakdown_voltage_v_peak < res_sl.breakdown_voltage_v_peak
    assert res_alt.dielectric_derating_factor < 0.75
    assert res_alt.max_rf_power_cw_watts < res_sl.max_rf_power_cw_watts


def test_cable_cryogenic_stiffness():
    pvc_model = CableHysteresisModel(material_key="standard_pvc")
    ptfe_model = CableHysteresisModel(material_key="mil_spec_ptfe")
    
    # At room temperature (+20C)
    mult_pvc_warm = pvc_model.compute_stiffness_multiplier(20.0)
    mult_ptfe_warm = ptfe_model.compute_stiffness_multiplier(20.0)
    assert mult_pvc_warm == 1.0
    assert mult_ptfe_warm == 1.0
    
    # At Siachen winter cold (-35C)
    mult_pvc_cold = pvc_model.compute_stiffness_multiplier(-35.0)
    mult_ptfe_cold = ptfe_model.compute_stiffness_multiplier(-35.0)
    
    # PVC stiffens radically due to glass transition
    assert mult_pvc_cold > 5.0
    # PTFE retains flexibility with much lower stiffening factor
    assert mult_ptfe_cold < mult_pvc_cold


def test_target_drone_aerodynamics_in_thin_air():
    drone = HighAltitudeTargetDrone()
    # At sea level (rho = 1.225)
    rpm_sl = drone.compute_rotor_rpm(1.225)
    # At 5400m (rho ~ 0.70)
    rpm_alt = drone.compute_rotor_rpm(0.70)
    
    # Drone must spin propellers significantly faster in thin air to sustain hover lift
    assert rpm_alt > rpm_sl * 1.20
