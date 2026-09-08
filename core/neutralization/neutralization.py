"""
High-Altitude Countermeasure & Neutralization Module.
Simulates smart multi-band RF/GNSS electronic jamming with Paschen-safe power management,
and calculates micro-radian Directed-Energy (Laser) and Kinetic Lead-Angle fire-control solutions.
"""

import math
import numpy as np
from dataclasses import dataclass
from typing import Dict, Any, Tuple


@dataclass
class JammingStatus:
    active: bool
    gnss_jamming_active: bool
    ism_jamming_active: bool
    rf_output_power_w: float
    effective_isotropic_radiated_power_dbm: float
    jamming_to_signal_ratio_db: float  # J/S ratio at target
    target_link_disrupted: bool
    paschen_limited: bool


@dataclass
class FireControlSolution:
    target_locked: bool
    line_of_sight_vector: np.ndarray
    lead_point_m: np.ndarray
    time_of_flight_s: float
    aiming_azimuth_deg: float
    aiming_elevation_deg: float
    pointing_error_urad: float
    kill_probability_pct: float


class NeutralizationSystem:
    """
    Counter-UAS Electronic Attack & Hard-Kill Interception Subsystem.
    """

    def __init__(self):
        # Jammer parameters
        self.max_nominal_tx_power_w = 80.0
        self.antenna_gain_dbi = 16.5  # Directional horn antenna
        
        # Operational bands
        self.bands = {
            "gnss_l1": {"freq_ghz": 1.575, "active": True},
            "gnss_l2": {"freq_ghz": 1.227, "active": True},
            "ism_2_4": {"freq_ghz": 2.450, "active": True},
            "ism_5_8": {"freq_ghz": 5.800, "active": True}
        }
        
        # Hard-kill laser/kinetic parameters
        self.laser_power_kw = 5.0
        self.kinetic_muzzle_vel_ms = 920.0  # High-velocity 30mm/canister interceptor

    def compute_jamming(
        self,
        target_range_m: float,
        paschen_max_rf_cw_w: float,
        air_density_ratio: float,
        engage: bool = True
    ) -> JammingStatus:
        """
        Calculates jamming link budget and RF emission envelopes.
        """
        if not engage or target_range_m <= 1.0:
            return JammingStatus(
                active=False,
                gnss_jamming_active=False,
                ism_jamming_active=False,
                rf_output_power_w=0.0,
                effective_isotropic_radiated_power_dbm=0.0,
                jamming_to_signal_ratio_db=0.0,
                target_link_disrupted=False,
                paschen_limited=False
            )
            
        # Paschen breakdown power clamp:
        # Prevent high-voltage RF spark in thin air by capping output power
        paschen_limited = False
        allowed_power_w = self.max_nominal_tx_power_w
        if paschen_max_rf_cw_w < self.max_nominal_tx_power_w:
            allowed_power_w = max(10.0, paschen_max_rf_cw_w * 0.85)
            paschen_limited = True
            
        # EIRP: P_tx (dBm) + G_tx (dBi)
        p_tx_dbm = 10.0 * math.log10(allowed_power_w * 1000.0)
        eirp_dbm = p_tx_dbm + self.antenna_gain_dbi
        
        # Free-Space Path Loss (FSPL): FSPL = 20*log10(d) + 20*log10(f) + 20*log10(4*pi/c)
        # At 2.4 GHz, FSPL = 20*log10(d) + 40.0 dB
        fspl_db = 20.0 * math.log10(max(10.0, target_range_m)) + 40.0
        
        # Received Jammer Power at target drone antenna (assuming 0 dBi target antenna)
        p_j_rx_dbm = eirp_dbm - fspl_db
        
        # Hostile remote controller signal at target drone:
        # Assuming remote controller is 2.5 km away transmitting at 100 mW (+20 dBm) with 2 dBi antenna
        r_controller_m = 2500.0
        p_s_rx_dbm = (20.0 + 2.0) - (20.0 * math.log10(r_controller_m) + 40.0)
        
        # Jamming-to-Signal (J/S) Ratio:
        js_ratio_db = p_j_rx_dbm - p_s_rx_dbm
        
        # Target link is successfully severed if J/S exceeds +12 dB
        link_disrupted = (js_ratio_db >= 12.0)
        
        return JammingStatus(
            active=True,
            gnss_jamming_active=True,
            ism_jamming_active=True,
            rf_output_power_w=round(allowed_power_w, 1),
            effective_isotropic_radiated_power_dbm=round(eirp_dbm, 1),
            jamming_to_signal_ratio_db=round(js_ratio_db, 1),
            target_link_disrupted=link_disrupted,
            paschen_limited=paschen_limited
        )

    def compute_fire_control_solution(
        self,
        fused_pos: np.ndarray,
        fused_vel: np.ndarray,
        gimbal_pointing_az_rad: float,
        gimbal_pointing_el_rad: float,
        air_density_kg_m3: float
    ) -> FireControlSolution:
        """
        Calculates micro-radian lead-angle fire control solution.
        In thin high-altitude air, reduced aerodynamic drag leads to flatter ballistic trajectory.
        """
        r_target = float(np.linalg.norm(fused_pos))
        if r_target < 1.0:
            return FireControlSolution(
                target_locked=False,
                line_of_sight_vector=np.zeros(3),
                lead_point_m=np.zeros(3),
                time_of_flight_s=0.0,
                aiming_azimuth_deg=0.0,
                aiming_elevation_deg=0.0,
                pointing_error_urad=0.0,
                kill_probability_pct=0.0
            )
            
        # High-velocity kinetic interceptor / laser beam
        # For directed-energy laser: ToF = R / c ~ 0 (instantaneous)
        # For kinetic interceptor: v_avg accounting for thin air drag
        drag_derate = air_density_kg_m3 / 1.225
        v_eff = self.kinetic_muzzle_vel_ms * (1.0 - 0.06 * drag_derate * (r_target / 1000.0))
        tof = r_target / max(100.0, v_eff)
        
        # First-order predictive lead point: P_lead = P + V * tof + 0.5 * (g_drop) * tof^2
        # Gravity drop correction on kinetic round
        lead_pos = fused_pos + fused_vel * tof
        lead_pos[2] += 0.5 * 9.81 * (tof ** 2)  # Aim higher to compensate bullet drop
        
        # Required lead angles
        lead_az_rad = math.atan2(lead_pos[1], lead_pos[0])
        horiz_dist = math.hypot(lead_pos[0], lead_pos[1])
        lead_el_rad = math.atan2(lead_pos[2], max(0.1, horiz_dist))
        
        # Pointing error between current gimbal boresight and required lead point
        e_az = (gimbal_pointing_az_rad - lead_az_rad + math.pi) % (2.0 * math.pi) - math.pi
        e_el = gimbal_pointing_el_rad - lead_el_rad
        total_error_rad = math.hypot(e_az, e_el)
        error_urad = total_error_rad * 1e6
        
        # Intercept Probability based on micro-radian pointing precision
        # Precision laser interdiction requires <= 50 urad on target
        if error_urad < 35.0:
            p_kill = 94.0
        elif error_urad < 75.0:
            p_kill = 78.0
        elif error_urad < 150.0:
            p_kill = 45.0
        else:
            p_kill = 12.0
            
        return FireControlSolution(
            target_locked=(error_urad < 75.0),
            line_of_sight_vector=fused_pos / r_target,
            lead_point_m=np.round(lead_pos, 2),
            time_of_flight_s=round(tof, 3),
            aiming_azimuth_deg=round(math.degrees(lead_az_rad), 3),
            aiming_elevation_deg=round(math.degrees(lead_el_rad), 3),
            pointing_error_urad=round(error_urad, 1),
            kill_probability_pct=round(p_kill, 1)
        )
