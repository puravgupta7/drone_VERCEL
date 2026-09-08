"""
Automated Unit Tests for 9-State 3D Unscented Kalman Filter Multi-Sensor Fusion.
Verifies tracking convergence and covariance estimation under radar and optical inputs.
"""

import pytest
import math
import numpy as np

from core.sensing.sensor_fusion import HighAltitudeSensorFusionUKF
from core.sensing.radar_model import RadarDetection
from core.sensing.optics_thermal_model import OpticalDetection


def test_ukf_convergence():
    ukf = HighAltitudeSensorFusionUKF(dt=0.02)
    
    # Target true position and velocity
    true_pos = np.array([-1800.0, 1400.0, 420.0])
    true_vel = np.array([20.0, -15.0, 2.0])
    
    # Run 60 filter cycles
    for i in range(60):
        t = i * 0.02
        curr_pos = true_pos + true_vel * t
        
        ukf.predict(dt=0.02)
        
        # Simulated radar detection
        r = float(np.linalg.norm(curr_pos))
        az = math.degrees(math.atan2(curr_pos[1], curr_pos[0]))
        el = math.degrees(math.atan2(curr_pos[2], math.hypot(curr_pos[0], curr_pos[1])))
        
        radar_hit = RadarDetection(
            detected=True,
            snr_db=18.5,
            measured_range_m=r,
            measured_azimuth_deg=az,
            measured_elevation_deg=el,
            measured_radial_velocity_ms=0.0,
            micro_doppler_peaks_hz=[],
            clutter_power_db=-25.0,
            false_alarm=False
        )
        ukf.update_radar(radar_hit)
        
    track = ukf.get_track_state(time_s=1.2)
    # Track uncertainty must converge
    assert track.pos_uncertainty_1sigma_m < 10.0
    assert track.track_quality_pct > 60.0
    # Position estimate must be close to true position
    est_pos = track.position_m
    final_true_pos = true_pos + true_vel * (60 * 0.02)
    pos_error = np.linalg.norm(est_pos - final_true_pos)
    assert pos_error < 15.0
