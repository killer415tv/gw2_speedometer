@echo off 
echo Actualizando dependencias... 
cd /d "%~dp0" 
call venv\Scripts\activate.bat 
python -m pip install --upgrade pip 
python -m pip install -r requirements.txt --upgrade 
echo Actualizacion completada 
pause 
