# TokenPFS — one-click auto installer for Windows 10/11 (PowerShell)
# Usage (in a normal PowerShell window):
#   powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1
# or from the web:
#   iwr -useb https://raw.githubusercontent.com/WFStudio-app/TokenPFS/main/scripts/install.ps1 | iex
$ErrorActionPreference = "Stop"
$Repo    = "https://github.com/WFStudio-app/TokenPFS.git"
$InstallDir = Join-Path $env:USERPROFILE ".tokenpfs\TokenPFS"

Write-Host "== TokenPFS installer (Windows) ==" -ForegroundColor Cyan

# --- 1. Python ---------------------------------------------------------------
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "[i] Python not found — installing via winget..." -ForegroundColor Yellow
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    } else {
        Write-Host "[!] winget unavailable. Install Python manually: https://www.python.org/downloads/" -ForegroundColor Red
        exit 1
    }
    # refresh PATH for this session
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path","User")
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { Write-Host "[!] Python still not on PATH — reopen PowerShell and rerun." -ForegroundColor Red; exit 1 }
}
& python --version
Write-Host "[ok] Python found." -ForegroundColor Green

# --- 2. Git -------------------------------------------------------------------
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    Write-Host "[i] Git not found — installing via winget..." -ForegroundColor Yellow
    winget install -e --id Git.Git --accept-source-agreements --accept-package-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path","User")
    $git = Get-Command git -ErrorAction SilentlyContinue
    if (-not $git) { Write-Host "[!] Git install failed." -ForegroundColor Red; exit 1 }
}
Write-Host "[ok] Git found." -ForegroundColor Green

# --- 3. Ollama ----------------------------------------------------------------
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Host "[i] Ollama not found — downloading official installer..." -ForegroundColor Yellow
    $tmp = Join-Path $env:TEMP "OllamaSetup.exe"
    Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile $tmp
    Start-Process -FilePath $tmp -ArgumentList "/VERYSILENT" -Wait
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path","User")
    $ollama = Get-Command ollama -ErrorAction SilentlyContinue
    if (-not $ollama) {
        Write-Host "[!] Silent install failed — run the downloaded installer manually: $tmp" -ForegroundColor Red
    }
}
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Write-Host "[ok] Ollama found. Starting server (background)..." -ForegroundColor Green
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
} else {
    Write-Host "[!] Continuing without Ollama — TokenPFS will run in DEMO mode." -ForegroundColor Yellow
}

# --- 4. TokenPFS source ---------------------------------------------------------
New-Item -ItemType Directory -Force -Path (Join-Path $env:USERPROFILE ".tokenpfs") | Out-Null
if (Test-Path (Join-Path $InstallDir ".git")) {
    Write-Host "[i] Updating existing installation (git pull)..." -ForegroundColor Yellow
    & git -C $InstallDir pull --ff-only
} else {
    Write-Host "[i] Cloning TokenPFS to $InstallDir ..." -ForegroundColor Yellow
    & git clone --depth 1 $Repo $InstallDir
}

# --- 5. Launcher 'tokenpfs' command ---------------------------------------------
$bin = Join-Path $env:USERPROFILE ".tokenpfs\bin"
New-Item -ItemType Directory -Force -Path $bin | Out-Null
$cmd = Join-Path $bin "tokenpfs.cmd"
@"
@echo off
rem UTF-8 codepage + PYTHONUTF8: prevents UnicodeEncodeError on Cyrillic/box chars
chcp 65001 >nul
set PYTHONUTF8=1
"$PYEXE" "$InstallDir\tokenpfs_app.py" %*
"@ | Set-Content -Path $cmd -Encoding ASCII

$userPath = [System.Environment]::GetEnvironmentVariable("Path","User")
if ($userPath -notlike "*$bin*") {
    [System.Environment]::SetEnvironmentVariable("Path", "$userPath;$bin", "User")
    Write-Host "[ok] Added $bin to user PATH (reopen terminal to use 'tokenpfs')." -ForegroundColor Green
}

Write-Host ""
Write-Host "== Installation complete ==" -ForegroundColor Green
Write-Host "Run:  tokenpfs     (after reopening the terminal)"
Write-Host "  or: python `"$InstallDir\tokenpfs_app.py`""
