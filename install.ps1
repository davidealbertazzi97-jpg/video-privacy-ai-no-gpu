$ErrorActionPreference = "Stop"

if ($env:PROCESSOR_ARCHITECTURE -ne "AMD64") {
    throw "This installer currently supports Windows x86-64 only."
}

$AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$UvVersion = "0.11.16"
$Asset = "uv-x86_64-pc-windows-msvc.zip"
$ExpectedHash = "dd9d6d6554bfab265bfa98aa8e8a406c5c3a7b97582f93de1f4d48d9154a0395"
$ToolsDir = Join-Path $AppDir ".tools"
$Archive = Join-Path $ToolsDir "uv-download.zip"
$Unpacked = Join-Path $ToolsDir "uv-unpacked"

New-Item -ItemType Directory -Force -Path $ToolsDir | Out-Null
Invoke-WebRequest `
  -Uri "https://github.com/astral-sh/uv/releases/download/$UvVersion/$Asset" `
  -OutFile $Archive `
  -UseBasicParsing

$ActualHash = (Get-FileHash -Algorithm SHA256 $Archive).Hash.ToLowerInvariant()
if ($ActualHash -ne $ExpectedHash) {
    throw "uv archive checksum mismatch"
}

New-Item -ItemType Directory -Force -Path $Unpacked | Out-Null
Expand-Archive -Path $Archive -DestinationPath $Unpacked -Force
$UvSource = Get-ChildItem -Path $Unpacked -Filter "uv.exe" -Recurse |
    Select-Object -First 1
if (-not $UvSource) {
    throw "uv.exe was not found in the verified archive"
}
$UvPath = Join-Path $ToolsDir "uv.exe"
Copy-Item -Path $UvSource.FullName -Destination $UvPath -Force

$env:LOCAL_AI_APP_UV = $UvPath
& $UvPath run --python 3.12 (Join-Path $AppDir "scripts\bootstrap.py") @args
exit $LASTEXITCODE
