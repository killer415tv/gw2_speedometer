IF EXIST "%~1" (
    python ghost3d.py "%~1"
) ELSE (
    python ghost3d.py
)
pause
