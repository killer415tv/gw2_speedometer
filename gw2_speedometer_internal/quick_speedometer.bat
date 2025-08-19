@echo off 
echo Starting Speedometer... 
cd /d "%~dp0\gw2_speedometer_internal" 
call venv\Scripts\activate.bat 
python speedometer.py 
pause 
