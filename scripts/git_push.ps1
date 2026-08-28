# Push to GitHub using GITHUB_USERNAME and GITHUB_TOKEN from .env (never commit .env).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path "$Root\.env")) {
    Write-Error ".env not found at $Root\.env"
}
Get-Content "$Root\.env" | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$' -and $_ -notmatch '^\s*#') {
        Set-Item -Path "env:$($matches[1])" -Value $matches[2]
    }
}
if (-not $env:GITHUB_TOKEN -or -not $env:GITHUB_USERNAME) {
    Write-Error "Set GITHUB_USERNAME and GITHUB_TOKEN in .env"
}
$remote = "https://${env:GITHUB_USERNAME}:${env:GITHUB_TOKEN}@github.com/prendleman/enterprise-agent-gateway.git"
Set-Location $Root
git push $remote @args
