IF EXIST "%~1" (
    python map_realtime.py "%~1"
) ELSE (
    python map_realtime.py
)
pause
