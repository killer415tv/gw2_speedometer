@echo off
echo ===============================================
echo    GW2 Speedometer Suite - Installation
echo ===============================================
echo.

REM Configure variables
set VENV_DIR=venv
set PYTHON_MIN_VERSION=3.10.9
set PROJECT_NAME=GW2 Speedometer Suite

REM Check if Python is installed
echo [1/6] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.9 or higher from:
    echo https://www.python.org/downloads/
    echo.
    echo IMPORTANT: Check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

REM Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo OK: Python %PYTHON_VERSION% found

REM Check minimum version
python -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.9 or higher required
    echo Current version: %PYTHON_VERSION%
    echo.
    echo Download Python 3.9+ from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo [2/6] Checking pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip is not available
    echo Installing pip...
    python -m ensurepip --upgrade
    if errorlevel 1 (
        echo ERROR: Could not install pip
        pause
        exit /b 1
    )
)
echo OK: pip available

echo.
echo [3/6] Removing previous virtual environment (if exists)...
if exist "%VENV_DIR%" (
    echo Removing %VENV_DIR%...
    rmdir /s /q "%VENV_DIR%"
)

echo.
echo [4/6] Creating virtual environment...
python -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo ERROR: Could not create virtual environment
    pause
    exit /b 1
)
echo OK: Virtual environment created in %VENV_DIR%

echo.
echo [5/6] Activating virtual environment and installing dependencies...
call "%VENV_DIR%\Scripts\activate.bat"

REM Update pip in virtual environment
echo Updating pip...
python -m pip install --upgrade pip

REM Install wheel to avoid compilation issues
echo Installing wheel...
python -m pip install wheel

REM Install main dependencies
echo Installing main dependencies...
python -m pip install -r gw2_speedometer_internal\requirements.txt

if errorlevel 1 (
    echo ERROR: Could not install dependencies
    echo.
    echo Trying individual installation of critical packages...
    
    REM Install packages one by one for better diagnostics
    python -m pip install numpy==1.21.2
    python -m pip install pandas==1.3.2
    python -m pip install scipy==1.7.1
    python -m pip install pynput==1.7.3
    python -m pip install requests==2.26.0
    python -m pip install paho-mqtt==1.5.1
    python -m pip install websocket-client==1.3.3
    
    REM Packages that might be problematic - install without specific version
    echo Installing GUI packages...
    python -m pip install PySide6 || (
        echo WARNING: Could not install PySide2
        echo Some 3D functions may not be available
    )
    
    python -m pip install pyqtgraph || (
        echo WARNING: Could not install pyqtgraph  
        echo Some 3D functions may not be available
    )
    
    python -m pip install pyopengl || (
        echo WARNING: Could not install pyopengl
        echo Some 3D functions may not be available  
    )
    
    python -m pip install opensimplex || (
        echo WARNING: Could not install opensimplex
        echo Some functions may not be available
    )
    
    python -m pip install plotly || (
        echo WARNING: Could not install plotly
        echo Advanced graphics functions may not be available
    )
    
    echo.
    echo WARNING: Installation completed with warnings
    echo Main speedometer should work correctly
    echo Some advanced 3D functions may not be available
) else (
    echo OK: Dependencies installed correctly
)

echo.
echo [6/6] Creating launch scripts...

REM Create main launcher
echo @echo off > launch.bat
echo echo Starting GW2 Speedometer Suite... >> launch.bat
echo cd /d "%%~dp0\gw2_speedometer_internal" >> launch.bat
echo call ..\venv\Scripts\activate.bat >> launch.bat
echo python launcher.py >> launch.bat
echo if errorlevel 1 pause >> launch.bat

REM Create quick speedometer launch script
echo @echo off > quick_speedometer.bat
echo echo Starting Speedometer... >> quick_speedometer.bat
echo cd /d "%%~dp0\gw2_speedometer_internal" >> quick_speedometer.bat
echo call ..\venv\Scripts\activate.bat >> quick_speedometer.bat
echo python speedometer.py >> quick_speedometer.bat
echo pause >> quick_speedometer.bat

REM Create update script
echo @echo off > update.bat
echo echo Updating dependencies... >> update.bat
echo cd /d "%%~dp0\gw2_speedometer_internal" >> update.bat
echo call ..\venv\Scripts\activate.bat >> update.bat
echo python -m pip install --upgrade pip >> update.bat
echo python -m pip install -r requirements.txt --upgrade >> update.bat
echo echo Update completed >> update.bat
echo pause >> update.bat

echo OK: Launch scripts created

echo.
echo ===============================================
echo          INSTALLATION COMPLETED
echo ===============================================
echo.
echo Available scripts:
echo   - launch.bat         - Main launcher
echo   - quick_speedometer.bat - Direct speedometer  
echo   - update.bat         - Update dependencies
echo.
echo To start the program:
echo   1. Run launch.bat for the complete launcher
echo   2. Or run quick_speedometer.bat for quick start
echo.
echo IMPORTANT: 
echo - Always use these scripts to run the program
echo - DO NOT run .py files directly 
echo - Virtual environment activates automatically
echo.

REM Ask if user wants to run the program now
set /p choice="Do you want to run the launcher now? (y/n): "
if /i "%choice%"=="y" (
    echo.
    echo Starting launcher...
    call launch.bat
) else (
    echo.
    echo Run 'launch.bat' when you want to use the program
)

echo.
echo ===============================================
pause 