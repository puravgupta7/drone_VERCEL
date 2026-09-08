"""
High-Altitude Target Drone Dynamics & Micro-Doppler Modeling.
Simulates thin-air multirotor and fixed-wing aerodynamics, high RPM blade flashes,
acoustic pitch shifts, battery thermal depletion, and multi-profile 3D flight trajectories.
"""

import math
import numpy as np
from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class TargetState:
    time_s: float
    position: np.ndarray  # [x, y, z] in meters relative to anti-drone station
    velocity: np.ndarray  # [vx, vy, vz] in m/s
    acceleration: np.ndarray  # [ax, ay, az] in m/s^2
    range_m: float
    azimuth_deg: float
    elevation_deg: float
    rotor_rpm: float
    micro_doppler_shift_hz: float  # Blade tip Doppler shift for radar
    acoustic_fundamental_hz: float  # Drone acoustic blade pass frequency
    battery_charge_pct: float
    radar_cross_section_m2: float  # RCS in square meters


class HighAltitudeTargetDrone:
    """
    Simulates a rogue or hostile drone operating in thin high-altitude air.
    """

    def __init__(
        self,
        drone_type: str = "tactical_quadcopter",
        mass_kg: float = 4.2,
        rotor_radius_m: float = 0.18,
        num_rotors: int = 4,
        num_blades_per_rotor: int = 2,
        base_rcs_m2: float = 0.035,  # Stealthy small quadcopter RCS
        initial_pos: List[float] = None,
        trajectory_profile: str = "valley_ingress"
    ):
        self.drone_type = drone_type
        self.mass_kg = mass_kg
        self.rotor_radius_m = rotor_radius_m
        self.num_rotors = num_rotors
        self.num_blades_per_rotor = num_blades_per_rotor
        self.base_rcs_m2 = base_rcs_m2
        self.trajectory_profile = trajectory_profile
        
        # Initial 3D kinematics
        self.pos = np.array(initial_pos if initial_pos else [-1800.0, 1400.0, 420.0], dtype=float)
        self.vel = np.array([22.0, -16.0, 2.5], dtype=float)
        self.acc = np.zeros(3, dtype=float)
        
        self.time = 0.0
        self.battery_pct = 95.0
        
        # Nominal sea-level hover RPM
        self.rpm_sea_level = 5800.0

    def compute_rotor_rpm(self, air_density_kg_m3: float) -> float:
        """
        Calculates required rotor RPM in thin air.
        Thrust T ~ rho * (RPM)^2 -> RPM(alt) = RPM_0 * sqrt(rho_0 / rho).
        """
        rho_0 = 1.225
        ratio = max(0.4, air_density_kg_m3 / rho_0)
        rpm = self.rpm_sea_level * math.sqrt(1.0 / ratio)
        return min(11500.0, rpm)  # Max physical motor ceiling

    def update(self, dt: float, air_density_kg_m3: float, ambient_temp_c: float) -> TargetState:
        """
        Steps the drone trajectory forward by dt seconds.
        """
        self.time += dt
        t = self.time
        
        # Trajectory generation based on profile
        if self.trajectory_profile == "valley_ingress":
            # Terrain-masking weaving path entering through mountain pass
            speed = 24.0
            heading = math.atan2(-self.pos[1], -self.pos[0])
            # Add lateral sinusoidal evasion
            heading += 0.35 * math.sin(0.4 * t)
            
            vx = speed * math.cos(heading)
            vy = speed * math.sin(heading)
            # Altitude profile bobbing over ridge line
            vz = 4.0 * math.sin(0.25 * t) - 0.8
            
            target_vel = np.array([vx, vy, vz])
            self.acc = (target_vel - self.vel) / dt
            self.vel = target_vel
            self.pos += self.vel * dt
            
        elif self.trajectory_profile == "kamikaze_dive":
            # High-speed steep dive toward the base station (origin)
            dist_to_base = np.linalg.norm(self.pos)
            if dist_to_base > 50.0:
                direction = -self.pos / dist_to_base
                speed = min(48.0, 20.0 + 1.2 * t)
                target_vel = direction * speed
                self.acc = (target_vel - self.vel) / dt
                self.vel = target_vel
                self.pos += self.vel * dt
                
        elif self.trajectory_profile == "recon_loiter":
            # Circular loiter orbit at standoff range
            radius = 1600.0
            omega = 0.05  # rad/s
            alt = 550.0 + 20.0 * math.sin(0.1 * t)
            target_pos = np.array([
                radius * math.cos(omega * t),
                radius * math.sin(omega * t),
                alt
            ])
            self.vel = (target_pos - self.pos) / dt
            self.acc = np.array([-radius * (omega ** 2) * math.cos(omega * t), -radius * (omega ** 2) * math.sin(omega * t), 0.0])
            self.pos = target_pos

        # Thin-air aerodynamics calculations
        current_rpm = self.compute_rotor_rpm(air_density_kg_m3)
        
        # Radar micro-Doppler frequency shift from blade tips:
        # v_tip = Omega * R = (2 * pi * RPM / 60) * R
        # f_mD = 2 * v_tip * f_radar / c (for Ku-band 15 GHz: lambda = 0.02m)
        lambda_radar = 0.02
        v_tip = (2.0 * math.pi * current_rpm / 60.0) * self.rotor_radius_m
        micro_doppler_hz = (2.0 * v_tip) / lambda_radar
        
        # Blade Pass Frequency (acoustic signature)
        blade_pass_freq_hz = (current_rpm / 60.0) * self.num_blades_per_rotor
        
        # Battery drain in cold thin air:
        # Cold temperature drops electrochemical efficiency; higher RPM consumes more power:
        # P_motor ~ RPM^3 * rho
        power_drain_factor = (current_rpm / self.rpm_sea_level) ** 1.8
        temp_drain_penalty = 1.0 + max(0.0, (-ambient_temp_c) / 30.0)
        drain_rate_pct_per_sec = 0.045 * power_drain_factor * temp_drain_penalty
        self.battery_pct = max(0.0, self.battery_pct - drain_rate_pct_per_sec * dt)
        
        # Spherical coordinates relative to anti-drone station
        range_m = float(np.linalg.norm(self.pos))
        azimuth_deg = math.degrees(math.atan2(self.pos[1], self.pos[0]))
        # Clamp to [-180, 180]
        if azimuth_deg > 180.0:
            azimuth_deg -= 360.0
        elif azimuth_deg < -180.0:
            azimuth_deg += 360.0
            
        horiz_dist = math.hypot(self.pos[0], self.pos[1])
        elevation_deg = math.degrees(math.atan2(self.pos[2], horiz_dist))
        
        return TargetState(
            time_s=round(self.time, 2),
            position=np.round(self.pos, 2),
            velocity=np.round(self.vel, 2),
            acceleration=np.round(self.acc, 2),
            range_m=round(range_m, 1),
            azimuth_deg=round(azimuth_deg, 2),
            elevation_deg=round(elevation_deg, 2),
            rotor_rpm=round(current_rpm, 0),
            micro_doppler_shift_hz=round(micro_doppler_hz, 1),
            acoustic_fundamental_hz=round(blade_pass_freq_hz, 1),
            battery_charge_pct=round(self.battery_pct, 1),
            radar_cross_section_m2=self.base_rcs_m2
        )
