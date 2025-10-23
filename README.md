# TrayWeatherApp — Build and Deployment Guide

This package contains the full unaltered logic of your TrayWeatherApp split into modules.

---

## Running the App (Development Mode)

To run directly from source:

```bash
python -m TrayWeatherApp
```

This launches the tray-based weather app using your system Python installation.  
Themes should be located in the `themes/` folder beside your project root.

---

## Dependencies and Requirements

Before running or building the app, install dependencies listed in `requirements.txt`.

### Installation
From the project root (`C:\Projects\TrayWeatherApp\`), run:

```bash
pip install -r requirements.txt
```

This ensures your Python environment has all required packages for development and building.

### Included Dependencies
```
PyQt6>=6.4
requests>=2.31
pyinstaller>=6.0
```

You can update versions as needed, but these provide a stable baseline for TrayWeatherApp.

---

## Building the Executable (Windows)

To package TrayWeatherApp into a standalone Windows `.exe`, use the PowerShell build script.

### Prerequisites
- Python 3.10+
- PyInstaller installed via requirements.txt
- (Optional) Inno Setup if you want to build an installer:
  [Download Inno Setup](https://jrsoftware.org/isinfo.php)

---

## Build Script: `build.ps1`

The `build.ps1` script automates the entire packaging process.

Run this from **PowerShell** at the project root:
```powershell
.uild.ps1 -AppName TrayWeatherApp
```

### What It Does
1. Automatically detects your project paths.
2. Cleans old `build/`, `dist/`, `.spec`, and `__pycache__` folders.
3. Runs PyInstaller to generate a single-file executable:
   ```powershell
   pyinstaller --noconfirm --onefile --windowed --name TrayWeatherApp --icon ..\TrayWeatherApp.ico main.py
   ```
4. Moves the built EXE to the project root.
5. Runs Inno Setup from:
   ```
   build\windows\TrayWeatherApp.iss
   ```
6. If Inno Setup completes successfully:
   - Displays the full installer `.exe` path.
   - Deletes the standalone EXE from the root folder.
7. If Inno Setup fails or is skipped, the standalone EXE remains in the project root.

---

## Folder Layout

```
C:\Projects\TrayWeatherApp│
├── build.ps1
├── requirements.txt           ← project dependencies
├── TrayWeatherApp.exe         ← standalone app (deleted after successful Inno build)
├── TrayWeatherApp.ico         ← app icon
├── build│   └── windows│       └── TrayWeatherApp.iss ← Inno Setup script
├── themes\                    ← external themes (not bundled)
│   ├── Dark.zip
│   ├── Light.zip
│   └── Beach.zip
└── TrayWeatherApp\            ← Python source package
    ├── main.py
    ├── app.py
    ├── windows.py
    ├── theme.py
    ├── config_utils.py
    ├── ...
```

---

## Notes

- The resulting EXE is **portable** and reads themes from the external `themes` folder.
- You can adjust the icon path or app name by editing the PowerShell script.
- If Inno Setup isn’t found, the script will still produce the standalone EXE.
- `requirements.txt` ensures consistency across build environments.

---

### Example Console Output
```
========================================
   Building TrayWeatherApp Executable
========================================
[INFO] Running PyInstaller...
[INFO] Moving TrayWeatherApp.exe to root directory...
[INFO] Cleaning up build and dist folders...
[INFO] Removing __pycache__ directories...
[INFO] Running Inno Setup Compiler...
[SUCCESS] Inno Setup build completed successfully.
Installer created:
   C:\Projects\TrayWeatherApp\Output\TrayWeatherAppSetup.exe
[INFO] Removed standalone EXE: C:\Projects\TrayWeatherApp\TrayWeatherApp.exe

[DONE] Build process complete.
========================================
```
