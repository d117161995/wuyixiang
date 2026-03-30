$ErrorActionPreference = 'Stop'

# Scene Library launcher:
# - Starts a local static server at http://localhost
# - Opens the scene library page in browser
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\start.ps1

$port = 5173
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$url = "http://localhost:$port/index.html"

Write-Host "Scene dir: $dir" -ForegroundColor Cyan
Write-Host "Opening:   $url" -ForegroundColor Green
Start-Process $url

# Use built-in Node server (server.mjs) to serve:
# - scene-library files
# - images at /sence/* (external folder)
$node = Get-Command node -ErrorAction SilentlyContinue
if ($node) {
  $env:PORT = "$port"
  & $node.Source (Join-Path $dir 'server.mjs')
  exit $LASTEXITCODE
}

Write-Host "ERROR: Cannot find node.exe. Please install Node.js, then run this script again." -ForegroundColor Red
exit 1

