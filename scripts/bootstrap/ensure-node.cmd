@echo off
rem Called with CALL from start-windows.bat / server-windows.bat (shares their environment).
rem Makes sure Node.js 22.22 or newer can be used:
rem   1) Node.js already installed and new enough -> use it
rem   2) otherwise download the official portable Node.js zip from nodejs.org into .tools\
rem      (checked with SHA-256, no admin rights, nothing installed system-wide)
rem      and put it first on PATH for this window only.
rem Needs Windows 10 (1803) or newer for curl.exe and tar.exe.
rem KEEP THIS FILE ASCII-ONLY: cmd.exe reads .cmd files in the OS code page (cp949).

set "BOOT_NODE_VERSION=24.21.0"
set "BOOT_NODE_ARCH=x64"
set "BOOT_NODE_SHA=158f7685b44de51f6c0df1d153526cbcd3e1bc739a8dfc607721cef75de9e541"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "BOOT_NODE_ARCH=arm64"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "BOOT_NODE_SHA=8779b1bde1d39f8d420e3b57aa657b39891af434d3de44a919044cec06785921"
set "BOOT_NODE_NAME=node-v%BOOT_NODE_VERSION%-win-%BOOT_NODE_ARCH%"
for %%I in ("%~dp0..\..") do set "BOOT_ROOT=%%~fI"
set "BOOT_TOOLS=%BOOT_ROOT%\.tools"
set "BOOT_NODE_DIR=%BOOT_TOOLS%\%BOOT_NODE_NAME%"

rem 1) installed Node.js
where node >nul 2>nul
if errorlevel 1 goto portable
node -e "const [a,b]=process.versions.node.split('.').map(Number);process.exit(a>22||(a===22&&b>=22)?0:1)" >nul 2>nul
if not errorlevel 1 exit /b 0
echo Installed Node.js is older than 22.22, so a portable Node.js %BOOT_NODE_VERSION% is used instead.

rem 2) portable Node.js in .tools
:portable
if exist "%BOOT_NODE_DIR%\node.exe" goto use_portable
where curl.exe >nul 2>nul
if errorlevel 1 goto old_windows
where tar.exe >nul 2>nul
if errorlevel 1 goto old_windows
echo.
echo Node.js was not found. Downloading portable Node.js %BOOT_NODE_VERSION% (about 30 MB, first time only).
echo It goes into the .tools folder of this project. Nothing is installed on the PC.
if not exist "%BOOT_TOOLS%" mkdir "%BOOT_TOOLS%"
set "BOOT_ZIP=%BOOT_TOOLS%\%BOOT_NODE_NAME%.zip"
set "BOOT_TMP=%BOOT_TOOLS%\tmp-node"
curl.exe -fL --retry 2 -o "%BOOT_ZIP%" "https://nodejs.org/dist/v%BOOT_NODE_VERSION%/%BOOT_NODE_NAME%.zip"
if errorlevel 1 goto download_failed
certutil -hashfile "%BOOT_ZIP%" SHA256 | findstr /i /x /c:"%BOOT_NODE_SHA%" >nul
if errorlevel 1 goto checksum_failed
if exist "%BOOT_TMP%" rmdir /s /q "%BOOT_TMP%"
mkdir "%BOOT_TMP%"
tar -xf "%BOOT_ZIP%" -C "%BOOT_TMP%"
if errorlevel 1 goto extract_failed
move "%BOOT_TMP%\%BOOT_NODE_NAME%" "%BOOT_NODE_DIR%" >nul
if errorlevel 1 goto extract_failed
rmdir /s /q "%BOOT_TMP%"
del "%BOOT_ZIP%"

:use_portable
set "PATH=%BOOT_NODE_DIR%;%PATH%"
echo Using portable Node.js %BOOT_NODE_VERSION% (.tools\%BOOT_NODE_NAME%)
exit /b 0

:old_windows
echo [ERROR] curl.exe or tar.exe is missing (Windows 10 1803 or newer is needed).
echo         Install Node.js 24 LTS from https://nodejs.org and run this again.
exit /b 1

:download_failed
if exist "%BOOT_ZIP%" del "%BOOT_ZIP%"
echo [ERROR] Could not download Node.js. Check the internet connection and run this again.
echo         Or install Node.js 24 LTS from https://nodejs.org yourself.
exit /b 1

:checksum_failed
if exist "%BOOT_ZIP%" del "%BOOT_ZIP%"
echo [ERROR] The downloaded Node.js file is broken (SHA-256 mismatch). Run this again.
exit /b 1

:extract_failed
if exist "%BOOT_TMP%" rmdir /s /q "%BOOT_TMP%"
echo [ERROR] Could not unpack Node.js into %BOOT_TOOLS%. Close other programs using this folder and run this again.
exit /b 1
