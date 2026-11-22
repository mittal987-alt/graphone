$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot\..
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Add credentials before live crawls." -ForegroundColor Yellow
}

docker compose up --build
