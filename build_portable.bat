@echo off
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"
where npm >nul 2>nul
if errorlevel 1 (
  echo npm not found
  exit /b 1
)
npm install
if errorlevel 1 exit /b %errorlevel%
npm run dist:win
exit /b %errorlevel%
