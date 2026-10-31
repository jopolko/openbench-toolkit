@echo off
rem ---------------------------------------------------------------------------
rem  openbench-toolkit - "just chat" launcher.
rem
rem  Starts llama-server in router mode (browse/download/load models from the
rem  webUI Models page - no model has to be picked up front) and opens the
rem  webUI in your default browser. No Metasploit/pentest here - see the
rem  "Enable pentest" button inside the webUI's /pentest panel for that,
rem  or start-openbench.ps1 -Pentest if you want it from the command line.
rem
rem  Double-click this file, or see create-desktop-shortcut.ps1 to pin a
rem  proper desktop icon to it.
rem ---------------------------------------------------------------------------
setlocal
set "HERE=%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%start-openbench.ps1" -Router
if errorlevel 1 (
    echo.
    echo Failed to start - see the message above.
    pause
    exit /b 1
)

start "" "http://127.0.0.1:8080"
