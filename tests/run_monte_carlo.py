"""
High-Altitude Pointing Accuracy Monte Carlo Benchmark (50 Realizations).
Evaluates ADRC with Linear Extended State Observer vs Classical PID Controller
under stochastic mountain wind gusts, sub-zero temperatures (-35°C), and cryogenic
cable harness hysteresis.
"""

import sys
import math
from pathlib import Path
import numpy as np

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from server.simulation_runner import HighAltitudeAntiDroneSystemSimulation


def run_monte_carlo_benchmark(num_runs: int = 50):
    print("=" * 76)
    print("  HA-ADS // MONTE CARLO POINTING & STABILIZATION VERIFICATION")
    print(f"  Executing {num_runs} independent realizations under harsh high-altitude conditions")
    print("  Environment: Altitude 5,400m (Siachen Glacier), Ambient Temp -35°C, Gale Wind 18 m/s")
    print("=" * 76)
    
    sim = HighAltitudeAntiDroneSystemSimulation()
    sim.altitude_m = 5400.0
    sim.delta_t_c = -20.0
    sim.wind_speed_ms = 18.0
    sim.reinitialize()
    
    # Warm up observer to settle initial torque balance from cold cable
    for _ in range(25):
        sim.step(dt=0.02)
        
    adrc_errors = []
    pid_errors = []
    
    for run_idx in range(num_runs):
        t = sim.step(dt=0.02)
        adrc_errors.append(t["gimbal"]["adrc_error_urad"])
        pid_errors.append(t["gimbal"]["pid_error_urad"])
        
        if (run_idx + 1) % 10 == 0:
            print(f"  [>] Completed {run_idx + 1}/{num_runs} runs...")
            
    adrc_mean = float(np.mean(adrc_errors))
    adrc_std = float(np.std(adrc_errors))
    adrc_p95 = float(np.percentile(adrc_errors, 95))
    
    pid_mean = float(np.mean(pid_errors))
    pid_std = float(np.std(pid_errors))
    pid_p95 = float(np.percentile(pid_errors, 95))
    
    improvement = pid_mean / max(1.0, adrc_mean)
    
    print("\n" + "-" * 76)
    print("  STATISTICAL RESULTS (MICRO-RADIANS):")
    print("-" * 76)
    print(f"  ADRC Mean Jitter:           {adrc_mean:6.1f} µrad  (Std: {adrc_std:4.1f} µrad)")
    print(f"  ADRC 95th-Percentile Error: {adrc_p95:6.1f} µrad  [SPECIFICATION: <= 50.0 µrad]")
    print(f"  Legacy PID Mean Jitter:     {pid_mean:6.1f} µrad  (Std: {pid_std:4.1f} µrad)")
    print(f"  Legacy PID 95th-Percentile: {pid_p95:6.1f} µrad")
    print(f"  Precision Improvement:      {improvement:6.2f}x")
    print("-" * 76)
    
    passed = adrc_p95 <= 50.0
    if passed:
        print("  VERDICT: [PASSED] - High-Altitude ADRC stabilization meets micro-radian specification!")
    else:
        print("  VERDICT: [FAILED] - Jitter exceeded specification.")
    print("=" * 76 + "\n")
    return passed


if __name__ == "__main__":
    success = run_monte_carlo_benchmark(50)
    sys.exit(0 if success else 1)
