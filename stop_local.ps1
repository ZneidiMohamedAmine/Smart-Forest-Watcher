$ErrorActionPreference = 'SilentlyContinue'

Write-Host "Stopping Django (daphne)..."
Get-CimInstance Win32_Process -Filter "name = 'python.exe'" |
    Where-Object { $_.CommandLine -like '*start_daphne.py*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

Write-Host "Stopping Celery worker..."
Get-CimInstance Win32_Process -Filter "name = 'python.exe'" |
    Where-Object { $_.CommandLine -like '*celery*' -and $_.CommandLine -like '*project*worker*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

Write-Host "Stopping TTN sensor listener..."
Get-CimInstance Win32_Process -Filter "name = 'python.exe'" |
    Where-Object { $_.CommandLine -like '*listen_ttn*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

Write-Host "Done. Postgres and Redis containers were left running."
Write-Host "To stop those too: docker compose stop db redis"
