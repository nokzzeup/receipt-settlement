@echo off
rem Double-click to run (Windows). First run installs everything (npm run setup),
rem then starts backend + frontend and opens the browser. Close this window to stop.
rem Node.js / Python missing? They are downloaded automatically into the .tools folder.
rem KEEP THIS FILE ASCII-ONLY: cmd.exe reads .bat files in the OS code page (cp949).
title Receipt Settlement - dev server
cd /d "%~dp0"
call scripts\bootstrap\ensure-node.cmd
if errorlevel 1 (
  pause
  exit /b 1
)
node scripts\launch.mjs
if errorlevel 1 pause
