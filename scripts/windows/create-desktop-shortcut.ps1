<#
.SYNOPSIS
  One-time: pin a real desktop shortcut to Launch-Openbench-Chat.bat.

.DESCRIPTION
  Creates "Open Benchmark Toolkit.lnk" on your Desktop, pointed at
  Launch-Openbench-Chat.bat in this same folder (chat + webUI only, router
  mode - no pentest). Safe to re-run; it just overwrites the .lnk.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\windows\create-desktop-shortcut.ps1
#>
[CmdletBinding()]
param(
    [string] $Name = 'Open Benchmark Toolkit'
)

$ErrorActionPreference = 'Stop'
$Here      = $PSScriptRoot
$Target    = Join-Path $Here 'Launch-Openbench-Chat.bat'
$RepoDir   = Split-Path (Split-Path $Here)          # scripts\windows -> repo root
$IconSrc   = Join-Path $RepoDir 'build\bin\llama-server.exe'
$Desktop   = [Environment]::GetFolderPath('Desktop')
$LinkPath  = Join-Path $Desktop "$Name.lnk"

if (-not (Test-Path $Target)) {
    Write-Host "x Launch-Openbench-Chat.bat not found at $Target" -ForegroundColor Red
    exit 1
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($LinkPath)
$shortcut.TargetPath       = $Target
$shortcut.WorkingDirectory = $Here
$shortcut.WindowStyle      = 7   # minimized - the .bat's own window is just status output
$shortcut.Description      = 'Launch openbench-toolkit chat + webUI (router mode)'
if (Test-Path $IconSrc) {
    # Not a dedicated .ico - just points at llama-server.exe's own icon resource
    # (falls back to the generic exe icon if it has none). Build it first if
    # this doesn't exist yet: scripts\windows\build.ps1 -InstallDeps -WithUI
    $shortcut.IconLocation = "$IconSrc,0"
}
$shortcut.Save()

Write-Host "created: $LinkPath" -ForegroundColor Green
