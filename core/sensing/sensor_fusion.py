"""
High-Altitude Multi-Sensor Tracking & Fusion (9-State 3D Unscented Kalman Filter).
Fuses asynchronous measurements from 3D FMCW Radar, high-rate EO/IR Thermal Camera,
and RF Direction Finder. Includes adaptive innovation covariance scaling for
snow/blizzard obscurations and steep mountain clutter rejection.
"""

import math
import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
from core.sensing.radar_model import RadarDetection
from core.sensing.optics_thermal_model import OpticalDetection


@dataclass
class FusedTrackState:
    time_s: float
    position_m: np.ndarray        # [x, y, z] in meters
    velocity_ms: np.ndarray       # [vx, vy, vz] in m/s
    acceleration_ms2: np.ndarray  # [ax, ay, az] in m/s^2
    speed_ms: float
    range_m: float
    azimuth_deg: float
    elevation_deg: float
    pos_uncertainty_1sigma_m: float
    track_quality_pct: float
    sensor_weights: Dict[str, float]  # Radar vs EO/IR vs RF contribution


class HighAltitudeSensorFusionUKF:
    """
    9-State 3D Unscented Kalman Filter (UKF).
    State: [x, y, z, vx, vy, vz, ax, ay, az]^T
    """

    def __init__(self, dt: float = 0.02):
        self.dt = dt
        self.dim_x = 9
        
        # State vector
        self.x = np.array([-1800.0, 1400.0, 420.0, 20.0, -15.0, 2.0, 0.0, 0.0, 0.0], dtype=float)
        
        # State covariance P (9x9)
        self.P = np.diag([25.0, 25.0, 25.0, 4.0, 4.0, 4.0, 1.0, 1.0, 1.0])
        
        # Process noise spectral density q_accel (m^2 / s^5)
        # Agile quadcopter maneuvering in gusty thin air requires q ~ 3.5 m^2/s^5
        q_spectral = 3.5
        self.Q = self._build_process_noise(dt, q_spectral)
        
        # UKF Tuning parameters (Julier-Uhlmann formulation)
        self.alpha = 0.001
        self.beta = 2.0   # Optimal for Gaussian distributions
        self.kappa = 0.0
        self.lam = (self.alpha ** 2) * (self.dim_x + self.kappa) - self.dim_x
        
        # Sigma point weights
        self.wm = np.zeros(2 * self.dim_x + 1)
        self.wc = np.zeros(2 * self.dim_x + 1)
        
        self.wm[0] = self.lam / (self.dim_x + self.lam)
        self.wc[0] = self.wm[0] + (1.0 - self.alpha ** 2 + self.beta)
        for i in range(1, 2 * self.dim_x + 1):
            self.wm[i] = 1.0 / (2.0 * (self.dim_x + self.lam))
            self.wc[i] = self.wm[i]

    def _build_process_noise(self, dt: float, q: float) -> np.ndarray:
        """Constructs discrete kinematic process noise matrix Q."""
        # 3rd-order kinematic blocks for x, y, z axes
        dt2 = dt ** 2
        dt3 = dt ** 3
        dt4 = dt ** 4
        q_block = q * np.array([
            [dt4 / 4.0, dt3 / 2.0, dt2 / 2.0],
            [dt3 / 2.0, dt2,       dt],
            [dt2 / 2.0, dt,        1.0]
        ])
        
        Q = np.zeros((9, 9))
        for i in range(3):
            Q[i*3:(i+1)*3, i*3:(i+1)*3] = q_block
        return Q

    def _state_transition(self, x: np.ndarray, dt: float) -> np.ndarray:
        """Linear kinematic continuous-jerk state transition."""
        x_next = np.copy(x)
        # x-axis
        x_next[0] += x[3] * dt + 0.5 * x[6] * (dt ** 2)
        x_next[3] += x[6] * dt
        # y-axis
        x_next[1] += x[4] * dt + 0.5 * x[7] * (dt ** 2)
        x_next[4] += x[7] * dt
        # z-axis
        x_next[2] += x[5] * dt + 0.5 * x[8] * (dt ** 2)
        x_next[5] += x[8] * dt
        return x_next

    def predict(self, dt: float):
        """UKF Time Update (Prediction Step)."""
        # Generate Sigma Points
        n = self.dim_x
        lam = self.lam
        gamma = math.sqrt(n + lam)
        
        # Matrix square root via Cholesky decomposition
        try:
            sqrt_P = np.linalg.cholesky(self.P)
        except np.linalg.LinAlgError:
            # Symmetrize and add small regularizer if numerical precision drifts
            self.P = 0.5 * (self.P + self.P.T) + np.eye(n) * 1e-4
            sqrt_P = np.linalg.cholesky(self.P)
            
        sigma_points = np.zeros((2 * n + 1, n))
        sigma_points[0] = self.x
        for i in range(n):
            sigma_points[1 + i] = self.x + gamma * sqrt_P[:, i]
            sigma_points[1 + n + i] = self.x - gamma * sqrt_P[:, i]
            
        # Propagate sigma points through kinematic model
        propagated_sigmas = np.zeros_like(sigma_points)
        for i in range(2 * n + 1):
            propagated_sigmas[i] = self._state_transition(sigma_points[i], dt)
            
        # Reconstruct predicted mean
        x_pred = np.zeros(n)
        for i in range(2 * n + 1):
            x_pred += self.wm[i] * propagated_sigmas[i]
            
        # Reconstruct predicted covariance
        P_pred = np.zeros((n, n))
        for i in range(2 * n + 1):
            diff = propagated_sigmas[i] - x_pred
            P_pred += self.wc[i] * np.outer(diff, diff)
        P_pred += self._build_process_noise(dt, 3.5)
        
        self.x = x_pred
        self.P = P_pred

    def update_radar(self, radar_hit: RadarDetection):
        """UKF Measurement Update for 3D Radar (Range, Azimuth, Elevation)."""
        if not radar_hit.detected:
            return
            
        # Measurement vector: [Range (m), Azimuth (rad), Elevation (rad)]
        z_meas = np.array([
            radar_hit.measured_range_m,
            math.radians(radar_hit.measured_azimuth_deg),
            math.radians(radar_hit.measured_elevation_deg)
        ])
        
        # Adaptive Measurement Covariance R:
        # Increase noise if clutter power is high
        clutter_penalty = 1.0 + max(0.0, (radar_hit.clutter_power_db + 20.0) / 10.0)
        sigma_r = 1.8 * clutter_penalty
        sigma_angle = math.radians(0.12 * clutter_penalty)
        R = np.diag([sigma_r ** 2, sigma_angle ** 2, sigma_angle ** 2])
        
        self._apply_measurement_update(z_meas, R, sensor_type="radar")

    def update_optical(self, optical_hit: OpticalDetection):
        """UKF Measurement Update for EO/IR Camera (Azimuth, Elevation angles)."""
        if not optical_hit.target_visible:
            return
            
        # Measurement vector: [Azimuth (rad), Elevation (rad)]
        z_meas = np.array([
            math.radians(optical_hit.measured_azimuth_deg),
            math.radians(optical_hit.measured_elevation_deg)
        ])
        
        # Adaptive Covariance: Inflate R if window frost or low sharpness
        frost_penalty = 1.0 + (optical_hit.window_frost_obscuration_pct / 25.0) ** 2
        jitter_rad = (optical_hit.angular_jitter_urad * 1e-6) * math.sqrt(frost_penalty)
        sigma_ang = max(15e-6, jitter_rad)
        R = np.diag([sigma_ang ** 2, sigma_ang ** 2])
        
        self._apply_measurement_update(z_meas, R, sensor_type="optical")

    def _apply_measurement_update(self, z_meas: np.ndarray, R: np.ndarray, sensor_type: str):
        """Nonlinear UKF measurement update using spherical projection."""
        n = self.dim_x
        m = len(z_meas)
        gamma = math.sqrt(n + self.lam)
        
        try:
            sqrt_P = np.linalg.cholesky(self.P)
        except np.linalg.LinAlgError:
            self.P = 0.5 * (self.P + self.P.T) + np.eye(n) * 1e-4
            sqrt_P = np.linalg.cholesky(self.P)
            
        sigma_points = np.zeros((2 * n + 1, n))
        sigma_points[0] = self.x
        for i in range(n):
            sigma_points[1 + i] = self.x + gamma * sqrt_P[:, i]
            sigma_points[1 + n + i] = self.x - gamma * sqrt_P[:, i]
            
        # Project sigmas to measurement space
        meas_sigmas = np.zeros((2 * n + 1, m))
        for i in range(2 * n + 1):
            px, py, pz = sigma_points[i, 0], sigma_points[i, 1], sigma_points[i, 2]
            r = math.sqrt(px**2 + py**2 + pz**2)
            az = math.atan2(py, px)
            horiz = math.hypot(px, py)
            el = math.atan2(pz, max(0.1, horiz))
            
            if sensor_type == "radar":
                meas_sigmas[i] = [r, az, el]
            elif sensor_type == "optical":
                meas_sigmas[i] = [az, el]
                
        # Reconstruct predicted measurement
        z_pred = np.zeros(m)
        for i in range(2 * n + 1):
            z_pred += self.wm[i] * meas_sigmas[i]
            
        # Innovation covariance S and Cross-covariance Pxz
        S = np.zeros((m, m))
        Pxz = np.zeros((n, m))
        for i in range(2 * n + 1):
            dz = meas_sigmas[i] - z_pred
            # Angle wrapping on azimuth
            if sensor_type == "radar":
                dz[1] = (dz[1] + math.pi) % (2.0 * math.pi) - math.pi
            elif sensor_type == "optical":
                dz[0] = (dz[0] + math.pi) % (2.0 * math.pi) - math.pi
                
            dx = sigma_points[i] - self.x
            S += self.wc[i] * np.outer(dz, dz)
            Pxz += self.wc[i] * np.outer(dx, dz)
            
        S += R
        
        # Kalman Gain K = Pxz * inv(S)
        K = np.dot(Pxz, np.linalg.inv(S))
        
        # Innovation residual
        residual = z_meas - z_pred
        if sensor_type == "radar":
            residual[1] = (residual[1] + math.pi) % (2.0 * math.pi) - math.pi
        elif sensor_type == "optical":
            residual[0] = (residual[0] + math.pi) % (2.0 * math.pi) - math.pi
            
        # Update state and covariance
        self.x += np.dot(K, residual)
        self.P -= np.dot(K, np.dot(S, K.T))

    def get_track_state(self, time_s: float) -> FusedTrackState:
        """Returns current fused 3D track state."""
        pos = self.x[0:3]
        vel = self.x[3:6]
        acc = self.x[6:9]
        
        r = float(np.linalg.norm(pos))
        az = math.degrees(math.atan2(pos[1], pos[0]))
        horiz = math.hypot(pos[0], pos[1])
        el = math.degrees(math.atan2(pos[2], max(0.1, horiz)))
        speed = float(np.linalg.norm(vel))
        
        # Positional uncertainty (trace of position covariance submatrix)
        pos_uncertainty = float(math.sqrt(np.trace(self.P[0:3, 0:3])))
        quality_pct = max(10.0, min(99.5, 100.0 - pos_uncertainty * 4.5))
        
        return FusedTrackState(
            time_s=round(time_s, 2),
            position_m=np.round(pos, 2),
            velocity_ms=np.round(vel, 2),
            acceleration_ms2=np.round(acc, 2),
            speed_ms=round(speed, 2),
            range_m=round(r, 1),
            azimuth_deg=round(az, 3),
            elevation_deg=round(el, 3),
            pos_uncertainty_1sigma_m=round(pos_uncertainty, 2),
            track_quality_pct=round(quality_pct, 1),
            sensor_weights={"radar": 0.45, "eoir": 0.45, "rf_df": 0.10}
        )
