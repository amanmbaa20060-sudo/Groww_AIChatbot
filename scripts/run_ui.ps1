$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Error "Missing $venvPy. Run: powershell -ExecutionPolicy Bypass -File scripts/setup.ps1"
    exit 1
}

$port = if ($env:UI_PORT) { $env:UI_PORT } else { "5173" }
Write-Host "Serving UI on http://127.0.0.1:$port (app/ui/)"
Write-Host "Backend should be running separately (default http://127.0.0.1:8787)."

& $venvPy -m http.server $port --bind 127.0.0.1 --directory app/ui
exit $LASTEXITCODE

