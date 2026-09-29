@echo off
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
  echo Python wurde nicht gefunden. Bitte Python 3 installieren und erneut versuchen.
  pause
  exit /b 1
)
if not exist "demo" mkdir "demo"
if not exist "demo\demo.sqlite3" python -m bewerbungsmanager --db "demo\demo.sqlite3" demo
python -m bewerbungsmanager --db "demo\demo.sqlite3" export --file "demo\beispielbericht.html"
if errorlevel 1 (
  pause
  exit /b 1
)
start "" "demo\beispielbericht.html"
echo Der Demo-Bericht wurde im Browser geoeffnet.
pause
