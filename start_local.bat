@echo off
setlocal
cd /d "%~dp0"
set "LOG=%~dp0director\server.log"
echo [%date% %time%] starting Director Desk >> "%LOG%"
start "H3 Director Desk" /min "%~dp0director\run_server.bat"
echo Director Desk started at http://127.0.0.1:8088/
echo Keep the minimized "H3 Director Desk" window running.
ping 127.0.0.1 -n 4 >nul
start "" http://127.0.0.1:8088/
