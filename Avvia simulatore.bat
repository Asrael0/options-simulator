@echo off
title Simulatore di Opzioni
cd /d "%~dp0"

:: Se il simulatore e' gia' acceso, apre solo il browser.
netstat -ano | findstr /r /c:":8080 .*LISTENING" >nul
if not errorlevel 1 (
    start "" http://127.0.0.1:8080
    exit /b
)

where uv >nul 2>&1
if errorlevel 1 (
    echo uv non e' installato. Installalo da https://docs.astral.sh/uv/ e riprova.
    pause
    exit /b 1
)

echo Avvio del simulatore... il browser si aprira' da solo.
echo Per spegnerlo chiudi questa finestra.
echo.
uv run simulatore-opzioni
if errorlevel 1 pause
