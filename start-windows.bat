@echo off
rem Double-click to run (Windows). The window asks how to start:
rem   1 = personal/local (this PC only, development)   2 = shared team server (phones, other PCs)
rem Skip the question: "start-windows.bat server" or "start-windows.bat dev"
rem   (e.g. add " server" to the end of a desktop shortcut's Target).
rem First run installs everything automatically. Close this window to stop.
rem Node.js / Python missing? They are downloaded automatically into the .tools folder.
rem KEEP THIS FILE ASCII-ONLY: cmd.exe reads .bat files in the OS code page (cp949).
rem The Korean menu is printed by scripts\start.mjs instead.
title Receipt Settlement
cd /d "%~dp0"
call scripts\bootstrap\ensure-node.cmd
if errorlevel 1 (
  pause
  exit /b 1
)
node scripts\start.mjs %*
if errorlevel 1 pause
