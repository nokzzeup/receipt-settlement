@echo off
rem Double-click to run THIS PC as the shared team server (Windows).
rem Other PCs and phones on the same Wi-Fi open the address shown in this window.
rem Server data (DB, receipt photos) is kept in the server-data folder, separate from development.
rem Node.js / Python missing? They are downloaded automatically into the .tools folder.
rem Close this window to stop the server.
rem KEEP THIS FILE ASCII-ONLY: cmd.exe reads .bat files in the OS code page (cp949).
title Receipt Settlement - team server
cd /d "%~dp0"
call scripts\bootstrap\ensure-node.cmd
if errorlevel 1 (
  pause
  exit /b 1
)
node scripts\serve.mjs
if errorlevel 1 pause
