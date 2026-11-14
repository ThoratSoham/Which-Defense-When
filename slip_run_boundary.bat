@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"$env:PY=$(where python); ^
& $env:PY slip_gen_boundary.py"
