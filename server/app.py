"""
High-Altitude Anti-Drone Defense System - Production FastAPI Server.
Provides REST APIs and 50 Hz WebSocket digital-twin telemetry streaming
for the 3D Tactical Battlefield Command & Control (C2) workstation.
"""

import asyncio
import json
import math
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np

# Ensure parent directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from server.simulation_runner import HighAltitudeAntiDroneSystemSimulation
from core.qualification.qualification_matrix import MILSTDQualificationMatrix

# Instantiate FastAPI application
app = FastAPI(
    title="High-Altitude Anti-Drone System - Digital Twin & C2 Server",
    description="Military-grade simulation, ADRC micro-radian control, multi-sensor fusion, and MIL-STD-810H qualification engine.",
    version="2.0.0"
)

# CORS middleware for local browser integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global simulation instance
sim = HighAltitudeAntiDroneSystemSimulation()


# Pydantic Request Models
class ScenarioConfigRequest(BaseModel):
    altitude_m: float = Field(default=5400.0, ge=0.0, le=10000.0)
    delta_t_c: float = Field(default=-20.0, ge=-50.0, le=30.0)
    wind_speed_ms: float = Field(default=18.0, ge=0.0, le=50.0)
    trajectory_profile: str = Field(default="valley_ingress")
    adrc_active: bool = Field(default=True)
    heaters_active: bool = Field(default=True)
    paschen_limiter_active: bool = Field(default=True)
    jamming_engaged: bool = Field(default=True)
    cable_material: str = Field(default="mil_spec_ptfe")


class BOMEvaluationRequest(BaseModel):
    selected_part_ids: List[str]
    target_altitude_m: float = 5400.0
    min_temp_c: float = -35.0


class CommandRequest(BaseModel):
    action: str
    value: Optional[Any] = None
    preset: Optional[str] = None


def apply_simulation_command(action: str, value: Any = None, preset: Optional[str] = None) -> Dict[str, Any]:
    """Applies interactive C2 commands to the digital-twin simulation state."""
    if action == "toggle_adrc":
        sim.adrc_active = bool(value if value is not None else True)
    elif action == "toggle_heaters":
        sim.heaters_active = bool(value if value is not None else True)
    elif action == "toggle_paschen":
        sim.paschen_limiter_active = bool(value if value is not None else True)
    elif action == "toggle_jamming":
        sim.jamming_engaged = bool(value if value is not None else True)
    elif action == "set_altitude":
        sim.altitude_m = float(value if value is not None else 5400.0)
        sim.reinitialize()
    elif action == "set_preset":
        target_preset = preset or str(value or "siachen")
        if target_preset == "sea_level":
            sim.altitude_m = 0.0
            sim.delta_t_c = 0.0
            sim.wind_speed_ms = 4.0
        elif target_preset == "ladakh":
            sim.altitude_m = 3500.0
            sim.delta_t_c = -10.0
            sim.wind_speed_ms = 12.0
        elif target_preset == "siachen":
            sim.altitude_m = 5400.0
            sim.delta_t_c = -20.0
            sim.wind_speed_ms = 18.0
        elif target_preset == "extreme_ridge":
            sim.altitude_m = 6500.0
            sim.delta_t_c = -30.0
            sim.wind_speed_ms = 28.0
        sim.reinitialize()
    return {"status": "SUCCESS", "action": action, "active_adrc": sim.adrc_active, "altitude_m": sim.altitude_m}


@app.get("/api/health")
async def get_health():
    return {"status": "ONLINE", "system": "High-Altitude Anti-Drone System", "version": "2.0.0"}


@app.post("/api/command")
async def execute_command(cmd: CommandRequest):
    """Executes a C2 command over REST for environments where WebSockets are unsupported (e.g. Vercel)."""
    result = apply_simulation_command(cmd.action, cmd.value, cmd.preset)
    return JSONResponse(content=result)


@app.get("/api/telemetry/snapshot")
async def get_telemetry_snapshot():
    """Returns a single step snapshot of current system telemetry."""
    data = sim.step(0.02)
    return JSONResponse(content=data)


@app.post("/api/scenario")
async def set_scenario(config: ScenarioConfigRequest):
    """Updates operational scenario and hardware compensation settings."""
    sim.altitude_m = config.altitude_m
    sim.delta_t_c = config.delta_t_c
    sim.wind_speed_ms = config.wind_speed_ms
    sim.adrc_active = config.adrc_active
    sim.heaters_active = config.heaters_active
    sim.paschen_limiter_active = config.paschen_limiter_active
    sim.jamming_engaged = config.jamming_engaged
    sim.cable_material_key = config.cable_material
    sim.target.trajectory_profile = config.trajectory_profile
    
    sim.reinitialize()
    return {"status": "SCENARIO_UPDATED", "config": config.model_dump()}


@app.get("/api/qualification/components")
async def get_qualification_components():
    """Returns the defense component qualification database."""
    components = MILSTDQualificationMatrix.get_all_components()
    return {"components": components}


@app.post("/api/qualification/evaluate-bom")
async def evaluate_bom(req: BOMEvaluationRequest):
    """Evaluates a Bill-of-Materials against MIL-STD-810H high-altitude criteria."""
    result = MILSTDQualificationMatrix.evaluate_bom(
        selected_part_ids=req.selected_part_ids,
        target_altitude_m=req.target_altitude_m,
        min_temp_c=req.min_temp_c
    )
    return JSONResponse(content=result)


@app.get("/api/simulation/monte-carlo")
async def run_monte_carlo(runs: int = 50):
    """
    Executes a high-altitude stochastic Monte Carlo test comparing ADRC vs PID
    under random wind turbulence gusts and cryogenic cable hysteresis.
    """
    runs = min(100, max(10, runs))
    adrc_errors = []
    pid_errors = []
    
    for _ in range(runs):
        # Step small sequence of 25 timesteps under random gust
        for _ in range(25):
            sim.step(0.02)
        adrc_errors.append(sim.last_adrc_error_urad)
        pid_errors.append(sim.last_pid_error_urad)
        
    adrc_mean = float(np.mean(adrc_errors))
    adrc_std = float(np.std(adrc_errors))
    adrc_p95 = float(np.percentile(adrc_errors, 95))
    
    pid_mean = float(np.mean(pid_errors))
    pid_std = float(np.std(pid_errors))
    pid_p95 = float(np.percentile(pid_errors, 95))
    
    return {
        "num_runs": runs,
        "adrc": {
            "mean_jitter_urad": round(adrc_mean, 1),
            "std_urad": round(adrc_std, 1),
            "p95_urad": round(adrc_p95, 1),
            "meets_specification": adrc_p95 <= 50.0
        },
        "pid": {
            "mean_jitter_urad": round(pid_mean, 1),
            "std_urad": round(pid_std, 1),
            "p95_urad": round(pid_p95, 1),
            "meets_specification": pid_p95 <= 50.0
        },
        "performance_improvement_factor": round(pid_mean / max(1.0, adrc_mean), 2)
    }


@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    """
    High-rate (50 Hz) WebSocket endpoint streaming full digital-twin telemetry
    to the 3D Tactical Battlefield Command & Control (C2) console.
    """
    await websocket.accept()
    try:
        while True:
            # Advance simulation step (dt = 0.02s => 50 Hz)
            telemetry = sim.step(dt=0.02)
            await websocket.send_text(json.dumps(telemetry))
            
            # Non-blocking check for incoming client commands
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.02)
                data = json.loads(msg)
                action = data.get("action")
                if action:
                    apply_simulation_command(action, data.get("value"), data.get("preset"))
            except asyncio.TimeoutError:
                pass
                
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# Mount Web Static Files directory
web_dir = BASE_DIR / "web"
if web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(web_dir / "index.html"))
