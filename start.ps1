$ErrorActionPreference = "Stop"

$AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $AppDir ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Run .\install.ps1 first."
}
& $Python (Join-Path $AppDir "scripts\start.py") @args
exit $LASTEXITCODE
