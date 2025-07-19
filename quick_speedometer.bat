@echo off 
echo Iniciando Speedometer... 
cd /d "%~dp0" 
call venv\Scripts\activate.bat 
python speedometer.py 
pause 
