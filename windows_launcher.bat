@echo off
setlocal ENABLEEXTENSIONS
set "PYTHONUTF8=1"
set "PYTHONDONTWRITEBYTECODE=1"
set "ROOT=%~dp0"
pushd "%ROOT%"
title Syntheris Continuum V5.1.0
set "PY=%ROOT%.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERROR] The application environment is missing. Run setup.bat first.
  popd
  endlocal & exit /b 1
)
set "PYTHONPYCACHEPREFIX=%ROOT%.venv\.pycache"
"%PY%" -B -c "import sys; assert sys.prefix != sys.base_prefix; assert sys.version_info[:2] == (3,11)"
if errorlevel 1 (
  echo [ERROR] Invalid application environment. Run setup.bat to check it.
  popd
  endlocal & exit /b 1
)
echo [START] Syntheris Continuum V5.1.0
"%PY%" -B "%ROOT%quick_launcher.py"
set "RC=%ERRORLEVEL%"
echo [STATUS] Application closed with exit code %RC%.
popd
endlocal & exit /b %RC%
