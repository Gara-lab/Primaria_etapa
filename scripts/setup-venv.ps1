<#
.SYNOPSIS
  Bootstraps an empty, isolated .venv for this project.

.DESCRIPTION
  Creates .venv/ in the project root using the Python already installed on
  this device. The venv starts empty on purpose - install only the packages
  a given task actually needs (see CLAUDE.md's Environment section), e.g.:

    .venv\Scripts\pip.exe install playwright && .venv\Scripts\playwright.exe install chromium
    .venv\Scripts\pip.exe install pillow
    .venv\Scripts\pip.exe install nodeenv
    .venv\Scripts\nodeenv.exe --node=24.20.0 .node_env   # isolated Node.js, if a task needs npm tooling

  Do not copy an existing .venv or .node_env folder from another project —
  a venv's activation scripts and pyvenv.cfg embed the absolute path it was
  created at, so a copied venv silently misreports (or breaks on) a
  different path. Always create a fresh one per project with this script.

.NOTES
  Run from the project root: powershell -ExecutionPolicy Bypass -File scripts\setup-venv.ps1
#>

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $projectRoot ".venv"

if (Test-Path $venvPath) {
    Write-Host ".venv already exists at $venvPath - nothing to do."
    exit 0
}

$pythonCmd = Get-Command py -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
}
if (-not $pythonCmd) {
    Write-Error "No 'py' or 'python' found on PATH. Install Python first."
    exit 1
}

Write-Host "Creating .venv at $venvPath using $($pythonCmd.Source) ..."
& $pythonCmd.Source -m venv $venvPath

Write-Host "Upgrading pip ..."
& (Join-Path $venvPath "Scripts\python.exe") -m pip install --upgrade pip

Write-Host ""
Write-Host "Done. .venv created empty. Install only what this project's current task needs, e.g.:"
Write-Host "  .venv\Scripts\pip.exe install <package>"
Write-Host "  .venv\Scripts\pip.exe install nodeenv; .venv\Scripts\nodeenv.exe --node=24.20.0 .node_env"
