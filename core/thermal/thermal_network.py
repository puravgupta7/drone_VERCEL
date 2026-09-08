"""
High-Altitude Multi-Node Lumped Thermal Management System.
Simulates thermodynamic heat exchange across 4 critical subsystem nodes:
1. GaN RF Power Amplifier (SSPA) with altitude-derated convective cooling
2. Gimbal Bearing & Slip Ring Hub with active heating
3. Lithium Battery Pack with Phase Change Material (PCM) thermal blanket
4. Optical Window with ITO defrost heater
"""

import math
from dataclasses import dataclass
from typing import Dict, Any, Tuple


@dataclass
class ThermalNodeState:
    node_name: str
    temperature_c: float
    target_temperature_c: float
    min_safe_temp_c: float
    max_safe_temp_c: float
    heater_power_w: float
    internal_heat_gen_w: float
    convective_loss_w: float
    status: str  # "NOMINAL", "HEATING", "COOLING", "OVERTEMP_WARNING", "CRITICAL_COLD"


@dataclass
class SystemThermalStatus:
    ambient_temp_c: float
    altitude_m: float
    convective_cooling_derate_pct: float
    nodes: Dict[str, ThermalNodeState]
    total_heater_power_w: float
    all_systems_ready: bool


class MultiNodeThermalNetwork:
    """
    4-Node Lumped Capacitance Thermal State-Space Model:
    C_i * (dT_i / dt) = Q_gen,i + Q_heater,i - Q_loss,i - Sum(Q_cond,ij)
    """

    def __init__(self):
        # Thermal Capacitances (J / K = mass * Cp)
        self.C_nodes = {
            "rf_amplifier": 1450.0,   # Aluminum heat sink + GaN module (~1.6 kg)
            "gimbal_bearings": 2200.0, # Steel bearing hub & slip rings (~4.5 kg)
            "battery_pack": 4800.0,   # 24V Li-ion pack + PCM matrix (~5.0 kg)
            "optics_window": 90.0     # Sapphire optical front glass (~0.12 kg)
        }
        
        # Initial temperatures in °C
        self.temp = {
            "rf_amplifier": -15.0,
            "gimbal_bearings": -20.0,
            "battery_pack": 15.0,
            "optics_window": -15.0
        }
        
        # Safe operational temperature ranges (°C)
        self.limits = {
            "rf_amplifier": {"min": -30.0, "max": 75.0, "target": 40.0},
            "gimbal_bearings": {"min": -20.0, "max": 65.0, "target": 5.0},
            "battery_pack": {"min": 5.0, "max": 45.0, "target": 22.0},
            "optics_window": {"min": 2.0, "max": 40.0, "target": 8.0}
        }
        
        # Heater capacities (Watts)
        self.max_heater_power = {
            "rf_amplifier": 0.0,       # Cooled by fan/heat-pipes, no heater
            "gimbal_bearings": 60.0,   # PTC collar heater
            "battery_pack": 45.0,      # Silicone heating jacket
            "optics_window": 75.0      # ITO transparent resistive film
        }
        
        # Current heater power outputs
        self.heater_power = {k: 0.0 for k in self.C_nodes}
        
        # Forced air fan speed (0.0 to 1.0)
        self.fan_speed = 0.4

    def update(
        self,
        dt: float,
        ambient_temp_c: float,
        wind_speed_ms: float,
        air_density_ratio: float,
        rf_transmitter_active: bool,
        rf_tx_power_rf_w: float = 60.0,
        active_thermal_control_enabled: bool = True
    ) -> SystemThermalStatus:
        """
        Integrates thermal state-space equations over dt.
        """
        # Convective cooling efficiency scales with air density: h ~ (rho / rho_0)^0.6
        cooling_derate_factor = math.pow(max(0.2, air_density_ratio), 0.6)
        
        # 1. Internal Heat Generation (Q_gen)
        q_gen = {
            # GaN PA efficiency ~45%; remainder is dissipated as heat:
            # P_dissipated = P_rf / 0.45 - P_rf = P_rf * 1.22
            "rf_amplifier": (rf_tx_power_rf_w * 1.22) if rf_transmitter_active else 8.0,
            "gimbal_bearings": 4.5,   # Motor copper & bearing friction losses
            "battery_pack": 6.0,      # Internal resistance I^2 * R discharge heat
            "optics_window": 0.0      # Passive window
        }
        
        # 2. Convective Heat Transfer Coefficients (W / K)
        # RF Amp Heat Sink: forced air fan cooling + natural convection
        h_rf_sl = 2.8 + 8.5 * self.fan_speed  # Sea level cooling
        h_rf = h_rf_sl * cooling_derate_factor
        
        # Gimbal hub housing exposed to mountain wind
        h_gimbal = (1.5 + 0.4 * wind_speed_ms) * cooling_derate_factor
        # Battery pack in insulated composite enclosure
        h_battery = 0.45 * cooling_derate_factor
        # Optics window exposed to direct wind
        h_optics = (2.2 + 0.9 * math.sqrt(max(0.1, wind_speed_ms))) * cooling_derate_factor
        
        h_coeffs = {
            "rf_amplifier": h_rf,
            "gimbal_bearings": h_gimbal,
            "battery_pack": h_battery,
            "optics_window": h_optics
        }
        
        # 3. Closed-Loop Thermal Controllers
        node_states = {}
        total_heater_w = 0.0
        
        for name in self.C_nodes:
            t_curr = self.temp[name]
            t_target = self.limits[name]["target"]
            max_heat = self.max_heater_power[name]
            
            # Active heater logic
            if active_thermal_control_enabled and max_heat > 0.0:
                if t_curr < t_target:
                    # Proportional heating with high gain
                    p_heat = min(max_heat, (t_target - t_curr) * 12.0)
                    self.heater_power[name] = max(0.0, p_heat)
                else:
                    self.heater_power[name] = 0.0
            else:
                self.heater_power[name] = 0.0
                
            total_heater_w += self.heater_power[name]
            
            # Convective loss to ambient
            q_conv_loss = h_coeffs[name] * (t_curr - ambient_temp_c)
            
            # Net heat flow
            q_net = q_gen[name] + self.heater_power[name] - q_conv_loss
            
            # Update temperature
            d_temp = (q_net / self.C_nodes[name]) * dt
            self.temp[name] += d_temp
            
            # Determine status classification
            min_lim = self.limits[name]["min"]
            max_lim = self.limits[name]["max"]
            
            if self.temp[name] > max_lim:
                status = "OVERTEMP_WARNING"
            elif self.temp[name] < min_lim:
                status = "CRITICAL_COLD"
            elif self.heater_power[name] > 5.0:
                status = "HEATING"
            else:
                status = "NOMINAL"
                
            node_states[name] = ThermalNodeState(
                node_name=name,
                temperature_c=round(self.temp[name], 2),
                target_temperature_c=t_target,
                min_safe_temp_c=min_lim,
                max_safe_temp_c=max_lim,
                heater_power_w=round(self.heater_power[name], 1),
                internal_heat_gen_w=round(q_gen[name], 1),
                convective_loss_w=round(q_conv_loss, 1),
                status=status
            )
            
        all_ready = all(
            self.limits[k]["min"] <= self.temp[k] <= self.limits[k]["max"]
            for k in self.C_nodes
        )
        
        return SystemThermalStatus(
            ambient_temp_c=round(ambient_temp_c, 1),
            altitude_m=0.0,  # Updated by caller
            convective_cooling_derate_pct=round((1.0 - cooling_derate_factor) * 100.0, 1),
            nodes=node_states,
            total_heater_power_w=round(total_heater_w, 1),
            all_systems_ready=all_ready
        )
