@echo off
echo ===============================================
echo    GW2 Speedometer Suite - Instalacion
echo ===============================================
echo.

REM Configurar variables
set VENV_DIR=venv
set PYTHON_MIN_VERSION=3.9
set PROJECT_NAME=GW2 Speedometer Suite

REM Verificar si Python esta instalado
echo [1/6] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Python no esta instalado o no esta en PATH
    echo.
    echo Por favor instala Python 3.9 o superior desde:
    echo https://www.python.org/downloads/
    echo.
    echo IMPORTANTE: Marca la opcion "Add Python to PATH" durante la instalacion
    echo.
    pause
    exit /b 1
)

REM Obtener version de Python
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION% encontrado

REM Verificar version minima
python -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Se requiere Python 3.9 o superior
    echo Version actual: %PYTHON_VERSION%
    echo.
    echo Descarga Python 3.9+ desde: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo [2/6] Verificando pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: pip no esta disponible
    echo Instalando pip...
    python -m ensurepip --upgrade
    if errorlevel 1 (
        echo ❌ ERROR: No se pudo instalar pip
        pause
        exit /b 1
    )
)
echo ✅ pip disponible

echo.
echo [3/6] Eliminando entorno virtual anterior (si existe)...
if exist "%VENV_DIR%" (
    echo Eliminando %VENV_DIR%...
    rmdir /s /q "%VENV_DIR%"
)

echo.
echo [4/6] Creando entorno virtual...
python -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo ❌ ERROR: No se pudo crear el entorno virtual
    pause
    exit /b 1
)
echo ✅ Entorno virtual creado en %VENV_DIR%

echo.
echo [5/6] Activando entorno virtual e instalando dependencias...
call "%VENV_DIR%\Scripts\activate.bat"

REM Actualizar pip en el entorno virtual
echo Actualizando pip...
python -m pip install --upgrade pip

REM Instalar wheel para evitar problemas de compilacion
echo Instalando wheel...
python -m pip install wheel

REM Instalar dependencias principales
echo Instalando dependencias principales...
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo ❌ ERROR: No se pudieron instalar las dependencias
    echo.
    echo Intentando instalacion individual de paquetes criticos...
    
    REM Instalar paquetes uno por uno para mejor diagnostico
    python -m pip install numpy==1.21.2
    python -m pip install pandas==1.3.2
    python -m pip install scipy==1.7.1
    python -m pip install pynput==1.7.3
    python -m pip install requests==2.26.0
    python -m pip install paho-mqtt==1.5.1
    python -m pip install websocket-client==1.3.3
    
    REM Paquetes que pueden ser problematicos - instalar sin version especifica
    echo Instalando paquetes de GUI...
    python -m pip install PySide2 || (
        echo ⚠️ ADVERTENCIA: No se pudo instalar PySide2
        echo Algunas funciones 3D pueden no estar disponibles
    )
    
    python -m pip install pyqtgraph || (
        echo ⚠️ ADVERTENCIA: No se pudo instalar pyqtgraph  
        echo Algunas funciones 3D pueden no estar disponibles
    )
    
    python -m pip install pyopengl || (
        echo ⚠️ ADVERTENCIA: No se pudo instalar pyopengl
        echo Algunas funciones 3D pueden no estar disponibles  
    )
    
    python -m pip install opensimplex || (
        echo ⚠️ ADVERTENCIA: No se pudo instalar opensimplex
        echo Algunas funciones pueden no estar disponibles
    )
    
    python -m pip install plotly || (
        echo ⚠️ ADVERTENCIA: No se pudo instalar plotly
        echo Funciones de graficos avanzados pueden no estar disponibles
    )
    
    echo.
    echo ⚠️ Instalacion completada con advertencias
    echo El speedometer principal deberia funcionar correctamente
    echo Algunas funciones 3D avanzadas pueden no estar disponibles
) else (
    echo ✅ Dependencias instaladas correctamente
)

echo.
echo [6/6] Creando scripts de lanzamiento...

REM Crear launcher principal
echo @echo off > launch.bat
echo echo Iniciando GW2 Speedometer Suite... >> launch.bat
echo cd /d "%%~dp0" >> launch.bat
echo call venv\Scripts\activate.bat >> launch.bat
echo python launcher.py >> launch.bat
echo if errorlevel 1 pause >> launch.bat

REM Crear script de lanzamiento rapido del speedometer
echo @echo off > quick_speedometer.bat
echo echo Iniciando Speedometer... >> quick_speedometer.bat
echo cd /d "%%~dp0" >> quick_speedometer.bat
echo call venv\Scripts\activate.bat >> quick_speedometer.bat
echo python speedometer.py >> quick_speedometer.bat
echo pause >> quick_speedometer.bat

REM Crear script de actualizacion
echo @echo off > update.bat
echo echo Actualizando dependencias... >> update.bat
echo cd /d "%%~dp0" >> update.bat
echo call venv\Scripts\activate.bat >> update.bat
echo python -m pip install --upgrade pip >> update.bat
echo python -m pip install -r requirements.txt --upgrade >> update.bat
echo echo Actualizacion completada >> update.bat
echo pause >> update.bat

echo ✅ Scripts de lanzamiento creados

echo.
echo ===============================================
echo          ✅ INSTALACION COMPLETADA
echo ===============================================
echo.
echo Scripts disponibles:
echo   • launch.bat         - Launcher principal
echo   • quick_speedometer.bat - Speedometer directo  
echo   • update.bat         - Actualizar dependencias
echo.
echo Para iniciar el programa:
echo   1. Ejecuta launch.bat para el launcher completo
echo   2. O ejecuta quick_speedometer.bat para inicio rapido
echo.
echo IMPORTANTE: 
echo - Siempre usa estos scripts para ejecutar el programa
echo - NO ejecutes los archivos .py directamente 
echo - El entorno virtual se activa automaticamente
echo.

REM Preguntar si quiere ejecutar el programa ahora
set /p choice="¿Quieres ejecutar el launcher ahora? (s/n): "
if /i "%choice%"=="s" (
    echo.
    echo Iniciando launcher...
    call launch.bat
) else (
    echo.
    echo Ejecuta 'launch.bat' cuando quieras usar el programa
)

echo.
echo ===============================================
pause 