IF EXIST "%~1" (
    python "%~dp0checkpoints.py" "%~1"
) ELSE (
    python "%~dp0checkpoints.py"
)
pause
