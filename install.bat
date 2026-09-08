@echo off
echo ============================================================================
echo   HA-ADS // High Altitude Anti-Drone System - Environment Setup
echo ============================================================================
echo.
echo [*] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please download and install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [*] Installing required Python dependencies from requirements.txt...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo ============================================================================
echo   [SUCCESS] All dependencies installed successfully!
echo   Run "run.bat" to start the 3D Tactical Battlefield C2 Digital Twin.
echo ============================================================================
pause
