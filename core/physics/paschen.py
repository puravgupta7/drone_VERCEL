"""
Paschen's Law & High-Altitude Dielectric Breakdown / Corona Discharge Module.
Models dielectric breakdown voltage across RF connectors, microwave waveguides,
slip-ring gaps, and high-voltage circuitry as atmospheric pressure drops.
Provides derating envelopes to prevent electrical arcing and RF burn-through.
"""

import math
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class DielectricBreakdownResult:
    altitude_m: float
    pressure_torr: float
    pressure_pa: float
    gap_distance_mm: float
    pd_product_torr_cm: float
    breakdown_voltage_v_peak: float
    sea_level_breakdown_voltage_v_peak: float
    dielectric_derating_factor: float  # V_B(alt) / V_B(sea_level)
    safe_working_voltage_v_peak: float  # With 2.0x safety factor
    max_rf_power_cw_watts: float  # Maximum continuous RF power into standard 50-ohm line without arcing
    corona_risk_level: str  # "SAFE", "ELEVATED", "CRITICAL"


class PaschenModel:
    """
    Paschen's Law formula for Air:
    V_B = (B * p * d) / [ ln(A * p * d) - ln(ln(1 + 1/gamma_se)) ]
    
    Standard empirical constants for Air:
    A = 15.0 (Torr * cm)^(-1)
    B = 365.0 V / (Torr * cm)
    gamma_se = 0.01 (Second Townsend coefficient for copper/aluminum electrodes)
    """
    A_AIR = 15.0
    B_AIR = 365.0
    GAMMA_SE = 0.01
    
    # Characteristic impedance of standard RF transmission lines
    Z0_RF_OHMS = 50.0

    @classmethod
    def calculate_breakdown(
        cls,
        pressure_pa: float,
        gap_distance_mm: float = 1.0,
        altitude_m: float = 0.0,
        safety_factor: float = 2.0
    ) -> DielectricBreakdownResult:
        """
        Calculates dielectric breakdown voltage for a given gap distance at current pressure.
        
        Args:
            pressure_pa: Air pressure in Pascals.
            gap_distance_mm: Electrode or conductor spacing in millimeters (default: 1.0 mm).
            altitude_m: Operational altitude for reporting.
            safety_factor: Safety margin divisor (MIL-STD requires >= 2.0).
        """
        # Convert Pa to Torr (1 Torr = 133.322368 Pa)
        pressure_torr = pressure_pa / 133.322368
        gap_cm = gap_distance_mm / 10.0
        pd = pressure_torr * gap_cm  # Torr * cm
        
        # Paschen formula denominator term
        ln_term = math.log(1.0 + 1.0 / cls.GAMMA_SE)  # ~ ln(101) ~ 4.615
        
        # Evaluate breakdown voltage at altitude
        v_breakdown = cls._raw_paschen(pd, ln_term)
        
        # Sea level baseline (101325 Pa = 760 Torr)
        pd_sl = 760.0 * gap_cm
        v_breakdown_sl = cls._raw_paschen(pd_sl, ln_term)
        
        derating_factor = max(0.1, min(1.0, v_breakdown / v_breakdown_sl))
        safe_voltage = v_breakdown / safety_factor
        
        # In a 50-ohm RF connector / transmission line:
        # P_peak = V_peak^2 / (2 * Z0)
        # Safe RF CW power limit:
        max_rf_cw = (safe_voltage ** 2) / (2.0 * cls.Z0_RF_OHMS)
        
        # Corona risk classification
        if derating_factor > 0.75:
            risk = "SAFE"
        elif derating_factor > 0.50:
            risk = "ELEVATED"
        else:
            risk = "CRITICAL"
            
        return DielectricBreakdownResult(
            altitude_m=round(altitude_m, 1),
            pressure_torr=round(pressure_torr, 2),
            pressure_pa=round(pressure_pa, 1),
            gap_distance_mm=gap_distance_mm,
            pd_product_torr_cm=round(pd, 4),
            breakdown_voltage_v_peak=round(v_breakdown, 1),
            sea_level_breakdown_voltage_v_peak=round(v_breakdown_sl, 1),
            dielectric_derating_factor=round(derating_factor, 3),
            safe_working_voltage_v_peak=round(safe_voltage, 1),
            max_rf_power_cw_watts=round(max_rf_cw, 1),
            corona_risk_level=risk
        )

    @classmethod
    def _raw_paschen(cls, pd: float, ln_term: float) -> float:
        """Evaluates Paschen equation with minimum clamping near the Paschen minimum (~327V)."""
        # Minimum physical spark threshold for air is ~327 V around pd = 0.57 Torr*cm
        V_MIN_AIR = 327.0
        if pd <= 0.001:
            return V_MIN_AIR
            
        arg = cls.A_AIR * pd
        if arg <= 1.0:
            return V_MIN_AIR
            
        denom = math.log(arg) - math.log(ln_term)
        if denom <= 0.05:
            return V_MIN_AIR
            
        v_b = (cls.B_AIR * pd) / denom
        return max(V_MIN_AIR, v_b)
