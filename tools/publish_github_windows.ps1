param(
    [Parameter(Mandatory=$true)]
    [string]$GitHubOwner,
    [string]$Repository = "solarpilot-home-assistant",
    [Parameter(Mandatory=$true)]
    [ValidateSet("mit", "apache-2.0", "gpl-3.0")]
    [string]$License
)

$ErrorActionPreference = "Stop"
$Version = (Get-Content (Join-Path $PSScriptRoot "../custom_components/solar_pilot/manifest.json") -Raw | ConvertFrom-Json).version
$Description = "SolarPilot - local Home Assistant EMS for PV surplus, flexible loads, heat pumps, EV charging coexistence and batteries."
$Topics = @("home-assistant", "hacs", "energy-management", "ems", "solar", "photovoltaics", "heat-pump", "battery")

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Ontbrekend programma: $Name"
    }
}

Require-Command "git"
Require-Command "gh"

$Python = $null
if (Get-Command "py" -ErrorAction SilentlyContinue) { $Python = "py" }
elseif (Get-Command "python" -ErrorAction SilentlyContinue) { $Python = "python" }
else { throw "Python ontbreekt (py of python)." }

& gh auth status | Out-Host
& $Python tools/configure_repository.py $GitHubOwner $Repository

$LicenseExists = (Test-Path "LICENSE") -or (Test-Path "LICENSE.txt") -or (Test-Path "LICENSE.md")
if (-not $LicenseExists) {
    # The user makes the legal choice explicitly via -License; fetch the official
    # GitHub license body rather than shipping a silently selected license.
    $licenseLines = & gh api "licenses/$License" --jq '.body'
    if ($LASTEXITCODE -ne 0 -or -not $licenseLines) {
        throw "Kon licentietekst '$License' niet ophalen via GitHub CLI."
    }
    $licenseText = (($licenseLines -join "`n").TrimEnd() + "`n")
    [System.IO.File]::WriteAllText((Join-Path (Get-Location) "LICENSE"), $licenseText, [System.Text.UTF8Encoding]::new($false))
    Write-Host "Licentie toegevoegd: $License" -ForegroundColor Cyan
}

$env:PYTHONDONTWRITEBYTECODE = "1"
& $Python tools/check_public_repository.py
& $Python tools/check_current_explanation.py

if (-not (Test-Path ".git")) {
    git init
}

git add .
$status = git status --porcelain
if ($status) {
    git commit -m "SolarPilot $Version - public HACS release"
}

git branch -M main

$repoFull = "$GitHubOwner/$Repository"
$repoExists = $false
try {
    # A missing repository is a normal first-publish state. Do not let
    # ErrorActionPreference=Stop abort before gh repo create can run.
    gh repo view $repoFull *> $null
    $repoExists = ($LASTEXITCODE -eq 0)
} catch {
    $repoExists = $false
}

if (-not $repoExists) {
    gh repo create $repoFull --public --source . --remote origin --push --description $Description
} else {
    $remote = git remote get-url origin 2>$null
    if ($LASTEXITCODE -ne 0) {
        git remote add origin "https://github.com/$repoFull.git"
    }
    git push -u origin main
}

# Repository metadata used by HACS validation.
gh repo edit $repoFull --description $Description --enable-issues
foreach ($topic in $Topics) {
    gh repo edit $repoFull --add-topic $topic
}

Write-Host ""
Write-Host "Upload klaar: https://github.com/$repoFull" -ForegroundColor Green
Write-Host "Controleer nu eerst GitHub -> Actions. Maak de v$Version tag pas wanneer HACS validation en Hassfest groen zijn." -ForegroundColor Yellow
