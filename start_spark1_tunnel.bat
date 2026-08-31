@echo off
setlocal

rem Forward the local ComfyUI port on spark1 to this 5800H machine.
rem spark1's own 127.0.0.1:8188 should already reach spark2 ComfyUI.
set "SPARK1_USER=yang1992"
set "SPARK1_HOST=192.168.3.75"

echo Forwarding 127.0.0.1:8188 to %SPARK1_USER%@%SPARK1_HOST%:127.0.0.1:8188
ssh -N -L 8188:127.0.0.1:8188 %SPARK1_USER%@%SPARK1_HOST% ^
  -o ExitOnForwardFailure=yes ^
  -o ServerAliveInterval=30 ^
  -o ServerAliveCountMax=3

if errorlevel 1 (
  echo.
  echo SSH tunnel failed. Confirm the account and authorized key on spark1.
  pause
)
