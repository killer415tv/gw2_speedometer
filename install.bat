@echo off
rem Compatibility alias: everything now lives in launch.bat.
rem Alias de compatibilidad: todo esta ahora en launch.bat.
call "%~dp0launch.bat" %*
exit /b %ERRORLEVEL%
