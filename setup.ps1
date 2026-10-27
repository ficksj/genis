# Установка Genis: venv + зависимости + модель

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) {
    throw "Python не найден. Установи Python 3.11+ с python.org и запусти setup.ps1 снова."
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Создаю виртуальное окружение..." -ForegroundColor Cyan
    & $python -m venv .venv
}

$venvPython = Join-Path $root ".venv\Scripts\python.exe"
Write-Host "Обновляю pip..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip --quiet

Write-Host "Ставлю зависимости (mediapipe, PySide6, opencv, pynput, pygrabber)..." -ForegroundColor Cyan
& $venvPython -m pip install -r requirements.txt

Write-Host "Скачиваю модель распознавания руки..." -ForegroundColor Cyan
& $venvPython -c "from app.paths import ensure_model; print('Модель:', ensure_model())"

Write-Host ""
Write-Host "Готово! Запускай run.bat" -ForegroundColor Green
