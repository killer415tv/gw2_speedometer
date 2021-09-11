IF EXIST "%~1" (
    python ghost_online.py "%~1"
) ELSE (
    python ghost_online.py
)
pause
