# Сборка Genis в .exe (папка dist\Genis)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Сначала запусти setup.ps1"
}

$python = ".venv\Scripts\python.exe"

Write-Host "Ставлю PyInstaller..." -ForegroundColor Cyan
& $python -m pip install --upgrade pyinstaller --quiet

Write-Host "Готовлю модель для встраивания..." -ForegroundColor Cyan
& $python prepare_model.py

Write-Host "Собираю..." -ForegroundColor Cyan
& $python -m PyInstaller --noconfirm --clean genis.spec

Write-Host ""
Write-Host "Готово: dist\Genis\Genis.exe" -ForegroundColor Green