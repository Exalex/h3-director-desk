@echo off
setlocal
cd /d "%~dp0"
python director\serve.py --host 127.0.0.1 --port 8088 --comfy http://127.0.0.1:8188
pause
