@echo off
REM Launches the full local dev stack: Docker (Postgres+Redis), Django (daphne), Celery worker.
REM Run from cmd.exe: start_local.bat

cd /d "%~dp0"

echo Checking Docker Desktop...
docker ps >nul 2>&1
if errorlevel 1 (
    echo Docker Desktop is not running. Starting it now, this can take a minute...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    :waitdocker
    timeout /t 5 >nul
    docker ps >nul 2>&1
    if errorlevel 1 goto waitdocker
    echo Docker is ready.
)

echo Starting Postgres + Redis containers...
docker compose up -d db redis

echo Loading config.env...
for /f "usebackq eol=# tokens=1,2 delims==" %%A in ("config.env") do (
    if not "%%A"=="" set "%%A=%%B"
)

REM Overrides for running outside Docker, against localhost-exposed ports
set DJANGO_SETTINGS_MODULE=project.settings.development
set POSTGRES_HOST=localhost
set REDIS_HOST=localhost
set CELERY_BROKER_URL=redis://localhost:6379/0
set CELERY_RESULT_BACKEND=redis://localhost:6379/0
set PORT=8000
set BIND=0.0.0.0

echo Starting Django (daphne) on port 8000...
start "Django" cmd /k "venv\Scripts\python.exe start_daphne.py"

echo Starting Celery worker...
start "Celery" cmd /k "venv\Scripts\python.exe -m celery -A project worker --loglevel=info --pool=solo"

echo All services launching in separate windows. Check http://localhost:8000/health/
