@echo off
setlocal
cd /d "%~dp0"
python director\serve.py --host 127.0.0.1 --port 8088 --comfy http://192.168.3.75:8188
pause
