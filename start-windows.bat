@echo off
rem Double-click to run (Windows). First run installs everything (npm run setup),
rem then starts backend + frontend and opens the browser. Close this window to stop.
rem KEEP THIS FILE ASCII-ONLY: cmd.exe reads .bat files in the OS code page (cp949).
title Receipt Settlement - dev server
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js is not installed. Install Node.js 24 LTS from https://nodejs.org and run this again.
  pause
  exit /b 1
)
node scripts\launch.mjs
if errorlevel 1 pause
