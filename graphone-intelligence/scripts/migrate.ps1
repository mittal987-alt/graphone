$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot\..
& .\.venv\Scripts\python.exe -m alembic upgrade head
