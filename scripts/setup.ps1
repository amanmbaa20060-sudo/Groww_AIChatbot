# Creates .venv and installs requirements. Run from repo root:
#   powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
$ErrorActionPreference = "Stop"
# scripts/setup.ps1 -> repo root is parent of scripts/
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
if (-not (Test-Path (Join-Path $Root "corpus\url_manifest.yaml"))) {
    Write-Error "Run this from the project repo (corpus/url_manifest.yaml not found under $Root)."
    exit 1
}

function Test-WindowsAppsStub {
    param([string]$Path)
    return $Path -match '\\WindowsApps\\' -and $Path -match 'python(3)?\.exe$'
}

function Find-PythonLauncher {
    if (-not (Get-Command "py" -ErrorAction SilentlyContinue)) { return $null }
    $out = & py -3 -c "import sys; print(sys.executable)" 2>$null
    if ($LASTEXITCODE -ne 0) { return $null }
    return "$out".Trim()
}

function Find-PythonInLocalPrograms {
    # python.org installer default: %LocalAppData%\Programs\Python\Python312-arm64\python.exe
    # This runs BEFORE PATH resolution so it still works when WindowsApps\python.exe shadows real Python.
    $base = Join-Path $env:LOCALAPPDATA "Programs\Python"
    if (-not (Test-Path $base)) { return $null }
    $found = @()
    Get-ChildItem $base -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        if ($_.Name -notmatch '^Python(\d)(\d+)') { return }
        $maj = [int]$Matches[1]
        $min = [int]$Matches[2]
        $exe = Join-Path $_.FullName "python.exe"
        if (-not (Test-Path $exe)) { return }
        & $exe -c "import sys; assert sys.version_info >= (3, 10)" 2>$null
        if ($LASTEXITCODE -ne 0) { return }
        $found += [PSCustomObject]@{ Path = $exe; SortKey = ($maj * 100 + $min) }
    }
    if ($found.Count -eq 0) { return $null }
    return ($found | Sort-Object SortKey -Descending | Select-Object -First 1).Path
}

function Find-PythonOnPath {
    foreach ($name in @("python3", "python")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        $def = $cmd.Source
        if (Test-WindowsAppsStub $def) {
            Write-Warning "Ignoring Windows Store stub: $def (see README Windows section)."
            continue
        }
        & $def -c "import sys" 2>$null
        if ($LASTEXITCODE -eq 0) { return $def }
    }
    return $null
}

$pythonExe = Find-PythonLauncher
if (-not $pythonExe) { $pythonExe = Find-PythonInLocalPrograms }
if (-not $pythonExe) { $pythonExe = Find-PythonOnPath }

if (-not $pythonExe) {
    Write-Host @"

No usable Python 3 found.

On Windows this is often the Microsoft Store stub. Fix it:

  1) Settings -> Apps -> Advanced app settings -> App execution aliases
     -> Turn OFF "python.exe" and "python3.exe".

  2) Install Python 3.10+ from https://www.python.org/downloads/windows/
     (this script also auto-discovers python.org installs under
     %LocalAppData%\Programs\Python\ even if PATH still points at the Store stub.)

  3) Optional: turn off Store aliases (step 1) and/or enable "Add python.exe to PATH"
     so `python` in a normal shell resolves to the real interpreter.

Then run this script again from the repository root.

"@
    exit 1
}

Write-Host "Using Python: $pythonExe"
& $pythonExe --version

$venv = Join-Path $Root ".venv"
if (-not (Test-Path $venv)) {
    Write-Host "Creating virtual environment at $venv ..."
    & $pythonExe -m venv $venv
}

$venvPy = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Error "venv python missing: $venvPy"
    exit 1
}

Write-Host "Upgrading pip ..."
& $venvPy -m pip install --upgrade pip
Write-Host "Installing requirements ..."
& $venvPy -m pip install -r (Join-Path $Root "requirements.txt")

Write-Host @"

Done. Use this interpreter for all project commands:

  $($venvPy)

Examples:
  & '$venvPy' scripts\validate_manifest.py
  & '$venvPy' -m ingestion.phase1.subphase_1_1_fetch --dry-run

In Cursor: Command Palette -> Python: Select Interpreter -> choose .\.venv\Scripts\python.exe

"@
exit 0
