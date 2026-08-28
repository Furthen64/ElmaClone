$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path -LiteralPath 'venv')) {
    Write-Host 'Creating virtual environment...'
    python -m venv venv
}

if (-not (Test-Path -LiteralPath 'venv\Scripts\Activate.ps1')) {
    Write-Host 'The virtual environment is broken. Recreating it...'
    Remove-Item -Recurse -Force 'venv'
    python -m venv venv
}

& 'venv\Scripts\Activate.ps1'
python -m pip install -r requirements.txt
python game.py