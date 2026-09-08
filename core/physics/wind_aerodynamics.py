"""
High-Altitude Mountain Wind Turbulence & Aerodynamic Disturbance Torque Module.
Generates stochastic gust profiles (Davenport / Dryden turbulence spectrum)
and computes aerodynamic drag forces and yaw/pitch torques acting on the gimbal pod.
"""

import math
import random
from dataclasses import dataclass
from typing import Tuple


@dataclass
class WindState:
    mean_speed_ms: float
    instantaneous_speed_ms: float
    direction_deg: float
    aerodynamic_force_n: float
    torque_disturbance_az_nm: float
    torque_disturbance_el_nm: float
    turbulence_intensity: float


class WindAerodynamicsModel:
    """
    Simulates wind profile at high-altitude mountain deployment:
    - Mean wind speed altitude power law: v_mean(h) = v_ref * (h / h_ref)^alpha
    - Colored noise gust generator matching Davenport/Dryden gust spectra
    - Aerodynamic drag & yaw/pitch overturning torques on the gimbal structure
    """

    def __init__(
        self,
        base_wind_speed_ms: float = 12.0,
        wind_direction_deg: float = 45.0,
        mast_height_m: float = 3.5,
        frontal_area_m2: float = 0.28,
        drag_coefficient: float = 1.15,
        center_of_pressure_arm_m: float = 0.18
    ):
        self.base_wind_speed_ms = base_wind_speed_ms
        self.wind_direction_deg = wind_direction_deg
        self.mast_height_m = mast_height_m
        self.frontal_area_m2 = frontal_area_m2
        self.drag_coefficient = drag_coefficient
        self.cp_arm_m = center_of_pressure_arm_m
        
        # Internal state of 1st-order low-pass shaping filter for turbulence
        self.gust_state = 0.0
        self.turbulence_intensity = 0.22  # High turbulence in mountain ridges

    def update(
        self,
        dt: float,
        air_density_kg_m3: float,
        gimbal_az_deg: float,
        gimbal_el_deg: float
    ) -> WindState:
        """
        Updates stochastic gust and calculates aerodynamic disturbance torques.
        
        Args:
            dt: Simulation timestep in seconds.
            air_density_kg_m3: Ambient air density at altitude.
            gimbal_az_deg: Current gimbal azimuth angle in degrees.
            gimbal_el_deg: Current gimbal elevation angle in degrees.
        """
        # Davenport turbulence correlation time: tau ~ 1.5 - 2.5 seconds
        tau = 1.8
        white_noise = random.gauss(0.0, 1.0)
        
        # Discrete low-pass filter (Dryden approximation)
        alpha_filter = dt / (tau + dt)
        sigma_gust = self.base_wind_speed_ms * self.turbulence_intensity
        self.gust_state = (1.0 - alpha_filter) * self.gust_state + alpha_filter * (sigma_gust * white_noise)
        
        # Total instantaneous wind speed
        v_instant = max(0.0, self.base_wind_speed_ms + self.gust_state)
        
        # Dynamic pressure: q = 0.5 * rho * v^2
        dynamic_pressure = 0.5 * air_density_kg_m3 * (v_instant ** 2)
        
        # Aerodynamic Drag Force: F_d = q * C_d * A
        total_drag_force = dynamic_pressure * self.drag_coefficient * self.frontal_area_m2
        
        # Relative angle of attack between wind direction and gimbal pointing
        rel_az_rad = math.radians(self.wind_direction_deg - gimbal_az_deg)
        rel_el_rad = math.radians(gimbal_el_deg)
        
        # Aerodynamic disturbing torques on Azimuth and Elevation axes
        # Cross-wind component induces yaw torque; pitch component induces elevation torque
        torque_az = total_drag_force * self.cp_arm_m * math.sin(rel_az_rad) * math.cos(rel_el_rad)
        torque_el = total_drag_force * self.cp_arm_m * math.sin(rel_el_rad) * 0.75
        
        return WindState(
            mean_speed_ms=round(self.base_wind_speed_ms, 2),
            instantaneous_speed_ms=round(v_instant, 2),
            direction_deg=self.wind_direction_deg,
            aerodynamic_force_n=round(total_drag_force, 2),
            torque_disturbance_az_nm=round(torque_az, 3),
            torque_disturbance_el_nm=round(torque_el, 3),
            turbulence_intensity=self.turbulence_intensity
        )
