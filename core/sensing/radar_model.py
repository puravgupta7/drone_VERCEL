"""
3D FMCW Anti-Drone Radar Model for High-Altitude Mountainous Deployments.
Simulates X/Ku-band (15 GHz) pulse-Doppler FMCW radar, incorporating
altitude atmospheric attenuation, steep slope snow/rock clutter, CFAR detection,
and micro-Doppler spectral extraction.
"""

import math
import random
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any


@dataclass
class RadarDetection:
    detected: bool
    snr_db: float
    measured_range_m: float
    measured_azimuth_deg: float
    measured_elevation_deg: float
    measured_radial_velocity_ms: float
    micro_doppler_peaks_hz: list
    clutter_power_db: float
    false_alarm: bool


class FMCWRadar3D:
    """
    3D Pulse-Doppler / FMCW Radar Subsystem.
    Frequency: 15.2 GHz (Ku-band)
    Peak Transmit Power: 60 W
    Antenna Gain: 28 dBi (Planar Array)
    Search Volume: Azimuth 360 deg mechanical, Elevation -10 deg to +60 deg
    """

    def __init__(
        self,
        center_freq_ghz: float = 15.2,
        peak_tx_power_w: float = 60.0,
        antenna_gain_dbi: float = 28.0,
        bandwidth_mhz: float = 120.0,
        noise_figure_db: float = 4.5
    ):
        self.freq_hz = center_freq_ghz * 1e9
        self.c = 299792458.0
        self.wavelength = self.c / self.freq_hz
        self.tx_power_w = peak_tx_power_w
        self.antenna_gain_linear = 10.0 ** (antenna_gain_dbi / 10.0)
        self.bandwidth_hz = bandwidth_mhz * 1e6
        self.noise_figure_linear = 10.0 ** (noise_figure_db / 10.0)
        
        # Thermal noise floor k*T*B
        self.k_boltzmann = 1.380649e-23
        
        # Measurement noise standards (1-sigma)
        self.sigma_range_m = 1.8
        self.sigma_angle_deg = 0.12  # ~2 mrad angular accuracy
        self.sigma_vel_ms = 0.35

    def compute_atmospheric_attenuation_db_per_km(self, altitude_m: float) -> float:
        """
        ITU-R P.676 model approximation for oxygen and water vapor attenuation at 15 GHz.
        At high altitude (low pressure/density), atmospheric attenuation drops significantly.
        Sea level: ~0.08 dB/km; at 5000m: ~0.035 dB/km.
        """
        alt_km = altitude_m / 1000.0
        base_attenuation = 0.08
        attenuation_db_km = base_attenuation * math.exp(-alt_km / 5.5)
        return max(0.015, attenuation_db_km)

    def compute_snow_clutter_db(self, elevation_deg: float, altitude_m: float) -> float:
        """
        High-altitude mountain clutter:
        Steep snowy/rocky ridges scatter radar energy. At low elevation angles (< 5 deg),
        severe backscatter clutter occurs.
        """
        if elevation_deg > 15.0:
            return -35.0  # Negligible clutter looking up into clear sky
        elif elevation_deg > 3.0:
            return -22.0  # Moderate terrain grazing clutter
        else:
            return -8.0   # Severe mountain backscatter clutter

    def scan(
        self,
        true_pos: np.ndarray,
        true_vel: np.ndarray,
        rcs_m2: float,
        altitude_m: float,
        ambient_temp_k: float,
        micro_doppler_freq: float
    ) -> RadarDetection:
        """
        Performs radar pulse transmission, backscatter reception, and CFAR detection.
        """
        r_true = float(np.linalg.norm(true_pos))
        az_true = math.degrees(math.atan2(true_pos[1], true_pos[0]))
        horiz_dist = math.hypot(true_pos[0], true_pos[1])
        el_true = math.degrees(math.atan2(true_pos[2], horiz_dist))
        
        # Radial velocity: v_r = (pos . vel) / |pos|
        v_radial_true = float(np.dot(true_pos, true_vel) / max(1.0, r_true))
        
        # 1. Atmospheric two-way path attenuation
        atten_db_km = self.compute_atmospheric_attenuation_db_per_km(altitude_m)
        total_two_way_atten_db = 2.0 * (r_true / 1000.0) * atten_db_km
        atten_linear = 10.0 ** (-total_two_way_atten_db / 10.0)
        
        # 2. Radar Range Equation
        # P_r = (P_t * G^2 * lambda^2 * sigma) / ((4 * pi)^3 * R^4) * Attenuation
        numerator = self.tx_power_w * (self.antenna_gain_linear ** 2) * (self.wavelength ** 2) * rcs_m2
        denominator = ((4.0 * math.pi) ** 3) * (r_true ** 4)
        p_recv = (numerator / denominator) * atten_linear
        
        # 3. Noise Floor: P_noise = k * T * B * F
        p_noise = self.k_boltzmann * ambient_temp_k * self.bandwidth_hz * self.noise_figure_linear
        
        # 4. Mountain Terrain Clutter
        clutter_db = self.compute_snow_clutter_db(el_true, altitude_m)
        p_clutter = p_noise * (10.0 ** (clutter_db / 10.0))
        
        # Signal to Interference + Noise Ratio (SINR)
        sinr = p_recv / (p_noise + p_clutter)
        snr_db = 10.0 * math.log10(max(1e-12, sinr))
        
        # CFAR Detection threshold (typical 11.5 dB for Pd > 0.90)
        cfar_threshold_db = 11.5
        detected = (snr_db >= cfar_threshold_db)
        
        if detected:
            # Corrupt true parameters with radar measurement noise
            meas_r = max(1.0, r_true + random.gauss(0.0, self.sigma_range_m))
            meas_az = az_true + random.gauss(0.0, self.sigma_angle_deg)
            meas_el = el_true + random.gauss(0.0, self.sigma_angle_deg)
            meas_vr = v_radial_true + random.gauss(0.0, self.sigma_vel_ms)
            
            # Micro-Doppler peaks (blade tips + body)
            m_doppler_peaks = [
                round(v_radial_true * (2.0 / self.wavelength), 1),
                round(v_radial_true * (2.0 / self.wavelength) + micro_doppler_freq, 1),
                round(v_radial_true * (2.0 / self.wavelength) - micro_doppler_freq, 1)
            ]
            
            return RadarDetection(
                detected=True,
                snr_db=round(snr_db, 1),
                measured_range_m=round(meas_r, 2),
                measured_azimuth_deg=round(meas_az, 3),
                measured_elevation_deg=round(meas_el, 3),
                measured_radial_velocity_ms=round(meas_vr, 2),
                micro_doppler_peaks_hz=m_doppler_peaks,
                clutter_power_db=round(clutter_db, 1),
                false_alarm=False
            )
        else:
            return RadarDetection(
                detected=False,
                snr_db=round(snr_db, 1),
                measured_range_m=0.0,
                measured_azimuth_deg=0.0,
                measured_elevation_deg=0.0,
                measured_radial_velocity_ms=0.0,
                micro_doppler_peaks_hz=[],
                clutter_power_db=round(clutter_db, 1),
                false_alarm=False
            )
