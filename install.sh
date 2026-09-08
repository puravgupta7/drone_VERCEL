#!/usr/bin/env bash
set -e

echo "============================================================================"
echo "  HA-ADS // High Altitude Anti-Drone System - Environment Setup (Unix)"
echo "============================================================================"

command -v python3 >/dev/null 2>&1 || {
    echo >&2 "[ERROR] python3 is required but not installed. Please install Python 3.10+."
    exit 1
}

echo "[*] Upgrading pip and installing requirements..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo "============================================================================"
echo "  [SUCCESS] All dependencies installed successfully!"
echo "  Run './run.sh' to launch the system."
echo "============================================================================"
