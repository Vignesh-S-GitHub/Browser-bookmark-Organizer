$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$logs = Join-Path $root "logs"
$backendPython = Join-Path $backend ".venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path $logs | Out-Null

if (-not (Test-Path $backendPython)) {
  Write-Host "Setting up backend..."
  Push-Location $backend
  python -m venv .venv
  .\.venv\Scripts\python.exe -m pip install -r requirements.txt
  Pop-Location
}

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
  Write-Host "Setting up frontend..."
  Push-Location $frontend
  npm.cmd install
  Pop-Location
}

Write-Host "Starting backend on http://localhost:8010 ..."
$backendProcess = Start-Process `
  -FilePath $backendPython `
  -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8010" `
  -WorkingDirectory $backend `
  -RedirectStandardOutput (Join-Path $logs "backend.log") `
  -RedirectStandardError (Join-Path $logs "backend.err.log") `
  -PassThru

Write-Host "Starting frontend on http://localhost:5173 ..."
$env:VITE_API_URL = "http://localhost:8010"
$frontendProcess = Start-Process `
  -FilePath "npm.cmd" `
  -ArgumentList "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173" `
  -WorkingDirectory $frontend `
  -RedirectStandardOutput (Join-Path $logs "frontend.log") `
  -RedirectStandardError (Join-Path $logs "frontend.err.log") `
  -PassThru

Set-Content -Path (Join-Path $logs "app-pids.txt") -Value @(
  "backend=$($backendProcess.Id)"
  "frontend=$($frontendProcess.Id)"
)

Start-Sleep -Seconds 3
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "App is running:"
Write-Host "  Frontend: http://localhost:5173"
Write-Host "  Backend:  http://localhost:8010"
Write-Host ""
Write-Host "Logs are in: $logs"
Write-Host "To stop the app, run: .\stop-app.ps1"
