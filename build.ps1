<#
.SYNOPSIS
    Builds a Python application with PyInstaller, moves the EXE to the root directory,
    and runs Inno Setup (ISCC) to package it.

.DESCRIPTION
    - Detects the root and source directories automatically.
    - Runs PyInstaller.
    - Moves the resulting EXE to the root folder.
    - Cleans up build artifacts.
    - Runs ISCC.exe to build an installer.
    - Deletes the standalone EXE only if the installer build succeeds.

.PARAMETER AppName
    The name of your application (used for folder, EXE, icon, and ISS file).
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$AppName
)

# Force UTF-8 output
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 > $null

Write-Host "========================================"
Write-Host "   Building $AppName Executable"
Write-Host "========================================"

# Resolve paths
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$SrcDir  = Join-Path $RootDir $AppName
$IconPath = Join-Path $RootDir "$AppName.ico"
$IssFile = Join-Path $RootDir "build\windows\$AppName.iss"

Write-Host "Root directory: $RootDir"
Write-Host "Source directory: $SrcDir"
Write-Host "ISS file: $IssFile"
Write-Host ""

# Ensure PyInstaller is installed
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] PyInstaller not found. Run: pip install pyinstaller"
    exit 1
}

# Move into source dir
Set-Location $SrcDir

# Clean up old builds
Write-Host "[INFO] Cleaning previous builds..."
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
Remove-Item "$AppName.spec" -ErrorAction SilentlyContinue

# Run PyInstaller
Write-Host "[INFO] Running PyInstaller..."
$Command = @(
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--name", $AppName,
    "--icon", $IconPath,
    "main.py"
)
pyinstaller @Command

# Locate built EXE
$BuiltExe = Join-Path $SrcDir "dist\$AppName.exe"
$TargetExe = Join-Path $RootDir "$AppName.exe"

if (Test-Path $BuiltExe) {
    Write-Host "[INFO] Moving built EXE to root..."
    Move-Item -Force $BuiltExe $TargetExe
} else {
    Write-Host "[ERROR] Build failed: EXE not found."
    exit 1
}

# Clean PyInstaller build artifacts
Write-Host "[INFO] Cleaning build artifacts..."
Remove-Item -Recurse -Force (Join-Path $SrcDir "build") -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $SrcDir "dist") -ErrorAction SilentlyContinue
Remove-Item (Join-Path $SrcDir "$AppName.spec") -ErrorAction SilentlyContinue

# Clean Python cache folders (__pycache__)
Write-Host "[INFO] Removing __pycache__ directories..."
Get-ChildItem -Path $RootDir -Directory -Recurse -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq "__pycache__" } |
    ForEach-Object {
        try {
            Remove-Item -Recurse -Force $_.FullName -ErrorAction Stop
            Write-Host "[INFO] Removed: $($_.FullName)"
        } catch {
            Write-Host "[WARN] Could not remove: $($_.FullName)"
        }
    }

# Return to root directory
Set-Location $RootDir
Write-Host "[INFO] Returned to root directory."
Write-Host ""

# Run Inno Setup if available
if (Test-Path $IssFile) {
    $ISCC = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

    if (Test-Path $ISCC) {
        Write-Host "[INFO] Running Inno Setup Compiler..."
        $ISCCOutput = & "$ISCC" "$IssFile" 2>&1
        $ISCCOutput | ForEach-Object { Write-Host $_ }

        # Detect installer .exe line
        $SetupExe = ($ISCCOutput | Select-String -Pattern "\.exe$").Line | Select-Object -Last 1

        if ($LASTEXITCODE -eq 0 -and $SetupExe) {
            Write-Host ""
            Write-Host "[SUCCESS] Inno Setup build completed successfully."
            Write-Host "Installer created:"
            Write-Host "   $SetupExe"
            Write-Host ""

            # Delete standalone EXE only if Inno Setup succeeded
            if (Test-Path $TargetExe) {
                Remove-Item -Force $TargetExe
                Write-Host "[INFO] Removed standalone EXE: $TargetExe"
            }

        } else {
            Write-Host ""
            Write-Host "[ERROR] Inno Setup failed or output not found."
            Write-Host "Exit code: $LASTEXITCODE"
            Write-Host "[INFO] Keeping standalone EXE: $TargetExe"
        }
    } else {
        Write-Host "[WARNING] ISCC.exe not found at: $ISCC"
        Write-Host "[INFO] Skipping installer build. EXE remains at:"
        Write-Host "   $TargetExe"
    }
} else {
    Write-Host "[WARNING] No ISS file found at: $IssFile"
    Write-Host "[INFO] Skipping installer build. EXE remains at:"
    Write-Host "   $TargetExe"
}

Write-Host ""
Write-Host "========================================"
Write-Host "[DONE] Build process complete."
Write-Host "========================================"
