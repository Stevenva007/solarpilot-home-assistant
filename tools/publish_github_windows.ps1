param(
    [Parameter(Mandatory=$true)]
    [string]$GitHubOwner,
    [string]$Repository = "solarpilot-home-assistant",
    [Parameter(Mandatory=$true)]
    [ValidateSet("mit", "apache-2.0", "gpl-3.0")]
    [string]$License
)

$ErrorActionPreference = "Stop"
$GitHubOwner = $GitHubOwner.Trim().TrimStart('@')
$Repository = $Repository.Trim()
if ($GitHubOwner -notmatch '^[A-Za-z0-9_.-]+$' -or $Repository -notmatch '^[A-Za-z0-9_.-]+$') {
    throw "Ongeldige GitHub owner of repositorynaam."
}
$repoFull = "$GitHubOwner/$Repository"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Description = "SolarPilot - local Home Assistant EMS for PV surplus, flexible loads, heat pumps, EV charging coexistence and batteries."
$Topics = @("home-assistant", "hacs", "energy-management", "ems", "solar", "photovoltaics", "heat-pump", "battery")

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -CommandType Application -ErrorAction SilentlyContinue)) {
        throw "Ontbrekend programma: $Name"
    }
}

function Invoke-NativeChecked {
    param([string]$Program, [string[]]$Arguments, [int[]]$AllowedExitCodes = @(0))
    # ErrorActionPreference alone does not check native process exit codes.
    # Use one checked boundary on Windows PowerShell and current PowerShell.
    $command = Get-Command $Program -CommandType Application -ErrorAction Stop
    $ErrorActionPreference = "Continue"
    $PSNativeCommandUseErrorActionPreference = $false
    $global:LASTEXITCODE = $null
    $output = & $command.Source @Arguments
    $script:LastNativeExitCode = $global:LASTEXITCODE
    if ($null -eq $script:LastNativeExitCode -or $script:LastNativeExitCode -notin $AllowedExitCodes) {
        throw "Programma '$Program' is mislukt (exitcode $script:LastNativeExitCode); publicatie gestopt."
    }
    return $output
}

function Assert-Origin([string]$RemoteUrl, [string]$Expected) {
    # Only exact GitHub identities in recognised HTTPS/SSH forms are accepted.
    # Do not print existing URLs: they may contain credentials.
    $path = $null
    foreach ($prefix in @("https://github.com/", "git@github.com:", "ssh://git@github.com/")) {
        if ($RemoteUrl.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            $path = $RemoteUrl.Substring($prefix.Length).TrimEnd('/')
            break
        }
    }
    if ($null -ne $path -and $path.EndsWith('.git', [System.StringComparison]::OrdinalIgnoreCase)) {
        $path = $path.Substring(0, $path.Length - 4)
    }
    if ($null -eq $path -or -not $path.Equals($Expected, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Bestaande origin hoort niet bij '$Expected'. Controleer de lokale checkout; origin is niet gewijzigd."
    }
}

function Assert-ConfiguredOrigin([string]$Expected) {
    $fetchUrl = (Invoke-NativeChecked -Program "git" -Arguments @("remote", "get-url", "origin") | Out-String).Trim()
    Assert-Origin $fetchUrl $Expected
    # Push URLs can differ from the fetch URL, and git can push to all of them.
    $pushUrls = @(Invoke-NativeChecked -Program "git" -Arguments @("remote", "get-url", "--push", "--all", "origin"))
    if (-not $pushUrls) { throw "Origin heeft geen controleerbare push-bestemming; publicatie gestopt." }
    foreach ($pushUrl in $pushUrls) {
        Assert-Origin -RemoteUrl (([string]$pushUrl).Trim()) -Expected $Expected
    }
}

Push-Location $root
try {
    $Version = (Get-Content "custom_components/solar_pilot/manifest.json" -Raw | ConvertFrom-Json).version
    Require-Command "git"
    Require-Command "gh"
    $Python = $null
    if (Get-Command "py" -CommandType Application -ErrorAction SilentlyContinue) { $Python = "py" }
    elseif (Get-Command "python" -CommandType Application -ErrorAction SilentlyContinue) { $Python = "python" }
    else { throw "Python ontbreekt (py of python)." }

    $hasOrigin = $false
    if (Test-Path ".git") {
        $remotes = @(Invoke-NativeChecked -Program "git" -Arguments @("remote"))
        $hasOrigin = $remotes -contains "origin"
        if ($hasOrigin) {
            Assert-ConfiguredOrigin $repoFull
        }
    }

    Invoke-NativeChecked -Program "gh" -Arguments @("auth", "status") | Out-Host
    Invoke-NativeChecked -Program $Python -Arguments @("tools/configure_repository.py", $GitHubOwner, $Repository) | Out-Host

    $LicenseExists = (Test-Path "LICENSE") -or (Test-Path "LICENSE.txt") -or (Test-Path "LICENSE.md")
    if (-not $LicenseExists) {
        # The legal choice remains the explicitly supplied -License value.
        $licenseLines = @(Invoke-NativeChecked -Program "gh" -Arguments @("api", "licenses/$License", "--jq", ".body"))
        if (-not $licenseLines) { throw "Kon licentietekst '$License' niet ophalen via GitHub CLI." }
        $licenseText = (($licenseLines -join "`n").TrimEnd() + "`n")
        [System.IO.File]::WriteAllText((Join-Path $root "LICENSE"), $licenseText, [System.Text.UTF8Encoding]::new($false))
        Write-Host "Licentie toegevoegd: $License" -ForegroundColor Cyan
    }

    $env:PYTHONDONTWRITEBYTECODE = "1"
    Invoke-NativeChecked -Program $Python -Arguments @("tools/check_public_repository.py") | Out-Host
    Invoke-NativeChecked -Program $Python -Arguments @("tools/check_current_explanation.py") | Out-Host

    if (-not (Test-Path ".git")) {
        Invoke-NativeChecked -Program "git" -Arguments @("init") | Out-Host
    }
    Invoke-NativeChecked -Program "git" -Arguments @("add", ".") | Out-Host
    $status = Invoke-NativeChecked -Program "git" -Arguments @("status", "--porcelain")
    if ($status) {
        Invoke-NativeChecked -Program "git" -Arguments @("commit", "-m", "SolarPilot $Version - public HACS release") | Out-Host
    }
    Invoke-NativeChecked -Program "git" -Arguments @("branch", "-M", "main") | Out-Host

    # Exit 1 from this read-only lookup is the ordinary first-publish state.
    Invoke-NativeChecked -Program "gh" -Arguments @("repo", "view", $repoFull) -AllowedExitCodes @(0, 1) *> $null
    $repoExists = $script:LastNativeExitCode -eq 0
    if (-not $repoExists) {
        Invoke-NativeChecked -Program "gh" -Arguments @("repo", "create", $repoFull, "--public", "--description", $Description) | Out-Host
    }
    if (-not $hasOrigin) {
        Invoke-NativeChecked -Program "git" -Arguments @("remote", "add", "origin", "https://github.com/$repoFull.git") | Out-Host
    }
    Assert-ConfiguredOrigin $repoFull
    Invoke-NativeChecked -Program "git" -Arguments @("push", "-u", "origin", "main") | Out-Host

    Invoke-NativeChecked -Program "gh" -Arguments @("repo", "edit", $repoFull, "--description", $Description, "--enable-issues") | Out-Host
    foreach ($topic in $Topics) {
        Invoke-NativeChecked -Program "gh" -Arguments @("repo", "edit", $repoFull, "--add-topic", $topic) | Out-Host
    }
    Write-Host ""
    Write-Host "Upload klaar: https://github.com/$repoFull" -ForegroundColor Green
    Write-Host "Controleer GitHub -> Actions. Maak de v$Version tag pas nadat repositorytests, HACS, Hassfest, echte HA-startup en browsercontrole groen zijn." -ForegroundColor Yellow
} finally {
    Pop-Location
}
