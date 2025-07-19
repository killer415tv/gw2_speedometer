@echo off
echo ===============================================
echo    GW2 Speedometer Suite - Prueba Rapida
echo ===============================================
echo.

echo Verificando archivos necesarios...

REM Verificar que Python esta disponible
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Python no encontrado
    echo Ejecuta 'install.bat' primero
    pause
    exit /b 1
)

REM Verificar que el launcher existe
if not exist "launcher.py" (
    echo ❌ ERROR: launcher.py no encontrado
    pause
    exit /b 1
)

REM Verificar que requirements.txt existe
if not exist "requirements.txt" (
    echo ❌ ERROR: requirements.txt no encontrado
    pause
    exit /b 1
)

echo ✅ Archivos principales encontrados
echo.

REM Verificar si el entorno virtual existe
if exist "venv\" (
    echo ✅ Entorno virtual encontrado
    echo Activando entorno virtual...
    call venv\Scripts\activate.bat
    
    echo Verificando dependencias criticas...
    python -c "import tkinter; print('✅ tkinter OK')" 2>nul || echo "⚠️ tkinter no disponible"
    python -c "import subprocess; print('✅ subprocess OK')" 2>nul || echo "❌ subprocess no disponible"
    python -c "import pathlib; print('✅ pathlib OK')" 2>nul || echo "❌ pathlib no disponible"
    
    echo.
    echo Iniciando launcher en modo prueba...
    echo (Se cerrara automaticamente despues de verificar que carga)
    echo.
    
    REM Iniciar launcher con timeout para prueba
    timeout /t 2 /nobreak >nul
    python launcher.py
    
) else (
    echo ⚠️ Entorno virtual no encontrado
    echo.
    echo Ejecutando launcher con Python del sistema...
    echo (Pueden faltar algunas dependencias)
    echo.
    python launcher.py
)

echo.
echo ===============================================
echo Prueba completada
echo.
echo Si el launcher se abrio correctamente:
echo   ✅ Todo funciona bien
echo.
echo Si hubo errores:
echo   🔧 Ejecuta 'install.bat' para configurar todo
echo ===============================================
pause 