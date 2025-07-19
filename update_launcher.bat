@echo off
echo ===============================================
echo    Beetlerank Speed Suite - Logo Update
echo ===============================================
echo.
echo Installing new dependencies for logo support...
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install new dependencies for logo support
echo Installing Pillow (image processing)...
python -m pip install Pillow>=8.0.0

echo Installing cairosvg (SVG conversion)...
python -m pip install cairosvg>=2.5.0

echo.
echo ===============================================
echo          LOGO DEPENDENCIES INSTALLED
echo ===============================================
echo.
echo The launcher will now be able to display the Beetlerank logo.
echo Run 'launch.bat' to see the updated interface.
echo.
pause 