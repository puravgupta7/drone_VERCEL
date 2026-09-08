"""
High-Altitude Anti-Drone Defense System - Master Startup Launcher.
Launches the FastAPI digital-twin server, 50 Hz WebSocket simulation,
and automatically opens the 3D Tactical Battlefield Command & Control (C2) console.
"""

import os
import sys
import time
import webbrowser
import uvicorn

def main():
    port = 8000
    host = "127.0.0.1"
    url = f"http://{host}:{port}"
    
    print("=" * 78)
    print("  HA-ADS // HIGH-ALTITUDE ANTI-DRONE SYSTEM & DIGITAL TWIN C2 WORKSTATION")
    print("  Robust Multi-Physics Modeling & Active Disturbance Rejection Control (ADRC)")
    print("=" * 78)
    print(f"[*] Starting local server on: {url}")
    print("[*] 50 Hz WebSocket Telemetry Stream: /ws/telemetry")
    print("[*] MIL-STD-810H / 461G Qualification Matrix: /api/qualification/components")
    print("[*] Opening Tactical 3D Battlefield Cockpit in browser...")
    print("=" * 78)
    
    # Try opening browser after 1.2 seconds in a background thread
    import threading
    def open_browser():
        time.sleep(1.2)
        try:
            webbrowser.open(url)
        except Exception:
            pass
            
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run uvicorn server
    uvicorn.run("server.app:app", host=host, port=port, log_level="info", reload=False)

if __name__ == "__main__":
    main()
