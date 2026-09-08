"""
High-Precision 2-DOF Pan-Tilt Gimbal Pedestal Dynamic Simulation.
Models mechanical inertia, temperature-dependent bearing friction/stiction,
gravity sag, cable harness restoring torques, and motor torque limits.
"""

import math
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Dict, Any
from core.physics.cable_dynamics import CableHysteresisModel


@dataclass
class GimbalState:
    az_rad: float
    az_deg: float
    az_vel_rad_s: float
    az_acc_rad_s2: float
    el_rad: float
    el_deg: float
    el_vel_rad_s: float
    el_acc_rad_s2: float
    motor_torque_az_nm: float
    motor_torque_el_nm: float
    cable_torque_az_nm: float
    cable_torque_el_nm: float
    wind_torque_az_nm: float
    wind_torque_el_nm: float
    friction_torque_az_nm: float
    friction_torque_el_nm: float


class GimbalPedestal:
    """
    2-Axis (Azimuth / Elevation) direct-drive gimbal assembly.
    Equipped with direct-drive BLDC torque motors and 26-bit optical encoders.
    """

    def __init__(
        self,
        cable_material: str = "standard_pvc",
        az_inertia_kg_m2: float = 0.42,
        el_inertia_kg_m2: float = 0.26,
        motor_torque_limit_nm: float = 45.0
    ):
        self.J_az = az_inertia_kg_m2
        self.J_el = el_inertia_kg_m2
        self.torque_limit = motor_torque_limit_nm
        
        # Cable harness model
        self.cable_model = CableHysteresisModel(material_key=cable_material)
        
        # Kinematic state (radians)
        self.az = 0.0          # rad
        self.az_vel = 0.0      # rad/s
        self.el = math.radians(15.0)  # rad (initial 15 deg elevation)
        self.el_vel = 0.0      # rad/s
        
        # Mechanical limits
        self.el_min_rad = math.radians(-15.0)
        self.el_max_rad = math.radians(88.0)
        
        # Nominal friction at +20°C
        self.b_viscous_nominal = 0.045  # N*m*s/rad
        self.coulomb_nominal = 0.12    # N*m

    @property
    def az_deg(self) -> float:
        return math.degrees(self.az)

    @property
    def el_deg(self) -> float:
        return math.degrees(self.el)

    def compute_bearing_friction(self, vel_rad_s: float, temperature_c: float) -> float:
        """
        Calculates temperature-dependent bearing friction.
        At -40°C, mineral lubricant viscosity escalates drastically.
        """
        delta_t = max(0.0, 20.0 - temperature_c)
        visc_multiplier = 1.0 + 0.08 * delta_t + 0.002 * (delta_t ** 2)
        
        b_viscous = self.b_viscous_nominal * visc_multiplier
        coulomb = self.coulomb_nominal * visc_multiplier
        
        f_coulomb = coulomb * math.tanh(vel_rad_s / 0.005)
        f_viscous = b_viscous * vel_rad_s
        return f_coulomb + f_viscous

    def step(
        self,
        dt: float,
        commanded_torque_az: float,
        commanded_torque_el: float,
        wind_torque_az: float,
        wind_torque_el: float,
        temperature_c: float
    ) -> GimbalState:
        """
        Integrates the equations of motion for both axes by dt seconds.
        """
        tau_m_az = max(-self.torque_limit, min(self.torque_limit, commanded_torque_az))
        tau_m_el = max(-self.torque_limit, min(self.torque_limit, commanded_torque_el))
        
        # 1. Cable harness resisting torques
        tau_cable_az, _ = self.cable_model.compute_restoring_torque(
            self.az, self.az_vel, temperature_c, dt, axis="az"
        )
        tau_cable_el, _ = self.cable_model.compute_restoring_torque(
            self.el, self.el_vel, temperature_c, dt, axis="el"
        )
        
        # 2. Temperature-degraded bearing friction
        tau_fric_az = self.compute_bearing_friction(self.az_vel, temperature_c)
        tau_fric_el = self.compute_bearing_friction(self.el_vel, temperature_c)
        
        # 3. Elevation gravity unbalance torque
        tau_grav_el = 0.35 * math.cos(self.el)
        
        # 4. Total net dynamics: J * ddot(theta) = tau_motor - tau_resisting
        net_torque_az = tau_m_az - tau_cable_az - tau_fric_az + wind_torque_az
        net_torque_el = tau_m_el - tau_cable_el - tau_fric_el - tau_grav_el + wind_torque_el
        
        acc_az = net_torque_az / self.J_az
        acc_el = net_torque_el / self.J_el
        
        # Semi-implicit Euler integration
        self.az_vel += acc_az * dt
        self.az += self.az_vel * dt
        
        self.el_vel += acc_el * dt
        self.el += self.el_vel * dt
        
        # Hard limits on elevation axis
        if self.el > self.el_max_rad:
            self.el = self.el_max_rad
            self.el_vel = 0.0
        elif self.el < self.el_min_rad:
            self.el = self.el_min_rad
            self.el_vel = 0.0
            
        return GimbalState(
            az_rad=self.az,
            az_deg=round(math.degrees(self.az), 4),
            az_vel_rad_s=round(self.az_vel, 4),
            az_acc_rad_s2=round(acc_az, 4),
            el_rad=self.el,
            el_deg=round(math.degrees(self.el), 4),
            el_vel_rad_s=round(self.el_vel, 4),
            el_acc_rad_s2=round(acc_el, 4),
            motor_torque_az_nm=round(tau_m_az, 3),
            motor_torque_el_nm=round(tau_m_el, 3),
            cable_torque_az_nm=round(tau_cable_az, 3),
            cable_torque_el_nm=round(tau_cable_el, 3),
            wind_torque_az_nm=round(wind_torque_az, 3),
            wind_torque_el_nm=round(wind_torque_el, 3),
            friction_torque_az_nm=round(tau_fric_az, 3),
            friction_torque_el_nm=round(tau_fric_el, 3)
        )

    def reset(self, initial_az_deg: float = 0.0, initial_el_deg: float = 15.0):
        self.az = math.radians(initial_az_deg)
        self.az_vel = 0.0
        self.el = math.radians(initial_el_deg)
        self.el_vel = 0.0
        self.cable_model.reset()
