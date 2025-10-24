# TrayWeatherApp — Build and Deployment Guide
This Repository contains the full source for the TrayWeatherApp, several themes
and an automated build powershell script for making a windows EXE.

## Dependencies and Requirements
Before running or building the app, install dependencies listed in `requirements.txt`.

### Installation
**NOTE:** There is a prebuilt installtion file in the realse\windows folder

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

## Running the App (Development Mode)
To run directly from source:

```bash
python -m TrayWeatherApp
```

This launches the tray-based weather app using your system Python installation.  
Themes should be located in the `themes/` folder beside your project root.

## Building the Executable (Windows)

To package TrayWeatherApp into a standalone Windows EXE, use the `build.py` build script.

### Prerequisites
- Python 3.10+
- PyInstaller installed via requirements.txt
- (Optional) Inno Setup if you want to build an installer:

  [Download Inno Setup](https://jrsoftware.org/isinfo.php)

  If Inno Setup is not installed a standalone exe file will be created.

## Build JSON: `build.json`
The `build.json` contains the information used to package the EXE file with `pyinstaller`

```json
{
  "AppName": "TrayWeatherApp",
  "Version": "2.1.4",
  "Icon": "$AppName.ico",
  "pyinstaller": [
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--name", "$AppName",
    "--icon", "$Icon",
    "main.py"
  ]
}
```

## Build Script: `build.py`
The `build.py` script automates the entire packaging process.

Run this from the command line at the project root:
```console
python build.py
```

### What It Does
1. It looks for the build.json file and executes `pyinstaller` with parameters in this file
4. Moves the built EXE to the project root.
5. Runs Inno Setup from:
   ```
   build\windows\TrayWeatherApp.iss
   ```
6. If Inno Setup completes successfully:
   - Deletes the standalone EXE file from the root folder.
   - Moves the installation EXE to the root folder.
7. If Inno Setup fails or is skipped, the standalone EXE remains in the project root.
8. Cleans `build/`, `dist/`, `.spec`, and `__pycache__` folders from the application folder.

## Folder Layout
```
C:\Projects\TrayWeatherApp\
│
├── build.ps1
├── requirements.txt               ← project dependencies
├── TrayWeatherApp.exe             ← standalone app (deleted after successful Inno build)
├── TrayWeatherApp.ico             ← app icon
│
├── build\
│   └── windows\
│       └── TrayWeatherApp.iss     ← Inno Setup script
│
├── themes\                        ← external themes (not bundled)
│   ├── Dark.zip
│   ├── Light.zip
│   └── Beach.zip
│
├── release\                     
│   └── windows\
│       └── TrayWeatherApp-Install.exe  ← prebuilt Windows installer
│
└── TrayWeatherApp\                ← Python source package
    ├── main.py
    ├── app.py
    ├── windows.py
    ├── theme.py
    ├── config_utils.py
    ├── __init__.py
    └── ...
```

## Notes
- The resulting EXE is **portable** and reads themes from the external `themes` folder.
- You can adjust the icon path or app name by editing the PowerShell script.
- If Inno Setup isn’t found, the script will still produce a standalone EXE.
- `requirements.txt` ensures consistency across build environments.
- The configuration and a log files are saved to: 
  ```
  C:\Users\<YourName>\.TrayWeatherApp\
  ```

---

## 🛠️ Configuration File

TrayNSLookup stores your settings in a JSON file:
```json
{
  "cities": [
    "New York"
  ],
  "units": "imperial",
  "window_pos": [
    734,
    582
  ],
  "window_size": [
    1180,
    421
  ],
  "debug": false,
  "time_format_24h": false,
  "theme": "Carbon Fiber"
}
```

You can delete this file to reset the app.

---

## Building Tips

- Always run the PyInstaller command from the **project root**.
- The `.spec` file can simplify rebuilding.
