# High-Altitude Anti-Drone Defense System (HA-ADS)
### Performance Optimization, Robust Design & Tactical Command & Control (C2) Digital Twin

[![GitHub Repo](https://img.shields.io/badge/GitHub-puravgupta7%2FDrone-blue?logo=github)](https://github.com/puravgupta7/Drone.git)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Military Standard](https://img.shields.io/badge/Aerospace-MIL--STD--810H-red.svg)](https://en.wikipedia.org/wiki/MIL-STD-810)
[![EMC Standard](https://img.shields.io/badge/EMC-MIL--STD--461G-purple.svg)](https://en.wikipedia.org/wiki/MIL-STD-461)
[![Pointing Accuracy](https://img.shields.io/badge/Pointing%20Precision-%E2%89%A425%20%C2%B5rad-brightgreen.svg)]()
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%2050Hz%20WebSocket-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![WebGL Three.js](https://img.shields.io/badge/Frontend-WebGL%20%2F%20Three.js-black.svg?logo=three.js&logoColor=white)](https://threejs.org/)

---

## 1. Problem Statement & Background

Anti-drone defense systems deployed in strategic high-altitude mountain environments (**3,000 m to 6,500 m**, such as Ladakh, the Siachen Glacier, and high Himalayan frontiers) face severe physical degradation across all mechanical, RF, optical, electrical, and stabilization subsystems:

1. **Sub-Zero Temperatures (-40°C to -20°C)**:
   - Wiring harnesses crossing rotating gimbal joints freeze below their glass-transition temperature ($T_g$), causing flexural and torsional stiffness to increase by **10× to 60×** with severe nonlinear Bouc-Wen hysteresis.
   - Standard bearing lubricants congeal and freeze, increasing startup friction by up to 800%.
   - Lithium-ion battery capacity drops by 50% to 70% due to reduced electrolyte ion mobility.
2. **Low Barometric Pressure (~500 hPa vs 1,013 hPa at sea level)**:
   - Reduced gas density lowers the dielectric breakdown voltage of air according to **Paschen’s Law**, causing catastrophic RF arcing and corona discharge in high-power microwave transmitters, feedhorns, and connectors.
3. **Reduced Air Density (40% to 50% lower)**:
   - Convective heat dissipation efficiency collapses ($h_{conv} \propto \rho^{0.6}$), causing RF power amplifiers and processing units to overheat despite freezing ambient air.
   - Hostile drones must spin propellers **25% to 40% faster** in thin air to hover, resulting in higher acoustic blade-pass pitch, shifted micro-Doppler radar signatures, and faster battery depletion.
4. **Severe Mountain Wind Gales & Buffeting (up to 120 km/h)**:
   - Davenport mountain wind gusts induce large overturning drag torques, destabilizing pedestals and ruining micro-radian pointing precision ($\le 50\ \mu\text{rad}$).
5. **Sensor Degradation**:
   - Cold snow backdrops ($\varepsilon \approx 0.98$) degrade infrared thermal contrast. Germanium lens thermo-optic expansion ($dn/dT$) causes severe optical defocusing without athermalization. Front optical windows freeze with crystalline frost.

**HA-ADS** is a complete, multi-physics software solution, control suite, and real-time digital twin designed to model, compensate, and solve each of these degradation modes.

---

## 2. Prerequisites & Required Downloads

Before running this project, ensure you have the following installed on your machine:

### A. Core Software Prerequisites

1. **Python 3.10, 3.11, 3.12, or 3.13**:
   - Download: [https://www.python.org/downloads/](https://www.python.org/downloads/)
   - *Important (Windows)*: During installation, check the box **"Add python.exe to PATH"**.
2. **Git**:
   - Download: [https://git-scm.com/downloads](https://git-scm.com/downloads)
3. **Modern Web Browser**:
   - Google Chrome, Microsoft Edge, Mozilla Firefox, or Brave (any browser supporting modern WebGL and WebSockets).

### B. Python Libraries (Installed automatically via `requirements.txt`)
- `fastapi` (>=0.110.0) — High-performance asynchronous REST backend.
- `uvicorn` (>=0.28.0) — ASGI server running the 50 Hz digital twin simulation.
- `websockets` (>=12.0) — Full-duplex real-time streaming to the 3D C2 console.
- `numpy` (>=1.26.0) — High-performance vector math and physics calculations.
- `scipy` (>=1.12.0) — Numerical algorithms and filtering.
- `pydantic` (>=2.6.0) — Strict schema validation for C2 API endpoints.
- `pytest` (>=8.0.0) — Automated physics and control verification test runner.
- `httpx` (>=0.27.0) — HTTP client testing library.

*(Note: Three.js and Chart.js are loaded automatically via CDN in the frontend—no Node.js build step is required!)*

---

## 3. Quick Start Guide (Installation & Execution)

### Option 1: One-Click Windows Launcher

1. **Clone the repository**:
   ```cmd
   git clone https://github.com/puravgupta7/Drone.git
   cd Drone
   ```
2. **Install dependencies**:
   Double-click `install.bat` (or run `install.bat` in Command Prompt / PowerShell).
3. **Run the 3D Tactical C2 Digital Twin**:
   Double-click `run.bat` (or run `run.bat`).
   Your browser will automatically open:
   👉 **`http://localhost:8000`**

---

### Option 2: Command Line (Windows, Linux, macOS)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/puravgupta7/Drone.git
   cd Drone
   ```
2. **Create a virtual environment (optional but recommended)**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```
3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Launch the system**:
   ```bash
   python run_system.py
   ```
   Open **`http://localhost:8000`** in your browser.

---

### Option 3: Deploy to Vercel (Cloud Production)

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fpuravgupta7%2FDrone)

This repository is pre-configured for zero-config Vercel deployment using `@vercel/python` serverless functions and Vercel edge CDN for static assets.

#### Method A: Via Vercel Web Dashboard (Recommended)
1. Push your code to your GitHub repository (e.g. `puravgupta7/Drone`).
2. Visit [vercel.com/new](https://vercel.com/new) and log in.
3. Import the `Drone` repository.
4. Leave **Framework Preset** as **Other** (Vercel automatically detects `vercel.json` and `api/index.py`).
5. Click **Deploy**. Your live tactical C2 digital twin will be available in ~60 seconds at `https://<your-project>.vercel.app`.

#### Method B: Via Vercel CLI
```bash
# Preview deployment
npx vercel

# Production deployment
npx vercel --prod
```

#### How Vercel Deployment Operates:
- **Serverless REST & Telemetry**: FastAPI endpoints (`/api/health`, `/api/telemetry/snapshot`, `/api/command`, `/api/simulation/monte-carlo`, `/api/qualification/*`) run as serverless Python functions on AWS Lambda.
- **Dual-Mode Telemetry Streaming**: Because Vercel serverless functions do not support long-lived persistent WebSocket connections, the frontend (`web/js/app.js`) automatically activates high-frequency HTTP telemetry streaming with smooth 3D interpolation and REST command dispatch.
- **Optional Hybrid Mode (Full 50 Hz WebSockets)**: If you prefer persistent 50 Hz WebSockets in production, host the Python backend on [Render](https://render.com), [Railway](https://railway.app), or a VPS, and append the URL query parameter `?backend=https://your-backend.domain` or set `window.HA_ADS_CONFIG = { backendUrl: 'https://your-backend.domain' }`.

---

## 4. Running Verification Tests & Monte Carlo Benchmarks

### Automated Unit Test Suite (8 Test Modules)
To run the automated physics and control verification tests:
```bash
python -m pytest tests/ -v
```
**Expected Result**: All 8 tests pass with 100% success rate in < 1.0 second:
- `test_atmosphere_sea_level`: Standard ISA 1976 validation.
- `test_atmosphere_high_altitude_siachen`: Siachen thermodynamics validation.
- `test_paschen_dielectric_breakdown`: Paschen breakdown curve validation.
- `test_cable_cryogenic_stiffness`: Bouc-Wen frozen cable stiffness validation.
- `test_target_drone_aerodynamics_in_thin_air`: Thin-air rotor RPM validation.
- `test_leso_observer_tracking`: Discrete LESO disturbance estimation validation.
- `test_adrc_micro_radian_precision_under_cold_cable_stress`: Micro-radian stabilization validation ($\le 50\ \mu\text{rad}$).
- `test_ukf_convergence`: 9-state 3D UKF multi-sensor tracking convergence.

### 50-Run Monte Carlo Pointing Benchmark
To evaluate pointing precision across 50 stochastic realizations of mountain wind gales and sub-zero frozen cable hysteresis:
```bash
python tests/run_monte_carlo.py
```
**Benchmark Output**:
```
----------------------------------------------------------------------------
  STATISTICAL RESULTS (MICRO-RADIANS):
----------------------------------------------------------------------------
  ADRC Mean Jitter:             12.8 µrad  (Std:  6.1 µrad)
  ADRC 95th-Percentile Error:   23.4 µrad  [SPECIFICATION: <= 50.0 µrad]
  Legacy PID Mean Jitter:      500.0 µrad  (Std:  0.0 µrad)
  Legacy PID 95th-Percentile:  500.0 µrad
  Precision Improvement:       39.02x
----------------------------------------------------------------------------
  VERDICT: [PASSED] - High-Altitude ADRC stabilization meets micro-radian specification!
============================================================================
```

---

## 5. System Architecture & Technical Depth

```
                                HA-ADS SYSTEM ARCHITECTURE

  ┌──────────────────────────────────────────────────────────────────────────────┐
  │                    3D TACTICAL C2 WORKSTATION (FRONTEND)                     │
  │   Three.js 3D Battlefield   │   MWIR Radiometric HUD   │   Chart.js Live     │
  │   Himalayan Digital Twin    │   Targeting Reticle      │   Strip Charts      │
  └───────────────────────────────────────▲──────────────────────────────────────┘
                                          │ 50 Hz WebSocket Stream (/ws/telemetry)
  ┌───────────────────────────────────────▼──────────────────────────────────────┐
  │                         FASTAPI BACKEND & SIMULATION                         │
  │   REST Endpoints (/api/scenario, /api/qualification, /api/monte-carlo)       │
  └───────┬───────────────────┬───────────────────┬───────────────────┬──────────┘
          │                   │                   │                   │
┌─────────▼─────────┐ ┌───────▼───────────┐ ┌─────▼───────────┐ ┌─────▼──────────┐
│ MULTI-PHYSICS     │ │ PRECISION GIMBAL  │ │ MULTI-SENSOR    │ │ THERMAL &      │
│ ENGINE            │ │ & ADRC CONTROL    │ │ 3D UKF FUSION   │ │ COUNTERMEASURES│
├───────────────────┤ ├───────────────────┤ ├─────────────────┤ ├────────────────┤
│• ISA 1976 Atmo    │ │• 2-DOF Pedestal   │ │• 3D FMCW Radar  │ │• 4-Node Lumped │
│• Paschen Arcing   │ │• Discrete LESO    │ │• MWIR Thermal   │ │  Thermal Model │
│• Bouc-Wen Cable   │ │• Disturbance Rej. │ │• RF Direction   │ │• BIT Health    │
│• Mountain Wind    │ │• 500 Hz Servo Sub │ │• 9-State UKF    │ │• RF Jammer J/S │
│• Thin-Air Drone   │ │• Micro-rad Lock   │ │• Snow Clutter   │ │• Lead Intercept│
└───────────────────┘ └───────────────────┘ └─────────────────┘ └────────────────┘
```

### Subsystem Descriptions

1. **High-Altitude Atmosphere (`core/physics/atmosphere.py`)**:
   - Models barometric pressure $P(h)$, air temperature $T(h)$, density $\rho(h)$, Sutherland’s dynamic viscosity $\mu(T)$, speed of sound $c(T)$, and thin-air convective heat transfer derating factors ($h_{conv} \propto \rho^{0.6}$).
2. **Paschen’s Law Dielectric Breakdown (`core/physics/paschen.py`)**:
   - Calculates sparkover voltages and prevents high-power RF arcing in low-pressure thin air.
3. **Cryogenic Cable Harness Hysteresis (`core/physics/cable_dynamics.py`)**:
   - Implements the non-linear Bouc-Wen model for cryogenic cable stiffening, comparing PVC, PUR, Fluorosilicone, and MIL-W-22759 PTFE/ETFE.
4. **Mountain Wind Turbulence (`core/physics/wind_aerodynamics.py`)**:
   - Generates colored-noise Davenport/Dryden wind gust turbulence and aerodynamic overturning torques.
5. **Target Drone Dynamics (`core/physics/target_dynamics.py`)**:
   - Models altitude-scaled rotor RPM, micro-Doppler frequency shifts, and accelerated battery depletion in cold thin air.
6. **Active Disturbance Rejection Control (ADRC) (`core/control/adrc_controller.py`)**:
   - 3rd-order Discrete Extended State Observer (LESO) running at a 500 Hz internal servo rate. Real-time online estimation and cancellation of cable stiffness and wind gusts, achieving $\le 25\ \mu\text{rad}$ pointing jitter.
7. **3D Multi-Sensor UKF Fusion (`core/sensing/sensor_fusion.py`)**:
   - 9-state 3D Unscented Kalman Filter fusing 3D FMCW Radar, MWIR Cooled Thermal Camera, and passive RF Direction Finding with adaptive innovation covariance scaling.
8. **Closed-Loop Thermal Network (`core/thermal/thermal_network.py`)**:
   - 4-node lumped state-space model with altitude-derated convection and automated closed-loop PID heaters for GaN RF amplifiers, bearing hubs, LiFePO4 batteries (PCM jacket), and optical windows (ITO defrost).
9. **Electronic Attack & Neutralization (`core/neutralization/neutralization.py`)**:
   - Multi-band RF/GNSS jammer link budget ($J/S$ dB) with Paschen power clamps and directed-energy lead-angle fire-control calculation.
10. **MIL-STD-810H / 461G Qualification Matrix (`core/qualification/qualification_matrix.py`)**:
    - Interactive defense trade study database and Bill-of-Materials evaluator.

---

## 6. Interactive C2 Console Features

When you open `http://localhost:8000`, the interactive Command & Control cockpit provides:

- **3D Himalayan Battlefield View (Three.js)**:
  - Articulated 2-DOF direct-drive turret tracking target drones in real time.
  - 3D visual beams: pulsing cyan radar beam, amber optical laser vector, translucent violet RF jamming cone, and dynamic snowstorm blizzard particles.
  - Camera views: **ORBIT** (God's eye view), **TURRET POV** (first-person boresight), and **DRONE CAM** (chase camera).
- **MWIR Radiometric Thermal Reticle Simulator**:
  - Synthesized Medium-Wave Infrared camera feed rendering hot motor cores, battery pack, stadiametric crosshair reticle, lead circle, and crystalline window frost accumulation.
- **Real-Time Strip Charts (Chart.js)**:
  - Pointing Jitter Comparison: ADRC error ($\le 25\ \mu\text{rad}$) vs Standard PID error ($>350\ \mu\text{rad}$) against the $50\ \mu\text{rad}$ tactical specification.
  - Cable Restoring Torque Hysteresis phase-plane loop.
- **Altitude Presets & Mission Controls**:
  - Switch between **Sea Level (0m)**, **Leh/Ladakh (3,500m)**, **Siachen Glacier (5,400m)**, and **Extreme Ridge (6,500m)**.
  - Toggle ADRC on/off to immediately observe PID degradation under frozen cables.
  - Toggle heating blankets on/off to watch optical window frosting and battery temperature drop.
  - Run the interactive 50-run Monte Carlo simulation and explore the MIL-STD-810H component qualification matrix.

---

## 7. Project Structure

```
Drone/
├── core/
│   ├── physics/
│   │   ├── atmosphere.py          # ISA 1976 atmosphere, Sutherland viscosity, convective derating
│   │   ├── paschen.py             # Paschen breakdown voltage & RF arcing envelopes
│   │   ├── cable_dynamics.py      # Non-linear Bouc-Wen cryogenic cable hysteresis model
│   │   ├── wind_aerodynamics.py   # Davenport mountain wind gust spectrum & aerodynamic drag
│   │   └── target_dynamics.py     # Thin-air drone rotor aerodynamics, high RPM & micro-Doppler
│   ├── control/
│   │   ├── gimbal_model.py        # 2-DOF Pan-Tilt gimbal pedestal dynamic simulation
│   │   └── adrc_controller.py     # Discrete 3rd-order LESO & Active Disturbance Rejection Control
│   ├── sensing/
│   │   ├── radar_model.py         # 3D FMCW Radar with atmospheric loss & snow slope clutter
│   │   ├── optics_thermal_model.py# Radiometric MWIR camera, athermalization & ITO defrosting
│   │   └── sensor_fusion.py       # 9-state 3D Unscented Kalman Filter (UKF)
│   ├── thermal/
│   │   ├── thermal_network.py     # 4-node lumped thermal state-space model & closed-loop heaters
│   │   └── health_monitor.py      # Built-In-Test (BIT) & prognostic health diagnostics
│   ├── neutralization/
│   │   └── neutralization.py      # RF jamming link budget & micro-radian fire control solution
│   └── qualification/
│       └── qualification_matrix.py# MIL-STD-810H & 461G component database & BOM evaluator
├── server/
│   ├── app.py                     # Production FastAPI server (REST APIs + 50Hz WebSocket stream)
│   └── simulation_runner.py       # Master digital twin coordinator (500 Hz servo sub-stepping)
├── web/
│   ├── index.html                 # 3D Tactical Battlefield Command & Control (C2) console
│   ├── css/style.css              # Military dark glassmorphic styling
│   └── js/
│       ├── app.js                 # WebSocket client, telemetry updates & modal controllers
│       ├── three_scene.js         # Three.js 3D Himalayan battlefield, articulated turret & drone
│       ├── thermal_canvas.js      # MWIR radiometric camera simulator & targeting HUD
│       └── telemetry_charts.js    # Real-time Chart.js pointing jitter & cable hysteresis strip charts
├── tests/
│   ├── test_physics.py            # Physics validation unit tests
│   ├── test_control.py            # ADRC micro-radian control verification unit tests
│   ├── test_fusion.py             # 3D UKF multi-sensor tracking unit tests
│   └── run_monte_carlo.py         # 50-run Monte Carlo pointing accuracy benchmark script
├── run_system.py                  # Master launcher (server + browser auto-launch)
├── requirements.txt               # Complete Python dependencies
├── install.bat / run.bat          # 1-click Windows setup & execution scripts
├── test.bat                       # 1-click Windows test suite runner
├── install.sh / run.sh            # 1-click Unix/Linux/macOS scripts
├── .gitignore                     # Git exclusion rules
├── LICENSE                        # MIT License
└── README.md                      # Comprehensive project documentation
```

---

## 8. License

This project is open-source and licensed under the [MIT License](LICENSE).
Developed by **Purav Gupta** for high-altitude defense applications.
