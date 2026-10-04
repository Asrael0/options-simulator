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

:: Avvia il server in un processo nascosto: questa finestra puo' chiudersi
:: subito. Il browser lo apre il server da solo quando e' pronto.
echo Avvio del simulatore...
powershell -NoProfile -Command "Start-Process -WindowStyle Hidden -FilePath 'uv' -ArgumentList 'run','options-simulator' -WorkingDirectory '%~dp0.'"

:: Aspetta al massimo 60 secondi che il server risponda.
for /l %%i in (1,1,60) do (
    netstat -ano | findstr /r /c:":8080 .*LISTENING" >nul
    if not errorlevel 1 exit /b
    timeout /t 1 /nobreak >nul
)

echo.
echo Il simulatore non e' partito. Per vedere l'errore apri un terminale
echo in questa cartella e scrivi:  uv run options-simulator
pause
exit /b 1
