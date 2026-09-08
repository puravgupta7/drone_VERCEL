"""
Active Disturbance Rejection Control (ADRC) & Discrete Extended State Observer (LESO).
Implements real-time estimation and active rejection of unknown nonlinear disturbances
(sub-zero cable rigidity hysteresis, bearing friction, mountain wind gusts)
to achieve sub-50 micro-radian pointing and tracking accuracy.
Includes benchmark Classical PID controller for direct comparative evaluation.
"""

import math
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Dict, Any


@dataclass
class ControlOutput:
    commanded_torque_nm: float
    estimated_position_rad: float
    estimated_velocity_rad_s: float
    estimated_disturbance_nm: float  # z3 state from ESO in N*m
    tracking_error_rad: float
    tracking_error_urad: float      # Micro-radians (1 rad = 1,000,000 urad)


class DiscreteExtendedStateObserver:
    """
    Discrete-Time 3rd-Order Linear Extended State Observer (ZOH Parameterized).
    Estimates:
    z1 = Position (rad)
    z2 = Velocity (rad/s)
    z3 = Total Generalized Disturbance acceleration (rad/s^2)
    """

    def __init__(self, omega_o: float, b0: float, dt: float = 0.002):
        self.omega_o = omega_o
        self.b0 = b0
        self.dt = dt
        
        # Gao's discrete pole placement at z_p = exp(-omega_o * dt)
        self.zp = math.exp(-omega_o * dt)
        self.l1 = 1.0 - (self.zp ** 3)
        self.l2 = (3.0 / (2.0 * dt)) * ((1.0 - self.zp) ** 2) * (1.0 + self.zp)
        self.l3 = (1.0 / (dt ** 2)) * ((1.0 - self.zp) ** 3)
        
        # Observer state vector [z1, z2, z3]
        self.z = np.zeros(3, dtype=float)

    def update(self, y_measured: float, u_control: float) -> np.ndarray:
        """
        Updates observer with current output measurement y and applied control u.
        Uses predictor-corrector structure for unconditional numerical stability.
        """
        h = self.dt
        # 1. State prediction (continuous double integrator + disturbance state)
        pred_z0 = self.z[0] + self.z[1] * h + 0.5 * self.z[2] * (h ** 2) + 0.5 * self.b0 * u_control * (h ** 2)
        pred_z1 = self.z[1] + self.z[2] * h + self.b0 * u_control * h
        pred_z2 = self.z[2]
        
        # 2. Measurement innovation correction
        e = y_measured - pred_z0
        
        self.z[0] = pred_z0 + self.l1 * e
        self.z[1] = pred_z1 + self.l2 * e
        self.z[2] = pred_z2 + self.l3 * e
        
        return self.z

    def reset(self, initial_position: float = 0.0):
        self.z = np.zeros(3, dtype=float)
        self.z[0] = initial_position


# Backward compatibility alias
LinearExtendedStateObserver = DiscreteExtendedStateObserver


class ActiveDisturbanceRejectionController:
    """
    Discrete Active Disturbance Rejection Controller (ADRC).
    Runs with high-rate servo bandwidth to eliminate cryogenic cable hysteresis.
    """

    def __init__(
        self,
        omega_c: float = 40.0,   # Controller bandwidth (rad/s)
        omega_o: float = 160.0,  # Observer bandwidth (rad/s)
        inertia: float = 0.42,   # Nominal axis inertia (kg*m^2)
        torque_limit: float = 45.0,
        dt_servo: float = 0.002  # 500 Hz internal servo rate
    ):
        self.inertia = inertia
        self.b0 = 1.0 / inertia
        self.torque_limit = torque_limit
        self.dt_servo = dt_servo
        
        self.eso = DiscreteExtendedStateObserver(omega_o=omega_o, b0=self.b0, dt=dt_servo)
        
        # State feedback gains (critically damped: s^2 + 2*omega_c*s + omega_c^2)
        self.kp = omega_c ** 2
        self.kd = 2.0 * omega_c

    def compute(
        self,
        reference_pos: float,
        reference_vel: float,
        measured_pos: float,
        previous_u: float,
        dt: float = 0.002
    ) -> ControlOutput:
        """
        Computes disturbance-rejecting torque command.
        """
        # Step 1: Update Extended State Observer
        z = self.eso.update(y_measured=measured_pos, u_control=previous_u)
        z1_pos = z[0]
        z2_vel = z[1]
        z3_dist = z[2]  # Disturbance in acceleration units (rad/s^2)
        
        # Step 2: Linear state feedback law
        e_pos = reference_pos - z1_pos
        e_vel = reference_vel - z2_vel
        u0 = self.kp * e_pos + self.kd * e_vel
        
        # Step 3: Total disturbance cancellation
        # Commanded torque: tau = (u0 - z3) / b0 = J * (u0 - z3)
        commanded_u = (u0 - z3_dist) / self.b0
        
        # Torque saturation
        saturated_u = max(-self.torque_limit, min(self.torque_limit, commanded_u))
        
        tracking_err = reference_pos - measured_pos
        tracking_err_urad = tracking_err * 1e6  # Convert to micro-radians
        
        return ControlOutput(
            commanded_torque_nm=saturated_u,
            estimated_position_rad=z1_pos,
            estimated_velocity_rad_s=z2_vel,
            estimated_disturbance_nm=z3_dist * self.inertia,
            tracking_error_rad=tracking_err,
            tracking_error_urad=tracking_err_urad
        )

    def reset(self, initial_position: float = 0.0):
        self.eso.reset(initial_position)


class ClassicalPIDController:
    """
    Standard Benchmark PID Controller with Anti-Windup.
    Represents conventional legacy gimbal tracking controllers.
    """

    def __init__(
        self,
        kp: float = 180.0,
        ki: float = 35.0,
        kd: float = 25.0,
        torque_limit: float = 45.0
    ):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.torque_limit = torque_limit
        
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(
        self,
        reference_pos: float,
        reference_vel: float,
        measured_pos: float,
        measured_vel: float,
        dt: float
    ) -> ControlOutput:
        error = reference_pos - measured_pos
        
        # Integral term with anti-windup clamping
        self.integral += error * dt
        self.integral = max(-1.0, min(1.0, self.integral))
        
        # Derivative on error
        d_error = (error - self.prev_error) / dt if dt > 0 else 0.0
        self.prev_error = error
        
        tau = self.kp * error + self.ki * self.integral + self.kd * d_error
        saturated_u = max(-self.torque_limit, min(self.torque_limit, tau))
        
        return ControlOutput(
            commanded_torque_nm=saturated_u,
            estimated_position_rad=measured_pos,
            estimated_velocity_rad_s=measured_vel,
            estimated_disturbance_nm=0.0,
            tracking_error_rad=error,
            tracking_error_urad=error * 1e6
        )

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0
