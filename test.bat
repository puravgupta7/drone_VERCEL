@echo off
echo ============================================================================
echo   HA-ADS // Running Verification Tests & Monte Carlo Benchmark
echo ============================================================================
echo [*] Running Pytest Unit Tests...
python -m pytest tests/ -v
echo.
echo [*] Running 50-Run Monte Carlo Pointing Benchmark...
python tests/run_monte_carlo.py
pause
