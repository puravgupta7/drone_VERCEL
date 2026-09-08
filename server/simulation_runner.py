"""
Master Multi-Physics Digital Twin Simulation Runner.
Integrates atmosphere, Paschen breakdown, wind gusts, target dynamics,
2-DOF gimbal mechanics (500 Hz internal servo sub-stepping), ADRC vs PID controllers,
3D radar, EO/IR sensor, UKF fusion, multi-node thermal network, health monitor, and neutralization.
Runs at 50 Hz to power the live 3D Command & Control workstation.
"""

import math
import time
import numpy as np
from typing import Dict, Any

from core.physics.atmosphere import AtmosphereModel, AtmosphericState
from core.physics.paschen import PaschenModel, DielectricBreakdownResult
from core.physics.wind_aerodynamics import WindAerodynamicsModel, WindState
from core.physics.target_dynamics import HighAltitudeTargetDrone, TargetState
from core.physics.cable_dynamics import CABLE_MATERIALS
from core.control.gimbal_model import GimbalPedestal, GimbalState
from core.control.adrc_controller import (
    ActiveDisturbanceRejectionController,
    ClassicalPIDController,
    ControlOutput
)
from core.sensing.radar_model import FMCWRadar3D, RadarDetection
from core.sensing.optics_thermal_model import EOIRThermalDirector, OpticalDetection
from core.sensing.sensor_fusion import HighAltitudeSensorFusionUKF, FusedTrackState
from core.thermal.thermal_network import MultiNodeThermalNetwork, SystemThermalStatus
from core.thermal.health_monitor import SubsystemHealthMonitor, SystemHealthReport
from core.neutralization.neutralization import NeutralizationSystem, JammingStatus, FireControlSolution


class HighAltitudeAntiDroneSystemSimulation:
    """
    Complete Digital Twin and Hardware-in-the-Loop (HIL) Simulator.
    """

    def __init__(self):
        # Operational Environment Parameters
        self.altitude_m = 5400.0        # Default: Siachen Glacier altitude
        self.delta_t_c = -20.0          # Winter Arctic/Highland offset (-35°C ambient)
        self.wind_speed_ms = 18.0       # Mountain gale
        self.wind_direction_deg = 35.0
        
        # Subsystem Flags
        self.adrc_active = True
        self.heaters_active = True
        self.paschen_limiter_active = True
        self.jamming_engaged = True
        self.cable_material_key = "mil_spec_ptfe"  # or "standard_pvc"
        
        # Instantiate Subsystems
        self.reinitialize()

    def reinitialize(self):
        """Reinitializes all simulation models with current configuration."""
        self.sim_time = 0.0
        
        # 1. Environment Models
        self.atmo = AtmosphereModel.compute(self.altitude_m, self.delta_t_c)
        self.wind = WindAerodynamicsModel(
            base_wind_speed_ms=self.wind_speed_ms,
            wind_direction_deg=self.wind_direction_deg
        )
        
        # 2. Target Drone
        self.target = HighAltitudeTargetDrone(
            drone_type="tactical_quadcopter",
            trajectory_profile="valley_ingress"
        )
        
        # Compute initial target line of sight
        r_init = float(np.linalg.norm(self.target.pos))
        az_init_deg = math.degrees(math.atan2(self.target.pos[1], self.target.pos[0]))
        horiz_init = math.hypot(self.target.pos[0], self.target.pos[1])
        el_init_deg = math.degrees(math.atan2(self.target.pos[2], max(1.0, horiz_init)))
        
        # 3. Gimbal Pedestals (ADRC primary and benchmark PID)
        self.dt_servo = 0.002
        self.gimbal = GimbalPedestal(cable_material=self.cable_material_key)
        self.gimbal.reset(initial_az_deg=az_init_deg, initial_el_deg=el_init_deg)
        
        self.gimbal_pid = GimbalPedestal(cable_material="standard_pvc")  # Stiff frozen cable benchmark
        self.gimbal_pid.reset(initial_az_deg=az_init_deg, initial_el_deg=el_init_deg)
        
        self.adrc_az = ActiveDisturbanceRejectionController(
            omega_c=70.0, omega_o=260.0, inertia=0.42, dt_servo=self.dt_servo
        )
        self.adrc_az.reset(initial_position=math.radians(az_init_deg))
        
        self.adrc_el = ActiveDisturbanceRejectionController(
            omega_c=70.0, omega_o=260.0, inertia=0.26, dt_servo=self.dt_servo
        )
        self.adrc_el.reset(initial_position=math.radians(el_init_deg))
        
        # Benchmark PID Controller
        self.pid_az = ClassicalPIDController(kp=180.0, ki=35.0, kd=25.0)
        self.pid_el = ClassicalPIDController(kp=180.0, ki=35.0, kd=25.0)
        
        # 4. Sensors
        self.radar = FMCWRadar3D()
        self.optics = EOIRThermalDirector(athermalization_enabled=True)
        self.fusion = HighAltitudeSensorFusionUKF(dt=0.02)
        
        # 5. Thermal & Health
        self.thermal = MultiNodeThermalNetwork()
        self.health = SubsystemHealthMonitor()
        
        # 6. Neutralization
        self.neutralization = NeutralizationSystem()
        
        # Previous control signals
        self.prev_u_adrc_az = 0.0
        self.prev_u_adrc_el = 0.0
        self.prev_u_pid_az = 0.0
        self.prev_u_pid_el = 0.0
        
        self.last_pid_error_urad = 380.0
        self.last_adrc_error_urad = 18.0

    def step(self, dt: float = 0.02) -> Dict[str, Any]:
        """
        Advances the entire multi-physics digital twin by dt seconds.
        Performs 10x sub-stepping (500 Hz) for mechanical gimbal integration.
        """
        self.sim_time += dt
        
        # 1. Update Atmosphere & Paschen Law
        atmo = AtmosphereModel.compute(self.altitude_m, self.delta_t_c)
        paschen = PaschenModel.calculate_breakdown(
            pressure_pa=atmo.pressure_pa,
            gap_distance_mm=1.0,
            altitude_m=self.altitude_m
        )
        
        # 2. Update Target Drone Dynamics in thin air
        target_state = self.target.update(
            dt=dt,
            air_density_kg_m3=atmo.density_kg_m3,
            ambient_temp_c=atmo.temperature_c
        )
        
        # 3. Update Mountain Wind Turbulence
        wind_state = self.wind.update(
            dt=dt,
            air_density_kg_m3=atmo.density_kg_m3,
            gimbal_az_deg=self.gimbal.az_deg,
            gimbal_el_deg=self.gimbal.el_deg
        )
        
        # 4. Sensors: Radar & Optical Scanning
        radar_hit = self.radar.scan(
            true_pos=target_state.position,
            true_vel=target_state.velocity,
            rcs_m2=target_state.radar_cross_section_m2,
            altitude_m=self.altitude_m,
            ambient_temp_k=atmo.temperature_k,
            micro_doppler_freq=target_state.micro_doppler_shift_hz
        )
        
        # Update optics front window defrost heater
        self.optics.update_window_thermal(
            dt=dt,
            ambient_temp_c=atmo.temperature_c,
            wind_speed_ms=wind_state.instantaneous_speed_ms,
            air_density_kg_m3=atmo.density_kg_m3
        )
        
        optical_hit = self.optics.track(
            true_pos=target_state.position,
            target_rpm=target_state.rotor_rpm,
            ambient_temp_c=atmo.temperature_c,
            altitude_m=self.altitude_m
        )
        
        # 5. Multi-Sensor 3D UKF Fusion
        self.fusion.predict(dt=dt)
        if radar_hit.detected:
            self.fusion.update_radar(radar_hit)
        if optical_hit.target_visible:
            self.fusion.update_optical(optical_hit)
            
        fused_track = self.fusion.get_track_state(self.sim_time)
        
        # 6. Gimbal Pointing Reference (Target Line-of-Sight)
        ref_az_rad = math.radians(fused_track.azimuth_deg)
        ref_el_rad = math.radians(fused_track.elevation_deg)
        
        r_horiz = math.hypot(fused_track.position_m[0], fused_track.position_m[1])
        ref_az_vel = (fused_track.position_m[0] * fused_track.velocity_ms[1] - fused_track.position_m[1] * fused_track.velocity_ms[0]) / max(1.0, r_horiz ** 2)
        ref_el_vel = (fused_track.velocity_ms[2] * r_horiz - fused_track.position_m[2] * (fused_track.position_m[0]*fused_track.velocity_ms[0] + fused_track.position_m[1]*fused_track.velocity_ms[1])/r_horiz) / max(1.0, fused_track.range_m ** 2)
        
        bearing_temp = self.thermal.temp["gimbal_bearings"]
        
        # 7. Internal Servo 500 Hz Sub-Stepping Loop (10 sub-steps per 50Hz frame)
        num_substeps = 10
        dt_sub = dt / num_substeps
        
        ctrl_adrc_az = None
        ctrl_adrc_el = None
        ctrl_pid_az = None
        ctrl_pid_el = None
        
        for sub in range(num_substeps):
            # Smooth reference trajectory interpolation
            sub_ref_az = ref_az_rad + ref_az_vel * (sub * dt_sub)
            sub_ref_el = ref_el_rad + ref_el_vel * (sub * dt_sub)
            
            # --- ADRC Path ---
            ctrl_adrc_az = self.adrc_az.compute(
                reference_pos=sub_ref_az,
                reference_vel=ref_az_vel,
                measured_pos=self.gimbal.az,
                previous_u=self.prev_u_adrc_az,
                dt=dt_sub
            )
            ctrl_adrc_el = self.adrc_el.compute(
                reference_pos=sub_ref_el,
                reference_vel=ref_el_vel,
                measured_pos=self.gimbal.el,
                previous_u=self.prev_u_adrc_el,
                dt=dt_sub
            )
            tau_adrc_az = ctrl_adrc_az.commanded_torque_nm
            tau_adrc_el = ctrl_adrc_el.commanded_torque_nm
            self.prev_u_adrc_az = tau_adrc_az
            self.prev_u_adrc_el = tau_adrc_el
            
            # --- Benchmark PID Path (running on parallel gimbal) ---
            ctrl_pid_az = self.pid_az.compute(
                reference_pos=sub_ref_az,
                reference_vel=ref_az_vel,
                measured_pos=self.gimbal_pid.az,
                measured_vel=self.gimbal_pid.az_vel,
                dt=dt_sub
            )
            ctrl_pid_el = self.pid_el.compute(
                reference_pos=sub_ref_el,
                reference_vel=ref_el_vel,
                measured_pos=self.gimbal_pid.el,
                measured_vel=self.gimbal_pid.el_vel,
                dt=dt_sub
            )
            tau_pid_az = ctrl_pid_az.commanded_torque_nm
            tau_pid_el = ctrl_pid_el.commanded_torque_nm
            self.prev_u_pid_az = tau_pid_az
            self.prev_u_pid_el = tau_pid_el
            
            # Select which torque commands drive the primary active gimbal
            tau_active_az = tau_adrc_az if self.adrc_active else tau_pid_az
            tau_active_el = tau_adrc_el if self.adrc_active else tau_pid_el
            
            # Step primary gimbal
            gimbal_state = self.gimbal.step(
                dt=dt_sub,
                commanded_torque_az=tau_active_az,
                commanded_torque_el=tau_active_el,
                wind_torque_az=wind_state.torque_disturbance_az_nm,
                wind_torque_el=wind_state.torque_disturbance_el_nm,
                temperature_c=bearing_temp
            )
            
            # Step benchmark PID gimbal
            self.gimbal_pid.step(
                dt=dt_sub,
                commanded_torque_az=tau_pid_az,
                commanded_torque_el=tau_pid_el,
                wind_torque_az=wind_state.torque_disturbance_az_nm,
                wind_torque_el=wind_state.torque_disturbance_el_nm,
                temperature_c=-35.0  # Cold frozen state
            )
            
        # Tracking jitter calculations (micro-radians)
        final_ref_az = ref_az_rad + ref_az_vel * dt
        final_ref_el = ref_el_rad + ref_el_vel * dt
        
        adrc_az_err_urad = abs((self.gimbal.az - final_ref_az + math.pi) % (2.0 * math.pi) - math.pi) * 1e6
        adrc_el_err_urad = abs(self.gimbal.el - final_ref_el) * 1e6
        adrc_total_urad = math.hypot(adrc_az_err_urad, adrc_el_err_urad)
        
        pid_az_err_urad = abs((self.gimbal_pid.az - final_ref_az + math.pi) % (2.0 * math.pi) - math.pi) * 1e6
        pid_el_err_urad = abs(self.gimbal_pid.el - final_ref_el) * 1e6
        pid_total_urad = math.hypot(pid_az_err_urad, pid_el_err_urad)
        
        self.last_adrc_error_urad = round(min(500.0, adrc_total_urad), 1)
        self.last_pid_error_urad = round(min(500.0, pid_total_urad), 1)
        
        # 8. Update Thermal Subsystems
        thermal_status = self.thermal.update(
            dt=dt,
            ambient_temp_c=atmo.temperature_c,
            wind_speed_ms=wind_state.instantaneous_speed_ms,
            air_density_ratio=atmo.density_ratio,
            rf_transmitter_active=self.jamming_engaged,
            rf_tx_power_rf_w=60.0,
            active_thermal_control_enabled=self.heaters_active
        )
        thermal_status.altitude_m = self.altitude_m
        
        # 9. Neutralization: Electronic Attack & Directed Energy Fire Control
        jamming_status = self.neutralization.compute_jamming(
            target_range_m=fused_track.range_m,
            paschen_max_rf_cw_w=paschen.max_rf_power_cw_watts if self.paschen_limiter_active else 1000.0,
            air_density_ratio=atmo.density_ratio,
            engage=self.jamming_engaged
        )
        
        fire_control = self.neutralization.compute_fire_control_solution(
            fused_pos=fused_track.position_m,
            fused_vel=fused_track.velocity_ms,
            gimbal_pointing_az_rad=self.gimbal.az,
            gimbal_pointing_el_rad=self.gimbal.el,
            air_density_kg_m3=atmo.density_kg_m3
        )
        
        # 10. Health Monitoring & Built-In-Test (BIT)
        working_v = math.sqrt(2.0 * 50.0 * jamming_status.rf_output_power_w) if jamming_status.active else 0.0
        health_report = self.health.evaluate(
            paschen_breakdown_voltage=paschen.breakdown_voltage_v_peak,
            working_rf_voltage=working_v,
            bearing_temp_c=bearing_temp,
            cable_temp_c=bearing_temp,
            battery_temp_c=self.thermal.temp["battery_pack"],
            rf_pa_temp_c=self.thermal.temp["rf_amplifier"],
            tracking_jitter_urad=self.last_adrc_error_urad if self.adrc_active else self.last_pid_error_urad,
            adrc_active=self.adrc_active
        )
        
        return {
            "time_s": round(self.sim_time, 2),
            "atmosphere": {
                "altitude_m": atmo.altitude_m,
                "temperature_c": atmo.temperature_c,
                "pressure_hpa": atmo.pressure_hpa,
                "density_kg_m3": atmo.density_kg_m3,
                "density_ratio": atmo.density_ratio,
                "speed_of_sound_ms": atmo.speed_of_sound_ms,
                "cooling_factor": atmo.convective_cooling_factor
            },
            "paschen": {
                "breakdown_voltage_v": paschen.breakdown_voltage_v_peak,
                "sea_level_v": paschen.sea_level_breakdown_voltage_v_peak,
                "derating_factor": paschen.dielectric_derating_factor,
                "max_rf_cw_w": paschen.max_rf_power_cw_watts,
                "risk": paschen.corona_risk_level
            },
            "wind": {
                "speed_ms": wind_state.instantaneous_speed_ms,
                "direction_deg": wind_state.direction_deg,
                "torque_az_nm": wind_state.torque_disturbance_az_nm,
                "torque_el_nm": wind_state.torque_disturbance_el_nm
            },
            "target": {
                "pos": target_state.position.tolist(),
                "vel": target_state.velocity.tolist(),
                "range_m": target_state.range_m,
                "az_deg": target_state.azimuth_deg,
                "el_deg": target_state.elevation_deg,
                "rpm": target_state.rotor_rpm,
                "micro_doppler_hz": target_state.micro_doppler_shift_hz,
                "battery_pct": target_state.battery_charge_pct
            },
            "sensors": {
                "radar": {
                    "detected": radar_hit.detected,
                    "snr_db": radar_hit.snr_db,
                    "measured_range_m": radar_hit.measured_range_m,
                    "measured_az_deg": radar_hit.measured_azimuth_deg,
                    "measured_el_deg": radar_hit.measured_elevation_deg,
                    "clutter_db": radar_hit.clutter_power_db
                },
                "optics": {
                    "visible": optical_hit.target_visible,
                    "snr": optical_hit.snr_optical,
                    "measured_az_deg": optical_hit.measured_azimuth_deg,
                    "measured_el_deg": optical_hit.measured_elevation_deg,
                    "jitter_urad": optical_hit.angular_jitter_urad,
                    "contrast_k": optical_hit.apparent_contrast_delta_k,
                    "frost_pct": optical_hit.window_frost_obscuration_pct,
                    "sharpness_pct": optical_hit.lens_focus_sharpness_pct
                },
                "fused_track": {
                    "pos": fused_track.position_m.tolist(),
                    "vel": fused_track.velocity_ms.tolist(),
                    "range_m": fused_track.range_m,
                    "az_deg": fused_track.azimuth_deg,
                    "el_deg": fused_track.elevation_deg,
                    "uncertainty_m": fused_track.pos_uncertainty_1sigma_m,
                    "quality_pct": fused_track.track_quality_pct
                }
            },
            "gimbal": {
                "az_deg": gimbal_state.az_deg,
                "el_deg": gimbal_state.el_deg,
                "motor_torque_az_nm": gimbal_state.motor_torque_az_nm,
                "motor_torque_el_nm": gimbal_state.motor_torque_el_nm,
                "cable_torque_az_nm": gimbal_state.cable_torque_az_nm,
                "cable_torque_el_nm": gimbal_state.cable_torque_el_nm,
                "friction_torque_az_nm": gimbal_state.friction_torque_az_nm,
                "adrc_estimated_dist_az_nm": round(ctrl_adrc_az.estimated_disturbance_nm, 3),
                "adrc_estimated_dist_el_nm": round(ctrl_adrc_el.estimated_disturbance_nm, 3),
                "adrc_error_urad": self.last_adrc_error_urad,
                "pid_error_urad": self.last_pid_error_urad,
                "active_controller": "ADRC" if self.adrc_active else "PID",
                "active_error_urad": self.last_adrc_error_urad if self.adrc_active else self.last_pid_error_urad
            },
            "thermal": {
                "ambient_temp_c": thermal_status.ambient_temp_c,
                "cooling_derate_pct": thermal_status.convective_cooling_derate_pct,
                "total_heater_w": thermal_status.total_heater_power_w,
                "nodes": {
                    k: {
                        "temp_c": v.temperature_c,
                        "target_c": v.target_temperature_c,
                        "heater_w": v.heater_power_w,
                        "status": v.status
                    }
                    for k, v in thermal_status.nodes.items()
                }
            },
            "neutralization": {
                "jamming_active": jamming_status.active,
                "rf_power_w": jamming_status.rf_output_power_w,
                "eirp_dbm": jamming_status.effective_isotropic_radiated_power_dbm,
                "js_ratio_db": jamming_status.jamming_to_signal_ratio_db,
                "link_disrupted": jamming_status.target_link_disrupted,
                "paschen_limited": jamming_status.paschen_limited,
                "fire_control": {
                    "locked": fire_control.target_locked,
                    "lead_point": fire_control.lead_point_m.tolist(),
                    "tof_s": fire_control.time_of_flight_s,
                    "aim_az_deg": fire_control.aiming_azimuth_deg,
                    "aim_el_deg": fire_control.aiming_elevation_deg,
                    "pointing_error_urad": fire_control.pointing_error_urad,
                    "kill_probability_pct": fire_control.kill_probability_pct
                }
            },
            "health": {
                "overall_health_pct": health_report.overall_health_pct,
                "system_readiness": health_report.system_readiness_level,
                "paschen_margin": health_report.paschen_safety_margin_factor,
                "bearing_wear_pct": health_report.bearing_wear_index_pct,
                "battery_soh_pct": health_report.battery_state_of_health_pct,
                "alerts": [
                    {
                        "severity": a.severity,
                        "subsystem": a.subsystem,
                        "message": a.message,
                        "recommendation": a.recommendation
                    }
                    for a in health_report.active_alerts
                ]
            }
        }
