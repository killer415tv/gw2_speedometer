@ECHO OFF
CLS
ECHO 1.MAP MULTIPLAYER
ECHO 2.MAP OFFLINE
ECHO.

CHOICE /C 12 /M "Enter your choice:"

:: Note - list ERRORLEVELS in decreasing order
IF ERRORLEVEL 2 GOTO Offline
IF ERRORLEVEL 1 GOTO Online

:Offline
python "%~dp0map_realtime.py"
pause
GOTO End

:Online
python "%~dp0map_realtime_multiplayer.py"
pause
GOTO End
