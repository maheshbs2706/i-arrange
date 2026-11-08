@echo off
rem Build a versioned exe into dist\i-arrange-vX.Y.Z.exe
rem Usage:  build.bat                 pick a version from a menu
rem         build.bat 1.2.0           build that exact version
rem         build.bat patch           bump: patch, minor, major, or same
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Run start.bat once to create it.
    pause
    exit /b 1
)
set "PY=.venv\Scripts\python.exe"

if not "%~1"=="" (
    set "CHOICE=%~1"
    goto :build
)

for /f %%v in ('%PY% build.py --current') do set "CUR=%%v"
echo.
echo  i-arrange - build exe
echo  Current version: %CUR%
echo.
echo   [1] Patch   bug fixes
echo   [2] Minor   new features
echo   [3] Major   big changes
echo   [4] Enter a version yourself
echo   [5] Rebuild same version
echo   [Q] Cancel
echo.
set /p SEL=Select an option:

set "CHOICE="
if "%SEL%"=="1" set "CHOICE=patch"
if "%SEL%"=="2" set "CHOICE=minor"
if "%SEL%"=="3" set "CHOICE=major"
if "%SEL%"=="5" set "CHOICE=same"
if "%SEL%"=="4" set /p CHOICE=Version, for example 1.2.0:
if not defined CHOICE (
    echo Cancelled.
    exit /b 0
)

:build
"%PY%" build.py %CHOICE%
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%
