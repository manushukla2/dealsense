# setup.ps1 - create the venv, install dependencies, check ffmpeg
Set-Location $PSScriptRoot\..

Write-Host "Creating virtual environment..." -ForegroundColor Cyan
python -m venv .venv

Write-Host "Activating..." -ForegroundColor Cyan
& .venv\Scripts\Activate.ps1

Write-Host "Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

Write-Host "Installing requirements..." -ForegroundColor Cyan
pip install -r requirements.txt

Write-Host "Checking ffmpeg..." -ForegroundColor Cyan
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "ffmpeg not found. Installing via winget..." -ForegroundColor Yellow
    winget install Gyan.FFmpeg
    Write-Host "Restart your terminal after this script finishes." -ForegroundColor Yellow
} else {
    Write-Host "ffmpeg OK: $(ffmpeg -version 2>&1 | Select-Object -First 1)" -ForegroundColor Green
}

Write-Host "Checking .env..." -ForegroundColor Cyan
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host ".env created from .env.example. Fill in your API keys before running." -ForegroundColor Yellow
} else {
    Write-Host ".env already exists." -ForegroundColor Green
}

Write-Host ""
Write-Host "Setup complete. Next steps:" -ForegroundColor Green
Write-Host "  1. Fill in .env with your GROQ_API_KEY and ANTHROPIC_API_KEY"
Write-Host "  2. Run: uvicorn api.main:app --port 8000"
Write-Host "  3. Or run the demo: .\scripts\run_demo.ps1 <path-to-audio-file>"
