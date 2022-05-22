IF EXIST "%~1" (
    python "~dp0ghost_online.py" "%~1"
) ELSE (
    python "~dp0ghost_online.py"
)
pause
