IF EXIST "%~1" (
    python checkpoints.py "%~1"
) ELSE (
    python checkpoints.py
)
pause