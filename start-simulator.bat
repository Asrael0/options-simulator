@echo off
title Options Simulator
cd /d "%~dp0"

:: If the simulator is already running, just open the browser.
netstat -ano | findstr /r /c:":8080 .*LISTENING" >nul
if not errorlevel 1 (
    start "" http://127.0.0.1:8080
    exit /b
)

where uv >nul 2>&1
if errorlevel 1 (
    echo uv is not installed. Install it from https://docs.astral.sh/uv/ and try again.
    pause
    exit /b 1
)

:: Start the server in a hidden process, so this window can close right away.
:: The server opens the browser by itself when it is ready.
echo Starting the simulator...
powershell -NoProfile -Command "Start-Process -WindowStyle Hidden -FilePath 'uv' -ArgumentList 'run','options-simulator' -WorkingDirectory '%~dp0.'"

:: Wait up to 60 seconds for the server to answer.
for /l %%i in (1,1,60) do (
    netstat -ano | findstr /r /c:":8080 .*LISTENING" >nul
    if not errorlevel 1 exit /b
    timeout /t 1 /nobreak >nul
)

echo.
echo The simulator did not start. To see the error, open a terminal in this
echo folder and type:  uv run options-simulator
pause
exit /b 1
