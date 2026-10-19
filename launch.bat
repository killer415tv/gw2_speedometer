@echo off
rem ======================================================================
rem  GW2 Speedometer Suite - one-file installer + launcher (Windows 10/11)
rem  Instalador + lanzador en un solo archivo (Windows 10/11)
rem
rem  Usage / Uso:
rem    launch.bat               start the launcher / abre el launcher
rem    launch.bat speedometer   start the speedometer directly / abre solo el speedometer
rem    launch.bat qt            speedometer with the new Qt HUD (experimental) / con el HUD nuevo
rem    launch.bat reinstall     rebuild the environment / reconstruye el entorno
rem
rem  Everything is stored INSIDE this folder (no admin rights, no system
rem  Python, no PATH changes):
rem    tools\uv         uv (tiny Python manager, downloaded once)
rem    tools\python     Python 3.12 managed by uv
rem    tools\uv-cache   download cache
rem    venv             virtual environment with the dependencies
rem  Delete the whole folder to uninstall.
rem ======================================================================
setlocal EnableExtensions DisableDelayedExpansion
title GW2 Speedometer Suite

rem ---- Settings --------------------------------------------------------
rem uv is pinned and verified with SHA-256 (asset: uv-x86_64-pc-windows-msvc.zip).
rem To upgrade: change both values (hash is published next to the release asset).
set "UV_VERSION=0.13.1"
set "UV_SHA256=3b2661a463a5baea7f5076ea2b25ab71d77f36a6c0d809e5350651792f80a672"
set "PY_VERSION=3.12"
set "APP_DIR=gw2_speedometer_internal"

rem ---- Work from the folder that contains this file --------------------
cd /d "%~dp0"
if errorlevel 1 goto :err_cd
set "ROOT=%~dp0"

rem ---- Arguments -------------------------------------------------------
set "APP=launcher.py"
set "APP_ARGS="
set "FORCE=0"
if /i "%~1"=="speedometer" set "APP=speedometer.py"
if /i "%~1"=="qt" set "APP=speedometer.py"
if /i "%~1"=="qt" set "APP_ARGS=--qt-hud"
if /i "%~1"=="reinstall" set "FORCE=1"
if /i "%~1"=="--reinstall" set "FORCE=1"

echo ===============================================
echo    GW2 Speedometer Suite
echo ===============================================

rem ---- Sanity checks ---------------------------------------------------
if /i "%PROCESSOR_ARCHITECTURE%"=="x86" if not defined PROCESSOR_ARCHITEW6432 goto :err_arch
if not exist "%ROOT%%APP_DIR%\launcher.py" goto :err_extract
if not exist "%ROOT%%APP_DIR%\requirements.txt" goto :err_extract

rem ---- Paths and environment (everything stays inside this folder) -----
set "TOOLS=%ROOT%tools"
set "UV_DIR=%TOOLS%\uv"
set "UV_EXE=%UV_DIR%\uv.exe"
set "VENV_DIR=%ROOT%venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "STAMP_FILE=%VENV_DIR%\.installed"
set "REQ=%ROOT%%APP_DIR%\requirements.txt"

set "UV_PYTHON_INSTALL_DIR=%TOOLS%\python"
set "UV_CACHE_DIR=%TOOLS%\uv-cache"
set "UV_PYTHON_PREFERENCE=only-managed"
set "UV_PYTHON_DOWNLOADS=automatic"
set "UV_NO_CONFIG=1"
set "UV_HTTP_TIMEOUT=120"
set "PYTHONIOENCODING=utf-8"
rem Ignore leftovers of other Python installs on this PC
set "UV_PYTHON="
set "VIRTUAL_ENV="
set "PYTHONHOME="
set "PYTHONPATH="

rem ---- Fast path: already installed and requirements.txt unchanged -----
if "%FORCE%"=="1" goto :setup
if not exist "%VENV_PY%" goto :setup
if not exist "%STAMP_FILE%" goto :setup
call :get_hash
set "OLD_STAMP="
set /p OLD_STAMP=<"%STAMP_FILE%"
if not defined REQ_HASH goto :fast_check
set "NEW_STAMP=py%PY_VERSION%-%REQ_HASH%"
if not "%OLD_STAMP%"=="%NEW_STAMP%" goto :setup
:fast_check
"%VENV_PY%" -c "import tkinter, numpy" >nul 2>&1
if errorlevel 1 goto :setup
if not defined APP_ARGS goto :run
"%VENV_PY%" -c "import PySide6.QtWidgets" >nul 2>&1
if errorlevel 1 goto :setup
goto :run

rem ======================================================================
:setup
echo.
echo First run, or requirements changed: installing. Internet is required.
echo Primera ejecucion, o cambiaron los requisitos: instalando. Hace falta internet.
echo This can take several minutes / Puede tardar varios minutos.
echo Folder / Carpeta: "%ROOT%"

call :get_hash
if not defined REQ_HASH goto :err_hash
set "NEW_STAMP=py%PY_VERSION%-%REQ_HASH%"

echo.
echo [1/3] uv (Python manager) ...
if not exist "%TOOLS%" mkdir "%TOOLS%" >nul 2>&1
if exist "%UV_EXE%" goto :check_uv

:download_uv
echo Downloading uv %UV_VERSION% / Descargando uv %UV_VERSION% ...
if not exist "%UV_DIR%" mkdir "%UV_DIR%" >nul 2>&1
set "UV_ZIP=%TOOLS%\uv-download.zip"
set "UV_URL=https://github.com/astral-sh/uv/releases/download/%UV_VERSION%/uv-x86_64-pc-windows-msvc.zip"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; try { [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -UseBasicParsing -Uri $env:UV_URL -OutFile $env:UV_ZIP; $h=(Get-FileHash -Algorithm SHA256 -LiteralPath $env:UV_ZIP).Hash; if ($h -ne $env:UV_SHA256) { Write-Host 'SHA-256 mismatch / el hash no coincide'; exit 3 }; Expand-Archive -LiteralPath $env:UV_ZIP -DestinationPath $env:UV_DIR -Force } catch { Write-Host $_.Exception.Message; exit 2 }"
set "PS_RC=%ERRORLEVEL%"
if exist "%UV_ZIP%" del /f /q "%UV_ZIP%" >nul 2>&1
if not "%PS_RC%"=="0" goto :err_download

:check_uv
"%UV_EXE%" --version >nul 2>&1
if not errorlevel 1 goto :uv_ok
if defined UV_TRIED goto :err_uv_run
set "UV_TRIED=1"
echo uv looks damaged, downloading it again / uv parece danado, se descarga de nuevo ...
rd /s /q "%UV_DIR%" >nul 2>&1
goto :download_uv

:uv_ok
echo OK: uv ready / uv listo

echo.
echo [2/3] Python %PY_VERSION% + virtual environment (folder: venv) ...
"%UV_EXE%" venv --clear --seed --python %PY_VERSION% "%VENV_DIR%"
if errorlevel 1 goto :err_venv
if not exist "%VENV_PY%" goto :err_venv

echo.
echo [3/3] Installing packages from requirements.txt (large download) ...
echo Instalando paquetes de requirements.txt (descarga grande) ...
"%UV_EXE%" pip install --python "%VENV_PY%" -r "%REQ%"
if errorlevel 1 goto :err_pip

"%VENV_PY%" -c "import tkinter, numpy, pandas, scipy, pynput, requests, websocket, PySide6, pyqtgraph"
if errorlevel 1 goto :err_verify

>"%STAMP_FILE%" echo %NEW_STAMP%
echo.
echo OK: installation finished / instalacion terminada.

rem ======================================================================
:run
echo.
if defined APP_ARGS goto :msg_qt
if /i "%APP%"=="speedometer.py" goto :msg_speedometer
echo Starting GW2 Speedometer Suite / Iniciando GW2 Speedometer Suite ...
goto :msg_done
:msg_speedometer
echo Starting Speedometer / Iniciando Speedometer ...
goto :msg_done
:msg_qt
echo Starting Speedometer with the new HUD / Iniciando Speedometer con el HUD nuevo ...
echo GW2 must be in Windowed or Windowed Fullscreen / GW2 debe estar en Ventana o Ventana a pantalla completa.
echo Ctrl+Shift+M = map selector / selector de mapas.  Ctrl+Shift+O = optional widgets / widgets opcionales.
:msg_done
echo Keep this window open while the program runs / No cierres esta ventana mientras uses el programa.
cd /d "%ROOT%%APP_DIR%"
if errorlevel 1 goto :err_cd
"%VENV_PY%" %APP% %APP_ARGS%
set "RC=%ERRORLEVEL%"
if "%RC%"=="0" goto :end_ok
echo.
echo The program ended with an error (code %RC%). Read the messages above.
echo El programa termino con un error (codigo %RC%). Lee los mensajes de arriba.
echo If it keeps failing, run "launch.bat reinstall" / Si sigue fallando, ejecuta "launch.bat reinstall".
goto :fail

:end_ok
endlocal
exit /b 0

rem ======================================================================
rem  Subroutine: SHA-256 of requirements.txt, stored in REQ_HASH (empty on failure)
rem ======================================================================
:get_hash
set "REQ_HASH="
for /f "usebackq delims=" %%H in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-FileHash -Algorithm SHA256 -LiteralPath $env:REQ).Hash" 2^>nul`) do set "REQ_HASH=%%H"
exit /b 0

rem ======================================================================
rem  Error handling (every error ends with a pause so the window stays open)
rem ======================================================================
:err_cd
echo.
echo ERROR: cannot enter the folder of this script / no se puede entrar en la carpeta del script.
echo Network paths ^(\\server\share^) are not supported: copy the folder to a local drive, e.g. C:\GW2Speedometer
echo Las rutas de red no estan soportadas: copia la carpeta a un disco local.
goto :fail

:err_arch
echo.
echo ERROR: 64-bit Windows is required / se necesita Windows de 64 bits.
goto :fail

:err_extract
echo.
echo ERROR: program files not found next to launch.bat / no se encuentran los archivos del programa.
echo Extract the WHOLE zip first ^(right click - Extract All^), then run launch.bat from the extracted folder.
echo Primero descomprime TODO el zip ^(clic derecho - Extraer todo^) y ejecuta launch.bat desde la carpeta descomprimida.
goto :fail

:err_hash
echo.
echo ERROR: could not read requirements.txt with PowerShell / no se pudo leer requirements.txt con PowerShell.
echo Check that PowerShell works and that security software is not blocking it.
echo Comprueba que PowerShell funciona y que el antivirus no lo bloquea.
goto :fail

:err_download
echo.
echo ERROR: could not download or unpack uv ^(code %PS_RC%^) / no se pudo descargar o descomprimir uv.
echo Possible causes / Posibles causas:
echo  - No internet, proxy or firewall / sin internet, proxy o cortafuegos.
echo  - Antivirus blocked the download / el antivirus bloqueo la descarga.
echo  - Code 3 = corrupted download, try again / codigo 3 = descarga corrupta, reintenta.
echo Manual alternative / Alternativa manual: download
echo   %UV_URL%
echo and put uv.exe inside "%UV_DIR%" , then run launch.bat again.
echo y copia uv.exe dentro de esa carpeta tools\uv, y ejecuta launch.bat otra vez.
goto :fail

:err_uv_run
echo.
echo ERROR: uv cannot run / uv no se puede ejecutar: "%UV_EXE%"
echo Your antivirus or SmartScreen may have blocked or removed it. Allow the folder "%TOOLS%"
echo in your antivirus, delete the folder tools\uv and run launch.bat again.
echo Es posible que el antivirus o SmartScreen lo haya bloqueado. Permite la carpeta tools, borra tools\uv y reintenta.
goto :fail

:err_venv
echo.
echo ERROR: could not create Python %PY_VERSION% / no se pudo crear el entorno con Python %PY_VERSION%.
echo Possible causes / Posibles causas:
echo  - No internet or proxy blocks github.com ^(Python is downloaded from GitHub^) / sin internet.
echo  - Antivirus blocked files in "%TOOLS%" / el antivirus bloqueo archivos.
echo  - Folder path has unusual characters or is too long: move the folder to e.g. C:\GW2Speedometer
echo    La ruta tiene caracteres raros o es muy larga: mueve la carpeta a C:\GW2Speedometer
echo  - Not enough disk space ^(about 2 GB free needed^) / poco espacio en disco.
goto :fail

:err_pip
echo.
echo ERROR: could not install packages / no se pudieron instalar los paquetes.
echo Check your internet connection and run launch.bat again: finished downloads are kept in cache.
echo Comprueba tu conexion y ejecuta launch.bat otra vez: lo ya descargado se conserva.
echo If it fails again: move the folder to a short path like C:\GW2Speedometer ^(Windows path length limit^),
echo allow the folder in your antivirus, and check free disk space.
goto :fail

:err_verify
echo.
echo ERROR: packages were installed but cannot be imported / los paquetes no se pueden importar.
echo Usually the antivirus removed some files. Allow this folder in your antivirus and run:
echo   launch.bat reinstall
echo Normalmente el antivirus borro archivos. Permite esta carpeta y ejecuta: launch.bat reinstall
goto :fail

:fail
echo.
echo ===============================================
echo  Setup/launch FAILED / Fallo la instalacion o el inicio
echo ===============================================
pause
endlocal
exit /b 1
