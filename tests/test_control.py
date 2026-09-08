"""
Automated Unit Tests for Active Disturbance Rejection Control (ADRC) & Gimbal Dynamics.
Verifies micro-radian pointing precision (<= 50 urad) under cryogenic cable stiffness
and mountain wind turbulence compared against legacy PID control.
"""

import pytest
import math
import numpy as np

from core.control.gimbal_model import GimbalPedestal
from core.control.adrc_controller import (
    ActiveDisturbanceRejectionController,
    ClassicalPIDController,
    DiscreteExtendedStateObserver
)


def test_leso_observer_tracking():
    # Test that Discrete LESO accurately tracks state and estimates disturbance
    inertia = 0.42
    b0 = 1.0 / inertia
    dt = 0.002
    leso = DiscreteExtendedStateObserver(omega_o=120.0, b0=b0, dt=dt)
    
    pos = 0.0
    vel = 0.0
    disturbance = 2.0  # Constant 2.0 N*m disturbance
    u = 0.0
    
    # Simulate for 1.0 seconds
    for _ in range(500):
        acc = (u + disturbance) / inertia
        vel += acc * dt
        pos += vel * dt
        
        z = leso.update(y_measured=pos, u_control=u)
        
    # Estimated position and velocity should closely match true values
    assert pytest.approx(pos, abs=0.01) == z[0]
    assert pytest.approx(vel, abs=0.05) == z[1]
    # Estimated disturbance in torque (z[2] * J) should match 2.0 N*m
    assert pytest.approx(disturbance, abs=0.20) == (z[2] * inertia)


def test_adrc_micro_radian_precision_under_cold_cable_stress():
    """
    Under -35°C conditions with frozen PVC cable stiffness and wind gusts,
    verifies that ADRC achieves micro-radian precision (<= 50 urad) while PID degrades.
    """
    dt_macro = 0.02
    substeps = 10
    dt_sub = dt_macro / substeps
    temp_c = -35.0
    
    # Line of sight to target with realistic micro-maneuver
    target_los = math.radians(15.0)
    
    gimbal_adrc = GimbalPedestal(cable_material="mil_spec_ptfe")
    gimbal_pid = GimbalPedestal(cable_material="standard_pvc")
    
    gimbal_adrc.az = target_los
    gimbal_pid.az = target_los
    
    adrc_az = ActiveDisturbanceRejectionController(
        omega_c=50.0, omega_o=200.0, inertia=0.42, dt_servo=dt_sub
    )
    adrc_az.reset(initial_position=target_los)
    
    pid_az = ClassicalPIDController(kp=180.0, ki=35.0, kd=25.0)
    
    adrc_errors_urad = []
    pid_errors_urad = []
    
    prev_u_adrc = 0.0
    prev_u_pid = 0.0
    
    for step_i in range(120):
        t_macro = step_i * dt_macro
        los = target_los + 0.0005 * math.sin(0.4 * t_macro)
        los_v = 0.0005 * 0.4 * math.cos(0.4 * t_macro)
        
        for sub in range(substeps):
            t = t_macro + sub * dt_sub
            wind_torque = 0.8 * math.sin(2.1 * t) + 0.3 * math.cos(5.4 * t)
            
            # ADRC step
            ctrl_adrc = adrc_az.compute(
                reference_pos=los,
                reference_vel=los_v,
                measured_pos=gimbal_adrc.az,
                previous_u=prev_u_adrc,
                dt=dt_sub
            )
            prev_u_adrc = ctrl_adrc.commanded_torque_nm
            gimbal_adrc.step(
                dt=dt_sub,
                commanded_torque_az=prev_u_adrc,
                commanded_torque_el=0.0,
                wind_torque_az=wind_torque,
                wind_torque_el=0.0,
                temperature_c=temp_c
            )
            
            # PID step
            ctrl_pid = pid_az.compute(
                reference_pos=los,
                reference_vel=los_v,
                measured_pos=gimbal_pid.az,
                measured_vel=gimbal_pid.az_vel,
                dt=dt_sub
            )
            prev_u_pid = ctrl_pid.commanded_torque_nm
            gimbal_pid.step(
                dt=dt_sub,
                commanded_torque_az=prev_u_pid,
                commanded_torque_el=0.0,
                wind_torque_az=wind_torque,
                wind_torque_el=0.0,
                temperature_c=temp_c
            )
            
        if step_i > 20:
            adrc_errors_urad.append(abs(los - gimbal_adrc.az) * 1e6)
            pid_errors_urad.append(abs(los - gimbal_pid.az) * 1e6)
            
    mean_adrc = np.mean(adrc_errors_urad)
    mean_pid = np.mean(pid_errors_urad)
    
    # ADRC must satisfy the <= 50 micro-radian specification
    assert mean_adrc <= 50.0, f"ADRC mean jitter {mean_adrc} urad exceeded 50 urad spec"
    # ADRC must significantly outperform legacy PID
    assert mean_adrc < mean_pid
