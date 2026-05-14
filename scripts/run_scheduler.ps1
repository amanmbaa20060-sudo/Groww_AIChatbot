# Local scheduler = Phase 1.6 orchestrator (same job as GitHub Actions corpus-refresh.yml)
# From repo root:
#   powershell -ExecutionPolicy Bypass -File scripts/run_scheduler.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "No .venv found - running setup.ps1 first..."
    & "$PSScriptRoot\setup.ps1"
    if (-not (Test-Path $venvPy)) {
        Write-Error "setup.ps1 did not produce $venvPy"
        exit 1
    }
}

$dash = [array]::IndexOf($args, "--")
if ($dash -ge 0) {
    $pass = $args[($dash + 1)..($args.Length - 1)]
} else {
    $pass = @("--ignore-robots")
}

Write-Host "Scheduler: validate manifest"
& $venvPy scripts/validate_manifest.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Scheduler: Phase 1.6 orchestrate"
& $venvPy -m ingestion.phase1.subphase_1_6_orchestrate @pass
exit $LASTEXITCODE
