# 🌦️ TrayWeatherApp

A lightweight **system tray weather monitor** for Windows and Linux built with **Python 3.11+** and **PyQt6**.  
TrayWeatherApp provides real-time weather updates, quick forecasts, and customizable themes — all from your system tray.

![Light](screenshots/Light.png)

![Dark](screenshots/Dark.png)

---

## 🧭 Features

- 🌡️ **Live weather data** for multiple cities  
- 🎨 **Customizable themes** (Dark, Light, Beach, etc.)  
- ⚙️ **Settings persistence** — city, units, theme, and window layout are saved  
- 📍 **Tray icon controls** — right-click for menu options:
  - *Refresh Weather*
  - *Change City*
  - *Switch Theme*
  - *Quit*
- 💾 **Local configuration** saved under your user profile
- 🖥️ **Cross-platform support** — works on both Windows and Linux

---

## Installation and development

Requires Python **3.11+** on Windows or Linux. From the repository root:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux: source .venv/bin/activate
python -m pip install -e .
python -m TrayWeatherApp
```

The installed command `trayweatherapp` also launches the app. Use
`python -m TrayWeatherApp --version` to display its version without opening the GUI.
The module name is case-sensitive on Linux.

## Unit tests

```bash
python -m unittest discover -s tests -v
```

Tests include offscreen Qt widget checks, mock weather requests, and use temporary
settings/theme directories; no API
access or running desktop is required. A manual **Unit tests** GitHub Actions
workflow covers Windows, Linux, and macOS with Python 3.11 and 3.14.
macOS test coverage does not imply a supported macOS executable build.

## Building

```bash
python -m pip install -e ".[build]"
python scripts/build.py
# Full build output:
python scripts/build.py --verbose
```

Build on the target operating system. The executable and release archive go to
`dist/`:

- Windows: `TrayWeatherApp.exe` and `TrayWeatherApp-2.3.0-windows-<arch>.zip`
- Linux: `TrayWeatherApp` and `TrayWeatherApp-2.3.0-linux-<arch>.tar.gz`

There is no Windows installer step. Archives contain the standalone executable
and any optional theme ZIPs from `themes/`. Extract before launching. Linux
archives preserve executable permissions. Built-in themes are included inside the executable; no writable application
folder is required.

The build script resolves paths from its own location, so it also works when
invoked by absolute path from another directory. Platform configurations live
in `packaging/windows/build.json` and `packaging/linux/build.json`, matching
TrayNSLookup. Temporary PyInstaller files go to the ignored `build/` folder.

To create an installable Python wheel:

```bash
python -m pip wheel . --no-deps --wheel-dir dist
```

## Versioning

Current version: **2.3.0**. This is the target for the first published release.

`TrayWeatherApp/_version.py` is the single version source for Python package
metadata, the application, and release archive names. Use **MAJOR.MINOR.PATCH**:
major for incompatible changes, minor for compatible additions, patch for fixes.
Builds never increment the version. Release tags should look like `v2.3.0`.

## Project layout

- `pyproject.toml`: package metadata, runtime dependencies, and optional build tools
- `TrayWeatherApp/`: application package and module entry point
- `tests/`: standard-library unittest suite
- `scripts/build.py`: executable build and release archive creation
- `packaging/<platform>/build.json`: tracked PyInstaller configuration
- `build/`: temporary build files (ignored)
- `themes/`: optional portable theme ZIP files
- `dist/`: executable and release archive output (ignored)

## Themes

Choose **System**, **Light**, **Dark**, or one of the other bundled presets in
Settings. System follows the OS appearance preference when available, with Dark
as its fallback. Existing saved selections are retained.

Settings shows a sample weather card before you Save. Cancel leaves the running
theme unchanged. Use **Import Theme**, **Export Theme**, and **Open Themes Folder**
to manage custom JSON themes or import existing theme ZIPs.

Built-in themes ship inside the application. Custom themes live under
~/.TrayWeatherApp/themes/; settings retain their existing location at
~/.TrayWeatherApp/pyqt_tray_weather.json (under your user profile on Windows).
See [Theme format and compatibility](docs/themes.md) for examples and details.

The tray menu's **About TrayWeatherApp** shows the current application version,
creator, project link, and issue link.

---

## ⚙️ Configuration File

TrayWeatherApp saves user settings in a JSON file:
```json
{
  "cities": ["New York"],
  "units": "imperial",
  "window_pos": [722, 575],
  "window_size": [1195, 425],
  "debug": false,
  "time_format_24h": false,
  "theme": "Dark"
}
```
You can delete this file to reset settings.

---
