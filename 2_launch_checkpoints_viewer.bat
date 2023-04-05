
@ECHO OFF
echo Launching checkpoint viewer...
echo keep this window open

IF EXIST "%~1" (
    python "%~dp0checkpoints.py" "%~1"
) ELSE (
    python "%~dp0checkpoints.py"
)
