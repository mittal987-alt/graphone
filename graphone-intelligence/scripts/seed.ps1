$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot\..
& .\.venv\Scripts\python.exe scripts\seed_entities.py
