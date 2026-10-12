# Execute the actual publisher with fictional native git/gh/Python processes.
# No GitHub account, network, real checkout, credentials or HA service is used.
$ErrorActionPreference = "Stop"
$RealPython = (Get-Command "python" -CommandType Application -ErrorAction Stop).Source
$RealPowerShell = [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
$scratch = Join-Path ([System.IO.Path]::GetTempPath()) ("solarpilot-publisher79-" + [guid]::NewGuid().ToString("N"))
$originalPath = $env:PATH
$originalLocation = (Get-Location).Path
$keys = @("SP_PUBLISH_REAL_PYTHON", "SP_PUBLISH_DRIVER", "SP_PUBLISH_TRACE", "SP_PUBLISH_FAIL",
          "SP_PUBLISH_ORIGIN", "SP_PUBLISH_PUSH_URLS", "SP_PUBLISH_ORIGIN_STATE", "SP_PUBLISH_REPO_EXISTS",
          "SP_PUBLISH_TARGET", "SP_PUBLISH_LOCATION", "SP_PUBLISH_BIN")
$previous = @{}
foreach ($key in $keys) { $previous[$key] = [Environment]::GetEnvironmentVariable($key, "Process") }
$utf8 = [System.Text.UTF8Encoding]::new($false)

function Write-ProbeFile([string]$Path, [string]$Content) {
    [System.IO.File]::WriteAllText($Path, $Content, $utf8)
}

function Assert-Probe([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

try {
    New-Item -ItemType Directory -Path $scratch | Out-Null
    $bin = Join-Path $scratch "bin"
    $repo = Join-Path $scratch "fictional-repository"
    $caller = Join-Path $scratch "unrelated-caller"
    foreach ($path in @($bin, $repo, $caller, (Join-Path $repo "tools"), (Join-Path $repo "custom_components/solar_pilot"))) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
    $publisher = Join-Path $repo "tools/publish_github_windows.ps1"
    Copy-Item (Join-Path $PSScriptRoot "publish_github_windows.ps1") $publisher
    Write-ProbeFile (Join-Path $repo "custom_components/solar_pilot/manifest.json") '{"version":"1.0.0-beta.79"}'
    $driver = Join-Path $scratch "native_driver.py"
    Write-ProbeFile $driver @'
import json
import os
from pathlib import Path
import sys

command, args = sys.argv[1], sys.argv[2:]
canonical = "python" if command in ("python", "py") else command
with Path(os.environ["SP_PUBLISH_TRACE"]).open("a", encoding="utf-8") as trace:
    trace.write(json.dumps({"command": canonical, "args": args, "cwd": os.getcwd()}) + "\n")
signature = " ".join([canonical, *args]).replace("\\", "/")
failure = os.environ.get("SP_PUBLISH_FAIL", "")
if failure and signature.startswith(failure):
    sys.exit(7)
state = Path(os.environ["SP_PUBLISH_ORIGIN_STATE"])
origin = state.read_text() if state.exists() else os.environ.get("SP_PUBLISH_ORIGIN", "")
if canonical == "git":
    if args == ["remote"]:
        if origin:
            print("origin")
    elif args[:2] == ["remote", "get-url"]:
        if not origin:
            sys.exit(2)
        if "--push" in args:
            print(os.environ.get("SP_PUBLISH_PUSH_URLS") or origin)
        else:
            print(origin)
    elif args[:3] == ["remote", "add", "origin"]:
        state.write_text(args[3])
    elif args == ["status", "--porcelain"]:
        print(" M README.md")
    elif args == ["init"]:
        Path(".git").mkdir(exist_ok=True)
elif canonical == "gh":
    if args[:2] == ["repo", "view"] and os.environ.get("SP_PUBLISH_REPO_EXISTS") == "0":
        sys.exit(1)
    if args[:1] == ["api"]:
        print("Fictional license body used only by this isolated executable probe.")
sys.exit(0)
'@
    $env:SP_PUBLISH_REAL_PYTHON = $RealPython
    $env:SP_PUBLISH_DRIVER = $driver
    foreach ($name in @("git", "gh", "python", "py")) {
        if ($IsWindows) {
            $launcher = '@echo off' + "`r`n" + '"%SP_PUBLISH_REAL_PYTHON%" "%SP_PUBLISH_DRIVER%" "' + $name + '" %*' + "`r`n" + 'exit /b %errorlevel%' + "`r`n"
            Write-ProbeFile (Join-Path $bin "$name.cmd") $launcher
        } else {
            $launcher = @'
#!/bin/sh
exec "$SP_PUBLISH_REAL_PYTHON" "$SP_PUBLISH_DRIVER" "__COMMAND__" "$@"
'@
            $path = Join-Path $bin $name
            Write-ProbeFile $path ($launcher.Replace("__COMMAND__", $name) + "`n")
            & chmod +x $path
            if ($LASTEXITCODE -ne 0) { throw "Could not make fictional native process executable" }
        }
    }
    $env:PATH = $bin + [System.IO.Path]::PathSeparator + $originalPath
    $env:SP_PUBLISH_TRACE = Join-Path $scratch "native_trace.jsonl"
    $env:SP_PUBLISH_ORIGIN_STATE = Join-Path $scratch "origin_state.txt"
    $env:SP_PUBLISH_TARGET = $publisher
    $env:SP_PUBLISH_LOCATION = Join-Path $scratch "publisher_location.txt"
    $env:SP_PUBLISH_BIN = $bin
    $harness = Join-Path $scratch "publisher_harness.ps1"
    Write-ProbeFile $harness @'
$ErrorActionPreference = "Stop"
$probeExitCode = 0
try {
    foreach ($probeCommand in @("git", "gh", "python", "py")) {
        $probeResolved = (Get-Command $probeCommand -CommandType Application -ErrorAction Stop).Source
        $probeExpected = Join-Path $env:SP_PUBLISH_BIN $(if ($IsWindows) { "$probeCommand.cmd" } else { $probeCommand })
        if ($probeResolved -ne $probeExpected) {
            throw "Fictional executable resolution failed for $probeCommand"
        }
    }
    & $env:SP_PUBLISH_TARGET -GitHubOwner "fictional-owner" -Repository "fictional-repository" -License "mit"
} catch {
    Write-Output $_.ToString()
    $probeExitCode = 1
} finally {
    [System.IO.File]::WriteAllText($env:SP_PUBLISH_LOCATION, (Get-Location).Path)
}
exit $probeExitCode
'@
    $good = "https://github.com/fictional-owner/fictional-repository.git"
    $checks = 0

    function Run-ProbeCase {
        param([string]$Name, [string]$Failure = "", [string]$Origin = $good,
              [string]$PushUrls = "", [bool]$Exists = $true, [bool]$NoGit = $false,
              [bool]$NeedsLicense = $false, [bool]$Success = $false)
        Write-Host "Publisher probe: $Name"
        Remove-Item $env:SP_PUBLISH_TRACE, $env:SP_PUBLISH_ORIGIN_STATE, $env:SP_PUBLISH_LOCATION -ErrorAction SilentlyContinue
        if (Test-Path (Join-Path $repo ".git")) { Remove-Item (Join-Path $repo ".git") -Recurse -Force }
        if (-not $NoGit) { New-Item -ItemType Directory (Join-Path $repo ".git") | Out-Null }
        if ($NeedsLicense) {
            Remove-Item (Join-Path $repo "LICENSE") -ErrorAction SilentlyContinue
        } else {
            Write-ProbeFile (Join-Path $repo "LICENSE") "Fictional existing license`n"
        }
        $env:SP_PUBLISH_FAIL = $Failure
        $env:SP_PUBLISH_ORIGIN = $Origin
        $env:SP_PUBLISH_PUSH_URLS = $PushUrls
        $env:SP_PUBLISH_REPO_EXISTS = if ($Exists) { "1" } else { "0" }
        Set-Location $caller
        $messages = [System.Collections.Generic.List[string]]::new()
        $failed = $false
        # Run the publisher as users do: in a fresh PowerShell process. Sharing
        # this probe's scope would also share cached command resolution and
        # $script/$global variables, hiding which executable actually ran.
        $PSNativeCommandUseErrorActionPreference = $false
        $global:LASTEXITCODE = $null
        try {
            & $RealPowerShell -NoLogo -NoProfile -NonInteractive -File $harness *>&1 |
                ForEach-Object { $messages.Add($_.ToString()) }
            $failed = $global:LASTEXITCODE -ne 0
        } catch {
            $failed = $true
            $messages.Add($_.Exception.Message)
        }
        $diagnostic = $messages -join "`n"
        Assert-Probe ($failed -ne $Success) "$Name returned the wrong success/failure. Publisher output: $diagnostic"
        Assert-Probe ((Get-Location).Path -eq $caller) "$Name did not restore the caller directory"
        Assert-Probe (Test-Path $env:SP_PUBLISH_LOCATION) "$Name did not finish the isolated publisher harness. Publisher output: $diagnostic"
        Assert-Probe ((Get-Content $env:SP_PUBLISH_LOCATION -Raw) -eq $caller) "$Name did not restore the publisher's caller directory"
        $ready = @($messages | Where-Object { $_ -like '*Upload klaar:*' }).Count -gt 0
        Assert-Probe ($ready -eq $Success) "$Name claimed publication after a failed native command"
        Assert-Probe (-not ($messages -join "`n").Contains("fictional_secret")) "$Name exposed an existing credential-like URL"
        Assert-Probe (Test-Path $env:SP_PUBLISH_TRACE) "$Name did not create a native-process trace. Publisher output: $diagnostic"
        $rows = @(Get-Content $env:SP_PUBLISH_TRACE | ForEach-Object { $_ | ConvertFrom-Json })
        Assert-Probe ($rows.Count -gt 0) "$Name did not execute actual fictional native processes"
        foreach ($row in $rows) {
            Assert-Probe ($row.cwd -eq $repo) "$Name ran a native process outside the publisher checkout"
        }
        if ($Failure) {
            $hits = @($rows | Where-Object { ($_.command + " " + ($_.args -join " ")).StartsWith($Failure) })
            Assert-Probe ($hits.Count -eq 1) "$Name did not reach the requested native failure"
            $last = $rows[-1].command + " " + ($rows[-1].args -join " ")
            Assert-Probe ($last.StartsWith($Failure)) "$Name continued invoking commands after failure"
        } elseif (-not $Success) {
            $writes = @($rows | Where-Object { $_.command -ne "git" -or $_.args[0] -ne "remote" -or $_.args[1] -in @("add", "set-url") })
            Assert-Probe ($writes.Count -eq 0) "$Name mutated/authenticated before rejecting the mismatched origin"
        }
        if ($Success) {
            Assert-Probe (@($rows | Where-Object { $_.command -eq "git" -and $_.args[0] -eq "push" }).Count -eq 1) "$Name did not push exactly once"
            Assert-Probe (@($rows | Where-Object { $_.command -eq "git" -and $_.args -contains "--push" }).Count -ge 1) "$Name did not verify effective push destinations"
            Assert-Probe (-not ($rows | Where-Object { $_.args -contains "--force" -or $_.args -contains "set-url" })) "$Name forced or replaced an origin"
        }
        $script:checks++
    }

    foreach ($failure in @("gh auth status", "python tools/configure_repository.py",
            "python tools/check_public_repository.py", "python tools/check_current_explanation.py",
            "git add", "git status", "git commit", "git branch", "gh repo view",
            "git remote get-url origin", "git remote get-url --push --all origin", "git push",
            "gh repo edit fictional-owner/fictional-repository --description",
            "gh repo edit fictional-owner/fictional-repository --add-topic energy-management")) {
        Run-ProbeCase -Name $failure -Failure $failure
    }
    Run-ProbeCase -Name "license failure" -Failure "gh api licenses/mit" -NeedsLicense $true
    Run-ProbeCase -Name "init failure" -Failure "git init" -Origin "" -NoGit $true
    Run-ProbeCase -Name "create failure" -Failure "gh repo create" -Origin "" -Exists $false
    Run-ProbeCase -Name "remote-add failure" -Failure "git remote add origin" -Origin ""
    foreach ($origin in @("https://github.com/other-example/other-repository.git",
            "https://github.com/fictional-owner/fictional-repository-other.git",
            "https://github.com.invalid/fictional-owner/fictional-repository.git",
            "https://fictional_secret@github.com/fictional-owner/fictional-repository.git")) {
        Run-ProbeCase -Name "wrong fetch identity" -Origin $origin
    }
    Run-ProbeCase -Name "different push URL" -PushUrls "https://github.com/other-example/other-repository.git"
    Run-ProbeCase -Name "multiple push URLs with one wrong" -PushUrls ($good + "`nhttps://github.com/other-example/other-repository.git")
    Run-ProbeCase -Name "existing correct HTTPS" -Success $true
    Run-ProbeCase -Name "existing correct SSH" -Origin "git@github.com:fictional-owner/fictional-repository.git" -Success $true
    Run-ProbeCase -Name "existing correct SSH URL" -Origin "ssh://git@github.com/fictional-owner/fictional-repository.git" -Success $true
    Run-ProbeCase -Name "new repository from unrelated cwd" -Origin "" -NoGit $true -Exists $false -NeedsLicense $true -Success $true
    Run-ProbeCase -Name "existing repository no origin" -Origin "" -Success $true
    Write-Host "OK: $checks actual PowerShell/native publisher regressions; no network or real repository mutation"
} finally {
    Set-Location $originalLocation
    $env:PATH = $originalPath
    foreach ($key in $keys) { [Environment]::SetEnvironmentVariable($key, $previous[$key], "Process") }
    if (Test-Path $scratch) { Remove-Item $scratch -Recurse -Force }
}
