"""
High-Altitude Dual-Band Electro-Optical / Infrared (EO/IR) Sensor Model.
Simulates Medium-Wave Infrared (MWIR 3-5 um) radiometric thermal imaging,
cold-background contrast degradation over snow, optical lens athermalization drift,
and front-window de-icing thermal balance.
"""

import math
import random
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Dict, Any


@dataclass
class OpticalDetection:
    target_visible: bool
    snr_optical: float
    measured_azimuth_deg: float
    measured_elevation_deg: float
    angular_jitter_urad: float      # Instantaneous centroiding noise (micro-radians)
    apparent_contrast_delta_k: float # Temperature delta after atmospheric propagation
    lens_focus_sharpness_pct: float  # 100% = perfectly focused
    window_frost_obscuration_pct: float # 0% = clear, 100% = fully frozen


class EOIRThermalDirector:
    """
    Dual-aperture Electro-Optical / Thermal Infrared Sensor Pod.
    - MWIR Cooled InSb / MCT Focal Plane Array (640x512, 15 um pitch)
    - Continuous Optical Zoom: 2.5 deg to 35 deg FOV
    - Integrated ITO conductive window defrost heater
    - Active motor-driven athermalization lens group
    """

    def __init__(
        self,
        focal_length_mm: float = 250.0,
        pixel_pitch_um: float = 15.0,
        aperture_diameter_mm: float = 75.0,
        athermalization_enabled: bool = True
    ):
        self.focal_length_mm = focal_length_mm
        self.pixel_pitch_um = pixel_pitch_um
        self.aperture_mm = aperture_diameter_mm
        self.athermalization_enabled = athermalization_enabled
        
        # Base instantaneous Field of View (IFOV) in micro-radians:
        # IFOV = pixel_pitch / focal_length = 15e-6 / 0.25 = 60 micro-radians
        self.ifov_urad = (self.pixel_pitch_um * 1e-6) / (self.focal_length_mm * 1e-3) * 1e6
        
        # Window defrosting state
        self.window_temperature_c = -15.0
        self.frost_obscuration_pct = 0.0
        self.defrost_heater_power_w = 0.0
        self.defrost_target_temp_c = 8.0

    def update_window_thermal(self, dt: float, ambient_temp_c: float, wind_speed_ms: float, air_density_kg_m3: float):
        """
        Calculates window surface temperature and frost formation/melt rate.
        """
        # Convective heat loss from window surface to cold mountain air:
        # h_conv ~ 10.45 - v + 10 * sqrt(v) scaled by air density
        h_conv = (10.0 + 8.5 * math.sqrt(max(0.1, wind_speed_ms))) * (air_density_kg_m3 / 1.225) ** 0.6
        window_area_m2 = math.pi * ((self.aperture_mm / 2000.0) ** 2)
        q_loss = h_conv * window_area_m2 * (self.window_temperature_c - ambient_temp_c)
        
        # Active ITO heater controller (closed-loop proportional-integral)
        if self.window_temperature_c < self.defrost_target_temp_c:
            error = self.defrost_target_temp_c - self.window_temperature_c
            self.defrost_heater_power_w = min(85.0, error * 12.0)
        else:
            self.defrost_heater_power_w = 0.0
            
        # Thermal mass of sapphire front window (~0.12 kg, Cp ~ 750 J/kg*K)
        c_thermal = 0.12 * 750.0  # ~90 J/K
        d_temp = ((self.defrost_heater_power_w - q_loss) / c_thermal) * dt
        self.window_temperature_c += d_temp
        
        # Frost buildup / clearing dynamics:
        # Frost accumulates if window < 0°C and ambient < 0°C
        if self.window_temperature_c < 0.0 and ambient_temp_c < 0.0:
            self.frost_obscuration_pct = min(85.0, self.frost_obscuration_pct + 0.8 * dt)
        elif self.window_temperature_c > 3.0:
            # Active defrost melting
            self.frost_obscuration_pct = max(0.0, self.frost_obscuration_pct - 3.5 * dt)

    def compute_athermalization_sharpness(self, ambient_temp_c: float) -> float:
        """
        Germanium thermo-optic expansion dn/dT = 400e-6 / K.
        Calculates modulation transfer function (MTF) sharpness degradation if uncompensated.
        """
        if self.athermalization_enabled:
            # Active focus compensator maintains sharp focal plane
            return 98.5
        else:
            delta_t = abs(20.0 - ambient_temp_c)
            # Severe optical defocusing without athermalization
            sharpness = max(25.0, 100.0 - 1.25 * delta_t)
            return sharpness

    def track(
        self,
        true_pos: np.ndarray,
        target_rpm: float,
        ambient_temp_c: float,
        altitude_m: float
    ) -> OpticalDetection:
        """
        Processes radiometric IR signature, line-of-sight tracking, and centroiding noise.
        """
        r_true = float(np.linalg.norm(true_pos))
        az_true = math.degrees(math.atan2(true_pos[1], true_pos[0]))
        horiz_dist = math.hypot(true_pos[0], true_pos[1])
        el_true = math.degrees(math.atan2(true_pos[2], horiz_dist))
        
        # Target Thermal Signature:
        # Drone BLDC motors heat up due to high RPM in thin air:
        motor_temp_c = ambient_temp_c + 25.0 + (target_rpm / 1000.0) * 4.5
        # Background temperature: cold snow/sky (-30°C to -45°C)
        bg_temp_c = ambient_temp_c - 5.0
        
        # Intrinsic thermal contrast
        delta_t_intrinsic = max(5.0, motor_temp_c - bg_temp_c)
        
        # Atmospheric transmission in MWIR band (MODTRAN approximation):
        # tau_atm = exp(-alpha_ir * R), where alpha_ir is lower in thin dry high-altitude air
        alpha_ir = 0.00015 * math.exp(-altitude_m / 6000.0)
        tau_atm = math.exp(-alpha_ir * r_true)
        
        apparent_delta_k = delta_t_intrinsic * tau_atm
        
        # Obscuration from window frost
        transmittance_window = (100.0 - self.frost_obscuration_pct) / 100.0
        
        # Optical Signal-to-Noise Ratio (SNR)
        snr_optical = (apparent_delta_k / 0.025) * transmittance_window * (1500.0 / max(100.0, r_true)) ** 1.5
        
        visible = (snr_optical >= 4.0 and self.frost_obscuration_pct < 75.0)
        sharpness = self.compute_athermalization_sharpness(ambient_temp_c)
        
        # Centroiding angular precision (sub-pixel algorithm):
        # Angular jitter in micro-radians:
        # sigma_angle = (IFOV / (2 * SNR)) * (100 / sharpness)
        if visible and snr_optical > 0.1:
            base_jitter_urad = max(8.0, (self.ifov_urad / (2.0 * math.sqrt(snr_optical))) * (100.0 / sharpness))
        else:
            base_jitter_urad = 250.0  # High noise when degraded
            
        jitter_deg = (base_jitter_urad * 1e-6) * (180.0 / math.pi)
        meas_az = az_true + random.gauss(0.0, jitter_deg)
        meas_el = el_true + random.gauss(0.0, jitter_deg)
        
        return OpticalDetection(
            target_visible=visible,
            snr_optical=round(snr_optical, 1),
            measured_azimuth_deg=round(meas_az, 4),
            measured_elevation_deg=round(meas_el, 4),
            angular_jitter_urad=round(base_jitter_urad, 1),
            apparent_contrast_delta_k=round(apparent_delta_k, 2),
            lens_focus_sharpness_pct=round(sharpness, 1),
            window_frost_obscuration_pct=round(self.frost_obscuration_pct, 1)
        )
