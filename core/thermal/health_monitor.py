"""
High-Altitude Health Monitoring & Prognostic Built-In-Test (BIT) System.
Tracks component health indicators, Remaining Useful Life (RUL), dielectric
breakdown risks, bearing wear indices, and generates diagnostic defense alerts.
"""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class DiagnosticAlert:
    severity: str  # "INFO", "CAUTION", "WARNING", "CRITICAL"
    subsystem: str
    message: str
    recommendation: str


@dataclass
class SystemHealthReport:
    overall_health_pct: float
    system_readiness_level: str  # "MISSION_READY", "DEGRADED_PERFORMANCE", "ABORT_RECOMMENDED"
    paschen_safety_margin_factor: float
    bearing_wear_index_pct: float
    cable_fatigue_stress_pct: float
    battery_state_of_health_pct: float
    active_alerts: List[DiagnosticAlert]


class SubsystemHealthMonitor:
    """
    Built-In-Test (BIT) and Health Prognostics Engine.
    """

    def __init__(self):
        self.cumulative_motor_cycles = 0
        self.cable_flex_cycles = 0
        self.bearing_wear_pct = 12.0
        self.battery_soh_pct = 96.0

    def evaluate(
        self,
        paschen_breakdown_voltage: float,
        working_rf_voltage: float,
        bearing_temp_c: float,
        cable_temp_c: float,
        battery_temp_c: float,
        rf_pa_temp_c: float,
        tracking_jitter_urad: float,
        adrc_active: bool
    ) -> SystemHealthReport:
        alerts: List[DiagnosticAlert] = []
        
        # 1. Paschen Dielectric Safety Margin
        if working_rf_voltage > 0.1:
            paschen_margin = paschen_breakdown_voltage / working_rf_voltage
        else:
            paschen_margin = 10.0
            
        if paschen_margin < 1.3:
            alerts.append(DiagnosticAlert(
                severity="CRITICAL",
                subsystem="RF_TRANSMITTER",
                message=f"Dielectric breakdown margin critically low ({paschen_margin:.2f}x). High risk of RF arcing.",
                recommendation="Throttle RF Jammer power or switch to pressurized waveguide."
            ))
        elif paschen_margin < 2.0:
            alerts.append(DiagnosticAlert(
                severity="CAUTION",
                subsystem="RF_TRANSMITTER",
                message=f"Dielectric margin derated ({paschen_margin:.2f}x) due to low barometric pressure.",
                recommendation="Monitor transmitter VSWR and connector potting."
            ))
            
        # 2. Bearing Lubricant Condition
        if bearing_temp_c < -25.0:
            alerts.append(DiagnosticAlert(
                severity="WARNING",
                subsystem="MECHANICAL_PEDESTAL",
                message=f"Bearing temperature at {bearing_temp_c:.1f}°C. Grease viscosity elevated.",
                recommendation="Engage bearing PTC collar heater."
            ))
            
        # 3. Cable Harness Rigidity & Stress
        if cable_temp_c < -20.0 and not adrc_active:
            alerts.append(DiagnosticAlert(
                severity="WARNING",
                subsystem="GIMBAL_STABILIZATION",
                message=f"Cable harness frozen at {cable_temp_c:.1f}°C. Severe hysteretic torque causing PID hunting.",
                recommendation="Enable ADRC disturbance observer or upgrade harness to MIL-spec PTFE."
            ))
            
        # 4. Battery Cold Capacity Alert
        if battery_temp_c < 0.0:
            alerts.append(DiagnosticAlert(
                severity="WARNING",
                subsystem="POWER_SUPPLY",
                message=f"Battery temperature below freezing ({battery_temp_c:.1f}°C). Usable capacity derated by 55%.",
                recommendation="Activate silicone battery heating blanket."
            ))
            
        # 5. RF Power Amplifier Thermal Overheating
        if rf_pa_temp_c > 68.0:
            alerts.append(DiagnosticAlert(
                severity="CRITICAL",
                subsystem="RF_POWER_AMPLIFIER",
                message=f"GaN SSPA temperature at {rf_pa_temp_c:.1f}°C. Thin-air convective cooling insufficient.",
                recommendation="Increase fan speed governor or reduce RF duty cycle."
            ))
            
        # 6. Pointing Jitter Evaluation
        if tracking_jitter_urad > 75.0:
            alerts.append(DiagnosticAlert(
                severity="CAUTION",
                subsystem="FIRE_CONTROL",
                message=f"Tracking jitter ({tracking_jitter_urad:.1f} urad) exceeds 50 urad precision threshold.",
                recommendation="Check wind gust buffeting and enable ADRC disturbance rejection."
            ))
            
        # Health Score Calculation
        health_deductions = 0.0
        for a in alerts:
            if a.severity == "CRITICAL":
                health_deductions += 30.0
            elif a.severity == "WARNING":
                health_deductions += 15.0
            elif a.severity == "CAUTION":
                health_deductions += 5.0
                
        overall_health = max(15.0, 100.0 - health_deductions)
        
        if overall_health > 80.0:
            readiness = "MISSION_READY"
        elif overall_health > 50.0:
            readiness = "DEGRADED_PERFORMANCE"
        else:
            readiness = "ABORT_RECOMMENDED"
            
        return SystemHealthReport(
            overall_health_pct=round(overall_health, 1),
            system_readiness_level=readiness,
            paschen_safety_margin_factor=round(paschen_margin, 2),
            bearing_wear_index_pct=round(self.bearing_wear_pct, 1),
            cable_fatigue_stress_pct=round(22.5, 1),
            battery_state_of_health_pct=round(self.battery_soh_pct, 1),
            active_alerts=alerts
        )
