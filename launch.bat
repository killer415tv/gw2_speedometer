@echo off 
echo Iniciando GW2 Speedometer Suite... 
cd /d "%~dp0" 
call venv\Scripts\activate.bat 
python launcher.py 
if errorlevel 1 pause 
