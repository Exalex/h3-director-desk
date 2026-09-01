@echo off
setlocal
cd /d "%~dp0.."
set "LOG=%~dp0server.log"
:run
echo [%date% %time%] launching Director Desk >> "%LOG%"
python director\serve.py --host 127.0.0.1 --port 8088 --comfy http://192.168.3.75:8188 >> "%LOG%" 2>&1
echo [%date% %time%] Director Desk exited with code %ERRORLEVEL%; restarting in 2 seconds >> "%LOG%"
timeout /t 2 /nobreak >nul
goto run
