$ErrorActionPreference = "SilentlyContinue"

$pidFile = Join-Path $PSScriptRoot "logs\app-pids.txt"

if (-not (Test-Path $pidFile)) {
  Write-Host "No running app PID file found."
  exit 0
}

Get-Content $pidFile | ForEach-Object {
  $parts = $_ -split "="
  if ($parts.Length -eq 2) {
    Stop-Process -Id ([int]$parts[1]) -Force
    Write-Host "Stopped $($parts[0]) process $($parts[1])"
  }
}

Remove-Item $pidFile -Force

