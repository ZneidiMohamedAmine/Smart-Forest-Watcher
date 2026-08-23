@echo off
REM Stops the local dev stack processes started by start_local.bat (Django + Celery).
REM Leaves Postgres/Redis containers running — use `docker compose stop db redis` to stop those too.

cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "stop_local.ps1"
