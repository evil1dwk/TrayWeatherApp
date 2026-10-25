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

Tests mock weather requests and use temporary settings/theme directories; no API
access or running desktop is required. A manual **Unit tests** GitHub Actions
workflow covers Windows, Linux, and macOS with Python 3.11 and 3.14.
macOS test coverage does not imply a supported macOS executable build.

## Building

```bash
python -m pip install -e ".[build]"
python build.py
# Full build output:
python build.py --verbose
```

Build on the target operating system. Executables go to `releases/windows/`
or `releases/linux/`. Windows optionally uses Inno Setup (`iscc` on PATH).
If Inno Setup is unavailable, the standalone executable remains available.

The build script resolves paths from its own location, so it also works when
invoked by absolute path from another directory. Platform configurations live
in `build/windows/build.json` and `build/linux/build.json`.
Temporary PyInstaller files are kept in `.build/`; tracked build configurations
are preserved.

To create an installable Python wheel:

```bash
python -m pip wheel . --no-deps --wheel-dir dist
```

## Versioning

Current version: **2.2.0**. The previous version, **2.1.4**, already used three parts.

`TrayWeatherApp/_version.py` is the single version source for Python package
metadata, the application, and the Windows installer. Use **MAJOR.MINOR.PATCH**:
major for incompatible changes, minor for compatible additions, patch for fixes.
Builds never increment the version. Release tags should look like `v2.2.0`.

## Project layout

- `pyproject.toml`: package metadata, runtime dependencies, and optional build tools
- `TrayWeatherApp/`: application package and module entry point
- `tests/`: standard-library unittest suite
- `build.py` and `build/<platform>/`: executable and installer configuration
- `themes/`: optional portable theme ZIP files
- `releases/<platform>/`: executable output

Settings retain their existing location:
`~/.TrayWeatherApp/pyqt_tray_weather.json` (under the user profile on Windows).
Existing theme ZIPs beside the source or executable remain usable. Otherwise,
default themes are generated under `~/.TrayWeatherApp/themes/`, which is
writable for installed applications.

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
