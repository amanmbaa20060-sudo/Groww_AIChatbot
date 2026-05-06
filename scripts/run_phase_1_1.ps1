# Run Phase 1.1 fetch (creates .venv via setup.ps1 if missing). From repo root:
#   powershell -ExecutionPolicy Bypass -File scripts/run_phase_1_1.ps1 -- -DryRun
#   powershell -ExecutionPolicy Bypass -File scripts/run_phase_1_1.ps1 -- --dry-run
# Arguments after `--` are passed to: python -m ingestion.phase1.subphase_1_1_fetch
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "No .venv found — running scripts\setup.ps1 first..."
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
    $pass = $args
}

Write-Host "Running: $venvPy -m ingestion.phase1.subphase_1_1_fetch $pass"
& $venvPy -m ingestion.phase1.subphase_1_1_fetch @pass
exit $LASTEXITCODE
