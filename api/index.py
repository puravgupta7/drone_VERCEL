"""
Vercel Serverless Function entry point for High-Altitude Anti-Drone Defense System (HA-ADS).
Exposes the FastAPI application as `app` for Vercel's Python runtime.
"""
import sys
from pathlib import Path

# Ensure repository root is on sys.path so 'server' and 'core' packages can be imported
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from server.app import app
